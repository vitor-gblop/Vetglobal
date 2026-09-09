from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator

# -- Schemas de Jobs --

class JobStatus(str, Enum):
    ENQUEUED = "ENQUEUED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class JobCreate(BaseModel):
    document_id: int = Field(...)
    status: JobStatus = Field(..., )
    created_at: str = Field(..., )
    updated_at: str = Field(..., )
    
class JobInternResponse(BaseModel): 
    job_id: int
    status: str
    summary: str | None
    error: str | None
    


class JobCompletion(BaseModel):
    """Payload enviado por um worker quando um job alcança um estado terminal."""

    status: JobStatus
    summary: Optional[str] = None
    error: Optional[str] = None

    @model_validator(mode="after")
    def validate_result(self) -> "JobCompletion":
        if self.status not in (JobStatus.DONE, JobStatus.FAILED):
            raise ValueError("callback status must be DONE or FAILED")
        if self.status == JobStatus.DONE and not self.summary:
            raise ValueError("summary is required when status is DONE")
        if self.status == JobStatus.FAILED and not self.error:
            raise ValueError("error is required when status is FAILED")
        return self
