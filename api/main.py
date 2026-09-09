from src.main.server import app as App
import uvicorn

app = App

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True
	)
