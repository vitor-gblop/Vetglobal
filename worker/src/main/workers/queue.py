import asyncio
import logging
# schemas
from src.main.schemas.job_schemas import Job
# workers
from src.main.workers.worker import Worker


logger = logging.getLogger(__name__)

class JobQueue:
    """FIFO in-memory queue with exactly one processing consumer."""

    def __init__(self, worker_factory=None) -> None:
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._worker_factory = worker_factory or Worker
        self._consumer: asyncio.Task[None] | None = None
        self._next_job_id = 1


    @property
    def size(self) -> int:
        return self._queue.qsize()


    async def enqueue(
        self,
        job_id: int | None,
        document_id: int,
        content: str,
        extension: str,
        use_ai: bool,
        callback_url: str | None,
    ) -> int:
        queued_job_id = job_id
        if queued_job_id is None:
            queued_job_id = self._next_job_id
            self._next_job_id += 1
        else:
            self._next_job_id = max(self._next_job_id, queued_job_id + 1)
        await self._queue.put(
            Job(queued_job_id, document_id, content, extension, use_ai, callback_url)
        )
        return queued_job_id


    async def start(self) -> None:
        if self._consumer is None or self._consumer.done():
            self._consumer = asyncio.create_task(self._consume())


    async def stop(self) -> None:
        if self._consumer is None:
            return
        await self._queue.join()
        self._consumer.cancel()
        await asyncio.gather(self._consumer, return_exceptions=True)
        self._consumer = None


    async def _consume(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                worker = self._worker_factory(
                    callback=_CallbackSender(job.callback_url),
                )
                await worker.start(
                    job.content,
                    job.job_id,
                    job.document_id,
                    job.extension,
                    job.use_ai,
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Job %s failed", job.job_id)
            finally:
                self._queue.task_done()


class _CallbackSender:
    def __init__(self, callback_url: str | None) -> None:
        self._callback_url = callback_url

    async def __call__(self, payload: dict[str, object]) -> None:
        if self._callback_url is None:
            logger.warning("Job %s has no callback URL", payload["job_id"])
            return

        import asyncio
        import json
        from urllib.request import Request, urlopen

        body = json.dumps(payload).encode("utf-8")
        
        # callback requisition
        def send() -> None:
            request = Request(
                self._callback_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(request, timeout=10) as response:
                if response.status >= 400:
                    raise RuntimeError(
                        f"Callback returned HTTP {response.status}"
                    )

        await asyncio.to_thread(send)


# Keep the short name available for callers that already imported Queue.
Queue = JobQueue