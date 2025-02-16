import os
import signal
import sys

from langchain_core.messages import AIMessageChunk, AIMessage
from ai_assistant.graph import graph
from ai_assistant.utils import print_event


def signal_handler(sig, frame):
    print("\nEncerrando o chat...")
    sys.exit(0)

def stream_graph_updates(user_input: str):
  config = {"configurable": {"thread_id": "1"}}

  # print("IA: ", end="")
  _printed = set()
  for event in graph.stream(
    {"messages": [{"role": "user", "content": user_input}]},
    config,
    stream_mode="values"):
      print_event(event, _printed)
      message = event.get('messages')
      if message:
          if isinstance(message, list):
              message = message[-1]
      if isinstance(message, AIMessage) and message.content:
          print('\nAssistant:')
          print(message.content)
      # if isinstance(event, tuple):
      #   if isinstance(event[0], AIMessageChunk):
      #     message = event[0].content
      #     print(message, end="", flush=True)
  # print()

def chat_loop():

  signal.signal(signal.SIGINT, signal_handler)

  print("Bem-vindo ao Chat de IA. Digite 'sair' para encerrar.")
  
  while True:
      try:
          # Receber entrada do usuário
          user_input = input("\nVocê: ")
          # Condição de saída
          if user_input.lower() in ['sair', 'exit', 'quit']:
              print("Encerrando o chat...")
              break
  
          stream_graph_updates(user_input)
      except Exception as e:
          print(f"Erro: {e}")
          break

if __name__ == "__main__":
    chat_loop()