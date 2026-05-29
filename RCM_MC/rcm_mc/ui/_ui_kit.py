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


# Editorial overlay for legacy shell()-routed pages.
#
# 26 routes in server.py (alerts, owners, cohorts, deadlines, audit,
# runs, ops, …) render their bodies with legacy markup:
#   - `<div class="card">` — picks up the LOGIN-card CSS (max-width
#     520px, auto-centered) on dashboard-style pages, looks wrong
#   - raw `<table>` — no class → no editorial typography, inherits
#     Source Serif from the page body
#   - `<h2>` direct headings inside cards — wrong size/letter-spacing
#     relative to editorial ck_section_header
#
# Refactoring each route into ck_panel + ck-table is ~26 PRs of
# mechanical work. Single CSS overlay below catches them all in one
# place — scoped to `.ck-main .card` (the chartis_shell main column)
# so it doesn't bleed into actual login/forgot card surfaces (which
# render outside `.ck-main`).
_LEGACY_BODY_OVERLAY = """
<style>
/* Editorial overlay for legacy `<div class="card">` panels inside
 * the chartis editorial shell — partner-flagged as "looks weird"
 * because the chartis CSS scopes .card to login-style centered
 * forms. Override here so legacy ops/owners/runs/etc. pages get
 * panel chrome that matches ck_panel without per-route refactors. */
.ck-main .card {
  background: var(--sc-paper, #fff);
  border: 1px solid var(--sc-rule, #d6cfc0);
  padding: 14px 18px;
  margin: 0 0 16px;
  max-width: none;
}
.ck-main .card h1,
.ck-main .card h2,
.ck-main .card h3 {
  font-family: var(--sc-sans, 'Inter Tight', sans-serif);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--sc-navy, #0b2341);
  margin: 0 0 10px;
}
.ck-main .card p,
.ck-main .card .muted {
  font-family: var(--sc-sans, 'Inter Tight', sans-serif);
  font-size: 13px;
  line-height: 1.55;
  color: var(--sc-text, #1a2332);
  margin: 0 0 8px;
}
.ck-main .card .muted {
  color: var(--sc-text-dim, #465366);
}
/* Legacy raw <table> inside cards — give it editorial typography
 * so it stops inheriting Source Serif. Same approach as PR #278's
 * wc-table fix. */
.ck-main .card table {
  width: 100%;
  border-collapse: collapse;
  font-family: var(--sc-sans, 'Inter Tight', sans-serif);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}
.ck-main .card table thead th {
  padding: 8px 10px;
  text-align: left;
  font-family: var(--sc-mono, 'JetBrains Mono', monospace);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--sc-text-dim, #465366);
  background: var(--sc-parchment, #f5f1ea);
  border-bottom: 1px solid var(--sc-rule, #d6cfc0);
}
.ck-main .card table tbody td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--sc-rule, #d6cfc0);
  color: var(--sc-text, #1a2332);
  vertical-align: top;
}
.ck-main .card table tbody tr:last-child td { border-bottom: 0; }
.ck-main .card table .num { text-align: right; font-variant-numeric: tabular-nums; }
/* Legacy `kpi-grid` / `kpi-card` markup — looks lazy without
 * editorial styling. Convert the visual to match ck_kpi_block: bone
 * background, mono uppercase label, mono value. */
.ck-main .kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 8px;
  margin: 0 0 16px;
}
.ck-main .kpi-card {
  background: var(--sc-paper, #fff);
  border: 1px solid var(--sc-rule, #d6cfc0);
  padding: 12px 14px;
}
.ck-main .kpi-card .kpi-label {
  font-family: var(--sc-mono, 'JetBrains Mono', monospace);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: var(--sc-text-dim, #465366);
  margin: 0 0 4px;
}
.ck-main .kpi-card .kpi-value {
  font-family: var(--sc-mono, 'JetBrains Mono', monospace);
  font-size: 22px;
  font-weight: 600;
  color: var(--sc-navy, #0b2341);
  font-variant-numeric: tabular-nums;
}
/* `badge` chips inside legacy pages */
.ck-main .badge {
  display: inline-block;
  padding: 1px 6px;
  font-family: var(--sc-mono, 'JetBrains Mono', monospace);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  border-radius: 2px;
  border: 1px solid var(--sc-rule, #d6cfc0);
  color: var(--sc-text, #1a2332);
}
.ck-main .badge-green {
  color: var(--sc-positive, #0a8a5f);
  border-color: var(--sc-positive, #0a8a5f);
}
.ck-main .badge-amber {
  color: var(--sc-warning, #b8732a);
  border-color: var(--sc-warning, #b8732a);
}
.ck-main .badge-red {
  color: var(--sc-negative, #b5321e);
  border-color: var(--sc-negative, #b5321e);
}
.ck-main .badge-muted {
  color: var(--sc-text-faint, #7a8699);
  border-color: var(--sc-rule, #d6cfc0);
}
</style>
"""


def shell(
    body: str,
    title: str,
    *,
    back_href: Optional[str] = None,
    subtitle: Optional[str] = None,
    extra_css: str = "",
    extra_js: str = "",
    active_nav: Optional[str] = None,
    generated: bool = True,  # noqa: ARG001 — kept for signature parity
    omit_h1: bool = False,
) -> str:
    """Legacy ``shell()`` — routes through ``chartis_shell``.

    Historically this function wrapped a body in a light-theme document
    and later delegated to ``shell_v2``. After the chartis unification
    it just calls ``chartis_shell`` with a compatible signature. The
    ``back_href`` argument is rendered as a small breadcrumb link above
    the body content; the ``generated`` argument is accepted for
    backward compat but ignored.

    ``omit_h1`` is honored: when False (the default) and the supplied
    body has no ``<h1`` element of its own, an editorial-styled h1 is
    prepended carrying ``title``. This closes the audit-2026-05-29
    finding that ~11 legacy ``shell()``-routed pages (/cohorts,
    /deadlines, /owners, /variance, /initiatives, /runs, /jobs,
    /upload, /users, /query, /settings) all rendered without an h1,
    directly violating the CLAUDE.md One-H1 invariant. Pages that
    genuinely don't want a title h1 can pass ``omit_h1=True``; the
    chartis ``ck_page_title`` path is unaffected because those bodies
    already contain ``<h1``.

    Always injects the editorial overlay CSS (`_LEGACY_BODY_OVERLAY`)
    so legacy `card` / `kpi-card` / raw-table markup picks up
    parchment + Inter Tight + JetBrains Mono. Partners flagged the
    legacy routes as "no editorial editing" — this overlay catches
    every shell()-routed page in one place rather than refactoring
    each of the 26 routes individually.
    """
    import html as _html
    if back_href:
        body = (
            f'<nav class="breadcrumb" aria-label="Breadcrumb" '
            f'style="margin-bottom:12px;font-size:11px;">'
            f'<a href="{_html.escape(back_href)}" '
            f'style="color:var(--sc-teal-ink);text-decoration:none;">'
            f'&larr; Back to index</a></nav>{body}'
        )
    # Auto-inject an editorial h1 when the body has none. Idempotent:
    # callers that already emit their own h1 (e.g. via ck_page_title)
    # are detected and untouched, so this never produces a double-h1.
    # Skip when caller explicitly opts out via omit_h1=True.
    if not omit_h1 and "<h1" not in body:
        body = (
            f'<h1 class="ck-page-h1" '
            f'style="font-family:Source Serif 4,Georgia,serif;'
            f'font-weight:600;font-size:28px;line-height:1.18;'
            f'color:var(--sc-ink,#1a2332);margin:0 0 12px;">'
            f'{_html.escape(title)}</h1>'
        ) + body
    # Prepend the editorial overlay — it's a <style> block so order
    # doesn't matter, but conceptually it belongs above the body so
    # the rules are in place before the markup renders.
    body = _LEGACY_BODY_OVERLAY + body
    return chartis_shell(
        body,
        title,
        subtitle=subtitle or "",
        extra_css=extra_css,
        extra_js=extra_js,
        active_nav=active_nav,
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
    """Format a PERCENT-POINT value as ``15.3%`` in tabular-nums.

    Input is the percent-point value already (``15.3`` → ``"15.3%"``);
    the helper does NOT scale. If you have a raw ratio (``0.153``),
    multiply by 100 first or use ``_chartis_kit.ck_fmt_percent``
    which takes the ratio directly — mixing the two on the same value
    will render the metric 100× off.

    ``signed=True`` forces a leading sign so beat/miss reads
    ``+4.1%`` / ``-4.1%``. CLAUDE.md spec: 1 decimal.
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
