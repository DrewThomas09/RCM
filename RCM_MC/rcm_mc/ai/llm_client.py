"""LLM client with cost tracking and response caching (Prompt 71).

Wraps the Anthropic Messages API via stdlib ``urllib.request`` — no
third-party HTTP library required.  When ``ANTHROPIC_API_KEY`` is not
set the client returns a no-op fallback so every caller can treat the
LLM as "optional acceleration" rather than a hard dependency.

Cost tracking lives in a SQLite ``llm_calls`` table; identical prompts
are served from the ``llm_response_cache`` table keyed on
``(prompt_hash, model)``.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Cost table (per-1K tokens, approximate) ──────────────────────────
# Current Claude 4 lineup. Legacy ids kept as aliases so historical
# llm_calls rows still map to a cost band.
_COST_PER_1K: dict[str, tuple[float, float]] = {
    "claude-opus-4-7":           (0.015,  0.075),
    "claude-sonnet-4-6":         (0.003,  0.015),
    "claude-haiku-4-5-20251001": (0.0008, 0.004),
    # Legacy aliases.
    "claude-haiku-4-5":          (0.0008, 0.004),
    "claude-sonnet-4-20250514":  (0.003,  0.015),
    "claude-opus-4-20250514":    (0.015,  0.075),
}

_FALLBACK_MODEL = "fallback"
_API_URL = "https://api.anthropic.com/v1/messages"


# ── Dataclass ────────────────────────────────────────────────────────

@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd_estimate: float = 0.0


# ── SQLite helpers ───────────────────────────────────────────────────

def _ensure_tables(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS llm_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                called_at TEXT NOT NULL
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS llm_response_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_hash TEXT NOT NULL,
                model TEXT NOT NULL,
                response_text TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(prompt_hash, model)
            )"""
        )
        con.commit()


def _prompt_hash(system_prompt: str, user_prompt: str) -> str:
    blob = f"{system_prompt}\x00{user_prompt}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _lookup_cache(store: Any, phash: str, model: str) -> Optional[LLMResponse]:
    _ensure_tables(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT response_text, input_tokens, output_tokens "
            "FROM llm_response_cache WHERE prompt_hash = ? AND model = ?",
            (phash, model),
        ).fetchone()
    if row is None:
        return None
    return LLMResponse(
        text=row["response_text"],
        model=model,
        input_tokens=row["input_tokens"],
        output_tokens=row["output_tokens"],
        latency_ms=0.0,
        cost_usd_estimate=0.0,
    )


def _save_cache(store: Any, phash: str, resp: LLMResponse) -> None:
    _ensure_tables(store)
    with store.connect() as con:
        con.execute(
            "INSERT OR REPLACE INTO llm_response_cache "
            "(prompt_hash, model, response_text, input_tokens, output_tokens, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (phash, resp.model, resp.text, resp.input_tokens, resp.output_tokens,
             datetime.now(timezone.utc).isoformat()),
        )
        con.commit()


def _log_call(store: Any, resp: LLMResponse) -> None:
    _ensure_tables(store)
    with store.connect() as con:
        con.execute(
            "INSERT INTO llm_calls (model, input_tokens, output_tokens, cost_usd, called_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (resp.model, resp.input_tokens, resp.output_tokens, resp.cost_usd_estimate,
             datetime.now(timezone.utc).isoformat()),
        )
        con.commit()


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = _COST_PER_1K.get(model, (0.001, 0.005))
    return (input_tokens / 1000) * rates[0] + (output_tokens / 1000) * rates[1]


# ── Client ───────────────────────────────────────────────────────────

class LLMClient:
    """Thin wrapper around the Anthropic Messages API."""

    def __init__(self, store: Any = None) -> None:
        self._api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._store = store

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str = "claude-haiku-4-5-20251001",
        max_tokens: int = 2000,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Send a completion request. Returns a fallback when the key is absent.

        Default model is Claude Haiku 4.5 — cheap + fast enough for
        fact-checking and short memo sections. Callers that need deeper
        reasoning (IC memo drafting, complex Q&A) should pass
        ``model="claude-sonnet-4-6"`` or ``"claude-opus-4-7"``.
        """
        if not self._api_key:
            return LLMResponse(
                text="[LLM not configured]",
                model=_FALLBACK_MODEL,
            )

        # Cache check
        phash = _prompt_hash(system_prompt, user_prompt)
        if self._store is not None:
            cached = _lookup_cache(self._store, phash, model)
            if cached is not None:
                return cached

        # Build request
        body = json.dumps({
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }).encode("utf-8")

        req = urllib.request.Request(
            _API_URL,
            data=body,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )

        t0 = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            logger.warning("LLM call failed: %s", exc)
            return LLMResponse(
                text="[LLM call failed]",
                model=model,
            )
        latency = (time.monotonic() - t0) * 1000

        # Parse response
        text_parts = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block["text"])
        text = "\n".join(text_parts) or "[empty response]"

        usage = data.get("usage", {})
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        cost = _estimate_cost(model, in_tok, out_tok)

        result = LLMResponse(
            text=text,
            model=model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_ms=latency,
            cost_usd_estimate=cost,
        )

        # Persist
        if self._store is not None:
            _save_cache(self._store, phash, result)
            _log_call(self._store, result)

        return result
