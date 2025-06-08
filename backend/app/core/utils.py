import os
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile
from typing import Optional


def generate_doc_id(prefix: str = "doc") -> str:
    """
    Generate a short, unique document ID.
    Example: "doc_ab12cd34" (eight-hex-digit suffix)
    """
    suffix = uuid.uuid4().hex[:8]
    return f"{prefix}_{suffix}"


def ensure_directory(path: str) -> None:
    """
    Ensure that the directory at 'path' exists. If not, create it (with parents).
    """
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not create directory {path}: {e}")


def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    """
    Save a FastAPI UploadFile to the given destination path on disk.
    Raises HTTPException(500) on failure.
    """
    try:
        parent_dir = os.path.dirname(destination)
        ensure_directory(parent_dir)

        with open(destination, "wb") as buffer:
            content = upload_file.file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file {upload_file.filename}: {e}")
    finally:
        upload_file.file.close()


def allowed_file_extension(filename: str) -> bool:
    """
    Check if the file extension is among a whitelist:
      - .pdf, .png, .jpg, .jpeg, .txt
    """
    allowed_exts = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}
    ext = Path(filename).suffix.lower()
    return ext in allowed_exts


def get_file_extension(filename: str) -> str:
    """
    Return the lowercase extension of the filename, including the dot.
    Example: "report.PDF" --> ".pdf"
    """
    return Path(filename).suffix.lower()


def build_document_directory(data_dir: str, doc_id: str) -> str:
    """
    Given the root data directory and a doc_id, return the path
    to that document’s folder, ensuring it exists.
    Example: data_dir="data/uploads", doc_id="doc_ab12", returns "data/uploads/doc_ab12"
    """
    doc_dir = os.path.join(data_dir, doc_id)
    ensure_directory(doc_dir)
    return doc_dir


def validate_filename(filename: str) -> None:
    """
    Basic validation: ensure no path traversal (e.g., "..") and filename is not empty.
    Raises HTTPException(400) if invalid.
    """
    if not filename or ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail=f"Invalid filename: {filename}")
