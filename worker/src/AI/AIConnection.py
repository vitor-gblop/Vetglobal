import os
from pathlib import Path

from google import genai
from dotenv import load_dotenv


load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

def summarize_text(
    text: str,
    language: str | None = None,
    model: str | None = None,
) -> str:
    language = language or os.getenv("SUMMARY_LANGUAGE", "english")
    model = model or os.getenv("GOOGLE_MODEL", "gemini-3.5-flash-lite")
    #
    if not api_key:
        raise ValueError("Defina a variável de ambiente GOOGLE_API_KEY.")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=(
            f"resuma o texto abaixo em {language}, destacando os pontos principais "
            "e mantendo um resumo claro e objetivo, de acordo com o modelo(não gere texto extra nem explicações apenas o resumo exigido):\n\n"
            "nome do pet ou animal: \n"
            "nome do tutor: \n"
            "idade: \n"
            "raça: \n"
            "simtomas: \n"
            "notas clinicas: \n"
            "observações gerais: \n\n"
            f"{text}"
        ),
    )

    return response.text


# def summarize_file(file_path: str, model: str = "gemini-2.5-flash") -> str:
#     file_content = Path(file_path).read_text(encoding="utf-8")
#     return summarize_text(file_content, model=model)
