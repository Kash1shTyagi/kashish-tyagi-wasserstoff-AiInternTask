import logging
import json
import asyncio
from typing import List, Dict, Optional

import google.generativeai as genai

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    groq_client: Optional[Groq] = Groq(api_key=settings.GROQ_API_KEY)
    logger.info("Initialized GroqClient successfully.")
except Exception as e:
    groq_client = None
    logger.warning(f"Failed to initialize GroqClient: {e}")

GEMINI_API_KEY = settings.GEMINI_API_KEY
GEMINI_MODEL_NAME = getattr(settings, "GEMINI_MODEL_NAME", "gemini-1.5-flash")

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY is not set; Gemini backend calls will fail.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info(f"Configured google.generativeai with model '{GEMINI_MODEL_NAME}'.")
    except Exception as e:
        logger.error(f"Failed to configure google.generativeai: {e}")


def get_embedding_vector(text: str) -> List[float]:
    """
    Dispatch to either Groq or Gemini embedding based on DEFAULT_LLM_BACKEND.
    Returns a list of floats (the embedding vector).
    """
    backend = settings.DEFAULT_LLM_BACKEND.lower()
    if backend == "groq":
        return get_embedding_vector_groq(text)
    elif backend == "gemini":
        return get_embedding_vector_gemini(text)
    else:
        raise ValueError(f"Unknown LLM backend: {backend}")


def get_embedding_vector_groq(text: str) -> List[float]:
    """
    Use Groq's embedding endpoint. Assumes Groq has a model named "<GROQ_MODEL_NAME>-embed".
    """
    if groq_client is None:
        raise RuntimeError("GroqClient is not initialized.")

    try:
        response = groq_client.embeddings.create(
            model=settings.GROQ_MODEL_NAME,
            input=[text]
        )
        embedding = response.embeddings[0]
        return embedding
    except Exception as e:
        logger.error(f"Groq embedding error: {e}")
        raise RuntimeError(f"Groq embedding failed: {e}")


def get_embedding_vector_gemini(text: str) -> List[float]:
    """
    Use google.generativeai for embeddings via a Gemini model that supports embeddings
    (Gemini models like 'embedding-gecko-001').
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set for embeddings.")

    try:
        response = genai.embed_content(
            model="models/embedding-001",  
            content=[text],               
            task_type="SEMANTIC_SIMILARITY" 
        )
        
        return response.get("embedding", [])
    except Exception as e:
        logger.error(f"Gemini embedding error: {e}")
        raise RuntimeError(f"Gemini embedding failed: {e}")



async def extract_answer_from_chunk(question: str, chunk: Dict) -> Dict[str, str]:
    """
    Given a user question and a chunk dict (with keys: doc_id, page_num, paragraph_index, chunk_text),
    dispatch to the appropriate LLM backend to extract a concise answer snippet and citation.
    Returns: {"answer": "...", "citation": "..."} or {"answer": "NO_ANSWER", "citation": ""}
    """
    backend = settings.DEFAULT_LLM_BACKEND.lower()
    if backend == "groq":
        return await extract_answer_groq(question, chunk)
    elif backend == "gemini":
        return await extract_answer_gemini(question, chunk)
    else:
        raise ValueError(f"Unknown LLM backend: {backend}")


async def extract_answer_groq(question: str, chunk: Dict) -> Dict[str, str]:
    """
    Use Groq's chat completions to extract an answer from a single chunk.
    """
    if groq_client is None:
        raise RuntimeError("GroqClient is not initialized.")

    prompt = (
        f"You are a research assistant. The user asked:\n\n"
        f"\"{question}\"\n\n"
        f"Below is a document excerpt (DocID: {chunk['doc_id']}, Page: {chunk['page_num']}, Para: {chunk['paragraph_index']}):\n\n"
        f"\"\"\"{chunk['chunk_text']}\"\"\"\n\n"
        "If this excerpt contains a relevant answer, extract a concise snippet (1-2 sentences). "
        "Otherwise respond with \"NO_ANSWER\".\n\n"
        "Return exactly JSON: {\n"
        '  "answer": "<text or NO_ANSWER>",\n'
        '  "citation": "DocID: ' + f"{chunk['doc_id']}, Page: {chunk['page_num']}, Para: {chunk['paragraph_index']}" + '"\n'
        "}"
    )

    try:
        response = await groq_client.chat.completions.create(
            model=settings.GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        if data.get("answer", "").upper() == "NO_ANSWER":
            return {"answer": "NO_ANSWER", "citation": ""}
        return {"answer": data["answer"], "citation": data["citation"]}
    except Exception as e:
        logger.error(f"Groq extract_answer error: {e}")
        return {"answer": "NO_ANSWER", "citation": ""}


async def extract_answer_gemini(question: str, chunk: Dict) -> Dict[str, str]:
    """
    Use google.generativeai to extract an answer from a single chunk.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set for Gemini extraction.")

    prompt = (
        f"You are a research assistant. The user asked:\n\n"
        f"\"{question}\"\n\n"
        f"Below is a document excerpt (DocID: {chunk['doc_id']}, Page: {chunk['page_num']}, Para: {chunk['paragraph_index']}):\n\n"
        f"\"\"\"{chunk['chunk_text']}\"\"\"\n\n"
        "If this excerpt contains a relevant answer, extract a concise snippet (1-2 sentences). "
        "Otherwise respond with \"NO_ANSWER\".\n\n"
        "Return exactly JSON: {\n"
        '  "answer": "<text or NO_ANSWER>",\n'
        '  "citation": "DocID: ' + f"{chunk['doc_id']}, Page: {chunk['page_num']}, Para: {chunk['paragraph_index']}" + '"\n'
        "}"
    )

    try:
        response = await asyncio.to_thread(
            lambda: genai.ChatCompletion.create(model=GEMINI_MODEL_NAME, prompt=prompt, temperature=0.0)
        )
        raw_text = response.text.strip()
        data = json.loads(raw_text)
        if data.get("answer", "").upper() == "NO_ANSWER":
            return {"answer": "NO_ANSWER", "citation": ""}
        return {"answer": data["answer"], "citation": data["citation"]}
    except Exception as e:
        logger.error(f"Gemini extract_answer error: {e}")
        return {"answer": "NO_ANSWER", "citation": ""}



async def generate_theme_summary(
    snippets: List[Dict], theme_id: int, question: str
) -> Dict:
    """
    Given a list of snippet dicts (each with keys: 'doc_id', 'text', 'citation'),
    produce a JSON-like dict with:
      {
        "theme_name": "<short label>",
        "summary": "<2-3 sentence synthesis>",
        "citations": [ ... ]
      }
    """
    backend = settings.DEFAULT_LLM_BACKEND.lower()
    if backend == "groq":
        return await generate_theme_groq(snippets, theme_id, question)
    elif backend == "gemini":
        return await generate_theme_gemini(snippets, theme_id, question)
    else:
        raise ValueError(f"Unknown LLM backend: {backend}")


async def generate_theme_groq(
    snippets: List[Dict], theme_id: int, question: str
) -> Dict:
    """
    Use Groq's chat to synthesize one theme’s summary.
    """
    if groq_client is None:
        raise RuntimeError("GroqClient is not initialized.")

    snippet_lines = "\n".join(
        [f"[{s['citation']}] \"{s['text']}\"" for s in snippets]
    )

    prompt = (
        f"You are a research assistant. The user asked: \"{question}\"\n\n"
        f"Below are the excerpts belonging to Theme {theme_id}:\n\n"
        f"{snippet_lines}\n\n"
        "Task:\n"
        "1) Provide a short label: \"Theme {theme_id} – <name>\".\n"
        "2) Write a 2-3 sentence synthesis of the main idea across these excerpts.\n"
        "3) Return all citations in a JSON array.\n\n"
        "Return exactly JSON:\n"
        "{\n"
        '  "theme_name": "<short label>",\n'
        '  "summary": "<synthesis>",\n'
        '  "citations": ["<cit1>", "<cit2>", ...]\n'
        "}"
    )

    try:
        response = await groq_client.chat.completions.create(
            model=settings.GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        data = json.loads(content)
        return {
            "theme_name": data.get("theme_name", f"Theme {theme_id}"),
            "summary": data.get("summary", ""),
            "citations": data.get("citations", [])
        }
    except Exception as e:
        logger.error(f"Groq generate_theme error: {e}")
        return {
            "theme_name": f"Theme {theme_id}",
            "summary": "",
            "citations": [s["citation"] for s in snippets]
        }


async def generate_theme_gemini(
    snippets: List[Dict], theme_id: int, question: str
) -> Dict:
    """
    Use google.generativeai to synthesize one theme’s summary.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set for theme synthesis.")

    snippet_lines = "\n".join(
        [f"[{s['citation']}] \"{s['text']}\"" for s in snippets]
    )

    prompt = (
        f"You are a research assistant. The user asked: \"{question}\"\n\n"
        f"Below are the excerpts belonging to Theme {theme_id}:\n\n"
        f"{snippet_lines}\n\n"
        "Task:\n"
        "1) Provide a short label: \"Theme {theme_id} – <name>\".\n"
        "2) Write a 2-3 sentence synthesis of the main idea across these excerpts.\n"
        "3) Return all citations in a JSON array.\n\n"
        "Return exactly JSON:\n"
        "{\n"
        '  "theme_name": "<short label>",\n'
        '  "summary": "<synthesis>",\n'
        '  "citations": ["<cit1>", "<cit2>", ...]\n'
        "}"
    )

    try:
        response = await asyncio.to_thread(
            lambda: genai.ChatCompletion.create(model=GEMINI_MODEL_NAME, prompt=prompt, temperature=0.2)
        )
        raw_text = response.text.strip()
        data = json.loads(raw_text)
        return {
            "theme_name": data.get("theme_name", f"Theme {theme_id}"),
            "summary": data.get("summary", ""),
            "citations": data.get("citations", [])
        }
    except Exception as e:
        logger.error(f"Gemini generate_theme error: {e}")
        return {
            "theme_name": f"Theme {theme_id}",
            "summary": "",
            "citations": [s["citation"] for s in snippets]
        }
