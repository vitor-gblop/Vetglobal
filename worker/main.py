import os

from dotenv import load_dotenv
from src.main.server import app as App
import uvicorn

from src.main.workers.worker import Worker

app = App
load_dotenv()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("WORKER_HOST", "127.0.0.1"),
        port=int(os.getenv("WORKER_PORT", "8001")),
        reload=os.getenv("WORKER_RELOAD", "false").lower() == "true",
	)