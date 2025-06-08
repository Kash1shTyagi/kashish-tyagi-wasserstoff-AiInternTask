from typing import List, Optional
from pydantic import BaseModel


class ThemeRequest(BaseModel):
    """
    Payload for /api/v1/theme:
      - question: the user’s natural-language question
      - doc_ids: optional list of doc_id strings; if omitted, query all documents
      - top_k_per_doc: optional int; how many chunks to retrieve per document
    Reuses the same fields as QueryRequest.
    """
    question: str
    doc_ids: Optional[List[str]] = None
    top_k_per_doc: Optional[int] = 3


class ThemeOutput(BaseModel):
    """
    One theme cluster, as synthesized by the LLM:
      - theme_name: a short label, e.g. "Regulatory Non-Compliance"
      - summary: a 2- to 3-sentence chat-style synthesis of all snippets in this theme
      - citations: list of citation strings, e.g. ["doc_ab12cd34, Page 4, Para 2", ...]
    """
    theme_name: str
    summary: str
    citations: List[str]


class ThemeResponse(BaseModel):
    """
    Response for /api/v1/theme:
    - themes: a list of ThemeOutput, one for each identified theme
    """
    themes: List[ThemeOutput]
