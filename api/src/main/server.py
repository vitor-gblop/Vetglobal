from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# Rotas
from src.main.routes.pet_router import pet_router
from src.main.routes.documents_router import document_router 
from src.main.routes.intern_router import intern_router
from src.main.models.job_model import Job
# banco de dados
from src.main.connection.database import Base, engine

Base.metadata.drop_all(bind=engine)  # remove todas as tabelas, se existirem
Base.metadata.create_all(bind=engine)  # cria as tabelas

app = FastAPI(title="vetglobal", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(pet_router)
app.include_router(document_router)
app.include_router(intern_router)

@app.get("/")
def api_home() -> dict[str, str]:
	return {"message": "VetGlobal API funcionando"}