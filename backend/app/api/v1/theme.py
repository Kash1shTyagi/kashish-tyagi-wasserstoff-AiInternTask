import logging
from typing import List
import asyncio

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.theme import ThemeRequest, ThemeResponse, ThemeOutput
from app.db.session import get_db
from app.db.document_model import DocumentORM
from app.services.retrieval import retrieve_top_k_chunks
from app.services.llm_clients import extract_answer_from_chunk
from app.services.theme_identification import identify_and_summarize_themes

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/",
    response_model=ThemeResponse,
    summary="Identify and summarize themes across documents",
    description=(
        "Given a question, this endpoint:\n"
        "1. Retrieves top‐K chunks per document\n"
        "2. Extracts answer snippets from each chunk via LLM\n"
        "3. Clusters all snippets into 1–4 themes (embedding‐based)\n"
        "4. Calls the LLM to generate a short “Theme # – <Label>” summary per cluster,\n"
        "   listing all citations for that theme.\n"
        "Returns a list of ThemeOutput objects."
    ),
)
async def generate_themes(
    req: ThemeRequest,
    db: Session = Depends(get_db),
):
    """
    1. Determine which doc_ids to query (same as /query).
    2. For each doc_id, retrieve top‐K chunks and extract snippets.
    3. Collect all non‐empty snippets into a single list of dicts:
       { "doc_id": str, "text": str, "citation": str }
    4. Call identify_and_summarize_themes(...) with that list + question.
    5. Return ThemeResponse with a list of ThemeOutput.
    """
    if req.doc_ids:
        doc_ids = req.doc_ids
    else:
        rows = db.query(DocumentORM).all()
        doc_ids = [row.doc_id for row in rows]

    if not doc_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No documents available to query.")

    all_snippets: List[dict] = []

    async def process_doc_snippets(doc_id: str):
        chunks = retrieve_top_k_chunks(req.question, doc_id, top_k=req.top_k_per_doc or 3)
        tasks = [extract_answer_from_chunk(req.question, c) for c in chunks]
        answers = await asyncio.gather(*tasks, return_exceptions=True)
        for ans in answers:
            if isinstance(ans, Exception):
                logger.error(f"Error in extract_answer_from_chunk: {ans}")
                continue
            if ans.get("answer") and ans["answer"] != "NO_ANSWER":
                all_snippets.append({
                    "doc_id": doc_id,
                    "text": ans["answer"],
                    "citation": ans["citation"]
                })

    await asyncio.gather(*(process_doc_snippets(did) for did in doc_ids))

    if not all_snippets:
        return ThemeResponse(themes=[])

    try:
        theme_dicts = await identify_and_summarize_themes(all_snippets, req.question)
    except Exception as e:
        logger.error(f"identify_and_summarize_themes failed: {e}")
        raise HTTPException(status_code=500, detail="Theme identification failed.")

    themes: List[ThemeOutput] = [
        ThemeOutput(
            theme_name=t["theme_name"],
            summary=t["summary"],
            citations=t["citations"]
        )
        for t in theme_dicts
    ]

    return ThemeResponse(themes=themes)
