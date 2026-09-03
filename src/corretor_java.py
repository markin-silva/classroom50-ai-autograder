from typing import TypedDict, Optional
import os

# Ajuste o import conforme a estrutura real do projeto
from llm import get_gemini_response

class CorrectionState(TypedDict):
    enunciado: str
    gabarito: str
    codigo_aluno: str
    feedback_bruto: str
    avaliacao_status: str

def load_prompt(filepath: str) -> str:
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def correction_node(state: CorrectionState) -> dict:
    """Nó principal que formata os prompts e aciona a LLM."""
    
    # Caminhos relativos ao WORKDIR do Docker (/app)
    system_prompt = load_prompt("prompts/system_prompt.md")
    user_template = load_prompt("prompts/user_template.md")
    
    prompt_completo = f"{system_prompt}\n\n" + user_template.format(
        enunciado=state["enunciado"],
        gabarito=state["gabarito"],
        codigo_aluno=state["codigo_aluno"]
    )
    
    resposta_json = get_gemini_response(prompt_completo)
    
    return {"feedback_bruto": resposta_json}