from pydantic import BaseModel
# schemas
from src.main.schemas.job_schemas import JobStatus

# -- Doc Schemas --

class DocumentResponse(BaseModel):
    id: int
    document_id: int
    job_id: int
    status: JobStatus