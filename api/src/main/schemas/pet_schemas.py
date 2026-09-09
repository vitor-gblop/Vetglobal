from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

# -- Pets Schemas --

class PetCreate(BaseModel):
    # 
    name: str = Field(..., min_length=1, example="Hank")
    owner_name: str = Field(..., min_length=1, example="John Bergeson")
    species: str = Field(..., min_length=1, example="Corgi")
    age: int = Field(..., ge=0, example=5)


class PetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    owner_name: str | None = Field(default=None, min_length=1)


class PetResponse(PetCreate):
    # 
    id: int
    name: str
    owner_name: str
    species: str
    age: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)