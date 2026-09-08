from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship
from src.main.connection.database import Base
from src.main.schemas.job_schemas import JobStatus

# Model
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("pet_documents.id"), nullable=False)
    status = Column(Enum(JobStatus), nullable=False)
    error_message = Column(Text, nullable=True)
    #
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    

    document = relationship("Pet_Document", back_populates="jobs")