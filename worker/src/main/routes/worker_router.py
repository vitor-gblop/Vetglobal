from fastapi import APIRouter, Request, status

from src.main.schemas.job_schemas import JobCreate, JobResponse, JobStatus
from src.main.workers.queue import JobQueue

worker_router = APIRouter(prefix="/worker", tags=["worker"])


@worker_router.post("/start", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_job(body: JobCreate, request: Request) -> JobResponse:
    queue: JobQueue = request.app.state.job_queue
    job_id = await queue.enqueue(
        job_id=body.job_id,
        document_id=body.document_id,
        content=body.document_content,
        extension=body.document_extension,
        use_ai=body.use_ai,
        callback_url=body.callback_url,
    )
    return JobResponse(
        job_id=job_id,
        document_id=body.document_id,
        status=JobStatus.ENQUEUED,
        queue_size=queue.size,
    )
