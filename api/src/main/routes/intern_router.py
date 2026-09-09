from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.main.connection.database import get_db
from src.main.models.job_model import Job
from src.main.schemas.job_schemas import JobCompletion, JobInternResponse, JobStatus

intern_router = APIRouter(prefix="/internal", tags=["internal"])

@intern_router.post("/jobs/{job_id}/complete", status_code=status.HTTP_200_OK)
def worker_callback(
    job_id: int,
    payload: JobCompletion,
    db: Session = Depends(get_db),
) -> JobInternResponse:
    job = db.query(Job).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with id {job_id} not found",
        )

    # Uma nova tentativa de callback não deve sobrescrever um resultado já concluído.
    if job.status not in (JobStatus.DONE, JobStatus.FAILED):
        job.status = payload.status
        if payload.status == JobStatus.DONE:
            job.document.summary = payload.summary
            job.error_message = None
        else:
            job.error_message = payload.error
        db.commit()
        db.refresh(job)

    return JobInternResponse(
        job_id=job.id,
        status=job.status,
        summary=job.document.summary if job.status == JobStatus.DONE else None,
        error=job.error_message if job.status == JobStatus.FAILED else None,
    )