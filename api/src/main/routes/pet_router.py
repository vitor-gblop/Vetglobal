import asyncio
import base64
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from dotenv import load_dotenv
# database
from src.main.schemas.document_schemas import DocumentResponse
from src.main.connection.database import get_db
from sqlalchemy.orm import Session
# schemas
from src.main.schemas.pet_schemas import PetCreate, PetResponse, PetUpdate
from src.main.schemas.job_schemas import JobStatus
# models
from src.main.models.pet_model import Pet
from src.main.models.job_model import Job
from src.main.models.pet_doc_model import Pet_Document 
# utils
from src.main.utils.file_utils import file_reader, file_validator, save_file_to_disk, remove_files_from_storage
from src.main.utils.model_utils import now


pet_router = APIRouter(prefix='/pets', tags=['pets'])
load_dotenv()

# Create
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
    # add pet
    db.add(new_pet)
    db.commit()
    db.refresh(new_pet)
    
    # response
    return new_pet


# Read
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

# Update
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


# Delete
@pet_router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(pet_id: int, db: Session = Depends(get_db)) -> None:
    pet = _get_pet(pet_id, db)
    documents = list(pet.documents)
    # remove files
    remove_files_from_storage(documents)
    
    db.delete(pet)
    db.commit()
    return None



@pet_router.post('/{pet_id}/documents', status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    pet_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    return await _upload_document(pet_id, file, db, use_ai=False)


@pet_router.post('/{pet_id}/documents/ai', status_code=status.HTTP_202_ACCEPTED)
async def upload_document_for_ai(
    pet_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    return await _upload_document(pet_id, file, db, use_ai=True)

async def _upload_document(
    pet_id: int,
    file: UploadFile,
    db: Session,
    use_ai: bool,
) -> DocumentResponse:
    file_ext = file_validator(file)
    
    # 1. Busca e valida se o pet existe
    _pet = db.query(Pet).filter_by(id=pet_id).first()
    if not _pet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pet not found",
        )
    
    contents = await file.read()

    if file_ext == "txt":
        # 2. Lendo conteúdo para a lógica do worker
        text_content = file_reader(contents) # returns text 

        # 3. Salva o arquivo no disco local
        file_path = save_file_to_disk(file, _pet.name, _pet.owner_name)
        file_name = Path(file_path).name
    
    elif file_ext == "pdf":
        file_path = save_file_to_disk(file, _pet.name, _pet.owner_name)
        file_name = Path(file_path).name
        text_content = base64.b64encode(contents).decode("ascii") # returns base 64 encoded text

    # 4. Cria e adiciona o documento no banco
    new_doc = Pet_Document(
        pet_id=_pet.id,
        file_name=file_name,
        file_extension=file_ext,
        file_path=file_path,
        summary="",
    )
    db.add(new_doc)
    db.flush()

    new_job = Job(document_id=new_doc.id, status=JobStatus.ENQUEUED)
    db.add(new_job)
    db.commit()
    db.refresh(new_doc)
    db.refresh(new_job)

    # make callback to verify new data from worker
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
    # start the worker service
    request = Request(
        worker_url,
        data=_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    # 
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