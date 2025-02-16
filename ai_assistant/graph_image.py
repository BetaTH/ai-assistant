# from graphviz import Source
from langchain_core.runnables.graph_png import PngDrawer

from ai_assistant.graph import graph



# Criando um objeto Graphviz e exportando como PNG
def get_graph():
  graph.get_graph().draw_mermaid_png(output_file_path="ai_assistant_graph.png")

