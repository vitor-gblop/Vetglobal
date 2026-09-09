import base64
from pathlib import Path

import pytest

from src.main.utils.file_utils import (
    extract_document_text,
    extract_formatted_data,
)


def test_extracts_pet_pdf_fields():
    # Localiza o PDF de exemplo usado como documento clínico.
    pdf_path = Path(__file__).parents[2] / "pet_doc_pdf.pdf"
    # Converte o arquivo para o Base64 recebido pelo worker.
    encoded_pdf = base64.b64encode(pdf_path.read_bytes()).decode("ascii")

    # Extrai o texto do PDF e gera o resumo padronizado.
    text = extract_document_text(encoded_pdf, "pdf")
    summary = extract_formatted_data(text)

    # Confirma que os campos principais do modelo foram reconhecidos.
    assert "Paciente: Luna" in summary
    assert "Idade: 4" in summary
    assert "Tutor: Ana" in summary
    assert "Sintomas: Vômito Desidratação" in summary


def test_rejects_invalid_pdf():
    # Simula um PDF inválido no mesmo formato Base64 do payload real.
    invalid_pdf = base64.b64encode(b"not a pdf").decode("ascii")

    # A função deve rejeitar o conteúdo com uma mensagem de domínio.
    with pytest.raises(ValueError, match="Não foi possível ler o PDF"):
        extract_document_text(invalid_pdf, "pdf")


def test_extracts_txt_content():
    # Define um conteúdo TXT simples para testar o caminho sem PDF.
    content = "Nome do pet: Luna\nIdade: 4"

    # Para TXT, o conteúdo deve ser preservado sem transformação.
    assert extract_document_text(content, "txt") == content
