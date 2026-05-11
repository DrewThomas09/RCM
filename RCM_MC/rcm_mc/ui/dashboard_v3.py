"""Dashboard v3 — story-driven morning view.

Replaces the wall-of-widgets v2 layout with a narrative read:

  1. **Portfolio health at a glance** — hero strip with the
     headline numbers + a one-sentence read on overall posture.
  2. **Top opportunities** — ranked deals with biggest realistic
     EBITDA uplift potential, prose-introduced.
  3. **Key alerts** — what needs the partner's decision today,
     not 'every covenant trigger ever'.
  4. **Recent activity** — what changed since the last open
     (new packets, completed runs, regime changes).

Each section opens with a sentence framing the numbers — partner
reads top-to-bottom and gets the story, not a dashboard quiz.

Public API::

    render_dashboard_v3(store) -> str
"""
from __future__ import annotations

import html as _html
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    ck_kpi_block, ck_panel, ck_section_intro, ck_signal_badge,
)

# Editorial port (2026-04-27): dropped imports for .colors / .loading /
# .nav / .responsive / .theme — chartis_shell() now provides all the
# editorial chrome + responsive layout + theme cascade. The .global_search
# render_search_bar dropped too — chartis_shell's editorial topbar
# already includes the editorial server-rendered search input.

logger = logging.getLogger(__name__)


def _esc(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def _fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1e9:
        return f"${v / 1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v / 1e6:,.1f}M"
    if abs(v) >= 1e3:
        return f"${v / 1e3:,.0f}K"
    return f"${v:,.0f}"


def _fmt_pct(v: Optional[float], digits: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v * 100:+.{digits}f}%"


def _days_since(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        ts = datetime.fromisoformat(
            iso.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - ts).days


# ── Data assembly ────────────────────────────────────────────

def _load_portfolio_summary(
    store: Any,
) -> Dict[str, Any]:
    """Headline numbers for the hero strip."""
    summary = {
        "n_deals": 0, "n_active": 0, "n_archived": 0,
        "total_npr": 0.0, "total_ebitda": 0.0,
        "weighted_health": None,
        "best_regime": "—", "best_deal": "—",
        "worst_regime": "—", "worst_deal": "—",
    }
    try:
        deals = store.list_deals(include_archived=True)
        summary["n_deals"] = len(deals)
        if "archived" in deals.columns:
            summary["n_active"] = int(
                (~deals["archived"].astype(bool)).sum())
            summary["n_archived"] = (
                summary["n_deals"] - summary["n_active"])
        else:
            summary["n_active"] = summary["n_deals"]
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "list_deals failed: %s", exc)
    try:
        from ..analysis.analysis_store import (
            list_packets, load_packet_by_id,
        )
        rows = list_packets(store) or []
        seen = set()
        npr = 0.0
        ebitda = 0.0
        health_w = 0.0
        health_total = 0.0
        for r in rows:
            did = r.get("deal_id")
            if did in seen:
                continue
            seen.add(did)
            pkt = load_packet_by_id(store, r["id"])
            if pkt is None:
                continue
            try:
                this_npr = float(getattr(
                    pkt.financials, "net_revenue",
                    0) or 0)
                this_ebitda = float(getattr(
                    pkt.financials, "current_ebitda",
                    0) or 0)
                npr += this_npr
                ebitda += this_ebitda
                hs = getattr(
                    pkt, "health_score", None)
                if hs is not None:
                    health_w += this_npr * float(hs)
                    health_total += this_npr
            except Exception:  # noqa: BLE001
                continue
        summary["total_npr"] = npr
        summary["total_ebitda"] = ebitda
        if health_total > 0:
            summary["weighted_health"] = (
                health_w / health_total)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "packet rollup failed: %s", exc)
    return summary


def _load_top_opportunities(
    store: Any, *, limit: int = 5,
) -> List[Dict[str, Any]]:
    """Deals ranked by realistic EBITDA uplift potential."""
    out: List[Dict[str, Any]] = []
    try:
        from ..analysis.analysis_store import (
            list_packets, load_packet_by_id,
        )
        rows = list_packets(store) or []
        seen = set()
        for r in rows:
            did = r.get("deal_id")
            if did in seen:
                continue
            seen.add(did)
            pkt = load_packet_by_id(store, r["id"])
            if pkt is None:
                continue
            try:
                bridge = getattr(
                    pkt, "ebitda_bridge", None)
                if bridge is None:
                    continue
                uplift = float(getattr(
                    bridge, "total_ebitda_impact", 0)
                    or 0)
                if uplift <= 0:
                    continue
                out.append({
                    "deal_id": did,
                    "uplift": uplift,
                    "current_ebitda": float(getattr(
                        bridge, "current_ebitda", 0)
                        or 0),
                    "target_ebitda": float(getattr(
                        bridge, "target_ebitda", 0)
                        or 0),
                    "uplift_pct": float(getattr(
                        bridge, "ebitda_delta_pct", 0)
                        or 0),
                })
            except Exception:  # noqa: BLE001
                continue
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "opportunities scan failed: %s", exc)
    out.sort(key=lambda x: -x["uplift"])
    return out[:limit]


def _load_alerts(
    store: Any, *, limit: int = 8,
) -> List[Dict[str, Any]]:
    """Active alerts that need the partner's decision."""
    try:
        from ..alerts.alerts import evaluate_active
        alerts = evaluate_active(store) or []
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "alerts eval failed: %s", exc)
        return []
    out = []
    for a in alerts[:limit]:
        out.append({
            "deal_id": getattr(a, "deal_id", "—"),
            "kind": getattr(a, "kind", "—"),
            "severity": getattr(a, "severity", "info"),
            "message": getattr(a, "message", ""),
        })
    return out


def _load_recent_activity(
    store: Any, *, limit: int = 8, lookback_days: int = 7,
) -> List[Dict[str, Any]]:
    """Recent packet builds, runs, snapshots — what's changed
    since the partner last opened the platform."""
    out: List[Dict[str, Any]] = []
    try:
        from ..analysis.analysis_store import list_packets
        rows = list_packets(store) or []
        for r in rows[:30]:
            did = r.get("deal_id") or "—"
            ts = r.get("created_at") or r.get(
                "timestamp")
            days = _days_since(ts)
            if days is None or days > lookback_days:
                continue
            out.append({
                "deal_id": did,
                "kind": "packet_built",
                "label": (f"Analysis packet built "
                          f"({days}d ago)"
                          if days > 0 else
                          "Analysis packet built (today)"),
                "days": days,
            })
    except Exception:  # noqa: BLE001
        pass
    out.sort(key=lambda x: x["days"])
    return out[:limit]


# ── Section renderers ───────────────────────────────────────

# Editorial port (2026-04-27): dark-shell palette → editorial palette
# Same mapping as deal_profile_v2.py port (b283a04).
_BG_PRIMARY = "#FFFFFF"   # was #0f172a → paper-pure
_BG_SURFACE = "#FFFFFF"   # was #1f2937 → paper-pure
_BG_ELEVATED = "#FAF7F0"  # was #111827 → paper
_BORDER = "#D6CFC0"       # was #374151 → editorial border
_TEXT = "#0F1C2E"         # was #f3f4f6 → ink (dark on light)
_TEXT_DIM = "#5C6878"     # was STATUS["neutral"] → muted
_ACCENT = "#155752"       # was STATUS["info"] → teal-deep
_GREEN = "#3F7D4D"        # editorial green
_AMBER = "#B7791F"        # editorial amber
_RED = "#A53A2D"          # editorial red


def _hero_strip(summary: Dict[str, Any]) -> str:
    """Top-of-page hero with the headline numbers + one-sentence read."""
    n_deals = summary["n_deals"]
    n_active = summary["n_active"]
    npr = summary["total_npr"]
    ebitda = summary["total_ebitda"]
    health = summary["weighted_health"]

    # One-sentence narrative read
    if n_deals == 0:
        narrative = (
            "No deals in the portfolio yet — start by "
            "uploading a deal or building an analysis packet.")
    elif health is None:
        narrative = (
            f"{n_active} active deal"
            f"{'s' if n_active != 1 else ''} representing "
            f"{_fmt_money(npr)} NPR. Health scores not yet "
            f"computed — build packets to populate.")
    elif health >= 75:
        narrative = (
            f"{n_active} active deals at {health:.0f}/100 "
            f"weighted health — the portfolio is in good "
            f"shape; focus on growth plays.")
    elif health >= 60:
        narrative = (
            f"{n_active} active deals at {health:.0f}/100 "
            f"weighted health — mid-tier; one or two "
            f"underperformers are pulling the average down.")
    else:
        narrative = (
            f"{n_active} active deals at {health:.0f}/100 "
            f"weighted health — material drag, "
            f"restructuring conversations needed.")

    health_text = (f"{health:.0f}" if health is not None
                   else "—")
    health_tone = (
        "positive" if (health or 0) >= 75
        else "warning" if (health or 0) >= 60
        else "negative")
    health_badge = ck_signal_badge(health_text, tone=health_tone)

    intro = ck_section_intro(
        eyebrow="MORNING VIEW",
        headline="Where the portfolio stands today.",
        italic_word="today",
        body=narrative,
    )
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Active deals", f"{n_active}",
            sub=f"of {n_deals} total",
        )
        + ck_kpi_block(
            "Total NPR", _fmt_money(npr),
            help={
                "definition": (
                    "Net Patient Revenue — billed services minus "
                    "contractual allowances, bad debt, and charity "
                    "care. The cash-realisable top line."
                ),
                "citation": "HFMA Glossary",
            },
        )
        + ck_kpi_block(
            "Current EBITDA", _fmt_money(ebitda),
            help={
                "definition": (
                    "Earnings before interest, taxes, depreciation, "
                    "and amortization. The operating cash-flow proxy "
                    "PE partners price deals against."
                ),
            },
        )
        + ck_kpi_block(
            "Health score", health_badge,
            sub="weighted by NPR",
            help={
                "definition": (
                    "Composite 0–100 score per deal combining "
                    "covenant headroom, EBITDA variance vs plan, "
                    "denial-rate drift, and management bench depth. "
                    "Weighted by Net Patient Revenue at the "
                    "portfolio level."
                ),
                "citation": "rcm_mc/deals/health_score.py",
            },
        )
        + '</div>'
    )
    return f'{intro}{kpis}'


def _section_header(label: str, prose: str) -> str:
    """No-op kept for back-compat; sections now ride ck_panel."""
    return ""


def _opportunities_section(
    opps: List[Dict[str, Any]],
) -> str:
    if not opps:
        return ck_panel(
            '<p class="ck-section-body">'
            'No realized EBITDA uplift opportunities yet — '
            'build analysis packets to populate this list.</p>',
            title="Top opportunities",
        )

    total_uplift = sum(o["uplift"] for o in opps)
    rows = []
    for i, opp in enumerate(opps, 1):
        deal_link = (
            f'<a href="/deal/{_esc(opp["deal_id"])}" class="ck-link"><strong>{_esc(opp["deal_id"])}</strong></a>')
        rows.append(
            f'<tr>'
            f'<td class="num">{i}.</td>'
            f'<td>{deal_link}</td>'
            f'<td class="num cad-pos"><strong>+{_fmt_money(opp["uplift"])}</strong></td>'
            f'<td class="num">{_fmt_pct(opp["uplift_pct"])}</td>'
            f'<td class="num">{_fmt_money(opp["current_ebitda"])} → {_fmt_money(opp["target_ebitda"])}</td>'
            f'</tr>')
    prose = (
        f"Ranked by realistic EBITDA uplift across the active "
        f"portfolio. The top {len(opps)} represent "
        f"{_fmt_money(total_uplift)} in additional EBITDA if "
        f"value-creation plans land — start with the biggest "
        f"and work down.")
    return ck_panel(
        f'<p class="ck-section-body">{prose}</p>'
        '<table class="cad-table">'
        '<thead><tr>'
        '<th>#</th><th>Deal</th>'
        '<th class="num">EBITDA Uplift</th>'
        '<th class="num">vs. Current</th>'
        '<th class="num">Bridge</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>',
        title="Top opportunities",
    )


def _alerts_section(
    alerts: List[Dict[str, Any]],
) -> str:
    if not alerts:
        return ck_panel(
            '<p class="ck-section-body cad-pos">All clear.</p>',
            title="Key alerts",
        )
    n_critical = sum(1 for a in alerts
                     if str(a.get("severity")
                            ).lower()
                     in ("critical", "high"))
    sev_tone_map = {
        "critical": "negative", "high": "negative",
        "medium": "warning", "warning": "warning",
        "low": "neutral", "info": "neutral",
    }
    rows = []
    for a in alerts:
        sev = str(a.get("severity") or "info").lower()
        badge = ck_signal_badge(sev, tone=sev_tone_map.get(sev, "neutral"))
        rows.append(
            '<div class="dv-alert-row">'
            '<div class="dv-alert-body">'
            f'<div class="dv-alert-msg">{_esc(a.get("message", ""))}</div>'
            '<div class="ck-eyebrow">'
            f'{_esc(a.get("kind", ""))} · '
            f'<a href="/deal/{_esc(a.get("deal_id", ""))}" class="ck-link">{_esc(a.get("deal_id", ""))}</a>'
            '</div></div>'
            f'<span>{badge}</span></div>'
        )
    prose = (
        f"{len(alerts)} active alert"
        f"{'s' if len(alerts) != 1 else ''}"
        + (f", {n_critical} requiring partner attention"
           if n_critical else "")
        + ". Triage starts with red badges; amber items can wait "
          "until the weekly review.")
    return ck_panel(
        f'<p class="ck-section-body">{prose}</p>'
        f'{"".join(rows)}',
        title="Key alerts",
    )


def _activity_section(
    activity: List[Dict[str, Any]],
) -> str:
    if not activity:
        return ck_panel(
            '<p class="ck-section-body">'
            'No changes in the last week — the portfolio data is steady.</p>',
            title="Recent activity",
        )
    rows = []
    for a in activity:
        deal_id = a.get("deal_id", "")
        rows.append(
            '<div class="dv-activity-row">'
            f'<a href="/deal/{_esc(deal_id)}" class="ck-link"><strong>{_esc(deal_id)}</strong></a>'
            f'<div class="dv-activity-label">{_esc(a.get("label", ""))}</div></div>')
    prose = (
        f"{len(activity)} item"
        f"{'s' if len(activity) != 1 else ''} from the last "
        f"week. Clicking through shows what changed and "
        f"who owns it.")
    return ck_panel(
        f'<p class="ck-section-body">{prose}</p>'
        f'{"".join(rows)}',
        title="Recent activity",
    )


def _pinned_tools_rail() -> str:
    """Editorial 'Pinned tools' rail — partner-curated favorites.

    Reads ``rcm_pinned_tools`` from localStorage (an array of
    ``{href, label, phase}`` rows that the deal-profile pin button
    writes). Renders nothing on first load — JS populates the rail
    on DOMContentLoaded. Stays hidden until at least one tool is
    pinned, so the section never feels half-empty.

    Each tile is a serif arrow-link with a JetBrains-Mono phase
    eyebrow ("WORKSPACE", "DILIGENCE", "RISK", etc.) so partners
    see the lifecycle context next to the analytic label.
    """
    return """
<style>
.dv-pinned{margin:18px 0 0;padding:18px 0;
border-top:1px solid var(--sc-rule,#d8d3c8);}
.dv-pinned[hidden]{display:none !important;}
.dv-pinned-head{display:flex;align-items:baseline;
justify-content:space-between;gap:14px;margin-bottom:12px;}
.dv-pinned-eyebrow{font-family:"Inter Tight",sans-serif;
font-size:10px;font-weight:700;letter-spacing:1.4px;
text-transform:uppercase;color:var(--sc-text-faint,#6e7787);}
.dv-pinned-meta{font-family:"Source Serif 4",serif;font-style:italic;
font-size:12px;color:var(--sc-text-faint,#6e7787);}
.dv-pinned-grid{display:grid;
grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;}
.dv-pinned-tile{display:block;padding:14px 16px;
background:var(--sc-bone,#f5f1ea);
border:1px solid var(--sc-rule,#d8d3c8);border-radius:3px;
text-decoration:none;color:inherit;
transition:transform 140ms ease, border-color 140ms ease,
box-shadow 140ms ease;}
.dv-pinned-tile:hover{transform:translateY(-1px);
border-color:var(--sc-teal,#155752);
box-shadow:0 4px 14px rgba(11,35,65,0.06);}
.dv-pinned-phase{font-family:"JetBrains Mono",monospace;
font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
color:var(--sc-teal-ink,#0e3e3a);margin-bottom:6px;}
.dv-pinned-label{font-family:"Source Serif 4",serif;font-size:15px;
font-weight:500;color:var(--sc-navy,#0b2341);line-height:1.25;}
.dv-pinned-label::after{content:" →";
color:var(--sc-text-faint,#6e7787);
transition:color 120ms ease;}
.dv-pinned-tile:hover .dv-pinned-label::after{
color:var(--sc-teal-ink,#0e3e3a);}
@media print{.dv-pinned{display:none !important;}}
</style>
<section class="dv-pinned" data-rcm-pinned-rail hidden>
  <div class="dv-pinned-head">
    <span class="dv-pinned-eyebrow">Pinned tools</span>
    <span class="dv-pinned-meta" data-rcm-pinned-meta>—</span>
  </div>
  <div class="dv-pinned-grid" data-rcm-pinned-grid></div>
</section>
<script>
(function(){
  function esc(s){var d=document.createElement("div");
    d.textContent=String(s||"");return d.innerHTML;}
  function paint(){
    var rail=document.querySelector("[data-rcm-pinned-rail]");
    if(!rail)return;
    var grid=rail.querySelector("[data-rcm-pinned-grid]");
    var meta=rail.querySelector("[data-rcm-pinned-meta]");
    var rows=[];try{rows=JSON.parse(localStorage.getItem("rcm_pinned_tools")||"[]");}
    catch(e){rows=[];}
    rows=(Array.isArray(rows)?rows:[]).filter(function(r){return r&&r.href&&r.label;});
    if(rows.length===0){rail.hidden=true;return;}
    grid.innerHTML=rows.map(function(r){
      var phase=esc(r.phase||"DILIGENCE");
      return '<a class="dv-pinned-tile" href="'+esc(r.href)+'">'+
        '<div class="dv-pinned-phase">'+phase+'</div>'+
        '<div class="dv-pinned-label">'+esc(r.label)+'</div></a>';
    }).join("");
    if(meta){meta.textContent=rows.length+(rows.length===1?" tool":" tools")+
      " · pin or unpin from any deal profile";}
    rail.hidden=false;
  }
  document.addEventListener("DOMContentLoaded",paint);
}());
</script>
"""


def _recently_viewed_rail() -> str:
    """Editorial 'Recently viewed' deals rail.

    Reads ``rcm_recent_deals`` from localStorage (a JSON array of
    ``{slug, name, ts}`` rows the deal-profile JS pushes whenever a
    partner opens a deal). Renders nothing on first load — JS
    populates the rail from storage on DOMContentLoaded so partners
    returning to /app see their last 5 deals as serif arrow-links.

    The deal_profile_page already keeps ``rcm_deal_<slug>`` entries
    per deal; this rail layers a small index on top so the partner
    has one-click re-entry to whatever they were last working on
    without searching the pipeline.
    """
    return """
<style>
.dv-recent{margin:24px 0 8px;padding:18px 0;
border-top:1px solid var(--sc-rule,#d8d3c8);}
.dv-recent[hidden]{display:none !important;}
.dv-recent-head{display:flex;align-items:baseline;
justify-content:space-between;gap:14px;margin-bottom:12px;}
.dv-recent-eyebrow{font-family:"Inter Tight",sans-serif;
font-size:10px;font-weight:700;letter-spacing:1.4px;
text-transform:uppercase;color:var(--sc-text-faint,#6e7787);}
.dv-recent-clear{font-family:"Source Serif 4",serif;
font-style:italic;font-size:12px;
color:var(--sc-text-faint,#6e7787);background:none;
border:0;cursor:pointer;padding:0;
text-decoration:underline;text-decoration-color:transparent;
transition:text-decoration-color 120ms ease;}
.dv-recent-clear:hover{text-decoration-color:var(--sc-text-faint,#6e7787);}
.dv-recent-grid{display:grid;
grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;}
.dv-recent-tile{display:block;padding:14px 16px;
background:var(--sc-bone,#f5f1ea);
border:1px solid var(--sc-rule,#d8d3c8);border-radius:3px;
text-decoration:none;color:inherit;
transition:transform 140ms ease, border-color 140ms ease,
box-shadow 140ms ease;}
.dv-recent-tile:hover{transform:translateY(-1px);
border-color:var(--sc-teal,#155752);
box-shadow:0 4px 14px rgba(11,35,65,0.06);}
.dv-recent-slug{font-family:"JetBrains Mono",monospace;
font-size:10px;letter-spacing:1.2px;text-transform:uppercase;
color:var(--sc-text-faint,#6e7787);margin-bottom:4px;}
.dv-recent-name{font-family:"Source Serif 4",serif;font-size:16px;
font-weight:500;color:var(--sc-navy,#0b2341);line-height:1.25;
margin-bottom:6px;}
.dv-recent-ts{font-family:"Source Serif 4",serif;font-style:italic;
font-size:11px;color:var(--sc-text-faint,#6e7787);}
@media print{.dv-recent{display:none !important;}}
</style>
<section class="dv-recent" data-rcm-recent-rail hidden>
  <div class="dv-recent-head">
    <span class="dv-recent-eyebrow">Recently viewed</span>
    <button type="button" class="dv-recent-clear"
            data-rcm-recent-clear>Clear list</button>
  </div>
  <div class="dv-recent-grid" data-rcm-recent-grid></div>
</section>
<script>
(function(){
  var STORE="rcm_recent_deals";
  function fmtRel(ts){
    if(!ts)return"";
    var d=Math.round((Date.now()-ts)/60000);
    if(d<1)return"just now";
    if(d<60)return d+" min ago";
    if(d<1440)return Math.round(d/60)+" hr ago";
    return Math.round(d/1440)+" d ago";
  }
  function esc(s){var d=document.createElement("div");
    d.textContent=String(s||"");return d.innerHTML;}
  function paint(){
    var rail=document.querySelector("[data-rcm-recent-rail]");
    if(!rail)return;
    var grid=rail.querySelector("[data-rcm-recent-grid]");
    var rows=[];try{rows=JSON.parse(localStorage.getItem(STORE)||"[]");}
    catch(e){rows=[];}
    if(!Array.isArray(rows)||rows.length===0){rail.hidden=true;return;}
    rows=rows.filter(function(r){return r&&r.slug;}).slice(0,5);
    grid.innerHTML=rows.map(function(r){
      return '<a class="dv-recent-tile" href="/diligence/deal/'+
        encodeURIComponent(r.slug)+'">'+
        '<div class="dv-recent-slug">'+esc(r.slug)+'</div>'+
        '<div class="dv-recent-name">'+esc(r.name||r.slug)+'</div>'+
        '<div class="dv-recent-ts">'+fmtRel(r.ts)+'</div></a>';
    }).join("");
    rail.hidden=false;
  }
  document.addEventListener("DOMContentLoaded",paint);
  document.addEventListener("click",function(e){
    var btn=e.target.closest&&e.target.closest("[data-rcm-recent-clear]");
    if(!btn)return;
    if(confirm("Clear recently-viewed deals list?")){
      localStorage.removeItem(STORE);paint();}
  });
}());
</script>
"""


def _keyboard_hint_footer() -> str:
    """Small editorial footer on /app surfacing the keyboard shortcuts
    and tour entry points. Three monospace `kbd` chips with a serif
    legend — discoverable without being interruptive. Hidden in print.
    """
    return """
<style>
.dv-kb-hint{display:flex;align-items:baseline;gap:18px;flex-wrap:wrap;
margin:32px 0 12px;padding:14px 18px;
border-top:1px solid var(--sc-rule,#d8d3c8);
font-family:"Source Serif 4",serif;font-size:13px;
color:var(--sc-text-faint,#6e7787);}
.dv-kb-hint-eyebrow{font-family:"Inter Tight",sans-serif;font-size:10px;
font-weight:700;letter-spacing:1.4px;text-transform:uppercase;
color:var(--sc-text-faint,#6e7787);}
.dv-kb-hint-row{display:inline-flex;align-items:baseline;gap:6px;}
.dv-kb-hint kbd{display:inline-flex;align-items:center;justify-content:center;
min-width:20px;padding:1px 6px;
background:var(--sc-bone,#f5f1ea);
border:1px solid var(--sc-rule,#d8d3c8);border-radius:3px;
font-family:"JetBrains Mono",monospace;font-size:11px;font-weight:600;
color:var(--sc-text,#1a2332);line-height:1.4;}
.dv-kb-hint em{font-style:italic;color:var(--sc-teal-ink,#0e3e3a);}
@media print{.dv-kb-hint{display:none !important;}}
</style>
<div class="dv-kb-hint">
<span class="dv-kb-hint-eyebrow">Keyboard</span>
<span class="dv-kb-hint-row">
Press <kbd>&#8984;</kbd><kbd>K</kbd> for the command palette.
</span>
<span class="dv-kb-hint-row">
<kbd>?</kbd> for all shortcuts.
</span>
<span class="dv-kb-hint-row">
<kbd>T</kbd> to open <em>The Atlas</em>.
</span>
</div>
"""


def _tour_banner_styles() -> str:
    """Scoped styles for the first-time tour banner.

    Sits at the top of /app for new partners. Editorial parchment
    surface with teal accent rule on the left; eyebrow + prose +
    serif arrow-link CTA; small dismiss ×. Never modal, never
    interruptive — just a quiet invitation.
    """
    return """
<style>
.dv-tour-banner{display:flex;align-items:center;gap:18px;
padding:14px 20px;margin-bottom:18px;
background:var(--sc-bone,#f5f1ea);
border:1px solid var(--sc-rule,#d8d3c8);
border-left:3px solid var(--sc-teal,#155752);
border-radius:3px;position:relative;}
.dv-tour-banner[hidden]{display:none !important;}
.dv-tour-banner-eyebrow{font-family:"Inter Tight",sans-serif;
font-size:10px;font-weight:700;letter-spacing:1.6px;
text-transform:uppercase;color:var(--sc-teal-ink,#0e3e3a);
flex-shrink:0;}
.dv-tour-banner-body{flex:1;display:flex;align-items:baseline;
gap:18px;flex-wrap:wrap;}
.dv-tour-banner-prose{font-family:"Source Serif 4",serif;
font-size:14px;line-height:1.55;color:var(--sc-text-dim,#37495e);}
.dv-tour-banner-prose em{font-style:italic;
color:var(--sc-teal-ink,#0e3e3a);}
.dv-tour-banner-cta{font-family:"Source Serif 4",serif;
font-size:15px;font-weight:400;
color:var(--sc-teal-ink,#0e3e3a);text-decoration:none;
border-bottom:1px solid transparent;
transition:border-color 120ms ease;white-space:nowrap;}
.dv-tour-banner-cta:hover{border-bottom-color:var(--sc-teal-ink,#0e3e3a);}
.dv-tour-banner-close{background:none;border:0;cursor:pointer;
padding:4px 8px;font-size:20px;line-height:1;
color:var(--sc-text-faint,#6e7787);
transition:color 120ms ease;}
.dv-tour-banner-close:hover{color:var(--sc-text,#1a2332);}
@media (max-width:640px){.dv-tour-banner{flex-direction:column;
align-items:flex-start;}.dv-tour-banner-close{position:absolute;
top:8px;right:8px;}}
@media print{.dv-tour-banner{display:none !important;}}
</style>
"""


def _start_here_styles() -> str:
    """Scoped styles for the empty-portfolio 'Start here' panel.

    Three editorial cards in a grid: each a parchment-toned tile
    with an eyebrow + serif title + body description. Hover lifts
    the tile and brightens the border to flag it as clickable.
    """
    return """
<style>
.dv-start-here{margin-top:16px;}
.dv-start-grid{display:grid;
grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:14px;margin-top:16px;}
.dv-start-tile{display:block;padding:18px 20px;
background:var(--sc-bone,#f5f1ea);
border:1px solid var(--sc-rule,#d8d3c8);border-radius:3px;
text-decoration:none;color:inherit;
transition:transform 140ms ease, border-color 140ms ease,
box-shadow 140ms ease;}
.dv-start-tile:hover{transform:translateY(-2px);
border-color:var(--sc-teal,#155752);
box-shadow:0 6px 18px rgba(11,35,65,0.08);}
.dv-start-eyebrow{font-family:"Inter Tight",sans-serif;font-size:10px;
font-weight:700;letter-spacing:1.4px;text-transform:uppercase;
color:var(--sc-teal-ink,#0e3e3a);margin-bottom:8px;}
.dv-start-title{font-family:"Source Serif 4",serif;
font-size:22px;font-weight:400;line-height:1.15;letter-spacing:-0.01em;
color:var(--sc-navy,#0b2341);margin-bottom:8px;}
.dv-start-sub{font-family:"Source Serif 4",serif;font-size:13.5px;
line-height:1.55;color:var(--sc-text-dim,#37495e);}
</style>
"""


# ── Main render ─────────────────────────────────────────────

def render_dashboard_v3(store: Any) -> str:
    """Render the story-driven dashboard.

    Editorial port (2026-04-27): drop the page's own <!doctype>,
    theme_init_script, theme_stylesheet, theme_toggle, and the
    page-progress-bar / keyboard-shortcuts JS. chartis_shell()
    provides the editorial parchment + topbar + breadcrumbs +
    PHI banner + sidebar + responsive layout. Per-section helpers
    (_hero_strip / _opportunities_section / _alerts_section /
    _activity_section) keep their existing markup; the page's
    inline-styled action links convert to editorial-typed anchors.
    """
    summary = _load_portfolio_summary(store)
    opportunities = _load_top_opportunities(store)
    alerts = _load_alerts(store)
    activity = _load_recent_activity(store)

    dv_styles = """
<style>
.dv-container{max-width:1100px;margin:0 auto;padding:1.5rem 1rem;}
.dv-toplinks{display:flex;gap:14px;font-size:12px;align-items:center;
justify-content:flex-end;margin-bottom:1.5rem;}
.dv-alert-row{display:flex;align-items:center;gap:14px;
padding:14px 0;border-bottom:1px solid var(--cad-border);}
.dv-alert-body{flex:1;}
.dv-alert-msg{font-size:13px;}
.dv-activity-row{display:flex;align-items:baseline;gap:14px;
padding:12px 0;border-bottom:1px solid var(--cad-border);}
.dv-activity-label{flex:1;font-size:13px;}
</style>
"""
    # "Start here" panel — first-load orientation when the portfolio
    # is empty. Gives a fresh partner three concrete next steps
    # (import a deal, screen hospitals, take the tour) instead of an
    # ambiguous "0 deals" hero strip with no direction.
    start_here = ""
    if summary.get("n_deals", 0) == 0:
        start_here = (
            '<section class="ck-panel dv-start-here">'
            '<div class="ck-panel-head">'
            '<div class="ck-panel-title">Start here</div>'
            '</div>'
            '<div class="ck-panel-body">'
            '<p class="ck-section-body">'
            'A fresh portfolio. Three ways to get the platform '
            'working with your <em>actual</em> deal pipeline:'
            '</p>'
            '<div class="dv-start-grid">'
            '<a href="/import" class="dv-start-tile">'
            '<div class="dv-start-eyebrow">1 · Import</div>'
            '<div class="dv-start-title">Add a deal</div>'
            '<div class="dv-start-sub">'
            'Upload a CSV or paste a JSON profile. Required '
            'fields: name, NPR, EBITDA, specialty, state.'
            '</div></a>'
            '<a href="/screen" class="dv-start-tile">'
            '<div class="dv-start-eyebrow">2 · Screen</div>'
            '<div class="dv-start-title">Find hospitals</div>'
            '<div class="dv-start-sub">'
            'Filter the HCRIS universe by sub-sector, size, '
            'and margin band. Add candidates to the watchlist.'
            '</div></a>'
            '<a href="/?tour=1" class="dv-start-tile">'
            '<div class="dv-start-eyebrow">3 · Tutorial</div>'
            '<div class="dv-start-title">Take the tour</div>'
            '<div class="dv-start-sub">'
            'Seven volumes covering pipeline, diligence, risk, '
            'monte carlo, portfolio, delivery, and settings.'
            '</div></a>'
            '</div>'
            '</div></section>'
        )

    # First-time tour banner. Renders for portfolios that already
    # have deals (the empty-state "Start here" panel handles the
    # zero-deal case) and is hidden by default. Inline JS toggles
    # visibility on DOMContentLoaded if localStorage shows no prior
    # tour interaction — first-time partners see a soft editorial
    # nudge at the top of /app without it interrupting returning
    # partners. Dismissal writes to localStorage so it never replays.
    tour_banner = ""
    if summary.get("n_deals", 0) > 0:
        tour_banner = (
            '<aside class="dv-tour-banner" data-ck-tour-firstcheck '
            'hidden role="complementary">'
            '<div class="dv-tour-banner-eyebrow">New here?</div>'
            '<div class="dv-tour-banner-body">'
            '<span class="dv-tour-banner-prose">'
            'Take a two-minute walkthrough of every surface on '
            'the platform — pipeline, diligence, risk, monte '
            'carlo, portfolio, delivery. <em>The Atlas</em>, '
            'seven volumes.'
            '</span>'
            '<a class="dv-tour-banner-cta" href="/?tour=1">'
            'Begin the tour <span aria-hidden="true">→</span>'
            '</a>'
            '</div>'
            '<button type="button" class="dv-tour-banner-close" '
            'data-ck-tour-banner-dismiss '
            'aria-label="Dismiss tour banner">&times;</button>'
            '</aside>'
            '<script>'
            '(function(){var b=document.querySelector('
            '"[data-ck-tour-firstcheck]");if(!b)return;try{'
            'var raw=localStorage.getItem("rcm_tour_v1");'
            'if(!raw){b.hidden=false;}else{var s=JSON.parse(raw);'
            'if(!s||(!s.completed||s.completed.length===0)&&'
            '!s.skipped&&!s.banner_dismissed){b.hidden=false;}}'
            '}catch(e){b.hidden=false;}'
            'document.addEventListener("click",function(e){'
            'if(e.target.closest&&e.target.closest('
            '"[data-ck-tour-banner-dismiss]")){b.hidden=true;'
            'try{var raw=localStorage.getItem("rcm_tour_v1");'
            'var s=raw?JSON.parse(raw):{version:1,completed:[],'
            'lastViewed:0,skipped:false};s.banner_dismissed=true;'
            'localStorage.setItem("rcm_tour_v1",JSON.stringify(s));'
            '}catch(e){}}});}());'
            '</script>'
        )

    page_body = (
        dv_styles
        + _start_here_styles()
        + _tour_banner_styles()
        + '<div class="dv-container">'
        + '<div class="dv-toplinks">'
        + '<a href="/day-one" class="ck-link">Today\'s brief →</a>'
        + '<a href="/data/catalog?ui=v3" class="ck-link">Data →</a>'
        + '<a href="/models/quality?ui=v3" class="ck-link">Models →</a>'
        + '</div>'
        + tour_banner
        + _hero_strip(summary)
        + start_here
        + _pinned_tools_rail()
        + _opportunities_section(opportunities)
        + _alerts_section(alerts)
        + _activity_section(activity)
        + _recently_viewed_rail()
        + _keyboard_hint_footer()
        + '</div>'
    )

    from ._chartis_kit import chartis_shell
    return chartis_shell(
        page_body,
        title="Portfolio · Morning view",
        active_nav="PORTFOLIO",
        breadcrumbs=[
            ("Home", "/app"),
            ("Dashboard", None),
        ],
    )
