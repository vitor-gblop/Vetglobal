from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.main.routes.worker_router import worker_router
from src.main.workers.queue import JobQueue


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.job_queue = JobQueue()
    await app.state.job_queue.start()
    try:
        yield
    finally:
        await app.state.job_queue.stop()


app = FastAPI(title="workers", version="1.0.0", lifespan=lifespan)

# Routers
app.include_router(worker_router)

@app.get("/")
def api_home() -> dict[str, str]:
    return {"message": "Worker Queue Running"}