"""Portfolio HTML dashboard (Brick 50).

Consumes the deal-snapshots store and renders a single self-contained HTML
page a PE partner opens weekly. Answers five questions:

1. **How is the portfolio performing?** Weighted MOIC, IRR, Σ entry EV
2. **Where are we in the funnel?** Stage counts with visual pipeline
3. **Which deals are at risk?** Covenant heatmap (SAFE / TIGHT / TRIPPED)
4. **Which deals are concerning?** Watchlist count per deal (from B30 signals)
5. **What's in the portfolio?** Full table of latest-per-deal snapshots

No external dependencies (no Chart.js, no D3) — everything renders with
inline styles + SVG so it works offline in any browser, and emails, and
pastes into Notion.
"""
from __future__ import annotations

import html
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .store import PortfolioStore
from .portfolio_snapshots import (
    DEAL_STAGES,
    latest_per_deal,
    portfolio_rollup,
)


# ── Style palette (shared with the rest of the product) ──
_PALETTE = {
    "bg":       "#FAFAFA",
    "card":     "#FFFFFF",
    "border":   "#E5E7EB",
    "text":     "#111827",
    "muted":    "#6B7280",
    "accent":   "#1F4E78",
    "green":    "#10B981",
    "amber":    "#F59E0B",
    "red":      "#EF4444",
    "blue":     "#3B82F6",
}


def _fmt_money(v: Any) -> str:
    if v is None:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    sign = "-" if f < 0 else ""
    af = abs(f)
    if af >= 1e9:
        return f"{sign}${af/1e9:.2f}B"
    if af >= 1e6:
        return f"{sign}${af/1e6:.0f}M"
    return f"{sign}${af:,.0f}"


def _fmt_pct(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v)*100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_moic(v: Any) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):.2f}x"
    except (TypeError, ValueError):
        return "—"


def _color_for_moic(v: Optional[float]) -> str:
    """Color coding matches PE IC norms: ≥2.5x green, ≥2.0x amber, <2.0x red."""
    if v is None:
        return _PALETTE["muted"]
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _PALETTE["muted"]
    if f >= 2.5:
        return _PALETTE["green"]
    if f >= 2.0:
        return _PALETTE["amber"]
    return _PALETTE["red"]


def _color_for_irr(v: Optional[float]) -> str:
    """≥25% green, ≥18% amber, <18% red — standard PE hurdle."""
    if v is None:
        return _PALETTE["muted"]
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _PALETTE["muted"]
    if f >= 0.25:
        return _PALETTE["green"]
    if f >= 0.18:
        return _PALETTE["amber"]
    return _PALETTE["red"]


def _color_for_covenant(status: Optional[str]) -> str:
    return {
        "SAFE": _PALETTE["green"],
        "TIGHT": _PALETTE["amber"],
        "TRIPPED": _PALETTE["red"],
    }.get(str(status or ""), _PALETTE["muted"])


# ── HTML building blocks ───────────────────────────────────────────────────

def _render_portfolio_pulse(store) -> str:
    """B144: single one-liner synthesizing alert + deadline state.

    Reads live evaluators so the partner's first glance at ``/``
    answers "what's the state of the world right now?" — no need to
    navigate to /alerts + /deadlines individually.
    """
    from ..alerts.alerts import evaluate_active
    from ..deals.deal_deadlines import overdue, upcoming
    try:
        alerts = evaluate_active(store)
    except Exception:  # noqa: BLE001
        alerts = []
    red = sum(1 for a in alerts if a.severity == "red")
    amber = sum(1 for a in alerts if a.severity == "amber")
    try:
        od = overdue(store)
    except Exception:  # noqa: BLE001
        import pandas as _pd
        od = _pd.DataFrame()
    try:
        up = upcoming(store, days_ahead=7)
    except Exception:  # noqa: BLE001
        import pandas as _pd
        up = _pd.DataFrame()

    if not (red or amber or (not od.empty) or (not up.empty)):
        return ""  # nothing to surface — dashboard stays clean

    parts = []
    if red:
        parts.append(
            f'<a href="/alerts" style="color: var(--red-text); '
            f'font-weight: 700; text-decoration: none;">{red} red</a>'
        )
    if amber:
        parts.append(
            f'<a href="/alerts" style="color: var(--amber-text); '
            f'font-weight: 700; text-decoration: none;">{amber} amber</a>'
        )
    if not od.empty:
        parts.append(
            f'<a href="/deadlines" style="color: var(--red-text); '
            f'font-weight: 600; text-decoration: none;">'
            f'{len(od)} overdue</a>'
        )
    if not up.empty:
        parts.append(
            f'<a href="/deadlines" style="color: var(--muted); '
            f'text-decoration: none;">'
            f'{len(up)} upcoming</a>'
        )
    sep = ' <span class="muted">·</span> '
    return (
        f'<div style="margin-bottom: 1rem; font-size: 0.95rem;">'
        f'<span class="muted" style="font-size: 0.82rem; '
        f'text-transform: uppercase; letter-spacing: 0.05em; '
        f'font-weight: 600; margin-right: 0.5rem;">Pulse</span>'
        f'{sep.join(parts)}'
        f'</div>'
    )


def _render_health_distribution(store, df) -> str:
    """B140: portfolio-wide health mix as a horizontal stacked bar.

    Counts deals in each band (green/amber/red) using the composite
    health score. Renders as a single card with a proportional bar
    and the numeric breakdown alongside.
    """
    if df is None or df.empty:
        return ""
    from ..deals.health_score import compute_health
    counts = {"green": 0, "amber": 0, "red": 0}
    for did in df["deal_id"]:
        h = compute_health(store, str(did))
        if h["score"] is None:
            continue
        band = h["band"]
        if band in counts:
            counts[band] += 1
    total = sum(counts.values())
    if total == 0:
        return ""

    def pct(n):
        return (n / total) * 100.0

    green_pct = pct(counts["green"])
    amber_pct = pct(counts["amber"])
    red_pct = pct(counts["red"])

    return f"""
    <div class="card">
      <h2>Portfolio health</h2>
      <div style="display: flex; align-items: center; gap: 1rem;
                  flex-wrap: wrap;">
        <div style="flex: 1; min-width: 20rem; display: flex;
                    height: 1.4rem; border-radius: 6px; overflow: hidden;
                    border: 1px solid var(--border);">
          <div style="background: var(--green); width: {green_pct:.1f}%;"
               title="Green: {counts['green']} deals"></div>
          <div style="background: var(--amber); width: {amber_pct:.1f}%;"
               title="Amber: {counts['amber']} deals"></div>
          <div style="background: var(--red); width: {red_pct:.1f}%;"
               title="Red: {counts['red']} deals"></div>
        </div>
        <div style="display: flex; gap: 1rem; font-size: 0.9rem;
                    font-variant-numeric: tabular-nums;">
          <span style="color: var(--green-text); font-weight: 700;">
            ● {counts['green']} green
          </span>
          <span style="color: var(--amber-text); font-weight: 700;">
            ● {counts['amber']} amber
          </span>
          <span style="color: var(--red-text); font-weight: 700;">
            ● {counts['red']} red
          </span>
        </div>
      </div>
    </div>
    """


def _render_headline(rollup: Dict[str, Any]) -> str:
    """Top-of-page KPI cards: deal count, weighted MOIC, weighted IRR, risk count.

    Card values get stable IDs so B93 JS can recompute them live as the
    analyst filters the table below.
    """
    at_risk = int(rollup.get("covenant_trips") or 0) + int(rollup.get("covenant_tight") or 0)
    moic = rollup.get("weighted_moic")
    irr = rollup.get("weighted_irr")

    def _card(label: str, value: str, value_id: str,
              color: str = _PALETTE["text"]) -> str:
        return (
            f'<div class="kpi-card">'
            f'<div class="kpi-value" id="{value_id}" '
            f'style="color: {color};">{html.escape(value)}</div>'
            f'<div class="kpi-label">{html.escape(label)}</div>'
            f'</div>'
        )

    return (
        '<div class="kpi-grid">'
        + _card("Deals", str(rollup.get("deal_count", 0)),
                "kpi-deal-count")
        + _card("Weighted MOIC", _fmt_moic(moic),
                "kpi-weighted-moic", _color_for_moic(moic))
        + _card("Weighted IRR", _fmt_pct(irr),
                "kpi-weighted-irr", _color_for_irr(irr))
        + _card("At risk (trip+tight)", str(at_risk),
                "kpi-at-risk",
                _PALETTE["red"] if at_risk else _PALETTE["green"])
        + '</div>'
    )


def _render_funnel(rollup: Dict[str, Any]) -> str:
    """Horizontal stage funnel — bar widths proportional to count."""
    funnel = rollup.get("stage_funnel") or {}
    max_count = max(funnel.values()) if funnel else 0
    if max_count == 0:
        return '<p style="color: var(--muted);">(no deals)</p>'

    bars = []
    for stage in DEAL_STAGES:
        count = int(funnel.get(stage, 0))
        width_pct = 0 if max_count == 0 else (count / max_count) * 100
        label = stage.replace("_", " ").title()
        bars.append(
            f'<div class="funnel-row">'
            f'<div class="funnel-label">{html.escape(label)}</div>'
            f'<div class="funnel-bar-wrap">'
            f'<div class="funnel-bar" style="width: {width_pct:.1f}%;"></div>'
            f'</div>'
            f'<div class="funnel-count">{count}</div>'
            f'</div>'
        )
    return '<div class="funnel">' + "".join(bars) + '</div>'


_BULK_BAR_HTML = """
<div id="rcm-bulk-bar" style="display: none; position: sticky; top: 0;
     z-index: 100; background: var(--accent); color: white;
     padding: 0.6rem 1rem; border-radius: 8px; margin-bottom: 1rem;
     box-shadow: var(--shadow-md); align-items: center; gap: 0.75rem;
     flex-wrap: wrap;">
  <span id="rcm-bulk-count" style="font-weight: 600;"></span>
  <form id="rcm-bulk-tag-form" method="POST" action="/api/bulk/tags/add"
        style="display: inline-flex; gap: 0.4rem; margin: 0;">
    <input type="text" name="tag" required placeholder="tag to apply"
           list="rcm-tag-datalist"
           pattern="[a-z0-9][a-z0-9_:.\\-]{0,39}"
           style="padding: 0.3rem 0.6rem; border-radius: 6px;
                  border: none; font-size: 0.85rem;">
    <input type="hidden" name="deal_ids" id="rcm-bulk-deal-ids">
    <button type="submit"
            style="padding: 0.3rem 0.9rem; border: none; border-radius: 6px;
                   background: white; color: var(--accent); font-weight: 600;
                   cursor: pointer; font-size: 0.85rem;">
      + Apply tag
    </button>
  </form>
  <form id="rcm-bulk-stage-form" method="POST" action="/api/bulk/stage"
        style="display: inline-flex; gap: 0.4rem; margin: 0;">
    <select name="stage" required
            style="padding: 0.3rem 0.6rem; border-radius: 6px;
                   border: none; font-size: 0.85rem;">
      <option value="" disabled selected>— advance to —</option>
      <option value="sourced">Sourced</option>
      <option value="ioi">IOI</option>
      <option value="loi">LOI</option>
      <option value="spa">SPA</option>
      <option value="closed">Closed</option>
      <option value="hold">Hold</option>
      <option value="exit">Exit</option>
    </select>
    <input type="hidden" name="deal_ids" id="rcm-bulk-deal-ids-stage">
    <button type="submit"
            onclick="return confirm('Advance selected deals to the chosen stage?');"
            style="padding: 0.3rem 0.9rem; border: none; border-radius: 6px;
                   background: white; color: var(--accent); font-weight: 600;
                   cursor: pointer; font-size: 0.85rem;">
      Advance stage
    </button>
  </form>
  <button id="rcm-bulk-clear" type="button"
          style="padding: 0.3rem 0.9rem; border: 1px solid white;
                 border-radius: 6px; background: transparent; color: white;
                 cursor: pointer; font-size: 0.85rem; margin-left: auto;">
    Clear selection
  </button>
</div>
<datalist id="rcm-tag-datalist"></datalist>
"""

_BULK_JS = """
(function() {
  var bar = document.getElementById('rcm-bulk-bar');
  var count = document.getElementById('rcm-bulk-count');
  var all = document.getElementById('rcm-bulk-all');
  var hiddenInput = document.getElementById('rcm-bulk-deal-ids');
  var hiddenInputStage = document.getElementById('rcm-bulk-deal-ids-stage');
  var form = document.getElementById('rcm-bulk-tag-form');
  var stageForm = document.getElementById('rcm-bulk-stage-form');
  var clear = document.getElementById('rcm-bulk-clear');
  if (!bar || !all || !hiddenInput || !form || !clear) return;

  function selected() {
    return Array.from(document.querySelectorAll('.rcm-bulk-select:checked'))
      .filter(function(c){ return c.closest('tr').style.display !== 'none'; })
      .map(function(c){ return c.value; });
  }
  function refresh() {
    var ids = selected();
    if (ids.length === 0) {
      bar.style.display = 'none';
    } else {
      bar.style.display = 'flex';
      count.textContent = ids.length + ' deal' +
        (ids.length === 1 ? '' : 's') + ' selected';
      hiddenInput.value = ids.join(',');
      if (hiddenInputStage) hiddenInputStage.value = ids.join(',');
    }
  }
  document.addEventListener('change', function(ev) {
    if (ev.target.classList.contains('rcm-bulk-select')) refresh();
  });
  all.addEventListener('change', function() {
    var on = all.checked;
    document.querySelectorAll('.rcm-bulk-select').forEach(function(c) {
      if (c.closest('tr').style.display !== 'none') c.checked = on;
    });
    refresh();
  });
  clear.addEventListener('click', function() {
    document.querySelectorAll('.rcm-bulk-select').forEach(function(c) {
      c.checked = false;
    });
    all.checked = false;
    refresh();
  });
  form.addEventListener('submit', function() { refresh(); });
  if (stageForm) stageForm.addEventListener('submit', function() { refresh(); });
})();

// Tag autocomplete: hydrate the <datalist> from /api/tags so every tag
// input on the page gets native browser typeahead.
(function() {
  var dl = document.getElementById('rcm-tag-datalist');
  if (!dl) return;
  fetch('/api/tags').then(function(r) {
    if (!r.ok) return null;
    return r.json();
  }).then(function(data) {
    if (!Array.isArray(data)) return;
    dl.innerHTML = data.map(function(row) {
      var t = String(row.tag || '').replace(/[<>&"]/g, function(c) {
        return {'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c];
      });
      return '<option value="' + t + '">' + row.count + ' deal(s)</option>';
    }).join('');
    // Also wire the filter bar tag input (no form association)
    var filt = document.getElementById('rcm-filter-tag');
    if (filt) filt.setAttribute('list', 'rcm-tag-datalist');
  }).catch(function() { /* ignore */ });
})();
"""

_FILTER_BAR_HTML = """
<div class="card" style="padding: 1rem 1.25rem; display: flex;
     gap: 0.75rem; flex-wrap: wrap; align-items: center;">
  <input type="text" id="rcm-filter-text" placeholder="Search deal ID..."
         style="flex: 1; min-width: 200px; padding: 0.5rem 0.75rem;
                border: 1px solid var(--border); border-radius: 6px;
                font-size: 0.9rem; font-family: inherit;">
  <select id="rcm-filter-stage" style="padding: 0.5rem 0.75rem;
          border: 1px solid var(--border); border-radius: 6px;
          font-size: 0.9rem; background: var(--card); font-family: inherit;">
    <option value="">All stages</option>
    <option value="sourced">Sourced</option>
    <option value="ioi">IOI</option>
    <option value="loi">LOI</option>
    <option value="spa">SPA</option>
    <option value="closed">Closed</option>
    <option value="hold">Hold</option>
    <option value="exit">Exit</option>
  </select>
  <select id="rcm-filter-covenant" style="padding: 0.5rem 0.75rem;
          border: 1px solid var(--border); border-radius: 6px;
          font-size: 0.9rem; background: var(--card); font-family: inherit;">
    <option value="">Any covenant</option>
    <option value="SAFE">SAFE</option>
    <option value="TIGHT">TIGHT</option>
    <option value="TRIPPED">TRIPPED</option>
  </select>
  <input type="text" id="rcm-filter-tag" placeholder="Tag (e.g. watch)"
         style="width: 180px; padding: 0.5rem 0.75rem;
                border: 1px solid var(--border); border-radius: 6px;
                font-size: 0.9rem; font-family: inherit;">
  <label style="display: flex; align-items: center; gap: 0.4rem;
         font-size: 0.88rem; color: var(--muted); cursor: pointer;">
    <input type="checkbox" id="rcm-filter-concerning" style="cursor: pointer;">
    Concerning only
  </label>
  <a id="rcm-export-link" href="#" download="portfolio_view.csv"
     style="padding: 0.5rem 0.75rem; text-decoration: none;
            border: 1px solid var(--accent); border-radius: 6px;
            color: var(--accent); font-size: 0.85rem; font-weight: 600;">
    ↓ Export CSV
  </a>
  <span id="rcm-filter-count" style="color: var(--muted);
        font-size: 0.82rem; font-variant-numeric: tabular-nums;
        margin-left: auto; white-space: nowrap;"></span>
</div>
"""

_FILTER_JS = """
(function() {
  var $ = function(id) { return document.getElementById(id); };
  var text = $('rcm-filter-text');
  var stage = $('rcm-filter-stage');
  var cov = $('rcm-filter-covenant');
  var tag = $('rcm-filter-tag');
  var concerning = $('rcm-filter-concerning');
  var counter = $('rcm-filter-count');
  var exportLink = $('rcm-export-link');
  if (!text || !stage || !cov || !concerning) return;

  // B96: persist filter state across page reloads in localStorage.
  var STORAGE_KEY = 'rcm-mc-filter-v1';
  var restored = null;
  try {
    restored = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
  } catch (e) { restored = null; }
  if (restored) {
    if (typeof restored.text === 'string') text.value = restored.text;
    if (typeof restored.stage === 'string') stage.value = restored.stage;
    if (typeof restored.cov === 'string') cov.value = restored.cov;
    if (tag && typeof restored.tag === 'string') tag.value = restored.tag;
    if (typeof restored.concerning === 'boolean') concerning.checked = restored.concerning;
  }
  function persist() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        text: text.value, stage: stage.value, cov: cov.value,
        tag: tag ? tag.value : '', concerning: concerning.checked,
      }));
    } catch (e) { /* localStorage full or unavailable — ignore */ }
  }

  // B96: "/" focuses the search box from anywhere (like GitHub / Gmail).
  // Esc clears the filter + blurs. Must be registered once at module load.
  document.addEventListener('keydown', function(ev) {
    if (ev.key === '/' && document.activeElement.tagName !== 'INPUT' &&
        document.activeElement.tagName !== 'TEXTAREA') {
      ev.preventDefault();
      text.focus();
      text.select();
    } else if (ev.key === 'Escape' && document.activeElement === text) {
      text.value = ''; applyFilter(); text.blur();
    }
  });

  function applyFilter() {
    var q = text.value.trim().toLowerCase();
    var wantStage = stage.value;
    var wantCov = cov.value;
    var wantTag = (tag && tag.value || '').trim().toLowerCase();
    var onlyConcerning = concerning.checked;
    var rows = document.querySelectorAll('tr.deal-row');
    var visible = 0;
    rows.forEach(function(r) {
      var did = r.getAttribute('data-deal-id') || '';
      var s = r.getAttribute('data-stage') || '';
      var c = r.getAttribute('data-covenant') || '';
      var tg = r.getAttribute('data-tags') || '';
      var nc = parseInt(r.getAttribute('data-concerning') || '0', 10);
      var match = true;
      if (q && did.indexOf(q) === -1) match = false;
      if (wantStage && s !== wantStage) match = false;
      if (wantCov && c !== wantCov) match = false;
      if (wantTag) {
        // Tag substring match: deal's tag string contains the queried token
        var tags = tg.split(' ');
        var hit = false;
        for (var i = 0; i < tags.length; i++) {
          if (tags[i].indexOf(wantTag) >= 0) { hit = true; break; }
        }
        if (!hit) match = false;
      }
      if (onlyConcerning && nc < 1) match = false;
      r.style.display = match ? '' : 'none';
      if (match) visible++;
    });
    counter.textContent = visible + ' / ' + rows.length + ' shown';

    // B88: update the export link to carry the current filter as query params
    if (exportLink) {
      var qs = new URLSearchParams();
      if (q) qs.set('q', q);
      if (wantStage) qs.set('stage', wantStage);
      if (wantCov) qs.set('covenant', wantCov);
      if (wantTag) qs.set('tag', wantTag);
      if (onlyConcerning) qs.set('concerning', '1');
      qs.set('format', 'csv');
      exportLink.href = '/api/export?' + qs.toString();
    }

    // B93: recompute headline KPIs from visible rows so the cards match
    // what the analyst's filter selected.
    var visRows = Array.from(document.querySelectorAll('tr.deal-row'))
      .filter(function(r){ return r.style.display !== 'none'; });
    var totalEv = 0, wMoicNum = 0, wIrrNum = 0;
    var atRisk = 0;
    visRows.forEach(function(r){
      var ev = parseFloat(r.getAttribute('data-entry-ev') || '');
      var moic = parseFloat(r.getAttribute('data-moic') || '');
      var irr = parseFloat(r.getAttribute('data-irr') || '');
      var cov = r.getAttribute('data-covenant') || '';
      if (!isNaN(ev)) {
        totalEv += ev;
        if (!isNaN(moic)) wMoicNum += moic * ev;
        if (!isNaN(irr))  wIrrNum  += irr  * ev;
      }
      if (cov === 'TRIPPED' || cov === 'TIGHT') atRisk++;
    });
    var setText = function(id, txt, color) {
      var el = document.getElementById(id);
      if (!el) return;
      el.textContent = txt;
      if (color) el.style.color = color;
    };
    setText('kpi-deal-count', String(visible));
    var fmtX = function(v){ return isFinite(v) ? (v.toFixed(2) + 'x') : '—'; };
    var fmtP = function(v){ return isFinite(v) ? ((v*100).toFixed(1) + '%') : '—'; };
    var colorMoic = function(v){
      if (!isFinite(v)) return '#6B7280';
      if (v >= 2.5) return '#10B981';
      if (v >= 2.0) return '#F59E0B';
      return '#EF4444';
    };
    var colorIrr = function(v){
      if (!isFinite(v)) return '#6B7280';
      if (v >= 0.25) return '#10B981';
      if (v >= 0.18) return '#F59E0B';
      return '#EF4444';
    };
    var wMoic = totalEv > 0 ? wMoicNum / totalEv : NaN;
    var wIrr  = totalEv > 0 ? wIrrNum  / totalEv : NaN;
    setText('kpi-weighted-moic', fmtX(wMoic), colorMoic(wMoic));
    setText('kpi-weighted-irr', fmtP(wIrr), colorIrr(wIrr));
    setText('kpi-at-risk', String(atRisk),
            atRisk ? '#EF4444' : '#10B981');

    // B96: save filter state (debounced trivially via last-wins)
    persist();
  }
  text.addEventListener('input', applyFilter);
  stage.addEventListener('change', applyFilter);
  cov.addEventListener('change', applyFilter);
  if (tag) tag.addEventListener('input', applyFilter);
  concerning.addEventListener('change', applyFilter);
  applyFilter();
})();
"""


def _attach_mini_sparkline_column(
    store: PortfolioStore, df: pd.DataFrame,
) -> pd.DataFrame:
    """Add a ``sparkline`` column: compact inline SVG per deal.

    Generates a 120×30 SVG polyline of the last 8 quarters of EBITDA
    actuals. Deals with <2 quarters get an empty string; the dashboard
    renders a dash placeholder in that cell.
    """
    if df is None or df.empty:
        return df
    from ..pe.hold_tracking import cumulative_drift
    sparks = []
    for did in df["deal_id"]:
        try:
            drift = cumulative_drift(store, str(did), kpi="ebitda")
        except (ValueError, TypeError):
            drift = None
        svg = _render_mini_sparkline(drift)
        sparks.append(svg)
    out = df.copy()
    out["sparkline"] = sparks
    return out


def _render_mini_sparkline(
    drift_df,
    width: int = 120,
    height: int = 30,
) -> str:
    """Tiny inline SVG: EBITDA actual trajectory over up to 8 quarters.

    Polyline colored by cumulative drift direction: green if ending
    above plan, red if below, muted gray if flat or missing plan.
    Returns "" when there's not enough data to chart.
    """
    import pandas as pd
    if drift_df is None:
        return ""
    # Handle both DataFrames and None / empty results
    if not hasattr(drift_df, "empty") or drift_df.empty:
        return ""
    if len(drift_df) < 2:
        return ""

    # Last 8 quarters only so the widget stays compact
    window = drift_df.tail(8)
    actuals = [float(v) for v in window["actual"].tolist()
               if v is not None]
    if len(actuals) < 2:
        return ""
    vmin, vmax = min(actuals), max(actuals)
    if vmax == vmin:
        vmax = vmin + 1  # flat → tiny offset to avoid div-by-zero

    pad_y = 3
    chart_h = height - 2 * pad_y
    step = width / max(len(actuals) - 1, 1)

    pts = " ".join(
        f"{i*step:.1f},{height - pad_y - ((v - vmin) / (vmax - vmin)) * chart_h:.1f}"
        for i, v in enumerate(actuals)
    )

    # Color by cumulative-drift direction
    last_drift = window.iloc[-1].get("cumulative_drift")
    try:
        ld = float(last_drift)
    except (TypeError, ValueError):
        ld = None
    if ld is None or ld != ld:
        stroke = "#6B7280"  # muted
    elif ld > 0.02:
        stroke = "#10B981"  # green
    elif ld < -0.02:
        stroke = "#EF4444"  # red
    else:
        stroke = "#6B7280"

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'xmlns="http://www.w3.org/2000/svg" '
        f'style="display: block; width: {width}px; height: {height}px;">'
        f'<polyline points="{pts}" fill="none" '
        f'stroke="{stroke}" stroke-width="1.75" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'</svg>'
    )


def _attach_tags_column(store: PortfolioStore, df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` with an added ``tags`` column (space-separated string).

    Used by the dashboard so each deal row carries a ``data-tags`` attribute
    the client-side filter JS can match against. Empty when a deal has no
    tags — avoids phantom matches for the empty string.
    """
    if df is None or df.empty:
        return df
    from ..deals.deal_tags import tags_for
    out = df.copy()
    out["tags"] = [
        " ".join(tags_for(store, str(did))) for did in out["deal_id"]
    ]
    return out


def _render_deal_table(df: pd.DataFrame) -> str:
    """Full latest-per-deal table with severity coloring on MOIC / IRR / Covenant."""
    if df is None or df.empty:
        return '<p style="color: var(--muted);">(no deals yet)</p>'

    rows = []
    for _, r in df.iterrows():
        moic = r.get("moic")
        irr = r.get("irr")
        cov = r.get("covenant_status")
        nc = r.get("concerning_signals")
        nc = int(nc) if pd.notna(nc) else 0
        nf = r.get("favorable_signals")
        nf = int(nf) if pd.notna(nf) else 0

        signals_cell = ""
        if nc:
            signals_cell += f'<span class="badge badge-red">{nc}c</span> '
        if nf:
            signals_cell += f'<span class="badge badge-green">{nf}f</span>'
        if not signals_cell:
            signals_cell = '<span style="color: var(--muted);">—</span>'

        # Pandas NaN surfaces as float; coerce to None for clean rendering
        if cov is None or (isinstance(cov, float) and cov != cov):
            cov_cell = '<span style="color: var(--muted);">—</span>'
        else:
            cov_cell = f'<span class="badge" style="background:{_color_for_covenant(cov)}1A; color:{_color_for_covenant(cov)};">{html.escape(str(cov))}</span>'

        created = str(r.get("created_at") or "")[:10]
        # UI-B64: data attributes drive the client-side filter (JS reads these)
        deal_id_str = str(r["deal_id"])
        stage_str = str(r["stage"])
        cov_str = "" if (cov is None or (isinstance(cov, float) and cov != cov)) else str(cov)
        tags_str = str(r.get("tags") or "")
        tag_pills = ""
        if tags_str.strip():
            tag_pills = " ".join(
                f'<span class="badge badge-blue" '
                f'style="font-size: 0.7rem;">{html.escape(t)}</span>'
                for t in tags_str.split()
            )
        spark = r.get("sparkline") or ""
        spark_cell = spark if spark else '<span style="color: var(--muted);">—</span>'
        checkbox_cell = (
            f'<input type="checkbox" class="rcm-bulk-select" '
            f'value="{html.escape(deal_id_str)}" '
            f'style="cursor: pointer;">'
        )
        # B93: numeric data attrs so the JS can recompute KPIs on filter
        def _numf(v):
            if v is None:
                return ""
            if isinstance(v, float) and v != v:
                return ""
            return str(float(v))
        rows.append(
            f'<tr class="deal-row"'
            f' data-deal-id="{html.escape(deal_id_str.lower())}"'
            f' data-stage="{html.escape(stage_str.lower())}"'
            f' data-covenant="{html.escape(cov_str)}"'
            f' data-concerning="{nc}"'
            f' data-tags="{html.escape(tags_str.lower())}"'
            f' data-moic="{_numf(moic)}"'
            f' data-irr="{_numf(irr)}"'
            f' data-entry-ev="{_numf(r.get("entry_ev"))}">'
            f'<td style="text-align: center;">{checkbox_cell}</td>'
            f'<td><strong>{html.escape(deal_id_str)}</strong>'
            + (f'<div style="margin-top: 0.25rem;">{tag_pills}</div>' if tag_pills else "")
            + '</td>'
            f'<td>{html.escape(stage_str.title())}</td>'
            f'<td class="num">{_fmt_money(r.get("entry_ev"))}</td>'
            f'<td class="num" style="color: {_color_for_moic(moic)};">{_fmt_moic(moic)}</td>'
            f'<td class="num" style="color: {_color_for_irr(irr)};">{_fmt_pct(irr)}</td>'
            f'<td>{cov_cell}</td>'
            f'<td>{signals_cell}</td>'
            f'<td>{spark_cell}</td>'
            f'<td style="color: var(--muted); font-size: 0.85rem;">{html.escape(created)}</td>'
            f'</tr>'
        )
    return (
        '<table class="deal-table">'
        '<thead><tr>'
        '<th style="width: 30px; text-align: center;">'
        '<input type="checkbox" id="rcm-bulk-all" style="cursor: pointer;" '
        'title="Select all visible">'
        '</th>'
        '<th>Deal ID</th><th>Stage</th><th>Entry EV</th><th>MOIC</th>'
        '<th>IRR</th><th>Covenant</th><th>Signals</th>'
        '<th>Recent</th><th>Snapshot</th>'
        '</tr></thead>'
        '<tbody>' + "".join(rows) + '</tbody>'
        '</table>'
    )


def _color_for_severity(severity: Optional[str]) -> str:
    """Reuse the quarterly-variance severity palette."""
    return {
        "on_track":  _PALETTE["green"],
        "lagging":   _PALETTE["amber"],
        "off_track": _PALETTE["red"],
        "no_plan":   _PALETTE["muted"],
    }.get(str(severity or ""), _PALETTE["muted"])


def _render_lagging_initiatives(store: PortfolioStore, df: pd.DataFrame) -> str:
    """Portfolio-wide snapshot of lagging initiatives across held deals.

    For each held deal, pull the top 1-2 lagging initiatives (severity =
    ``lagging`` or ``off_track``). Rendered as one compact table so a
    partner can eyeball the portfolio and ask "which workstreams are
    universally behind, vs deal-specific?" — the multi-deal pattern
    recognition a single-deal memo can't give them.

    Silent no-op when no held deals have initiative actuals recorded.
    """
    from ..rcm.initiative_tracking import initiative_variance_report

    if df is None or df.empty:
        return ""
    held = df[df["stage"].isin(["hold", "exit"])]
    if held.empty:
        return ""

    rows_html: List[str] = []
    for _, r in held.iterrows():
        deal_id = str(r["deal_id"])
        init_df = initiative_variance_report(store, deal_id)
        if init_df.empty:
            continue
        lagging = init_df[init_df["severity"].isin(["lagging", "off_track"])]
        if lagging.empty:
            continue
        # Top 2 worst for this deal
        for _, init in lagging.head(2).iterrows():
            sev = str(init.get("severity") or "no_plan")
            color = _color_for_severity(sev)
            vp = init.get("variance_pct")
            var_str = ("—" if vp is None or (isinstance(vp, float) and vp != vp)
                       else f"{vp*100:+.1f}%")
            actual = init.get("cumulative_actual")
            actual_str = "—" if actual is None else f"${actual/1e6:.2f}M"
            rows_html.append(
                f'<tr>'
                f'<td><strong>{html.escape(deal_id)}</strong></td>'
                f'<td>{html.escape(str(init["initiative_id"]))}</td>'
                f'<td class="num">{actual_str}</td>'
                f'<td style="color: {color}; font-weight: 600;">{var_str}</td>'
                f'<td>{int(init["quarters_active"])}q</td>'
                f'</tr>'
            )
    if not rows_html:
        return ""
    return (
        '<div class="card">'
        '<h2>Lagging initiatives across held deals</h2>'
        '<p style="color: var(--muted); font-size: 0.85rem; margin: 0.25rem 0 1rem 0;">'
        'Top 2 worst-performing initiatives per held deal. Repeated initiatives '
        'across deals usually signal a playbook gap, not a deal-specific issue.'
        '</p>'
        '<table class="deal-table">'
        '<thead><tr>'
        '<th>Deal</th><th>Initiative</th><th>Cum. actual</th>'
        '<th>Variance</th><th>Quarters</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows_html)}</tbody>'
        '</table>'
        '</div>'
    )


def _render_held_deal_variance(store: PortfolioStore, df: pd.DataFrame) -> str:
    """Per-held-deal quarterly variance strip — the hold-period track record.

    For every deal with stage in {hold, exit} AND any quarterly actuals,
    render last 4 quarters of EBITDA variance as colored severity cells
    plus cumulative drift. Empty string if no held deals have actuals.
    """
    from ..pe.hold_tracking import cumulative_drift

    if df is None or df.empty:
        return ""

    held = df[df["stage"].isin(["hold", "exit"])]
    if held.empty:
        return ""

    rows_html: List[str] = []
    for _, r in held.iterrows():
        deal_id = str(r["deal_id"])
        drift = cumulative_drift(store, deal_id, kpi="ebitda")
        if drift.empty:
            continue  # Held but no actuals recorded yet

        # Last 4 quarters (newest last)
        last4 = drift.tail(4)
        cells = []
        for _, q in last4.iterrows():
            sev = q["severity"]
            var_pct = q["variance_pct"]
            label = "—" if (var_pct is None or (isinstance(var_pct, float) and var_pct != var_pct)) else f"{var_pct*100:+.1f}%"
            color = _color_for_severity(sev)
            cells.append(
                f'<td style="text-align: center; background: {color}15; '
                f'color: {color}; font-weight: 600; padding: 4px 8px;">'
                f'<div style="font-size: 0.7rem; color: var(--muted);">{html.escape(str(q["quarter"]))}</div>'
                f'{label}</td>'
            )
        # Pad with empty cells if fewer than 4 quarters
        while len(cells) < 4:
            cells.insert(0, '<td style="text-align: center; color: var(--muted);">—</td>')

        cum = last4.iloc[-1]["cumulative_drift"]
        cum_str = "—" if (cum is None or (isinstance(cum, float) and cum != cum)) else f"{cum*100:+.1f}%"
        cum_color = _color_for_severity(
            "off_track" if (cum is not None and abs(cum) >= 0.15)
            else ("lagging" if (cum is not None and abs(cum) >= 0.05) else "on_track")
        )

        rows_html.append(
            f'<tr>'
            f'<td><strong>{html.escape(deal_id)}</strong></td>'
            + "".join(cells)
            + f'<td class="num" style="color: {cum_color}; font-weight: 600;">{cum_str}</td>'
            + '</tr>'
        )

    if not rows_html:
        return ""

    return (
        '<div class="card">'
        '<h2>Hold-period variance — EBITDA actual vs plan</h2>'
        '<p style="color: var(--muted); font-size: 0.85rem; margin: 0.25rem 0 1rem 0;">'
        'Last 4 quarters per held deal. Green = on track (|Δ|&lt;5%), amber = lagging '
        '(|Δ|&lt;15%), red = off track.'
        '</p>'
        '<table class="deal-table">'
        '<thead><tr>'
        '<th>Deal ID</th><th>Q-3</th><th>Q-2</th><th>Q-1</th><th>Latest</th>'
        '<th>Cumulative drift</th>'
        '</tr></thead>'
        '<tbody>' + "".join(rows_html) + '</tbody>'
        '</table>'
        '</div>'
    )


def _render_at_risk(df: pd.DataFrame) -> str:
    """List deals currently TRIPPED or TIGHT — the partner's Monday-morning read."""
    if df is None or df.empty:
        return ""
    at_risk = df[df["covenant_status"].isin(["TRIPPED", "TIGHT"])]
    if at_risk.empty:
        return (
            '<div class="card at-risk-card">'
            '<h3>At-risk deals</h3>'
            '<p style="color: var(--green);">None — all covenants SAFE.</p>'
            '</div>'
        )

    bullets = []
    for _, r in at_risk.iterrows():
        cov = r.get("covenant_status")
        lev = r.get("covenant_leverage")
        bullets.append(
            f'<li><strong>{html.escape(str(r["deal_id"]))}</strong> '
            f'({html.escape(str(r["stage"]).title())}) — '
            f'<span style="color: {_color_for_covenant(cov)};">{html.escape(str(cov))}</span> '
            f'at {float(lev):.2f}x leverage</li>'
        )
    return (
        '<div class="card at-risk-card">'
        '<h3>At-risk deals</h3>'
        '<ul>' + "".join(bullets) + '</ul>'
        '</div>'
    )


# ── Top-level builder ──────────────────────────────────────────────────────

_CSS = """
:root {
  --bg: #FAFAFA; --card: #FFFFFF; --border: #E5E7EB;
  --text: #111827; --muted: #6B7280; --accent: #1F4E78;
  --green: #10B981; --amber: #F59E0B; --red: #EF4444;
}
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
       margin: 0; padding: 2rem; background: var(--bg); color: var(--text); }
.container { max-width: 1100px; margin: 0 auto; }
h1 { margin: 0 0 0.25rem 0; color: var(--accent); }
.subtitle { color: var(--muted); margin-bottom: 2rem; }
.card { background: var(--card); border: 1px solid var(--border);
        border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; }
.card h2, .card h3 { margin-top: 0; color: var(--accent); }
.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;
            margin-bottom: 1.5rem; }
.kpi-card { background: var(--card); border: 1px solid var(--border);
            border-radius: 8px; padding: 1rem 1.25rem; }
.kpi-value { font-size: 2rem; font-weight: 700; line-height: 1.1; }
.kpi-label { font-size: 0.85rem; color: var(--muted); margin-top: 0.25rem; }
.funnel { display: flex; flex-direction: column; gap: 0.5rem; }
.funnel-row { display: grid; grid-template-columns: 100px 1fr 40px; gap: 0.75rem; align-items: center; }
.funnel-label { color: var(--muted); font-size: 0.9rem; }
.funnel-bar-wrap { background: var(--border); height: 12px; border-radius: 6px; overflow: hidden; }
.funnel-bar { background: var(--accent); height: 100%; border-radius: 6px; }
.funnel-count { text-align: right; font-weight: 600; color: var(--text); }
.deal-table { width: 100%; border-collapse: collapse; }
.deal-table th { text-align: left; padding: 0.5rem; border-bottom: 2px solid var(--border);
                 color: var(--muted); font-weight: 600; font-size: 0.85rem;
                 text-transform: uppercase; letter-spacing: 0.03em; }
.deal-table td { padding: 0.5rem; border-bottom: 1px solid var(--border); }
.deal-table td.num { text-align: right; font-variant-numeric: tabular-nums; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
         font-size: 0.75rem; font-weight: 600; }
.badge-green { background: #D1FAE5; color: #065F46; }
.badge-red   { background: #FEE2E2; color: #991B1B; }
.badge-amber { background: #FEF3C7; color: #92400E; }
.at-risk-card ul { margin: 0.5rem 0 0 0; padding-left: 1.2rem; }
.at-risk-card li { margin-bottom: 0.25rem; }
footer { color: var(--muted); font-size: 0.8rem; margin-top: 2rem; text-align: center; }
"""


def build_portfolio_dashboard(
    store: PortfolioStore,
    out_path: str,
    title: str = "RCM Portfolio Dashboard",
) -> str:
    """Write a self-contained HTML dashboard to ``out_path``. Returns the path."""
    rollup = portfolio_rollup(store)
    df = latest_per_deal(store)
    df = _attach_tags_column(store, df)
    df = _attach_mini_sparkline_column(store, df)

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    deal_count = rollup.get("deal_count", 0)
    try:
        all_deals = store.list_deals(include_archived=True)
        archived_count = sum(
            1 for _, r in all_deals.iterrows()
            if r.get("archived_at")
        ) if len(all_deals) > 0 else 0
    except Exception:
        archived_count = 0
    archived_badge = (
        f' · <span style="color:#f59e0b;">{archived_count} archived</span>'
        if archived_count > 0 else ""
    )

    body = f"""
    <div class="container">
      <h1>{html.escape(title)}</h1>
      <div class="subtitle" style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 0.5rem;">
        <span>{deal_count} deal{'s' if deal_count != 1 else ''}{archived_badge} · Generated {generated}</span>
        <span style="font-size: 0.85rem;">
          <a href="/search" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Search →</a>
          <a href="/notes" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Notes →</a>
          <a href="/watchlist" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">★ Watchlist →</a>
          <a href="/owners" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Owners →</a>
          <a href="/deadlines" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Deadlines →</a>
          <a href="/compare" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Compare →</a>
          <a href="/activity" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Activity →</a>
          <a href="/initiatives" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Initiatives →</a>
          <a href="/ops" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Ops →</a>
          <a href="/jobs" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Jobs →</a>
          <a href="/alerts" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">
            Alerts <span id="rcm-alert-badge"
                         style="display: none; background: var(--red);
                                color: white; padding: 1px 7px;
                                border-radius: 10px; font-size: 0.75rem;
                                font-weight: 700; margin-left: 0.25rem;
                                vertical-align: middle;"></span>
          </a>
          <a href="/escalations" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Escalations →</a>
          <a href="/cohorts" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Cohorts →</a>
          <a href="/lp-update" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">LP update →</a>
          <a href="/variance" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Variance →</a>
          <a href="/upload" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent); margin-right: 1rem;">Upload CSV →</a>
          <a href="/?live=1" style="color: var(--accent); text-decoration: none;
             border-bottom: 1px dotted var(--accent);">Live mode →</a>
          <span id="rcm-whoami" style="margin-left: 1rem; font-size: 0.82rem;
             color: var(--muted);"></span>
        </span>
      </div>

      {_render_portfolio_pulse(store)}

      {_render_headline(rollup)}

      {_render_health_distribution(store, df)}

      <div class="card" id="rcm-recent-deals-card" style="display: none;">
        <h2>Recently viewed</h2>
        <div id="rcm-recent-deals-list"
             style="display: flex; flex-wrap: wrap; gap: 0.4rem;"></div>
      </div>

      <div class="card">
        <h2>Pipeline funnel</h2>
        {_render_funnel(rollup)}
      </div>

      {_render_at_risk(df)}

      {_render_held_deal_variance(store, df)}

      {_render_lagging_initiatives(store, df)}

      <div class="card">
        <h2>Latest-per-deal snapshot</h2>
        {_BULK_BAR_HTML}
        {_FILTER_BAR_HTML}
        {_render_deal_table(df)}
      </div>

      <footer>
        Generated by rcm-mc portfolio · All data sourced from shipped HCRIS,
        simulation outputs, and registered deal snapshots.
      </footer>
    </div>
    """

    html_doc = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{_CSS}</style>
</head><body>
{body}
<script>{_FILTER_JS}</script>
<script>{_BULK_JS}</script>
<script>
// B101: hydrate the alerts badge from /api/alerts/active.
// Severity = red OR amber count → red pill in nav.
(function() {{
  fetch('/api/alerts/active').then(function(r) {{
    return r.ok ? r.json() : null;
  }}).then(function(data) {{
    if (!Array.isArray(data)) return;
    var n = data.filter(function(a) {{
      return a.severity === 'red' || a.severity === 'amber';
    }}).length;
    if (n > 0) {{
      var badge = document.getElementById('rcm-alert-badge');
      if (badge) {{
        badge.style.display = 'inline-block';
        badge.textContent = String(n);
      }}
    }}
  }}).catch(function() {{ /* ignore */ }});
}})();
</script>

<script>
// B126: hydrate sign-in state in the nav bar.
(function() {{
  fetch('/api/me').then(function(r) {{
    return r.ok ? r.json() : null;
  }}).then(function(me) {{
    var el = document.getElementById('rcm-whoami');
    if (!el) return;
    if (me && me.username) {{
      el.innerHTML =
        '· Signed in as <strong>' + me.username + '</strong> ('
        + me.role + ') '
        + '<form method="POST" action="/api/logout" '
        +   'style="display:inline;margin-left:0.3rem;">'
        + '<button type="submit" '
        +   'style="font-size:0.75rem;background:none;border:none;'
        +   'color:var(--accent);cursor:pointer;'
        +   'border-bottom:1px dotted var(--accent);padding:0;">'
        + 'Sign out</button></form>';
    }} else {{
      el.innerHTML = '· <a href="/login" style="color:var(--accent);">'
        + 'Sign in</a>';
    }}
  }}).catch(function() {{ /* ignore */ }});
}})();
</script>

<script>
// B98: hydrate the "Recently viewed" card from localStorage.
(function() {{
  try {{
    var KEY = 'rcm-mc-recent-deals-v1';
    var arr = JSON.parse(localStorage.getItem(KEY) || '[]');
    if (!Array.isArray(arr) || arr.length === 0) return;
    var card = document.getElementById('rcm-recent-deals-card');
    var list = document.getElementById('rcm-recent-deals-list');
    if (!card || !list) return;
    card.style.display = '';
    list.innerHTML = arr.map(function(did) {{
      var esc = String(did).replace(/[<>&"]/g, function(c) {{
        return {{'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}}[c];
      }});
      return '<a href="/deal/' + encodeURIComponent(did) + '" '
           + 'class="badge badge-blue" '
           + 'style="text-decoration: none; font-family: monospace;">'
           + esc + '</a>';
    }}).join('');
  }} catch (e) {{ /* ignore */ }}
}})();
</script>
</body></html>
"""
    from ..ui._html_polish import polish_tables_in_html
    html_doc = polish_tables_in_html(html_doc)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return out_path
