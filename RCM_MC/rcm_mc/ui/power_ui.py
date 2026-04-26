"""Power-UI builders — Python side of the PE-analyst power features.

Pairs with ``rcm_mc/ui/static/power_ui.{js,css}``. The JS library is
loaded once per page via :func:`power_ui_tags` (the Chartis shell
calls this automatically). Python-side helpers below produce HTML
snippets that opt into the client features via data-attributes.

Usage::

    from .power_ui import (
        power_ui_tags, provenance, sortable_table, export_json_panel,
    )

    body = provenance(
        value="$4,200",
        source="hospital_06 H6-P000 .. H6-P009 (5 paid + 1 bad-debt)",
        formula="sum(paid_amount) over mature cohort",
    )

The tags emitted by this module are self-contained HTML — no
requirement to manually include the bundle; ``chartis_shell`` handles
that now.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, Iterable, List, Optional, Sequence


def benchmark_chip(
    *,
    value: float,
    peer_low: Optional[float] = None,
    peer_high: Optional[float] = None,
    peer_median: Optional[float] = None,
    higher_is_better: bool = True,
    format_spec: str = ",.2f",
    suffix: str = "",
    label: str = "",
    peer_label: str = "peer band",
) -> str:
    """Render one number with its peer band, semantic color, and a
    plain-English verdict beneath.

    The chip answers three questions at a glance:
        1. What is the value?              → big tabular-nums number
        2. How does it compare?            → colored dot (green / amber / red)
        3. What does that mean in plain English?  → one-line verdict

    Color semantics are load-bearing:
        green   — better than peer_high (or below peer_low when
                  ``higher_is_better=False``) → "above peer range"
        amber   — inside the peer band
        red     — worse than peer_low (or above peer_high when
                  ``higher_is_better=False``)

    ``higher_is_better`` flips the comparison: set to ``False`` for
    metrics like denial rate, leverage, DSO where lower is better.

    When only ``peer_median`` is supplied (no band), the chip falls
    back to a ±10% band around the median.
    """
    if peer_low is None and peer_high is None and peer_median is not None:
        peer_low = peer_median * 0.9
        peer_high = peer_median * 1.1

    def _fmt(v: float) -> str:
        return format(v, format_spec) + suffix

    # Resolve color + verdict
    color = "var(--muted)"                     # text_faint (neutral)
    verdict = "no peer benchmark available"
    band_str = (
        f"{_fmt(peer_low)}–{_fmt(peer_high)} {peer_label}"
        if (peer_low is not None and peer_high is not None)
        else ""
    )
    if peer_low is not None and peer_high is not None:
        if higher_is_better:
            if value >= peer_high:
                color = "var(--green)"
                verdict = f"above {band_str}"
            elif value <= peer_low:
                color = "var(--red)"
                verdict = f"below {band_str}"
            else:
                color = "var(--amber)"
                verdict = f"inside {band_str}"
        else:
            if value <= peer_low:
                color = "var(--green)"
                verdict = f"better than {band_str}"
            elif value >= peer_high:
                color = "var(--red)"
                verdict = f"worse than {band_str}"
            else:
                color = "var(--amber)"
                verdict = f"inside {band_str}"

    lbl_html = ""
    if label:
        lbl_html = (
            f'<div style="font-size:9px;letter-spacing:1.3px;'
            f'text-transform:uppercase;color:var(--muted);'
            f'font-weight:600;margin-bottom:3px;">'
            f'{html.escape(label)}</div>'
        )

    return (
        f'<div style="display:inline-block;min-width:140px;'
        f'vertical-align:top;">'
        f'{lbl_html}'
        f'<div style="font-family:\'JetBrains Mono\',monospace;'
        f'font-size:22px;font-weight:700;color:{color};'
        f'line-height:1.1;">{_fmt(value)}</div>'
        f'<div style="display:flex;align-items:center;gap:6px;'
        f'margin-top:4px;font-size:10.5px;color:var(--muted);">'
        f'<span style="width:8px;height:8px;border-radius:50%;'
        f'background:{color};display:inline-block;"></span>'
        f'<span>{html.escape(verdict)}</span></div>'
        f'</div>'
    )


def interpret_callout(
    title: str,
    body: str,
    *,
    tone: str = "info",
) -> str:
    """Plain-English summary that sits next to a complex chart.

    ``tone`` ∈ {info, good, warn, bad}.  Info is the default neutral
    navy-accent callout; the other tones re-color the left border so
    the reader absorbs the verdict before reading the words.
    """
    tone_colors = {
        "info": "var(--blue)",
        "good": "var(--green)",
        "warn": "var(--amber)",
        "bad": "var(--red)",
    }
    border = tone_colors.get(tone, tone_colors["info"])
    return (
        f'<div style="background:var(--bg);padding:12px 16px;'
        f'border-left:3px solid {border};border-radius:0 3px 3px 0;'
        f'font-size:12.5px;color:var(--border);line-height:1.65;'
        f'max-width:900px;margin-top:12px;">'
        f'<strong style="color:var(--bg-tint);">'
        f'{html.escape(title)}</strong> '
        f'<span>{body}</span>'
        f'</div>'
    )


def deal_context_bar(
    qs: Optional[Dict[str, List[str]]] = None,
    *,
    active_surface: str = "",
) -> str:
    """Persistent "Working Deal" context bar for diligence pages.

    Pulled to the top of every big diligence surface (Deal MC,
    Covenant Stress, Bridge Audit, Payer Stress, Bear Case,
    Regulatory Calendar). Reads the deal's identity + core
    financials from whatever alias the current page uses and emits
    a single bar with:

        * deal name + revenue + EBITDA + entry multiple (when known)
        * one-click "jump to" buttons to every sibling surface, with
          the params *translated* into each destination's expected
          query-string names (e.g. ``revenue_usd`` on Deal MC becomes
          ``total_npr_usd`` on Payer Stress).

    Param aliasing: different pages use different names for the same
    concept.  This helper normalizes to a canonical dict and rewrites
    per destination.  If no deal identity can be inferred, returns
    empty string and the caller page simply doesn't render a bar.
    """
    qs = qs or {}

    def _first(keys: List[str]) -> str:
        for k in keys:
            vals = qs.get(k) or []
            if vals and str(vals[0]).strip():
                return str(vals[0]).strip()
        return ""

    def _fnum(keys: List[str]) -> Optional[float]:
        v = _first(keys)
        if not v:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    deal_name = _first(["deal_name", "target_name"])
    if not deal_name:
        return ""

    revenue = _fnum([
        "revenue_usd", "revenue_year0_usd", "total_npr_usd",
    ])
    ebitda = _fnum([
        "ebitda_usd", "ebitda_year0_usd", "ebitda_y0",
        "total_ebitda_usd",
    ])
    enterprise_value = _fnum([
        "enterprise_value_usd", "ev_usd", "asking_price_usd",
    ])
    equity = _fnum(["equity_usd", "equity_check_usd"])
    debt = _fnum([
        "debt_usd", "debt_year0_usd", "total_debt_usd",
    ])
    specialty = _first(["specialty"])
    dataset = _first(["dataset"])
    entry_multiple = _fnum(["entry_multiple"])
    medicare_share = _fnum(["medicare_share"])
    ma_mix = _fnum(["ma_mix_pct"])
    commercial_share = _fnum(["commercial_payer_share"])

    # Core financial strip
    strip_parts: List[str] = []
    if revenue:
        strip_parts.append(f"${revenue/1e6:,.0f}M NPR")
    if ebitda:
        margin = (
            f" ({ebitda/revenue*100:.1f}% margin)"
            if revenue and revenue > 0 else ""
        )
        strip_parts.append(f"${ebitda/1e6:,.1f}M EBITDA{margin}")
    if enterprise_value:
        mult_bit = (
            f" · {entry_multiple:.1f}× entry"
            if entry_multiple else
            f" · {enterprise_value/ebitda:.1f}× implied"
            if ebitda and ebitda > 0 else ""
        )
        strip_parts.append(
            f"${enterprise_value/1e6:,.0f}M EV{mult_bit}"
        )
    if specialty:
        strip_parts.append(specialty.replace("_", " "))
    strip = " · ".join(strip_parts) or "deal profile"

    # Build cross-link URLs.  Each destination has its own expected
    # param names; we rewrite.
    def _encode(params: Dict[str, Any]) -> str:
        from urllib.parse import urlencode as _urlencode
        # Drop None / empty; coerce to str
        clean = {}
        for k, v in params.items():
            if v is None:
                continue
            s = str(v)
            if s == "" or s == "0" or s == "0.0":
                # Keep zeros if explicitly supplied? Simpler: drop
                # empties but keep non-empty numeric zeros
                if v == 0 or v == 0.0:
                    continue
            clean[k] = s
        return _urlencode(clean)

    surfaces = [
        ("deal_mc", "Deal MC", "/diligence/deal-mc", {
            "deal_name": deal_name,
            "specialty": specialty,
            "revenue_usd": revenue, "ebitda_usd": ebitda,
            "ev_usd": enterprise_value, "equity_usd": equity,
            "debt_usd": debt, "entry_multiple": entry_multiple,
        }),
        ("covenant", "Covenant Stress", "/diligence/covenant-stress", {
            "deal_name": deal_name,
            "ebitda_y0": ebitda, "total_debt_usd": debt,
        }),
        ("bridge", "Bridge Audit", "/diligence/bridge-audit", {
            "target_name": deal_name,
            "asking_price_usd": enterprise_value,
            "entry_multiple": entry_multiple,
            "ma_mix_pct": ma_mix,
            "commercial_payer_share": commercial_share,
        }),
        ("payer", "Payer Stress", "/diligence/payer-stress", {
            "target_name": deal_name,
            "total_npr_usd": revenue, "total_ebitda_usd": ebitda,
        }),
        ("bear", "Bear Case", "/diligence/bear-case", {
            "dataset": dataset, "deal_name": deal_name,
            "specialty": specialty,
            "revenue_year0_usd": revenue,
            "ebitda_year0_usd": ebitda,
            "enterprise_value_usd": enterprise_value,
            "equity_check_usd": equity, "debt_usd": debt,
            "medicare_share": medicare_share,
        }),
        ("reg", "Reg Calendar", "/diligence/regulatory-calendar", {
            "target_name": deal_name,
            "specialty": specialty,
            "ma_mix_pct": ma_mix,
            "commercial_payer_share": commercial_share,
            "revenue_usd": revenue, "ebitda_usd": ebitda,
        }),
        ("profile", "Deal Profile", "/diligence/deal", {
            "target_name": deal_name,
        }),
        ("pipeline", "Full Pipeline", "/diligence/thesis-pipeline", {
            "dataset": dataset, "deal_name": deal_name,
            "specialty": specialty,
            "revenue_year0_usd": revenue,
            "ebitda_year0_usd": ebitda,
            "enterprise_value_usd": enterprise_value,
            "equity_check_usd": equity, "debt_usd": debt,
            "medicare_share": medicare_share,
        }),
    ]

    links: List[str] = []
    for key, label, base, params in surfaces:
        # Only require one meaningful param besides deal_name
        meaningful = sum(
            1 for k, v in params.items()
            if v not in (None, "", 0, 0.0)
        )
        if meaningful < 2:
            continue
        url = base + "?" + _encode(params) if meaningful else base
        is_active = key == active_surface
        color = "var(--blue-soft)" if is_active else "var(--border)"
        weight = "700" if is_active else "500"
        cursor = (
            'default' if is_active else 'pointer'
        )
        link = (
            f'<a href="{html.escape(url)}" '
            f'style="color:{color};text-decoration:none;'
            f'font-size:11px;font-weight:{weight};'
            f'letter-spacing:0.3px;padding:4px 10px;'
            f'border:1px solid {"var(--teal)" if is_active else "var(--border)"};'
            f'border-radius:3px;background:'
            f'{"rgba(59,130,246,0.15)" if is_active else "transparent"};'
            f'transition:all 120ms;cursor:{cursor};" '
            f'{"onclick=\"return false;\"" if is_active else ""}>'
            f'{html.escape(label)}</a>'
        )
        links.append(link)

    if not links:
        return ""

    return (
        f'<div style="background:var(--bg);border-top:1px solid var(--border);'
        f'border-bottom:1px solid var(--border);padding:8px 16px;'
        f'margin:0 -24px 18px -24px;'
        f'display:flex;flex-wrap:wrap;gap:10px;align-items:center;'
        f'font-family:\'Helvetica Neue\',Arial,sans-serif;">'
        f'<div style="display:flex;align-items:baseline;gap:8px;'
        f'font-size:12px;color:var(--muted);">'
        f'<span style="font-size:10px;letter-spacing:1.4px;'
        f'text-transform:uppercase;font-weight:700;color:var(--muted);">'
        f'Working deal</span>'
        f'<span style="color:var(--bg-tint);font-weight:700;font-size:13px;">'
        f'{html.escape(deal_name)}</span>'
        f'<span style="color:var(--muted);">·</span>'
        f'<span style="font-family:\'JetBrains Mono\',monospace;'
        f'font-size:11px;color:var(--border);">{html.escape(strip)}</span>'
        f'</div>'
        f'<div style="flex:1 1 auto;"></div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:6px;">'
        + "".join(links)
        + f'</div>'
        f'</div>'
    )


def power_ui_tags() -> str:
    """Emit the <link> + <script> pair for the power-ui bundle.

    Idempotent — safe to call inside pages that might also be wrapped
    by the shell."""
    return (
        '<link rel="stylesheet" href="/static/power_ui.css">\n'
        '<script src="/static/power_ui.js" defer></script>\n'
    )


def provenance(
    value: str,
    *,
    source: str,
    formula: Optional[str] = None,
    detail: Optional[str] = None,
    tag: str = "span",
    extra_class: str = "",
    extra_style: str = "",
) -> str:
    """Wrap ``value`` in a span with a hover tooltip exposing the
    provenance (source, formula, detail). Cursor becomes `help`,
    underline is dotted — discoverable without being distracting.
    """
    attrs = [
        f'data-provenance="{html.escape(source, quote=True)}"',
    ]
    if formula:
        attrs.append(
            f'data-provenance-formula="{html.escape(formula, quote=True)}"'
        )
    if detail:
        attrs.append(
            f'data-provenance-detail="{html.escape(detail, quote=True)}"'
        )
    if extra_class:
        attrs.append(f'class="{html.escape(extra_class, quote=True)}"')
    if extra_style:
        attrs.append(f'style="{html.escape(extra_style, quote=True)}"')
    attrs.append("tabindex=\"0\"")
    return (
        f"<{tag} {' '.join(attrs)}>{html.escape(value)}</{tag}>"
    )


def sortable_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[Any]],
    *,
    name: str = "table",
    sortable: bool = True,
    filterable: bool = True,
    exportable: bool = True,
    sort_keys: Optional[Sequence[Sequence[Any]]] = None,
    caption: Optional[str] = None,
    table_class: str = "",
) -> str:
    """Render a table with optional client features opted in via
    data-attributes. ``sort_keys`` (optional) is a parallel matrix of
    machine-readable sort values for columns where the display text
    isn't directly sortable (e.g. "$1,234" → 1234)."""
    attrs = [f'data-export-name="{html.escape(name, quote=True)}"']
    if sortable:
        attrs.append('data-sortable')
    if filterable:
        attrs.append('data-filterable')
    if exportable:
        attrs.append('data-export')
    # Default class — applies editorial cad-table rules (cells with
    # padding, borders, tabular-num right-aligned numerics). Without
    # this, the table renders cell-borderless and column headers
    # visually run together.
    final_class = table_class or "cad-table"
    attrs.append(f'class="{html.escape(final_class, quote=True)}"')
    head_cells = "".join(
        f'<th>{html.escape(str(h))}</th>' for h in headers
    )
    body_rows = []
    for ridx, row in enumerate(rows):
        cells = []
        for cidx, cell in enumerate(row):
            display = "" if cell is None else str(cell)
            sort_attr = ""
            if sort_keys is not None:
                try:
                    key = sort_keys[ridx][cidx]
                    if key is not None:
                        sort_attr = (
                            f' data-sort-key="{html.escape(str(key), quote=True)}"'
                        )
                except IndexError:
                    pass
            # If the display value already contains HTML (from
            # provenance etc.) we trust it through — callers who
            # need raw HTML build the cell content themselves.
            cells.append(f'<td{sort_attr}>{display}</td>')
        body_rows.append('<tr>' + "".join(cells) + '</tr>')
    caption_html = (
        f'<caption>{html.escape(caption)}</caption>' if caption else ""
    )
    return (
        f'<table {" ".join(attrs)}>'
        f'{caption_html}'
        f'<thead><tr>{head_cells}</tr></thead>'
        f'<tbody>{"".join(body_rows)}</tbody>'
        f'</table>'
    )


def export_json_panel(
    inner_html: str,
    *,
    payload: Any,
    name: str = "panel",
    extra_class: str = "",
    extra_style: str = "",
) -> str:
    """Wrap a block of HTML in a container that gets a floating
    'Export JSON' button auto-injected by the bundle."""
    encoded = html.escape(json.dumps(payload, default=str), quote=True)
    cls_attr = f' class="{html.escape(extra_class, quote=True)}"' if extra_class else ""
    style_attr = f' style="{html.escape(extra_style, quote=True)}"' if extra_style else ""
    return (
        f'<div data-export-json="{encoded}" '
        f'data-export-name="{html.escape(name, quote=True)}"'
        f'{cls_attr}{style_attr}>'
        f'{inner_html}'
        f'</div>'
    )


def bookmark_hint() -> str:
    """Small hint text (footer) telling the user about b/s shortcuts.
    Use sparingly — don't clutter every page."""
    return (
        '<div style="font-size:10px;color:var(--muted);letter-spacing:.5px;'
        'text-transform:uppercase;margin-top:20px;opacity:0.7;">'
        'Press <kbd style="padding:1px 5px;border:1px solid currentColor;'
        'border-radius:2px;font-family:inherit;">?</kbd> for shortcuts · '
        '<kbd style="padding:1px 5px;border:1px solid currentColor;'
        'border-radius:2px;font-family:inherit;">b</kbd> to bookmark · '
        '<kbd style="padding:1px 5px;border:1px solid currentColor;'
        'border-radius:2px;font-family:inherit;">⌘K</kbd> to jump'
        '</div>'
    )


def diff_badge(
    left_value: float,
    right_value: float,
    *,
    format_spec: str = ",.0f",
    unit: str = "$",
    higher_is_better: bool = False,
) -> str:
    """Badge showing left vs right delta for comparison views.

    ``higher_is_better`` flips the coloring: when True, right > left
    gets positive (green); when False, right > left gets negative."""
    if left_value == right_value:
        cls = "rcm-diff-neutral"
        arrow = "→"
        delta_str = "="
    else:
        delta = right_value - left_value
        if (delta > 0) == higher_is_better:
            cls = "rcm-diff-positive"
        else:
            cls = "rcm-diff-negative"
        arrow = "▲" if delta > 0 else "▼"
        delta_str = f"{unit}{format(abs(delta), format_spec)}"
    return (
        f'<span class="rcm-diff-indicator {cls}">'
        f'{arrow} {delta_str}</span>'
    )
