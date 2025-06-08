import logging
from typing import List, Dict

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct, VectorParams
from app.config import settings
from app.services.llm_clients import get_embedding_vector

logger = logging.getLogger(__name__)

COLLECTION_NAME = "document_chunks"


def ensure_collection_exists() -> None:
    """
    Checks whether the Qdrant collection exists; if not, creates it with
    appropriate vector parameters (e.g., size=1536, distance="Cosine").
    """
    client = QdrantClient(url=settings.QDRANT_URL)

    existing = client.get_collections().collections
    if any(col.name == COLLECTION_NAME for col in existing):
        return

    vector_size = 1536

    logger.info(f"Creating Qdrant collection '{COLLECTION_NAME}' with vector size {vector_size}.")
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={"vectors": VectorParams(size=vector_size, distance="Cosine")},
    )


def index_chunks_in_vector_store(
    chunks: List[Dict],
    batch_size: int = 16
) -> None:
    """
    Given a list of chunk dictionaries (each with keys: "doc_id", "page_num",
    "paragraph_index", "chunk_text"), embed each chunk_text and upsert into Qdrant.

    Each point’s payload will include:
      - doc_id (str)
      - page_num (int)
      - paragraph_index (int)
      - chunk_text (str)

    Points are batched in sizes of `batch_size` for upsert efficiency.
    """
    if not chunks:
        logger.info("No chunks to index; skipping embedding_index.")
        return

    ensure_collection_exists()
    client = QdrantClient(url=settings.QDRANT_URL)

    all_point_ids: List[str] = []
    all_vectors: List[List[float]] = []
    all_payloads: List[Dict] = []

    for idx, chunk in enumerate(chunks):
        doc_id = chunk["doc_id"]
        page_num = chunk["page_num"]
        para_idx = chunk["paragraph_index"]
        text = chunk["chunk_text"]

        try:
            vector = get_embedding_vector(text)
        except Exception as e:
            logger.error(f"Embedding failed for doc={doc_id}, page={page_num}, para={para_idx}: {e}")
            continue

        point_id = f"{doc_id}_pg{page_num}_para{para_idx}"

        payload = {
            "doc_id": doc_id,
            "page_num": page_num,
            "paragraph_index": para_idx,
            "chunk_text": text,
        }

        all_point_ids.append(point_id)
        all_vectors.append(vector)
        all_payloads.append(payload)

        if len(all_point_ids) >= batch_size or idx == len(chunks) - 1:
            points = [
                PointStruct(id=pid, vector=vec, payload=pay)
                for pid, vec, pay in zip(all_point_ids, all_vectors, all_payloads)
            ]

            try:
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                logger.info(f"Upserted {len(points)} vectors into '{COLLECTION_NAME}'.")
            except Exception as e:
                logger.error(f"Failed to upsert batch to Qdrant: {e}")

            all_point_ids.clear()
            all_vectors.clear()
            all_payloads.clear()
