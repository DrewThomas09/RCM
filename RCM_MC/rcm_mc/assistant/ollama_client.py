"""Local Ollama HTTP client for the read-only PEdesk Guide.

Stdlib ``urllib`` only — no third-party HTTP dependency (matching
``rcm_mc/ai/llm_client.py``). Ollama is treated as *optional acceleration*:
when it is disabled or unreachable, callers get a typed ``OllamaError``
rather than a crash, so the Guide endpoint can return a clean 503.

Built to work across environments (local dev, a Tailscale-reachable box, a
container) without code change, and to ride out a slow first call:

  PEDESK_GUIDE_OLLAMA_ENABLED          true/false  (default: DISABLED)
  PEDESK_GUIDE_OLLAMA_BASE_URL         default http://localhost:11434
                                       (may be a COMMA-SEPARATED list of hosts
                                        tried in order with failover)
  OLLAMA_HOST                          the standard Ollama env var — also
                                       honoured, so a normal Ollama install
                                       works with no PEdesk-specific config
  PEDESK_GUIDE_OLLAMA_MODEL            default gemma4:e4b
  PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS  default 30
  PEDESK_GUIDE_OLLAMA_RETRIES          transient-error retries per host
                                       (default 2 — the first call after a
                                        model load is often slow)
  PEDESK_GUIDE_OLLAMA_NUM_CTX          context window override (e.g. 8192) so
                                       large page contexts fit
  PEDESK_GUIDE_OLLAMA_KEEP_ALIVE       how long Ollama keeps the model warm
                                       (default "5m") — faster repeat calls

Default-disabled is deliberate: production / unknown environments make no
model calls unless someone explicitly opts in.

This module is read-only: it sends chat/embedding requests and returns data.
It never writes to disk, never touches the portfolio store, and performs no
diligence computation.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, List, Optional, Tuple

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e4b"
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_RETRIES = 2
DEFAULT_KEEP_ALIVE = "5m"


class OllamaError(RuntimeError):
    """Raised when Ollama is disabled, unreachable, or errors."""


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    val = (os.environ.get(name) or "").strip()
    return val or default


def _normalize_host(raw: str) -> str:
    """Trim, strip a trailing slash, and add http:// if no scheme is given."""
    h = (raw or "").strip().rstrip("/")
    if not h:
        return ""
    if not h.startswith(("http://", "https://")):
        h = "http://" + h
    return h


def ollama_base_urls() -> List[str]:
    """Ordered, de-duplicated list of candidate Ollama hosts to try.

    Priority: PEDESK_GUIDE_OLLAMA_BASE_URL (comma-separated allowed) → the
    standard OLLAMA_HOST → the localhost default. This lets the same build
    reach Ollama wherever it lives (local, Tailscale, sidecar) with failover,
    and works out-of-the-box for a normal Ollama install via OLLAMA_HOST.
    """
    urls: List[str] = []
    for src in (_env("PEDESK_GUIDE_OLLAMA_BASE_URL"), _env("OLLAMA_HOST")):
        if not src:
            continue
        for part in src.split(","):
            u = _normalize_host(part)
            if u and u not in urls:
                urls.append(u)
    default = _normalize_host(DEFAULT_BASE_URL)
    if default not in urls:
        urls.append(default)
    return urls


def ollama_base_url() -> str:
    """The primary host (first candidate). Back-compat for older callers."""
    return ollama_base_urls()[0]


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


def ollama_max_retries() -> int:
    raw = _env("PEDESK_GUIDE_OLLAMA_RETRIES")
    if not raw:
        return DEFAULT_RETRIES
    try:
        return max(0, min(5, int(raw)))
    except ValueError:
        return DEFAULT_RETRIES


def ollama_num_ctx() -> Optional[int]:
    raw = _env("PEDESK_GUIDE_OLLAMA_NUM_CTX")
    if not raw:
        return None
    try:
        n = int(raw)
        return n if n > 0 else None
    except ValueError:
        return None


def ollama_keep_alive() -> str:
    return _env("PEDESK_GUIDE_OLLAMA_KEEP_ALIVE", DEFAULT_KEEP_ALIVE) or DEFAULT_KEEP_ALIVE


def is_ollama_enabled() -> bool:
    """True only when PEDESK_GUIDE_OLLAMA_ENABLED is explicitly truthy."""
    return (_env("PEDESK_GUIDE_OLLAMA_ENABLED", "") or "").lower() in (
        "1", "true", "yes", "on",
    )


def _request_json(
    path: str,
    payload: Optional[dict] = None,
    *,
    method: str = "POST",
    timeout: Optional[int] = None,
    retries: Optional[int] = None,
) -> Tuple[str, Any]:
    """Try every configured host until one answers; return (base_used, json).

    Per host, transient connection errors are retried with a short backoff
    (the first call after a model load is often slow); an HTTP error from a
    responding server moves on to the next host. Raises ``OllamaError`` only
    when every candidate host has failed, with an aggregated reason.
    """
    timeout = ollama_timeout_seconds() if timeout is None else timeout
    retries = ollama_max_retries() if retries is None else retries
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    errors: List[str] = []

    for base in ollama_base_urls():
        url = base + path
        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(
                    url, data=data, method=method, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw = resp.read().decode("utf-8", errors="replace")
                try:
                    return base, json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise OllamaError(
                        f"Ollama at {base} returned a non-JSON response."
                    ) from exc
            except urllib.error.HTTPError as exc:
                try:
                    detail = exc.read().decode("utf-8", errors="replace")[:300]
                except Exception:  # noqa: BLE001
                    detail = ""
                errors.append(f"{base}: HTTP {exc.code} {detail}".strip())
                break  # server responded with an error — try the next host
            except (urllib.error.URLError, TimeoutError, OSError):
                errors.append(f"{base}: unreachable")
                if attempt < retries:
                    time.sleep(min(2.0, 0.4 * (attempt + 1)))
                    continue
                break  # retries exhausted — try the next host

    if errors:
        raise OllamaError("Ollama unavailable — tried " + "; ".join(errors))
    raise OllamaError("No Ollama host configured.")


def check_ollama_health() -> bool:
    """True if ANY configured Ollama host answers GET /api/tags. Never raises."""
    t = min(5, ollama_timeout_seconds())
    for base in ollama_base_urls():
        try:
            req = urllib.request.Request(base + "/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=t) as resp:
                if 200 <= resp.status < 300:
                    return True
        except Exception:  # noqa: BLE001 — health check must never throw
            continue
    return False


def call_ollama_chat(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
) -> str:
    """POST /api/chat to a reachable Ollama host; return the message text.

    Tries every configured host with retries/backoff and failover. Raises
    ``OllamaError`` when disabled or when no host can serve the request, never
    leaking a raw stack trace to the caller.
    """
    if not is_ollama_enabled():
        raise OllamaError("PEdesk Guide local model is disabled.")

    options: dict = {"temperature": temperature}
    num_ctx = ollama_num_ctx()
    if num_ctx:
        options["num_ctx"] = num_ctx
    payload = {
        "model": model or ollama_default_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": options,
        "keep_alive": ollama_keep_alive(),
    }
    _, parsed = _request_json("/api/chat", payload)
    content = (parsed.get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise OllamaError("Ollama response contained no message content.")
    return content


def embed_texts(texts: List[str], model: str) -> List[List[float]]:
    """Embed ``texts`` with a local Ollama embedding model.

    Tries the newer batch ``/api/embed`` first (across all hosts), falling
    back to the older per-text ``/api/embeddings``. Raises ``OllamaError`` when
    no host can serve the request or the response is malformed. Does NOT gate
    on ``is_ollama_enabled`` — the RAG layer has its own enable flag and the
    index builder runs as a CLI.
    """
    if not texts:
        return []

    # 1) batch /api/embed (with host failover). Any failure here (404 on an
    #    older Ollama, or a transient miss) falls through to the legacy path.
    try:
        _, body = _request_json("/api/embed", {"model": model, "input": list(texts)})
        embs = body.get("embeddings")
        if isinstance(embs, list) and len(embs) == len(texts):
            return [[float(x) for x in e] for e in embs]
    except OllamaError:
        pass  # fall back to the legacy per-text endpoint

    # 2) legacy per-text /api/embeddings (with host failover per text).
    out: List[List[float]] = []
    for text in texts:
        try:
            _, body = _request_json(
                "/api/embeddings", {"model": model, "prompt": text})
        except OllamaError as exc:
            raise OllamaError(
                f"{exc} — is the embedding model pulled (ollama pull {model})?"
            ) from exc
        emb = body.get("embedding")
        if not isinstance(emb, list) or not emb:
            raise OllamaError("Ollama embeddings response had no vector.")
        out.append([float(x) for x in emb])
    return out


def list_models() -> List[str]:
    """Installed model names from the first reachable host. [] on error."""
    t = min(5, ollama_timeout_seconds())
    for base in ollama_base_urls():
        try:
            req = urllib.request.Request(base + "/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=t) as resp:
                body = json.loads(resp.read().decode("utf-8", errors="replace"))
            names = [m.get("name", "")
                     for m in (body.get("models") or []) if m.get("name")]
            if names:
                return names
        except Exception:  # noqa: BLE001 — diagnostics only, never throw
            continue
    return []


def ollama_status() -> dict:
    """Best-effort diagnostic snapshot for operators / the settings page.

    Never raises. Reports config + which host (if any) is reachable and what
    models it has — useful when wiring Ollama up in a new environment.
    """
    hosts = ollama_base_urls()
    reachable = ""
    t = min(5, ollama_timeout_seconds())
    for base in hosts:
        try:
            req = urllib.request.Request(base + "/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=t) as resp:
                if 200 <= resp.status < 300:
                    reachable = base
                    break
        except Exception:  # noqa: BLE001
            continue
    return {
        "enabled": is_ollama_enabled(),
        "hosts": hosts,
        "reachable_host": reachable,
        "healthy": bool(reachable),
        "model": ollama_default_model(),
        "models": list_models() if reachable else [],
        "num_ctx": ollama_num_ctx(),
        "keep_alive": ollama_keep_alive(),
        "timeout_seconds": ollama_timeout_seconds(),
        "retries": ollama_max_retries(),
    }
