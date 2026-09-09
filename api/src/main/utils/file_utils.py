import re
import uuid
from pathlib import Path

from fastapi import File, HTTPException, UploadFile, status

STORAGE_DIR = Path("src/main/docs")


def file_validator(file=File(...)):
    allowed_extensions = [".txt", ".pdf"]
    allowed_content_types = ["text/plain", "application/pdf"]

    filename = file.filename or ""
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_extensions or file.content_type not in allowed_content_types:
        raise HTTPException(
            detail="Formato de arquivo inválido. Apenas arquivos .txt ou .pdf são aceitos.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    return file_ext.removeprefix(".")


def file_reader(content: bytes) -> str:
    """Decodifica arquivos de texto, com fallback para latin-1 em documentos legados."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


# Estes são os únicos rótulos aceitos: cada rótulo em inglês e sua tradução para pt-BR.
_FIELD_LABELS = {
    "pet_name": ("pet name", "nome do pet"),
    "age": ("age", "idade"),
    "owner_name": ("owner name", "nome do proprietário"),
    "species": ("breed", "raça"),
    "symptoms": ("symptoms", "sintomas"),
    "clinical_notes": ("clinical notes", "notas clínicas"),
}
_LABEL_TO_FIELD = {
    label: field
    for field, labels in _FIELD_LABELS.items()
    for label in labels
}
_LABEL_PATTERN = "|".join(
    re.escape(label) for labels in _FIELD_LABELS.values() for label in labels
)
_FIELD_LINE_PATTERN = re.compile(
    rf"^\s*(?P<label>{_LABEL_PATTERN})\s*:\s*(?P<value>.*)\s*$",
    re.IGNORECASE,
)


def _extract_fields(text: str) -> dict[str, str]:
    """Extrai os rótulos suportados e coleta seus valores multilinha."""
    fields: dict[str, list[str]] = {field: [] for field in _FIELD_LABELS}
    current_field: str | None = None

    for raw_line in text.splitlines():
        match = _FIELD_LINE_PATTERN.match(raw_line)
        if match:
            current_field = _LABEL_TO_FIELD[match.group("label").lower()]
            value = match.group("value").strip()
            if value:
                fields[current_field].append(value)
            continue

        if current_field and raw_line.strip():
            fields[current_field].append(raw_line.strip())

    return {
        field: " ".join(values) if values else "Não informado"
        for field, values in fields.items()
    }


def extract_formatted_data(text: str) -> str:
    """Normaliza o template TXT suportado em um resumo determinístico."""
    fields = _extract_fields(text)
    return (
        f"Paciente: {fields['pet_name']} | Idade: {fields['age']} | "
        f"Tutor: {fields['owner_name']} | Espécie: {fields['species']}\n"
        f"Sintomas: {fields['symptoms']}\n"
        f"Notas Clínicas: {fields['clinical_notes']}"
    )


def extract_formated_data(text: str) -> str:
    """Alias compatível com a versão anterior para o nome da função com erro de grafia."""
    return extract_formatted_data(text)


def save_file_to_disk(
    file: UploadFile,
    doc_type: str,
    pet_name: str,
    owner_name: str,
    existing_path: str | None = None,
) -> str:
    """Salva o documento enviado usando sua identidade como nome do arquivo."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    file_extension = Path(file.filename).suffix.lower() if file.filename else ".txt"

    if existing_path:
        file_path = Path(existing_path)
    else:
        file_path = build_file_path(file, doc_type, pet_name, owner_name, file_extension)

    file.file.seek(0)
    with file_path.open("wb") as buffer:
        buffer.write(file.file.read())
    return str(file_path)


def build_file_path(
    file: UploadFile,
    doc_type: str,
    pet_name: str,
    owner_name: str,
    file_extension: str | None = None,
) -> Path:
    """Constrói o caminho de armazenamento sem gravar o conteúdo enviado."""
    extension = file_extension or (
        Path(file.filename).suffix.lower() if file.filename else ".txt"
    )
    safe_file_name = Path(file.filename or "document").stem.strip().replace(" ", "_").lower()
    safe_pet_name = pet_name.strip().replace(" ", "_").lower()
    safe_owner_name = owner_name.strip().replace(" ", "_").lower()
    file_name = f"{safe_file_name}_{safe_pet_name}_{safe_owner_name}_{doc_type.lower()}"
    # se não for único, adiciona UUID
    if doc_type.lower() != "unique":
        file_name = f"{file_name}_{uuid.uuid4().hex[:6]}"
    return STORAGE_DIR / f"{file_name}{extension}"


def remove_files_from_storage(documents: list) -> None:
    """Remove os arquivos associados aos documentos excluídos do banco de dados."""
    storage_root = STORAGE_DIR.resolve()
    for document in documents:
        file_path = Path(document.file_path).resolve()
        if storage_root not in file_path.parents:
            raise ValueError(f"Document path is outside storage: {document.file_path}")
        file_path.unlink(missing_ok=True)