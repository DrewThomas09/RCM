"""Strict read-only prompt builder for the local PEdesk Guide.

Turns a ``GuideContextPacket`` into a system prompt + a compacted
user prompt for a local model. The model is instructed to answer ONLY
from the supplied context and never to take actions. Nothing here calls
a model, mutates state, or runs diligence logic — it only formats text.
"""
from __future__ import annotations

import re
from typing import List

from .context.guide_context_packet import GuideContextPacket

# Visible chain-of-thought blocks some models emit; stripped before return.
_THINK_RE = re.compile(r"<think\b[^>]*>.*?</think\s*>", re.IGNORECASE | re.DOTALL)
_DANGLING_THINK_OPEN_RE = re.compile(r"<think\b[^>]*>.*\Z", re.IGNORECASE | re.DOTALL)
_REPETITIVE_PREAMBLE_RE = re.compile(
    r"^\s*(based on (the )?(provided |supplied |given )?context[,:]?\s*)",
    re.IGNORECASE,
)

_OMITTED_NOTE = "Some context was omitted for length."


def _bullets(items: List[str], limit: int = 0) -> str:
    vals = [str(i).strip() for i in (items or []) if str(i).strip()]
    if limit and len(vals) > limit:
        vals = vals[:limit] + ["… (trimmed)"]
    return "\n".join(f"- {v}" for v in vals) if vals else "- (none documented)"


def _policy_summary(packet: GuideContextPacket) -> str:
    pol = packet.read_only_policy or {}
    allowed = pol.get("allowed_behavior") or []
    disallowed = pol.get("disallowed_behavior") or []
    lines = [pol.get("identity", "PEdesk Guide is a read-only assistant.")]
    if allowed:
        lines.append("MAY: " + "; ".join(str(a) for a in allowed) + ".")
    if disallowed:
        lines.append("MUST NOT: " + "; ".join(str(d) for d in disallowed) + ".")
    if pol.get("default_uncertainty_message"):
        lines.append(
            "When unsure, say: \"" + str(pol["default_uncertainty_message"])
            + "\""
        )
    return "\n".join(lines)


def build_guide_system_prompt(packet: GuideContextPacket) -> str:
    """The behavioral contract + answer rules for the local model."""
    return (
        _policy_summary(packet)
        + "\n\n"
        "ANSWER RULES:\n"
        "1. Answer ONLY from the PEdesk Guide context provided in the user "
        "message. Do not use outside knowledge to fill gaps.\n"
        "2. If the context is insufficient, say so plainly — do not guess.\n"
        "3. Do not invent formulas. Do not invent data lineage or sources.\n"
        "4. Do not claim a page/number is IC-ready, validated, or real-time "
        "unless the context explicitly says so.\n"
        "5. Distinguish observed target data from estimates, benchmarks, "
        "demo/fixture data, and unknown data, exactly as the context labels "
        "them.\n"
        "6. You may explain pages, metrics, data sources, model intent, why a "
        "number matters, limitations, and related pages.\n"
        "7. You may NOT modify data, run models, change assumptions, create "
        "tasks, submit forms, send messages, create exports, or make final "
        "investment recommendations.\n"
        "8. Be concise and practical; use PE-diligence language but stay "
        "understandable.\n"
        "9. Do NOT expose chain-of-thought or internal reasoning. Do NOT emit "
        "<think> tags. Return only the final answer.\n\n"
        "When it fits the question, structure the answer as: What it means · "
        "Where it comes from · Why it matters · Caveats / limitations · "
        "Related PEdesk pages. Do not force this shape when it does not fit."
    )


def packet_to_prompt_context(
    packet: GuideContextPacket, max_chars: int = 12000
) -> str:
    """Render the packet into a compact context block for the prompt.

    Builds a full rendering first; if it exceeds ``max_chars`` it rebuilds
    a compact version (metric/source detail trimmed to labels) while always
    keeping limitations and missing_context_notes, and appends an omission
    note. A final hard truncation guards the cap.
    """
    full = _render_context(packet, compact=False)
    if len(full) <= max_chars:
        return full
    compact = _render_context(packet, compact=True)
    compact += "\n\n" + _OMITTED_NOTE
    if len(compact) > max_chars:
        compact = compact[: max_chars - len(_OMITTED_NOTE) - 2].rstrip() + (
            "\n" + _OMITTED_NOTE
        )
    return compact


def _render_context(packet: GuideContextPacket, compact: bool) -> str:
    pc = packet.page_context
    out: List[str] = []
    out.append("=== PEdesk Guide context ===")
    out.append(f"Route: {packet.normalized_route}")
    out.append(f"Context quality: {packet.context_quality}")
    if packet.fallback_message:
        out.append(f"Note: {packet.fallback_message}")

    if pc is not None:
        list_limit = 4 if compact else 0
        out.append(f"Page title: {pc.title}")
        out.append(f"Category: {pc.category.value}")
        out.append(f"Source confidence: {pc.source_confidence.value}")
        out.append(f"Data confidence: {pc.data_confidence.value}")
        out.append(f"Short description: {pc.short_description}")
        out.append(f"Primary purpose: {pc.primary_purpose}")
        out.append(f"Why it matters: {pc.why_it_matters}")
        if not compact:
            out.append("Inputs:\n" + _bullets(pc.inputs))
            out.append("Outputs:\n" + _bullets(pc.outputs))
        out.append("Key metrics:\n" + _bullets(pc.key_metrics, list_limit))
        out.append(
            "Interpretation guidance:\n" + _bullets(pc.interpretation_guidance)
        )
        # Limitations + missing notes are NEVER trimmed.
        out.append("Page limitations:\n" + _bullets(pc.limitations))
        out.append("Related PEdesk routes:\n" + _bullets(pc.related_routes,
                                                          list_limit))

    if packet.metric_contexts:
        out.append("--- Metric contexts ---")
        for m in packet.metric_contexts:
            if compact:
                out.append(f"- {m.label} ({m.metric_id})")
            else:
                out.append(
                    f"- {m.label} ({m.metric_id}): {m.definition} "
                    f"Formula: {m.formula} [{m.formula_confidence.value}]. "
                    f"Why it matters: {m.why_it_matters} "
                    f"Caveats: {'; '.join(m.caveats) if m.caveats else 'none'}"
                )

    if packet.data_source_contexts:
        out.append("--- Data source contexts ---")
        for s in packet.data_source_contexts:
            if compact:
                out.append(f"- {s.label} ({s.source_id})")
            else:
                out.append(
                    f"- {s.label} ({s.source_id}): {s.description} "
                    f"Type: {s.source_type.value}. Cadence: {s.update_cadence}; "
                    f"freshness lag: {s.freshness_lag}. "
                    f"Limitations: "
                    f"{'; '.join(s.limitations) if s.limitations else 'none'}"
                )

    # Always include — these carry the honesty of the answer.
    out.append("Known limitations:\n" + _bullets(packet.known_limitations))
    out.append(
        "Missing context notes:\n" + _bullets(packet.missing_context_notes)
    )
    return "\n".join(out)


def build_guide_user_prompt(question: str, packet: GuideContextPacket) -> str:
    """The context block + the user's question."""
    context = packet_to_prompt_context(packet)
    q = (question or "").strip()
    return (
        context
        + "\n\n=== Question ===\n"
        + q
        + "\n\nAnswer using only the context above. If it is not enough, say "
        "so."
    )


def clean_guide_answer(text: str) -> str:
    """Strip visible <think> blocks and tidy whitespace.

    Removes complete ``<think>...</think>`` blocks and any dangling
    unterminated ``<think>`` tail, trims a single repetitive
    "Based on the provided context" preamble, and collapses excess blank
    lines. Never removes substantive content/caveats.
    """
    if not text:
        return ""
    cleaned = _THINK_RE.sub("", text)
    cleaned = _DANGLING_THINK_OPEN_RE.sub("", cleaned)
    cleaned = _REPETITIVE_PREAMBLE_RE.sub("", cleaned, count=1)
    # Collapse 3+ newlines to a blank line; strip trailing spaces per line.
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
