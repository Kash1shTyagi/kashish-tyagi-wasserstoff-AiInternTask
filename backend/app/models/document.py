from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class DocumentORM(Base):
    """
    SQLAlchemy model for storing uploaded document metadata.
    Table: documents
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, unique=True, index=True, nullable=False)   
    filename = Column(String, nullable=False)                            
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    doc_type = Column(String, nullable=False)                          
    author = Column(String, nullable=True)                              
    doc_date = Column(DateTime(timezone=True), nullable=True)            

    # chunks = relationship("ChunkORM", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DocumentORM(doc_id={self.doc_id}, filename={self.filename})>"


class DocumentBase(BaseModel):
    """
    Shared fields for creating or reading a document.
    """
    doc_id: str
    filename: str
    doc_type: str
    author: Optional[str]
    doc_date: Optional[datetime]


class DocumentCreate(DocumentBase):
    """
    Fields required when creating a new document. 
    """
    pass


class DocumentRead(DocumentBase):
    """
    Fields returned when reading a document from the database.
    Includes upload_date (server-generated).
    """
    upload_date: datetime

    class Config:
        orm_mode = True
