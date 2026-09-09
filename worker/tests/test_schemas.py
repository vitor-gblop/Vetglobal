import pytest
from pydantic import ValidationError

from src.main.schemas.job_schemas import JobCreate


def test_job_schema_accepts_ai_flag():
    # Cria um job válido para um PDF que será processado pela IA.
    job = JobCreate(
        document_id=1,
        document_content="conteúdo clínico válido",
        document_extension="pdf",
        use_ai=True,
    )

    # O schema deve preservar a opção use_ai recebida pela API.
    assert job.use_ai is True


def test_job_schema_rejects_unsupported_extension():
    # Tenta criar um job com uma extensão não suportada pelo worker.
    with pytest.raises(ValidationError):
        # O Pydantic deve rejeitar o payload antes de entrar na fila.
        JobCreate(
            document_id=1,
            document_content="conteúdo clínico válido",
            document_extension="docx",
        )
