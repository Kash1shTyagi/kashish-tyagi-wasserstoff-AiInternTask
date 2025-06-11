import pytest
import numpy as np
from uuid import UUID
from app.services.embedding_index import (
    deterministic_uuid,
    ensure_collection_exists,
    index_chunks_in_vector_store,
    COLLECTION_NAME,
    VECTOR_DIMENSION
)
from app.services.llm_clients import get_embedding_vector

class DummyClient:
    def __init__(self, **kwargs):
        self._collections = []
        self.upserted = []

    def get_collections(self):
        return type("C", (), {"collections": self._collections})

    def create_collection(self, collection_name, vectors_config):
        self._collections.append(type("Col", (), {"name": collection_name}))

    def upsert(self, collection_name, points, wait):
        self.upserted.append((collection_name, points))

@pytest.fixture(autouse=True)
def patch_qdrant_and_embeddings(monkeypatch):
    dummy = DummyClient()
    monkeypatch.setattr("app.services.embedding_index.QdrantClient", lambda **kw: dummy)
    monkeypatch.setattr("app.services.llm_clients.get_embedding_vector", lambda text: [0.1]*VECTOR_DIMENSION)
    return dummy

def test_deterministic_uuid_consistency():
    u1 = deterministic_uuid("doc1", 2, 3)
    u2 = deterministic_uuid("doc1", 2, 3)
    assert u1 == u2
    assert isinstance(UUID(u1), UUID)

def test_ensure_collection_exists_creates_once(patch_qdrant_and_embeddings):
    client = patch_qdrant_and_embeddings
    ensure_collection_exists()
    assert any(col.name == COLLECTION_NAME for col in client._collections)
    before = len(client._collections)
    ensure_collection_exists()
    assert len(client._collections) == before

def test_index_chunks_batches_and_upserts(patch_qdrant_and_embeddings):
    dummy = patch_qdrant_and_embeddings
    chunks = []
    for i in range(20):
        chunks.append({
            "doc_id": "d",
            "page_num": 1,
            "paragraph_index": i,
            "chunk_text": f"text {i}"
        })
    index_chunks_in_vector_store(chunks, batch_size=7)
    assert len(dummy.upserted) >= 3
    for _, batch in dummy.upserted:
        for point in batch:
            assert point["payload"]["doc_id"] == "d"
            assert len(point["vector"]) == VECTOR_DIMENSION
