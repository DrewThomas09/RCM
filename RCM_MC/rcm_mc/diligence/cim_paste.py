"""Heuristic CIM-text → field-dict extractor.

PROMPTS.md Phase 6 / Prompt 85: bankers send 50-page CIMs. Bridge
Audit / Thesis Pipeline / Deal MC each take 12-18 inputs that
overlap with the same five or six "key facts" in any CIM. This
module accepts pasted text and returns a dict of canonical fields
the form can pre-populate.

No LLM — regex against common CIM phrasings. Returns a partial
dict (keys present only when a confident match was found). Caller
merges into the form's defaults; the partner edits anything wrong
before submitting.

Public API::

    from rcm_mc.diligence.cim_paste import extract_from_cim
    fields = extract_from_cim(pasted_text)
"""
from __future__ import annotations

import re
from typing import Optional


_MONEY_SUFFIX_TO_MULTIPLIER = {
    "k": 1_000,
    "m": 1_000_000,
    "mm": 1_000_000,
    "b": 1_000_000_000,
    "bn": 1_000_000_000,
}


def _parse_money(s: str) -> Optional[float]:
    """Parse "$450M", "1.2bn", "67,500,000" → float USD."""
    s = s.strip().replace(",", "").replace("$", "").lower()
    m = re.match(r"^([0-9.]+)\s*(k|mm|m|bn|b)?$", s)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    suffix = m.group(2) or ""
    mult = _MONEY_SUFFIX_TO_MULTIPLIER.get(suffix, 1)
    return v * mult


def _parse_pct(s: str) -> Optional[float]:
    """Parse "45%", "0.45" → 0..1 fraction."""
    s = s.strip().rstrip("%")
    try:
        v = float(s)
    except ValueError:
        return None
    if v > 1:
        v = v / 100.0
    if 0 <= v <= 1:
        return v
    return None


_PATTERNS: list[tuple[str, str, callable]] = [
    # Money fields. Patterns search the *line* — each tuple is
    # (key, regex, parser). Order matters: the first match per
    # key wins.
    ("deal_name",
     r"^\s*(?:Project|Target|Company|Deal)[\s:]+([A-Z][\w &-]{2,60})\s*$",
     lambda s: s.strip().rstrip(".,")),
    ("revenue_year0_usd",
     r"(?:revenue|net revenue|total revenue|topline)[^\d]{0,20}"
     r"(\$?[\d,.]+\s*(?:k|mm|m|bn|b)?)",
     _parse_money),
    ("ebitda_year0_usd",
     r"(?:ebitda|adjusted ebitda)[^\d]{0,20}"
     r"(\$?[\d,.]+\s*(?:k|mm|m|bn|b)?)",
     _parse_money),
    ("enterprise_value_usd",
     r"(?:enterprise value|\bEV\b|\bTEV\b|purchase price)"
     r"[^\d]{0,20}"
     r"(\$?[\d,.]+\s*(?:k|mm|m|bn|b)?)",
     _parse_money),
    ("equity_check_usd",
     r"(?:equity (?:check|contribution|investment))[^\d]{0,20}"
     r"(\$?[\d,.]+\s*(?:k|mm|m|bn|b)?)",
     _parse_money),
    ("debt_usd",
     r"(?:debt(?:\s+(?:financing|component))?|leverage)[^\d]{0,20}"
     r"(\$?[\d,.]+\s*(?:k|mm|m|bn|b)?)",
     _parse_money),
    # Lease term in years.
    ("lease_term_years",
     r"(?:lease term|term)[^\d]{0,20}([0-9]{1,2})\s*(?:yr|year)",
     lambda s: int(s)),
    # Percentage fields.
    ("medicare_share",
     r"(?:medicare(?:\s+share)?|medicare mix)[^\d]{0,20}([0-9]+(?:\.[0-9]+)?\s*%?)",
     _parse_pct),
    ("commercial_share",
     r"(?:commercial(?:\s+share)?|commercial mix)[^\d]{0,20}([0-9]+(?:\.[0-9]+)?\s*%?)",
     _parse_pct),
    ("medicaid_share",
     r"(?:medicaid(?:\s+share)?|medicaid mix)[^\d]{0,20}([0-9]+(?:\.[0-9]+)?\s*%?)",
     _parse_pct),
]


def extract_from_cim(text: str) -> dict:
    """Return a dict of canonical fields parsed from ``text``.

    Keys present only when a confident regex match was found. The
    partner is expected to edit any wrong values before submit;
    this is a labour-saver, not a source-of-truth.
    """
    if not text:
        return {}
    out: dict = {}
    for key, pattern, parser in _PATTERNS:
        if key in out:
            continue
        m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if not m:
            continue
        try:
            value = parser(m.group(1))
        except (ValueError, TypeError):
            continue
        if value is None:
            continue
        out[key] = value
    return out
