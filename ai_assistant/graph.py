from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from ai_assistant.llm   import llm


class State(TypedDict):
    messages: Annotated[list, add_messages]

class Agent:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        return {'messages': self.runnable.invoke(state)}

chatbot_initial_prompt = ChatPromptTemplate.from_messages([
    ('system', 'Você é um assistente de IA útil e amigável. Seu nome é Thielson'),
    ('placeholder', '{messages}'),
])
chatbot = chatbot_initial_prompt | llm

# def chatbot_agent(state: State):
#     print(state)
#     return {"messages": chatbot.invoke(state)}

chatbot_agent = Agent(chatbot)


graph_builder = StateGraph(State)

graph_builder.add_node("chatbot", chatbot_agent)
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

memory = MemorySaver()

graph = graph_builder.compile(checkpointer=memory)