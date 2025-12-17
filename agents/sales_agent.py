"""Sales agent: ingestion and hierarchical chunking of RFPs."""

from __future__ import annotations

import logging
from typing import List

import fitz  # PyMuPDF

from utils.llm import generate_summary
from utils.redis_store import cache_json
from utils.state import RFPState
from utils.text import chunk_text, clean_text, find_sections
from utils.vector_store import upsert_rfp_chunks

logger = logging.getLogger(__name__)


def extract_text(pdf_bytes: bytes) -> str:
    """Extract raw text from a PDF byte stream."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text


def hierarchical_chunk(text: str) -> List[str]:
    """Perform section-level chunking with token-aware splits."""
    chunks: List[str] = []
    for heading, body in find_sections(text):
        body_chunks = chunk_text(body, max_tokens=1000, overlap=120)
        if not body_chunks:
            chunks.append(f"{heading}\n\n{body}")
        else:
            for idx, c in enumerate(body_chunks):
                chunks.append(f"{heading} [{idx + 1}]\n\n{c}")
    return chunks


def sales_agent(state: RFPState, redis_client=None) -> RFPState:
    """
    Entry-point agent:
    - Ingest raw text
    - Clean and chunk
    - Produce abstract
    - Persist chunks into Redis for downstream agents
    """
    rfp_id = state.get("rfp_id", "rfp")
    logger.info(f"[SALES AGENT] Starting processing for RFP: {rfp_id}")
    logger.info(f"[SALES AGENT] Received state with status: {state.get('status', 'UNKNOWN')}")
    
    raw_text = clean_text(state.get("raw_text", ""))
    if not raw_text and "pdf_bytes" in state:
        logger.info("[SALES AGENT] Extracting text from PDF bytes")
        raw_text = clean_text(extract_text(state["pdf_bytes"]))  # type: ignore[arg-type]
    
    logger.info(f"[SALES AGENT] Processing text of length: {len(raw_text)} characters")
    
    chunks = hierarchical_chunk(raw_text)
    logger.info(f"[SALES AGENT] Created {len(chunks)} chunks")
    
    # Use LLM for intelligent abstract generation
    logger.info("[SALES AGENT] Generating abstract using Gemini Flash 2.5...")
    abstract = generate_summary(raw_text, max_words=140)
    logger.info(f"[SALES AGENT] Generated abstract: {abstract[:100]}...")
    
    # Cache to Redis
    cache_key_chunks = f"rfp:{rfp_id}:chunks"
    cache_key_abstract = f"rfp:{rfp_id}:abstract"
    cache_json(redis_client, cache_key_chunks, chunks)
    cache_json(redis_client, cache_key_abstract, abstract)
    logger.info(f"[SALES AGENT] Cached chunks to Redis: {cache_key_chunks}")
    logger.info(f"[SALES AGENT] Cached abstract to Redis: {cache_key_abstract}")

    # Also persist chunks to Pinecone vector index for semantic search.
    logger.info("[SALES AGENT] Upserting chunks to Pinecone vector store...")
    upsert_rfp_chunks(rfp_id, chunks)

    updated: RFPState = {
        **state,
        "raw_text": raw_text,
        "chunks": chunks,
        "abstract": abstract,
        "status": "RFP_READY",
    }
    
    logger.info(f"[SALES AGENT] Completed. Status: RFP_READY. Passing to TECHNICAL AGENT")
    return updated

