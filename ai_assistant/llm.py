from langchain_groq import ChatGroq

from ai_assistant.env import env

llm = ChatGroq(
    api_key=env.AI_API_KEY, model='llama-3.3-70b-versatile', temperature=0
)