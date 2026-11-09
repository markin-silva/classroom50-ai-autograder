import argparse
import json
import os
import sys
import time
from pathlib import Path
from langgraph.graph import StateGraph, END
from corretor_java import correction_node, CorrectionState

MAX_TENTATIVAS = 3
PAUSA_BASE_SEGUNDOS = 5  # pausas progressivas: 5s, 10s, ...

AVALIACOES_VALIDAS = {"Certo", "Parcialmente Certo", "Errado"}

# Resultado usado quando a IA falha em todas as tentativas ou a chave não está configurada.
RESULTADO_FALLBACK = {
    "avaliacao": "Parcialmente Certo",
    "justificativa": "Ocorreu uma instabilidade temporária na avaliação via IA.",
    "dica_correcao": "Por favor, aguarde alguns minutos e execute no terminal o comando `gh student submit` para tentar novamente.",
    "sugestao_correcao": "",
}

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

def validar_resultado(texto: str) -> dict:
    """Garante que a resposta da IA segue o contrato do workflow. Lança ValueError se não seguir."""
    dados = json.loads(texto)
    if not isinstance(dados, dict):
        raise ValueError("A resposta da IA não é um objeto JSON.")
    if dados.get("avaliacao") not in AVALIACOES_VALIDAS:
        raise ValueError(f"Valor inválido em 'avaliacao': {dados.get('avaliacao')!r}")
    for chave in ("justificativa", "dica_correcao"):
        if not isinstance(dados.get(chave), str):
            raise ValueError(f"Chave '{chave}' ausente ou não é texto.")
    if dados.get("sugestao_correcao") is None:
        dados["sugestao_correcao"] = ""
    if not isinstance(dados["sugestao_correcao"], str):
        raise ValueError("Chave 'sugestao_correcao' não é texto.")
    return {
        "avaliacao": dados["avaliacao"],
        "justificativa": dados["justificativa"],
        "dica_correcao": dados["dica_correcao"],
        "sugestao_correcao": dados["sugestao_correcao"],
    }

def executar_com_retry(graph, initial_state) -> dict:
    """Executa o grafo até MAX_TENTATIVAS vezes, com pausa progressiva entre as tentativas."""
    ultimo_erro = None
    for tentativa in range(1, MAX_TENTATIVAS + 1):
        try:
            print(f"Iniciando avaliação via LangGraph (Tentativa {tentativa}/{MAX_TENTATIVAS})...")
            estado = graph.invoke(initial_state)
            return validar_resultado(estado["feedback_bruto"])
        except Exception as e:  # 503/429, instabilidades de rede e respostas fora do contrato
            ultimo_erro = e
            print(f"Falha na tentativa {tentativa}: {type(e).__name__}: {e}", file=sys.stderr)
            if tentativa < MAX_TENTATIVAS:
                pausa = PAUSA_BASE_SEGUNDOS * 2 ** (tentativa - 1)
                print(f"Aguardando {pausa}s antes de tentar novamente...", file=sys.stderr)
                time.sleep(pausa)
    raise RuntimeError(f"Todas as {MAX_TENTATIVAS} tentativas falharam.") from ultimo_erro

def main():
    parser = argparse.ArgumentParser(description="Classroom50 Autograder Engine")
    # Argumentos com VALORES PADRÃO apontando para os volumes montados pelo Docker
    parser.add_argument("--aluno", default="/app/submission", help="Diretório do aluno")
    parser.add_argument("--gabarito", default="/app/reference", help="Diretório do gabarito")
    parser.add_argument("--enunciado", default="/app/reference", help="Diretório do enunciado")
    parser.add_argument("--output", default="/app/output/results.json", help="Arquivo JSON de saída")
    args = parser.parse_args()

    resultado = None
    try:
        if not os.getenv("GEMINI_API_KEY"):
            raise RuntimeError("GEMINI_API_KEY não foi injetada.")

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

        resultado = executar_com_retry(graph, initial_state)
    except Exception as e:
        print(f"ERRO na avaliação: {type(e).__name__}: {e}", file=sys.stderr)

    if resultado is None:
        print("Gerando results.json de fallback.", file=sys.stderr)
        resultado = RESULTADO_FALLBACK

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as out:
        json.dump(resultado, out, ensure_ascii=False, indent=2)

    print(f"Avaliação concluída. Resultados gravados em: {args.output}")
    # Sempre sucesso: o Job do GitHub Actions deve ficar verde, inclusive no fallback.
    sys.exit(0)

if __name__ == "__main__":
    main()
