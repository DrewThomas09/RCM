"""Conversational interface wrapping the LLM with tool definitions (Prompt 72).

Partners can ask natural-language questions about the portfolio and
the engine dispatches to existing platform functions (deal query,
packet loading, portfolio stats) via tool-calling. Multi-turn context
is persisted in a SQLite ``conversation_sessions`` table.

When the LLM is not configured the engine returns a helpful fallback
directing the partner to the query interface.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .llm_client import LLMClient, LLMResponse

logger = logging.getLogger(__name__)

_FALLBACK_MSG = "LLM not configured — use the query interface at /screen instead."

# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class ConversationResponse:
    answer_text: str
    tool_calls_made: list[str] = field(default_factory=list)
    cited_deals: list[str] = field(default_factory=list)


# ── SQLite session persistence ───────────────────────────────────────

def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS conversation_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_conv_session "
            "ON conversation_sessions(session_id, created_at)"
        )
        con.commit()


def _load_history(store: Any, session_id: str, limit: int = 20) -> list[dict[str, str]]:
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT role, content FROM conversation_sessions "
            "WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    # Reverse to chronological order
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def _save_message(store: Any, session_id: str, role: str, content: str) -> None:
    _ensure_table(store)
    with store.connect() as con:
        con.execute(
            "INSERT INTO conversation_sessions (session_id, role, content, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.now(timezone.utc).isoformat()),
        )
        con.commit()


# ── Tool definitions ─────────────────────────────────────────────────

def _tool_find_deals(store: Any, filters: dict[str, Any]) -> str:
    """Search deals matching filter criteria."""
    try:
        from ..analysis.deal_query import parse_query, execute_query
        query_str = filters.get("query", "")
        if not query_str:
            # Build query from individual filters
            parts = []
            for k, v in filters.items():
                if k != "query":
                    parts.append(f"{k} = {v}")
            query_str = " and ".join(parts) if parts else ""
        if not query_str:
            return json.dumps({"deals": [], "message": "No filters provided"})
        parsed = parse_query(query_str)
        results = execute_query(store, parsed)
        return json.dumps({
            "deals": [r.to_dict() for r in results],
            "count": len(results),
        })
    except Exception as exc:
        logger.warning("find_deals tool error: %s", exc)
        return json.dumps({"error": str(exc), "deals": []})


def _tool_load_packet_summary(store: Any, deal_id: str) -> str:
    """Load packet summary for a specific deal."""
    try:
        from ..analysis.analysis_store import load_latest_packet
        packet = load_latest_packet(store, deal_id)
        if packet is None:
            return json.dumps({"error": f"No packet found for deal {deal_id}"})
        summary = {
            "deal_id": packet.deal_id,
            "deal_name": getattr(packet, "deal_name", None),
            "model_version": getattr(packet, "model_version", None),
            "generated_at": str(getattr(packet, "generated_at", "")),
        }
        # Include completeness if available
        comp = getattr(packet, "completeness", None)
        if comp:
            summary["completeness_grade"] = getattr(comp, "grade", None)
        return json.dumps(summary)
    except Exception as exc:
        logger.warning("load_packet_summary tool error: %s", exc)
        return json.dumps({"error": str(exc)})


def _tool_get_portfolio_stats(store: Any) -> str:
    """Get aggregate portfolio statistics."""
    try:
        from ..analysis.analysis_store import list_packets
        rows = list_packets(store)
        deal_ids = set()
        for r in rows:
            did = r.get("deal_id", "")
            if did:
                deal_ids.add(did)
        return json.dumps({
            "total_deals": len(deal_ids),
            "total_analysis_runs": len(rows),
        })
    except Exception as exc:
        logger.warning("get_portfolio_stats tool error: %s", exc)
        return json.dumps({"error": str(exc)})


_TOOLS = {
    "find_deals": _tool_find_deals,
    "load_packet_summary": _tool_load_packet_summary,
    "get_portfolio_stats": _tool_get_portfolio_stats,
}

_TOOL_DESCRIPTIONS = [
    {
        "name": "find_deals",
        "description": "Search for deals matching filter criteria (e.g. state, denial rate, beds)",
        "parameters": {"query": "string — filter expression like 'state = IL and denial rate > 10'"},
    },
    {
        "name": "load_packet_summary",
        "description": "Load the analysis packet summary for a specific deal",
        "parameters": {"deal_id": "string — the deal identifier"},
    },
    {
        "name": "get_portfolio_stats",
        "description": "Get aggregate portfolio statistics (deal count, run count)",
        "parameters": {},
    },
]

_SYSTEM_PROMPT = (
    "You are an RCM analytics assistant for healthcare PE diligence. "
    "You have access to tools that query the portfolio database. "
    "Use them to answer partner questions accurately. "
    "Always cite the deal IDs you reference.\n\n"
    "Available tools:\n" + json.dumps(_TOOL_DESCRIPTIONS, indent=2)
)


# ── Engine ───────────────────────────────────────────────────────────

class ConversationEngine:
    """Multi-turn conversational interface backed by LLM + tool dispatch."""

    def __init__(self, store: Any, llm_client: Optional[LLMClient] = None) -> None:
        self._store = store
        self._client = llm_client or LLMClient(store=store)

    def process_message(
        self,
        session_id: str,
        user_message: str,
        store: Optional[Any] = None,
    ) -> ConversationResponse:
        """Process a user message in the given session.

        When the LLM is not configured, returns a fallback message
        directing the partner to the query interface.
        """
        effective_store = store or self._store

        if not self._client.is_configured:
            return ConversationResponse(answer_text=_FALLBACK_MSG)

        # Save user message
        _save_message(effective_store, session_id, "user", user_message)

        # Build context from history
        history = _load_history(effective_store, session_id)
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in history
        )
        user_prompt = f"Conversation so far:\n{history_text}\n\nUser: {user_message}"

        # Detect tool calls from user intent
        tool_calls_made: list[str] = []
        cited_deals: list[str] = []
        tool_context = ""

        # Simple intent detection — dispatch tools before calling LLM
        lower_msg = user_message.lower()
        if any(kw in lower_msg for kw in ["find", "search", "filter", "show deals", "which deals"]):
            result = _tool_find_deals(effective_store, {"query": user_message})
            tool_calls_made.append("find_deals")
            tool_context += f"\nTool result (find_deals): {result}"
            try:
                data = json.loads(result)
                for d in data.get("deals", []):
                    if "deal_id" in d:
                        cited_deals.append(d["deal_id"])
            except (json.JSONDecodeError, KeyError):
                pass

        if any(kw in lower_msg for kw in ["portfolio", "stats", "how many", "total"]):
            result = _tool_get_portfolio_stats(effective_store)
            tool_calls_made.append("get_portfolio_stats")
            tool_context += f"\nTool result (get_portfolio_stats): {result}"

        if "deal" in lower_msg and any(kw in lower_msg for kw in ["detail", "summary", "packet", "load"]):
            # Try to extract deal_id from message
            import re
            deal_match = re.search(r"deal[_\s-]*(?:id[:\s]*)?([A-Za-z0-9_-]+)", user_message, re.IGNORECASE)
            if deal_match:
                deal_id = deal_match.group(1)
                result = _tool_load_packet_summary(effective_store, deal_id)
                tool_calls_made.append("load_packet_summary")
                tool_context += f"\nTool result (load_packet_summary): {result}"
                cited_deals.append(deal_id)

        # Call LLM with tool context
        full_prompt = user_prompt
        if tool_context:
            full_prompt += f"\n\nTool results:\n{tool_context}"

        resp = self._client.complete(_SYSTEM_PROMPT, full_prompt)

        # Save assistant response
        _save_message(effective_store, session_id, "assistant", resp.text)

        return ConversationResponse(
            answer_text=resp.text,
            tool_calls_made=tool_calls_made,
            cited_deals=cited_deals,
        )
