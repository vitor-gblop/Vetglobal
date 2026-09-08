from src.main.server import app as App
import uvicorn

from src.main.workers.worker import Worker

app = App

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True
	)

if __name__ == "__main__":
    import asyncio

    current_job = Worker()
    asyncio.run(current_job.start("simulação"))
