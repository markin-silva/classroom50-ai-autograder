import argparse
import json
import os
import sys
import time
from google.genai.errors import ServerError
from langgraph.graph import StateGraph, END
from corretor_java import correction_node, CorrectionState

def ler_arquivo(caminho: str) -> str:
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"AVISO: Arquivo não encontrado - {caminho}", file=sys.stderr)
        return ""

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
    parser = argparse.ArgumentParser()
    parser.add_argument("--aluno", required=True)
    parser.add_argument("--gabarito", required=True)
    parser.add_argument("--enunciado", required=True)
    parser.add_argument("--output", default="./output/results.json")
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        print("ERRO: GEMINI_API_KEY não injetada.", file=sys.stderr)
        sys.exit(1)

    initial_state = {
        "enunciado": ler_arquivo(args.enunciado),
        "gabarito": ler_arquivo(args.gabarito),
        "codigo_aluno": ler_arquivo(args.aluno),
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
        
    print(f"Avaliação concluída! Resultados gravados em: {args.output}")

if __name__ == "__main__":
    main()