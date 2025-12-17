"""Redis helpers for caching intermediate pipeline artifacts."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)


def get_redis_client() -> Optional[redis.Redis]:
    """Initialize a Redis client, returning None if connection fails."""
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    try:
        client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        # Ping to validate connectivity
        client.ping()
        return client
    except Exception:
        # In environments without Redis, downstream code should handle None.
        return None


def cache_json(client: Optional[redis.Redis], key: str, value: Any, ttl_seconds: int = 86400) -> None:
    """Persist a JSON-serializable value if Redis is available."""
    if not client:
        logger.debug(f"[REDIS] Skipping cache (no client): {key}")
        return
    try:
        client.setex(key, ttl_seconds, json.dumps(value))
        logger.debug(f"[REDIS] Cached data: {key} (TTL: {ttl_seconds}s)")
    except Exception as e:
        logger.warning(f"[REDIS] Failed to cache {key}: {str(e)}")
        # Fail silently to keep the pipeline running
        return


def fetch_json(client: Optional[redis.Redis], key: str) -> Any:
    """Retrieve cached JSON data if present."""
    if not client:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


