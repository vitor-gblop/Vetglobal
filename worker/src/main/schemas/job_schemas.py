from dataclasses import dataclass
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

# -- Job Schemas --
@dataclass(frozen=True)
class Job:
    job_id: int
    document_id: int
    content: str
    extension: str
    use_ai: bool
    callback_url: str | None
    
    
class JobStatus(str, Enum):
    ENQUEUED = "ENQUEUED"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    FAILED = "FAILED"


class JobCreate(BaseModel):
    job_id: Optional[int] = Field(default=None, ge=1)
    document_id: int = Field(..., ge=0)
    document_content: str = Field(..., min_length=10)
    document_extension: str = Field(default="txt", pattern=r"^(txt|pdf)$")
    use_ai: bool = False
    callback_url: Optional[str] = None


class JobResponse(BaseModel):
    job_id: int
    document_id: int
    status: JobStatus
    queue_size: int


class JobCompletion(BaseModel):
    """Payload sent by a worker when a job reaches a terminal state."""

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
