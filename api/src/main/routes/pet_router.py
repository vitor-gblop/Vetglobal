import asyncio
import base64
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Form, HTTPException, status, UploadFile, File
from dotenv import load_dotenv
# banco de dados
from src.main.schemas.document_schemas import DocumentPayload, DocumentResponse
from src.main.connection.database import get_db
from sqlalchemy.orm import Session
# esquemas
from src.main.schemas.pet_schemas import PetCreate, PetResponse, PetUpdate
from src.main.schemas.job_schemas import JobStatus
# modelos
from src.main.models.pet_model import Pet
from src.main.models.job_model import Job
from src.main.models.pet_doc_model import DocumentTypes, Pet_Document 
# utilitários
from src.main.utils.file_utils import (
    build_file_path,
    file_reader,
    file_validator,
    remove_files_from_storage,
    save_file_to_disk,
)
from src.main.utils.model_utils import now


pet_router = APIRouter(prefix='/pets', tags=['pets'])
load_dotenv()

# Criação
@pet_router.post('/', response_model= PetResponse, status_code=status.HTTP_201_CREATED)
async def create_pet(
    payload: PetCreate, 
    db: Session = Depends(get_db)
):
    new_pet = Pet(
        name = payload.name,
        owner_name = payload.owner_name,
        species = payload.species,
        age = payload.age,
        created_at = now()
    )
    # adiciona o pet
    db.add(new_pet)
    db.commit()
    db.refresh(new_pet)
    
    # resposta
    return new_pet


# Leitura
def _get_pet(pet_id: int, db: Session) -> Pet:
    pet = db.query(Pet).filter(Pet.id == pet_id).first()
    if not pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pet with id {pet_id} not found",
        )
    return pet

@pet_router.get("/", response_model=list[PetResponse], status_code=status.HTTP_200_OK)
def list_pets(db: Session = Depends(get_db)):
    return db.query(Pet).order_by(Pet.id).all()


@pet_router.get("/{pet_id}", response_model=PetResponse, status_code=status.HTTP_200_OK)
def retrieve_pet(pet_id: int, db: Session = Depends(get_db)):
    return _get_pet(pet_id, db)

# Atualização
def _update_pet(pet_id: int, payload: PetUpdate, db: Session) -> Pet:
    pet = _get_pet(pet_id, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pet, field, value)
    db.commit()
    db.refresh(pet)
    return pet

@pet_router.put("/{pet_id}", response_model=PetResponse, status_code=status.HTTP_200_OK)
def update_pet(pet_id: int, payload: PetUpdate, db: Session = Depends(get_db)):
    return _update_pet(pet_id, payload, db)


# Exclusão
@pet_router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(pet_id: int, db: Session = Depends(get_db)) -> None:
    pet = _get_pet(pet_id, db)
    documents = list(pet.documents)
    # remove arquivos
    remove_files_from_storage(documents)
    
    db.delete(pet)
    db.commit()
    return None



@pet_router.post('/{pet_id}/documents', status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    pet_id: int,
    document_type: DocumentTypes = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    body = DocumentPayload(document_type=document_type)
    return await _upload_document(pet_id, body, file, db, use_ai=False)


@pet_router.post('/{pet_id}/documents/ai', status_code=status.HTTP_202_ACCEPTED)
async def upload_document_for_ai(
    pet_id: int,
    document_type: DocumentTypes = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    body = DocumentPayload(document_type=document_type)
    return await _upload_document(pet_id, body, file, db, use_ai=True)


@pet_router.put('/documents/{document_id}', status_code=status.HTTP_202_ACCEPTED)
async def overwrite_document(
    document_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    """Substitui o conteúdo de um documento sem perder sua identidade no banco de dados."""
    document = (
        db.query(Pet_Document)
        .filter(Pet_Document.id == document_id)
        .first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with id {document_id} not found",
        )

    return await _upload_document(
        document.pet_id,
        DocumentPayload(document_type=document.doc_type),
        file,
        db,
        use_ai=False,
        document_to_overwrite=document,
    )


async def _upload_document(
    pet_id: int,
    body: DocumentPayload,
    file: UploadFile,
    db: Session,
    use_ai: bool,
    document_to_overwrite: Pet_Document | None = None,
) -> DocumentResponse:
    file_ext = file_validator(file)
    
    # 1. Busca e valida se o pet existe
    _pet = _get_pet(pet_id, db)

    contents = await file.read()
    candidate_path = (
        Path(document_to_overwrite.file_path)
        if document_to_overwrite
        else build_file_path(
            file,
            body.document_type.value,
            _pet.name,
            _pet.owner_name,
            f".{file_ext}",
        )
    )
    candidate_file_name = candidate_path.name
    if (
        not document_to_overwrite
        and body.document_type == DocumentTypes.UNIQUE
        and db.query(Pet_Document)
        .filter_by(
            doc_type=body.document_type,
            file_name=candidate_file_name,
        )
        .first()
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um documento UNIQUE com esse nome",
        )

    file_path = save_file_to_disk(
        file,
        body.document_type.value,
        _pet.name,
        _pet.owner_name,
        existing_path=(
            document_to_overwrite.file_path
            if document_to_overwrite
            else None
        ),
    )
    file_name = Path(file_path).name

    if file_ext == "txt":
        # 2. Lendo o conteúdo para a lógica do worker
        text_content = file_reader(contents)  # retorna texto
    
    elif file_ext == "pdf":
        text_content = base64.b64encode(contents).decode("ascii")  # retorna texto codificado em base64

    if document_to_overwrite:
        existing_document = document_to_overwrite
        old_file_path = existing_document.file_path
        new_doc = existing_document
        new_doc.file_name = file_name
        new_doc.file_extension = file_ext
        new_doc.file_path = file_path
        new_doc.summary = ""
    else:
        new_doc = Pet_Document(
            pet_id=_pet.id,
            file_name=file_name,
            file_extension=file_ext,
            file_path=file_path,
            doc_type=body.document_type,
            summary="",
        )
        db.add(new_doc)
    db.flush()

    new_job = Job(document_id=new_doc.id, status=JobStatus.ENQUEUED)
    db.add(new_job)
    db.commit()
    db.refresh(new_doc)
    db.refresh(new_job)
    if document_to_overwrite and old_file_path != file_path:
        Path(old_file_path).unlink(missing_ok=True)

    # cria o callback para verificar os dados novos do worker
    api_base_url = os.environ["API_BASE_URL"].rstrip("/")
    worker_url = os.environ["WORKER_START_URL"]
    callback_url = f"{api_base_url}/internal/jobs/{new_job.id}/complete"
    _payload = json.dumps(
        {
            "job_id": new_job.id,
            "document_id": new_doc.id,
            "document_content": text_content,
            "document_extension": file_ext,
            "use_ai": use_ai,
            "callback_url": callback_url,
        }
    ).encode("utf-8")
    # inicia o serviço do worker
    request = Request(
        worker_url,
        data=_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        await asyncio.to_thread(urlopen, request, timeout=10)
        
    except Exception as exc:
        new_job.status = JobStatus.FAILED
        new_job.error_message = f"Worker indisponível: {exc}"
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker indisponível para processar o documento",
        ) from exc

    return DocumentResponse(
        id=new_doc.id,
        document_id=new_doc.id,
        job_id=new_job.id,
        status=new_job.status,
    )