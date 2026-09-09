from io import BytesIO

import pytest
from fastapi import UploadFile

from src.main.utils.file_utils import file_reader, file_validator


def test_validates_txt_upload():
    # Monta um UploadFile equivalente ao arquivo recebido pela rota.
    file = UploadFile(
        filename="clinical.txt",
        file=BytesIO(b"clinical notes"),
        headers={"content-type": "text/plain"},
    )

    # Confirma a extensão validada e a leitura correta do conteúdo.
    assert file_validator(file) == "txt"
    assert file_reader(b"clinical notes") == "clinical notes"


def test_rejects_unsupported_upload():
    # Simula um DOCX, formato que não faz parte do contrato da API.
    file = UploadFile(
        filename="clinical.docx",
        file=BytesIO(b"content"),
        headers={"content-type": "application/octet-stream"},
    )

    # A validação deve interromper o fluxo com uma exceção.
    with pytest.raises(Exception):
        file_validator(file)
