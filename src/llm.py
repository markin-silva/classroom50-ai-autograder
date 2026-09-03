import os
from google import genai
from google.genai import types

def get_gemini_response(prompt_texto: str) -> str:
    """Aciona o Gemini forçando o retorno estrito em JSON."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    chat = client.chats.create(
        model='gemini-3.6-flash',
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    response = chat.send_message(prompt_texto)
    return response.text