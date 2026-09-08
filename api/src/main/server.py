from fastapi import FastAPI
# Routes
from src.main.routes.pet_router import pet_router
from src.main.routes.documents_router import document_router 
from src.main.routes.intern_router import intern_router
from src.main.models.job_model import Job
# database
from src.main.connection.database import Base, engine

Base.metadata.drop_all(bind=engine)  # drop all tables if they exist
Base.metadata.create_all(bind=engine) # create tables 

app = FastAPI(title="vetglobal", version="1.0.0")

# Routers
app.include_router(pet_router)
app.include_router(document_router)
app.include_router(intern_router)

@app.get("/")
def api_home() -> dict[str, str]:
	return {"message": "VetGlobal API funcionando"}