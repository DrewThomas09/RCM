"""Shared scaffold for single-provider deep-dive profiles (Home Health,
Hospice, …). Drill-down target from the sector screeners (sector_screener.py).

Given a CCN it renders, from the vendored sector loaders: an identity header,
a lead KPI strip (the provider's headline quality measure benchmarked against
its state average), a full quality table with a per-metric "vs state avg"
column, a same-state peer list (each linking to its own profile), and the
same provenance + limitations framing as the screener. No external calls;
public quality data only — never a financial/$ figure (none exists in these
files), and never a final investment recommendation.
"""
from __future__ import annotations

import html as _html
from typing import Any, Callable, Dict, List, Optional, Tuple

from ._chartis_kit import chartis_shell, ck_kpi_block, ck_page_title, ck_panel


def _esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _fmt(v: Optional[float], suffix: str = "") -> str:
    return f"{v:g}{suffix}" if v is not None else "—"


def _state_avg(quality: Dict[str, Dict[str, Optional[float]]],
               ccns: List[str], key: str) -> Optional[float]:
    """Mean of a metric across same-state providers that report it."""
    vals = [quality[c][key] for c in ccns
            if c in quality and quality[c].get(key) is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def render_sector_provider_profile(
    *,
    ccn: str,
    route: str,
    eyebrow: str,
    kind_singular: str,          # "agency" / "hospice"
    providers: Dict[str, Any],
    quality: Dict[str, Dict[str, Optional[float]]],
    name_attr: str,              # "provider_name" / "facility_name"
    identity_rows: Callable[[Any], List[Tuple[str, str]]],
    headline: Tuple[str, str, str],          # (label, metric_key, suffix)
    metrics: List[Tuple[str, str, str]],     # [(label, metric_key, suffix), …]
    avg_label: str,
    higher_is_better: bool,
    provenance: str,
    limitations: List[str],
) -> Optional[str]:
    """Render the profile, or ``None`` if the CCN isn't in ``providers``
    (the route turns that into a 404)."""
    provider = providers.get(ccn)
    if provider is None:
        return None

    name = _esc(getattr(provider, name_attr, "") or "Unknown provider")
    state = getattr(provider, "state", "") or ""
    q = quality.get(ccn, {})

    # Same-state peers (exclude self) for benchmarking + the peer list.
    peer_ccns = [c for c, p in providers.items()
                 if getattr(p, "state", "") == state and c != ccn]

    # ── Identity meta line ──
    city = getattr(provider, "city", "") or ""
    own = getattr(provider, "ownership", "") or ""
    meta_bits = [f"CCN {_esc(ccn)}"]
    if city or state:
        meta_bits.append(_esc(", ".join(b for b in (city, state) if b)))
    if own:
        meta_bits.append(_esc(own))

    # ── Lead KPI strip: headline metric vs state average ──
    h_label, h_key, h_suffix = headline
    h_val = q.get(h_key)
    h_state_avg = _state_avg(quality, peer_ccns + [ccn], h_key)
    delta_sub = "no state benchmark"
    if h_val is not None and h_state_avg is not None:
        diff = round(h_val - h_state_avg, 2)
        better = (diff >= 0) if higher_is_better else (diff <= 0)
        arrow = "▲" if diff > 0 else ("▼" if diff < 0 else "▬")
        tone = "above" if better else "below"
        delta_sub = f"{arrow} {diff:+g} vs {state} avg {_fmt(h_state_avg)} ({tone} peers)"
    elif h_state_avg is not None:
        delta_sub = f"{state} avg {_fmt(h_state_avg)}"

    # rank within state on the headline metric (rated providers only)
    rank_sub = "not rated"
    rated = [(c, quality[c][h_key]) for c in peer_ccns + [ccn]
             if c in quality and quality[c].get(h_key) is not None]
    if h_val is not None and rated:
        ordered = sorted(rated, key=lambda kv: kv[1], reverse=higher_is_better)
        rank = [c for c, _ in ordered].index(ccn) + 1
        rank_sub = f"#{rank} of {len(ordered)} rated in {state}"

    kpis = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(3,1fr);'
        'gap:8px;margin-bottom:14px;">'
        + ck_kpi_block(h_label, _fmt(h_val, h_suffix), delta_sub)
        + ck_kpi_block(f"Rank in {state or 'state'}", rank_sub.split(" of ")[0]
                       if rank_sub.startswith("#") else "—", rank_sub)
        + ck_kpi_block(f"{kind_singular.title()}s in {state or 'state'}",
                       f"{len(peer_ccns) + 1:,}", "Medicare-certified")
        + '</div>'
    )

    # ── Identity panel ──
    id_rows = "".join(
        f'<tr><td style="color:var(--sc-text-dim);white-space:nowrap;">{_esc(k)}</td>'
        f'<td>{_esc(v)}</td></tr>'
        for k, v in identity_rows(provider) if v
    )
    identity_panel = ck_panel(
        f'<table class="ck-table" style="font-size:13px;"><tbody>{id_rows}</tbody></table>',
        title="Provider identity",
    )

    # ── Quality table: value + state-avg benchmark per metric ──
    qrows = ""
    for label, key, suffix in metrics:
        val = q.get(key)
        savg = _state_avg(quality, peer_ccns + [ccn], key)
        qrows += (
            f'<tr><td>{_esc(label)}</td>'
            f'<td class="num">{_fmt(val, suffix)}</td>'
            f'<td class="num" style="color:var(--sc-text-dim);">{_fmt(savg, suffix)}</td></tr>'
        )
    quality_panel = ck_panel(
        '<table class="ck-table"><thead><tr><th>Quality measure</th>'
        f'<th class="num">This {_esc(kind_singular)}</th>'
        f'<th class="num">{_esc(state) or "State"} avg</th></tr></thead>'
        f'<tbody>{qrows}</tbody></table>'
        '<p style="font-size:11px;color:var(--sc-text-dim);margin:8px 0 0;">'
        'State average is the mean across same-state Medicare-certified '
        f'{_esc(kind_singular)}s that publicly report each measure. '
        '&ldquo;&mdash;&rdquo; means not reported.</p>',
        title="Publicly reported quality",
    )

    # ── Same-state peer list (each links to its own profile) ──
    peer_rated = sorted(
        ((c, quality.get(c, {}).get(h_key)) for c in peer_ccns),
        key=lambda kv: (kv[1] is None, -(kv[1] or 0) if higher_is_better else (kv[1] or 0)),
    )
    peer_rows = ""
    for c, val in peer_rated[:8]:
        p = providers[c]
        pname = _esc(getattr(p, name_attr, "") or c)
        peer_rows += (
            f'<tr><td><a href="{route}/{_esc(c)}" class="ck-link">{pname}</a></td>'
            f'<td><span class="num">{_esc(c)}</span></td>'
            f'<td class="num">{_fmt(val, h_suffix)}</td></tr>'
        )
    peers_panel = ck_panel(
        f'<p class="ck-section-body">Other Medicare-certified {_esc(kind_singular)}s in '
        f'{_esc(state) or "this state"}, by {_esc(avg_label)}. '
        f'<a href="{route}?state={_esc(state)}" class="ck-link">See all &rarr;</a></p>'
        '<table class="ck-table"><thead><tr><th>Provider</th><th>CCN</th>'
        f'<th class="num">{_esc(h_label)}</th></tr></thead>'
        f'<tbody>{peer_rows}</tbody></table>'
        if peer_rows else
        f'<p class="ck-section-body">No other {_esc(kind_singular)}s in '
        f'{_esc(state) or "this state"}.</p>',
        title=f"Peers in {_esc(state) or 'state'}",
    )

    # ── Provenance + limitations (trust) ──
    lim = "".join(f"<li>{_esc(x)}</li>" for x in limitations)
    prov_panel = ck_panel(
        f'<p class="ck-section-body"><strong>Source:</strong> {_esc(provenance)}</p>'
        '<p class="ck-section-body" style="margin-top:6px;">Market and provider '
        'diligence context from public CMS quality data — <strong>not a final '
        'investment recommendation</strong> and not target-company financials.</p>'
        f'<ul style="font-size:12px;color:var(--sc-text-dim);line-height:1.6;'
        f'margin:6px 0 0;padding-left:18px;">{lim}</ul>',
        title="Data source & limitations",
    )

    back = (
        f'<p class="ck-section-body" style="margin:0 0 12px;">'
        f'<a href="{route}" class="ck-link">&larr; All {_esc(kind_singular)}s</a>'
        + (f' · <a href="{route}?state={_esc(state)}" class="ck-link">{_esc(state)} list</a>'
           if state else '')
        + '</p>'
    )

    body = (
        ck_page_title(name, eyebrow=eyebrow, meta=" · ".join(meta_bits))
        + back + kpis + identity_panel + quality_panel + peers_panel + prov_panel
    )
    return chartis_shell(body, name, active_nav=route)
