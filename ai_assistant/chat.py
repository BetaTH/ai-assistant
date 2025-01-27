import os
import signal
import sys

from ai_assistant.graph import graph


def signal_handler(sig, frame):
    print("\nEncerrando o chat...")
    sys.exit(0)

def stream_graph_updates(user_input: str):
  config = {"configurable": {"thread_id": "1"}}

  print("IA: ", end="")
  for event in graph.stream(
    {"messages": [{"role": "user", "content": user_input}]},
    config,
    stream_mode="messages"):
      if isinstance(event, tuple):
        message = event[0].content
        print(message, end="", flush=True)
  print()

def chat_loop_langgraph():

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