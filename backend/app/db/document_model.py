import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    func,
)
from app.db.base import Base


class DocumentORM(Base):
    """
    ORM model for the 'documents' table.
    Stores metadata for each uploaded document.
    """
    __tablename__ = "documents"

    id: int = Column(Integer, primary_key=True, index=True)
    doc_id: str = Column(String, unique=True, index=True, nullable=False) 
    filename: str = Column(String, nullable=False)  

    upload_date: datetime.datetime = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    doc_type: str = Column(String, nullable=False)  
    author: str | None = Column(String, nullable=True)  
    doc_date: datetime.datetime | None = Column(DateTime(timezone=True), nullable=True) 

    def __repr__(self) -> str:
        return f"<DocumentORM(doc_id={self.doc_id!r}, filename={self.filename!r})>"
