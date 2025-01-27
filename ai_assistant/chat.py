import os
import signal
import sys

from langchain.schema import HumanMessage, SystemMessage

from ai_assistant.llm   import llm


def signal_handler(sig, frame):
    print("\nEncerrando o chat...")
    sys.exit(0)

def chat_loop():
    # Identificar o sinal de interrupção (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)

    # Mensagem inicial do sistema
    messages = [
        SystemMessage(content="Você é um assistente de IA útil e amigável.")
    ]
    
    print("Bem-vindo ao Chat de IA. Digite 'sair' para encerrar.")
    
    while True:
        # Receber entrada do usuário
        user_input = input("\nVocê: ")
        
        # Condição de saída
        if user_input.lower() in ['sair', 'exit', 'quit']:
            print("Encerrando o chat...")
            break
        
        # Adicionar mensagem do usuário
        messages.append(HumanMessage(content=user_input))
        
        try:
            # Obter resposta da IA
            print("IA: ", end="")
            for response in llm.stream(messages):
              print(response.content, end="", flush=True)
            print()
            # Adicionar resposta ao histórico
            messages.append(response)
        
        except Exception as e:
            print(f"Erro: {e}")

if __name__ == "__main__":
    chat_loop()