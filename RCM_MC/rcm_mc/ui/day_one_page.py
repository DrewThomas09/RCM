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
from typing import Any, Dict, List, Optional

from ._chartis_kit import (
    chartis_shell, ck_eyebrow, ck_help_tooltip, ck_kpi_block,
    ck_next_section, ck_panel, ck_progress_checklist,
    ck_section_intro, ck_signal_badge,
)
from .dashboard_v3 import (
    _load_alerts, _load_portfolio_summary, _load_recent_activity,
)


_DAY_ONE_STYLES = """
<style>
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
  background: var(--sc-bone, #f5f1ea);
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


def _activity_section(activity: List[Dict[str, Any]]) -> str:
    """Section IV — what changed in the last 7 days."""
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
    return (
        '<section class="do-section">'
        '<div class="do-eyebrow-wrap">'
        '<span class="do-vol">Vol IV</span>'
        + ck_eyebrow("THIS WEEK · PIPELINE PULSE")
        + '</div>'
        '<h2 class="do-h2">What <em>moved</em> in seven days.</h2>'
        f'<p class="do-prose">{prose}</p>'
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

    intro = ck_section_intro(
        eyebrow="MONDAY MORNING",
        headline="Where to start your week.",
        italic_word="start",
        body=(
            "Five surfaces in the order partners check them. Each "
            "one is a two-minute read or a click into deeper work. "
            "Begin with alerts — anything that needs a decision "
            "before lunch — and end with your platform journey."
        ),
    )

    next_up = ck_next_section(
        "Open the v3 dashboard for the full data view",
        "/?v3=1",
        eyebrow="Continue —",
        italic_word="data",
    )

    body = (
        _DAY_ONE_STYLES
        + intro
        + ck_panel(
            _alerts_section(alerts)
            + _health_section(summary)
            + _recent_section()
            + _activity_section(activity)
            + _journey_section(),
            title="The Monday brief",
        )
        + next_up
    )

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
