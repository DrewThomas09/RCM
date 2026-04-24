"""Claude second-pass review for partner-review pages.

The goal is additive assurance, not a hard dependency. If Claude is not
configured or the call fails, the platform still renders the deterministic
review and supplemental healthcare checks.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .llm_client import LLMClient

_DEFAULT_MODEL = os.environ.get(
    "ANTHROPIC_PARTNER_REVIEW_MODEL",
    "claude-haiku-4-5-20251001",
)

_SYSTEM_PROMPT = (
    "You are Claude performing a second-pass review of a healthcare PE revenue-"
    "cycle diligence verdict. Use only the supplied payload. Do not invent data, "
    "benchmarks, or numbers. Return strict JSON with keys: "
    "status, summary, confirmed_points, concerns. "
    "Valid status values: confirmed, needs_attention, insufficient_support."
)


def _compact_band_checks(checks: Any, limit: int = 6) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for chk in list(checks or [])[:limit]:
        rows.append({
            "metric": getattr(chk, "metric", None),
            "verdict": getattr(chk, "verdict", None),
            "observed": getattr(chk, "observed", None),
            "partner_note": getattr(chk, "partner_note", None),
        })
    return rows


def _compact_hits(hits: Any, limit: int = 6) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for hit in list(hits or [])[:limit]:
        if isinstance(hit, dict):
            rows.append({
                "id": hit.get("id"),
                "severity": hit.get("severity"),
                "category": hit.get("category"),
                "title": hit.get("title"),
                "finding": hit.get("finding"),
            })
            continue
        rows.append({
            "id": getattr(hit, "id", None),
            "severity": getattr(hit, "severity", None),
            "category": getattr(hit, "category", None),
            "title": getattr(hit, "title", None),
            "finding": getattr(hit, "finding", None),
        })
    return rows


def _review_payload(review: Any) -> Dict[str, Any]:
    healthcare = getattr(review, "healthcare_checks", None) or {}
    return {
        "deal_id": getattr(review, "deal_id", ""),
        "deal_name": getattr(review, "deal_name", ""),
        "recommendation": getattr(getattr(review, "narrative", None), "recommendation", ""),
        "headline": getattr(getattr(review, "narrative", None), "headline", ""),
        "recommendation_rationale": getattr(
            getattr(review, "narrative", None), "recommendation_rationale", "",
        ),
        "context_summary": getattr(review, "context_summary", None) or {},
        "reasonableness_checks": _compact_band_checks(
            getattr(review, "reasonableness_checks", None),
        ),
        "heuristic_hits": _compact_hits(getattr(review, "heuristic_hits", None)),
        "healthcare_checks": {
            "summary": healthcare.get("summary", ""),
            "total_hits": healthcare.get("total_hits", 0),
            "severity_counts": healthcare.get("severity_counts", {}),
            "focus_areas": healthcare.get("focus_areas", []),
            "hits": _compact_hits(healthcare.get("hits", [])),
        },
    }


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return None
    candidates = [raw]
    if "```" in raw:
        parts = [p.strip() for p in raw.split("```") if p.strip()]
        candidates.extend(parts)
    for candidate in candidates:
        if candidate.startswith("json"):
            candidate = candidate[4:].strip()
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def build_claude_review(
    review: Any,
    *,
    llm_client: Optional[LLMClient] = None,
    store: Any = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a JSON-safe Claude review payload for the UI."""
    client = llm_client or LLMClient(store=store)
    selected_model = model or _DEFAULT_MODEL
    if not client.is_configured:
        return {
            "reviewer": "claude",
            "status": "not_configured",
            "summary": (
                "Claude is not configured. Deterministic healthcare checks "
                "are still rendered below."
            ),
            "confirmed_points": [],
            "concerns": [],
            "model": "fallback",
            "latency_ms": 0.0,
            "cost_usd_estimate": 0.0,
        }

    payload = _review_payload(review)
    user_prompt = (
        "Claude, look at this partner-review payload and confirm whether the "
        "verdict is supported by the supplied evidence.\n\n"
        + json.dumps(payload, indent=2, default=str)
    )
    resp = client.complete(
        _SYSTEM_PROMPT,
        user_prompt,
        model=selected_model,
        max_tokens=700,
        temperature=0.1,
    )
    parsed = _extract_json(resp.text)
    if parsed is None:
        summary = (resp.text or "").strip() or "Claude did not return a parseable review."
        if summary == "[LLM call failed]":
            status = "call_failed"
            summary = (
                "Claude review call failed. Deterministic healthcare checks are "
                "still available."
            )
        else:
            status = "needs_attention"
        return {
            "reviewer": "claude",
            "status": status,
            "summary": summary[:800],
            "confirmed_points": [],
            "concerns": [],
            "model": resp.model,
            "latency_ms": resp.latency_ms,
            "cost_usd_estimate": resp.cost_usd_estimate,
        }

    status = str(parsed.get("status") or "needs_attention").strip() or "needs_attention"
    return {
        "reviewer": "claude",
        "status": status,
        "summary": str(parsed.get("summary") or "").strip(),
        "confirmed_points": [
            str(x).strip() for x in list(parsed.get("confirmed_points") or []) if str(x).strip()
        ][:4],
        "concerns": [
            str(x).strip() for x in list(parsed.get("concerns") or []) if str(x).strip()
        ][:4],
        "model": resp.model,
        "latency_ms": resp.latency_ms,
        "cost_usd_estimate": resp.cost_usd_estimate,
    }
