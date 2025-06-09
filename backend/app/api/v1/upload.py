import os
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.utils import (
    generate_doc_id,
    build_document_directory,
    save_upload_file,
    allowed_file_extension,
    validate_filename,
)
from app.db.session import get_db
from app.db.document_model import DocumentORM
from app.services.ingestion import extract_and_chunk_document
from app.services.embedding_index import index_chunks_in_vector_store

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Upload one or more documents",
    description=(
        "Accepts multiple files (.pdf, .png, .jpg, .jpeg, .txt). "
        "For each file:\n"
        "1. Validates extension\n"
        "2. Generates a unique `doc_id`\n"
        "3. Saves it under DATA_DIR/<doc_id>/<filename>\n"
        "4. Inserts a row into the `documents` table\n"
        "5. Extracts and chunks text (including OCR)\n"
        "6. Indexes each chunk’s embedding into Qdrant\n"
        "Returns a JSON array of upload results."
    ),
)
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    1. Ensure DATA_DIR exists.
    2. For each uploaded file:
       - Validate filename and extension
       - Generate doc_id
       - Save the file to disk
       - Create a DocumentORM row
       - Extract & chunk via ingestion.extract_and_chunk_document
       - Index embeddings via embedding_index.index_chunks_in_vector_store
    3. Return a JSON array of per‐file statuses.
    """
    data_dir = Path(os.getenv("DATA_DIR", "data/uploads"))
    data_dir.mkdir(parents=True, exist_ok=True)

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided for upload.",
        )

    results = []

    for upload_file in files:
        filename = upload_file.filename
        validate_filename(filename)
        if not allowed_file_extension(filename):
            detail = f"Unsupported file extension: {filename}"
            logger.warning(detail)
            results.append({"filename": filename, "status": "skipped", "detail": detail})
            continue

        doc_id = generate_doc_id()

        doc_folder = build_document_directory(str(data_dir), doc_id)
        dest_path = Path(doc_folder) / filename

        try:
            save_upload_file(upload_file, str(dest_path))
        except HTTPException as e:
            detail = f"Failed to save file {filename}: {e.detail}"
            logger.error(detail)
            results.append({"filename": filename, "status": "error", "detail": detail})
            continue

        try:
            new_doc = DocumentORM(
                doc_id=doc_id,
                filename=filename,
                doc_type=Path(filename).suffix.lower().lstrip("."),
                author=None,
                doc_date=None,
            )
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)
        except Exception as e:
            detail = f"Database error inserting document {doc_id}: {e}"
            logger.error(detail)
            results.append({"doc_id": doc_id, "filename": filename, "status": "error", "detail": detail})
            try:
                dest_path.unlink()
                Path(dest_path.parent).rmdir()
            except:
                pass
            continue

        try:
            chunks = extract_and_chunk_document(doc_id, dest_path)
        except Exception as e:
            detail = f"Extraction error for {doc_id}: {e}"
            logger.error(detail)
            results.append({"doc_id": doc_id, "filename": filename, "status": "error", "detail": detail})
            db.delete(new_doc)
            db.commit()
            try:
                dest_path.unlink()
                Path(dest_path.parent).rmdir()
            except:
                pass
            continue

        try:
            index_chunks_in_vector_store(chunks)
            status_str = "indexed"
            detail = f"{len(chunks)} chunks indexed."
        except Exception as e:
            detail = f"Indexing error for {doc_id}: {e}"
            logger.error(detail)
            status_str = "error"

        results.append({
            "doc_id": doc_id,
            "filename": filename,
            "status": status_str,
            "detail": detail,
        })

    return {"upload_results": results}
