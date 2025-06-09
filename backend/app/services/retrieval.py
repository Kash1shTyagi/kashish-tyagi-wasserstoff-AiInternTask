import logging
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from app.config import settings
from app.services.llm_clients import get_embedding_vector

logger = logging.getLogger(__name__)

COLLECTION_NAME = "document_chunks"

qdrant_client = QdrantClient(url=settings.QDRANT_URL)


def retrieve_top_k_chunks(
    question: str,
    doc_id: str,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Given a natural-language question and a specific document ID, this function:
      1. Computes the embedding vector for the question.
      2. Queries Qdrant to retrieve the top K most similar chunks for that doc_id.
      3. Returns a list of chunk dicts:
         [
           {
             "chunk_text": <str>,
             "page_num": <int>,
             "paragraph_index": <int>
           },
           ...
         ]

    If any step fails, logs the error and returns an empty list.

    :param question: The user’s question to embed and search.
    :param doc_id:   The document identifier to filter chunks by.
    :param top_k:    Number of top chunks to retrieve (default: 3).
    :return:         List of dicts containing chunk_text, page_num, paragraph_index.
    """
    try:
        query_embedding = get_embedding_vector(question)
    except Exception as e:
        logger.error(f"Failed to compute embedding for question '{question}': {e}")
        return []

    search_filter = Filter(
        must=[
            FieldCondition(
                key="doc_id",
                match=MatchValue(value=doc_id)
            )
        ]
    )

    try:
        search_result = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=top_k,
            with_payload=True,    
            with_vectors=False,
            query_filter=search_filter
        )
    except Exception as e:
        logger.error(f"Qdrant search failed for doc_id={doc_id}: {e}")
        return []

    chunks: List[Dict[str, Any]] = []
    for hit in search_result:
        payload = hit.payload or {}
        text = payload.get("chunk_text", "")
        page_num = payload.get("page_num", 0)
        para_idx = payload.get("paragraph_index", 0)
        chunks.append({
            "chunk_text": text,
            "page_num": page_num,
            "paragraph_index": para_idx
        })

    logger.info(f"Retrieved {len(chunks)} chunks for doc_id={doc_id} (top_k={top_k}).")
    return chunks
