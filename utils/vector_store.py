"""Vector store utilities for Pinecone integration."""

from __future__ import annotations

import logging
import os
from typing import Iterable, List, Tuple, Any

from dotenv import dotenv_values
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_config = dotenv_values(".env")
_PINECONE_KEY = _config.get("PINECONE_KEY") or os.getenv("PINECONE_KEY")
_PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX", "ey")

_embed_model: SentenceTransformer | None = None
_pinecone_client: Pinecone | None = None
_pinecone_index: Any | None = None


def get_embed_model() -> SentenceTransformer:
    """Lazy-load a 768-dim sentence transformer."""
    global _embed_model
    if _embed_model is None:
        # Default to a 768-d model to match the Pinecone index.
        model_name = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-mpnet-base-v2")
        logger.info(f"[VECTOR] Loading embedding model: {model_name}")
        _embed_model = SentenceTransformer(model_name)
    return _embed_model


def get_pinecone_index() -> Any | None:
    """Return a handle to the configured Pinecone index, or None on failure."""
    global _pinecone_client, _pinecone_index

    if not _PINECONE_KEY:
        logger.warning("[VECTOR] PINECONE_KEY not configured; skipping Pinecone integration")
        return None

    if _pinecone_index is not None:
        return _pinecone_index

    try:
        _pinecone_client = Pinecone(api_key=_PINECONE_KEY)
        index_name = _PINECONE_INDEX_NAME or "ey"
        logger.info(f"[VECTOR] Connecting to Pinecone index: {index_name}")
        _pinecone_index = _pinecone_client.Index(index_name)
        return _pinecone_index
    except Exception as e:
        logger.warning(f"[VECTOR] Failed to initialize Pinecone index: {str(e)}")
        return None


def upsert_rfp_chunks(
    rfp_id: str,
    chunks: Iterable[str],
    namespace: str | None = None,
) -> None:
    """
    Embed and upsert RFP chunks into Pinecone.

    Each chunk is stored with an id of the form "{rfp_id}-chunk-{i}" and
    basic metadata containing the RFP id and raw text.
    """
    index = get_pinecone_index()
    if index is None:
        logger.debug("[VECTOR] Skipping Pinecone upsert (no index available)")
        return

    chunk_list: List[str] = list(chunks)
    if not chunk_list:
        logger.debug("[VECTOR] No chunks to upsert to Pinecone")
        return

    try:
        model = get_embed_model()
        logger.info(f"[VECTOR] Embedding {len(chunk_list)} chunks for RFP {rfp_id}")
        vectors = model.encode(chunk_list, convert_to_numpy=True, show_progress_bar=False)

        # Build (id, vector, metadata) tuples for Pinecone
        upserts: List[Tuple[str, List[float], dict]] = []
        for i, (text, vec) in enumerate(zip(chunk_list, vectors)):
            vec_id = f"{rfp_id}-chunk-{i}"
            metadata = {
                "rfp_id": rfp_id,
                "chunk_index": i,
                "text": text,
            }
            upserts.append((vec_id, vec.tolist(), metadata))

        index.upsert(
            vectors=upserts,
            namespace=namespace or rfp_id,
        )
        logger.info(f"[VECTOR] Upserted {len(upserts)} chunks to Pinecone (namespace='{namespace or rfp_id}')")
    except Exception as e:
        logger.warning(f"[VECTOR] Failed to upsert RFP chunks to Pinecone: {str(e)}")
        # Do not fail the main pipeline if vector storage is unavailable.
        return


