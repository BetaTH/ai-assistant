from typing import Annotated, Literal, Optional, Callable
from typing_extensions import TypedDict

from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import tools_condition
from pydantic import BaseModel, Field

from ai_assistant.llm     import llm
from ai_assistant.tools   import map_directory_structure_tree_tools
from ai_assistant.utils   import create_tool_node_with_fallback


def update_dialog_stack(left: list[str], right: Optional[str]) -> list[str]:
    """Push or pop the state."""
    if right is None:
        return left
    if right == "pop":
        return left[:-1]
    return left + [right]


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    dialog_state: Annotated[
        list[
            Literal[
                    "directory_map_assistant",
            ]
        ],
        update_dialog_stack,
    ]

class Agent:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            result = self.runnable.invoke(state)
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response.
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {'messages': result}
    
class CompleteOrEscalate(BaseModel):
    """Uma ferramenta para marcar a tarefa atual como concluída e/ou para escalar o controle da caixa de diálogo para o assistente principal,
    quem pode redirecionar a caixa de diálogo com base nas necessidades do usuário."""

    cancel: bool = True
    reason: str

    class Config:
        json_schema_extra = {
            "example": {
                "cancel": True,
                "reason": "Usuário mudou de ideia sobre a tarefa atual",
            },
            "example 2": {
                "cancel": True,
                "reason": "Eu finalizei completamente a tarefa",
            },
            "example 3": {
                "cancel": False,
                "reason": "Eu preciso salvar os arquivos",
            },
        }



directory_map_assistant_prompt = ChatPromptTemplate.from_messages([
    ('system', 
    "Você é um assistente especializado em mapear diretórios, "
    "você é um assistente auxiliar que recebe tarefas do assistente principal. " 
    "Você possui a habilidade de criar um mapa da estrutura de um diretório. "
    "Use a tools 'get_directory_tree' para mapear a estrutura, ela vai retornar um json. "
    "Além disso voce também tem duas tools que podem salvar essa estrutura em arquivos .json ou .txt (estas so podem ser chamadas apos obter o mapa da estrutura). "
    "\n\n Lembre-se que a tarefa não esta concluída ate todas as tools relevantes tenham sido usadas. "
    "o usuário não precisa saber das suas habilidades, então não precisa mencioná-las"
    "\n\nSe o usuário precisar de ajuda e nenhuma de suas ferramentas for apropriada para isso, então"
    ' "CompleteOrEscalate" a caixa de diálogo para o assistente de host. Não desperdice o tempo do usuário. Não invente ferramentas ou funções inválidas.',),
    ('placeholder', '{messages}'),
])
directory_map_assistant_runnable = directory_map_assistant_prompt | llm.bind_tools(map_directory_structure_tree_tools + [CompleteOrEscalate])
directory_map_assistant = Agent(directory_map_assistant_runnable)
class ToDirectoryMapAssistant(BaseModel):
    """Transfere para um assistente especializado para lidar com o mapeamento de diretórios. 
    Usado quando se deseja obter o mapa da estrutura de um diretório"""

    request: str = Field(
        description="Qualquer instrução necessária para que o assistente especializado em mapear diretórios complete com exito sua tarefa"
    )


primary_assistant_prompt = ChatPromptTemplate.from_messages([
    ('system', 
    "Você é um assistente de IA útil e amigável. Seu nome é F9. Responda sempre em português-BR. "
    "Você é um assistente geral e orquestrador de outros assistentes especializados em diversas tarefas, "
    "você pode simplesmente responder o usuário ou então transferir o trabalho para o assistente especializado mais adequado para a tarefa que o usuário pediu. "
    "Caso for chamar chamar algum assistente auxiliar melhore a demanda do usuário para que o assistente auxiliar consiga ter um melhor contexto  "
    ),
    ('placeholder', '{messages}'),
])

primary_assistant_runnable = primary_assistant_prompt | llm.bind_tools([ToDirectoryMapAssistant])

def create_entry_node(assistant_name: str, new_dialog_state: str) -> Callable:
    def entry_node(state: State) -> dict:
        tool_call_id = state["messages"][-1].tool_calls[0]["id"]
        return {
            "messages": [
                ToolMessage(
                    content=f"O assistente agora é {assistant_name}. Reflita sobre a conversa acima entre o assistente do anfitrião e o usuário."
                    f" A intenção do usuário não foi satisfeita. Use as ferramentas fornecidas para ajudar o usuário. Lembre-se, você é {assistant_name}, "
                    "e as tarefas não serão concluídas até que você tenha invocado com êxito as ferramentas apropriadas."
                    "Se o usuário mudar de ideia ou precisar de ajuda para outras tarefas, chame a função CompleteOrEscalate para permitir que o assistente principal assuma o controle."
                    " Não mencione quem você é - apenas atue como um assistente auxiliar do assistente geral.",
                    tool_call_id=tool_call_id,
                )
            ],
            "dialog_state": new_dialog_state,
        }

    return entry_node



graph_builder = StateGraph(State)

def pop_dialog_state(state: State) -> dict:
    """Pop the dialog stack and return to the main assistant.

    This lets the full graph explicitly track the dialog flow and delegate control
    to specific sub-graphs.
    """
    messages = []
    if state["messages"][-1].tool_calls:
        # Note: Doesn't currently handle the edge case where the llm performs parallel tool calls
        messages.append(
            ToolMessage(
                content="Retomando o diálogo com o assistente geral. Por favor, reflita sobre a conversa passada e ajude o usuário conforme necessário.",
                tool_call_id=state["messages"][-1].tool_calls[0]["id"],
            )
        )
    return {
        "dialog_state": "pop",
        "messages": messages,
    }


graph_builder.add_node("leave_skill", pop_dialog_state)
graph_builder.add_edge("leave_skill", "primary_assistant")



graph_builder.add_node(
    "enter_directory_map_assistant",
    create_entry_node("Directory Structure Map Assistant", "directory_map_assistant"),
)
graph_builder.add_node("directory_map_assistant", directory_map_assistant)
graph_builder.add_edge("enter_directory_map_assistant", "directory_map_assistant")
graph_builder.add_node('directory_map_assistant_tools', create_tool_node_with_fallback(map_directory_structure_tree_tools))

def route_directory_map_assistant(
    state: State,
):
    route = tools_condition(state)
    print(route)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    did_cancel = any(tc["name"] == CompleteOrEscalate.__name__ for tc in tool_calls)
    if did_cancel:
        return "leave_skill"
    return "directory_map_assistant_tools"

graph_builder.add_conditional_edges(
    "directory_map_assistant",
    route_directory_map_assistant,
    ["directory_map_assistant_tools", "leave_skill", END],
)
graph_builder.add_edge('directory_map_assistant_tools', 'directory_map_assistant')

primary_assistant = Agent(primary_assistant_runnable)

graph_builder.add_node("primary_assistant", primary_assistant)

def route_primary_assistant(
    state: State,
):
    route = tools_condition(state)
    if route == END:
        return END
    tool_calls = state["messages"][-1].tool_calls
    if tool_calls:
        if tool_calls[0]["name"] == ToDirectoryMapAssistant.__name__:
            return "enter_directory_map_assistant"
    raise ValueError("Invalid route")

graph_builder.add_conditional_edges(
    "primary_assistant",
    route_primary_assistant,
    [
        "enter_directory_map_assistant",
        END,
    ],
)

def route_to_workflow(
    state: State,
) -> Literal[
    "primary_assistant",
    "directory_map_assistant",
]:
    """If we are in a delegated state, route directly to the appropriate assistant."""
    dialog_state = state.get("dialog_state")
    if not dialog_state:
        return "primary_assistant"
    return dialog_state[-1]

graph_builder.add_conditional_edges(START, route_to_workflow)


memory = MemorySaver()

graph = graph_builder.compile(checkpointer=memory)