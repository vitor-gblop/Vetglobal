import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.main.connection.database import get_db
from src.main.models.job_model import Job
from src.main.models.pet_doc_model import Pet_Document

document_router = APIRouter(prefix="/documents", tags=["documents"])


def _get_document(doc_id: int, db: Session) -> Pet_Document:
    document = db.query(Pet_Document).filter_by(id=doc_id).first()
    if not document:
        raise HTTPException(
            detail=f"Document with id {doc_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return document


def _document_response(document: Pet_Document) -> dict:
    return {
        "document_id": document.id,
        "file_name": document.file_name,
        "file_extension": document.file_extension,
        "file_path": document.file_path,
        "summary": document.summary,
        "pet": document.pet,
        "created_at": document.created_at,
    }


@document_router.get("/{document_id}", status_code=status.HTTP_200_OK)
def retrieve_doc(document_id: int, db: Session = Depends(get_db)):
    return _document_response(_get_document(document_id, db))


@document_router.get("/{document_id}/poll", status_code=status.HTTP_200_OK)
async def poll_document(
    document_id: int,
    response: Response,
    after_job_id: int = 0,
    db: Session = Depends(get_db),
):
    """Wait up to 25 seconds for a newer job to reach a terminal state.

    A timeout returns 204 without a response body, so clients can retry with
    the same ``after_job_id``.
    """
    if after_job_id < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="after_job_id must be greater than or equal to zero",
        )

    _get_document(document_id, db)
    deadline = time.monotonic() + 25

    while True:
        db.expire_all()
        job = (
            db.query(Job)
            .filter(Job.document_id == document_id, Job.id > after_job_id)
            .order_by(Job.id.desc())
            .first()
        )
        if job and job.status.value in ("DONE", "FAILED"):
            if job.status.value == "DONE":
                return _document_response(job.document)
            return {
                "document_id": document_id,
                "job_id": job.id,
                "status": job.status,
                "error": job.error_message,
            }

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            response.status_code = status.HTTP_204_NO_CONTENT
            return response
        await asyncio.sleep(min(0.25, remaining))
