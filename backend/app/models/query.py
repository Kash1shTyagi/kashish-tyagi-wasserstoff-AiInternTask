from typing import List, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    """
    Payload for /api/v1/query:
      - question: the user’s natural-language question
      - doc_ids: optional list of doc_id strings; if omitted, query all documents
      - top_k_per_doc: optional int; how many chunks to retrieve per document
    """
    question: str
    doc_ids: Optional[List[str]] = None
    top_k_per_doc: Optional[int] = 3



class AnswerSnippet(BaseModel):
    """
    One snippet of answer extracted from a single chunk of a document.
    - text: the snippet text itself
    - citation: a string of the form "DocID: <doc_id>, Page: <n>, Para: <m>"
    """
    text: str
    citation: str


class DocumentAnswers(BaseModel):
    """
    All answer snippets for one document.
    - doc_id: which document these snippets came from
    - answers: list of AnswerSnippet
    """
    doc_id: str
    answers: List[AnswerSnippet]


class QueryResponse(BaseModel):
    """
    Response for /api/v1/query:
    - individual_answers: a list of DocumentAnswers, one per document that had at least one snippet
    """
    individual_answers: List[DocumentAnswers]
