import pytest
from typing import Dict, List, Any

from app.services.theme_identification import cluster_snippets, identify_and_summarize_themes

@pytest.fixture(autouse=True)
def patch_embeddings_and_generation(monkeypatch):
    monkeypatch.setattr(
        "app.services.theme_identification.get_embedding_vector",
        lambda text: [float(len(text)), float(len(text))],
    )
    async def fake_generate(snippets: List[Dict[str, Any]], theme_id: int, question: str):
        return {
            "theme_name": f"Theme {theme_id}",
            "summary": f"Synthesized for {theme_id}",
            "citations": [s["citation"] for s in snippets],
        }
    monkeypatch.setattr("app.services.theme_identification.generate_theme_summary", fake_generate)

def make_snippet(text: str, citation: str) -> Dict[str, Any]:
    return {"doc_id": "d", "text": text, "citation": citation}

def test_cluster_snippets_forced_single_cluster():
    """
    If we explicitly request 1 cluster, all snippets should go into cluster 0.
    """
    snippets = [make_snippet("short", "c1"), make_snippet("another", "c2")]
    clusters = cluster_snippets(snippets, n_clusters=1)
    assert list(clusters.keys()) == [0]
    assert set(clusters[0]) == {0, 1}

def test_cluster_snippets_two_clusters_default():
    """
    If we request more clusters than snippets, k becomes len(snippets),
    so with 2 snippets we get 2 clusters, each with one member.
    """
    snippets = [make_snippet("short", "c1"), make_snippet("another", "c2")]
    clusters = cluster_snippets(snippets, n_clusters=3)
    assert set(clusters.keys()) == {0, 1}
    all_indices = set(idx for members in clusters.values() for idx in members)
    assert all_indices == {0, 1}

@pytest.mark.anyio
async def test_identify_and_summarize_themes_multiple():
    """
    Integration test for identify_and_summarize_themes:
    - with 6 snippets, heuristic n_clusters = min(max(1,6//3),4)=2
    """
    snippets = [make_snippet(f"text{i}", f"c{i}") for i in range(6)]
    themes = await identify_and_summarize_themes(snippets, question="Q?")
    assert isinstance(themes, list)
    assert 1 <= len(themes) <= 2
    for idx, theme in enumerate(themes, start=1):
        assert theme["theme_name"] == f"Theme {idx}"
        assert "Synthesized for" in theme["summary"]
        assert all(isinstance(c, str) for c in theme["citations"])
