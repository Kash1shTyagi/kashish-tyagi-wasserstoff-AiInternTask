import logging
from pathlib import Path
from typing import List, Dict

import pdfplumber
from PIL import Image
import pytesseract

from fastapi import HTTPException

from app.config import settings
from app.core.utils import ensure_directory, allowed_file_extension

logger = logging.getLogger(__name__)

MAX_WORDS_PER_CHUNK = 300    
WORD_OVERLAP = 50            


def ocr_image_file(image_path: Path) -> str:
    """
    Perform OCR on a single image file using Tesseract.
    Returns the extracted text.
    """
    try:
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as e:
        logger.error(f"OCR failed for image {image_path}: {e}")
        return ""


def extract_text_from_pdf(pdf_path: Path) -> List[str]:
    """
    Extract text from each page of a PDF by:
      1) Using pdfplumber.page.extract_text() for “native” text
      2) Rendering the page as an image (at 300 DPI) and running OCR
    Returns a list where each element is the combined text of that page.
    """
    page_texts: List[str] = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                native_text = page.extract_text() or ""
                native_text = native_text.strip()

                try:
                    page_image = page.to_image(resolution=300).original
                    temp_img_path = pdf_path.with_name(f"{pdf_path.stem}_page{page_number}.png")
                    page_image.save(temp_img_path, format="PNG")
                    ocr_text = ocr_image_file(temp_img_path)
                finally:
                    if temp_img_path.exists():
                        temp_img_path.unlink()

                combined = ""
                if native_text and ocr_text:
                    if native_text in ocr_text:
                        combined = ocr_text
                    elif ocr_text in native_text:
                        combined = native_text
                    else:
                        combined = native_text + "\n" + ocr_text
                elif native_text:
                    combined = native_text
                elif ocr_text:
                    combined = ocr_text
                else:
                    combined = ""

                page_texts.append(combined)
    except Exception as e:
        logger.error(f"Failed to extract/ocr PDF {pdf_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"PDF extraction error for {pdf_path.name}: {e}"
        )

    return page_texts


def extract_text_from_txt(txt_path: Path) -> List[str]:
    """
    Read a plain-text file and return its content as a single “page”.
    """
    try:
        content = txt_path.read_text(encoding="utf-8", errors="ignore")
        return [content]
    except Exception as e:
        logger.error(f"Failed to read text file {txt_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Text file read error for {txt_path.name}: {e}"
        )


def chunk_text_into_paragraphs(text: str) -> List[str]:
    """
    Split a block of text into overlapping chunks of ~MAX_WORDS_PER_CHUNK, with WORD_OVERLAP.
    """
    words = text.split()
    if not words:
        return []

    if len(words) <= MAX_WORDS_PER_CHUNK:
        return [" ".join(words)]

    chunks: List[str] = []
    start = 0
    total_words = len(words)

    while start < total_words:
        end = min(start + MAX_WORDS_PER_CHUNK, total_words)
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end == total_words:
            break
        start = end - WORD_OVERLAP

    return chunks


def extract_and_chunk_document(
    doc_id: str,
    file_path: Path
) -> List[Dict]:
    """
    For a given uploaded file (PDF, image, or text), extract page-wise text (including OCR)
    and then split each page into overlapping chunks.

    Returns a list of dicts:
      {
        "doc_id": "<doc_id>",
        "page_num": <int>,
        "paragraph_index": <int>,
        "chunk_text": "<string>"
      }
    """
    ext = file_path.suffix.lower()
    if not allowed_file_extension(file_path.name):
        logger.warning(f"Skipping unsupported file type: {file_path.name}")
        return []

    page_texts: List[str] = []
    if ext == ".pdf":
        page_texts = extract_text_from_pdf(file_path)
    elif ext in {".png", ".jpg", ".jpeg"}:
        ocr_text = ocr_image_file(file_path)
        page_texts = [ocr_text]
    elif ext == ".txt":
        page_texts = extract_text_from_txt(file_path)
    else:
        logger.warning(f"Unexpected extension {ext} for file {file_path.name}. Skipping.")
        return []

    chunks_output: List[Dict] = []
    for page_index, page_text in enumerate(page_texts, start=1):
        if not page_text.strip():
            continue

        paragraph_chunks = chunk_text_into_paragraphs(page_text)
        for para_idx, chunk in enumerate(paragraph_chunks, start=1):
            chunks_output.append({
                "doc_id": doc_id,
                "page_num": page_index,
                "paragraph_index": para_idx,
                "chunk_text": chunk
            })

    logger.info(f"Document {doc_id}: extracted and chunked into {len(chunks_output)} chunks.")
    return chunks_output
