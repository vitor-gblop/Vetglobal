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
    """Decode text files, falling back to latin-1 for legacy documents."""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


# These are the only accepted labels: each English label and its pt-BR translation.
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
    """Extract supported labels and collect their multiline values."""
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
    """Normalize the supported TXT template into a deterministic summary."""
    fields = _extract_fields(text)
    return (
        f"Paciente: {fields['pet_name']} | Idade: {fields['age']} | "
        f"Tutor: {fields['owner_name']} | Espécie: {fields['species']}\n"
        f"Sintomas: {fields['symptoms']}\n"
        f"Notas Clínicas: {fields['clinical_notes']}"
    )


def extract_formated_data(text: str) -> str:
    """Backward-compatible alias for the original misspelled function name."""
    return extract_formatted_data(text)


def save_file_to_disk(file: UploadFile, pet_name: str, owner_name: str) -> str:
    """Save the uploaded document with a unique, predictable filename."""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    file_extension = Path(file.filename).suffix.lower() if file.filename else ".txt"

    safe_pet_name = pet_name.strip().replace(" ", "_").lower()
    safe_owner_name = owner_name.strip().replace(" ", "_").lower()
    
    unique_suffix = uuid.uuid4().hex[:6]
    
    file_path = STORAGE_DIR / f"{safe_pet_name}_{safe_owner_name}_{unique_suffix}{file_extension}"

    file.file.seek(0)
    with file_path.open("wb") as buffer:
        buffer.write(file.file.read())
    return str(file_path)


def remove_files_from_storage(documents: list) -> None:
    """Remove the files associated with documents deleted from the database."""
    storage_root = STORAGE_DIR.resolve()
    for document in documents:
        file_path = Path(document.file_path).resolve()
        if storage_root not in file_path.parents:
            raise ValueError(f"Document path is outside storage: {document.file_path}")
        file_path.unlink(missing_ok=True)