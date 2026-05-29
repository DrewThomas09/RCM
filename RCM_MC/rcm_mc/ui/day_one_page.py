"""Monday-morning editorial workflow — ``/day-one``.

Reads as a partner's curated daily ritual rather than another
dashboard. Five short editorial sections in the order partners check
them on a Monday morning:

  I.   Alerts            — anything firing?
  II.  Portfolio health  — composite scores at a glance
  III. Where you left off — recently-viewed deals (JS-hydrated)
  IV.  This week's pipeline — new + advanced deals in the last 7d
  V.   Your journey      — onboarding checklist state

Pure composition: pulls existing loaders from dashboard_v3 +
ck_progress_checklist from _chartis_kit. No new server endpoints, no
new SQL, no synthesis. Editorial cadence throughout — eyebrow + serif
italic-accent headline + body + arrow-link per section.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_help_tooltip, ck_kpi_block,
    ck_next_section, ck_panel, ck_progress_checklist,
    ck_section_intro, ck_signal_badge,
)
from .dashboard_v3 import (
    _load_alerts, _load_portfolio_summary, _load_recent_activity,
    _load_recent_packets,
)


_DAY_ONE_STYLES = """
<style>
.do-datestamp {
  display: flex; align-items: baseline; gap: 14px;
  margin: 0 0 18px;
  padding: 12px 0 14px;
  border-bottom: 1px solid var(--sc-rule, #d8d3c8);
}
.do-datestamp-day {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-weight: 400; font-size: 18px;
  color: var(--sc-teal-ink, #0e3e3a);
}
.do-datestamp-date {
  font-family: "Source Serif 4", serif; font-weight: 500;
  font-size: 18px; color: var(--sc-navy, #0b2341);
}
.do-datestamp-week {
  font-family: "JetBrains Mono", monospace; font-size: 10px;
  letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--sc-text-faint, #6e7787);
  margin-left: auto;
}
.do-section { margin-bottom: 28px; }
.do-eyebrow-wrap {
  display: flex; align-items: baseline; gap: 10px;
  margin-bottom: 8px;
}
.do-vol {
  font-family: "JetBrains Mono", monospace;
  font-size: 11px; font-weight: 700; letter-spacing: 0.16em;
  color: var(--sc-text-faint, #6e7787);
}
.do-h2 {
  font-family: "Source Serif 4", serif; font-weight: 400;
  font-size: 26px; line-height: 1.2; letter-spacing: -0.012em;
  color: var(--sc-navy, #0b2341); margin: 0 0 8px;
}
.do-h2 em {
  font-style: italic; color: var(--sc-teal-ink, #0e3e3a);
}
.do-prose {
  font-family: "Source Serif 4", serif;
  font-size: 14px; line-height: 1.6;
  color: var(--sc-text-dim, #37495e); max-width: 64ch;
  margin: 0 0 12px;
}
.do-prose em { font-style: italic; color: var(--sc-teal-ink, #0e3e3a); }
.do-prose strong {
  font-weight: 600; color: var(--sc-navy, #0b2341);
}
.do-alerts-list { list-style: none; padding: 0; margin: 8px 0 12px; }
.do-alert-row {
  display: grid; grid-template-columns: 90px 1fr;
  gap: 14px; align-items: baseline;
  padding: 10px 0; border-bottom: 1px solid var(--sc-rule, #d8d3c8);
}
.do-alert-row:last-child { border-bottom: 0; }
.do-alert-deal {
  font-family: "JetBrains Mono", monospace;
  font-size: 11px; color: var(--sc-text-faint, #6e7787);
  letter-spacing: 0.12em; text-transform: uppercase;
}
.do-alert-msg {
  font-family: "Source Serif 4", serif;
  font-size: 14px; line-height: 1.5;
  color: var(--sc-text, #1a2332);
}
.do-quiet {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 14px; color: var(--sc-text-dim, #37495e);
  padding: 14px 18px;
  border-left: 3px solid var(--sc-positive, #0a8a5f);
  background: var(--sc-bone, #f2ede3);
  margin: 8px 0 12px;
}
.do-recent { margin: 8px 0 12px; }
.do-recent[hidden] { display: none !important; }
.do-recent-list { list-style: none; padding: 0; margin: 0; }
.do-recent-empty {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 14px; color: var(--sc-text-faint, #6e7787);
}
.do-recent-row {
  display: grid; grid-template-columns: 110px 1fr 85px 90px;
  gap: 12px; align-items: baseline;
  padding: 10px 0; border-bottom: 1px solid var(--sc-rule, #d8d3c8);
}
.do-recent-q {
  font-family: "Inter Tight", sans-serif; font-size: 9px;
  font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--sc-warning, #b8732a);
  border: 1px solid currentColor; border-radius: 2px;
  padding: 1px 6px; align-self: center;
  white-space: nowrap;
}
.do-recent-q[hidden] { display: none !important; }
.do-recent-row:last-child { border-bottom: 0; }
.do-recent-slug {
  font-family: "JetBrains Mono", monospace; font-size: 10.5px;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--sc-text-faint, #6e7787);
}
.do-recent-name {
  font-family: "Source Serif 4", serif; font-size: 15px;
  font-weight: 500; color: var(--sc-navy, #0b2341);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 120ms ease;
}
.do-recent-name:hover {
  border-bottom-color: var(--sc-navy, #0b2341);
}
.do-recent-ts {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 12px; color: var(--sc-text-faint, #6e7787);
  text-align: right;
}
.do-kpi-row {
  display: flex; gap: 24px; margin: 8px 0 12px; flex-wrap: wrap;
}
.do-kpi { min-width: 90px; }
.do-kpi-val {
  font-family: "JetBrains Mono", monospace;
  font-size: 22px; font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--sc-navy, #0b2341); line-height: 1;
}
.do-kpi-lbl {
  font-family: "Inter Tight", sans-serif; font-size: 10px;
  letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--sc-text-faint, #6e7787); margin-top: 6px;
}
.do-link {
  display: inline-block; margin-top: 8px;
  font-family: "Source Serif 4", serif; font-size: 14px;
  color: var(--sc-teal-ink, #0e3e3a); text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 120ms ease;
}
.do-link:hover {
  border-bottom-color: var(--sc-teal-ink, #0e3e3a);
}
.do-link::after { content: " →"; }
@media print { .do-recent { display: none; } }
</style>
"""


def _alerts_section(alerts: List[Dict[str, Any]]) -> str:
    """Section I — anything firing this morning?"""
    if alerts:
        rows = []
        # Take top 3 by severity for the Monday brief
        sev_order = {
            "critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4,
        }
        sorted_alerts = sorted(
            alerts,
            key=lambda a: sev_order.get(a.get("severity", "info"), 5),
        )[:3]
        for a in sorted_alerts:
            tone = (
                "critical" if a.get("severity") == "critical"
                else "negative" if a.get("severity") == "high"
                else "warning" if a.get("severity") == "medium"
                else "neutral"
            )
            badge = ck_signal_badge(
                str(a.get("severity", "info")).upper(),
                tone=tone,
            )
            rows.append(
                '<li class="do-alert-row">'
                f'<div class="do-alert-deal">'
                f'{_html.escape(str(a.get("deal_id", "—")))}'
                f' {badge}</div>'
                f'<div class="do-alert-msg">'
                f'{_html.escape(str(a.get("message", "")))}</div>'
                '</li>'
            )
        body_html = (
            '<ul class="do-alerts-list">'
            + "".join(rows)
            + '</ul>'
        )
        if len(alerts) > 3:
            body_html += (
                f'<p class="do-prose" style="font-style:italic;">'
                f'+ {len(alerts) - 3} more.'
                '</p>'
            )
    else:
        body_html = (
            '<p class="do-quiet">'
            '<strong>All quiet.</strong> No alerts above the '
            'ack threshold this morning. Move on.'
            '</p>'
        )
    return (
        '<section class="do-section">'
        '<div class="do-eyebrow-wrap">'
        '<span class="do-vol">Vol I</span>'
        + ck_eyebrow("ALERTS · ANYTHING FIRING")
        + '</div>'
        '<h2 class="do-h2">What demands a <em>decision</em>.</h2>'
        '<p class="do-prose">'
        'Alerts fire when covenant headroom narrows, EBITDA misses '
        'plan, or initiative variance crosses thresholds. The top '
        'three by severity:'
        '</p>'
        + body_html
        + '<a href="/alerts" class="do-link">Open all alerts</a>'
        + '</section>'
    )


def _health_section(summary: Dict[str, Any]) -> str:
    """Section II — portfolio health at a glance."""
    n_deals = summary.get("n_deals", 0)
    n_active = summary.get("n_active", 0)
    npr = summary.get("total_npr") or 0
    health = summary.get("weighted_health")
    health_text = (
        f"{health:.0f} / 100" if health is not None else "—"
    )
    npr_text = (
        f"${npr/1e9:.2f}B" if npr >= 1e9
        else f"${npr/1e6:.0f}M" if npr >= 1e6
        else f"${npr:,.0f}"
    )
    health_prose = (
        f"The composite score for the {n_active} active "
        f"deal{'s' if n_active != 1 else ''} weights individual "
        f"health scores by Net Patient Revenue."
        if health is not None else
        "Health scores require analysis packets — build one from "
        "any deal profile to populate this number."
    )
    return (
        '<section class="do-section">'
        '<div class="do-eyebrow-wrap">'
        '<span class="do-vol">Vol II</span>'
        + ck_eyebrow("PORTFOLIO HEALTH")
        + '</div>'
        '<h2 class="do-h2">The composite, <em>weighted</em>.</h2>'
        '<p class="do-prose">'
        + health_prose
        + '</p>'
        '<div class="do-kpi-row">'
        f'<div class="do-kpi"><div class="do-kpi-val">{n_deals}</div>'
        f'<div class="do-kpi-lbl">Total deals</div></div>'
        f'<div class="do-kpi"><div class="do-kpi-val">{n_active}</div>'
        f'<div class="do-kpi-lbl">Active</div></div>'
        f'<div class="do-kpi"><div class="do-kpi-val">{npr_text}</div>'
        f'<div class="do-kpi-lbl">Total NPR</div></div>'
        f'<div class="do-kpi"><div class="do-kpi-val">{health_text}</div>'
        f'<div class="do-kpi-lbl">Weighted health</div></div>'
        '</div>'
        '<a href="/portfolio" class="do-link">Open the portfolio</a>'
        '</section>'
    )


def _recent_section() -> str:
    """Section III — JS-hydrated from rcm_recent_deals localStorage.

    Server renders empty / loading state; JS paints up to 3 most
    recent rows on DOMContentLoaded. If localStorage is empty the
    section shows an italic editorial empty state with a link to
    the pipeline.
    """
    return """
<section class="do-section">
  <div class="do-eyebrow-wrap">
    <span class="do-vol">Vol III</span>
    <div class="ck-eyebrow">WHERE YOU LEFT OFF</div>
  </div>
  <h2 class="do-h2">Three deals open from <em>last week</em>.</h2>
  <p class="do-prose">
    Pulled from your browser. Click any row to resume — your deal
    parameters are still in localStorage, so every analytic opens
    pre-filled.
  </p>
  <div class="do-recent" data-rcm-recent-section>
    <ul class="do-recent-list" data-rcm-recent-list></ul>
    <p class="do-recent-empty" data-rcm-recent-empty hidden>
      No deals opened yet. Start one from the
      <a href="/pipeline" class="ck-link">pipeline</a>.
    </p>
  </div>
  <a href="/pipeline" class="do-link">Open the full pipeline</a>
</section>
<script>
(function() {
  var STORE = "rcm_recent_deals";
  function esc(s) {
    var d = document.createElement("div");
    d.textContent = String(s || "");
    return d.innerHTML;
  }
  function relTime(ts) {
    if (!ts) return "";
    var d = Math.round((Date.now() - ts) / 60000);
    if (d < 1) return "just now";
    if (d < 60) return d + " min ago";
    if (d < 1440) return Math.round(d / 60) + " hr ago";
    return Math.round(d / 1440) + " d ago";
  }
  document.addEventListener("DOMContentLoaded", function() {
    var list = document.querySelector("[data-rcm-recent-list]");
    var empty = document.querySelector("[data-rcm-recent-empty]");
    if (!list) return;
    var rows = [];
    try { rows = JSON.parse(localStorage.getItem(STORE) || "[]"); }
    catch (e) { rows = []; }
    rows = (Array.isArray(rows) ? rows : []).filter(function(r) {
      return r && r.slug;
    }).slice(0, 3);
    if (rows.length === 0) {
      list.style.display = "none";
      if (empty) empty.hidden = false;
      return;
    }
    function openQuestions(slug) {
      try {
        var raw = localStorage.getItem(
          "rcm_deal_" + slug + "_questions");
        if (!raw) return 0;
        var qs = JSON.parse(raw);
        if (!Array.isArray(qs)) return 0;
        return qs.filter(function(q) { return q && !q.asked; }).length;
      } catch (e) { return 0; }
    }
    list.innerHTML = rows.map(function(r) {
      var qOpen = openQuestions(r.slug);
      var qChip = qOpen > 0
        ? '<span class="do-recent-q">' + qOpen + ' open ' +
            (qOpen === 1 ? 'q' : 'qs') + '</span>'
        : '<span></span>';
      return '<li class="do-recent-row">' +
        '<span class="do-recent-slug">' + esc(r.slug) + '</span>' +
        '<a class="do-recent-name" href="/diligence/deal/' +
          encodeURIComponent(r.slug) + '">' +
          esc(r.name || r.slug) + '</a>' +
        qChip +
        '<span class="do-recent-ts">' + relTime(r.ts) + '</span>' +
      '</li>';
    }).join("");
  });
}());
</script>
"""


def _activity_section(
    activity: List[Dict[str, Any]],
    packets: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Section IV — what changed in the last 7 days.

    ``packets`` is the optional Phase U recent-packets cohort
    (analysis_runs server-side, last 14 days, dedup'd per deal).
    When present, the section renders a small inline 'Built this
    fortnight' rail below the prose so partners see the specific
    deals + scenarios in the Monday brief without bouncing to /app.
    """
    n_changes = len(activity)
    if n_changes == 0:
        prose = (
            "No packet builds, snapshot rolls, or pipeline "
            "advancements in the last seven days. The portfolio "
            "is steady — a good week to catch up on diligence."
        )
    else:
        prose = (
            f"<strong>{n_changes}</strong> change"
            f"{'s' if n_changes != 1 else ''} in the last seven "
            "days. The pipeline pulse below shows the cohort of "
            "deals that advanced, the new entries, and the packet "
            "rebuilds."
        )
    # Inline 'Built this fortnight' tile strip — surfaces the
    # Phase U server-side packet roster directly in the Monday
    # brief so partners scan recent IC-ready deals without
    # leaving the page.
    packet_html = ""
    if packets:
        tiles = []
        for p in packets[:4]:
            did = _html.escape(str(p.get("deal_id", "—")))
            scn = _html.escape(str(p.get("scenario_id") or "base").upper())
            days = p.get("days", 0) or 0
            rel = ("today" if days <= 0
                   else "yesterday" if days == 1
                   else f"{days} d ago")
            tiles.append(
                f'<a class="do-packet-tile" href="/analysis/{did}">'
                f'<div class="do-packet-scn">{scn}</div>'
                f'<div class="do-packet-name">{did}</div>'
                f'<div class="do-packet-ts">{rel}</div>'
                '</a>'
            )
        packet_html = (
            '<style>'
            '.do-packet-strip{display:grid;'
            'grid-template-columns:repeat(auto-fill,minmax(190px,1fr));'
            'gap:10px;margin:12px 0 8px;}'
            '.do-packet-tile{display:block;padding:12px 14px;'
            'background:var(--sc-bone,#f2ede3);'
            'border:1px solid var(--sc-rule,#d8d3c8);'
            'border-radius:3px;text-decoration:none;color:inherit;'
            'transition:transform 140ms ease, border-color 140ms ease, '
            'box-shadow 140ms ease;}'
            '.do-packet-tile:hover{transform:translateY(-1px);'
            'border-color:var(--sc-teal,#155752);'
            'box-shadow:0 4px 14px rgba(11,35,65,0.06);}'
            '.do-packet-scn{font-family:"JetBrains Mono",monospace;'
            'font-size:9px;letter-spacing:1.3px;text-transform:uppercase;'
            'color:var(--sc-teal-ink,#0e3e3a);margin-bottom:5px;}'
            '.do-packet-name{font-family:"Source Serif 4",serif;'
            'font-size:14px;font-weight:500;'
            'color:var(--sc-navy,#0b2341);line-height:1.25;}'
            '.do-packet-ts{font-family:"Source Serif 4",serif;'
            'font-style:italic;font-size:11px;'
            'color:var(--sc-text-faint,#6e7787);margin-top:4px;}'
            '@media print{.do-packet-strip{display:none !important;}}'
            '</style>'
            '<div class="ck-eyebrow" style="margin:10px 0 4px;">'
            f'Built this fortnight · {len(packets)} '
            f'packet{"s" if len(packets) != 1 else ""}</div>'
            '<div class="do-packet-strip">' + "".join(tiles) + '</div>'
        )
    return (
        '<section class="do-section">'
        '<div class="do-eyebrow-wrap">'
        '<span class="do-vol">Vol IV</span>'
        + ck_eyebrow("THIS WEEK · PIPELINE PULSE")
        + '</div>'
        '<h2 class="do-h2">What <em>moved</em> in seven days.</h2>'
        f'<p class="do-prose">{prose}</p>'
        + packet_html +
        '<a href="/pipeline" class="do-link">'
        'Open the pipeline funnel</a>'
        '</section>'
    )


def _journey_section() -> str:
    """Section V — onboarding checklist state."""
    checklist = ck_progress_checklist([
        {
            "id": "j1",
            "title": "Open your first deal profile",
            "check": "recent_deals",
        },
        {
            "id": "j2",
            "title": "Start The Atlas — the editorial tour",
            "check": "tour_started",
        },
        {
            "id": "j3",
            "title": "Run your first analytic",
            "check": "any_tool_visited",
        },
        {
            "id": "j4",
            "title": "Open an IC memo or packet",
            "check": "ic_memo_visited",
        },
        {
            "id": "j5",
            "title": "Complete the full tour",
            "check": "tour_completed",
        },
    ])
    return (
        '<section class="do-section">'
        '<div class="do-eyebrow-wrap">'
        '<span class="do-vol">Vol V</span>'
        + ck_eyebrow("YOUR JOURNEY")
        + '</div>'
        '<h2 class="do-h2">Five milestones, one <em>arc</em>.</h2>'
        '<p class="do-prose">'
        'The platform is a workflow, not a dashboard. Each milestone '
        'unlocks the next surface — by the time the bar is full, '
        'you\'ve touched every diligence tool that matters.'
        '</p>'
        # State-conditional one-liner — partners see different
        # editorial copy based on where they are in the journey.
        # Server-emits the placeholder; inline JS picks the line
        # from rcm_tour_v1 + any *_visited entries.
        '<p class="do-prose do-journey-state" data-rcm-journey-state '
        'style="font-style:italic;font-size:13px;'
        'color:var(--sc-teal-ink,#0e3e3a);">—</p>'
        + checklist
        + '<a href="/diligence/questions" class="do-link" '
        'style="margin-right:18px;">'
        'Open the portfolio question ledger'
        '</a>'
        '<a href="/settings" class="do-link">'
        'Open settings for the full journey'
        '</a>'
        # Inline JS picks the contextual line. Quiet defaults when
        # localStorage is empty, encouraging when partially through,
        # congratulatory when complete.
        '<script>'
        '(function(){var el=document.querySelector('
        '"[data-rcm-journey-state]");if(!el)return;'
        'function tour(){try{var r=localStorage.getItem("rcm_tour_v1");'
        'return r?JSON.parse(r):null;}catch(e){return null;}}'
        'function recentN(){try{var r=JSON.parse(localStorage.getItem('
        '"rcm_recent_deals")||"[]");return Array.isArray(r)?r.length:0;}'
        'catch(e){return 0;}}'
        'function anyTool(){try{for(var i=0;i<localStorage.length;i++){'
        'var k=localStorage.key(i);if(k&&/_visited$/.test(k)){'
        'var v=JSON.parse(localStorage.getItem(k)||"{}");'
        'if(v&&Object.keys(v).length)return true;}}return false;}'
        'catch(e){return false;}}'
        'var s=tour();var done=(s&&s.completed)?s.completed.length:0;'
        'var n=recentN();var line;'
        'if(done>=7){line="All seven volumes complete \\u2014 the '
        'tour is yours to <em>restart</em> any time from Settings.";}'
        'else if(done>0){line="Volume "+done+" of VII complete \\u2014 '
        '<em>press T</em> anywhere to pick up where you left off.";}'
        'else if(anyTool()){line="You\\u2019re using the platform '
        'already \\u2014 the tour fills in the <em>why</em>. '
        'Press T to start Volume I.";}'
        'else if(n>0){line="You opened a deal \\u2014 try the '
        '<em>tour</em> (press T) to see what every analytic does.";}'
        'else{line="Everything begins at the pipeline. Open a deal, '
        'or <em>press T</em> for the seven-volume tour.";}'
        'el.innerHTML=line;}());'
        '</script>'
        + '</section>'
    )


def render_day_one(store: Any) -> str:
    """Compose the Monday-morning brief.

    Pulls live portfolio summary + alerts + recent activity from the
    same loaders as the v3 dashboard, then renders five editorial
    volumes in the order partners check them on a Monday morning.
    """
    summary = _load_portfolio_summary(store)
    alerts = _load_alerts(store, limit=8)
    activity = _load_recent_activity(store, lookback_days=7)
    recent_packets = _load_recent_packets(store, limit=4)

    # Date stamp — partners glance at the brief and immediately
    # know which Monday it covers. Calendar date + weekday + ISO
    # week number gives them three reads on temporal context.
    now = datetime.now(timezone.utc)
    weekday = now.strftime("%A")
    iso_week = now.isocalendar()[1]

    # 2026-05-28 style-sweep · strict Tier-1 5-block head. Replaces
    # the legacy date-stamp + ck_section_intro pair with a single
    # editorial header. The date stamp content folds into the mono
    # meta-line; the eyebrow names the weekday brief; the lede
    # carries the partner-facing italic-first-phrase guidance.
    n_alerts = len(alerts) if alerts else 0
    n_activity = len(activity) if activity else 0
    n_packets = len(recent_packets) if recent_packets else 0
    # Auto-derived counts in the meta-line — never hard-coded.
    meta_bits = [
        f"WEEK {iso_week:02d}",
        f"{now.strftime('%Y-%m-%d').upper()}",
    ]
    if n_alerts:
        meta_bits.append(
            f"{n_alerts} ALERT{'S' if n_alerts != 1 else ''}"
        )
    if n_activity:
        meta_bits.append(
            f"{n_activity} ACTIVITY ITEM{'S' if n_activity != 1 else ''}"
        )
    if n_packets:
        meta_bits.append(
            f"{n_packets} RECENT PACKET{'S' if n_packets != 1 else ''}"
        )
    meta_line = " · ".join(meta_bits)

    _do_head_css = """
<style>
.do-head{padding:0 0 28px;margin:0 0 24px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac);}
.do-head .eyebrow{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.18em;text-transform:uppercase;
  color:var(--green-deep,#154e36);display:flex;align-items:center;
  gap:12px;margin:0 0 18px;}
.do-head .eyebrow .dash{width:24px;height:1px;
  background:var(--green-deep,#154e36);}
.do-head h1{font:400 44px/1.05 var(--sc-serif,Georgia),serif;
  letter-spacing:-.015em;color:var(--ink,#16263a);margin:0 0 14px;}
.do-head .meta{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted,#7a8595);margin:0 0 18px;}
.do-head .lede{font:400 italic 16.5px/1.55 var(--sc-serif,Georgia),serif;
  color:var(--ink-2,#2b3e54);max-width:68ch;margin:0 0 18px;}
.do-head .lede em{color:var(--green-deep,#154e36);font-style:italic;}
.do-head .legend{display:flex;gap:24px;list-style:none;padding:0;
  margin:0;font:400 12.5px/1 var(--sc-sans,Inter),sans-serif;
  color:var(--ink-2,#2b3e54);flex-wrap:wrap;}
.do-head .legend li{display:flex;align-items:center;}
.do-head .legend .dot{width:8px;height:8px;border-radius:50%;
  display:inline-block;margin-right:10px;}
.do-head .legend .dot.live{background:var(--green-deep,#154e36);}
.do-head .legend .dot.computed{background:var(--ink-deep,#0e1a29);}
.do-head .legend .dot.needs{background:var(--coral,#b04a3a);}
.do-head .legend .dot.illustrative{background:var(--gold,#a08227);}
@media (max-width:960px){.do-head h1{font-size:36px;}}
</style>
"""
    intro = (
        _do_head_css
        + '<header class="do-head">'
        f'<div class="eyebrow"><span class="dash"></span>'
        f'{weekday.upper()} BRIEF</div>'
        f'<h1>Day One — {weekday}, '
        f'{now.strftime("%B")} {now.day}</h1>'
        f'<div class="meta">{meta_line}</div>'
        '<p class="lede">'
        '<em>Where to start your week.</em> '
        'Five surfaces in the order partners check them. Each '
        'one is a two-minute read or a click into deeper work. '
        'Begin with alerts — anything that needs a decision '
        'before lunch — and end with your platform journey.</p>'
        '<ul class="legend">'
        '<li><span class="dot live"></span>Live data</li>'
        '<li><span class="dot computed"></span>Computed</li>'
        '<li><span class="dot needs"></span>Needs data</li>'
        '<li><span class="dot illustrative"></span>Illustrative</li>'
        '</ul>'
        '</header>'
    )
    # The legacy `date_stamp` block is now subsumed into the head's
    # mono meta-line (`WEEK NN · YYYY-MM-DD · ...`); kept here as an
    # empty string so the body assembly below doesn't 500 on a name
    # reference, but it no longer renders separately.
    date_stamp = ""

    # 2026-05-29: drop the internal "v3 dashboard" vocabulary leak from
    # the partner-facing CTA copy. URL (/?v3=1) is unchanged — it's the
    # legacy flag that still routes to the morning dashboard view.
    next_up = ck_next_section(
        "Open the morning dashboard for the full view",
        "/?v3=1",
        eyebrow="Continue —",
        italic_word="dashboard",
    )

    body = (
        _DAY_ONE_STYLES
        + date_stamp
        + intro
        + ck_panel(
            _alerts_section(alerts)
            + _health_section(summary)
            + _recent_section()
            + _activity_section(activity, recent_packets)
            + _journey_section(),
            title="The Monday brief",
        )
        + next_up
    )

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        title="Day One — Monday brief",
        active_nav="PORTFOLIO",
        breadcrumbs=[
            ("Home", "/"),
            ("Day One", None),
        ],
        subtitle=(
            "Curated morning ritual · alerts → health → recent → "
            "pipeline → your journey"
        ),
    )
