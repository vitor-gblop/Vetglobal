import asyncio
import logging
from collections.abc import Awaitable, Callable

from src.main.utils.file_utils import extract_document_text, extract_formatted_data
from src.AI.AIConnection import summarize_text
from src.main.schemas.job_schemas import JobStatus

logger = logging.getLogger(__name__)


class Worker:
    def __init__(
        self,
        callback: Callable[[dict[str, object]], Awaitable[None]] | None = None,
    ) -> None:
        self._callback = callback

    async def start(
        self,
        content: str,
        job_id: int,
        document_id: int | None = None,
        extension: str = "txt",
        use_ai: bool = False,
    ) -> str:
        """Read and summarize one document, then notify the API."""
        try:
            await asyncio.sleep(5)  # Simulate a long-running task
            text = extract_document_text(content, extension)
            
            if use_ai:
                summary = summarize_text(text)
            else: 
                summary = extract_formatted_data(text)
                
        except Exception as exc:
            logger.exception("Job %s failed while summarizing", job_id)
            await self._notify(
                {
                    "job_id": job_id,
                    "document_id": document_id,
                    "status": JobStatus.FAILED.value,
                    "error": str(exc),
                }
            )
            raise

        await self._notify(
            {
                "job_id": job_id,
                "document_id": document_id,
                "status": JobStatus.DONE.value,
                "summary": summary,
            }
        )
        return summary

    async def _notify(self, payload: dict[str, object]) -> None:
        if self._callback is not None:
            await self._callback(payload)

 