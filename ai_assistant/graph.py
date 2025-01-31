from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import tools_condition

from ai_assistant.llm     import llm
from ai_assistant.tools   import map_directory_structure_tree_tools
from ai_assistant.utils   import create_tool_node_with_fallback


class State(TypedDict):
    messages: Annotated[list, add_messages]

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

chatbot_initial_prompt = ChatPromptTemplate.from_messages([
    ('system', 
    "Você é um assistente de IA útil e amigável. Seu nome é F9. Responda sem em português-BR"
    "Você pode simplesmente responder o usuario ou então realizar ações usando suas habilidades, caso seja solicitado"
    "Você possui a habilidade de criar um mapa da estrutura de um diretório"
    "Para isso foi dispõe de ferramentas que te ajudam a primeiro pegar um caminho (path) absoluto a partir de um caminho recebido e fazer o mapa da estrutura"
    "além disso voce tambem pode salvar em essa estrutura em arquivos .json ou .txt"
    "o usuario não precisa saber das suas habilidades, então não precisa mencioná-las"),
    ('placeholder', '{messages}'),
])
chatbot = chatbot_initial_prompt | llm.bind_tools(map_directory_structure_tree_tools)

chatbot_agent = Agent(chatbot)

graph_builder = StateGraph(State)

graph_builder.add_node("chatbot", chatbot_agent)
graph_builder.add_node('tools', create_tool_node_with_fallback(map_directory_structure_tree_tools))
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)
graph_builder.add_conditional_edges(
    'chatbot',
    tools_condition,
)
graph_builder.add_edge('tools', 'chatbot')

memory = MemorySaver()

graph = graph_builder.compile(checkpointer=memory)