import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def patch_ingestion_and_index(monkeypatch):
    """
    Stub out both:
      - the service implementation (app.services.ingestion.extract_and_chunk_document)
      - the symbol imported into the upload endpoint (app.api.v1.upload.extract_and_chunk_document)
    And similarly for the indexer.
    """
    dummy_chunks = [
        {"doc_id": "doc_dummy", "page_num": 1, "paragraph_index": 1, "chunk_text": "hello world"}
    ]

    monkeypatch.setattr(
        "app.services.ingestion.extract_and_chunk_document",
        lambda doc_id, path: dummy_chunks
    )
    monkeypatch.setattr(
        "app.api.v1.upload.extract_and_chunk_document",
        lambda doc_id, path: dummy_chunks
    )

    monkeypatch.setattr(
        "app.services.embedding_index.index_chunks_in_vector_store",
        lambda chunks: None
    )
    monkeypatch.setattr(
        "app.api.v1.upload.index_chunks_in_vector_store",
        lambda chunks: None
    )

@pytest.mark.parametrize("ext,mime", [
    (".txt", "text/plain"),
    (".pdf", "application/pdf"),
    (".png", "image/png"),
])
def test_upload_basic_file(tmp_path: Path, ext: str, mime: str):
    file_path = tmp_path / f"sample{ext}"
    file_path.write_bytes(b"Dummy content")

    with open(file_path, "rb") as f:
        response = client.post(
            "/api/v1/upload/",
            files=[("files", (file_path.name, f, mime))]
        )

    assert response.status_code == 201, response.text
    results = response.json()["upload_results"]
    assert isinstance(results, list) and len(results) == 1

    data = results[0]
    assert data["status"] == "indexed"
    assert "doc_id" in data

def test_upload_no_files():
    response = client.post("/api/v1/upload/", files=[])
    assert response.status_code == 422
    body = response.json()
    assert any(err["loc"][-1] == "files" for err in body["detail"])
