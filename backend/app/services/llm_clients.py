import logging
import json
import asyncio
import re
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
genai.configure(api_key=GEMINI_API_KEY)
_model = genai.GenerativeModel(GEMINI_MODEL_NAME)

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
    Uses google.generativeai to generate an embedding via a Gemini model.
    Returns a flat list of floats.
    """
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set for embeddings.")

    try:
        response = genai.embed_content(
            model="models/embedding-001",
            content=[text],
            task_type="SEMANTIC_SIMILARITY"
        )
        embedding = response.get("embedding", [])
        if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
            embedding = embedding[0]
        embedding = [float(x) for x in embedding]
        return embedding
    except Exception as e:
        logger.error(f"Gemini embedding error: {e}")
        raise RuntimeError(f"Gemini embedding failed: {e}")
    

def get_query_embedding(query_text: str) -> List[float]:
    """
    Generates an embedding for the provided query text.
    Ensures the output is a flat list of floats.
    """
    embedding = get_embedding_vector(query_text)
    if isinstance(embedding, list) and len(embedding) == 1 and isinstance(embedding[0], list):
        embedding = embedding[0]
    return [float(x) for x in embedding]


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


_FALLBACK_JSON = '{"answer": "NO_ANSWER", "citation": ""}'

def _do_chat(prompt: str) -> str:
    try:
        chat = _model.start_chat()
        resp = chat.send_message(prompt)
        print(f"Gemini raw resp: {resp!r}")

        if hasattr(resp, "result"):
            candidates = resp.result.candidates
            if candidates:
                text = candidates[0].content.parts[0].text
            else:
                text = ""
        else:
            text = getattr(resp, "text", "") or ""

        text = re.sub(r"```json\s*|\s*```", "", text)

        stripped = text.strip()
        if stripped.startswith('"') and stripped.endswith('"'):
            inner = stripped[1:-1].replace('\\"', '"')
            text = inner

        if not text.strip().startswith("{"):
            print("→ No leading '{', falling back to NO_ANSWER")
            return _FALLBACK_JSON

        return text

    except Exception as e:
        logger.error("Gemini send_message error: %s", e)
        return _FALLBACK_JSON

async def extract_answer_gemini(question: str, chunk: Dict) -> Dict[str, str]:
    """
    Uses google.generativeai to extract an answer from a document chunk.
    Returns {"answer": str, "citation": str}.
    """
    doc_id     = chunk.get("doc_id", "UnknownDoc")
    page_num   = chunk.get("page_num", 0)
    para_idx   = chunk.get("paragraph_index", 0)
    chunk_text = chunk.get("chunk_text", "")


    prompt = (
         f"You are a research assistant. The user asked:\n\n"
         f"\"{question}\"\n\n"
         f"Here is the document excerpt (DocID: {doc_id}, Page: {page_num}, Para: {para_idx}):\n\n"
         f"\"\"\"\n{chunk_text}\n\"\"\"\n\n"
         "Please respond **strictly** in JSON **with these two fields**:\n"
         "{\n"
         '  "answer": "<the exact snippet or NO_ANSWER>",\n'
         '  "citation": "DocID: <doc_id>, Page: <page_num>, Para: <para_idx>"\n'
         "}\n\n"
         "If you do not see the answer to the question in this excerpt, return:\n"
         "{ \"answer\": \"NO_ANSWER\", \"citation\": \"\" }"
     )



    try:
        raw = await asyncio.to_thread(_do_chat, prompt)
        data = json.loads(raw.strip())
    except json.JSONDecodeError:
        logger.error("Invalid JSON from Gemini, falling back to NO_ANSWER")
        return {"answer": "NO_ANSWER", "citation": ""}
    except Exception as e:
        logger.error("Unexpected error in extract_answer_gemini: %s", e)
        return {"answer": "NO_ANSWER", "citation": ""}

    if data.get("answer", "").upper() == "NO_ANSWER":
        return {"answer": "NO_ANSWER", "citation": ""}

    return {"answer": data["answer"], "citation": data["citation"]}

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


_FALLBACK_THEME = {
    "theme_name": None,
    "summary": "",
    "citations": []
}

def _do_theme_chat(prompt: str) -> str:
    try:
        chat = _model.start_chat()
        resp = chat.send_message(prompt)

        if hasattr(resp, "result"):
            candidates = resp.result.candidates
            text = candidates[0].content.parts[0].text if candidates else ""
        else:
            text = getattr(resp, "text", "") or ""

        text = re.sub(r"```json\s*|\s*```", "", text)

        stripped = text.strip()
        if stripped.startswith('"') and stripped.endswith('"'):
            text = stripped[1:-1].replace('\\"', '"')

        if not text.strip().startswith("{"):
            return ""

        return text

    except Exception as e:
        logger.error("Gemini theme send_message error: %s", e)
        return ""

async def generate_theme_gemini(
    snippets: List[Dict], theme_id: int, question: str
) -> Dict:
    """
    Uses google.generativeai to synthesize a thematic summary from multiple snippets.
    """
    snippet_lines = "\n".join([f"[{s['citation']}] \"{s['text']}\"" for s in snippets])

    prompt = (
        f"You are a research assistant. The user asked: \"{question}\"\n\n"
        f"Below are the excerpts belonging to Theme {theme_id}:\n\n"
        f"{snippet_lines}\n\n"
        "Task:\n"
        f"1) Provide a short label: \"Theme {theme_id} – <name>\".\n"
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
        raw = await asyncio.to_thread(_do_theme_chat, prompt)
        data = json.loads(raw)

        return {
            "theme_name": data.get("theme_name", f"Theme {theme_id}"),
            "summary": data.get("summary", ""),
            "citations": data.get("citations", []),
        }
    except Exception as e:
        logger.error(f"Gemini generate_theme error: {e}")
        return {
            "theme_name": data.get("theme_name", f"Theme {theme_id}") if "data" in locals() else f"Theme {theme_id}",
            "summary": data.get("summary", "") if "data" in locals() else "",
            "citations": data.get("citations", []) if "data" in locals() else [s.get("citation","") for s in snippets],
        }