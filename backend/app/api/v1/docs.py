import os
import shutil
import logging
from typing import List
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.document_model import DocumentORM
from app.models.document import DocumentRead
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/",
    response_model=List[DocumentRead],
    summary="List all uploaded documents",
    description=(
        "Returns a list of all documents in the system. "
        "Supports optional filters: author, doc_type, date_from, date_to."
    ),
)
def list_documents(
    author: str = Query(None),
    doc_type: str = Query(None),
    date_from: str = Query(None), 
    date_to: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Optional filters:
      - author (string)
      - doc_type (e.g., "pdf", "image", "txt")
      - date_from (inclusive, ISO date)
      - date_to   (inclusive, ISO date)
    """
    query = db.query(DocumentORM)

    if author:
        query = query.filter(DocumentORM.author == author)
    if doc_type:
        query = query.filter(DocumentORM.doc_type == doc_type)
    if date_from:
        try:
            query = query.filter(DocumentORM.upload_date >= date_from)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date_from: {e}")
    if date_to:
        try:
            query = query.filter(DocumentORM.upload_date <= date_to)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date_to: {e}")

    docs = query.all()
    return docs


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document and its embeddings",
    description=(
        "Deletes the specified document from the database, removes its folder from disk, "
        "and deletes all its embeddings in Qdrant."
    ),
)
def delete_document(
    doc_id: str,
    db: Session = Depends(get_db),
):
    """
    1. Check if DocumentORM exists; 404 if not.
    2. Remove data/uploads/<doc_id> directory.
    3. Delete the row from documents table.
    4. Delete all points from Qdrant where payload.doc_id == doc_id.
    """
    doc = db.query(DocumentORM).filter(DocumentORM.doc_id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")

    data_dir = Path(os.getenv("DATA_DIR", "data/uploads"))
    doc_folder = data_dir / doc_id
    try:
        if doc_folder.exists() and doc_folder.is_dir():
            shutil.rmtree(doc_folder)
    except Exception as e:
        logger.error(f"Failed to remove folder {doc_folder}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete files for {doc_id}")

    try:
        db.delete(doc)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to delete DocumentORM row for {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Database deletion failed.")

    try:
        qdrant = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, prefer_grpc=False )
        points_selector = Filter(
            must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
        )
        qdrant.delete(
            collection_name="document_chunks",
            points_selector=points_selector,
            wait=True
        )
    except Exception as e:
        logger.error(f"Failed to delete embeddings for {doc_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete embeddings from vector store.")

    return {"detail": f"Document {doc_id} and its embeddings have been deleted."}