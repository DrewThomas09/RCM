"""Local Ollama HTTP client for the read-only PEdesk Guide.

Stdlib ``urllib`` only — no third-party HTTP dependency (matching
``rcm_mc/ai/llm_client.py``). Ollama is treated as *optional acceleration*:
when it is disabled or unreachable, callers get a typed ``OllamaError``
rather than a crash, so the Guide endpoint can return a clean 503.

Config (environment variables; PEdesk has no central config system, so we
read ``os.environ`` directly):

  PEDESK_GUIDE_OLLAMA_ENABLED          true/false  (default: DISABLED)
  PEDESK_GUIDE_OLLAMA_BASE_URL         default http://localhost:11434
  PEDESK_GUIDE_OLLAMA_MODEL            default gemma4:e4b
  PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS  default 30

Default-disabled is deliberate: production / unknown environments make no
model calls unless someone explicitly opts in. Local dev sets
``PEDESK_GUIDE_OLLAMA_ENABLED=true``.

This module is read-only: it sends a chat request and returns text. It
never writes to disk, never touches the portfolio store, and performs no
diligence computation.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e4b"
DEFAULT_TIMEOUT_SECONDS = 30


class OllamaError(RuntimeError):
    """Raised when Ollama is disabled, unreachable, or errors."""


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = (os.environ.get(name) or "").strip()
    return val or default


def ollama_base_url() -> str:
    return _env("PEDESK_GUIDE_OLLAMA_BASE_URL", DEFAULT_BASE_URL) or DEFAULT_BASE_URL


def ollama_default_model() -> str:
    return _env("PEDESK_GUIDE_OLLAMA_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL


def ollama_timeout_seconds() -> int:
    raw = _env("PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def is_ollama_enabled() -> bool:
    """True only when PEDESK_GUIDE_OLLAMA_ENABLED is explicitly truthy."""
    return (_env("PEDESK_GUIDE_OLLAMA_ENABLED", "") or "").lower() in (
        "1", "true", "yes", "on",
    )


def check_ollama_health() -> bool:
    """True if the local Ollama server answers GET /api/tags. Never raises."""
    url = ollama_base_url().rstrip("/") + "/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        timeout = min(5, ollama_timeout_seconds())
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:  # noqa: BLE001 — health check must never throw
        return False


def call_ollama_chat(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
) -> str:
    """POST /api/chat to local Ollama; return the assistant message text.

    Raises ``OllamaError`` when disabled, unreachable, on HTTP error
    (e.g. the model is not pulled), or on a malformed response. Never
    leaks a raw stack trace to the caller.
    """
    if not is_ollama_enabled():
        raise OllamaError("PEdesk Guide local model is disabled.")

    base = ollama_base_url().rstrip("/")
    url = base + "/api/chat"
    payload = {
        "model": model or ollama_default_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=ollama_timeout_seconds()) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:  # noqa: BLE001
            detail = ""
        raise OllamaError(
            f"Ollama returned HTTP {exc.code} from {base}. {detail}".strip()
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise OllamaError(
            f"Ollama could not be reached at {base}."
        ) from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise OllamaError("Ollama returned a non-JSON response.") from exc

    content = (parsed.get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise OllamaError("Ollama response contained no message content.")
    return content


def embed_texts(texts: List[str], model: str) -> List[List[float]]:
    """Embed ``texts`` with a local Ollama embedding model.

    Tries the newer batch ``/api/embed`` first, falling back to the older
    per-text ``/api/embeddings``. Raises ``OllamaError`` on unreachable
    server, missing model, or malformed response. Does NOT gate on
    ``is_ollama_enabled`` — the RAG layer has its own enable flag and the
    index builder runs as a CLI.
    """
    if not texts:
        return []
    base = ollama_base_url().rstrip("/")

    # 1) batch /api/embed
    payload = json.dumps({"model": model, "input": list(texts)}).encode("utf-8")
    req = urllib.request.Request(
        base + "/api/embed", data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=ollama_timeout_seconds()) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
        embs = body.get("embeddings")
        if isinstance(embs, list) and len(embs) == len(texts):
            return [[float(x) for x in e] for e in embs]
    except urllib.error.HTTPError as exc:
        if exc.code not in (404, 400, 405):
            raise OllamaError(
                f"Ollama embed returned HTTP {exc.code} from {base}."
            ) from exc
        # else fall through to the legacy endpoint
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise OllamaError(f"Ollama could not be reached at {base}.") from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise OllamaError("Ollama embed returned a malformed response.") from exc

    # 2) legacy per-text /api/embeddings
    out: List[List[float]] = []
    for text in texts:
        p = json.dumps({"model": model, "prompt": text}).encode("utf-8")
        r = urllib.request.Request(
            base + "/api/embeddings", data=p, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(r, timeout=ollama_timeout_seconds()) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.HTTPError as exc:
            raise OllamaError(
                f"Ollama embed returned HTTP {exc.code} from {base}. "
                "Is the embedding model pulled (ollama pull "
                f"{model})?"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise OllamaError(f"Ollama could not be reached at {base}.") from exc
        emb = body.get("embedding")
        if not isinstance(emb, list) or not emb:
            raise OllamaError("Ollama embeddings response had no vector.")
        out.append([float(x) for x in emb])
    return out


def list_models() -> List[str]:
    """Return installed Ollama model names via GET /api/tags. [] on error."""
    url = ollama_base_url().rstrip("/") + "/api/tags"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=min(5, ollama_timeout_seconds())) as resp:
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
        return [m.get("name", "") for m in (body.get("models") or []) if m.get("name")]
    except Exception:  # noqa: BLE001 — diagnostics only, never throw
        return []
