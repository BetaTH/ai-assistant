from langchain_groq import ChatGroq

from ai_assistant.env import env

llm = ChatGroq(
    api_key=env.AI_API_KEY, model='deepseek-r1-distill-llama-70b', temperature=0
)
