"""Dashboard — private-web-app landing page.

Renders four sections composed from existing data sources:

1. **Available analyses** — curated user-triggerable routes with
   descriptions + fixture links so analysts can immediately run them.

2. **Recent results** — in-process job queue (``infra.job_queue``)
   + on-disk run history (``infra.run_history``).

3. **System status** — platform version, uptime, DB reachability,
   migration state, job-queue worker health, PHI posture.

4. **Data freshness** — per-source last-refreshed timestamps from
   the ``data_source_status`` table (``data.data_refresh``). Color-
   coded traffic lights: green < 7 d, amber 7-30 d, red > 30 d.

All four sections render graceful empty states (fresh Heroku deploy
has zero deals, zero runs, zero data refreshes).

Public API:
    render_dashboard(db_path: str, *, started_at: datetime | None = None) -> str
"""
from __future__ import annotations

import html as _html
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def _safe_status_str(v: object) -> str:
    """Coerce a possibly-NaN covenant_status value to a string safely.

    pandas serializes NULL DB columns as float('nan'), which is truthy
    so the common `(value or "")` idiom doesn't catch it, and calling
    `.upper()` on the float then crashes. This helper canonicalizes
    None and NaN to empty string.

    Same pattern as the number_maybe NaN fix in
    _chartis_kit_editorial.py — surfaced by the seeded-DB integration
    test 2026-04-26.
    """
    if v is None:
        return ""
    if isinstance(v, float) and v != v:  # NaN: x != x is True only for NaN
        return ""
    s = str(v)
    return "" if s.lower() == "nan" else s


# ── Curated analyses catalog ───────────────────────────────────────
# Not the full 40-module module_index — a focused subset of the
# highest-signal user-triggerable analyses. Each entry is a single
# click away, with a fixture parameter when one applies.

_CURATED_ANALYSES: List[Dict[str, str]] = [
    {
        "name": "Thesis Pipeline",
        "route": "/diligence/thesis-pipeline?dataset=hospital_04_mixed_payer",
        "category": "One-click diligence",
        "desc": "Run the full 19-step diligence chain on a fixture in ~170 ms.",
        "runtime": "~170 ms",
    },
    {
        "name": "HCRIS Peer X-Ray",
        "route": "/diligence/hcris-xray?ccn=010001",
        "category": "Screening",
        "desc": "Benchmark a hospital vs 25–50 bed/state/region-matched peers across 15 metrics.",
        "runtime": "~250 ms cold, ~7 ms cached",
    },
    {
        "name": "Bear Case Auto-Generator",
        "route": "/diligence/bear-case?dataset=hospital_04_mixed_payer",
        "category": "Synthesis",
        "desc": "Evidence-synthesized bear case from 8 source modules with citation keys.",
        "runtime": "~100 ms",
    },
    {
        "name": "Regulatory Calendar × Kill-Switch",
        "route": "/diligence/regulatory-calendar",
        "category": "Risk",
        "desc": "11 CMS/OIG/FTC events mapped to named thesis drivers. First-kill dates.",
        "runtime": "~50 ms",
    },
    {
        "name": "Covenant Stress Lab",
        "route": "/diligence/covenant-stress",
        "category": "Financial",
        "desc": "500-path × 20-quarter breach probability × 4 covenants.",
        "runtime": "~3–7 s",
    },
    {
        "name": "Payer Mix Stress",
        "route": "/diligence/payer-stress",
        "category": "Risk",
        "desc": "500-path rate-shock MC over 19 curated payers + HHI amplifier.",
        "runtime": "~2–5 s",
    },
    {
        "name": "Bridge Auto-Auditor",
        "route": "/diligence/bridge-audit",
        "category": "Diligence",
        "desc": "Paste banker bridge, get risk-adjusted rebuild vs ~3,000 historical outcomes.",
        "runtime": "~4 s",
    },
    {
        "name": "Deal Autopsy",
        "route": "/diligence/deal-autopsy",
        "category": "Pattern match",
        "desc": "9-dim signature match against 12 named historical failures.",
        "runtime": "~50 ms",
    },
    {
        "name": "Corpus Browser",
        "route": "/sponsor-league",
        "category": "Market intel",
        "desc": "173 corpus-browser pages: sponsor league, vintage cohorts, payer intelligence, etc.",
        "runtime": "varies",
    },
    {
        "name": "IC Packet Builder",
        "route": "/diligence/ic-packet",
        "category": "Deliverable",
        "desc": "Print-ready IC memo bundling every diligence module.",
        "runtime": "~500 ms",
    },
]


# ── Utility: freshness bucket ──────────────────────────────────────

def _freshness_bucket(last_refreshed_iso: Optional[str]) -> tuple[str, str]:
    """Classify an ISO timestamp into (level, label) — level ∈ {ok/stale/cold/never}."""
    if not last_refreshed_iso:
        return ("never", "never refreshed")
    try:
        ts = datetime.fromisoformat(last_refreshed_iso.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
    except ValueError:
        return ("never", "unparseable")
    days = (datetime.now(timezone.utc) - ts).days
    if days < 7:
        return ("ok", f"{days}d ago")
    if days < 30:
        return ("stale", f"{days}d ago")
    return ("cold", f"{days}d ago")


def _dot(level: str) -> str:
    """Traffic-light dot — tone comes from the .dash-dot-* classes in
    ``_DASH_CSS`` (kit severity tokens), not per-span inline hexes."""
    lvl = level if level in ("ok", "stale", "cold", "never") else "never"
    return f'<span class="dash-dot dash-dot-{lvl}" aria-hidden="true"></span>'


# ── Page-scoped CSS ────────────────────────────────────────────────
# One namespaced <style> block for the whole dashboard. Every class
# resolves to the kit's semantic custom properties (with canonical
# fallbacks) so retheming stays a one-file change in _chartis_kit.
# Replaces the pre-editorial inline-style idiom flagged by the
# 2026-07 design audit (146 inline styles, 17 raw legacy hexes).

_DASH_CSS = """<style>
/* ── dashboard editorial facelift · .dash-* namespace ─────────── */
.dash-link { color:var(--sc-teal-ink,#155752); font-weight:500;
  text-decoration:none; }
.dash-link:hover { text-decoration:underline; }
.dash-link:focus-visible { outline:2px solid var(--sc-teal-ink,#155752);
  outline-offset:2px; }
.dash-dim { color:var(--sc-text-dim,#465366); }
.dash-faint { color:var(--sc-text-faint,#7a8699); }
/* Element-qualified: .wc-container p (element+class) would otherwise
   out-rank a bare class and re-impose its 4px margins on these. */
p.dash-note { margin:0 0 10px; color:var(--sc-text-dim,#465366);
  font-size:12px; }
p.dash-note-after { margin:10px 0 0; color:var(--sc-text-dim,#465366);
  font-size:12px; }
p.dash-note.sm, p.dash-note-after.sm { font-size:11px; }
.dash-actions-note { font-weight:normal; font-size:11px; }
.dash-form-inline { display:inline; margin:0; }
.dash-grow { flex:1; }
.dash-static { flex-shrink:0; }
.dash-btn-row { flex-shrink:0; display:flex; gap:4px; }
.dash-runtime { font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-size:11px; }
.dash-id { font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-size:11px; color:var(--sc-text-dim,#465366);
  text-transform:uppercase; letter-spacing:0.03em; }
.dash-ts { flex-shrink:0; color:var(--sc-text-faint,#7a8699);
  font-size:11px; font-family:var(--sc-mono,'JetBrains Mono',monospace);
  white-space:nowrap; }
.dash-ul { list-style:none; padding:0; margin:0; }
.dash-ul.dash-evts { font-size:13px; }
.dash-svg-mid { vertical-align:middle; }
.dash-id-col { min-width:100px; }
.dash-list-row { padding:8px 0;
  border-bottom:1px solid var(--sc-bone,#ece5d6);
  display:flex; align-items:center; gap:12px; }
.dash-list-row:last-child { border-bottom:none; }
.dash-list-row.pad-sm { padding:6px 0; }
.dash-list-row.pad-lg { padding:10px 0; }
.dash-list-row.pad-x  { padding:8px 12px; }
.dash-evt-body { flex:1; color:var(--sc-text,#1a2332); }
.dash-reasons { flex-shrink:0; font-size:12px; display:flex;
  flex-wrap:wrap; gap:12px; }
.dash-pos  { color:var(--sc-positive,#0a8a5f); }
.dash-warn { color:var(--sc-warning,#b8732a); }
.dash-neg  { color:var(--sc-negative,#b5321e); }
.dash-neg-strong { color:var(--sc-negative,#b5321e); font-weight:600; }

/* Traffic-light dots — freshness buckets + job statuses */
.dash-dot { display:inline-block; width:8px; height:8px;
  border-radius:50%; margin-right:6px; }
.dash-dot-ok    { background:var(--sc-positive,#0a8a5f); }
.dash-dot-stale { background:var(--sc-warning,#b8732a); }
.dash-dot-cold  { background:var(--sc-negative,#b5321e); }
.dash-dot-never { background:var(--sc-text-faint,#8a93a0); }

/* Buttons — one ghost + one icon treatment for all page controls */
.dash-btn-ghost { background:#fff;
  border:1px solid var(--sc-rule,#d6cfc0);
  color:var(--sc-teal-ink,#155752); padding:2px 10px; border-radius:2px;
  font-size:11px; font-weight:500; cursor:pointer;
  font-family:var(--sc-sans,'Inter Tight',sans-serif);
  transition:border-color 0.1s, background 0.1s; }
.dash-btn-ghost:hover { border-color:var(--sc-teal-ink,#155752);
  background:var(--sc-parchment,#f5f1ea); }
.dash-btn-ghost:focus-visible {
  outline:2px solid var(--sc-teal-ink,#155752); outline-offset:1px; }
.dash-btn-icon { background:transparent; border:0;
  color:var(--sc-text-faint,#8a93a0); cursor:pointer; font-size:14px;
  padding:0 4px; transition:color 0.1s; }
.dash-btn-icon:hover { color:var(--sc-teal-ink,#155752); }
.dash-btn-icon:focus-visible {
  outline:2px solid var(--sc-teal-ink,#155752); outline-offset:1px;
  color:var(--sc-teal-ink,#155752); }

/* Mono tag chips — event kinds, PINNED marker */
.dash-tag { display:inline-block; flex-shrink:0; padding:1px 6px;
  font-family:var(--sc-mono,'JetBrains Mono',monospace); font-size:9px;
  font-weight:600; letter-spacing:0.08em; text-transform:uppercase;
  border:1px solid var(--sc-rule,#d6cfc0); border-radius:2px;
  color:var(--sc-text-dim,#465366);
  background:var(--sc-parchment,#f5f1ea); min-width:42px;
  text-align:center; }
.dash-tag.ml { margin-left:6px; }
.dash-tag.t-neg  { color:var(--sc-negative,#b5321e); }
.dash-tag.t-warn { color:var(--sc-warning,#b8732a); }
.dash-tag.t-pos  { color:var(--sc-positive,#0a8a5f); }
.dash-tag.t-teal { color:var(--sc-teal-ink,#155752); }

/* Jump row + section band dividers */
.dash-jump { display:flex; gap:16px; flex-wrap:wrap; margin:0 0 8px;
  font-family:var(--sc-mono,'JetBrains Mono',monospace); font-size:10px;
  letter-spacing:0.08em; text-transform:uppercase; }
.dash-jump a { color:var(--sc-text-dim,#465366); text-decoration:none;
  border-bottom:1px solid transparent; padding-bottom:1px; }
.dash-jump a:hover, .dash-jump a:focus-visible {
  color:var(--sc-teal-ink,#155752);
  border-bottom-color:var(--sc-teal-ink,#155752); outline:none; }
.dash-band { margin:28px 0 2px; scroll-margin-top:70px; }

/* ⌘K discoverability strip */
.dash-cmdk-hint { margin:4px 0 14px; padding:8px 12px;
  background:var(--sc-parchment,#f5f1ea);
  border:1px solid var(--sc-rule,#d6cfc0); border-radius:2px;
  font-size:12px; color:var(--sc-text-dim,#465366); }
.dash-cmdk-hint kbd {
  font-family:var(--sc-mono,'JetBrains Mono',monospace); padding:1px 5px;
  background:#fff; color:var(--sc-text,#1a2332);
  border:1px solid var(--sc-rule,#d6cfc0); border-radius:2px;
  font-size:11px; }

/* Portfolio-pulse hero — kit navy panel idiom */
.dash-hero { background:var(--sc-navy,#0b2341); color:#fff;
  padding:22px 26px; border-radius:2px; margin:6px 0 18px; }
.dash-hero-top { display:flex; align-items:center;
  justify-content:space-between; margin-bottom:14px; }
h2.dash-hero-label { font-size:11px; font-weight:700; margin:0;
  text-transform:uppercase; letter-spacing:0.18em; color:#fff; }
.dash-hero-live { display:inline-flex; align-items:center; gap:6px;
  font-size:10px; color:rgba(255,255,255,0.72); font-weight:600;
  text-transform:uppercase; letter-spacing:0.12em; }
.dash-hero-stats { display:flex; gap:24px; flex-wrap:wrap;
  margin-bottom:16px; }
.dash-hero-stat { flex:1; min-width:120px; }
.dash-hero-stat .v { font-size:32px; font-weight:700; color:#fff;
  line-height:1; font-variant-numeric:tabular-nums;
  letter-spacing:-0.02em; }
.dash-hero-stat .l { font-size:10px; font-weight:600;
  text-transform:uppercase; letter-spacing:0.1em;
  color:rgba(255,255,255,0.78); margin:6px 0 0; }
p.dash-hero-sub { font-size:10px; font-weight:600;
  text-transform:uppercase; letter-spacing:0.08em;
  color:rgba(255,255,255,0.78); margin:8px 0 4px; }
.dash-mosaic { display:flex; flex-wrap:wrap; gap:4px; margin-top:2px;
  line-height:0; }
.dash-mosaic a { display:inline-block; width:18px; height:18px;
  border-radius:2px; transition:transform 0.1s; }
.dash-mosaic a:hover, .dash-mosaic a:focus-visible {
  transform:scale(1.15); outline:2px solid #fff; outline-offset:1px; }
.dash-hero-legend { display:flex; gap:14px; margin-top:8px;
  flex-wrap:wrap; }
.dash-hero-legend .chip { display:inline-flex; align-items:center;
  gap:4px; font-size:11px; color:rgba(255,255,255,0.78);
  font-variant-numeric:tabular-nums; }
.dash-hero-legend .sw { display:inline-block; width:10px; height:10px;
  border-radius:2px; }
.dash-hero-legend strong { color:#fff; }
.dash-hero-moic { display:flex; align-items:center; gap:14px;
  margin-top:14px; padding-top:12px;
  border-top:1px solid rgba(255,255,255,0.18); flex-wrap:wrap; }
.dash-hero-moic .lab { font-size:10px; font-weight:600; margin:0;
  text-transform:uppercase; letter-spacing:0.08em;
  color:rgba(255,255,255,0.78); flex-shrink:0; }
.dash-hero-moic .big { font-size:28px; font-weight:700; color:#fff;
  font-variant-numeric:tabular-nums; flex-shrink:0; }
.dash-hero-moic .panel { background:#fff; padding:6px 10px;
  border-radius:2px; flex-shrink:0; }
.dash-hero-moic .pct { font-size:11px; color:rgba(255,255,255,0.78);
  font-variant-numeric:tabular-nums; margin:0; }
.dash-hero-syn { background:rgba(255,255,255,0.08);
  border-left:3px solid var(--sc-warning,#b8732a); padding:12px 16px;
  border-radius:2px; margin:18px 0 0; }
.dash-hero-syn .eb { font-size:10px; font-weight:600;
  text-transform:uppercase; letter-spacing:0.1em;
  color:rgba(255,255,255,0.78); margin:0 0 4px; }
.dash-hero-syn .tx { font-size:14px; color:#fff; line-height:1.5;
  margin:0; }
@keyframes wc-pulse {
  0%,100% { opacity:1; transform:scale(1); }
  50% { opacity:0.55; transform:scale(0.85); } }
.wc-pulse-dot { display:inline-block; width:8px; height:8px;
  border-radius:50%; background:#7ED3A8; box-shadow:0 0 6px #7ED3A8;
  animation:wc-pulse 1.6s ease-in-out infinite; }
@media (prefers-reduced-motion: reduce) {
  .wc-pulse-dot { animation:none; }
  .dash-mosaic a:hover, .dash-mosaic a:focus-visible { transform:none; }
}

/* Sharpest-insight card — sibling anchors, no nesting */
.dash-insight { position:relative; display:flex; align-items:baseline;
  gap:12px; margin:4px 0 16px; padding:18px 22px; background:#fff;
  border:1px solid var(--sc-rule,#d6cfc0); border-left-width:4px;
  border-radius:2px; transition:border-color 0.1s; }
.dash-insight:hover { border-color:var(--sc-teal-ink,#155752); }
.dash-insight-dot { flex-shrink:0; width:10px; height:10px;
  border-radius:50%; position:relative; top:-1px; }
.dash-insight-alert    { border-left-color:var(--sc-negative,#b5321e); }
.dash-insight-warn     { border-left-color:var(--sc-warning,#b8732a); }
.dash-insight-positive { border-left-color:var(--sc-positive,#0a8a5f); }
.dash-insight-neutral  { border-left-color:var(--sc-teal-ink,#155752); }
.dash-insight-alert    .dash-insight-dot { background:var(--sc-negative,#b5321e); }
.dash-insight-warn     .dash-insight-dot { background:var(--sc-warning,#b8732a); }
.dash-insight-positive .dash-insight-dot { background:var(--sc-positive,#0a8a5f); }
.dash-insight-neutral  .dash-insight-dot { background:var(--sc-teal-ink,#155752); }
.dash-insight-main { flex:1; }
p.dash-insight-eyebrow {
  font-family:var(--sc-mono,'JetBrains Mono',monospace); font-size:10px;
  font-weight:600; text-transform:uppercase; letter-spacing:0.08em;
  color:var(--sc-text-dim,#465366); margin:0; }
/* Undo the .wc-container h3 uppercase/tracking — the headline is a
   serif sentence, not a label. */
h3.dash-insight-headline { margin:0; text-transform:none;
  letter-spacing:normal; }
.dash-insight-headline a {
  font-family:var(--sc-serif,'Source Serif 4',serif); font-size:18px;
  font-weight:600; color:var(--sc-text,#1a2332); text-decoration:none;
  display:inline-block; margin-top:4px; line-height:1.3; }
/* Stretched link: the headline anchor covers the whole card without
   nesting an <a> inside an <a> (the pre-facelift markup fractured). */
.dash-insight-headline a::after { content:""; position:absolute;
  inset:0; }
.dash-insight-headline a:focus-visible { outline:none; }
.dash-insight:focus-within {
  outline:2px solid var(--sc-teal-ink,#155752); outline-offset:1px; }
p.dash-insight-body { font-size:13px; margin:6px 0 0;
  color:var(--sc-text-dim,#465366); }
p.dash-insight-more { margin:8px 0 0; font-size:11px;
  color:var(--sc-text-dim,#465366); }
.dash-insight-more a { position:relative; z-index:1; }
.dash-insight-arrow { flex-shrink:0; font-size:18px;
  color:var(--sc-text-faint,#7a8699); }

/* Exposure bars */
h3.dash-subhead { font-size:11px; font-weight:600;
  color:var(--sc-text,#1a2332); text-transform:uppercase;
  letter-spacing:0.05em; margin:0 0 6px; }
.dash-subhead .qual { font-weight:normal;
  color:var(--sc-text-faint,#7a8699); text-transform:none;
  letter-spacing:normal; }
.dash-bar-row { display:grid; grid-template-columns:140px 1fr 70px;
  align-items:center; gap:10px; padding:4px 0; font-size:12px; }
.dash-bar-row .lab { color:var(--sc-text,#1a2332); white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }
.dash-bar-track { background:var(--sc-parchment,#f5f1ea);
  border-radius:2px; height:14px; overflow:hidden; }
.dash-bar-fill { height:100%; transition:width 0.2s; }
.dash-bar-fill.teal { background:var(--sc-teal,#155752); }
.dash-bar-fill.warn { background:var(--sc-warning,#b8732a); }
.dash-bar-row .num { color:var(--sc-text-dim,#465366);
  font-variant-numeric:tabular-nums; text-align:right;
  font-family:var(--sc-mono,'JetBrains Mono',monospace); }
p.dash-empty-inline { margin:0; color:var(--sc-text-faint,#7a8699);
  font-size:12px; font-style:italic; }

/* Pinned-deal cards */
.dash-pin-grid { display:flex; flex-wrap:wrap; gap:8px; }
.dash-pin-card { display:block; text-decoration:none; color:inherit;
  background:#fff; border:1px solid var(--sc-rule,#d6cfc0);
  border-radius:2px; padding:10px 12px; min-width:160px;
  flex:1 1 160px; transition:border-color 0.1s; }
.dash-pin-card:hover, .dash-pin-card:focus-visible {
  border-color:var(--sc-teal-ink,#155752); outline:none; }
.dash-pin-head { display:flex; align-items:baseline;
  justify-content:space-between; gap:6px; }
.dash-pin-meta { display:flex; align-items:center; gap:8px;
  margin-top:4px; }
.dash-pin-reason { flex:1; font-size:12px;
  color:var(--sc-text-dim,#465366); white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }

/* Predicted-outcomes rows */
.dash-moic-median { font-weight:600; color:var(--sc-teal-ink,#155752);
  font-size:14px;
  border-bottom:1px dotted var(--sc-teal-ink,#155752); }
.dash-moic-legend { display:flex; align-items:center; gap:14px;
  font-size:11px; color:var(--sc-text-dim,#465366);
  margin-bottom:10px; flex-wrap:wrap; }
.dash-moic-legend .li { display:inline-flex; align-items:center;
  gap:5px; }
.dash-moic-legend .sw-range { display:inline-block; width:14px;
  height:6px; background:var(--sc-teal,#155752); opacity:0.35;
  border-radius:2px; }
.dash-moic-legend .sw-median { display:inline-block; width:8px;
  height:8px; background:var(--sc-teal,#155752); border-radius:50%;
  border:1.5px solid #fff;
  box-shadow:0 0 0 1px var(--sc-teal,#155752); }
.dash-deal-cell { color:inherit; text-decoration:none;
  min-width:160px; flex-shrink:0; }
.dash-deal-cell .nm { font-size:13px; }
.dash-deal-cell .id { font-size:10px; margin-top:2px; }
.dash-moic-cell { flex:1; font-size:12px;
  color:var(--sc-text,#1a2332); font-variant-numeric:tabular-nums;
  white-space:nowrap; }
.dash-moic-cell a { text-decoration:none; color:inherit; }

/* Quiet-too-long rows */
.dash-quiet-link { flex:1; font-size:12px;
  color:var(--sc-teal-ink,#155752); }
.dash-quiet-chip { display:inline-block; padding:1px 8px;
  border-radius:2px; font-size:11px; font-weight:600; }

/* Templates — whole-row launch anchor */
.dash-tpl-launch { flex:1; color:inherit; text-decoration:none; }
.dash-tpl-launch .sub { font-size:11px;
  color:var(--sc-text-faint,#7a8699); margin-top:2px; }

/* System-status value line (inside ck_kpi_block) */
.dash-status-val { font-size:13px; font-weight:500;
  color:var(--sc-text,#1a2332); }
.dash-status-grid {
  grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:8px; }
.dash-subhead.mt { margin:14px 0 6px; }
</style>"""


# ── Section renderers ──────────────────────────────────────────────

def _render_analyses_section() -> str:
    from . import _web_components as _wc

    rows: List[List[str]] = []
    for a in _CURATED_ANALYSES:
        # Save-as-template form: pre-fills the name + route from
        # this row so the partner just clicks ★ to bookmark the
        # current parametrization. Wraps to /api/saved-analyses
        # POST → 303-redirect back to /dashboard.
        save_form = (
            f'<form method="POST" action="/api/saved-analyses" '
            f'class="dash-form-inline" '
            f'onsubmit="var n=prompt(\'Save this analysis as template '
            f'and give it a name:\', \'{_html.escape(a["name"])}\');'
            f'if(!n){{return false;}}'
            f'this.querySelector(\'input[name=name]\').value=n;return true;">'
            f'<input type="hidden" name="name" value="">'
            f'<input type="hidden" name="route" '
            f'value="{_html.escape(a["route"])}">'
            f'<input type="hidden" name="description" '
            f'value="{_html.escape(a["desc"][:200])}">'
            f'<input type="hidden" name="redirect" value="/dashboard">'
            f'<button type="submit" class="dash-btn-icon" '
            f'title="Save as template for one-click relaunch">★</button>'
            f'</form>'
        )
        rows.append([
            (f'<a href="{_html.escape(a["route"])}" class="dash-link">'
             f'{_html.escape(a["name"])}</a>'
             f'&nbsp;{save_form}'),
            f'<span class="dash-dim">{_html.escape(a["category"])}</span>',
            _html.escape(a["desc"]),
            (f'<span class="dash-dim dash-runtime">'
             f'{_html.escape(a["runtime"])}</span>'),
        ])
    table = _wc.sortable_table(
        ["Analysis", "Category", "What it does", "Runtime"],
        rows, id="dashboard-analyses", hide_columns_sm=[1, 3],
        filterable=True, filter_placeholder="Filter analyses…",
    )
    return _wc.section_card(
        "What you can run", table, pad=False,
        actions_html=(
            '<span class="dash-faint dash-actions-note">'
            'click ★ to save as template</span>'
        ),
    )


def _workflow_badge_counts(db_path: str) -> Dict[str, Optional[int]]:
    """Read live counts for the Daily workflow surfaces.

    Each value is the number a partner cares about for the morning
    sweep: open alerts to triage, overdue deadlines to chase, deals
    on the watchlist, etc. Failures degrade silently to ``None`` so a
    missing table on a fresh DB doesn't break the dashboard render.
    """
    counts: Dict[str, Optional[int]] = {}
    try:
        from ..portfolio.store import PortfolioStore
        store = PortfolioStore(db_path)
    except Exception:  # noqa: BLE001
        return counts

    def _safe(key: str, fn) -> None:
        try:
            counts[key] = int(fn())
        except Exception:  # noqa: BLE001 — every count is best-effort
            counts[key] = None

    try:
        from ..alerts.alerts import active_count
        _safe("alerts", lambda: active_count(store))
    except Exception:  # noqa: BLE001 — module import itself can fail
        counts["alerts"] = None

    try:
        from ..deals.deal_deadlines import overdue
        _safe("overdue_deadlines", lambda: len(overdue(store)))
    except Exception:  # noqa: BLE001
        counts["overdue_deadlines"] = None

    try:
        from ..deals.watchlist import list_starred
        _safe("watchlist", lambda: len(list_starred(store)))
    except Exception:  # noqa: BLE001
        counts["watchlist"] = None

    try:
        from ..data.pipeline import list_searches
        import sqlite3 as _sql
        with _sql.connect(db_path) as con:
            con.row_factory = _sql.Row
            _safe("saved_searches", lambda: len(list_searches(con)))
    except Exception:  # noqa: BLE001
        counts["saved_searches"] = None

    return counts


def _badge(n: Optional[int], *, level: str = "neutral") -> str:
    """Inline count chip rendered next to a workflow label."""
    if n is None or n <= 0:
        return ""
    palette = {
        "ok": ("#DCE6D9", "#3F7D4D"),
        "warn": ("#EFE2BC", "#B7791F"),
        "alert": ("#EBD3CD", "#A53A2D"),
        "neutral": ("#D6E1EB", "#2C5C84"),
    }
    bg, fg = palette.get(level, palette["neutral"])
    return (
        f'<span style="display:inline-block;margin-left:8px;'
        f'padding:1px 8px;background:{bg};color:{fg};'
        f'border-radius:9999px;font-size:11px;font-weight:600;'
        f'font-variant-numeric:tabular-nums;">{n}</span>'
    )


def _since_yesterday_events(db_path: str,
                            *, window_hours: int = 24) -> List[Dict[str, str]]:
    """Gather a cross-source change list for the "Since yesterday" card.

    Reads the four time-tagged tables that exist on a live install:
      - alert_history (new alerts fired in the window)
      - analysis_runs (packets built)
      - data_source_status (data refreshed)
      - audit_events (login/create/update events, scoped to non-GET)

    Each event is normalized into a dict with keys:
      ``at`` (ISO timestamp), ``icon``, ``label`` (≤ 80 chars),
      ``href`` (optional), ``kind`` (category for grouping).

    Every source is best-effort — a missing table on a fresh DB just
    returns no events from that source. Caller can render the empty
    state as "no changes in the last 24 hours."
    """
    import sqlite3 as _sql
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td

    cutoff = (_dt.now(_tz.utc) - _td(hours=window_hours)).isoformat()
    events: List[Dict[str, str]] = []

    def _q(sql: str, params: tuple) -> List[Any]:
        try:
            with _sql.connect(db_path) as con:
                con.row_factory = _sql.Row
                return list(con.execute(sql, params).fetchall())
        except Exception:  # noqa: BLE001 — missing table / permission / race
            return []

    # Alerts fired. Pull `kind` + `trigger_key` so the UI can emit an
    # inline ack form per row — the three together identify a specific
    # alert instance for POST /api/alerts/ack.
    for r in _q(
        "SELECT first_seen_at AS at, kind, deal_id, trigger_key, "
        "title, severity "
        "FROM alert_history WHERE first_seen_at >= ? "
        "ORDER BY first_seen_at DESC LIMIT 10",
        (cutoff,),
    ):
        events.append({
            "at": r["at"] or "",
            "icon": "🔔",
            "kind": "alert",
            "label": f'{r["severity"].upper()}: {r["title"]}'[:80],
            "href": f"/deal/{r['deal_id']}" if r["deal_id"] else "/alerts",
            # Ack-form fields
            "alert_kind": r["kind"] or "",
            "alert_deal_id": r["deal_id"] or "",
            "alert_trigger_key": r["trigger_key"] or "",
        })

    # Data refreshes
    for r in _q(
        "SELECT last_refresh_at AS at, source_name, record_count, status "
        "FROM data_source_status WHERE last_refresh_at >= ? "
        "ORDER BY last_refresh_at DESC",
        (cutoff,),
    ):
        status = (r["status"] or "").lower()
        icon = "✓" if status in ("ok", "success") else "!"
        records = r["record_count"] or 0
        events.append({
            "at": r["at"] or "",
            "icon": icon,
            "kind": "refresh",
            "label": f"{r['source_name']} refreshed, {records:,} rows",
            "href": "/data/refresh",
        })

    # Packets built
    for r in _q(
        "SELECT created_at AS at, deal_id, model_version "
        "FROM analysis_runs WHERE created_at >= ? "
        "ORDER BY created_at DESC LIMIT 10",
        (cutoff,),
    ):
        events.append({
            "at": r["at"] or "",
            "icon": "📋",
            "kind": "packet",
            "label": f"Packet built for {r['deal_id']} "
                     f"(v{r['model_version']})"[:80],
            "href": f"/analysis/{r['deal_id']}",
        })

    # High-signal audit events only: logins, user management, exports
    high_signal_actions = (
        "login.success", "user.create", "user.delete",
        "backup.create", "deal.create", "deal.archive",
    )
    placeholders = ",".join("?" * len(high_signal_actions))
    for r in _q(
        f"SELECT at, actor, action, target FROM audit_events "
        f"WHERE at >= ? AND action IN ({placeholders}) "
        f"ORDER BY at DESC LIMIT 10",
        (cutoff, *high_signal_actions),
    ):
        action = r["action"] or ""
        if action == "login.success":
            icon, label = "→", f"{r['actor']} signed in"
        elif action.startswith("user."):
            icon = "👤"
            verb = action.split(".", 1)[1]
            label = f"{r['actor']} {verb}d user {r['target']}"[:80]
        elif action == "backup.create":
            icon, label = "💾", f"{r['actor']} ran a backup"
        elif action.startswith("deal."):
            icon = "📁"
            verb = action.split(".", 1)[1]
            label = f"{r['actor']} {verb}d deal {r['target']}"[:80]
        else:
            icon, label = "·", f"{r['actor']}: {action}"
        events.append({
            "at": r["at"] or "",
            "icon": icon,
            "kind": "audit",
            "label": label,
            "href": "",
        })

    # Newest first, capped
    events.sort(key=lambda e: e["at"] or "", reverse=True)
    return events[:20]


def _all_insights(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Compute ALL candidate insights (not just the top-1).

    Used by the dashboard headline card (which picks #1) AND by
    the /insights full-page view (which renders the complete
    ranked list). Insights are returned sorted highest-score first;
    consumers can slice as needed.

    Each insight is a dict with:
      - ``kind`` (slug for templating)
      - ``headline`` (one-line attention-grabber, ≤ 100 chars)
      - ``body`` (one-line "so what", ≤ 200 chars)
      - ``href`` (drill-down URL)
      - ``tone`` ("alert" | "warn" | "positive" | "neutral")
      - ``score`` (priority for ranking — higher = more urgent)
    """
    if deals is None:
        try:
            from .portfolio_risk_scan_page import _gather_per_deal
            deals = _gather_per_deal(db_path)
        except Exception:  # noqa: BLE001
            return []
    if not deals:
        return []

    insights: List[Dict[str, Any]] = []
    insights.extend(_chain_concentration_insights(deals))
    insights.extend(_covenant_insights(deals))
    insights.extend(_health_distribution_insights(deals))
    insights.extend(_freshness_insights(deals))
    insights.extend(_attention_pileup_insights(deals))
    insights.extend(_geo_concentration_insights(deals))
    insights.extend(_sponsor_concentration_insights(db_path, deals))
    insights.extend(_low_quality_insights(deals))
    insights.extend(_hrrp_penalty_insights(deals))
    insights.extend(_quiet_morning_insights(deals))

    insights.sort(key=lambda i: i.get("score", 0), reverse=True)
    return insights


# ── Individual insight detectors ──────────────────────────────────
#
# Each returns 0+ insight dicts. Composing them in `_all_insights`
# lets us add new signals without touching the picking logic.

def _chain_concentration_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Multiple deals in the same CMS POS chain → correlated
    covenant + sponsor + regulatory exposure."""
    chain_counts: Dict[str, List[Dict[str, Any]]] = {}
    for d in deals:
        c = (d.get("chain") or "").strip()
        if c:
            chain_counts.setdefault(c, []).append(d)
    out: List[Dict[str, Any]] = []
    for chain, members in chain_counts.items():
        if len(members) >= 2:
            names = ", ".join(m["name"] for m in members[:3])
            if len(members) > 3:
                names += f", +{len(members) - 3} more"
            out.append({
                "kind": "chain_concentration",
                "headline": f"You have {len(members)} deals in the {chain} chain",
                "body": (f"Same corporate parent → correlated covenant, "
                         f"sponsor, and regulatory exposure. "
                         f"Deals: {names}."),
                "href": "/portfolio/risk-scan",
                "tone": "warn",
                "score": 40 + 10 * len(members),
            })
    return out


def _covenant_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """TRIPPED is the scariest signal; TIGHT pile-up is a quieter
    warning that 3+ deals are within 1 turn of breach."""
    out: List[Dict[str, Any]] = []
    tripped = [d for d in deals
               if _safe_status_str(d.get("covenant_status")).upper() == "TRIPPED"]
    if tripped:
        t = tripped[0]
        rest = (
            f"{len(tripped)-1} other deal{'s' if len(tripped) > 2 else ''} also tripped."
            if len(tripped) > 1 else ""
        )
        out.append({
            "kind": "covenant_tripped",
            "headline": f"Covenant TRIPPED on {t['name']}",
            "body": (f"{t['name']} is over its leverage cap: "
                     f"action today. {rest}".strip()),
            "href": f"/deal/{t['deal_id']}",
            "tone": "alert",
            "score": 100,
        })
    tight = [d for d in deals
             if _safe_status_str(d.get("covenant_status")).upper() == "TIGHT"]
    if len(tight) >= 3:
        names = ", ".join(d["name"] for d in tight[:3])
        out.append({
            "kind": "covenant_tight_pileup",
            "headline": f"{len(tight)} deals within 1 turn of covenant breach",
            "body": (f"Cluster of TIGHT-covenant deals: {names}. "
                     f"Run covenant-stress on each before any "
                     f"adverse-case shock lands."),
            "href": "/diligence/covenant-stress",
            "tone": "warn",
            "score": 50 + 5 * len(tight),
        })
    return out


def _health_distribution_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Worst-of-portfolio + median-shift signals."""
    out: List[Dict[str, Any]] = []
    scored = [d for d in deals if isinstance(d.get("score"), int)]
    if not scored:
        return out

    # Single worst deal — even if covenant is fine, a 25 health is
    # an "investigate today" signal.
    worst = min(scored, key=lambda d: d["score"])
    if worst["score"] < 40:
        out.append({
            "kind": "single_worst_deal",
            "headline": (f"{worst['name']} health score is "
                         f"{worst['score']} ({worst.get('band') or 'poor'})"),
            "body": (f"{worst['name']} is the weakest deal in the "
                     f"portfolio: drill into the deal page to see "
                     f"which components are dragging the score."),
            "href": f"/deal/{worst['deal_id']}",
            "tone": "warn",
            "score": 35 + max(0, 40 - worst["score"]),
        })

    # Median check — if median < 60, the whole portfolio is shaky.
    sorted_scores = sorted(d["score"] for d in scored)
    median = sorted_scores[len(sorted_scores) // 2]
    if median < 60 and len(scored) >= 5:
        out.append({
            "kind": "median_health_low",
            "headline": (f"Median health score across {len(scored)} "
                         f"deals is {median}"),
            "body": ("Half the portfolio is below a 60: the issue "
                     "isn't a single bad deal. Look for systemic "
                     "drivers (sector, payer mix, vintage)."),
            "href": "/portfolio/risk-scan",
            "tone": "warn",
            "score": 28 + (60 - median),
        })
    return out


def _freshness_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Stale snapshots → tool is rendering old numbers."""
    stale = [d for d in deals
             if d.get("snap_age_days") is not None
             and d["snap_age_days"] > 30]
    if len(stale) >= 3:
        worst = max(stale, key=lambda x: x.get("snap_age_days") or 0)
        return [{
            "kind": "stale_portfolio",
            "headline": (f"{len(stale)} deals haven't refreshed "
                         f"in over 30 days"),
            "body": (f"Oldest: {worst['name']} "
                     f"({worst['snap_age_days']}d stale). "
                     f"Current numbers may be outdated."),
            "href": "/data/refresh",
            "tone": "warn",
            "score": 25 + len(stale) * 3,
        }]
    return []


def _attention_pileup_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """When a meaningful share of the portfolio needs attention."""
    flagged = [d for d in deals
               if (d.get("alerts") or 0) > 0
               or (d.get("overdue_deadlines") or 0) > 0
               or _safe_status_str(d.get("covenant_status")).upper() == "TRIPPED"]
    if len(flagged) >= 3 and len(deals) >= 5:
        pct = int(100 * len(flagged) / len(deals))
        return [{
            "kind": "attention_pileup",
            "headline": (f"{len(flagged)} of {len(deals)} deals "
                         f"({pct}%) need attention"),
            "body": (f"Worst deal: {flagged[0]['name']}. "
                     f"See the portfolio risk scan for the full triage."),
            "href": "/portfolio/risk-scan",
            "tone": "alert" if pct > 30 else "warn",
            "score": 30 + pct,
        }]
    return []


def _geo_concentration_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Single-state exposure ≥ 50% → state-policy / Medicaid-rate
    risk concentrated in one regulator's hands. Reads the state
    field from the CMS POS join (already in `deals` dicts via
    chain lookup; falls back to deal name parsing if absent)."""
    # State field isn't propagated through _gather_per_deal yet,
    # so we infer from the chain's POS row when available. This
    # is an approximation that improves once the per-deal POS row
    # is threaded through (separate refactor).
    out: List[Dict[str, Any]] = []
    # Skip for tiny portfolios — concentration math isn't meaningful.
    if len(deals) < 5:
        return out
    # We don't have state yet on the deal dicts; placeholder until
    # _gather_per_deal threads facility.state through.
    # Don't emit anything here for now — better to ship empty than
    # fake.
    return out


def _sponsor_concentration_insights(
    db_path: str,
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Multiple deals from the same sponsor → reputation risk +
    correlated diligence assumptions. Sponsor field comes from the
    deals table profile_json; uses a best-effort lookup."""
    import json as _json
    out: List[Dict[str, Any]] = []
    try:
        from ..portfolio.store import PortfolioStore
        store = PortfolioStore(db_path)
        sponsor_counts: Dict[str, List[str]] = {}
        with store.connect() as con:
            rows = con.execute(
                "SELECT deal_id, profile_json FROM deals "
                "WHERE archived_at IS NULL"
            ).fetchall()
        for r in rows:
            try:
                profile = _json.loads(r["profile_json"] or "{}")
            except (TypeError, _json.JSONDecodeError):
                continue
            sponsor = (profile.get("sponsor") or "").strip()
            if sponsor:
                sponsor_counts.setdefault(sponsor, []).append(r["deal_id"])
        for sponsor, dids in sponsor_counts.items():
            if len(dids) >= 3:
                out.append({
                    "kind": "sponsor_concentration",
                    "headline": (f"{len(dids)} deals from sponsor "
                                 f"{sponsor}"),
                    "body": ("Diligence on these deals is correlated: "
                             "if the sponsor's playbook fails on one, "
                             "expect it to fail on the others."),
                    "href": "/sponsor-league",
                    "tone": "warn",
                    "score": 30 + 5 * len(dids),
                })
    except Exception:  # noqa: BLE001 — best effort
        pass
    return out


def _low_quality_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """CMS Hospital General 5-star rating ≤2 → labor + revenue-cycle
    issues that flow straight into the EBITDA bridge. Cluster of
    these is a real PE concern."""
    low_rated = [d for d in deals
                 if isinstance(d.get("quality_rating"), int)
                 and d["quality_rating"] <= 2]
    if len(low_rated) >= 2:
        names = ", ".join(d["name"] for d in low_rated[:3])
        if len(low_rated) > 3:
            names += f", +{len(low_rated) - 3} more"
        return [{
            "kind": "low_quality_cluster",
            "headline": (f"{len(low_rated)} hospitals at CMS quality "
                         f"≤2 stars"),
            "body": (f"Low CMS rating means readmission penalties + "
                     f"labor friction + patient-experience drag. "
                     f"Deals: {names}."),
            "href": "/portfolio/risk-scan",
            "tone": "warn",
            "score": 35 + 8 * len(low_rated),
        }]
    return []


def _hrrp_penalty_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Hospitals carrying HRRP readmission penalties >2% have
    direct Medicare-revenue exposure: a 2% penalty on Medicare ≈
    60-80bps EBITDA hit on a typical hospital. Cluster of these
    is a real bridge-math concern."""
    high = [d for d in deals
            if isinstance(d.get("hrrp_pct"), (int, float))
            and d["hrrp_pct"] >= 2.0]
    if len(high) >= 2:
        names = ", ".join(d["name"] for d in high[:3])
        if len(high) > 3:
            names += f", +{len(high) - 3} more"
        worst_pct = max(d["hrrp_pct"] for d in high)
        return [{
            "kind": "hrrp_penalty_cluster",
            "headline": (f"{len(high)} hospitals carrying HRRP "
                         f"penalties ≥2%"),
            "body": (f"Worst: {worst_pct:.1f}% Medicare reduction. "
                     f"Each 1% HRRP penalty is ~30-40bps EBITDA "
                     f"on Medicare-heavy facilities. Deals: "
                     f"{names}."),
            "href": "/portfolio/risk-scan",
            "tone": "warn",
            "score": 32 + 8 * len(high),
        }]
    return []


def _quiet_morning_insights(
    deals: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """All-green reassurance — when nothing is firing, say so."""
    no_flags = [d for d in deals
                if (d.get("alerts") or 0) == 0
                and (d.get("overdue_deadlines") or 0) == 0
                and _safe_status_str(d.get("covenant_status")).upper()
                    not in ("TRIPPED", "TIGHT")]
    if len(deals) >= 3 and len(no_flags) == len(deals):
        return [{
            "kind": "all_green",
            "headline": f"All {len(deals)} deals are healthy this morning",
            "body": ("No covenant breaks, no overdue deadlines, no open "
                     "alerts. Great week to focus on the pipeline."),
            "href": "/pipeline",
            "tone": "positive",
            "score": 15,
        }]
    return []


def _compute_sharpest_insight(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Top-ranked candidate — used by the dashboard headline card.
    See ``_all_insights`` for the full ranked list."""
    rows = _all_insights(db_path, deals=deals)
    return rows[0] if rows else None


def _portfolio_pulse_inputs(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Crunch the numbers behind the Portfolio Pulse hero.

    Pulled out of the renderer so tests can assert on the maths
    without parsing HTML.

    Returns a dict with:
      n_deals, total_ev_mm, avg_health, band_counts (great/good/fair/poor),
      portfolio_moic_median + p25 + p75 (from corpus benchmarks),
      hrrp_exposure_mm (annualized $ EBITDA at risk from HRRP penalties),
      headline_synthesis (string — the surprise insight).
    """
    out: Dict[str, Any] = {
        "n_deals": 0,
        "total_ev_mm": 0.0,
        "avg_health": None,
        "band_counts": {"great": 0, "good": 0, "fair": 0, "poor": 0},
        "deal_tiles": [],          # [{deal_id, name, score, band}]
        "portfolio_moic_median": None,
        "portfolio_moic_p25": None,
        "portfolio_moic_p75": None,
        "hrrp_exposure_mm": 0.0,
        "n_hrrp_exposed": 0,
        "headline_synthesis": "",
    }

    rows: List[Dict[str, Any]] = list(deals or [])
    if not rows:
        return out

    out["n_deals"] = len(rows)

    # ── Per-deal profile lookup for EV ──────────────────────────
    profiles: Dict[str, Dict[str, Any]] = {}
    try:
        from ..portfolio.store import PortfolioStore
        import json as _json
        store = PortfolioStore(db_path)
        deal_ids = [d.get("deal_id") for d in rows if d.get("deal_id")]
        if deal_ids:
            with store.connect() as con:
                placeholders = ",".join("?" * len(deal_ids))
                for r in con.execute(
                    f"SELECT deal_id, profile_json FROM deals "
                    f"WHERE deal_id IN ({placeholders})",
                    deal_ids,
                ).fetchall():
                    try:
                        profiles[r["deal_id"]] = _json.loads(
                            r["profile_json"] or "{}")
                    except (TypeError, _json.JSONDecodeError):
                        profiles[r["deal_id"]] = {}
    except Exception:  # noqa: BLE001
        pass

    # HCRIS revenue → EV proxy fallback. Loaded once, used per deal.
    hcris_lookup = None
    try:
        from ..data.hcris import _get_latest_per_ccn
        hcris_lookup = _get_latest_per_ccn()
    except Exception:  # noqa: BLE001
        pass

    # ── Aggregate stats ─────────────────────────────────────────
    score_sum = 0
    score_n = 0
    deal_tiles: List[Dict[str, Any]] = []
    for d in rows:
        deal_id = d.get("deal_id") or ""
        score = d.get("score")
        band = d.get("band") or "unknown"
        if isinstance(score, (int, float)):
            score_sum += int(score)
            score_n += 1
        if band in out["band_counts"]:
            out["band_counts"][band] += 1
        deal_tiles.append({
            "deal_id": deal_id,
            "name": d.get("name") or deal_id,
            "score": score,
            "band": band,
        })

        # Total EV: explicit profile.ev_mm wins; HCRIS proxy second
        prof = profiles.get(deal_id, {})
        ev = prof.get("ev_mm")
        if ev is None and hcris_lookup is not None:
            try:
                if not hcris_lookup.empty:
                    h = hcris_lookup[hcris_lookup["ccn"] == deal_id]
                    if not h.empty:
                        rev = h.iloc[0].get("net_patient_revenue")
                        if rev and rev > 0:
                            ev = float(rev) / 1_000_000.0
            except Exception:  # noqa: BLE001
                pass
        if ev:
            try:
                out["total_ev_mm"] += float(ev)
            except (TypeError, ValueError):
                pass

        # HRRP exposure: penalty% × Medicare-IPPS-equivalent. We
        # use a lightweight proxy: 1% HRRP penalty ≈ 30bps of EBITDA
        # for a typical Medicare-heavy hospital. Anchor a $200M EV
        # deal to ~$20M EBITDA at 10% margin × 30bps × pct.
        # Resulting $ figure is in $M of *annualized* EBITDA at risk.
        hrrp = d.get("hrrp_pct")
        if hrrp and hrrp > 0:
            out["n_hrrp_exposed"] += 1
            ev_for_calc = ev or 200.0  # default proxy if unknown
            ebitda_proxy = ev_for_calc * 0.10
            out["hrrp_exposure_mm"] += (
                ebitda_proxy * 0.0030 * hrrp)

    if score_n > 0:
        out["avg_health"] = round(score_sum / score_n, 1)
    out["deal_tiles"] = deal_tiles

    # ── Portfolio-level predicted MOIC (corpus benchmark) ───────
    # Run benchmark_deal once per deal and aggregate the medians.
    # Bounded — only deals with enough profile signal participate.
    try:
        from ..diligence.comparable_outcomes import benchmark_deal
        from ..data_public.deals_corpus import DealsCorpus
        corpus = DealsCorpus(db_path)
        try:
            corpus.seed(skip_if_populated=True)
        except Exception:  # noqa: BLE001
            pass

        medians: List[float] = []
        for d in rows:
            deal_id = d.get("deal_id") or ""
            prof = profiles.get(deal_id, {})
            target = {
                "sector": d.get("sector") or prof.get("sector")
                          or "hospital",
                "ev_mm": prof.get("ev_mm"),
                "year": prof.get("entry_year") or prof.get("year"),
                "buyer": prof.get("sponsor") or prof.get("buyer") or "",
                "payer_mix": prof.get("payer_mix"),
            }
            try:
                res = benchmark_deal(corpus, target, top_n=10)
            except Exception:  # noqa: BLE001
                continue
            outcome = res.get("outcome_distribution", {})
            moic = outcome.get("moic", {})
            med = moic.get("median")
            if med is not None and outcome.get("n_comparables", 0) >= 3:
                medians.append(float(med))

        if medians:
            sorted_m = sorted(medians)
            n = len(sorted_m)
            out["portfolio_moic_median"] = round(
                sorted_m[n // 2], 2)
            # 25th/75th of the per-deal medians = portfolio dispersion
            out["portfolio_moic_p25"] = round(
                sorted_m[max(0, int(n * 0.25))], 2)
            out["portfolio_moic_p75"] = round(
                sorted_m[min(n - 1, int(n * 0.75))], 2)
    except Exception:  # noqa: BLE001
        pass

    # ── Surprise synthesis: pick the most striking aggregate ────
    # Priority order: HRRP $ exposure → covenant-tripped count →
    # health-band cluster → readiness affirmation.
    syn = ""
    if out["n_hrrp_exposed"] >= 2:
        syn = (
            f"{out['n_hrrp_exposed']} portfolio hospitals carry CMS "
            f"readmission penalties: combined ~"
            f"${out['hrrp_exposure_mm']:.2f}M EBITDA at risk this fiscal "
            f"year. Discount the bid book accordingly."
        )
    else:
        tripped = sum(
            1 for d in rows
            if _safe_status_str(d.get("covenant_status")).upper() == "TRIPPED"
        )
        if tripped >= 1:
            syn = (
                f"{tripped} deal{'s' if tripped != 1 else ''} have "
                f"TRIPPED covenants in the latest snapshot. Lender "
                f"calls land first. Review the watchlist before the "
                f"morning standup."
            )
        elif (out["band_counts"]["poor"] + out["band_counts"]["fair"]
              >= max(2, len(rows) // 3)):
            n_below = (out["band_counts"]["poor"]
                       + out["band_counts"]["fair"])
            syn = (
                f"{n_below} of {len(rows)} deals scored fair-or-poor "
                f"on health. The portfolio's middle is widening; "
                f"prioritize ops time on the bottom-quartile names."
            )
        elif out["portfolio_moic_median"] is not None:
            syn = (
                f"Predicted exit MOIC across the portfolio: "
                f"{out['portfolio_moic_median']:.2f}x median, benchmarked "
                f"against an illustrative deal corpus: {out['n_deals']} "
                f"deals track inside the modeled band."
            )
        else:
            syn = (
                f"Portfolio of {out['n_deals']} deals: "
                f"{out['band_counts']['great']} great, "
                f"{out['band_counts']['good']} good. Quiet morning. "
                f"Use it to chase the long-tail diligence asks."
            )
    out["headline_synthesis"] = syn

    return out


def _band_color(band: str) -> str:
    """Map health bands to the visual palette for the mosaic."""
    return {
        "great": "#3F7D4D",
        "good":  "#2C5C84",
        "fair":  "#B7791F",
        "poor":  "#A53A2D",
    }.get(band or "unknown", "#8A92A0")


def _format_money_compact(mm: float) -> str:
    """`$1,840M` → `$1.84B`; `$320M` → `$320M`. Compact for the hero."""
    if mm is None:
        return "—"
    try:
        v = float(mm)
    except (TypeError, ValueError):
        return "—"
    if v >= 1000:
        return f"${v/1000:.2f}B"
    if v >= 1:
        return f"${v:.0f}M"
    return f"${v*1000:.0f}K"


def _render_portfolio_pulse_hero(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """The wow-moment hero card. Sits at the very top of the
    dashboard and synthesizes:

      • Total deals + total EV (sum across portfolio profiles)
      • Average health + a per-deal mosaic (one colored tile per deal)
      • The most striking aggregate signal (HRRP $ exposure, covenant
        cluster, health-band cluster, or predicted MOIC)
      • Predicted portfolio-level exit MOIC distribution

    Designed so a partner who has never opened the tool sees a
    single screen that explains: how big the book is, how it's
    doing, and what to worry about — without clicking anywhere.
    """
    from ._chartis_kit import ck_fmt_number, ck_provenance_tooltip

    pulse = _portfolio_pulse_inputs(db_path, deals=deals)
    if pulse["n_deals"] == 0:
        return ""

    n = pulse["n_deals"]
    total_ev = _format_money_compact(pulse["total_ev_mm"])
    avg_health = (f"{int(round(pulse['avg_health']))}"
                  if pulse["avg_health"] is not None else "—")
    bands = pulse["band_counts"]

    # ── Mosaic: one colored square per deal ─────────────────────
    # Sorted high-to-low so the mosaic reads as a gradient — visual
    # cue for portfolio shape at a glance. Hover/focus scale lives in
    # the .dash-mosaic CSS (keyboard reachable); the tile color is the
    # only per-tile inline property because it is data-driven.
    tiles = sorted(
        pulse["deal_tiles"],
        key=lambda t: (t.get("score") or -1),
        reverse=True,
    )
    tile_html: List[str] = []
    for t in tiles[:80]:  # cap at 80 to keep DOM bounded
        c = _band_color(t.get("band") or "")
        deal_id = _html.escape(t.get("deal_id") or "")
        name = _html.escape(t.get("name") or "")
        score = t.get("score")
        score_str = f"{score}" if isinstance(score, (int, float)) else "—"
        tile_html.append(
            f'<a href="/deal/{deal_id}" '
            f'title="{name} · health {score_str}" '
            f'aria-label="{name}, health {score_str}" '
            f'style="background:{c};"></a>'
        )
    mosaic = (
        '<div class="dash-mosaic">'
        + "".join(tile_html)
        + '</div>'
    )

    # ── MOIC strip ──────────────────────────────────────────────
    moic_med = pulse["portfolio_moic_median"]
    moic_p25 = pulse["portfolio_moic_p25"]
    moic_p75 = pulse["portfolio_moic_p75"]
    moic_strip = ""
    if moic_med is not None:
        bar = _moic_range_bar(moic_p25, moic_med, moic_p75,
                              width=300, height=22)
        moic_value = ck_provenance_tooltip(
            "Predicted exit MOIC",
            f"{moic_med:.2f}x",
            explainer=(
                "Median of the per-deal predicted MOIC medians, each "
                "benchmarked against comparable realized deals in an "
                "illustrative corpus. Directional context for the "
                "morning read — not a valuation."
            ),
            inject_css=False,  # tooltip CSS injected by the stat tiles
        )
        moic_strip = (
            '<div class="dash-hero-moic">'
            '<p class="lab">'
            'Predicted exit MOIC<br/>(illustrative corpus)</p>'
            f'<div class="big">{moic_value}</div>'
            f'<div class="panel">{bar}</div>'
            f'<p class="pct">'
            f'p25 {moic_p25:.2f}x · p75 {moic_p75:.2f}x'
            f'</p></div>'
        )

    # ── Band-mosaic legend ──────────────────────────────────────
    # Swatch colors come from _band_color — the same data-driven map
    # the mosaic tiles use, so legend and tiles can never drift.
    legend_chip = (
        lambda band, label, n: (
            f'<span class="chip">'
            f'<span class="sw" style="background:{_band_color(band)};">'
            f'</span>'
            f'{label} <strong>{n}</strong></span>'
        )
    )
    legend = (
        '<div class="dash-hero-legend">'
        + legend_chip("great", "great", bands["great"])
        + legend_chip("good", "good", bands["good"])
        + legend_chip("fair", "fair", bands["fair"])
        + legend_chip("poor", "poor", bands["poor"])
        + '</div>'
    )

    # ── Stat tiles — each big number carries an "explain this" hover
    def _stat(big: str, small: str) -> str:
        return (
            '<div class="dash-hero-stat">'
            f'<div class="v">{big}</div>'
            f'<p class="l">{small}</p>'
            '</div>'
        )

    ev_value = ck_provenance_tooltip(
        "Total EV",
        total_ev,
        explainer=(
            "Sum across active deals: profile-declared EV where the "
            "deal was registered with one, HCRIS net-patient-revenue "
            "proxy otherwise. Directional sizing, not a valuation."
        ),
    )
    health_value = ck_provenance_tooltip(
        "Portfolio health",
        avg_health,
        explainer=(
            "Average composite health score (0-100 scale) across "
            "every scored deal. Components: covenant posture, open "
            "alerts, deadline slippage, snapshot freshness."
        ),
        inject_css=False,
    )
    stats = (
        '<div class="dash-hero-stats">'
        + _stat(ck_fmt_number(n), "deals")
        + _stat(ev_value, "total EV")
        + _stat(health_value, "portfolio health · avg /100")
        + '</div>'
    )

    # ── The synthesis line — the surprise the partner didn't ask for
    syn_text = _html.escape(pulse["headline_synthesis"])
    synthesis = (
        '<div class="dash-hero-syn">'
        '<p class="eb">The synthesis you\'d miss</p>'
        f'<p class="tx">{syn_text}</p>'
        '</div>'
    )

    # ── Live indicator + label row ──────────────────────────────
    # <header>/<h2> so the hero joins the page's heading outline the
    # same way every section_card title does.
    label_row = (
        '<header class="dash-hero-top">'
        '<h2 class="dash-hero-label">Portfolio pulse</h2>'
        '<span class="dash-hero-live">'
        '<span class="wc-pulse-dot"></span> live</span>'
        '</header>'
    )

    # Navy panel per the kit hero idiom (ck_search_hero); all styling
    # lives in the .dash-hero block of _DASH_CSS, keyframes included.
    return (
        '<section class="dash-hero" id="dash-hero">'
        + label_row
        + stats
        + '<p class="dash-hero-sub">'
        'Deals (sorted by health, hover for name)</p>'
        + mosaic
        + legend
        + moic_strip
        + synthesis
        + '</section>'
    )


def _render_headline_insight_section(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """One-glance insight card — the "wow" that justifies the morning
    visit. Rendered immediately after the header, before every other
    section, so it's the first thing a partner sees."""
    all_ins = _all_insights(db_path, deals=deals)
    ins = all_ins[0] if all_ins else None
    if ins is None:
        return ""

    # Tone → .dash-insight-* modifier (kit severity tokens drive the
    # left frame + dot; see _DASH_CSS). Replaces the platform-
    # dependent emoji glyphs and the legacy tint palette.
    tone = ins.get("tone", "neutral")
    if tone not in ("alert", "warn", "positive", "neutral"):
        tone = "neutral"
    href = ins.get("href") or "#"
    headline = _html.escape(ins.get("headline", ""))
    body = _html.escape(ins.get("body", ""))

    # "See all N" link only appears when there are more than the
    # top-1 — otherwise we're nudging the partner at empty. It is a
    # SIBLING of the headline anchor (never nested inside it — the
    # pre-facelift <a>-in-<a> markup fractured in every browser) and
    # sits above the stretched-link overlay via z-index.
    extras = len(all_ins) - 1
    see_all = ""
    if extras > 0:
        from ._chartis_kit import ck_arrow_link
        see_all = (
            f'<p class="dash-insight-more">'
            f'+ {extras} more signal{"s" if extras != 1 else ""} · '
            f'{ck_arrow_link("see all", "/insights")}'
            f'</p>'
        )
    # Whole-card click comes from the ::after stretched-link on the
    # headline anchor — valid HTML, keyboard focusable, no JS hover.
    # <article>/<h3> because the card is a self-contained story with
    # a real headline — screen readers get it in the outline.
    return (
        f'<article class="dash-insight dash-insight-{tone}">'
        f'<span class="dash-insight-dot" aria-hidden="true"></span>'
        f'<div class="dash-insight-main">'
        f'<p class="dash-insight-eyebrow">'
        f'Sharpest insight · today</p>'
        f'<h3 class="dash-insight-headline">'
        f'<a href="{_html.escape(href)}">{headline}</a></h3>'
        f'<p class="dash-insight-body">{body}</p>'
        f'{see_all}'
        f'</div>'
        f'<span class="dash-insight-arrow" aria-hidden="true">→</span>'
        f'</article>'
    )


def _fmt_event_ts(iso19: str) -> str:
    """Compact display form of an event timestamp.

    Today's events render as bare HH:MM:SS — inside a 24-hour feed
    the date is implied, and repeating it twenty times turns the
    column into noise. Yesterday's events keep the date (ISO order,
    date first, per house style). The full 19-char ISO string rides
    in the row's title attribute either way, so nothing is lost.
    """
    if len(iso19) < 19:
        return iso19
    today = datetime.now(timezone.utc).date().isoformat()
    if iso19[:10] == today:
        return iso19[11:19]
    return f"{iso19[:10]} {iso19[11:16]}"


def _render_since_yesterday_section(db_path: str) -> str:
    """One-screen "what changed since yesterday" roll-up.

    The differentiator vs. a static spreadsheet: a partner opens the
    tool and sees, without clicking, what happened while they were
    away. Alerts that fired overnight, data sources that refreshed,
    packets that ran, team activity — all chronological.
    """
    from . import _web_components as _wc
    from ._chartis_kit import ck_empty_state

    events = _since_yesterday_events(db_path, window_hours=24)

    if not events:
        body = ck_empty_state(
            "Nothing happened in the last 24 hours.",
            body=(
                "When alerts fire, data refreshes, or a teammate runs "
                "a packet, the summary shows up here — newest first."
            ),
            eyebrow="OVERNIGHT FEED",
            icon="◷",
        )
        return _wc.section_card("Since yesterday", body, pad=True)

    # Event-kind → mono tag. Rendered here (not in
    # _since_yesterday_events) so the event-dict contract consumed by
    # infra/morning_digest keeps its emoji ``icon`` field untouched.
    kind_tags = {
        "alert":   ("ALERT", "t-neg"),
        "refresh": ("DATA", "t-pos"),
        "packet":  ("RUN", "t-teal"),
        "audit":   ("TEAM", ""),
    }

    rows: List[str] = []
    for ev in events:
        ts_full = str(ev.get("at", ""))[:19]
        ts = _html.escape(_fmt_event_ts(ts_full))
        ts_title = _html.escape(ts_full)
        tag, tag_tone = kind_tags.get(
            str(ev.get("kind", "")), ("EVENT", ""))
        label = _html.escape(ev.get("label", ""))
        href = ev.get("href") or ""
        if href:
            label = (f'<a href="{_html.escape(href)}" '
                     f'class="dash-link">{label}</a>')

        # Inline ack + snooze controls for alert rows. Two
        # one-click options without leaving the dashboard:
        #   - Ack       (snooze_days=0, "I'm handling it")
        #   - Snooze 7d (snooze_days=7, "remind me in a week")
        # CSRF auto-injected by the shell's form-patching JS.
        # Both forms redirect back to /dashboard so the user's
        # scroll position + other events are preserved.
        ack_form = ""
        if ev.get("kind") == "alert":
            k = _html.escape(ev.get("alert_kind") or "")
            d = _html.escape(ev.get("alert_deal_id") or "")
            t = _html.escape(ev.get("alert_trigger_key") or "")
            if k and d and t:
                hidden = (
                    f'<input type="hidden" name="kind" value="{k}">'
                    f'<input type="hidden" name="deal_id" value="{d}">'
                    f'<input type="hidden" name="trigger_key" value="{t}">'
                    f'<input type="hidden" name="redirect" value="/dashboard">'
                )
                ack_form = (
                    f'<span class="dash-btn-row">'
                    # Ack now (snooze_days=0)
                    f'<form method="POST" action="/api/alerts/ack" '
                    f'class="dash-form-inline" '
                    f'onsubmit="event.target.querySelector(\'button\')'
                    f'.disabled=true;">'
                    f'{hidden}'
                    f'<input type="hidden" name="snooze_days" value="0">'
                    f'<button type="submit" title="Acknowledge · handled" '
                    f'class="dash-btn-ghost">Ack</button></form>'
                    # Snooze 7d (snooze_days=7) — partner says "I see
                    # this, but don't bother me about it for a week"
                    f'<form method="POST" action="/api/alerts/ack" '
                    f'class="dash-form-inline" '
                    f'onsubmit="event.target.querySelector(\'button\')'
                    f'.disabled=true;">'
                    f'{hidden}'
                    f'<input type="hidden" name="snooze_days" value="7">'
                    f'<button type="submit" '
                    f'title="Snooze for 7 days · remind me later" '
                    f'class="dash-btn-ghost">'
                    f'Snooze 7d</button></form>'
                    f'</span>'
                )

        rows.append(
            f'<li class="dash-list-row pad-sm">'
            f'<span class="dash-tag {tag_tone}">{tag}</span>'
            f'<span class="dash-evt-body">'
            f'{label}</span>'
            f'{ack_form}'
            f'<span class="dash-ts" title="{ts_title}">{ts}</span>'
            f'</li>'
        )
    # Sort hint — the list is always newest-first, but without this
    # caption a partner may wonder whether it's oldest-first or some
    # priority ordering. 20-event cap also surfaced so they know
    # older-than-top might exist off-page.
    hint = (
        f'<p class="dash-note sm">'
        f'{len(events)} event{"s" if len(events) != 1 else ""} · '
        f'newest first · last 24 hours'
        f'{" · older events in /audit" if len(events) >= 20 else ""}'
        f'</p>'
    )
    body = (
        hint
        + f'<ul class="dash-ul dash-evts">'
        f'{"".join(rows)}</ul>'
    )
    return _wc.section_card("Since yesterday", body, pad=True)


def _sparkline_svg(scores: List[int], *,
                   width: int = 80, height: int = 20,
                   stroke: str = "#155752") -> str:
    """Tiny inline SVG — one score per point, oldest-first.

    Returns empty string when there are <2 points (a single point
    isn't a trend). Scores are auto-normalized to the SVG viewport
    using the observed min/max of the series, so a deal bouncing
    between 70 and 75 uses the full chart height instead of looking
    flat against a 0-100 scale.

    Rendered as an inline SVG (no external request) so it lands
    with the page and stays cached with it.
    """
    if not scores or len(scores) < 2:
        return ""
    lo = min(scores)
    hi = max(scores)
    span = max(1, hi - lo)  # guard against flat line
    n = len(scores)
    pad_y = 2
    usable_h = height - 2 * pad_y

    points: List[str] = []
    for i, s in enumerate(scores):
        x = (i / (n - 1)) * width
        # Higher score should be higher on the chart — SVG y is
        # inverted, so normalized=0 is top, 1 is bottom; subtract
        # from 1 to flip.
        norm = (s - lo) / span
        y = pad_y + (1 - norm) * usable_h
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)

    # Last-point marker shows where the trend ended
    last_x = (n - 1) / (n - 1) * width
    last_norm = (scores[-1] - lo) / span
    last_y = pad_y + (1 - last_norm) * usable_h

    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'aria-label="Health score trend, {n} points" '
        f'class="dash-svg-mid">'
        f'<polyline fill="none" stroke="{stroke}" stroke-width="1.5" '
        f'stroke-linejoin="round" stroke-linecap="round" '
        f'points="{polyline}"/>'
        f'<circle cx="{last_x:.1f}" cy="{last_y:.1f}" r="2" '
        f'fill="{stroke}"/>'
        f'</svg>'
    )


def _render_saved_templates_section(db_path: str) -> str:
    """Partner's own named shortcuts — one click to relaunch an
    analysis with the same params they used last time.

    Empty → render a one-line pitch ("Save analyses you run often to
    relaunch them in one click") + a "Save current" form below the
    curated analyses table. Non-empty → show up to 8 cards sorted
    pinned-first, then by most recent run.
    """
    from . import _web_components as _wc
    try:
        from ..portfolio.store import PortfolioStore
        from ..analysis.saved_analyses import list_templates, resolved_href
        store = PortfolioStore(db_path)
        templates = list_templates(store, limit=8)
    except Exception:  # noqa: BLE001
        return ""

    if not templates:
        return ""

    rows: List[str] = []
    for t in templates:
        href = resolved_href(t)
        run_count = t.get("run_count") or 0
        last_run = t.get("last_run_at") or "never run"
        desc = t.get("description") or ""
        name = t.get("name") or "unnamed"
        pinned_chip = (
            '<span class="dash-tag t-teal ml">'
            'pinned</span>'
        ) if t.get("pinned") else ""
        # Clone button — copy this template's route + params under a
        # new name so a partner can tweak (e.g. swap the CCN) without
        # rebuilding from scratch. Major time-saver for repeated
        # diligence on similar deals.
        clone_form = (
            f'<form method="POST" action="/api/saved-analyses/'
            f'{t["id"]}/clone" class="dash-form-inline">'
            f'<input type="hidden" name="redirect" value="/dashboard">'
            f'<button type="submit" '
            f'title="Clone: duplicate this template under a new name '
            f'so you can tweak it (e.g. swap the CCN)" '
            f'class="dash-btn-icon">⎘</button>'
            f'</form>'
        )
        delete_form = (
            f'<form method="POST" action="/api/saved-analyses/'
            f'{t["id"]}/delete" class="dash-form-inline" '
            f'onsubmit="return confirm(\'Delete template: '
            f'{_html.escape(name)}?\');">'
            f'<input type="hidden" name="redirect" value="/dashboard">'
            f'<button type="submit" title="Delete template" '
            f'class="dash-btn-icon">×</button>'
            f'</form>'
        )
        rows.append(
            f'<li class="dash-list-row pad-x">'
            f'<a href="/api/saved-analyses/{t["id"]}/run" '
            f'class="dash-tpl-launch" '
            f'title="Click to launch"'
            f' onclick="if(!event.metaKey&&!event.ctrlKey){{'
            f'fetch(this.href,{{method:\'POST\',credentials:\'same-origin\'}})'
            f'.then(()=>window.location=\'{_html.escape(href)}\');'
            f'event.preventDefault();}}">'
            f'<span class="dash-link">'
            f'{_html.escape(name)}</span>{pinned_chip}'
            f'<div class="sub">'
            f'{_html.escape(desc) if desc else _html.escape(href)}'
            f' · ran {run_count}×</div>'
            f'</a>'
            f'{clone_form}{delete_form}'
            f'</li>'
        )
    body = (
        f'<ul class="dash-ul">'
        f'{"".join(rows)}</ul>'
        f'<p class="dash-note-after sm">'
        f'Click any template to launch. Run count updates automatically. '
        f'<a href="/api/docs" class="dash-link">API</a>'
        f'</p>'
    )
    return _wc.section_card(
        f"Your templates ({len(templates)})", body, pad=True,
    )


def _render_needs_attention_section(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Top-3 deals the risk scanner flagged as highest-priority.

    Complement to "Pinned deals" — Pinned shows deals the partner
    has *explicitly* starred; this card shows deals the TOOL has
    auto-flagged. A deal covenant-tripping overnight that the
    partner hasn't starred still surfaces here.

    The ranking uses the same `_priority_rank()` the risk-scan
    page uses, so the top item here is always the top row on
    /portfolio/risk-scan — consistent answers across surfaces.
    """
    from . import _web_components as _wc
    try:
        from .portfolio_risk_scan_page import _priority_rank
    except Exception:  # noqa: BLE001
        return ""

    if deals is None:
        try:
            from .portfolio_risk_scan_page import _gather_per_deal
            deals = _gather_per_deal(db_path)
        except Exception:  # noqa: BLE001
            return ""

    if not deals:
        return ""  # no deals → no card (empty state covered elsewhere)

    # Filter to deals with ANY actionable signal — priority > 0
    # means at least one of the five risk factors is non-neutral.
    scored = [(d, _priority_rank(d)) for d in deals]
    scored = [(d, r) for d, r in scored if r > 0]
    if not scored:
        # Everything is healthy — the kit's affirmative "all clear"
        # band instead of a bare green paragraph.
        from ._chartis_kit import ck_affirm_empty
        return _wc.section_card(
            "Needs attention today",
            ck_affirm_empty(
                headline="Everything looks healthy.",
                body=(
                    "No deals are flagging covenant, alert, or "
                    "deadline risks right now. A quiet triage is a "
                    "good morning to work the pipeline."
                ),
                cta_text="Open the pipeline",
                cta_href="/pipeline",
            ),
        )

    scored.sort(key=lambda t: t[1], reverse=True)
    top = scored[:3]

    # One chip row per flagged deal — same visual language as the
    # risk-scan page so the partner doesn't have to translate.
    rows: List[str] = []
    for d, priority in top:
        # Build a compact "why" string — which factors are firing.
        reasons: List[str] = []
        cov = _safe_status_str(d.get("covenant_status")).upper()
        if cov == "TRIPPED":
            reasons.append(
                '<span class="dash-neg-strong">covenant TRIPPED</span>')
        elif cov == "TIGHT":
            reasons.append(
                '<span class="dash-warn">covenant TIGHT</span>')
        if (d.get("overdue_deadlines") or 0) > 0:
            reasons.append(
                f'<span class="dash-neg">'
                f'{d["overdue_deadlines"]} overdue '
                f'deadline{"s" if d["overdue_deadlines"] != 1 else ""}</span>')
        if (d.get("alerts") or 0) > 0:
            reasons.append(
                f'<span class="dash-warn">'
                f'{d["alerts"]} open alert{"s" if d["alerts"] != 1 else ""}</span>')
        score = d.get("score")
        if isinstance(score, int) and score < 60:
            reasons.append(
                f'<span class="dash-warn">'
                f'health {score}</span>')
        if d.get("snap_age_days") is not None and d["snap_age_days"] > 30:
            reasons.append(
                f'<span class="dash-dim">'
                f'snapshot {d["snap_age_days"]}d stale</span>')

        rows.append(
            f'<li class="dash-list-row pad-lg">'
            f'<span class="dash-id dash-static dash-id-col">'
            f'{_html.escape(d["deal_id"])}</span>'
            f'<a href="/deal/{_html.escape(d["deal_id"])}" '
            f'class="dash-link dash-grow">'
            f'{_html.escape(d["name"])}</a>'
            f'<span class="dash-reasons">'
            f'{" · ".join(reasons) if reasons else ""}</span>'
            f'</li>'
        )
    more_link = (
        f'<p class="dash-note-after">'
        f'Showing top 3 of {len(scored)} deals with active risk flags. '
        f'See all on <a href="/portfolio/risk-scan" '
        f'class="dash-link">Portfolio risk scan</a>.'
        f'</p>'
        if len(scored) > 3 else
        f'<p class="dash-note-after">'
        f'Showing {len(scored)} deal{"s" if len(scored) != 1 else ""} '
        f'with active risk flags. See all on '
        f'<a href="/portfolio/risk-scan" '
        f'class="dash-link">Portfolio risk scan</a>.'
        f'</p>'
    )
    body = (
        f'<ul class="dash-ul">'
        f'{"".join(rows)}</ul>{more_link}'
    )
    return _wc.section_card(
        f"Needs attention today ({len(scored)})", body, pad=True,
    )


def _render_exposure_section(
    db_path: str,
    *, deals: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Sector + chain concentration at a glance.

    A partner with 12 deals should be able to read their portfolio
    composition without opening every deal. This card shows two
    breakdowns — sector and chain — as inline horizontal bars
    sorted by exposure.

    Skipped entirely on portfolios <= 1 deal (concentration math
    is meaningless on a single deal).
    """
    from . import _web_components as _wc
    from ._chartis_kit import ck_fmt_percent
    if deals is None:
        try:
            from .portfolio_risk_scan_page import _gather_per_deal
            deals = _gather_per_deal(db_path)
        except Exception:  # noqa: BLE001
            return ""
    if not deals or len(deals) <= 1:
        return ""

    sector_counts: Dict[str, int] = {}
    chain_counts: Dict[str, int] = {}
    for d in deals:
        s = (d.get("sector") or "").strip() or "—"
        sector_counts[s] = sector_counts.get(s, 0) + 1
        c = (d.get("chain") or "").strip()
        if c:
            chain_counts[c] = chain_counts.get(c, 0) + 1

    total = len(deals)

    def _bar_chart(items: Dict[str, int], *, top_n: int = 6,
                   tone: str = "teal") -> str:
        if not items:
            return '<p class="dash-empty-inline">No data yet.</p>'
        # Sort descending, cap at top_n, lump the rest into "Other"
        ranked = sorted(items.items(), key=lambda t: t[1], reverse=True)
        head = ranked[:top_n]
        tail = ranked[top_n:]
        if tail:
            head.append((f"Other ({len(tail)})", sum(v for _, v in tail)))

        rows: List[str] = []
        for label, count in head:
            pct = (count / total) * 100
            bar_w = int(round(pct))
            rows.append(
                f'<div class="dash-bar-row">'
                f'<span class="lab" '
                f'title="{_html.escape(label)}">'
                f'{_html.escape(label)}</span>'
                f'<div class="dash-bar-track">'
                f'<div class="dash-bar-fill {tone}" '
                f'style="width:{bar_w}%;"></div></div>'
                # precision=0 is deliberate here (house pct style is
                # 1dp, but "3 · 60%" whole-share chips are pinned by
                # tests/test_exposure_section.py and read cleaner on
                # a count-of-deals share).
                f'<span class="num">'
                f'{count} · '
                f'{ck_fmt_percent(count / total, precision=0)}'
                f'</span></div>'
            )
        return "".join(rows)

    sector_block = (
        '<h3 class="dash-subhead">By sector</h3>'
        + _bar_chart(sector_counts, tone="teal")
    )
    chain_block = (
        '<h3 class="dash-subhead mt">By chain '
        '<span class="qual">'
        '· deals where CMS POS knows the parent</span></h3>'
        + (_bar_chart(chain_counts, tone="warn") if chain_counts
           else '<p class="dash-empty-inline">'
                'No chain-affiliated deals: '
                'either all independent or POS data not loaded.</p>')
    )
    body = sector_block + chain_block
    return _wc.section_card(
        f"Portfolio composition ({total} active deals)", body, pad=True,
    )


def _moic_range_bar(p25: Optional[float],
                    median: Optional[float],
                    p75: Optional[float],
                    *, scale_max: float = 6.0,
                    width: int = 200, height: int = 18) -> str:
    """Inline SVG horizontal range bar showing p25 - median - p75
    of predicted realized MOIC.

    Visual: a thin gray track from 0 to scale_max, an indigo whisker
    spanning p25-p75, a navy dot at the median, optional dashed line
    at 1.0x (cost of capital) and 2.5x (the partner's "good deal" bar).
    """
    if median is None:
        return ""
    p25 = p25 if p25 is not None else median
    p75 = p75 if p75 is not None else median

    def _x(v: float) -> float:
        return min(width, max(0, (v / scale_max) * width))

    cost_x = _x(1.0)
    bar_x = _x(2.5)
    p25_x = _x(p25)
    p75_x = _x(p75)
    med_x = _x(median)

    # SVG attributes can't take var() portably in this codebase's
    # inline-SVG idiom, so the constants below are the kit chart
    # palette from rcm_mc/ui/README.md: gridline #E8E0D0 (track),
    # rule #BFB6A2 (cost-of-capital reference), positive #0a8a5f
    # (the 2.5x "good deal" bar), teal-deep #155752 (whisker/median).
    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'aria-label="MOIC range chart" '
        f'class="dash-svg-mid">'
        # Background track
        f'<rect x="0" y="{height/2 - 2}" width="{width}" height="4" '
        f'fill="#E8E0D0"/>'
        # 1.0x cost-of-capital reference line
        f'<line x1="{cost_x}" y1="2" x2="{cost_x}" y2="{height-2}" '
        f'stroke="#BFB6A2" stroke-width="1" stroke-dasharray="2,2"/>'
        # 2.5x "good deal" reference line
        f'<line x1="{bar_x}" y1="2" x2="{bar_x}" y2="{height-2}" '
        f'stroke="#0a8a5f" stroke-width="1" stroke-dasharray="2,2"/>'
        # p25-p75 whisker
        f'<rect x="{p25_x}" y="{height/2 - 4}" '
        f'width="{max(2, p75_x - p25_x)}" height="8" '
        f'fill="#155752" opacity="0.35" rx="2"/>'
        # Median dot
        f'<circle cx="{med_x}" cy="{height/2}" r="4" '
        f'fill="#155752" stroke="#fff" stroke-width="1.5"/>'
        f'</svg>'
    )


def _render_predicted_outcomes_section(
    db_path: str,
    *, deals_scan: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """For each pinned deal, predict an exit MOIC distribution by
    running it through the comparable-outcomes engine against the
    corpus of 600+ realized PE deals.

    The wow moment: a partner pinned DEAL_042 to track. Without
    asking for any analysis, the dashboard volunteers "your similar
    deals returned 2.3x median, 3.1x p75 at exit. Yours is on track."

    Compute is bounded — only runs for the partner's watchlisted
    deals (max 8) so the dashboard doesn't pay for 100 corpus
    scans on every render.
    """
    from . import _web_components as _wc
    from ._chartis_kit import ck_fmt_moic, ck_fmt_percent
    try:
        from ..portfolio.store import PortfolioStore
        from ..deals.watchlist import list_starred
        from ..data_public.deals_corpus import DealsCorpus
        from ..diligence.comparable_outcomes import benchmark_deal
        store = PortfolioStore(db_path)
        starred = list_starred(store)
    except Exception:  # noqa: BLE001
        return ""

    if not starred:
        return ""

    # Cap at 8 — bounded compute, room for partners with deep watchlists
    starred = starred[:8]

    # Best-effort corpus seed so the prediction has data to chew on
    try:
        corpus = DealsCorpus(db_path)
        try:
            corpus.seed(skip_if_populated=True)
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        return ""

    # Build a {deal_id → scan_row} map for sector + size lookup
    scan_by_id: Dict[str, Dict[str, Any]] = {}
    if deals_scan:
        scan_by_id = {d.get("deal_id", ""): d for d in deals_scan
                      if d.get("deal_id")}

    rows: List[str] = []
    any_prediction = False
    # Pull EV / payer-mix / sponsor from the deal's profile_json
    # in one query so each prediction can be deal-specific instead
    # of every starred deal getting the same hardcoded target.
    profiles_by_id: Dict[str, Dict[str, Any]] = {}
    try:
        import json as _json
        with store.connect() as con:
            for r in con.execute(
                "SELECT deal_id, profile_json FROM deals "
                "WHERE deal_id IN ({})".format(
                    ",".join("?" * len(starred))),
                starred,
            ).fetchall():
                try:
                    profiles_by_id[r["deal_id"]] = _json.loads(
                        r["profile_json"] or "{}")
                except (TypeError, _json.JSONDecodeError):
                    profiles_by_id[r["deal_id"]] = {}
    except Exception:  # noqa: BLE001
        pass

    # Cache HCRIS revenue → rough EV proxy (10x revenue is a typical
    # hospital multiple) when the profile doesn't carry an explicit EV.
    hcris_lookup = None
    try:
        from ..data.hcris import _get_latest_per_ccn
        hcris_lookup = _get_latest_per_ccn()
    except Exception:  # noqa: BLE001
        pass

    for deal_id in starred:
        scan_row = scan_by_id.get(deal_id, {})
        profile = profiles_by_id.get(deal_id, {})

        # Sector: prefer the scan row (already normalized), fall
        # back to profile, finally default to hospital.
        sector = (scan_row.get("sector")
                  or profile.get("sector")
                  or "hospital")

        # EV: explicit profile wins; HCRIS-derived proxy second;
        # None last (corpus matcher uses 0.5 neutral on None).
        ev_mm: Optional[float] = profile.get("ev_mm")
        if ev_mm is None and hcris_lookup is not None:
            try:
                if not hcris_lookup.empty:
                    h = hcris_lookup[hcris_lookup["ccn"] == deal_id]
                    if not h.empty:
                        rev = h.iloc[0].get("net_patient_revenue")
                        # Hospital EV / revenue typically 0.5-1.5x;
                        # use 1.0 as a middling proxy.
                        if rev and rev > 0:
                            ev_mm = float(rev) / 1_000_000.0
            except Exception:  # noqa: BLE001
                pass

        # Year: sponsor expects the analysis-year (default to current
        # so recency match favors recent comparables).
        year = profile.get("entry_year") or profile.get("year") or 2024

        # Buyer: helps the same-sponsor weight when the partner
        # tracks a sponsor's playbook
        buyer = (profile.get("sponsor") or profile.get("buyer") or "")

        # Payer mix: directly from profile if the deal was
        # registered with one, otherwise falls through to neutral.
        payer_mix = profile.get("payer_mix")

        target = {
            "sector": sector,
            "ev_mm": ev_mm,
            "year": year,
            "buyer": buyer,
            "payer_mix": payer_mix,
        }
        try:
            result = benchmark_deal(corpus, target, top_n=10)
        except Exception:  # noqa: BLE001
            continue
        outcome = result.get("outcome_distribution", {})
        moic = outcome.get("moic", {})
        median = moic.get("median")
        p25 = moic.get("p25")
        p75 = moic.get("p75")
        win_rate = outcome.get("win_rate_2_5x")
        n_comps = outcome.get("n_comparables", 0)

        if median is None or n_comps < 3:
            continue
        any_prediction = True

        bar = _moic_range_bar(p25, median, p75)
        # House numeric style: percentages carry 1 decimal place —
        # ck_fmt_percent takes the raw ratio and applies exactly that.
        win_pct = ck_fmt_percent(win_rate) if win_rate else "—"
        name = scan_row.get("name") or deal_id

        # "See why" deep-link — preserves the EXACT target profile
        # used for the prediction so the comparable-outcomes page
        # shows the same comparable set. Partner clicks the median,
        # gets the full ranked match list with reasons.
        import urllib.parse as _urlparse
        comp_qs = _urlparse.urlencode(
            {k: v for k, v in {
                "sector": target.get("sector"),
                "ev_mm": target.get("ev_mm"),
                "year": target.get("year"),
                "buyer": target.get("buyer"),
            }.items() if v not in (None, "")},
        )
        comp_href = f"/diligence/comparable-outcomes?{comp_qs}"

        rows.append(
            f'<li class="dash-list-row pad-lg">'
            f'<a href="/deal/{_html.escape(deal_id)}" '
            f'class="dash-deal-cell">'
            f'<div class="dash-link nm">'
            f'{_html.escape(name)}</div>'
            f'<div class="dash-id id">'
            f'{_html.escape(deal_id)}</div></a>'
            f'<div class="dash-static">{bar}</div>'
            f'<div class="dash-moic-cell">'
            f'<a href="{_html.escape(comp_href)}" '
            f'title="See the comparable deals that drove this prediction">'
            f'<span class="dash-moic-median">'
            f'{ck_fmt_moic(median)}</span>'
            f'<span class="dash-dim"> median · '
            f'p25 {ck_fmt_moic(p25)} · p75 {ck_fmt_moic(p75)} · '
            f'{win_pct} clear 2.5x</span>'
            f'</a></div>'
            f'</li>'
        )

    if not any_prediction:
        return ""

    # Mini-legend swatches repeat the _moic_range_bar constants —
    # kit chart palette (gridline / rule / positive / teal-deep).
    legend = (
        '<div class="dash-moic-legend">'
        '<span class="li">'
        '<svg width="20" height="10" viewBox="0 0 20 10">'
        '<rect x="0" y="3" width="20" height="4" fill="#E8E0D0"/>'
        '<line x1="3" y1="0" x2="3" y2="10" stroke="#BFB6A2" '
        'stroke-width="1" stroke-dasharray="2,2"/>'
        '<line x1="9" y1="0" x2="9" y2="10" stroke="#0a8a5f" '
        'stroke-width="1" stroke-dasharray="2,2"/>'
        '</svg>scale 0–6×</span>'
        '<span class="li">'
        '<span class="sw-range"></span>'
        'p25–p75 range</span>'
        '<span class="li">'
        '<span class="sw-median"></span>'
        'median predicted MOIC</span>'
        '<span class="dash-pos">— —</span>'
        '<span>2.5× "good deal" bar</span>'
        '</div>'
    )

    from ._chartis_kit import ck_provenance_tooltip
    corpus_note = ck_provenance_tooltip(
        "Illustrative corpus",
        "an illustrative corpus",
        explainer=(
            "Realized healthcare-PE deal outcomes assembled for "
            "benchmarking. Each match weighs sector, size, vintage, "
            "and sponsor. Directional context — not a valuation."
        ),
    )
    body = (
        '<p class="dash-note">'
        'Predicted exit MOIC for each watchlisted deal, computed '
        'live by matching against the realized deals in '
        f'{corpus_note} — directional, not a valuation.</p>'
        + legend
        + f'<ul class="dash-ul">'
        f'{"".join(rows)}</ul>'
    )
    return _wc.section_card(
        f"Predicted exit outcomes ({len(rows)})", body, pad=True,
    )


def _render_quiet_too_long_section(db_path: str) -> str:
    """Surface deals that haven't been touched in too long — the
    inverse of "Needs attention". A deal you watchlisted 6 months
    ago but never opened might be the one needing your fresh eyes
    more than the one pinging you daily.

    Source: ``audit_events`` table — the same audit log that
    powers Since-yesterday. Looks for the most recent view event
    targeting each watchlisted deal; ranks by oldest-first.
    """
    from . import _web_components as _wc
    try:
        from ..portfolio.store import PortfolioStore
        from ..deals.watchlist import list_starred
        store = PortfolioStore(db_path)
        starred = list_starred(store)
    except Exception:  # noqa: BLE001
        return ""

    if not starred:
        return ""

    # Pull last-view timestamps for each starred deal in one pass.
    # The audit table doesn't always exist on a fresh install, so
    # this whole branch is best-effort.
    last_view_by_deal: Dict[str, Optional[str]] = {d: None for d in starred}
    try:
        import sqlite3 as _sql
        with _sql.connect(db_path) as con:
            con.row_factory = _sql.Row
            # Check the table exists first (lazy-created elsewhere)
            tbl = con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name='audit_events'",
            ).fetchone()
            if tbl is None:
                return ""
            placeholders = ",".join("?" * len(starred))
            for row in con.execute(
                f"SELECT target, MAX(at) AS last_at FROM audit_events "
                f"WHERE target IN ({placeholders}) "
                f"GROUP BY target",
                starred,
            ).fetchall():
                last_view_by_deal[row["target"]] = row["last_at"]
    except Exception:  # noqa: BLE001
        return ""

    # Rank quiet-first: never-viewed comes first, then oldest, then
    # newest. Cap at 4 — this is a complement to Pinned, not a
    # replacement.
    from datetime import datetime as _dt, timezone as _tz
    now = _dt.now(_tz.utc)

    def _days_since(iso: Optional[str]) -> Optional[int]:
        if not iso:
            return None
        try:
            ts = _dt.fromisoformat(str(iso).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=_tz.utc)
            return (now - ts).days
        except (TypeError, ValueError):
            return None

    enriched: List[Dict[str, Any]] = []
    for did in starred:
        last = last_view_by_deal.get(did)
        days = _days_since(last)
        # Only surface deals that are actually "quiet" (unseen >14d,
        # or never viewed). A deal viewed yesterday isn't quiet.
        if days is not None and days < 14:
            continue
        enriched.append({
            "deal_id": did,
            "last_view_iso": last,
            "days_quiet": days,  # None = never viewed
        })

    if not enriched:
        return ""

    # Never-viewed first (sentinel: -1 sorts before all positive
    # day counts when reversed); then by days_quiet descending
    enriched.sort(
        key=lambda d: (-1 if d["days_quiet"] is None else d["days_quiet"]),
        reverse=True,
    )
    rows: List[str] = []
    for d in enriched[:4]:
        days = d["days_quiet"]
        # Chip tint pairs are the editorial quiet-severity trio; the
        # red pair (#EBD3CD / #A53A2D) is pinned by
        # tests/test_quiet_too_long.py and stays literal.
        if days is None:
            quiet_label = "never viewed"
            tone, fg = "#EBD3CD", "#A53A2D"
        elif days >= 60:
            quiet_label = f"{days}d quiet"
            tone, fg = "#EBD3CD", "#A53A2D"
        elif days >= 30:
            quiet_label = f"{days}d quiet"
            tone, fg = "#EFE2BC", "#B7791F"
        else:
            quiet_label = f"{days}d quiet"
            tone, fg = "#D6E1EB", "#2C5C84"
        rows.append(
            f'<li class="dash-list-row">'
            f'<a href="/deal/{_html.escape(d["deal_id"])}" '
            f'class="dash-link dash-id dash-quiet-link">'
            f'{_html.escape(d["deal_id"])}</a>'
            f'<span class="dash-quiet-chip" '
            f'style="background:{tone};color:{fg};">'
            f'{quiet_label}</span>'
            f'</li>'
        )
    body = (
        '<p class="dash-note">'
        'Watchlisted deals you haven\'t opened in a while. The '
        'one nobody is yelling at might need your fresh eyes more '
        'than the one pinging you daily.</p>'
        + f'<ul class="dash-ul">'
        f'{"".join(rows)}</ul>'
    )
    return _wc.section_card(
        f"Quiet too long ({len(enriched)})", body, pad=True,
    )


def _render_pinned_deals_section(db_path: str) -> str:
    """Morning glance at health scores for every deal the user has
    starred in the watchlist.

    Each deal renders as a compact card: score (color-coded by band),
    band label, top-contributing component (the single factor moving
    the score most). No card if the watchlist is empty — saves space
    for partners who haven't starred anything yet.

    Failures degrade silently: a deal that can't resolve (no snapshot,
    DB error during compute) is skipped rather than surfacing a
    traceback, since the section is a convenience view, not a
    critical workflow.
    """
    from . import _web_components as _wc
    from ._chartis_kit import ck_signal_badge
    try:
        from ..portfolio.store import PortfolioStore
        from ..deals.watchlist import list_starred
        from ..deals.health_score import compute_health
        store = PortfolioStore(db_path)
        starred = list_starred(store)
    except Exception:  # noqa: BLE001
        return ""  # no section at all — nothing to show

    if not starred:
        return ""

    # Band → (kit badge tone, sparkline stroke). Stroke hexes are the
    # kit's semantic severity constants (SVG attrs can't take var()).
    band_palette = {
        "excellent": ("positive", "#0a8a5f"),
        "good":      ("positive", "#0a8a5f"),
        "fair":      ("warning", "#b8732a"),
        "poor":      ("negative", "#b5321e"),
        "critical":  ("negative", "#b5321e"),
        "unknown":   ("neutral", "#7a8699"),
    }

    try:
        from ..deals.health_score import history_series
    except Exception:  # noqa: BLE001
        history_series = None  # type: ignore[assignment]

    cards: List[str] = []
    # Cap at 12 so a partner with a big watchlist doesn't blow the
    # dashboard height — Daily workflow has the full list.
    for deal_id in starred[:12]:
        try:
            h = compute_health(store, deal_id)
        except Exception:  # noqa: BLE001
            continue
        score = h.get("score")
        band = (h.get("band") or "unknown").lower()
        components = h.get("components") or []
        badge_tone, stroke = band_palette.get(
            band, band_palette["unknown"])

        # Pick the single top-impact component (most negative) — that's
        # the "why" a partner wants to see at a glance.
        def _abs_impact(c: Dict[str, Any]) -> float:
            try:
                return abs(float(c.get("impact") or 0))
            except (TypeError, ValueError):
                return 0.0
        top = max(components, key=_abs_impact) if components else None
        reason = (_html.escape(str(top.get("label") or ""))
                  if top else "")

        # 90-day score trend — pulled from deal_health_history.
        # Silent no-op when the history table doesn't exist yet
        # (fresh deploy) or the deal has <2 snapshots.
        spark = ""
        if history_series is not None:
            try:
                series = history_series(store, deal_id, days=90)
                scores = [s for _, s in series if s is not None]
                if scores:
                    # Color the spark the same as the score badge —
                    # a tight visual tie between the number and the
                    # line.
                    spark = _sparkline_svg(scores, stroke=stroke)
            except Exception:  # noqa: BLE001
                spark = ""

        score_str = str(score) if score is not None else "—"
        cards.append(
            f'<a href="/deal/{_html.escape(deal_id)}" '
            f'class="dash-pin-card">'
            f'<div class="dash-pin-head">'
            f'<span class="dash-id">'
            f'{_html.escape(deal_id)}</span>'
            f'{ck_signal_badge(score_str, tone=badge_tone)}'
            f'</div>'
            f'<div class="dash-pin-meta">'
            f'<span class="dash-pin-reason">{reason or "&nbsp;"}</span>'
            f'<span class="dash-static">{spark}</span>'
            f'</div>'
            f'</a>'
        )

    if not cards:
        return ""

    body = (
        f'<div class="dash-pin-grid">'
        f'{"".join(cards)}</div>'
    )
    return _wc.section_card(
        f"Pinned deals ({len(cards)})", body, pad=True,
    )


def _render_workflow_shortcuts_section(db_path: str) -> str:
    """One-click hops into the partner's daily workflow surfaces.

    Each row links to a route that already exists in server.py and
    shows a live badge count where one is informative — alerts to
    triage, deadlines that have slipped, deals on your watchlist,
    saved filters waiting to be re-run. Counts come from the same
    DB the surfaces themselves read, so the dashboard never lies.
    """
    from . import _web_components as _wc
    counts = _workflow_badge_counts(db_path)

    overdue_lvl = ("alert" if (counts.get("overdue_deadlines") or 0) > 0
                   else "neutral")
    alert_lvl = ("warn" if (counts.get("alerts") or 0) > 0 else "neutral")

    items = [
        ("Portfolio risk scan",       "/portfolio/risk-scan",
         "One-screen scan: which deals need attention today, "
         "sorted highest-priority first. Start here on Monday.",
         ""),
        ("Pipeline & saved searches", "/pipeline",
         "Resume a saved filter or pin a new one for the morning sweep.",
         _badge(counts.get("saved_searches"))),
        ("Watchlist",                 "/watchlist",
         "Hospitals you've starred: see freshness + recent flag changes.",
         _badge(counts.get("watchlist"))),
        ("Active alerts",             "/alerts",
         "Fired alerts awaiting ack/snooze; returning-badges show "
         "snooze expirations.",
         _badge(counts.get("alerts"), level=alert_lvl)),
        ("My inbox",                  "/my/me",
         "Per-owner pulse: deals you own, deadlines you're on the hook for.",
         _badge(counts.get("overdue_deadlines"), level=overdue_lvl)),
        ("Team activity",             "/team",
         "Recent comments, reassignments, and IC checklist progress.",
         ""),
        ("LP quarterly update",       "/lp-update",
         "Fund-scope partner-ready HTML over the last 90 days.",
         ""),
        ("Notifications",             "/settings/integrations",
         "Email + Slack channels for alert digests and refresh status.",
         ""),
        ("Scheduled refreshes",       "/data/refresh",
         "Per-source freshness + on-demand background refresh.",
         ""),
    ]
    rows: List[List[str]] = []
    for label, href, desc, badge in items:
        # NOTE: the `</a>{badge}` adjacency is regex-pinned by
        # tests/test_dashboard_badges.py — keep the chip immediately
        # after the closing anchor.
        rows.append([
            (f'<a href="{_html.escape(href)}" class="dash-link">'
             f'{_html.escape(label)}</a>{badge}'),
            f'<span class="dash-dim">{_html.escape(desc)}</span>',
        ])
    table = _wc.sortable_table(
        ["Open", "Why you'd come here today"], rows,
        id="dashboard-workflow",
        filterable=True, filter_placeholder="Filter workflow…",
    )
    return _wc.section_card("Daily workflow", table, pad=False)


def _render_recent_results_section(db_path: str) -> str:
    """Compose from in-process job queue (always safe) + optional run history."""
    from . import _web_components as _wc

    rows: List[List[str]] = []

    try:
        from ..infra.job_queue import get_default_registry
        reg = get_default_registry()
        jobs = reg.list_recent(n=5)
        for j in jobs:
            # Job status → the same CSS traffic-light dots the
            # freshness table uses (no colored ● text glyphs).
            badge = {
                "done": f'{_dot("ok")}done',
                "running": f'{_dot("stale")}running',
                "queued": f'{_dot("never")}queued',
                "failed": f'{_dot("cold")}failed',
            }.get(j.status, _html.escape(j.status))
            # Trim sub-second noise — ISO to the second is the house
            # display grain for a submitted-at column.
            ts = _html.escape((j.created_at or "")[:19])
            job_id = _html.escape(j.job_id or "")
            kind = _html.escape(j.kind or "")
            rows.append([
                f'<code>{job_id[:8]}</code>',
                kind,
                badge,
                f'<span class="dash-dim">{ts}</span>',
            ])
    except Exception:  # noqa: BLE001
        pass

    if not rows:
        from ._chartis_kit import ck_empty_state
        body = ck_empty_state(
            "No runs yet, first time here?",
            body=(
                "Try one of the curated analyses above — the Thesis "
                "Pipeline runs in ~170 ms on a fixture and walks you "
                "through 19 diligence steps end-to-end. Async jobs "
                "(data refresh, packet rebuild) appear here once "
                "submitted, with status badges that update "
                "automatically."
            ),
            eyebrow="RUN HISTORY",
            icon="▸",
            cta_label="Run the Thesis Pipeline",
            cta_href=(
                "/diligence/thesis-pipeline"
                "?dataset=hospital_04_mixed_payer"
            ),
        )
    else:
        body = _wc.sortable_table(
            ["Job ID", "Kind", "Status", "Submitted (UTC)"],
            rows, id="dashboard-recent-runs", hide_columns_sm=[3],
        )
    return _wc.section_card("Recent runs", body, pad=(not rows))


def _render_system_status_section(db_path: str,
                                  started_at: Optional[datetime]) -> str:
    # (label, level, value[, tooltip]) — optional 4th element renders as a
    # title attribute on the card for admin-level detail.
    items: List[tuple] = []

    # Version
    try:
        from .. import __version__
        items.append(("Version", "ok", str(__version__)))
    except Exception:  # noqa: BLE001
        items.append(("Version", "never", "unknown"))

    # Uptime
    if started_at is not None:
        up = datetime.now(timezone.utc) - started_at
        hrs = up.total_seconds() / 3600.0
        items.append(("Uptime", "ok", f"{hrs:.1f} h"))
    else:
        items.append(("Uptime", "never", "—"))

    # DB reachable + migrations applied
    try:
        from ..infra import migrations
        from ..portfolio.store import PortfolioStore
        store = PortfolioStore(db_path)
        with store.connect() as con:
            con.execute("SELECT 1").fetchone()
        items.append(("DB", "ok", "reachable"))
        applied = migrations.list_applied(store)
        from ..infra.migrations import _MIGRATIONS
        total = len(_MIGRATIONS)
        if len(applied) >= total:
            items.append(("Database schema", "ok", "up to date",
                          f"{len(applied)}/{total} migrations applied"))
        else:
            items.append(("Database schema", "stale", "update pending",
                          f"{len(applied)}/{total} migrations applied"))
    except Exception as exc:  # noqa: BLE001
        items.append(("DB", "cold", f"error: {type(exc).__name__}"))

    # Job queue worker
    try:
        from ..infra.job_queue import get_default_registry
        reg = get_default_registry()
        if reg._worker_started.is_set():
            items.append(("Job worker", "ok", "running"))
        else:
            items.append(("Job worker", "stale", "idle (lazy-start)"))
    except Exception:  # noqa: BLE001
        items.append(("Job worker", "cold", "unavailable"))

    # PHI posture
    phi_mode = (os.environ.get("RCM_MC_PHI_MODE") or "unset").lower()
    phi_level = {"disallowed": "ok", "restricted": "stale",
                 "unset": "never"}.get(phi_mode, "never")
    items.append(("PHI mode", phi_level, phi_mode))

    from . import _web_components as _wc
    from ._chartis_kit import ck_kpi_block
    cards = []
    for item in items:
        label, level, value = item[0], item[1], item[2]
        tip = item[3] if len(item) > 3 else ""
        # Editorial KPI block; the traffic dot rides inside the value
        # slot (trusted server markup) and the admin detail that used
        # to hide in a title attribute renders as the visible sub line.
        cards.append(ck_kpi_block(
            label,
            (f'<span class="dash-status-val">'
             f'{_dot(level)}{_html.escape(value)}</span>'),
            sub=_html.escape(tip) if tip else None,
        ))
    body = (
        '<div class="ck-kpi-grid dash-status-grid">'
        + "".join(cards) + '</div>'
    )
    return _wc.section_card("System status", body)


def _render_data_freshness_section(db_path: str) -> str:
    from . import _web_components as _wc

    from ._chartis_kit import ck_empty_state

    try:
        from ..data.data_refresh import get_status
        from ..portfolio.store import PortfolioStore
        rows_data = get_status(PortfolioStore(db_path))
    except Exception as exc:  # noqa: BLE001
        return _wc.section_card(
            "Data freshness",
            ck_empty_state(
                "Status table unavailable.",
                body=(
                    f"({type(exc).__name__}) Run `rcm-mc data refresh` "
                    f"to populate the per-source status table, or "
                    f"trigger a refresh from the Data refresh panel."
                ),
                eyebrow="DATA ESTATE",
                icon="◌",
                cta_label="Open Data refresh",
                cta_href="/data/refresh",
                tone="warning",
            ),
        )

    if not rows_data:
        return _wc.section_card(
            "Data freshness",
            ck_empty_state(
                "No data sources registered yet.",
                body=(
                    "Run a data refresh via the `rcm-mc data refresh` "
                    "CLI or open the Data refresh panel and click a "
                    "Refresh button — per-source freshness lands here."
                ),
                eyebrow="DATA ESTATE",
                icon="◌",
                cta_label="Open Data refresh",
                cta_href="/data/refresh",
            ),
        )

    rows: List[List[str]] = []
    for r in rows_data:
        name = _html.escape(str(r.get("source_name", "—")))
        last = r.get("last_refreshed")
        level, label = _freshness_bucket(last)
        status = _html.escape(str(r.get("status", "—")))
        rows.append([
            name,
            f'{_dot(level)}{_html.escape(label)}',
            f'<span class="dash-dim">{status}</span>',
        ])
    table = _wc.sortable_table(
        ["Source", "Last refreshed", "Status"], rows,
        id="dashboard-freshness",
    )
    return _wc.section_card("Data freshness", table, pad=False)


# ── Public entry point ─────────────────────────────────────────────

def render_dashboard(db_path: str, *,
                     started_at: Optional[datetime] = None) -> str:
    """Render the private-app landing page.

    Args:
        db_path: SQLite path; used for DB reachability, migrations, runs,
                 data-freshness lookups.
        started_at: Process start time (UTC) for uptime display. Falls
                    back to "—" if None.

    Returns:
        Full HTML page (passes through `chartis_shell` for consistent
        chrome + PHI banner).
    """
    from ._chartis_kit import (
        chartis_shell, ck_editorial_head, ck_eyebrow, ck_fmt_number,
        ck_next_section,
    )
    from ._export_menu import export_menu
    from . import _web_components as _wc

    portfolio_exports = export_menu(
        "Download portfolio-scope exports",
        [
            ("Portfolio CSV",       "/api/export/portfolio.csv"),
            ("Data refresh panel",  "/data/refresh"),
            ("LP quarterly update", "/exports/lp-update?days=90"),
        ],
    )

    workflow_shortcuts = _render_workflow_shortcuts_section(db_path)

    # Compute the per-deal scan ONCE per dashboard render and thread
    # it through every section that needs it. Without this, three
    # separate sections (headline-insight, needs-attention, exposure)
    # each call _gather_per_deal independently, multiplying
    # compute_health and POS lookups by 3× on every page load.
    deals_scan: Optional[List[Dict[str, Any]]] = None
    try:
        from .portfolio_risk_scan_page import _gather_per_deal
        deals_scan = _gather_per_deal(db_path)
    except Exception:  # noqa: BLE001
        deals_scan = None

    # Mode-aware eyebrow — "PARTNER WORKSPACE" for the PE-fund view,
    # "CONSULTING WORKSPACE" for the Chartis commercial-diligence view.
    from ._workspace_mode import current_workspace_mode, CONSULTING
    _eyebrow = (
        "CONSULTING WORKSPACE · LANDING"
        if current_workspace_mode() == CONSULTING
        else "PARTNER WORKSPACE · LANDING"
    )

    # Real-count meta line for the masthead — deals from the scan
    # already in hand, alert/watchlist counts from the same best-
    # effort reader the Daily-workflow badges use. Every part is
    # optional so a fresh DB still renders a truthful strip.
    n_deals = len(deals_scan or [])
    badge_counts = _workflow_badge_counts(db_path)
    meta_parts = [
        f"{ck_fmt_number(n_deals)} DEAL{'S' if n_deals != 1 else ''}"
    ]
    n_alerts = badge_counts.get("alerts")
    if n_alerts is not None:
        meta_parts.append(
            f"{ck_fmt_number(n_alerts)} OPEN ALERT"
            f"{'S' if n_alerts != 1 else ''}")
    n_watch = badge_counts.get("watchlist")
    if n_watch is not None:
        meta_parts.append(f"{ck_fmt_number(n_watch)} WATCHLISTED")
    meta_parts.append("LIVE")

    header = ck_editorial_head(
        eyebrow=_eyebrow,
        title="Dashboard",
        meta=" · ".join(meta_parts),
        lede_italic_phrase="One screen, every morning:",
        lede_body=(
            "what changed overnight, which deals need attention, and "
            "what to run next — composed from the same live data "
            "every analysis surface reads."
        ),
    )
    # Discoverability hint for the command palette — kbd tags need to
    # render as HTML, which page_header's subtitle escapes, so emit
    # this as a standalone strip below the masthead.
    cmdk_hint = (
        '<div class="wc-cmdk-hint-bar dash-cmdk-hint">'
        'Tip: press '
        '<kbd>⌘K</kbd> '
        '(or <kbd>Ctrl-K</kbd>) '
        'anywhere on this page to open the command palette: '
        'jump to a deal, open any page, or launch an analysis.'
        '</div>'
    )

    # ── Compose in four editorial bands ─────────────────────────
    # Section order is unchanged from the single-column era; the
    # bands only add grouping rhythm + jump anchors. A band whose
    # every section rendered empty (fresh DB) is skipped entirely —
    # no orphaned eyebrows.
    def _band(band_id: str, label: str) -> str:
        return (
            f'<div class="dash-band" id="{band_id}">'
            f'{ck_eyebrow(label)}</div>'
        )

    morning_group = (
        _render_portfolio_pulse_hero(db_path, deals=deals_scan)
        + _render_headline_insight_section(db_path, deals=deals_scan)
        + _render_since_yesterday_section(db_path)
        + _render_needs_attention_section(db_path, deals=deals_scan)
    )
    shape_group = (
        _render_exposure_section(db_path, deals=deals_scan)
        + _render_pinned_deals_section(db_path)
        + _render_quiet_too_long_section(db_path)
        + _render_predicted_outcomes_section(db_path, deals_scan=deals_scan)
    )
    run_group = (
        _render_saved_templates_section(db_path)
        + _render_analyses_section()
        + workflow_shortcuts
    )
    platform_group = (
        _render_recent_results_section(db_path)
        + _render_system_status_section(db_path, started_at)
        + _render_data_freshness_section(db_path)
        + portfolio_exports
    )

    bands = [
        ("dash-morning", "This morning", morning_group),
        ("dash-shape", "Portfolio shape", shape_group),
        ("dash-run", "Run analyses", run_group),
        ("dash-platform", "Platform", platform_group),
    ]
    jump_row = (
        '<nav class="dash-jump" aria-label="Page sections">'
        + "".join(
            f'<a href="#{band_id}">{label}</a>'
            for band_id, label, group in bands if group
        )
        + '</nav>'
    )
    banded = "".join(
        _band(band_id, label) + group
        for band_id, label, group in bands if group
    )

    inner = (
        _DASH_CSS
        + header
        + cmdk_hint
        + jump_row
        + banded
        + ck_next_section(
            "Open the portfolio risk scan",
            "/portfolio/risk-scan",
            eyebrow="Up next",
            italic_word="risk",
        )
    )
    # The Cmd-K palette is now injected globally by chartis_shell
    # via universal_palette_bundle() — every authenticated page on
    # the private web deployment has it. No dashboard-specific
    # wiring needed; removing the duplicate here keeps the DOM
    # free of two #wc-cmdk modals on the dashboard.
    # 2026-05-28 wave-B: ck_page_actions adds the Copy share link
    # affordance + Back-to-top jump for partners who deep-scroll
    # the dashboard. Idempotent JS guards prevent double-binding.
    # (spinner_js was dropped in the 2026-07 facelift: no
    # loading_spinner() is rendered anywhere on this page, so the
    # helper was dead JS on every landing-page load.)
    from ._chartis_kit import ck_page_actions
    body = (
        _wc.web_styles()
        + _wc.responsive_container(inner)
        + _wc.sortable_table_js()
        + ck_page_actions()
    )
    return chartis_shell(
        body, "Dashboard", active_nav="/dashboard",
        editorial_intro={
            "eyebrow": "MORNING BRIEFING",
            "headline": "The whole book, before coffee.",
            "italic_word": "whole",
            "body": (
                "Portfolio pulse, overnight changes, triage, and "
                "one-click analyses — every number on this page reads "
                "from the same live database the deal pages use."
            ),
        },
    )
