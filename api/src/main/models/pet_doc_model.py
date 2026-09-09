from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from src.main.schemas.document_schemas import DocumentTypes
from src.main.connection.database import Base


class Pet_Document(Base):
    __tablename__ = "pet_documents"

    id = Column(Integer, primary_key = True, index = True)
    pet_id = Column(
        Integer,
        ForeignKey("pets.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_name = Column(String, nullable = False)
    file_extension = Column(String, nullable = False)
    file_path = Column(String, nullable = False)
    doc_type = Column(Enum(DocumentTypes), nullable=False)
    summary = Column(String, nullable = True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    pet = relationship("Pet", back_populates="documents")
    jobs = relationship(
        "Job",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )