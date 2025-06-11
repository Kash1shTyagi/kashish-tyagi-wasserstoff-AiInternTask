import logging
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

from app.config import settings
from app.services.llm_clients import get_embedding_vector, get_query_embedding

logger = logging.getLogger(__name__)

COLLECTION_NAME = "document_chunks"

qdrant_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY, prefer_grpc=False)


def retrieve_top_k_chunks(
    question: str,
    doc_id: str,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Given a natural-language question and a specific document ID, this function:
      1. Computes the query embedding vector for the question.
      2. Queries Qdrant to retrieve the top K most similar chunks, filtering by doc_id.
      3. Returns a list of chunk dicts containing:
            - doc_id
            - chunk_text
            - page_num 
            - paragraph_index

    If any step fails, logs the error and returns an empty list.
    """
    try:
        query_embedding = get_query_embedding(question)
    except Exception as e:
        logger.error(f"Failed to compute embedding for question '{question}': {e}")
        return []

    if isinstance(query_embedding, list) and len(query_embedding) == 1 and isinstance(query_embedding[0], list):
        query_embedding = query_embedding[0]
    query_embedding = [float(x) for x in query_embedding]

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
        chunk_doc_id = payload.get("doc_id", "") or doc_id
        chunks.append({
            "doc_id": chunk_doc_id, 
            "chunk_text": text,
            "page_num": page_num,
            "paragraph_index": para_idx
        })

    logger.info(f"Retrieved {len(chunks)} chunks for doc_id={doc_id} (top_k={top_k}).")
    return chunks 