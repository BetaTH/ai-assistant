import os
import json
from typing import List, Optional

from langchain_core.tools import tool

@tool
def get_resolved_path(path: Optional[str]) -> str:
    """
    Resolve o caminho absoluto de um diretório ou arquivo a partir da home do usuário ou do diretório atual.
    Caso não seja fornecido um caminho, será retornado o caminho absoluto do diretório atual.
    Caso seja fornecido um caminho, será retornado o caminho absoluto do diretório ou arquivo levando em conta a home do usuário.
    Função necessária para garantir que o caminho fornecido seja válido.
    ideal para ser usada em conjunto com outras funções que requerem um caminho absoluto.
    

    Args:
        path (Optional[str]): Caminho do diretório ou arquivo a partir da home do usuário.

    Returns:
        str: Caminho absoluto do diretório ou arquivo.
        
    Example:
        get_resolved_path("my_project/teste")
    """
    resolved_path = os.path.abspath('./') if not path else os.path.expanduser("~") + "/" + path
    print("get_resolved_path")
    return resolved_path

@tool
def get_directory_tree(path: str, ignore_dirs: Optional[List[str]] = None) -> str:
    """
    Gera a estrutura em árvore de um diretório no formato JSON (string), ignorando arquivos/diretórios especificados,
    e considerando arquivos e diretórios listados no arquivo `.gitignore` (se existir).

    Args:
        path (str): Caminho do diretório a ser explorado.
        ignore_dirs (Optional[List[str]]): Lista de arquivos/diretórios a serem ignorados (opcional). Se não fornecido,
                                           serão usados diretórios comuns de ignorados como `.git`, `node_modules`, etc.

    Returns:
        str: Estrutura do diretório no formato JSON (string).
        
    Example:
        get_directory_tree("/home/thielson/my_project", ["test_dir", "temp_dir"])
    """
    # Lista padrão de diretórios/arquivos a serem ignorados

    default_ignore_dirs = [
        '.git', 
        '.venv', 
        'venv', 
        'node_modules', 
        '__pycache__', 
        '.pytest_cache', 
        '.mypy_cache'
    ]
    
    # Se ignore_dirs não for fornecido, combina com a lista padrão e o conteúdo do .gitignore
    if ignore_dirs is None:
        ignore_dirs = default_ignore_dirs
        gitignore_path = os.path.join(path, ".gitignore")
        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                gitignore_files = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            ignore_dirs.extend(gitignore_files)
    else:
        ignore_dirs = set(ignore_dirs)  # Remove duplicatas
    
    # Função interna para construir a árvore
    def build_tree(current_path: str) -> str:
        """
        Constrói recursivamente a árvore de diretórios e arquivos em um formato estruturado.

        Args:
            current_path (str): Caminho do diretório atual a ser analisado.

        Returns:
            dict: Dicionário representando a estrutura de diretórios e arquivos.
        """
        tree = {"name": os.path.basename(current_path), "children": []}
        try:
            entries = os.listdir(current_path)
            # Filtra os arquivos e diretórios ignorados
            entries = [entry for entry in entries if entry not in ignore_dirs]
            
            # Separando pastas e arquivos
            directories = sorted([entry for entry in entries if os.path.isdir(os.path.join(current_path, entry))])
            files = sorted([entry for entry in entries if os.path.isfile(os.path.join(current_path, entry))])
            
            # Primeiro adicionamos as pastas, depois os arquivos
            for directory in directories:
                tree["children"].append(build_tree(os.path.join(current_path, directory)))
            for file in files:
                tree["children"].append({"name": file})

        except PermissionError:
            pass  # Ignora diretórios sem permissão de acesso
        return tree
    result = json.dumps(build_tree(path))
    return result

@tool
def save_json_to_file(json_string: str, output_path: str) -> None:
    """
    Salva um JSON formatado em string em um arquivo no formato .json.

    Está é uma função auxiliar, ou seja ela só pode ser chamada depois de alguma outra função, que tenha como retorno uma JSON formatado como string, tenha sido executada

    Ela poderá ser usada também caso tenha certeza que o que esta sendo passado é no arg json_string seja um JSON (string)

    Só usar essa função caso seja solicitado pelo usuário.

    Args:
        json_string (str): JSON (string).
        output_path (str): Caminho do arquivo de saída (.json).

    Returns:
        str: Texto confirmando a criação do arquivo.
        
    Example:
        save_json_to_file("{ 'key' : 'value' }", "path_to_directory/file_name.json")
    """
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(json_string)
    return f"Arquivo JSON salvo em: {output_path}"

@tool
def save_json_structure_as_txt(json_string: str, output_path: str) -> None:
    """

    Está função é especifica para converter um em JSON (string) para o formato de texto estilizado e salva em um arquivo `.txt`.

    Está é uma função auxiliar, ou seja ela só pode ser chamada depois de alguma outra função, que tenha como retorno uma JSON formatado como string, tenha sido executada
    
    Ela poderá ser usada também caso tenha certeza que o que esta sendo passado é no arg json_string seja um JSON (string)
    
    Só usar essa função caso seja solicitado pelo usuário.

    A estrutura será formatada como uma árvore com linhas e ramas representando a hierarquia de diretórios e arquivos.

    Args:
        json_string (str): JSON (string).
        output_path (str): Caminho do arquivo de saída (.txt).
    
    Returns:
        str: Texto confirmando a criação do arquivo.
        
    Example:
        save_tree_as_txt("{ 'key' : 'value' }", "path_to_directory/file_name.txt")
    """

    def json_to_stylized_text(node: dict, is_last_parent: bool = True, prefix: str = "", is_root: bool = False) -> List[str]:
        """
        Converte um nó da árvore JSON em um formato estilizado com linhas e ramas.

        Args:
            node (dict): Nó da árvore contendo o nome e os filhos.
            is_last_parent (bool): Indica se o nó é o último da lista de filhos.
            prefix (str): Prefixo que indica a profundidade na árvore.
            is_root (bool): Indica se o nó é a raiz da árvore.

        Returns:
            List[str]: Lista de linhas formatadas representando a estrutura da árvore.
        """
        rama = "├──" if not is_last_parent else "└──"
        lines = [f"{prefix}{rama} {node['name']}/"] if not is_root else [f"{node['name']}/"]
        if "children" in node:
            for i, child in enumerate(node["children"]):
                is_last = i == len(node["children"]) - 1
                new_prefix = (f"{prefix}│   " if not is_last_parent else f"{prefix}    ") if not is_root else ""
                lines.extend(json_to_stylized_text(child, is_last, new_prefix))
        return lines

    tree = json.loads(json_string)
    stylized_lines = json_to_stylized_text(tree, is_root=True)
    with open(output_path, "w", encoding="utf-8") as file:
        file.write("\n".join(stylized_lines))
    return f"Estrutura salva em: {output_path}"


map_directory_structure_tree_tools = [get_directory_tree, save_json_to_file, save_json_structure_as_txt]

# Exemplo de uso
if __name__ == "__main__":
    directory_path = "/home/thielson/personal/ai-assistant"  # Caminho do diretório a ser explorado
    json_output_path = "directory_structure.json"
    txt_output_path = "/home/thielson/personal/ai-assistant/directory_structure.txt"

    # Gerar JSON
    directory_json = get_directory_tree(directory_path)

    # Salvar JSON
    # save_json_to_file(directory_json, json_output_path)

    # Salvar estrutura em formato .txt estilizado
    save_json_structure_as_txt(directory_json, txt_output_path)