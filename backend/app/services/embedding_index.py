import logging
import uuid
import hashlib
from typing import List, Dict

from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams

from app.config import settings
from app.services.llm_clients import get_embedding_vector

logger = logging.getLogger(__name__)

COLLECTION_NAME = "document_chunks"
VECTOR_DIMENSION = 768

def deterministic_uuid(doc_id: str, page_num: int, para_idx: int) -> str:
    """
    Generate a deterministic UUID for each chunk based on its doc_id, page number, and paragraph index.
    """
    key = f"{doc_id}_pg{page_num}_para{para_idx}"
    md5_hash = hashlib.md5(key.encode("utf-8")).hexdigest()
    return str(uuid.UUID(md5_hash))

def ensure_collection_exists() -> None:
    """
    Deletes any existing collection named COLLECTION_NAME, then creates a new one
    using single-vector mode with the vector field "vector" (dimension = VECTOR_DIMENSION).
    """
    client = QdrantClient(url=settings.QDRANT_URL)
    existing = client.get_collections().collections
    if not any(col.name == COLLECTION_NAME for col in existing):
        logger.info(f"Creating Qdrant collection '{COLLECTION_NAME}' with vector field 'vector' and size {VECTOR_DIMENSION}.")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIMENSION, distance="Cosine"),
        )
    else:
        logger.info(f"Collection '{COLLECTION_NAME}' already exists. Skipping deletion/recreation.")

def index_chunks_in_vector_store(chunks: List[Dict], batch_size: int = 16) -> None:
    """
    For each chunk (with keys: 'doc_id', 'page_num', 'paragraph_index', 'chunk_text'),
    generate an embedding using Gemini LLM, print its structure and types, validate its length,
    and upsert the chunk into Qdrant.
    """
    if not chunks:
        logger.info("No chunks provided for indexing. Skipping upsert.")
        return

    ensure_collection_exists()
    client = QdrantClient(url=settings.QDRANT_URL)
    buffer_points: List[Dict] = []

    for idx, chunk in enumerate(chunks):
        doc_id = chunk["doc_id"]
        page_num = chunk["page_num"]
        para_idx = chunk["paragraph_index"]
        text = chunk["chunk_text"]

        try:
            vector = get_embedding_vector(text)
            if isinstance(vector, list) and len(vector) == 1 and isinstance(vector[0], list):
                vector = vector[0]
            vector = [float(x) for x in vector]
        except Exception as e:
            logger.error(f"Embedding failed for doc_id {doc_id}, page {page_num}, para {para_idx}: {e}")
            continue

        if len(vector) != VECTOR_DIMENSION:
            logger.error(f"Embedding dimension mismatch: expected {VECTOR_DIMENSION}, got {len(vector)} "
                         f"for doc_id {doc_id}, page {page_num}, para {para_idx}")
            continue

        point_id = deterministic_uuid(doc_id, page_num, para_idx)
        point_dict = {
            "id": point_id,
            "vector": vector,
            "payload": {
                "doc_id": doc_id,
                "page_num": page_num,
                "paragraph_index": para_idx,
                "chunk_text": text,
            },
        }
        buffer_points.append(point_dict)

        if len(buffer_points) >= batch_size or idx == len(chunks) - 1:
            try:
                client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=buffer_points,
                    wait=True
                )
                logger.info(f"Upserted {len(buffer_points)} points into collection '{COLLECTION_NAME}'.")
            except Exception as e:
                logger.error(f"Failed to upsert batch to Qdrant: {e}")
            buffer_points.clear()
