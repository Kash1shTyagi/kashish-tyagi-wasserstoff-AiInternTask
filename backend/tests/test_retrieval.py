import pytest
from app.services.retrieval import retrieve_top_k_chunks

class DummyHit:
    def __init__(self, payload):
        self.payload = payload

class DummyQdrant:
    def __init__(self, **kwargs):
        pass

    def search(self, *, collection_name, query_vector, limit, with_payload, with_vectors, query_filter):
        return [
            DummyHit({"doc_id": "docX", "chunk_text": "A", "page_num": 1, "paragraph_index": 1}),
            DummyHit({"doc_id": "docX", "chunk_text": "B", "page_num": 1, "paragraph_index": 2}),
        ]

@pytest.fixture(autouse=True)
def patch_qdrant(monkeypatch):
    monkeypatch.setattr("app.services.retrieval.QdrantClient", lambda **kw: DummyQdrant())
    monkeypatch.setattr("app.services.retrieval.qdrant_client", DummyQdrant())
    yield

def test_retrieve_top_k_chunks_basic():
    chunks = retrieve_top_k_chunks("question?", doc_id="docX", top_k=2)
    assert isinstance(chunks, list)
    assert len(chunks) == 2
    for c in chunks:
        assert set(c.keys()) == {"doc_id", "chunk_text", "page_num", "paragraph_index"}

def test_retrieve_empty_on_error(monkeypatch):
    monkeypatch.setattr(
        "app.services.retrieval.get_query_embedding",
        lambda text: (_ for _ in ()).throw(RuntimeError("fail"))
    )

    chunks = retrieve_top_k_chunks("q", doc_id="docX")
    assert chunks == []
