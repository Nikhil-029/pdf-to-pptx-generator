"""
job_store.py
────────────
Thin abstraction over Redis for job-status tracking.

Falls back to an in-memory dict when Redis is unavailable so the app still
runs locally without a Redis server (useful for development / quick tests).
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_MEMORY_STORE: Dict[str, str] = {}  # fallback when Redis is down


def _redis_client():
    """Lazy import + connect so startup never crashes if Redis is absent."""
    try:
        import redis
        from core.config import settings

        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


class JobStore:
    JOB_TTL_SECONDS = 60 * 60 * 2  # 2 hours

    @classmethod
    def set(cls, job_id: str, data: Dict[str, Any]) -> None:
        payload = json.dumps(data, default=str)
        r = _redis_client()
        if r:
            try:
                r.setex(f"job:{job_id}", cls.JOB_TTL_SECONDS, payload)
                return
            except Exception as exc:
                logger.warning("Redis write failed, using memory fallback: %s", exc)
        _MEMORY_STORE[f"job:{job_id}"] = payload

    @classmethod
    def get(cls, job_id: str) -> Optional[Dict[str, Any]]:
        r = _redis_client()
        if r:
            try:
                raw = r.get(f"job:{job_id}")
                if raw:
                    return json.loads(raw)
                return None
            except Exception as exc:
                logger.warning("Redis read failed, using memory fallback: %s", exc)
        raw = _MEMORY_STORE.get(f"job:{job_id}")
        return json.loads(raw) if raw else None

    @classmethod
    def update_status(
        cls,
        job_id: str,
        status: str,
        *,
        progress: int = 0,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> None:
        existing = cls.get(job_id) or {}
        existing.update({"status": status, "progress": progress})
        if result is not None:
            existing["result"] = result
        if error is not None:
            existing["error"] = error
        cls.set(job_id, existing)
