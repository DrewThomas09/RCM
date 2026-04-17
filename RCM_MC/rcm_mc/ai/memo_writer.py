"""LLM-assisted memo composition with fact-checking (Prompt 71 continued).

When ``use_llm=False`` (the default), ``compose_memo`` produces
template-based sections from the packet — same content as the existing
``packet_renderer`` path. No regression.

When ``use_llm=True``, the writer builds section-specific prompts with
packet data, calls the LLM, then fact-checks every dollar amount and
percentage in the generated text against the packet. Numbers that do
not appear in the packet (within 1 % tolerance) are flagged as
warnings so the partner can review before sending.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .llm_client import LLMClient, LLMResponse

# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class SectionDraft:
    text: str
    cited_fields: list[str] = field(default_factory=list)
    fact_checks_passed: bool = True


@dataclass
class ComposedMemo:
    sections: dict[str, SectionDraft] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    fact_check_warnings: list[str] = field(default_factory=list)


# ── Number extraction ────────────────────────────────────────────────

_DOLLAR_RE = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?)\s*([MBKmk])?",
)
_PCT_RE = re.compile(
    r"([\d,]+(?:\.\d+)?)\s*%",
)


def _extract_numbers(text: str) -> list[float]:
    """Find dollar amounts and percentages in *text*.

    Dollar amounts are normalised to raw floats (e.g. ``$4.5M`` -> 4500000).
    Percentages are kept as-is (e.g. ``15.3%`` -> 15.3).
    """
    results: list[float] = []
    for m in _DOLLAR_RE.finditer(text):
        raw = float(m.group(1).replace(",", ""))
        suffix = (m.group(2) or "").upper()
        if suffix == "M":
            raw *= 1_000_000
        elif suffix == "B":
            raw *= 1_000_000_000
        elif suffix == "K":
            raw *= 1_000
        results.append(raw)
    for m in _PCT_RE.finditer(text):
        results.append(float(m.group(1).replace(",", "")))
    return results


# ── Packet value extraction ──────────────────────────────────────────

def _packet_numbers(packet: Any) -> list[float]:
    """Recursively collect all numeric values from a packet."""
    nums: list[float] = []

    def _walk(obj: Any) -> None:
        if obj is None:
            return
        if isinstance(obj, (int, float)):
            if math.isfinite(obj):
                nums.append(float(obj))
            return
        if isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
            return
        if isinstance(obj, (list, tuple)):
            for item in obj:
                _walk(item)
            return
        # Dataclass-like objects
        if hasattr(obj, "__dataclass_fields__"):
            for fname in obj.__dataclass_fields__:
                _walk(getattr(obj, fname, None))
            return
        # Fallback: try __dict__
        if hasattr(obj, "__dict__"):
            for v in obj.__dict__.values():
                _walk(v)

    _walk(packet)
    return nums


def _fact_check(numbers: list[float], packet: Any) -> list[str]:
    """Return warnings for numbers in LLM text not found in the packet.

    A number "matches" if some packet value is within 1 % relative
    tolerance (or absolute tolerance of 0.01 for values near zero).
    """
    packet_nums = _packet_numbers(packet)
    warnings: list[str] = []
    for n in numbers:
        found = False
        for pn in packet_nums:
            if abs(pn) < 0.01 and abs(n) < 0.01:
                found = True
                break
            if abs(pn) > 0:
                if abs(n - pn) / abs(pn) <= 0.01:
                    found = True
                    break
        if not found:
            warnings.append(f"Number {n} not found in packet data (possible hallucination)")
    return warnings


# ── Template-based sections ──────────────────────────────────────────

_DEFAULT_SECTIONS = [
    "executive_summary",
    "rcm_performance",
    "ebitda_bridge",
    "risk_flags",
    "diligence_questions",
]


def _template_section(packet: Any, section_name: str) -> SectionDraft:
    """Build a section from packet data using simple templates."""
    deal_name = getattr(packet, "deal_name", None) or getattr(packet, "deal_id", "Unknown Deal")
    deal_id = getattr(packet, "deal_id", "unknown")

    if section_name == "executive_summary":
        text = f"Diligence analysis for {deal_name} (ID: {deal_id})."
        grade = getattr(getattr(packet, "completeness", None), "grade", None)
        if grade:
            text += f" Data completeness grade: {grade}."
        return SectionDraft(text=text, cited_fields=["deal_name", "deal_id", "completeness"])

    if section_name == "rcm_performance":
        om = getattr(packet, "observed_metrics", None) or {}
        lines = [f"RCM Performance for {deal_name}:"]
        cited = ["deal_name"]
        if isinstance(om, dict):
            for key, metric in om.items():
                val = getattr(metric, "value", metric) if not isinstance(metric, (int, float)) else metric
                lines.append(f"  - {key}: {val}")
                cited.append(f"observed_metrics.{key}")
        return SectionDraft(text="\n".join(lines), cited_fields=cited)

    if section_name == "ebitda_bridge":
        bridge = getattr(packet, "ebitda_bridge", None)
        if bridge is None:
            return SectionDraft(text="EBITDA bridge data not available.", cited_fields=[])
        total = getattr(bridge, "total_ebitda_impact", None)
        text = f"EBITDA Bridge: total impact ${total:,.2f}" if total else "EBITDA bridge computed."
        return SectionDraft(text=text, cited_fields=["ebitda_bridge"])

    if section_name == "risk_flags":
        flags = getattr(packet, "risk_flags", None) or []
        if not flags:
            return SectionDraft(text="No risk flags identified.", cited_fields=["risk_flags"])
        lines = ["Risk Flags:"]
        for rf in flags:
            label = getattr(rf, "label", str(rf))
            lines.append(f"  - {label}")
        return SectionDraft(text="\n".join(lines), cited_fields=["risk_flags"])

    if section_name == "diligence_questions":
        qs = getattr(packet, "diligence_questions", None) or []
        if not qs:
            return SectionDraft(text="No diligence questions generated.", cited_fields=[])
        lines = ["Diligence Questions:"]
        for q in qs:
            qtext = getattr(q, "question", str(q))
            lines.append(f"  - {qtext}")
        return SectionDraft(text="\n".join(lines), cited_fields=["diligence_questions"])

    return SectionDraft(text=f"[Section '{section_name}' not implemented]", cited_fields=[])


# ── LLM-based sections ──────────────────────────────────────────────

_SECTION_PROMPTS: dict[str, str] = {
    "executive_summary": (
        "Write a concise executive summary for a healthcare PE diligence memo. "
        "Cover the deal overview, key metrics, and recommendation. "
        "Use only the data provided — do not invent numbers."
    ),
    "rcm_performance": (
        "Summarise the RCM performance metrics for this deal. "
        "Highlight any concerning trends. Use only the data provided."
    ),
    "ebitda_bridge": (
        "Describe the EBITDA bridge analysis. "
        "Explain each lever's contribution. Use only the data provided."
    ),
    "risk_flags": (
        "List and explain the risk flags for this deal. "
        "Prioritise by severity. Use only the data provided."
    ),
    "diligence_questions": (
        "Generate follow-up diligence questions based on the analysis. "
        "Focus on areas of uncertainty. Use only the data provided."
    ),
}


def _build_user_prompt(packet: Any, section_name: str) -> str:
    """Serialise packet data relevant to a section into a user prompt."""
    # We serialise the whole packet as JSON for the LLM
    to_json = getattr(packet, "to_json", None)
    if to_json:
        packet_str = to_json(indent=2)
    else:
        packet_str = str(packet)
    return f"Deal data:\n{packet_str}\n\nSection: {section_name}"


def _llm_section(
    client: LLMClient,
    packet: Any,
    section_name: str,
) -> tuple[SectionDraft, float]:
    """Generate one section via LLM and fact-check it."""
    system_prompt = _SECTION_PROMPTS.get(
        section_name,
        "Write this section of a healthcare PE diligence memo. Use only provided data.",
    )
    user_prompt = _build_user_prompt(packet, section_name)
    resp = client.complete(system_prompt, user_prompt)

    numbers = _extract_numbers(resp.text)
    warnings = _fact_check(numbers, packet)
    passed = len(warnings) == 0

    draft = SectionDraft(
        text=resp.text,
        cited_fields=[],
        fact_checks_passed=passed,
    )
    return draft, resp.cost_usd_estimate


# ── Public API ───────────────────────────────────────────────────────

def compose_memo(
    packet: Any,
    *,
    sections: Optional[list[str]] = None,
    use_llm: bool = False,
    llm_client: Optional[LLMClient] = None,
) -> ComposedMemo:
    """Compose a diligence memo from a packet.

    When *use_llm* is ``False`` (default), returns template-based sections
    built purely from packet data — zero LLM calls, zero cost, zero
    regression risk.

    When *use_llm* is ``True``, builds prompts per section, calls the LLM,
    and fact-checks every number in the output against the packet.
    """
    section_names = sections or list(_DEFAULT_SECTIONS)
    memo = ComposedMemo()

    if not use_llm:
        for name in section_names:
            memo.sections[name] = _template_section(packet, name)
        return memo

    client = llm_client or LLMClient()
    if not client.is_configured:
        # Fall back to templates when no key
        for name in section_names:
            memo.sections[name] = _template_section(packet, name)
        return memo

    total_cost = 0.0
    all_warnings: list[str] = []

    for name in section_names:
        draft, cost = _llm_section(client, packet, name)
        memo.sections[name] = draft
        total_cost += cost
        if not draft.fact_checks_passed:
            numbers = _extract_numbers(draft.text)
            section_warnings = _fact_check(numbers, packet)
            all_warnings.extend(
                f"[{name}] {w}" for w in section_warnings
            )

    memo.total_cost_usd = total_cost
    memo.fact_check_warnings = all_warnings
    return memo
