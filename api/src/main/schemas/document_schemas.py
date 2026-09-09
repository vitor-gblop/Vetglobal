from enum import Enum

from pydantic import BaseModel, Field
# schemas
from src.main.schemas.job_schemas import JobStatus

# -- Doc Schemas --

class DocumentTypes(str, Enum):
    UNIQUE = "UNIQUE"
    MULTIPLE = "MULTIPLE"


class DocumentPayload(BaseModel):
    document_type: DocumentTypes = Field(..., example=DocumentTypes.UNIQUE)
    
    
class DocumentResponse(BaseModel):
    id: int
    document_id: int
    job_id: int
    status: JobStatus