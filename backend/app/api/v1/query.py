import logging
from typing import List
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.query import QueryRequest, QueryResponse, DocumentAnswers, AnswerSnippet
from app.db.session import get_db
from app.db.document_model import DocumentORM
from app.services.retrieval import retrieve_top_k_chunks
from app.services.llm_clients import extract_answer_from_chunk

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=QueryResponse,
    summary="Retrieve per‐document answers",
    description=(
        "Given a question, for each document (or a specified subset),\n"
        "1. Retrieves the top‐K chunks via Qdrant\n"
        "2. Calls the LLM to extract a concise answer snippet from each chunk\n"
        "3. Returns, for each document, a list of snippet objects with text + citation"
    ),
)
async def query_documents(
    req: QueryRequest,
    db: Session = Depends(get_db),
):
    """
    1. Determine which doc_ids to query: 
       - If req.doc_ids is provided, use that list.
       - Otherwise, query all documents from the database.
    2. For each doc_id, retrieve top_k chunks via retrieve_top_k_chunks().
    3. For each chunk, call extract_answer_from_chunk(...) concurrently.
    4. Filter out "NO_ANSWER" or errors, and collect per‐document snippets.
    5. Return QueryResponse(individual_answers=[DocumentAnswers, ...]).
    """
    if req.doc_ids:
        doc_ids = req.doc_ids
    else:
        rows = db.query(DocumentORM).all()
        doc_ids = [row.doc_id for row in rows]

    if not doc_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No documents available to query.")

    individual_answers: List[DocumentAnswers] = []

    async def process_single_doc(doc_id: str):
        """
        Retrieve and extract snippets for one document.
        Returns a DocumentAnswers or None if no valid snippets.
        """
        snippets: List[AnswerSnippet] = []
        chunks = retrieve_top_k_chunks(req.question, doc_id, top_k=req.top_k_per_doc or 3)

        tasks = [extract_answer_from_chunk(req.question, chunk) for chunk in chunks]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error during extract_answer_from_chunk: {result}")
                continue
            answer_text = result.get("answer")
            citation = result.get("citation", "")
            if answer_text and answer_text != "NO_ANSWER":
                snippets.append(AnswerSnippet(text=answer_text, citation=citation))

        if snippets:
            return DocumentAnswers(doc_id=doc_id, answers=snippets)
        return None

    tasks = [process_single_doc(did) for did in doc_ids]
    completed = await asyncio.gather(*tasks)

    for doc_ans in completed:
        if doc_ans:
            individual_answers.append(doc_ans)

    return QueryResponse(individual_answers=individual_answers)
