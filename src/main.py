import argparse
import json
import os
import sys
import time
from pathlib import Path
from google.genai.errors import ServerError
from langgraph.graph import StateGraph, END
from corretor_java import correction_node, CorrectionState

def ler_conteudo_diretorio(caminho_dir: str, extensao: str = None) -> str:
    """Varre um diretório e concatena o conteúdo dos arquivos encontrados."""
    caminho = Path(caminho_dir)
    if not caminho.exists():
        print(f"AVISO: Caminho não encontrado - {caminho_dir}", file=sys.stderr)
        return ""
    
    # Se for um arquivo individual
    if caminho.is_file():
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.read()

    # Se for um diretório, busca todos os arquivos (ou filtra por extensão)
    conteudos = []
    for arquivo in caminho.rglob('*'):
        if arquivo.is_file():
            if extensao and not arquivo.name.endswith(extensao):
                continue
            with open(arquivo, 'r', encoding='utf-8') as f:
                conteudos.append(f"--- Arquivo: {arquivo.name} ---\n" + f.read())
    
    return "\n\n".join(conteudos)

def executar_com_retry(graph, initial_state, max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Iniciando avaliação via LangGraph (Tentativa {attempt}/{max_retries})...")
            return graph.invoke(initial_state)
        except ServerError as e:
            print(f"Erro no servidor Gemini na tentativa {attempt}: {e}", file=sys.stderr)
            if attempt == max_retries:
                raise e
            time.sleep(5)

def main():
    parser = argparse.ArgumentParser(description="Classroom50 Autograder Engine")
    # Argumentos com VALORES PADRÃO apontando para os volumes montados pelo Docker
    parser.add_argument("--aluno", default="/app/submission", help="Diretório do aluno")
    parser.add_argument("--gabarito", default="/app/reference", help="Diretório do gabarito")
    parser.add_argument("--enunciado", default="/app/reference", help="Diretório do enunciado")
    parser.add_argument("--output", default="/app/output/results.json", help="Arquivo JSON de saída")
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        print("ERRO: GEMINI_API_KEY não foi injetada.", file=sys.stderr)
        sys.exit(1)

    # Leitura automática e flexível
    codigo_aluno = ler_conteudo_diretorio(args.aluno, extensao=".java")
    codigo_gabarito = ler_conteudo_diretorio(args.gabarito, extensao=".java")
    enunciado = ler_conteudo_diretorio(args.enunciado, extensao=".md")

    initial_state = {
        "enunciado": enunciado,
        "gabarito": codigo_gabarito,
        "codigo_aluno": codigo_aluno,
        "feedback_bruto": "",
        "avaliacao_status": ""
    }

    workflow = StateGraph(CorrectionState)
    workflow.add_node("correcao", correction_node)
    workflow.set_entry_point("correcao")
    workflow.add_edge("correcao", END)
    graph = workflow.compile()

    final_state = executar_com_retry(graph, initial_state)

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as out:
        out.write(final_state["feedback_bruto"])
        
    print(f"Avaliação concluída com sucesso! Resultados gravados em: {args.output}")

if __name__ == "__main__":
    main()