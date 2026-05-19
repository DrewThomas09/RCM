"""Workspace mode — dual-purpose interface lexicon.

The platform serves two audiences from the same surfaces:

- ``partner``  — a PE fund partner running deals (the default; all
  legacy copy lives here so existing tests/contracts are unchanged).
- ``consulting`` — a Chartis-style PE healthcare *commercial diligence*
  consulting team running client engagements.

The mode is a per-request preference. The server reads the
``ck_workspace_mode`` cookie at the top of each request and calls
:func:`set_workspace_mode`; page renderers then call :func:`term` to
resolve audience-specific copy without threading a ``mode`` argument
through 145 render functions.

Why contextvars: ``ThreadingHTTPServer`` handles each request on its
own thread, and a fresh thread starts with an empty context, so a
``ContextVar`` set at request-start cannot leak across requests. We
set the value explicitly on every request regardless, so correctness
does not depend on thread-pool behavior.

This is intentionally a *copy-only* (L1) layer: it swaps vocabulary,
never page structure. Hiding/showing panels per mode (L2) would be a
separate, heavier change and is deliberately out of scope to avoid
introducing UI regressions.
"""
from __future__ import annotations

import contextvars
from typing import Dict

# Valid modes. ``partner`` is the default and maps to today's copy.
PARTNER = "partner"
CONSULTING = "consulting"
_VALID = (PARTNER, CONSULTING)

# Human labels for the toggle UI.
MODE_LABELS = {
    PARTNER: "PE Partner",
    CONSULTING: "Chartis Consulting",
}
MODE_TAGLINES = {
    PARTNER: "Fund-level deal operations",
    CONSULTING: "Commercial diligence for client engagements",
}

_mode: "contextvars.ContextVar[str]" = contextvars.ContextVar(
    "workspace_mode", default=PARTNER,
)


def set_workspace_mode(mode: str) -> str:
    """Set the current request's workspace mode. Returns the resolved
    mode (falls back to PARTNER for unknown values)."""
    resolved = mode if mode in _VALID else PARTNER
    _mode.set(resolved)
    return resolved


def current_workspace_mode() -> str:
    """Return the current request's workspace mode (PARTNER default)."""
    return _mode.get()


# ── Lexicon ─────────────────────────────────────────────────────────
# Key → {partner_copy, consulting_copy}. The partner column is
# byte-identical to today's strings so existing tests pass unchanged.
# Add keys here as more surfaces are converted; an unknown key falls
# back to the key itself (so a missing entry degrades to literal text
# rather than raising).
_TERMS: Dict[str, Dict[str, str]] = {
    # Core nouns
    "deal":            {PARTNER: "Deal",            CONSULTING: "Engagement"},
    "deal_lower":      {PARTNER: "deal",            CONSULTING: "engagement"},
    "deals":           {PARTNER: "Deals",           CONSULTING: "Engagements"},
    "deals_lower":     {PARTNER: "deals",           CONSULTING: "engagements"},
    "sponsor":         {PARTNER: "Sponsor",         CONSULTING: "Client"},
    "sponsor_lower":   {PARTNER: "sponsor",         CONSULTING: "client"},
    "portfolio":       {PARTNER: "Portfolio",       CONSULTING: "Engagement Book"},
    "deal_team":       {PARTNER: "Deal Team",       CONSULTING: "Engagement Team"},
    # Deliverables / surfaces
    "ic_memo":         {PARTNER: "IC Memo",         CONSULTING: "Diligence Readout"},
    "lp_update":       {PARTNER: "LP Update",       CONSULTING: "Client Briefing"},
    "deal_profile":    {PARTNER: "Deal Profile",    CONSULTING: "Target Profile"},
    # Workspace framing
    "workspace_kind":  {PARTNER: "Fund workspace",  CONSULTING: "Engagement workspace"},
    "open_workspace":  {PARTNER: "Open Deal Workspace",
                        CONSULTING: "Open Engagement"},
    # Audience descriptor (used in mode badge / settings)
    "audience":        {PARTNER: "PE partner & associates",
                        CONSULTING: "Commercial diligence consulting team"},
}


def term(key: str, mode: str | None = None) -> str:
    """Resolve a lexicon key to audience-specific copy.

    Falls back to the PARTNER value, then to the key itself, so a
    missing key degrades gracefully to literal text instead of raising.
    """
    entry = _TERMS.get(key)
    if entry is None:
        return key
    m = mode if mode in _VALID else current_workspace_mode()
    return entry.get(m) or entry.get(PARTNER) or key
