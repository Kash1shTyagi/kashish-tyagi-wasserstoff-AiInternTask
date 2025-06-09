import logging
from typing import List, Dict, Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from app.services.llm_clients import get_embedding_vector, generate_theme_summary

logger = logging.getLogger(__name__)


def cluster_snippets(
    snippets: List[Dict[str, str]],
    n_clusters: int
) -> Dict[int, List[int]]:
    """
    Given a list of snippet dicts (each with at least a "text" key),
    embed each snippet, then cluster embeddings into `n_clusters` clusters.

    Returns:
      A mapping from cluster label (0..n_clusters-1) to a list of indices
      (into the original `snippets` list) that belong to that cluster.

    If embedding a snippet fails, that snippet is skipped.
    """
    valid_embeddings: List[List[float]] = []
    valid_indices: List[int] = []

    for idx, snippet in enumerate(snippets):
        text = snippet.get("text", "").strip()
        if not text:
            logger.warning(f"Skipping empty snippet at index {idx}.")
            continue
        try:
            emb = get_embedding_vector(text)
            valid_embeddings.append(emb)
            valid_indices.append(idx)
        except Exception as e:
            logger.error(f"Embedding failed for snippet index {idx}: {e}")

    if not valid_embeddings:
        return {}

    k = min(n_clusters, len(valid_embeddings))
    if k <= 1:
        return {0: valid_indices}

    try:
        embedding_matrix = np.array(valid_embeddings)
        clustering = AgglomerativeClustering(n_clusters=k)
        labels = clustering.fit_predict(embedding_matrix)
    except Exception as e:
        logger.error(f"Clustering failed: {e}")
        return {0: valid_indices}

    clusters: Dict[int, List[int]] = {}
    for emb_idx, cluster_label in enumerate(labels):
        orig_idx = valid_indices[emb_idx]
        clusters.setdefault(cluster_label, []).append(orig_idx)

    return clusters


async def identify_and_summarize_themes(
    snippets: List[Dict[str, Any]],
    question: str
) -> List[Dict[str, Any]]:
    """
    Given a list of snippet dicts (each with keys: "doc_id", "text", "citation"),
    cluster them into themes and generate a summary for each theme using the LLM.

    Steps:
      1. Determine number of clusters: heuristic = min(max(1, len(snippets)//3), 4)
      2. Call cluster_snippets(...) to get clusters mapping.
      3. For each cluster, gather its member snippets and call generate_theme_summary(...)
         which returns a dict: {"theme_name": ..., "summary": ..., "citations": [...]}
      4. Return a list of these theme‐summary dicts, in ascending cluster_label order.

    If no snippets, returns an empty list.
    """
    n_snip = len(snippets)
    if n_snip == 0:
        return []

    n_clusters = min(max(1, n_snip // 3), 4)

    clusters_map = cluster_snippets(snippets, n_clusters)
    if not clusters_map:
        citations = [s.get("citation", "") for s in snippets]
        return [
            {
                "theme_name": "Theme 1",
                "summary": "",
                "citations": citations,
            }
        ]

    themes: List[Dict[str, Any]] = []

    for label in sorted(clusters_map.keys()):
        member_indices = clusters_map[label]
        member_snippets = [snippets[i] for i in member_indices]

        try:
            theme_data = await generate_theme_summary(
                snippets=member_snippets,
                theme_id=label + 1,
                question=question
            )
            themes.append(theme_data)
        except Exception as e:
            logger.error(f"Theme generation failed for cluster {label}: {e}")
            fallback_citations = [s.get("citation", "") for s in member_snippets]
            themes.append({
                "theme_name": f"Theme {label + 1}",
                "summary": "",
                "citations": fallback_citations
            })

    return themes
