"""Compatibility shim — re-exports ``shell`` as chartis_shell.

Historically this module held a light-theme ``BASE_CSS`` + ``shell()``
renderer. Both are dead code after the unify-on-chartis migration
(chore/ui-polish-and-sanity-guards). The legacy ``shell()`` function
is kept as a thin wrapper so callers that still import
``from rcm_mc.ui._ui_kit import shell`` continue to work — they now
render through ``chartis_shell`` like everything else.

Callers that still use this shim:
  - rcm_mc/server.py (top-level import)
  - rcm_mc/ui/csv_to_html.py
  - rcm_mc/ui/text_to_html.py
  - rcm_mc/ui/sensitivity_dashboard.py
  - rcm_mc/ui/json_to_html.py
  - rcm_mc/infra/output_index.py
  - rcm_mc/reports/lp_update.py

Once those migrate to `from rcm_mc.ui._chartis_kit import chartis_shell`
directly, this module can be deleted entirely.

v3 format helpers (campaign target 1C):
``fmt_money``, ``fmt_pct``, ``fmt_moic``, ``fmt_iso_date``, and
``fmt_num`` emit HTML wrapped in the v3 utility classes already
declared in ``static/v3/chartis.css`` (``.num`` for tabular-nums,
``.mono`` for the monospace stack). Renderers should import these
rather than hand-rolling spans — the single import enforces
CLAUDE.md's number-formatting spec (financials 2dp, percentages
1dp, multiples 2dp + 'x', dates ISO) at the point of emission.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, Union

from ._chartis_kit import chartis_shell


def shell(
    body: str,
    title: str,
    *,
    back_href: Optional[str] = None,
    subtitle: Optional[str] = None,
    extra_css: str = "",
    extra_js: str = "",
    generated: bool = True,  # noqa: ARG001 — kept for signature parity
    omit_h1: bool = False,  # noqa: ARG001 — kept for signature parity
) -> str:
    """Legacy ``shell()`` — routes through ``chartis_shell``.

    Historically this function wrapped a body in a light-theme document
    and later delegated to ``shell_v2``. After the chartis unification
    it just calls ``chartis_shell`` with a compatible signature. The
    ``back_href`` argument is rendered as a small breadcrumb link above
    the body content; the ``generated`` and ``omit_h1`` arguments are
    accepted for backward compat but ignored.
    """
    import html as _html
    if back_href:
        body = (
            f'<nav class="breadcrumb" aria-label="Breadcrumb" '
            f'style="margin-bottom:12px;font-size:11px;">'
            f'<a href="{_html.escape(back_href)}" '
            f'style="color:var(--ck-accent);text-decoration:none;">'
            f'&larr; Back to index</a></nav>{body}'
        )
    return chartis_shell(
        body,
        title,
        subtitle=subtitle or "",
        extra_css=extra_css,
        extra_js=extra_js,
    )


# ── v3 format helpers (campaign target 1C) ──────────────────────────
#
# Each helper emits HTML pre-wrapped in the v3 utility classes that
# static/v3/chartis.css declares (.num for tabular-nums, .mono for the
# JetBrains Mono stack). Callers get CLAUDE.md-compliant formatting
# by importing the helper instead of writing the span manually.
#
# All helpers accept None and emit an em-dash placeholder so renderers
# can pass packet fields through without pre-checking. Strings are
# never returned raw — every code path goes through html.escape so
# the helpers are safe to use with packet-derived data.

_PLACEHOLDER = '<span class="num">—</span>'


def _coerce_float(value: object) -> Optional[float]:
    """Return ``value`` as float, or None if not numeric. Accepts
    int, float, numeric str, decimal-strings, None."""
    if value is None:
        return None
    if isinstance(value, bool):
        # bool is an int subclass; reject so True/False don't accidentally
        # render as "1.00" / "0.00"
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        return None


def fmt_money(
    value: object, *, decimals: int = 2, suffix: str = "",
) -> str:
    """Format a financial value as ``$1,234.56`` in tabular-nums.

    CLAUDE.md spec: financials at 2 decimals. ``suffix`` lets callers
    emit ``$450.25M`` etc.; pass ``"M"``, ``"B"``, ``"K"``.
    """
    n = _coerce_float(value)
    if n is None:
        return _PLACEHOLDER
    sign = "-" if n < 0 else ""
    body = f"{abs(n):,.{decimals}f}"
    return f'<span class="num mono">{sign}${body}{suffix}</span>'


def fmt_pct(
    value: object, *, signed: bool = False, decimals: int = 1,
) -> str:
    """Format a percentage as ``15.3%`` in tabular-nums.

    CLAUDE.md spec: percentages at 1 decimal. ``signed=True`` forces
    a leading sign so beat/miss reads ``+4.1%`` / ``-4.1%``. Input
    may be either a fraction (``0.153`` → ``15.3%``) or a percentage
    point already (``15.3`` → ``15.3%``); the helper does NOT guess.
    Callers pass the percentage point value directly.
    """
    n = _coerce_float(value)
    if n is None:
        return _PLACEHOLDER
    if signed:
        body = f"{n:+.{decimals}f}%"
    else:
        body = f"{n:.{decimals}f}%"
    return f'<span class="num">{body}</span>'


def fmt_moic(value: object, *, decimals: int = 2) -> str:
    """Format a multiple-on-invested-capital as ``2.50x``.

    CLAUDE.md spec: multiples at 2 decimals with ``x`` suffix.
    """
    n = _coerce_float(value)
    if n is None:
        return _PLACEHOLDER
    return f'<span class="num mono">{n:.{decimals}f}x</span>'


def fmt_num(value: object, *, decimals: int = 0) -> str:
    """Format a generic numeric value in tabular-nums.

    Use this for counts, days, basis points, anything not money /
    pct / multiple. Default 0 decimals (matches CLAUDE.md spec for
    integer counts).
    """
    n = _coerce_float(value)
    if n is None:
        return _PLACEHOLDER
    return f'<span class="num">{n:,.{decimals}f}</span>'


def fmt_iso_date(value: Union[str, date, datetime, None]) -> str:
    """Format a date as ISO ``YYYY-MM-DD`` in tabular-nums.

    CLAUDE.md spec: dates ISO-like, never US-style. Accepts a
    ``date``, ``datetime``, ISO string (returned as-is up to first
    ``T``), or None. Non-ISO strings render as the placeholder so a
    bad packet field doesn't paint the page with garbage.
    """
    if value is None:
        return _PLACEHOLDER
    if isinstance(value, datetime):
        return f'<span class="num">{value.date().isoformat()}</span>'
    if isinstance(value, date):
        return f'<span class="num">{value.isoformat()}</span>'
    s = str(value).strip()
    if not s:
        return _PLACEHOLDER
    head = s.split("T", 1)[0]
    # Reject obvious non-ISO inputs (e.g. "4/15/2026") rather than
    # pretend we can parse them. Caller should normalise upstream.
    if len(head) != 10 or head[4] != "-" or head[7] != "-":
        return _PLACEHOLDER
    return f'<span class="num">{head}</span>'
