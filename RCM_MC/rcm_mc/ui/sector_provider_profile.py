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
from .sector_market_intel import percentile_rank
from .xray_kit import XRAY_CSS, xr_eyebrow


def _esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


# Same handoff X-Ray skin the sector screener uses (scoped to `.xr`) so the
# provider deep-dive matches its parent screener and the hospital HCRIS X-Ray:
# green accent, navy ribbon panel heads, sharp corners, mono table headers.
_PROFILE_SKIN = """
.xr .ck-link{color:var(--xr-green);}
.xr .ck-link:hover{color:var(--xr-green-deep);}
.xr .ck-panel{border-radius:0;border-color:var(--xr-rule);}
.xr .ck-panel-head{background:var(--xr-navy);border-radius:0;}
.xr .ck-kpi-block,.xr .ck-kpi{border-radius:0;}
.xr .ck-kpi-value em,.xr .ck-kpi-value .num{color:var(--xr-green);}
.xr .ck-table th{font-family:var(--xr-mono);letter-spacing:.06em;text-transform:uppercase;}
.xr .ck-table td a.ck-link{color:var(--xr-green);}
.xr-profile-eyebrow{margin-bottom:6px;}
"""


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
    locality_attr: str = "",
    locality_label: str = "",
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

    # ── Quality table: value + state-avg benchmark + state percentile ──
    all_state = peer_ccns + [ccn]
    qrows = ""
    for label, key, suffix in metrics:
        val = q.get(key)
        savg = _state_avg(quality, all_state, key)
        sorted_vals = sorted(
            quality[c][key] for c in all_state
            if c in quality and quality[c].get(key) is not None)
        pctl = percentile_rank(sorted_vals, val)
        pctl_txt = f"{pctl}th" if pctl is not None else "—"
        qrows += (
            f'<tr><td>{_esc(label)}</td>'
            f'<td class="num">{_fmt(val, suffix)}</td>'
            f'<td class="num" style="color:var(--sc-text-dim);">{_fmt(savg, suffix)}</td>'
            f'<td class="num" style="color:var(--sc-text-dim);">{pctl_txt}</td></tr>'
        )
    quality_panel = ck_panel(
        '<table class="ck-table"><thead><tr><th>Quality measure</th>'
        f'<th class="num">This {_esc(kind_singular)}</th>'
        f'<th class="num">{_esc(state) or "State"} avg</th>'
        f'<th class="num">{_esc(state) or "State"} %ile</th></tr></thead>'
        f'<tbody>{qrows}</tbody></table>'
        '<p style="font-size:11px;color:var(--sc-text-dim);margin:8px 0 0;">'
        'State average + percentile are computed across same-state '
        f'Medicare-certified {_esc(kind_singular)}s that publicly report each '
        'measure (higher percentile = better relative to state peers). '
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

    # ── Same-locality peer list (county for hospice, city for home health) ──
    locality_panel = ""
    locality = (getattr(provider, locality_attr, "") or "").strip() if locality_attr else ""
    if locality:
        loc_ccns = [c for c in peer_ccns
                    if (getattr(providers[c], locality_attr, "") or "").strip().lower()
                    == locality.lower()]
        loc_rated = sorted(
            ((c, quality.get(c, {}).get(h_key)) for c in loc_ccns),
            key=lambda kv: (kv[1] is None,
                            -(kv[1] or 0) if higher_is_better else (kv[1] or 0)),
        )
        loc_rows = ""
        for c, val in loc_rated[:8]:
            p = providers[c]
            pname = _esc(getattr(p, name_attr, "") or c)
            loc_rows += (
                f'<tr><td><a href="{route}/{_esc(c)}" class="ck-link">{pname}</a></td>'
                f'<td><span class="num">{_esc(c)}</span></td>'
                f'<td class="num">{_fmt(val, h_suffix)}</td></tr>'
            )
        ll = (locality_label or "locality").lower()
        if loc_rows:
            link = (f'{route}?state={_esc(state)}&locality='
                    + _html.escape(locality, quote=True).replace(" ", "%20"))
            locality_panel = ck_panel(
                f'<p class="ck-section-body">{len(loc_ccns):,} other Medicare-certified '
                f'{_esc(kind_singular)}s in the same {_esc(ll)} '
                f'(<strong>{_esc(locality)}</strong>), by {_esc(avg_label)}. '
                f'<a href="{link}" class="ck-link">See all &rarr;</a></p>'
                '<table class="ck-table"><thead><tr><th>Provider</th><th>CCN</th>'
                f'<th class="num">{_esc(h_label)}</th></tr></thead>'
                f'<tbody>{loc_rows}</tbody></table>',
                title=f"Peers in {_esc(locality)}",
            )
        else:
            locality_panel = ck_panel(
                f'<p class="ck-section-body">This is the only Medicare-certified '
                f'{_esc(kind_singular)} in {_esc(locality)} ({_esc(ll)}) in the '
                'CMS data — local competition would come from providers not '
                'visible in this public file.</p>',
                title=f"Peers in {_esc(locality)}",
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

    # ── 2026-05-28 style-sweep · strict Tier-1 5-block head ──
    # Powers every provider profile cascade: /dialysis/<ccn>, /snf/<ccn>,
    # /home-health/<ccn>, /hospice/<ccn>, /irf/<ccn>, /ltch/<ccn>.
    # Replaces the legacy xr_eyebrow + ck_page_title + back-link
    # triple with a single <header class="pp-head"> carrying:
    #   eyebrow + dash → serif h1 (provider name) → mono meta-line
    #   (CCN · city · ownership) → italic-first-phrase lede with
    #   real rank/benchmark verdict → source-note → status-dot legend
    _pp_head_css = """
<style>
.pp-head{padding:0 0 28px;margin:0 0 24px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac);}
.pp-head .crumb{font:500 10px/1 var(--sc-mono,monospace);
  letter-spacing:.2em;text-transform:uppercase;
  color:var(--muted,#7a8595);margin:0 0 22px;}
.pp-head .crumb a{color:var(--muted,#7a8595);text-decoration:none;}
.pp-head .crumb a:hover{color:var(--ink,#16263a);}
.pp-head .crumb .sep{color:var(--rule-hi,#b6a87f);margin:0 8px;}
.pp-head .eyebrow{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.18em;text-transform:uppercase;
  color:var(--green-deep,#154e36);display:flex;align-items:center;
  gap:12px;margin:0 0 18px;}
.pp-head .eyebrow .dash{width:24px;height:1px;
  background:var(--green-deep,#154e36);}
.pp-head h1{font:400 40px/1.05 var(--sc-serif,Georgia),serif;
  letter-spacing:-.015em;color:var(--ink,#16263a);margin:0 0 14px;}
.pp-head .meta{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted,#7a8595);margin:0 0 18px;}
.pp-head .lede{font:400 italic 16.5px/1.55 var(--sc-serif,Georgia),serif;
  color:var(--ink-2,#2b3e54);max-width:70ch;margin:0 0 18px;}
.pp-head .lede em{color:var(--green-deep,#154e36);font-style:italic;}
.pp-head .source-note{font:500 10px/1.4 var(--sc-mono,monospace);
  letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted-2,#9a9e8a);margin:0 0 16px;max-width:62ch;}
.pp-head .legend{display:flex;gap:24px;list-style:none;padding:0;
  margin:0;font:400 12.5px/1 var(--sc-sans,Inter),sans-serif;
  color:var(--ink-2,#2b3e54);flex-wrap:wrap;}
.pp-head .legend li{display:flex;align-items:center;}
.pp-head .legend .dot{width:8px;height:8px;border-radius:50%;
  display:inline-block;margin-right:10px;}
.pp-head .legend .dot.live{background:var(--green-deep,#154e36);}
.pp-head .legend .dot.computed{background:var(--ink-deep,#0e1a29);}
.pp-head .legend .dot.needs{background:var(--coral,#b04a3a);}
.pp-head .legend .dot.illustrative{background:var(--gold,#a08227);}
@media (max-width:960px){.pp-head h1{font-size:32px;}}
</style>
"""
    # Auto-derived verdict line — quotes real rank + real delta. If
    # rank is unknown the verdict honestly says so; never editorial
    # filler. The "above peers" / "below peers" framing is the
    # higher_is_better axis the caller already declared.
    if h_val is not None and rated and h_state_avg is not None:
        # Use the existing `rank` integer computed just above the
        # kpis block — it's already in scope.
        diff_h = round(h_val - h_state_avg, 2)
        better = (diff_h >= 0) if higher_is_better else (diff_h <= 0)
        diff_word = "above" if better else "below"
        verdict_text = (
            f"Ranks #{rank} of {len(rated)} rated "
            f"{_esc(kind_singular)}s in {_esc(state)} on "
            f"{_esc(h_label.lower())}, {_fmt(diff_h, h_suffix)} "
            f"{diff_word} the state mean of {_fmt(h_state_avg)}."
        )
    elif h_val is not None:
        verdict_text = (
            f"{_esc(h_label)} reads {_fmt(h_val, h_suffix)} on this "
            f"{_esc(kind_singular)}; "
            f"no state benchmark available for the comparison."
        )
    else:
        verdict_text = (
            f"No {_esc(h_label.lower())} on file for this "
            f"{_esc(kind_singular)}; the comparison panel below "
            "may be partial."
        )
    # Italic FIRST PHRASE per spec §2.3.
    if "." in verdict_text:
        _first, _rest = verdict_text.split(".", 1)
        verdict_html = f"<em>{_first.strip()}.</em>{_rest}"
    else:
        verdict_html = f"<em>{verdict_text}</em>"

    crumb_html = (
        '<nav class="crumb">'
        f'<a href="{route}">All {_esc(kind_singular)}s</a>'
        + (
            f'<span class="sep">/</span>'
            f'<a href="{route}?state={_esc(state)}">{_esc(state)} list</a>'
            if state else ""
        )
        + '<span class="sep">/</span>'
        f'<b>{_esc(getattr(provider, name_attr, "") or "Profile")}</b>'
        '</nav>'
    )

    head_block = (
        _pp_head_css
        + '<header class="pp-head">'
        + crumb_html
        + f'<div class="eyebrow"><span class="dash"></span>'
        f'{_esc(eyebrow)}</div>'
        + f'<h1>{name}</h1>'
        + f'<div class="meta">{" · ".join(meta_bits)}</div>'
        + f'<p class="lede">{verdict_html}</p>'
        + f'<p class="source-note">Source: {_esc(provenance)}</p>'
        + '<ul class="legend">'
        '<li><span class="dot live"></span>Live data</li>'
        '<li><span class="dot computed"></span>Computed</li>'
        '<li><span class="dot needs"></span>Needs data</li>'
        '<li><span class="dot illustrative"></span>Illustrative</li>'
        '</ul>'
        '</header>'
    )

    body = (
        head_block
        + '<div class="xr">'
        + kpis + identity_panel + quality_panel
        + peers_panel + locality_panel + prov_panel
        + '</div>'
    )
    return chartis_shell(body, name, active_nav=route,
                         extra_css=XRAY_CSS + _PROFILE_SKIN)
