"""Market-intelligence analytics for the sector screeners (Home Health,
Hospice, …) — Phase 2D.

Turns the already-vendored CMS provider + quality data into a local-market
read for diligence: ownership mix, quality distribution (quartiles),
sub-state "locality" competition (county for hospice, city for home health —
the HH CMS file carries city, not county), and per-provider percentile/peer
context. Pure functions (testable in isolation) + ck_panel renderers.

Honest by construction: counts/means/quartiles over the public file only —
no invented composites, no fabricated coordinates, no external calls, and
never a financial/$ figure (none exists in these files).
"""
from __future__ import annotations

import html as _html
import math
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

from ._chartis_kit import ck_kpi_block, ck_panel

_UNKNOWN_OWNERSHIP = {"", "-", "—", "n/a", "not available", "not reported"}


def _esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _fmt(v: Optional[float], suffix: str = "") -> str:
    return f"{v:g}{suffix}" if v is not None else "—"


def _own_label(v: Any) -> str:
    s = (str(v) if v is not None else "").strip()
    return "Not reported" if s.lower() in _UNKNOWN_OWNERSHIP else s


# ── Pure analytics ─────────────────────────────────────────────────────────

def ownership_mix(providers: List[Any]) -> List[Tuple[str, int]]:
    """``[(ownership_label, count)]`` desc; unknowns folded to 'Not reported'."""
    c = Counter(_own_label(getattr(p, "ownership", "")) for p in providers)
    return c.most_common()


def _quantile(sorted_vals: List[float], q: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = q * (len(sorted_vals) - 1)
    lo, hi = math.floor(idx), math.ceil(idx)
    if lo == hi:
        return round(sorted_vals[int(idx)], 2)
    return round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (idx - lo), 2)


def quality_distribution(
    quality: Dict[str, Dict[str, Optional[float]]],
    ccns: List[str],
    key: str,
) -> Optional[Dict[str, Any]]:
    """Quartile summary of one metric over the given CCNs (None if no data)."""
    vals = sorted(
        quality[c][key] for c in ccns
        if c in quality and quality[c].get(key) is not None
    )
    if not vals:
        return None
    return {
        "n": len(vals), "min": round(vals[0], 2), "max": round(vals[-1], 2),
        "q1": _quantile(vals, 0.25), "median": _quantile(vals, 0.5),
        "q3": _quantile(vals, 0.75),
    }


def percentile_rank(sorted_vals: List[float], v: Optional[float]) -> Optional[int]:
    """Percentile of ``v`` within ``sorted_vals`` (mid-rank), 0–100."""
    if v is None or not sorted_vals:
        return None
    below = sum(1 for x in sorted_vals if x < v)
    equal = sum(1 for x in sorted_vals if x == v)
    return round(100 * (below + 0.5 * equal) / len(sorted_vals))


def locality_competition(
    providers: Dict[str, Any],
    quality: Dict[str, Dict[str, Optional[float]]],
    state: str,
    locality_attr: str,
    headline_key: str,
) -> List[Dict[str, Any]]:
    """Per-locality competition rows for one state, sorted by provider count."""
    groups: Dict[str, List[Tuple[str, Any]]] = defaultdict(list)
    for ccn, p in providers.items():
        if getattr(p, "state", "") != state:
            continue
        loc = (getattr(p, locality_attr, "") or "").strip()
        if loc:
            groups[loc].append((ccn, p))
    rows: List[Dict[str, Any]] = []
    for loc, members in groups.items():
        vals = [quality.get(c, {}).get(headline_key) for c, _ in members]
        vals = [v for v in vals if v is not None]
        avg = round(sum(vals) / len(vals), 2) if vals else None
        own = Counter(_own_label(getattr(p, "ownership", "")) for _, p in members)
        top = own.most_common(1)
        rows.append({
            "locality": loc, "count": len(members), "avg": avg,
            "top_ownership": top[0][0] if top else "—",
        })
    rows.sort(key=lambda r: (-r["count"], r["locality"]))
    return rows


def state_market_summary(
    providers: Dict[str, Any],
    quality: Dict[str, Dict[str, Optional[float]]],
    state: str,
    locality_attr: str,
    headline_key: str,
) -> Dict[str, Any]:
    """Aggregate market read for one state (counts + mix + distribution)."""
    members = [(c, p) for c, p in providers.items()
               if getattr(p, "state", "") == state]
    ccns = [c for c, _ in members]
    localities = {(getattr(p, locality_attr, "") or "").strip()
                  for _, p in members if (getattr(p, locality_attr, "") or "").strip()}
    return {
        "provider_count": len(members),
        "n_localities": len(localities),
        "ownership_mix": ownership_mix([p for _, p in members]),
        "quality_distribution": quality_distribution(quality, ccns, headline_key),
        "competition": locality_competition(
            providers, quality, state, locality_attr, headline_key),
    }


# ── Panel renderers ────────────────────────────────────────────────────────

def _ownership_bar(mix: List[Tuple[str, int]], total: int) -> str:
    if not total:
        return '<p class="ck-section-body">No ownership data.</p>'
    rows = ""
    for label, n in mix:
        pct = round(100 * n / total)
        rows += (
            f'<tr><td>{_esc(label)}</td>'
            f'<td class="num">{n:,}</td>'
            f'<td class="num">{pct}%</td></tr>'
        )
    return ('<table class="ck-table"><thead><tr><th>Ownership</th>'
            '<th class="num">Providers</th><th class="num">Share</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def render_state_market_panels(
    *,
    providers: Dict[str, Any],
    quality: Dict[str, Dict[str, Optional[float]]],
    state: str,
    route: str,
    kind_singular: str,
    locality_attr: str,
    locality_label: str,
    headline_label: str,
    headline_suffix: str,
    headline_key: str,
    selected_locality: str = "",
) -> str:
    """State competitive-market section for the screener state view."""
    s = state_market_summary(providers, quality, state, locality_attr, headline_key)
    if not s["provider_count"]:
        return ""

    # ── Market summary cards ──
    dist = s["quality_distribution"]
    median_txt = _fmt(dist["median"], headline_suffix) if dist else "—"
    own_leader = s["ownership_mix"][0] if s["ownership_mix"] else ("—", 0)
    own_share = (round(100 * own_leader[1] / s["provider_count"])
                 if s["provider_count"] else 0)
    cards = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(4,1fr);'
        'gap:8px;margin-bottom:14px;">'
        + ck_kpi_block(f"{kind_singular.title()}s", f"{s['provider_count']:,}",
                       f"in {_esc(state)}")
        + ck_kpi_block(f"{locality_label}s represented", f"{s['n_localities']:,}",
                       "with providers")
        + ck_kpi_block(f"Median {headline_label}", median_txt,
                       f"{dist['n']:,} rated" if dist else "not rated")
        + ck_kpi_block("Ownership leader", _esc(own_leader[0]),
                       f"{own_share}% of providers")
        + '</div>'
    )

    # ── Quality distribution (quartiles) ──
    if dist:
        dist_html = (
            '<table class="ck-table"><thead><tr>'
            '<th class="num">Min</th><th class="num">25th</th>'
            '<th class="num">Median</th><th class="num">75th</th>'
            '<th class="num">Max</th><th class="num">Rated</th></tr></thead>'
            f'<tbody><tr><td class="num">{_fmt(dist["min"], headline_suffix)}</td>'
            f'<td class="num">{_fmt(dist["q1"], headline_suffix)}</td>'
            f'<td class="num">{_fmt(dist["median"], headline_suffix)}</td>'
            f'<td class="num">{_fmt(dist["q3"], headline_suffix)}</td>'
            f'<td class="num">{_fmt(dist["max"], headline_suffix)}</td>'
            f'<td class="num">{dist["n"]:,}</td></tr></tbody></table>'
        )
    else:
        dist_html = (f'<p class="ck-section-body">No published {_esc(headline_label)} '
                     f'for {_esc(state)} providers.</p>')

    # ── Ownership mix ──
    own_html = _ownership_bar(s["ownership_mix"], s["provider_count"])

    _subhead = ('font-size:11px;letter-spacing:.04em;text-transform:uppercase;'
                'color:var(--sc-text-dim);font-weight:600;margin:0 0 6px;')
    summary_panel = ck_panel(
        cards
        + f'<p style="{_subhead}">{_esc(headline_label)} distribution</p>'
        + dist_html
        + f'<p style="{_subhead}margin-top:14px;">Ownership mix</p>'
        + own_html,
        title=f"{_esc(state)} market summary",
    )

    # ── Locality competition table (links filter the provider list) ──
    comp = s["competition"]
    if comp:
        crows = ""
        for r in comp[:50]:
            loc = r["locality"]
            sel = ' style="background:var(--sc-rule-subtle,#f0ece3);"' if loc == selected_locality else ""
            link = f'{route}?state={_esc(state)}&locality={_html.escape(loc, quote=True).replace(" ", "%20")}'
            crows += (
                f'<tr{sel}><td><a href="{link}" class="ck-link">{_esc(loc)}</a></td>'
                f'<td class="num">{r["count"]:,}</td>'
                f'<td class="num">{_fmt(r["avg"], headline_suffix)}</td>'
                f'<td>{_esc(r["top_ownership"])}</td></tr>'
            )
        comp_panel = ck_panel(
            f'<p class="ck-section-body">{len(comp):,} {_esc(locality_label.lower())}s '
            f'with Medicare-certified {_esc(kind_singular)}s in {_esc(state)} — '
            f'click a {_esc(locality_label.lower())} to filter the list below. '
            f'Showing up to 50 by provider count.</p>'
            f'<table class="ck-table"><thead><tr><th>{_esc(locality_label)}</th>'
            f'<th class="num">{_esc(kind_singular.title())}s</th>'
            f'<th class="num">Avg {_esc(headline_label)}</th>'
            f'<th>Top ownership</th></tr></thead><tbody>{crows}</tbody></table>',
            title=f"{_esc(locality_label)} competition",
        )
    else:
        comp_panel = ""

    caveat = ck_panel(
        '<ul style="font-size:12px;color:var(--sc-text-dim);line-height:1.6;'
        'margin:0;padding-left:18px;">'
        f'<li>Medicare-certified {_esc(kind_singular)}s only — commercial / '
        'private-pay competitors are not visible here.</li>'
        '<li>CMS public quality data, not commercial revenue or payor mix.</li>'
        f'<li>{_esc(locality_label)} is the locality field in the CMS file '
        + ('(home health agencies are published with city, not county).'
           if locality_label.lower() == "city" else
           'as published by CMS.') +
        '</li>'
        '<li>Market context for diligence — <strong>not an investment '
        'recommendation</strong>.</li></ul>',
        title="What this market view can & cannot tell you",
    )

    return summary_panel + comp_panel + caveat


def filter_by_locality(rows: List[Any], locality_attr: str, locality: str) -> List[Any]:
    """Filter a provider list to one locality (case-insensitive). Empty
    ``locality`` returns the rows unchanged."""
    loc = (locality or "").strip().lower()
    if not loc:
        return rows
    return [p for p in rows
            if (getattr(p, locality_attr, "") or "").strip().lower() == loc]
