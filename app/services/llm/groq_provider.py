"""
groq_provider.py
────────────────
Wraps the Groq API with retry logic, structured JSON output, and
clear error messages.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict

from groq import Groq, RateLimitError, APIStatusError

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY_SECONDS = 2


class GroqProvider:
    def __init__(self) -> None:
        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to your .env file or environment."
            )
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    def generate_json(self, prompt: str) -> Dict[str, Any]:
        """
        Sends *prompt* to Groq and returns a parsed JSON dict.
        Retries up to _MAX_RETRIES times on rate-limit or transient errors.
        """
        last_exc: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                logger.debug("Groq request (attempt %d/%d)", attempt, _MAX_RETRIES)
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a JSON data API. "
                                "Respond with valid JSON only. "
                                "No markdown, no code fences, no preamble."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                raw = response.choices[0].message.content or ""
                return json.loads(raw)

            except RateLimitError as exc:
                logger.warning("Groq rate-limit hit (attempt %d): %s", attempt, exc)
                last_exc = exc
                time.sleep(_RETRY_DELAY_SECONDS * attempt)

            except json.JSONDecodeError as exc:
                logger.error("Groq returned non-JSON: %s", exc)
                raise ValueError("LLM returned invalid JSON. Please try again.") from exc

            except APIStatusError as exc:
                logger.error("Groq API error (attempt %d): %s", attempt, exc)
                last_exc = exc
                if exc.status_code and exc.status_code < 500:
                    break  # 4xx – no point retrying
                time.sleep(_RETRY_DELAY_SECONDS)

            except Exception as exc:
                logger.exception("Unexpected Groq error")
                raise

        raise RuntimeError(
            f"Groq API failed after {_MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc
