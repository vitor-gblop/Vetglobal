from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship
from src.main.connection.database import Base


class Pet(Base):
    __tablename__ = "pets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    owner_name = Column(String, nullable=False)
    species = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    documents = relationship(
        "Pet_Document",
        back_populates="pet",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )