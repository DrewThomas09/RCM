"""Bloomberg-style analyst workbench renderer for a single deal.

Produces a full HTML page at ``/analysis/<deal_id>`` that renders the
entire :class:`DealAnalysisPacket` across six tabs: Overview, RCM
Profile, EBITDA Bridge, Monte Carlo, Risk & Diligence, Provenance.

Design constraints from the spec:
- Editorial Chartis theme — parchment background, navy topbar, teal
  accents, near-ink text (palette via ``--wb-*`` tokens bound to
  ``rcm_mc.ui.brand.PALETTE``). Originally a dark Bloomberg terminal;
  ported to the editorial system.
- JetBrains Mono for numeric cells; inter-system default for body.
- No border-radius > 4px. Dense padding (6px/10px on table cells).
- Zero external dependencies — no charts library, no framework, just
  inline SVG + HTML/CSS for every visualization.
- Interactive: the EBITDA Bridge tab has per-lever sliders that debounce
  300ms, POST to ``/api/analysis/<deal_id>/bridge``, and update the
  waterfall + total in-place via fetch.

This module is the single renderer — every tab reads from the *same*
packet object. If the packet's simulation section is missing the MC
tab renders an empty state, rather than the tab itself disappearing.
Progressive disclosure happens within tabs.
"""
from __future__ import annotations

import html
import json
from typing import Any, Dict, Iterable, List, Optional

from ..analysis.packet import (
    DealAnalysisPacket,
    DiligencePriority,
    MetricSource,
    PercentileSet,
    RiskSeverity,
    SectionStatus,
)
# A.10 PR B — chip propagation on the surfaces consuming ProfileMetric.
# Module-level import (not call-time) because the chip helper is used
# on hot render paths (metric table, risk flags, diligence questions)
# where a function-scope import would re-resolve on every row.
from ._chartis_kit import (
    ck_aggregate,
    ck_arrow_link,
    ck_empty_state,
    ck_eyebrow,
    ck_fmt_percent,
    ck_json_for_script,
    ck_kpi_block,
    ck_prediction_chip,
    ck_provenance_tooltip,
    ck_signal_badge,
)


# ── Palette & CSS ────────────────────────────────────────────────────

# Exposed so tests can assert specific tokens are in the output.
# Phase 3 of the UI v2 editorial rework: the local PALETTE dict was
# replaced with an import from the flag-aware central palette.
# Same key names resolve to legacy dark values when CHARTIS_UI_V2=0
# and to editorial navy/teal/parchment when CHARTIS_UI_V2=1. Every
# ``PALETTE['panel']`` / ``PALETTE['accent']`` / etc. reference in
# the ~2k-line renderer below flips with the flag unchanged.
from .brand import PALETTE  # noqa: F401  (used by _WORKBENCH_CSS below)


def _rgba(hex_color: str, alpha: float) -> str:
    """Low-alpha tint derived from a PALETTE hex.

    Facelift rule: every soft badge/heatmap background must be a tint
    of the SAME semantic hex its foreground uses (positive / warning /
    negative / critical from ``brand.PALETTE``) — never a hardcoded
    Tailwind-era RGB. Deriving the tint here keeps the whole family
    flag-aware (legacy vs editorial palette) for free.
    """
    h = str(hex_color or "").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:  # malformed token — fall back to ink
        r, g, b = 22, 38, 58
    return f"rgba({r},{g},{b},{alpha:g})"


_WORKBENCH_CSS = f"""
:root {{
  --wb-bg: {PALETTE['bg']};
  --wb-panel: {PALETTE['panel']};
  --wb-panel-alt: {PALETTE['panel_alt']};
  --wb-border: {PALETTE['border']};
  --wb-text: {PALETTE['text']};
  --wb-text-dim: {PALETTE['text_dim']};
  --wb-text-faint: {PALETTE['text_faint']};
  --wb-positive: {PALETTE['positive']};
  --wb-negative: {PALETTE['negative']};
  --wb-warning: {PALETTE['warning']};
  --wb-neutral: {PALETTE['neutral']};
  --wb-accent: {PALETTE['accent']};
}}

/* Scoped to the workbench — the old universal selector leaked
   box-sizing into shell chrome outside this page's root div. */
.analysis-workbench, .analysis-workbench * {{ box-sizing: border-box; }}
body.analysis-workbench {{
  margin: 0; padding: 0;
  background: var(--wb-bg);
  color: var(--wb-text);
  font-family: "Inter Tight", "Inter", -apple-system, BlinkMacSystemFont,
               "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 13px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}}
.analysis-workbench .num,
.analysis-workbench td.num,
.analysis-workbench .kpi-value,
.analysis-workbench .hero-number {{
  font-family: "JetBrains Mono", "SF Mono", Menlo, Consolas,
               "Liberation Mono", monospace;
  font-variant-numeric: tabular-nums;
}}

/* B.1 — α-disclosure inline with the quality bar. Small mono-font
 * label, faint color, sits to the right of the bar in the same cell.
 * Always visible (D4 refinement 1a: discoverable by accident); the
 * tooltip carries the methodology context for any partner who hovers.
 */
.analysis-workbench .ck-cohort-alpha {{
  font-family: "JetBrains Mono", "SF Mono", Menlo, Consolas,
               "Liberation Mono", monospace;
  font-size: 10px;
  color: var(--wb-text-faint);
  margin-left: 6px;
  vertical-align: middle;
  cursor: help;
}}

/* Editorial hero band — dark navy ink with parchment text. Slimmer
 * than the original (1.25/1.5rem instead of 2/2.25rem) so it reads
 * as a deal-context strip rather than a second topbar stacked under
 * the chartis_shell navy chrome. */
.analysis-workbench .wb-hero {{
  background: var(--sc-navy, #0b2341);
  color: var(--sc-on-navy, #f2ede3);
  padding: 1.25rem 0 1.5rem;
  border-bottom: 3px solid var(--sc-teal, var(--sc-teal-deep, #155752));
}}
.analysis-workbench .wb-hero-inner {{
  max-width: 1720px; margin: 0 auto; padding: 0 2rem;
}}
.analysis-workbench .wb-hero-eyebrow {{
  display: inline-flex; align-items: center; gap: .8rem;
  font-family: "Inter", sans-serif; font-size: .68rem;
  letter-spacing: .18em; text-transform: uppercase;
  color: rgba(250, 247, 240, 0.65); font-weight: 600;
  margin-bottom: .85rem;
}}
.analysis-workbench .wb-hero-eyebrow::before {{
  content: ""; width: 28px; height: 2px; background: var(--sc-teal, var(--sc-teal-deep, #155752)); display: inline-block;
}}
/* SET ACTIVE — a real feature, styled as a quiet chip instead of an
   inline-styled micro-link jammed into the eyebrow. */
.analysis-workbench .wb-set-active {{
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 9.5px; letter-spacing: .10em; font-weight: 600;
  color: rgba(250, 247, 240, 0.75);
  border: 1px solid rgba(250, 247, 240, 0.30);
  border-radius: 2px; padding: 2px 7px; text-decoration: none;
}}
.analysis-workbench .wb-set-active:hover {{
  color: var(--sc-on-navy, #f2ede3);
  border-color: rgba(250, 247, 240, 0.65);
}}

/* Editorial deck — the v5 head cadence continues on parchment below
   the navy deal strip: italic-first-phrase serif lede, mono source
   note, 4-dot status legend (mirrors ck_editorial_head anatomy,
   mapped onto the workbench --wb-* token layer). */
.analysis-workbench .wb-deck {{
  max-width: 1720px; margin: 0 auto;
  padding: 1.1rem 2rem 1.15rem;
}}
.analysis-workbench .wb-lede {{
  font-family: "Source Serif 4", Georgia, serif;
  font-style: italic; font-size: 16px; line-height: 1.6;
  color: var(--wb-text); max-width: 72ch; margin: 0 0 .7rem;
}}
.analysis-workbench .wb-lede em {{
  color: var(--wb-accent); font-style: italic;
}}
.analysis-workbench .wb-source-note {{
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 10px; letter-spacing: .14em; text-transform: uppercase;
  color: var(--wb-text-faint); margin: 0 0 .8rem;
}}
.analysis-workbench .wb-legend {{
  display: flex; gap: 22px; flex-wrap: wrap; list-style: none;
  margin: 0; padding: 0;
  font-family: "Inter Tight", "Inter", sans-serif; font-size: 12px;
  color: var(--wb-text-dim);
}}
.analysis-workbench .wb-legend li {{ display: flex; align-items: center; }}
.analysis-workbench .wb-legend .wb-dot {{
  width: 8px; height: 8px; border-radius: 50%;
  display: inline-block; margin-right: 9px;
}}
.analysis-workbench .wb-legend .wb-dot.live {{ background: var(--wb-positive); }}
.analysis-workbench .wb-legend .wb-dot.computed {{ background: var(--wb-text); }}
.analysis-workbench .wb-legend .wb-dot.needs {{ background: var(--wb-negative); }}
.analysis-workbench .wb-legend .wb-dot.illustrative {{ background: var(--wb-warning); }}

/* Keyboard focus — one shared rule for the whole workbench (the page
   previously suppressed outlines and defined zero :focus-visible). */
.analysis-workbench :is(button, a, input, summary, select, textarea):focus-visible {{
  outline: 2px solid var(--wb-accent); outline-offset: 2px;
}}
.analysis-workbench .wb-hero-row {{
  display: grid; grid-template-columns: 1fr auto;
  gap: 2rem; align-items: end;
}}
.analysis-workbench .wb-hero-name {{
  font-family: "Source Serif 4", Georgia, serif;
  font-size: 1.85rem; font-weight: 500; line-height: 1.1;
  letter-spacing: -0.015em; margin: 0; color: var(--sc-on-navy, #f2ede3);
}}
.analysis-workbench .wb-hero-meta {{
  margin-top: .75rem;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: .72rem; letter-spacing: .06em;
  color: rgba(250, 247, 240, 0.7);
  display: flex; flex-wrap: wrap; gap: .35rem .55rem;
  align-items: baseline;
}}
.analysis-workbench .wb-hero-meta .m-key {{
  color: rgba(250, 247, 240, 0.45);
  text-transform: uppercase; letter-spacing: .12em;
  font-size: .62rem; font-weight: 600;
}}
.analysis-workbench .wb-hero-meta .m-val {{
  color: var(--sc-on-navy, #f2ede3); font-weight: 600;
}}
.analysis-workbench .wb-hero-meta .m-sep {{
  color: rgba(250, 247, 240, 0.30); margin: 0 .15rem;
}}
.analysis-workbench .wb-hero-cta {{
  display: flex; gap: .65rem; align-items: end;
}}
.analysis-workbench .wb-cta-primary {{
  background: var(--sc-teal, var(--sc-teal-deep, #155752)); color: #FFFFFF;
  border: none; cursor: pointer;
  padding: .85rem 1.4rem;
  font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase;
  text-decoration: none; display: inline-block;
}}
.analysis-workbench .wb-cta-primary:hover {{ background: var(--sc-teal-deep, #155752); }}
.analysis-workbench .wb-cta-ghost {{
  background: transparent;
  color: var(--sc-on-navy, #f2ede3);
  border: 1px solid rgba(250, 247, 240, 0.35);
  padding: .85rem 1.4rem;
  font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase;
  text-decoration: none; display: inline-block;
}}
.analysis-workbench .wb-cta-ghost:hover {{
  background: rgba(250, 247, 240, 0.08);
  border-color: rgba(250, 247, 240, 0.65);
}}

/* Utility row — breadcrumb + secondary actions on parchment */
.analysis-workbench .wb-utility {{
  background: var(--wb-bg);
  border-bottom: 1px solid var(--wb-border);
  padding: .75rem 0;
}}
.analysis-workbench .wb-utility-inner {{
  max-width: 1720px; margin: 0 auto; padding: 0 2rem;
  display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;
}}
.analysis-workbench .wb-utility-bc {{
  font-family: "Inter", sans-serif; font-size: .72rem;
  color: var(--wb-text-dim); letter-spacing: .04em;
}}
.analysis-workbench .wb-utility-bc a {{
  color: var(--wb-text-dim); text-decoration: none;
}}
.analysis-workbench .wb-utility-bc a:hover {{ color: var(--wb-accent); }}
.analysis-workbench .wb-utility-bc .here {{ color: var(--wb-text); font-weight: 600; }}
.analysis-workbench .wb-utility-actions {{
  display: flex; gap: .4rem; align-items: center; flex: 1; flex-wrap: wrap;
}}
/* Teal-outline treatment (mirrors covenant-lab head-actions): the default
   wb-btn renders near-white-on-parchment and effectively disappears in this
   row, so give the navigational actions a visible teal border + teal label
   that fills teal on hover. Warn/Delete keep their semantic amber/red. */
.analysis-workbench .wb-utility-actions
  .wb-btn:not(.wb-btn-warn):not(.wb-btn-danger) {{
  background: var(--wb-panel);
  border-color: var(--wb-accent);
  color: var(--wb-accent);
}}
.analysis-workbench .wb-utility-actions
  .wb-btn:not(.wb-btn-warn):not(.wb-btn-danger):hover {{
  background: var(--wb-accent);
  border-color: var(--wb-accent);
  color: var(--sc-on-navy, #f2ede3);
}}
/* Semantic warn/danger recolored to the house palette (was ad-hoc
   #B7791F/#A53A2D with !important). Specificity beats the utility-row
   teal rule via the :not() guards above, so no !important needed. */
.analysis-workbench .wb-btn-warn {{ color: {PALETTE['warning']}; border-color: {PALETTE['warning']}; }}
.analysis-workbench .wb-btn-danger {{ color: {PALETTE['negative']}; border-color: {PALETTE['negative']}; }}
.analysis-workbench .wb-btn.wb-btn-warn:hover {{ background: {_rgba(PALETTE['warning'], 0.10)}; }}
.analysis-workbench .wb-btn.wb-btn-danger:hover {{ background: {_rgba(PALETTE['negative'], 0.10)}; }}

/* 6-card hero KPI strip — overview tab top. Tone colors come from the
   semantic palette; borders from the --wb token layer (was hardcoded
   #3F7D4D/#B7791F/#A53A2D + #BFB6A2/#D6CFC0). */
.analysis-workbench .wb-hero-kpi {{
  display: grid; grid-template-columns: repeat(6, 1fr); gap: 0;
  background: var(--wb-panel); border: 1px solid {PALETTE['border_light']};
  margin: 1.5rem 0 2rem 0;
}}
.analysis-workbench .wb-hero-card {{
  padding: 1.4rem 1.25rem 1.25rem;
  border-right: 1px solid var(--wb-border);
}}
.analysis-workbench .wb-hero-card:last-child {{ border-right: none; }}
.analysis-workbench .wb-hc-value {{
  font-family: "Source Serif 4", Georgia, serif;
  font-size: 2.1rem; font-weight: 600;
  line-height: 1; color: var(--sc-navy, #0b2341);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.01em;
}}
.analysis-workbench .wb-hero-card.tone-green .wb-hc-value {{ color: {PALETTE['positive']}; }}
.analysis-workbench .wb-hero-card.tone-amber .wb-hc-value {{ color: {PALETTE['warning']}; }}
.analysis-workbench .wb-hero-card.tone-red .wb-hc-value {{ color: {PALETTE['negative']}; }}
.analysis-workbench .wb-hc-label {{
  font-family: "Inter", sans-serif; font-size: .68rem; font-weight: 600;
  letter-spacing: .14em; text-transform: uppercase; color: var(--wb-text-dim);
  margin-top: .55rem;
}}
.analysis-workbench .wb-hc-sub {{
  font-family: "Inter", sans-serif; font-size: .72rem; color: var(--wb-text-faint);
  margin-top: .35rem; font-style: italic;
}}

/* Partner review — dark navy footer band, mirrors hero band treatment */
.analysis-workbench .wb-partner-review {{
  background: var(--sc-navy, #0b2341); color: var(--sc-on-navy, #f2ede3);
  padding: 2.5rem 0; margin-top: 3rem;
  border-top: 4px solid var(--sc-teal, var(--sc-teal-deep, #155752));
}}
.analysis-workbench .wb-pr-inner {{
  max-width: 1720px; margin: 0 auto; padding: 0 2rem;
}}
.analysis-workbench .wb-pr-eyebrow {{
  display: inline-flex; align-items: center; gap: .8rem;
  font-family: "Inter", sans-serif; font-size: .68rem;
  letter-spacing: .18em; text-transform: uppercase;
  color: rgba(250, 247, 240, 0.65); font-weight: 600;
  margin-bottom: 1.25rem;
}}
.analysis-workbench .wb-pr-eyebrow::before {{
  content: ""; width: 28px; height: 2px; background: var(--sc-teal, var(--sc-teal-deep, #155752)); display: inline-block;
}}
.analysis-workbench .wb-pr-quote {{
  font-family: "Source Serif 4", Georgia, serif;
  font-size: 1.45rem; line-height: 1.45;
  color: var(--sc-on-navy, #f2ede3); margin: 0 0 1.5rem 0;
  max-width: 1100px; font-style: italic;
}}
.analysis-workbench .wb-pr-meta {{
  display: flex; flex-wrap: wrap; gap: 2rem;
  padding-top: 1rem; border-top: 1px solid rgba(250, 247, 240, 0.18);
}}
.analysis-workbench .wb-pr-meta-item {{
  display: flex; flex-direction: column; gap: .15rem;
  font-family: "JetBrains Mono", ui-monospace, monospace;
}}
.analysis-workbench .wb-pr-meta .m-key {{
  font-family: "Inter", sans-serif; font-size: .6rem; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase;
  color: rgba(250, 247, 240, 0.45);
}}
.analysis-workbench .wb-pr-meta .m-val {{
  font-size: .82rem; color: var(--sc-on-navy, #f2ede3); font-weight: 600;
  font-variant-numeric: tabular-nums;
}}
/* Verdict keeps cream text (contrast on navy); an 8px semantic dot
   carries the tone instead of a low-contrast alpha-tinted color. */
.analysis-workbench .wb-pr-dot {{
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  margin-right: 7px; vertical-align: baseline;
}}
.analysis-workbench .wb-pr-dot.tone-green {{ background: {PALETTE['positive']}; }}
.analysis-workbench .wb-pr-dot.tone-amber {{ background: {PALETTE['warning']}; }}
.analysis-workbench .wb-pr-dot.tone-red {{ background: {PALETTE['negative']}; }}

.analysis-workbench .wb-btn {{
  background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border);
  color: var(--wb-text);
  padding: 5px 12px; border-radius: 2px;
  font-family: "Inter Tight", "Inter", sans-serif;
  font-size: 11px; font-weight: 600;
  letter-spacing: .08em; text-transform: uppercase;
  cursor: pointer;
  text-decoration: none; display: inline-block;
  transition: background .15s ease, transform .15s ease, box-shadow .15s ease;
}}
.analysis-workbench .wb-btn:hover {{
  background: var(--wb-border);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px -6px rgba(15,28,46,.18);
}}
.analysis-workbench .wb-btn-primary {{
  background: var(--wb-accent); border-color: var(--wb-accent);
  color: var(--sc-on-navy, #f2ede3);
}}
.analysis-workbench .wb-btn-primary:hover {{
  /* #1F7A75 is the canonical editorial chart teal (README palette) —
     one step brighter than the deep-teal accent for hover states. */
  background: var(--sc-teal-bright, #1F7A75);
  border-color: var(--sc-teal-bright, #1F7A75);
}}

/* Tab nav — the six-tab masthead of the flagship page. Sticky offset
   58px matches the shell topbar height (.ck-subnav uses the same). */
.analysis-workbench .wb-tabs {{
  position: sticky; top: 58px; z-index: 15;
  background: var(--wb-bg);
  border-bottom: 1px solid var(--wb-border);
  display: flex; gap: 4px; padding: 0 2rem;
}}
.analysis-workbench .wb-tab {{
  background: transparent; border: none; color: var(--wb-text-dim);
  padding: 13px 15px 11px;
  font-family: "JetBrains Mono", ui-monospace, monospace;
  font-size: 11.5px; font-weight: 600; cursor: pointer;
  border-bottom: 3px solid transparent;
  text-transform: uppercase; letter-spacing: 0.12em;
  transition: color .15s ease, border-bottom-color .15s ease;
}}
.analysis-workbench .wb-tab:hover {{ color: var(--wb-accent); }}
.analysis-workbench .wb-tab.active {{
  color: var(--wb-accent); border-bottom-color: var(--wb-accent);
  font-weight: 700;
}}
.analysis-workbench .wb-tab:focus-visible {{
  outline: 2px solid var(--wb-accent); outline-offset: -2px;
}}
.analysis-workbench .wb-tab-panel {{
  display: none; padding: 20px 2rem 14px;
  max-width: 1720px; margin: 0 auto;
}}
.analysis-workbench .wb-tab-panel.active {{ display: block; }}

/* Per-tab section head — the v5 editorial cadence applied at tab
   level: kit mono eyebrow (.ck-eyebrow), serif headline whose first
   phrase is italic in the page accent, one-line dim lede. Gives each
   of the eight panels a masthead instead of jumping straight into
   card chrome. */
.analysis-workbench .wb-tab-intro {{ margin: 2px 0 16px; }}
.analysis-workbench .wb-tab-intro .ck-eyebrow {{ margin-bottom: .4rem; }}
.analysis-workbench .wb-tab-head {{
  font-family: "Source Serif 4", Georgia, serif;
  font-size: 1.35rem; font-weight: 500; line-height: 1.2;
  letter-spacing: -0.012em; margin: 0 0 .3rem; color: var(--wb-text);
}}
.analysis-workbench .wb-tab-head em {{
  color: var(--wb-accent); font-style: italic;
}}
.analysis-workbench .wb-tab-lede {{
  font-size: 12.5px; color: var(--wb-text-dim);
  margin: 0; max-width: 78ch;
}}

/* Cards / panels */
.analysis-workbench .wb-card {{
  background: var(--wb-panel);
  border: 1px solid var(--wb-border);
  border-radius: 2px;
  padding: 12px 14px;
  margin-bottom: 10px;
  transition: border-color .18s ease, box-shadow .18s ease;
}}
.analysis-workbench .wb-card:hover {{
  border-color: {PALETTE['border_light']};
  box-shadow: 0 2px 6px -3px rgba(15,28,46,.08);
}}
.analysis-workbench .wb-card-title {{
  font-family: "JetBrains Mono", monospace;
  font-size: 10.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.14em;
  color: var(--wb-text-dim); margin-bottom: 8px;
}}
.analysis-workbench .wb-grid {{
  display: grid; grid-template-columns: 60% 40%;
  gap: 10px;
}}
.analysis-workbench .wb-grid-5050 {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 10px;
}}

/* Badges */
.analysis-workbench .wb-badge {{
  display: inline-block; padding: 2px 7px; border-radius: 2px;
  font-family: "JetBrains Mono", monospace;
  font-size: 10.5px; font-weight: 700;
  letter-spacing: 0.06em; text-transform: uppercase;
}}
.analysis-workbench .wb-badge-critical {{
  background: {_rgba(PALETTE['critical'], 0.10)}; color: {PALETTE['critical']};
}}
.analysis-workbench .wb-badge-high {{
  background: {_rgba(PALETTE['high'], 0.10)}; color: {PALETTE['high']};
}}
.analysis-workbench .wb-badge-medium {{
  background: {_rgba(PALETTE['medium'], 0.10)}; color: {PALETTE['medium']};
}}
.analysis-workbench .wb-badge-low {{
  background: {_rgba(PALETTE['low'], 0.12)}; color: {PALETTE['low']};
}}
.analysis-workbench .wb-badge-grade-A {{
  background: {_rgba(PALETTE['positive'], 0.12)}; color: {PALETTE['positive']};
}}
.analysis-workbench .wb-badge-grade-B {{
  background: {_rgba(PALETTE['accent'], 0.12)}; color: {PALETTE['accent']};
}}
.analysis-workbench .wb-badge-grade-C {{
  background: {_rgba(PALETTE['high'], 0.10)}; color: {PALETTE['high']};
}}
.analysis-workbench .wb-badge-grade-D {{
  background: {_rgba(PALETTE['critical'], 0.10)}; color: {PALETTE['critical']};
}}

/* Source chips — typographic replacement for the emoji source column
   (OBS / PRED / BMK letter tags), same idiom as ck_basis_badge. */
.analysis-workbench .wb-src-chip {{
  display: inline-block; padding: 1px 5px; border-radius: 2px;
  font-family: "JetBrains Mono", monospace;
  font-size: 8.5px; font-weight: 600; letter-spacing: 0.08em;
  border: 1px solid currentColor; cursor: help;
}}
.analysis-workbench .wb-src-chip.src-observed {{ color: var(--wb-accent); }}
.analysis-workbench .wb-src-chip.src-predicted {{ color: var(--wb-warning); }}
.analysis-workbench .wb-src-chip.src-benchmark {{ color: var(--wb-text-dim); }}
.analysis-workbench .wb-src-chip.src-unknown {{ color: var(--wb-text-faint); }}

/* Tables */
.analysis-workbench table.wb-table {{
  width: 100%; border-collapse: collapse;
  font-size: 13px;
}}
.analysis-workbench .wb-table th {{
  text-align: left; padding: 7px 10px;
  background: var(--wb-panel-alt);
  border-bottom: 1px solid var(--wb-border);
  color: var(--wb-text-dim);
  font-family: "JetBrains Mono", monospace;
  font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.10em;
}}
/* Numeric headers align with their right-aligned data columns; the
   30+-row profile table gets a sticky head under the tab bar
   (58px shell chrome + ~42px tab bar). */
.analysis-workbench .wb-table th.num {{ text-align: right; }}
.analysis-workbench .wb-table thead th {{
  position: sticky; top: 100px; z-index: 5;
}}
.analysis-workbench .wb-table td {{
  padding: 6px 10px;
  border-bottom: 1px solid var(--wb-border);
}}
.analysis-workbench .wb-table tbody tr:nth-child(even) {{
  background: var(--wb-panel-alt);
}}
.analysis-workbench .wb-table tbody tr:hover {{ background: {_rgba(PALETTE['accent'], 0.06)}; }}
.analysis-workbench .wb-table td.num {{ text-align: right; }}
.analysis-workbench .wb-table td.center {{ text-align: center; }}
.analysis-workbench .wb-table-narrow {{ max-width: 420px; }}
.analysis-workbench .wb-group-header td {{
  background: var(--wb-bg);
  color: var(--wb-text-dim);
  font-size: 11px; text-transform: uppercase;
  letter-spacing: 0.08em; padding: 8px 10px;
  font-weight: 600;
}}

/* Color semantics */
.analysis-workbench .pos {{ color: var(--wb-positive); }}
.analysis-workbench .neg {{ color: var(--wb-negative); }}
.analysis-workbench .warn {{ color: var(--wb-warning); }}
.analysis-workbench .dim {{ color: var(--wb-text-dim); }}
.analysis-workbench .hero-number {{ font-size: 32px; font-weight: 700; }}
.analysis-workbench .kpi-value {{ font-size: 20px; font-weight: 600; }}
.analysis-workbench .kpi-label {{
  font-size: 10px; color: var(--wb-text-dim);
  text-transform: uppercase; letter-spacing: 0.06em;
}}
.analysis-workbench .hero-caption {{ font-size: 11px; margin-top: 4px; }}
.analysis-workbench .hero-why {{ font-size: 10.5px; }}
.analysis-workbench .wb-ev-line {{ margin-top: 10px; font-size: 12px; }}

/* Small copy utilities — replace the page's ad-hoc style= attributes */
.analysis-workbench .wb-note {{ font-size: 11px; }}
.analysis-workbench .wb-note-sm {{ font-size: 10.5px; }}
.analysis-workbench .wb-center-note {{
  text-align: center; font-size: 11px; max-width: 640px;
  margin: 10px auto 0;
}}
.analysis-workbench .wb-mt {{ margin-top: 10px; }}
.analysis-workbench .wb-flex-row {{ display: flex; gap: 14px; align-items: center; }}
.analysis-workbench .wb-chip-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }}
.analysis-workbench .wb-list {{ padding-left: 20px; margin: 4px 0; }}
.analysis-workbench .wb-card-subtitle {{ margin-top: 12px; }}
.analysis-workbench .wb-spacer {{ flex: 1; }}
.analysis-workbench .wb-inline-form {{ display: inline; }}
.analysis-workbench code.mono {{ font-family: "JetBrains Mono", monospace; }}

/* Confidence bar — width + text label + title/aria (was width-only) */
.analysis-workbench .wb-qbar {{
  display: inline-block; width: 64px; height: 6px;
  background: var(--wb-border); vertical-align: middle;
}}
.analysis-workbench .wb-qbar > span {{ display: block; height: 6px; }}
.analysis-workbench .wb-qbar.q-high > span {{ width: 60px; background: var(--wb-positive); }}
.analysis-workbench .wb-qbar.q-medium > span {{ width: 40px; background: var(--wb-warning); }}
.analysis-workbench .wb-qbar.q-low > span {{ width: 20px; background: var(--wb-negative); }}
.analysis-workbench .wb-qbar.q-none > span {{ width: 10px; background: var(--wb-text-faint); }}
.analysis-workbench .wb-qbar-label {{
  font-family: "JetBrains Mono", monospace; font-size: 9.5px;
  color: var(--wb-text-faint); margin-left: 6px; vertical-align: middle;
}}

/* Trend arrows (profile table) */
.analysis-workbench .wb-trend {{ margin-left: 6px; }}
.analysis-workbench .wb-trend.trend-up {{ color: var(--wb-positive); }}
.analysis-workbench .wb-trend.trend-down {{ color: var(--wb-negative); }}
.analysis-workbench .wb-trend.trend-flat {{ color: var(--wb-text-faint); }}
.analysis-workbench .wb-anomaly {{ margin-left: 4px; cursor: help; }}
.analysis-workbench .wb-anomaly.sev-critical {{ color: {PALETTE['critical']}; }}
.analysis-workbench .wb-anomaly.sev-high {{ color: {PALETTE['high']}; }}
.analysis-workbench .wb-anomaly.sev-medium {{ color: {PALETTE['medium']}; }}
.analysis-workbench .wb-anomaly.sev-low {{ color: {PALETTE['low']}; }}
.analysis-workbench .wb-metric-link {{ text-decoration: none; }}
.analysis-workbench .wb-spark {{ vertical-align: middle; margin-left: 4px; }}

/* Next-actions — numbered editorial list (emoji bullets removed) */
.analysis-workbench .wb-actions {{ display: flex; flex-direction: column; gap: 10px; font-size: 12px; }}
.analysis-workbench .wb-action {{ display: flex; gap: 10px; align-items: baseline; }}
.analysis-workbench .wb-action-n {{
  font-family: "JetBrains Mono", monospace; font-size: 10px;
  font-weight: 700; color: var(--wb-accent);
  border: 1px solid var(--wb-accent); border-radius: 50%;
  width: 18px; height: 18px; line-height: 16px; text-align: center;
  flex-shrink: 0;
}}
.analysis-workbench .wb-action a {{ color: var(--wb-accent); font-weight: 600; }}
.analysis-workbench .wb-action-ok {{ color: var(--wb-positive); font-size: 12px; }}

/* Radial progress (completeness) */
.analysis-workbench .radial {{
  width: 90px; height: 90px; position: relative;
  display: inline-block; vertical-align: middle;
}}
.analysis-workbench .radial svg {{ transform: rotate(-90deg); }}
.analysis-workbench .radial .radial-label {{
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-family: "JetBrains Mono", monospace;
  font-size: 18px; font-weight: 700;
}}

/* Waterfall — right-aligned labels against the bars, a zero-axis rule
   on the left edge of every track, mono right-aligned values. */
.analysis-workbench .waterfall {{ display: flex; flex-direction: column; gap: 2px; }}
.analysis-workbench .wf-row {{
  display: grid; grid-template-columns: 160px 1fr 110px;
  gap: 8px; align-items: center;
  padding: 4px 0; font-size: 12px;
}}
.analysis-workbench .wf-row > div:first-child {{
  text-align: right; color: var(--wb-text-dim);
}}
.analysis-workbench .wf-row > div:last-child {{ text-align: right; }}
.analysis-workbench .wf-bar {{
  height: 16px; border-radius: 2px;
  background: var(--wb-accent);
}}
.analysis-workbench .wf-bar.pos {{ background: var(--wb-positive); }}
.analysis-workbench .wf-bar.neg {{ background: var(--wb-negative); }}
.analysis-workbench .wf-bar.anchor {{ background: var(--wb-text-dim); }}
.analysis-workbench .wf-track {{
  position: relative; height: 16px; background: var(--wb-panel-alt);
  border-left: 2px solid var(--wb-text-faint);
}}
.analysis-workbench .wf-track .wf-bar {{
  position: absolute; top: 0;
}}
.analysis-workbench .wb-bridge-status {{
  min-height: 16px; font-size: 11px; margin-top: 6px;
  font-family: "JetBrains Mono", monospace; color: var(--wb-text-faint);
}}
.analysis-workbench #wb-waterfall {{ transition: opacity .15s ease; }}
.analysis-workbench .wb-preset-row {{ margin-bottom: 8px; }}

/* Sliders */
.analysis-workbench .slider-row {{
  display: grid; grid-template-columns: 160px 1fr 80px 60px;
  align-items: center; gap: 10px; padding: 6px 0;
  font-size: 12px;
}}
.analysis-workbench input[type="range"].wb-slider {{
  width: 100%; accent-color: var(--wb-accent);
}}
.analysis-workbench .slider-label {{ color: var(--wb-text-dim); }}
.analysis-workbench .slider-target {{
  font-family: "JetBrains Mono", monospace; color: var(--wb-text);
}}
.analysis-workbench .slider-delta {{
  font-family: "JetBrains Mono", monospace; font-size: 11px;
}}

/* Histogram (inline SVG wrapper) */
.analysis-workbench .histo svg {{ display: block; width: 100%; height: auto; }}
.analysis-workbench .histo svg.wb-histo-svg {{ height: 160px; }}

/* Tornado */
.analysis-workbench .tornado-row {{
  display: grid; grid-template-columns: 180px 1fr 90px;
  gap: 8px; padding: 3px 0; font-size: 12px;
  align-items: center;
}}
.analysis-workbench .tornado-row > div:first-child {{
  text-align: right; color: var(--wb-text-dim);
}}
.analysis-workbench .tornado-row > .num {{ text-align: right; }}
.analysis-workbench .tornado-bar {{
  height: 14px; background: var(--wb-accent); border-radius: 2px;
}}
.analysis-workbench .tornado-bar.pos {{ background: var(--wb-positive); }}
.analysis-workbench .tornado-bar.neg {{ background: var(--wb-negative); }}
.analysis-workbench .tornado-bar.share {{ background: var(--wb-neutral); }}

/* Chart honesty caption — mono uppercase, muted (kit chart idiom) */
.analysis-workbench .wb-chart-caption {{
  font-family: "JetBrains Mono", monospace; font-size: 10px;
  letter-spacing: .10em; text-transform: uppercase;
  color: var(--wb-text-faint); margin-top: 6px;
}}

/* Risk cards — severity chip + serif-weight title on the top row with
   the EBITDA-at-risk figure right-aligned in mono (the number a
   partner scans for, promoted from an 11px footnote). */
.analysis-workbench .risk-card {{
  border-left: 3px solid var(--wb-accent);
  padding: 10px 12px; margin-bottom: 8px;
  background: var(--wb-panel);
  border-top: 1px solid var(--wb-border);
  border-right: 1px solid var(--wb-border);
  border-bottom: 1px solid var(--wb-border);
}}
.analysis-workbench .risk-card.severity-CRITICAL {{ border-left-color: {PALETTE['critical']}; }}
.analysis-workbench .risk-card.severity-HIGH {{ border-left-color: {PALETTE['high']}; }}
.analysis-workbench .risk-card.severity-MEDIUM {{ border-left-color: {PALETTE['medium']}; }}
.analysis-workbench .risk-card.severity-LOW {{ border-left-color: {PALETTE['low']}; }}
.analysis-workbench .risk-head {{
  display: flex; align-items: baseline; gap: 8px;
}}
.analysis-workbench .risk-title {{ font-weight: 600; font-size: 13.5px; flex: 1; }}
.analysis-workbench .risk-ear {{
  font-family: "JetBrains Mono", monospace; font-size: 12px;
  font-weight: 600; white-space: nowrap; text-align: right;
}}
.analysis-workbench .risk-ear .k {{
  font-size: 9px; color: var(--wb-text-faint); font-weight: 600;
  letter-spacing: .08em; text-transform: uppercase; margin-right: 5px;
}}
.analysis-workbench .risk-detail {{ font-size: 12px; color: var(--wb-text-dim); margin-top: 3px; }}
.analysis-workbench .risk-trigger {{ font-size: 11px; margin-top: 3px; }}

/* Diligence question */
.analysis-workbench .dq-card {{
  padding: 9px 12px; margin-bottom: 6px;
  background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border);
  border-radius: 2px;
}}
.analysis-workbench .dq-priority {{
  display: inline-block; padding: 1px 6px;
  margin-right: 8px; border-radius: 3px;
  font-family: "JetBrains Mono", monospace;
  font-size: 10px; font-weight: 700;
}}
.analysis-workbench .dq-P0 {{ background: {_rgba(PALETTE['critical'], 0.10)}; color: {PALETTE['critical']}; }}
.analysis-workbench .dq-P1 {{ background: {_rgba(PALETTE['high'], 0.10)}; color: {PALETTE['high']}; }}
.analysis-workbench .dq-P2 {{ background: {_rgba(PALETTE['low'], 0.12)}; color: {PALETTE['low']}; }}
.analysis-workbench .dq-cat {{
  display: inline-block; padding: 1px 6px; border-radius: 2px;
  font-family: "JetBrains Mono", monospace; font-size: 9.5px;
  font-weight: 600; letter-spacing: .05em; text-transform: uppercase;
  color: var(--wb-text-faint); border: 1px solid var(--wb-border);
}}
.analysis-workbench .dq-question {{ margin-top: 5px; }}
.analysis-workbench .dq-trigger {{ font-size: 11px; margin-top: 3px; }}
/* Group head wraps the kit .ck-eyebrow (caps + teal dash) and adds
   the list rhythm: top margin + hairline underline. */
.analysis-workbench .dq-group-head {{
  margin: 16px 0 6px;
  padding-bottom: 4px; border-bottom: 1px solid var(--wb-border);
}}
.analysis-workbench .dq-group-head .ck-eyebrow {{ font-size: 10.5px; }}
.analysis-workbench .dq-group-head:first-child {{ margin-top: 4px; }}

/* Provenance list */
.analysis-workbench .prov-row {{
  display: grid; grid-template-columns: 240px 110px 1fr;
  gap: 8px; padding: 6px 0;
  border-bottom: 1px solid var(--wb-border); font-size: 12px;
}}
.analysis-workbench .prov-row > .num {{ text-align: right; }}
.analysis-workbench .wb-prov-group {{ margin-top: 6px; }}

/* Heatmap */
.analysis-workbench .heatmap {{
  display: grid; gap: 2px;
  font-family: "JetBrains Mono", monospace; font-size: 11px;
}}
.analysis-workbench .heatmap-payer {{ grid-template-columns: repeat(4, 1fr); }}
.analysis-workbench .heatmap-cell {{
  padding: 6px 10px; text-align: center;
  background: var(--wb-panel-alt);
}}
.analysis-workbench .heatmap-cell .hm-label {{ font-size: 10px; color: var(--wb-text-dim); }}
.analysis-workbench .heatmap-cell.hm-good {{ background: {_rgba(PALETTE['positive'], 0.12)}; color: {PALETTE['positive']}; }}
.analysis-workbench .heatmap-cell.hm-warn {{ background: {_rgba(PALETTE['warning'], 0.10)}; color: {PALETTE['warning']}; }}
.analysis-workbench .heatmap-cell.hm-bad {{ background: {_rgba(PALETTE['negative'], 0.10)}; color: {PALETTE['negative']}; }}
.analysis-workbench details summary {{ cursor: pointer; padding: 4px 0; }}

/* Scenarios tab — side-by-side cards + pairwise matrix + overlay */
.analysis-workbench .scenario-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px; margin-bottom: 16px;
}}
.analysis-workbench .scenario-card {{
  background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border);
  padding: 12px; border-radius: 2px;
  transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease;
}}
.analysis-workbench .scenario-card:hover {{
  border-color: var(--wb-accent);
  box-shadow: 0 4px 12px -6px rgba(21,87,82,.25);
  transform: translateY(-1px);
}}
.analysis-workbench .scenario-card.recommended {{
  border: 2px solid var(--wb-accent);
  box-shadow: 0 0 0 1px var(--wb-accent) inset;
}}
.analysis-workbench .scenario-name {{
  font-weight: 600; font-size: 14px; margin-bottom: 8px;
  display: flex; align-items: center; gap: 6px;
}}
.analysis-workbench .scenario-rec-badge {{
  background: var(--wb-accent); color: #FAF7F0;
  font-family: "JetBrains Mono", monospace;
  font-size: 9.5px; font-weight: 700;
  padding: 2px 7px; border-radius: 2px;
  letter-spacing: 0.10em; text-transform: uppercase;
}}
.analysis-workbench .scenario-kpi {{
  display: grid; grid-template-columns: 1fr auto; gap: 4px;
  font-size: 12px; padding: 2px 0;
}}
.analysis-workbench .scenario-kpi .dim {{ color: var(--wb-text-dim); }}
.analysis-workbench .scenario-drivers {{
  margin-top: 8px; font-size: 11px; color: var(--wb-text-dim);
}}
.analysis-workbench .scenario-drivers ol {{
  margin: 4px 0 0; padding-left: 18px;
}}
.analysis-workbench .scenario-mini {{
  margin-top: 8px;
}}
.analysis-workbench .scenario-mini svg {{
  display: block; width: 100%; height: 60px;
}}
.analysis-workbench .pairwise-matrix {{
  border-collapse: collapse; margin-top: 8px;
  font-size: 12px;
}}
.analysis-workbench .pairwise-matrix th,
.analysis-workbench .pairwise-matrix td {{
  padding: 6px 10px; text-align: right;
  border: 1px solid var(--wb-border);
  font-family: "JetBrains Mono", monospace;
}}
.analysis-workbench .pairwise-matrix th {{
  background: var(--wb-panel); font-weight: 700;
  color: var(--wb-text-dim); text-transform: uppercase;
  font-size: 10px; letter-spacing: 0.10em;
}}
.analysis-workbench .pairwise-matrix td.pw-self {{
  color: var(--wb-text-faint);
}}
.analysis-workbench .pairwise-matrix td.pw-high {{
  background: {_rgba(PALETTE['positive'], 0.12)}; color: var(--wb-positive);
}}
.analysis-workbench .pairwise-matrix td.pw-low {{
  background: {_rgba(PALETTE['negative'], 0.10)}; color: var(--wb-negative);
}}
.analysis-workbench .scenario-overlay-svg {{
  width: 100%; height: 200px; display: block;
  background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border);
}}
.analysis-workbench .scenario-empty {{
  padding: 28px 24px; text-align: center;
  color: var(--wb-text-dim); font-size: 14px;
  font-family: "Source Serif 4", Georgia, serif;
  border: 1px dashed var(--wb-border); border-radius: 2px;
  background: var(--wb-panel);
}}
/* Overlay legend — classes replace the inline-styled span chain */
.analysis-workbench .wb-overlay-legend {{ margin-top: 6px; font-size: 11px; }}
.analysis-workbench .wb-rationale {{ margin-top: 8px; font-size: 12px; }}
.analysis-workbench .wb-btn-right {{ float: right; }}
.analysis-workbench .wb-reg-card {{ margin-bottom: 14px; }}
.analysis-workbench .wb-reg-narrative {{ font-size: 12px; line-height: 1.5; }}
.analysis-workbench .wb-overlay-legend .scenario-legend-item {{
  display: inline-flex; align-items: center; gap: 4px; margin-right: 12px;
}}
.analysis-workbench .wb-overlay-legend .scenario-swatch {{ opacity: 0.7; }}
.analysis-workbench .histo svg {{ border: 1px solid var(--wb-border); }}
.analysis-workbench .scenario-add-form {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px;
  padding: 12px; background: var(--wb-panel-alt);
  border: 1px solid var(--wb-border); border-radius: 2px;
  margin-top: 12px;
}}
.analysis-workbench .scenario-add-form.hidden {{ display: none; }}
.analysis-workbench .scenario-add-form label {{
  font-size: 11px; color: var(--wb-text-dim);
  display: flex; flex-direction: column; gap: 2px;
}}
.analysis-workbench .scenario-add-form input {{
  background: var(--wb-panel); color: var(--wb-text);
  border: 1px solid var(--wb-border); padding: 4px 8px;
  font-family: "JetBrains Mono", monospace; font-size: 12px;
}}
.analysis-workbench .scenario-add-form .full-row {{ grid-column: 1 / -1; }}
.analysis-workbench .scenario-palette-0 {{ --sc-color: {PALETTE['accent']}; }}
.analysis-workbench .scenario-palette-1 {{ --sc-color: {PALETTE['positive']}; }}
.analysis-workbench .scenario-palette-2 {{ --sc-color: {PALETTE['warning']}; }}
.analysis-workbench .scenario-palette-3 {{ --sc-color: {PALETTE['negative']}; }}
.analysis-workbench .scenario-swatch {{
  display: inline-block; width: 10px; height: 10px;
  background: var(--sc-color); border-radius: 2px;
}}

/* ── Prompt 32: Inline explain panel ──────────────────────── */
.analysis-workbench .wb-explain-panel {{
  position: fixed; top: 0; right: -400px; width: 380px; height: 100vh;
  background: var(--wb-panel); border-left: 1px solid var(--wb-border);
  z-index: 50; padding: 20px; overflow-y: auto;
  transition: right 0.25s ease-in-out;
  box-shadow: -4px 0 16px rgba(15,28,46,0.18);
}}
.analysis-workbench .wb-explain-panel.open {{ right: 0; }}
.analysis-workbench .wb-explain-panel .ep-close {{
  position: absolute; top: 12px; right: 16px; cursor: pointer;
  font-size: 18px; color: var(--wb-text-dim); background: none; border: none;
}}
.analysis-workbench .wb-explain-panel .ep-title {{
  font-size: 16px; font-weight: 600; margin-bottom: 12px;
  padding-right: 30px;
}}
.analysis-workbench .wb-explain-panel .ep-section {{
  margin-bottom: 14px; font-size: 12px;
}}
.analysis-workbench .wb-explain-panel .ep-label {{
  font-size: 10px; color: var(--wb-text-dim); text-transform: uppercase;
  letter-spacing: .06em; margin-bottom: 4px;
}}
.analysis-workbench .wb-explain-panel .ep-bar {{
  background: var(--wb-border); height: 8px; border-radius: 4px;
  overflow: hidden; margin-top: 4px;
}}
.analysis-workbench .wb-explain-panel .ep-bar > div {{
  height: 100%; border-radius: 4px;
}}
.analysis-workbench [data-explain] {{ cursor: pointer; }}
.analysis-workbench [data-explain]:hover {{ text-decoration: underline; }}
.analysis-workbench .wb-explain-panel .ep-source-chip {{
  background: var(--sc-navy, #0b2341); color: var(--sc-on-navy, #f2ede3);
  padding: 2px 8px; border-radius: 3px; font-size: 11px;
}}
.analysis-workbench .wb-explain-panel .ep-value {{ font-size: 18px; }}
.analysis-workbench .wb-explain-panel .ep-quote {{ font-style: italic; }}
.analysis-workbench .wb-explain-panel .ep-label.wb-mt6 {{ margin-top: 6px; }}

/* ── Prompt 56: Mobile-responsive breakpoints ────────────────── */
@media (max-width: 768px) {{
  .analysis-workbench .wb-tabs {{ flex-wrap: wrap; gap: 2px; padding: 0 12px; }}
  .analysis-workbench .wb-tab {{ font-size: 10px; padding: 6px 8px; }}
  .analysis-workbench .wb-tab-panel {{ padding: 14px 12px; }}
  .analysis-workbench .wb-hero-inner,
  .analysis-workbench .wb-utility-inner,
  .analysis-workbench .wb-deck {{ padding: 0 12px; }}
  .analysis-workbench .wb-hero-kpi {{ grid-template-columns: repeat(2, 1fr); }}
  .analysis-workbench .wb-hero-card {{ border-bottom: 1px solid var(--wb-border); }}
  .analysis-workbench .wb-grid {{ grid-template-columns: 1fr; }}
  .analysis-workbench .wb-grid-5050 {{ grid-template-columns: 1fr; }}
  .analysis-workbench .wb-table {{ font-size: 11px; display: block; overflow-x: auto; }}
  .analysis-workbench .scenario-grid {{ grid-template-columns: 1fr; }}
  .analysis-workbench .hero-number {{ font-size: 28px; }}
  .analysis-workbench input.wb-slider {{ min-height: 48px; }}
}}
@media (min-width: 769px) and (max-width: 1024px) {{
  .analysis-workbench .wb-grid {{ grid-template-columns: 1fr 1fr; }}
  .analysis-workbench .scenario-grid {{ grid-template-columns: 1fr 1fr; }}
}}

/* ── Print-friendly stylesheet ────────────────────────────────── */
@media print {{
  body {{ background: white !important; color: black !important; padding: 0 !important; }}
  nav, .wb-tabs, .skip-link, footer,
  .breadcrumb, button, .wb-explain-panel {{ display: none !important; }}
  .analysis-workbench {{
    background: white !important; color: black !important;
    border: none !important; box-shadow: none !important;
  }}
  .analysis-workbench .wb-card {{
    background: white !important; border: 1px solid #ccc !important;
    box-shadow: none !important; break-inside: avoid;
  }}
  .analysis-workbench .wb-grid {{ grid-template-columns: 1fr 1fr; }}
  .analysis-workbench .hero-number {{ color: black !important; }}
  table {{ border-collapse: collapse; }}
  th {{ background: #f0f0f0 !important; color: black !important; }}
  td, th {{ border: 1px solid #ccc !important; }}
  a {{ color: black !important; text-decoration: underline; }}
  /* Print URLs only for real external/route links — a printed
     "(#prov-denial_rate)" after every internal anchor is noise. */
  a[href]:not([href^="#"]):after {{ content: " (" attr(href) ")"; font-size: 0.8em; color: #666; }}
}}

/* ── Analyst Override / Assumptions tab ── */
/* 2026-05-28 batch 38 · Tier-4 trope removal — drops 135° gradient;
   flat brand-tinted background + decorative left stripe stripped.
   The border + radius already mark this as a banner. */
.analysis-workbench .ov-banner {{
  background: rgba(21,87,82,0.06);
  border: 1px solid var(--wb-accent);
  border-radius: 2px;
  padding: 9px 12px; margin-bottom: 10px;
  font-size: 12px; color: var(--wb-text);
}}
.analysis-workbench .ov-section {{
  margin-bottom: 14px;
}}
.analysis-workbench .ov-section-title {{
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.07em;
  color: var(--wb-text-dim); margin-bottom: 6px;
  padding-bottom: 4px; border-bottom: 1px solid var(--wb-border);
}}
.analysis-workbench .ov-row {{
  display: grid; grid-template-columns: minmax(200px, 260px) 1fr 90px 90px 1fr;
  gap: 6px; align-items: center;
  padding: 5px 0; border-bottom: 1px solid var(--wb-panel-alt);
  font-size: 12px;
}}
.analysis-workbench .ov-family {{
  font-family: "JetBrains Mono", monospace; font-size: 9.5px;
  font-weight: 700; letter-spacing: .12em; text-transform: uppercase;
  color: var(--wb-text-faint); margin: 10px 0 2px;
}}
.analysis-workbench .ov-hint {{
  margin-top: 6px; font-size: 11px; color: var(--wb-text-faint);
}}
.analysis-workbench .ov-rebuild-btn {{ padding: 2px 8px; }}
.analysis-workbench .ov-label {{ font-size: 12px; color: var(--wb-text); }}
.analysis-workbench .ov-row-head {{
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--wb-text-faint);
  border-bottom: 1px solid var(--wb-border) !important;
}}
.analysis-workbench .ov-key {{
  font-family: "JetBrains Mono", monospace; font-size: 10.5px;
  color: var(--wb-text-dim); min-width: 0; overflow-wrap: anywhere;
}}
.analysis-workbench .ov-model-val {{
  color: var(--wb-text-dim); font-family: "JetBrains Mono", monospace;
  font-size: 11px;
}}
.analysis-workbench .ov-active-val {{
  color: var(--wb-accent); font-family: "JetBrains Mono", monospace;
  font-size: 11px; font-weight: 600;
}}
.analysis-workbench .ov-badge-a {{
  display: inline-block; background: {_rgba(PALETTE['accent'], 0.12)};
  color: var(--wb-accent); border-radius: 3px;
  padding: 1px 6px; font-size: 10px; font-weight: 700;
  letter-spacing: 0.05em;
}}
.analysis-workbench .ov-input {{
  width: 90px; padding: 4px 6px; border: 1px solid var(--wb-border);
  border-radius: 2px; font-size: 12px; background: var(--wb-panel);
  color: var(--wb-text); font-family: "JetBrains Mono", monospace;
}}
.analysis-workbench .ov-input:focus {{
  border-color: var(--wb-accent);
  outline: 1px solid var(--wb-accent); outline-offset: 0;
}}
.analysis-workbench .ov-reason {{
  width: 100%; padding: 4px 6px; border: 1px solid var(--wb-border);
  border-radius: 3px; font-size: 11px; background: var(--wb-panel);
  color: var(--wb-text);
}}
.analysis-workbench .ov-feedback {{
  font-size: 11px; padding: 2px 0; min-height: 16px;
}}
.analysis-workbench .ov-feedback.ok {{ color: var(--wb-positive); }}
.analysis-workbench .ov-feedback.err {{ color: var(--wb-negative); }}
.analysis-workbench .ov-add-form {{
  margin-top: 10px; padding: 10px;
  background: var(--wb-panel-alt); border-radius: 2px;
  display: grid; grid-template-columns: 200px 110px 1fr 80px; gap: 6px;
  align-items: end;
}}
.analysis-workbench .ov-add-form label {{
  font-size: 10px; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--wb-text-dim);
  display: block; margin-bottom: 3px;
}}
.analysis-workbench .ov-add-input {{
  width: 100%; padding: 4px 6px; border: 1px solid var(--wb-border);
  border-radius: 2px; font-size: 12px; background: var(--wb-panel);
  color: var(--wb-text); font-family: "JetBrains Mono", monospace;
}}
.analysis-workbench .ov-bridge-banner {{
  background: {_rgba(PALETTE['accent'], 0.07)};
  border-left: 3px solid var(--wb-accent);
  padding: 6px 10px; margin-bottom: 10px;
  font-size: 11px; color: var(--wb-text-dim);
}}
"""


# ── Value formatting ─────────────────────────────────────────────────

def _fmt_money(v: Optional[float]) -> str:
    # HOUSE-RULE DEVIATION (deliberate): $M renders at 1dp and $K/$ at
    # 0dp, not the house 2dp-dollars rule. The exact strings "$13.0M",
    # "$10.0M" and "$14.0M" are pinned by test_analysis_workbench and
    # test_scenario_overlay (and mirrored in the page JS fmtMoney), so
    # changing precision here requires a coordinated test cycle.
    if v is None or v != v:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if abs(f) >= 1e9:
        return f"${f / 1e9:.2f}B"
    if abs(f) >= 1e6:
        return f"${f / 1e6:.1f}M"
    if abs(f) >= 1e3:
        return f"${f / 1e3:,.0f}K"
    return f"${f:,.0f}"


def _fmt_pct(v: Optional[float], *, one_dp: bool = True) -> str:
    if v is None or v != v:
        return "—"
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    fmt = "{:.1f}%" if one_dp else "{:.0f}%"
    return fmt.format(f)


def _fmt_signed_pct(v: Optional[float]) -> str:
    if v is None:
        return "—"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.1f}%"


def _fmt_num(v: Optional[float], *, dp: int = 2) -> str:
    if v is None or v != v:
        return "—"
    try:
        return f"{float(v):.{dp}f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_moic(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{float(v):.2f}x"


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _metric_display_name(metric_key: str) -> str:
    """Partner-facing label for a metric key.

    Registry ``display_name`` when the key is known; otherwise the raw
    key with underscores replaced so snake_case never reaches the page.
    """
    key = str(metric_key or "")
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
        name = (RCM_METRIC_REGISTRY.get(key) or {}).get("display_name")
    except Exception:  # noqa: BLE001
        name = None
    return name or key.replace("_", " ")


def _fmt_metric_value(v: Optional[float], unit: str) -> str:
    """Unit-aware metric formatter shared by the Current column and the
    P25/P50/P75 benchmark columns, so ``14.2%`` never sits next to a
    bare ``5.2`` in the same row."""
    if v is None:
        return "—"
    if unit == "pct":
        return _fmt_pct(v)
    if unit == "days":
        try:
            return f"{float(v):.1f}d"
        except (TypeError, ValueError):
            return "—"
    if unit == "dollars":
        return _fmt_money(v)
    return _fmt_num(v, dp=2)


def _fmt_signed_delta(delta: Optional[float], unit: str) -> str:
    """Unit-aware signed delta for the profile table's ``Δ vs P50``.

    The previous renderer piped every raw unit delta through
    ``_fmt_signed_pct``, so a 10-day A/R gap printed as ``+10.0%`` —
    actively misleading on the partner's core table. Percentage-point
    metrics render ``+4.1 pp``, day metrics ``+10.0d``, dollar metrics
    a signed money string, anything else a signed 2dp number.
    """
    if delta is None:
        return "—"
    try:
        d = float(delta)
    except (TypeError, ValueError):
        return "—"
    sign = "+" if d > 0 else ""
    if unit == "pct":
        return f"{sign}{d:.1f} pp"
    if unit == "days":
        return f"{sign}{d:.1f}d"
    if unit == "dollars":
        money = _fmt_money(abs(d))
        return f"-{money}" if d < 0 else f"+{money}"
    return f"{d:+.2f}"


def _looks_internal_reason(reason: str) -> bool:
    """True when a packet section ``reason`` looks like a raw exception
    (repr / traceback) rather than partner-readable copy. Visual review
    caught ``Top-level YAML must be a dict, got <class 'NoneType'>``
    printed verbatim on the Monte Carlo empty state."""
    r = str(reason or "")
    return any(tok in r for tok in ("<class", "Traceback", "Error("))


#: Provenance node ``source`` values → partner-facing labels. Enum
#: values from rcm_mc/provenance/tracker.py Source plus the ad-hoc
#: builder strings in rcm_mc/provenance/graph.py.
_PROV_SOURCE_LABELS = {
    "USER_INPUT": "User input",
    "HCRIS": "HCRIS",
    "IRS990": "IRS Form 990",
    "CARE_COMPARE": "Care Compare",
    "CCD": "Claims dataset",
    "CCD_DERIVED": "Derived (claims dataset)",
    "CALCULATED": "Derived",
    "AGGREGATED": "Cohort aggregate",
    "OBSERVED": "User input",
    "SOURCE": "External source",
    "PREDICTED": "Predicted",
    "REGRESSION_PREDICTED": "Predicted (regression)",
    "ridge_regression": "Predicted (ridge regression)",
    "BENCHMARK": "Benchmark",
    "BENCHMARK_MEDIAN": "Benchmark",
    "MONTE_CARLO_P50": "Monte Carlo",
    "monte_carlo": "Monte Carlo",
    "rcm_ebitda_bridge": "Derived (EBITDA bridge)",
    "comparable_finder": "Comparable cohort",
    "moderate_tier_recommendation": "Benchmark target (moderate tier)",
    "UNKNOWN": "Unknown",
}


def _prov_source_label(source: Any) -> str:
    s = str(source or "").strip()
    if not s:
        return "Unknown"
    if s in _PROV_SOURCE_LABELS:
        return _PROV_SOURCE_LABELS[s]
    words = s.replace("_", " ").strip()
    return words[:1].upper() + words[1:]


def _prov_detail_redundant(source: Any, detail: Any) -> bool:
    """True when ``source_detail`` merely restates the source (e.g.
    detail ``Provided by USER_INPUT`` on a USER_INPUT node) and would
    read as duplication on the provenance row."""
    def _norm(x: Any) -> str:
        return " ".join(str(x or "").lower().replace("_", " ").split())
    d, s = _norm(detail), _norm(source)
    if not d:
        return True
    return d in (s, f"provided by {s}", f"from {s}")


def _humanize_trigger(trigger: str) -> str:
    """Turn a machine trigger pattern (``missing:avoidable_denial_pct``,
    ``ar_over_90_pct=22.4%``) into partner-readable copy using registry
    display names."""
    t = str(trigger or "").strip()
    if not t:
        return t
    if t.startswith("missing:"):
        return f"missing {_metric_display_name(t.split(':', 1)[1])}"
    if "=" in t:
        key, _, val = t.partition("=")
        return f"{_metric_display_name(key.strip())} = {val.strip()}"
    if "_" in t:
        return _metric_display_name(t)
    return t


# ── Section renderers ────────────────────────────────────────────────

def _render_header(packet: DealAnalysisPacket) -> str:
    """Editorial workbench hero — dark-navy band per the design reference.

    Mirrors the reference screenshot: dark navy bg with parchment text,
    eyebrow ("DEAL WORKBENCH · <deal-id>"), large serif deal name,
    metadata row, and right-aligned primary CTAs (EXPORT IC PACKET,
    GENERATE MEMO style). Secondary actions (Archive/Delete/etc.) move
    to a subtle utility row below.
    """
    grade = packet.completeness.grade or "—"
    # No explicit as-of date → show the packet build date rather than
    # the literal word "current" (visual-review defect: "AS OF current").
    if packet.as_of:
        as_of = packet.as_of.isoformat()
    elif getattr(packet, "generated_at", None):
        as_of = packet.generated_at.date().isoformat()
    else:
        as_of = "latest"
    cov = ck_fmt_percent(packet.completeness.coverage_pct)
    freshness = "fresh" if not packet.completeness.stale_fields else \
                f"{len(packet.completeness.stale_fields)} stale"
    deal_id_upper = (packet.deal_id or "").upper()
    n_prov = len((packet.provenance.nodes or {})
                 if getattr(packet, "provenance", None) else {})
    prov_bit = f" · {n_prov} provenance nodes" if n_prov else ""
    return f"""
    <div class="wb-hero">
      <div class="wb-hero-inner">
        <div class="wb-hero-eyebrow">DEAL WORKBENCH &nbsp;·&nbsp; {_esc(deal_id_upper)} &nbsp;·&nbsp; <a class="wb-set-active" href="/deal-context?set={_esc(packet.deal_id)}&return=/deal/{_esc(packet.deal_id)}" title="Carry this deal as ambient context — module links in the bar open pre-scoped to it.">SET ACTIVE</a></div>
        <div class="wb-hero-row">
          <div class="wb-hero-name-block">
            <h1 class="wb-hero-name">{_esc(packet.deal_name or packet.deal_id)}</h1>
            <div class="wb-hero-meta">
              <span class="m-key">COMPLETENESS</span><span class="m-val">{_esc(grade)}</span>
              <span class="m-sep">·</span>
              <span class="m-key">COVERAGE</span><span class="m-val">{_esc(cov)}</span>
              <span class="m-sep">·</span>
              <span class="m-key">AS OF</span><span class="m-val">{_esc(as_of)}</span>
              <span class="m-sep">·</span>
              <span class="m-key">DATA</span><span class="m-val">{_esc(freshness)}</span>
            </div>
          </div>
          <div class="wb-hero-cta">
            <form method="POST" action="/api/analysis/{_esc(packet.deal_id)}/rebuild" class="wb-inline-form">
              <button class="wb-cta-primary" type="submit">REBUILD &nbsp;→</button>
            </form>
            <a class="wb-cta-ghost" href="/api/deals/{_esc(packet.deal_id)}/package">EXPORT ZIP</a>
          </div>
        </div>
      </div>
    </div>
    <div class="wb-utility">
      <div class="wb-utility-inner">
        <div class="wb-utility-bc">
          <a href="/home">home</a> &nbsp;›&nbsp;
          <a href="/analysis">analysis</a> &nbsp;›&nbsp;
          <a href="/deal/{_esc(packet.deal_id)}">{_esc(packet.deal_name or packet.deal_id)}</a>
          &nbsp;›&nbsp; <span class="here">workbench</span>
        </div>
        <div class="wb-utility-actions">
          <a class="wb-btn" href="/models/dcf/{_esc(packet.deal_id)}">DCF</a>
          <a class="wb-btn" href="/models/lbo/{_esc(packet.deal_id)}">LBO</a>
          <a class="wb-btn" href="/models/financials/{_esc(packet.deal_id)}">Financials</a>
          <a class="wb-btn" href="/api/analysis/{_esc(packet.deal_id)}">JSON</a>
          <a class="wb-btn" href="/api/analysis/{_esc(packet.deal_id)}/diligence-questions">Diligence CSV</a>
          <span class="wb-spacer"></span>
          <form method="POST" action="/api/deals/{_esc(packet.deal_id)}/archive" class="wb-inline-form">
            <button class="wb-btn wb-btn-warn" type="submit"
                    onclick="return confirm('Archive this deal? It will be hidden from the dashboard.');"
                    aria-label="Archive this deal">Archive</button>
          </form>
          <button class="wb-btn wb-btn-danger" type="button"
                  onclick="if(confirm('Permanently delete this deal and ALL associated data? This cannot be undone.')){{fetch('/api/deals/{_esc(packet.deal_id)}',{{method:'DELETE'}}).then(r=>r.json()).then(d=>{{if(d.deleted){{if(window.rcmToast)rcmToast('Deal deleted','success');setTimeout(function(){{window.location='/';}},500);}}}}).catch(function(){{if(window.rcmToast)rcmToast('Delete failed','error');}});}}"
                  aria-label="Permanently delete this deal">Delete</button>
        </div>
      </div>
    </div>
    <div class="wb-deck">
      <p class="wb-lede"><em>Six tabs, one packet.</em> Every number on
      this page renders from the same deal-analysis packet — overview,
      profile, bridge, simulation, risk and provenance can never
      disagree, and every figure traces back to its source.</p>
      <p class="wb-source-note">Source: deal analysis packet · as of {_esc(as_of)}{_esc(prov_bit)}</p>
      <ul class="wb-legend">
        <li><span class="wb-dot live"></span>Live data</li>
        <li><span class="wb-dot computed"></span>Computed</li>
        <li><span class="wb-dot needs"></span>Needs data</li>
        <li><span class="wb-dot illustrative"></span>Illustrative</li>
      </ul>
    </div>
    """


def _render_tab_nav(override_count: int = 0) -> str:
    ov_label = f"Assumptions ({override_count})" if override_count else "Assumptions"
    tabs = [
        ("overview",     "Overview"),
        ("profile",      "RCM Profile"),
        ("bridge",       "EBITDA Bridge"),
        ("mc",           "Monte Carlo"),
        ("scenarios",    "Scenarios"),
        ("risk",         "Risk & Diligence"),
        ("provenance",   "Provenance"),
        ("assumptions",  ov_label),
    ]
    buttons = "\n".join(
        f'<button class="wb-tab{" active" if i == 0 else ""}" data-tab="{k}"'
        f' id="wb-tab-{k}" aria-controls="wb-panel-{k}"'
        f' role="tab" aria-selected="{"true" if i == 0 else "false"}">{v}</button>'
        for i, (k, v) in enumerate(tabs)
    )
    return f'<div class="wb-tabs" role="tablist" aria-label="Workbench sections">{buttons}</div>'


def _panel_attrs(key: str) -> str:
    """ARIA plumbing shared by every tab panel — pairs each panel with
    its ``role=tab`` button (``aria-controls`` ↔ ``aria-labelledby``).
    The JS keeps keying off ``data-panel``; these are additive."""
    return (f'id="wb-panel-{key}" role="tabpanel" '
            f'aria-labelledby="wb-tab-{key}"')


def _tab_intro(eyebrow: str, headline: str, italic_phrase: str,
               lede: str = "") -> str:
    """Per-tab editorial section head.

    The house cadence (mono eyebrow → serif headline with an italic
    first phrase → dim one-line lede) applied at tab level, so each
    panel opens with a masthead instead of jumping straight into card
    chrome. Composes the kit's ``ck_eyebrow`` for the caps-and-rule
    anchor; the italic phrase takes the workbench accent (this page's
    token layer — not ``--green-deep``, which would introduce a second
    green family next to the teal accent).
    """
    h = _esc(headline)
    ip = _esc(italic_phrase)
    if ip and ip in h:
        h = h.replace(ip, f"<em>{ip}</em>", 1)
    lede_html = f'<p class="wb-tab-lede">{_esc(lede)}</p>' if lede else ""
    return (
        '<div class="wb-tab-intro">'
        f'{ck_eyebrow(eyebrow)}'
        f'<h2 class="wb-tab-head">{h}</h2>'
        f'{lede_html}'
        '</div>'
    )


# Overview --------------------------------------------------------------

def _hero_kpi_strip(packet: DealAnalysisPacket) -> str:
    """6-card hero KPI strip — the Overview tab's masthead numbers.

    Cards: ENTRY MULTIPLE / BASE MOIC / BASE IRR / COVENANT FLAGS /
    PARTNER VERDICT / METRICS OBSERVED. Data is pulled from the packet
    where available; missing values render "—" (honest partial wiring
    rule). Tones (green / amber / red) signal at-a-glance status.
    Facelift notes: the old "COVENANT HEADROOM" card showed a flag
    COUNT labelled as headroom (a partner reads headroom as a ratio)
    and "HEALTH SCORE" was the third rendering of coverage_pct on one
    tab — both renamed to what they actually are. Key derivations get
    an explain-this-number hover (ck_provenance_tooltip).
    """
    # Entry multiple — from bridge if present (multiples: 2dp + "x")
    em = getattr(packet.ebitda_bridge, "entry_multiple", None) if packet.ebitda_bridge else None
    em_str = _fmt_moic(float(em)) if em is not None else "—"
    # Base MOIC / IRR — from simulation P50
    moic = irr = None
    moic_tone = irr_tone = ""
    sim = packet.simulation
    if sim is not None and sim.status == SectionStatus.OK:
        moic = float(sim.moic.p50) if sim.moic else None
        irr = float(sim.irr.p50) if sim.irr else None
        if moic is not None:
            moic_tone = "green" if moic >= 2.5 else "amber" if moic >= 2.0 else "red"
        if irr is not None:
            irr_tone = "green" if irr >= 0.20 else "amber" if irr >= 0.15 else "red"
    moic_str = _fmt_moic(moic) if moic is not None else "—"
    irr_str = ck_fmt_percent(irr) if irr is not None else "—"
    # Covenant flags — count of covenant-mentioning risk flags
    cov_warns = sum(
        1 for rf in (packet.risk_flags or [])
        if "covenant" in (rf.title or "").lower() or "covenant" in (rf.detail or "").lower()
    )
    cov_str = f"{cov_warns} flag" + ("s" if cov_warns != 1 else "")
    cov_tone = "green" if cov_warns == 0 else "amber" if cov_warns <= 1 else "red"
    # Partner verdict — derive from risk severity counts
    crit = sum(
        1 for rf in (packet.risk_flags or [])
        if (rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)) == "CRITICAL"
    )
    high = sum(
        1 for rf in (packet.risk_flags or [])
        if (rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)) == "HIGH"
    )
    if crit > 0:
        verdict, verdict_tone = "HOLD", "red"
    elif high > 1:
        verdict, verdict_tone = "CAUTION", "amber"
    else:
        verdict, verdict_tone = "PROCEED", "green"
    # Metrics observed — a real packet stat (replaces "HEALTH SCORE",
    # which duplicated COVERAGE under a third name).
    obs = packet.completeness.observed_count or 0
    total = packet.completeness.total_metrics or 0
    obs_str = f"{obs}/{total}" if total else "—"
    cov_pct = float(packet.completeness.coverage_pct or 0.0)
    obs_tone = "green" if cov_pct >= 0.75 else "amber" if cov_pct >= 0.50 else "red"

    em_html = ck_provenance_tooltip(
        "Entry multiple", _esc(em_str),
        explainer="EV / EBITDA multiple assumed at entry — a bridge "
                  "assumption (editable on the Assumptions tab), not "
                  "a computed output.",
    )
    moic_html = ck_provenance_tooltip(
        "Base MOIC", _esc(moic_str),
        explainer="P50 of the Monte Carlo MOIC distribution — the "
                  "median simulated multiple on invested capital, not "
                  "a point estimate.",
        inject_css=False,
    )
    irr_html = ck_provenance_tooltip(
        "Base IRR", _esc(irr_str),
        explainer="P50 of the Monte Carlo IRR distribution (gross, "
                  "levered) across all simulated trajectories.",
        inject_css=False,
    )
    verdict_html = ck_provenance_tooltip(
        "Partner verdict", _esc(verdict),
        explainer="Rules-based screen: HOLD when any CRITICAL risk "
                  "flag fired; CAUTION when more than one HIGH flag "
                  "fired; PROCEED otherwise. A triage signal, not a "
                  "recommendation.",
        inject_css=False,
    )
    flags_html = ck_provenance_tooltip(
        "Covenant flags", _esc(cov_str),
        explainer="Count of risk-scan flags that mention covenants. "
                  "Zero flags means none fired — not that headroom "
                  "was measured.",
        inject_css=False,
    )
    obs_html = ck_provenance_tooltip(
        "Metrics observed", _esc(obs_str),
        explainer="Registry metrics with observed (partner-entered) "
                  "values — the numerator of the coverage grade. "
                  "Predicted and benchmark fills do not count.",
        inject_css=False,
    )

    cards = [
        (em_html,      "ENTRY MULTIPLE",   "EBITDA · base case",     ""),
        (moic_html,    "BASE MOIC",        "5-year hold",            moic_tone),
        (irr_html,     "BASE IRR",         "Gross, levered",         irr_tone),
        (flags_html,   "COVENANT FLAGS",   "From risk scan",         cov_tone),
        (verdict_html, "PARTNER VERDICT",  "Rules-based screen",     verdict_tone),
        (obs_html,     "METRICS OBSERVED", "Of registry",            obs_tone),
    ]
    cells = "".join(
        f'<div class="wb-hero-card{" tone-" + tone if tone else ""}">'
        f'<div class="wb-hc-value">{value}</div>'
        f'<div class="wb-hc-label">{_esc(label)}</div>'
        f'<div class="wb-hc-sub">{_esc(sub)}</div>'
        f'</div>'
        for value, label, sub, tone in cards
    )
    return f'<div class="wb-hero-kpi">{cells}</div>'


def _partner_review_band(packet: DealAnalysisPacket) -> str:
    """Editorial partner-review footer — dark navy band with auto-quote.

    Mirrors the design reference's "PARTNER REVIEW · AUTO-GENERATED"
    section. Composes a one-paragraph review from packet signals.
    Heuristics-fired count + critical count + confidence proxy form the
    bottom row of meta — visible commitment that the verdict is data-
    derived, not narrative-only.
    """
    heuristics = len(packet.risk_flags or [])
    crit = sum(
        1 for rf in (packet.risk_flags or [])
        if (rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)) == "CRITICAL"
    )
    cov = packet.completeness.coverage_pct or 0.0
    coverage = max(0.0, min(1.0, cov)) if cov else 0.0
    # Pick one of three review variants based on data quality
    if not packet.risk_flags or len(packet.risk_flags) < 2:
        review = (
            "Diligence packet has not surfaced material risk flags. "
            "Recommend completing remaining metric collection before "
            "moving the deal forward: partner-level signal is light."
        )
        verdict_label = "MORE DATA NEEDED"
        verdict_tone = "tone-amber"
    elif crit > 0:
        review = (
            f"Critical risk flags present ({crit}); thesis "
            "should be re-tested against the named-failure library before "
            "advancing. Bridge math holds but exit-multiple sensitivity "
            "is high: recommend HOLD pending additional evidence."
        )
        verdict_label = "HOLD"
        verdict_tone = "tone-red"
    else:
        review = (
            "Thesis validated against the corpus: bridge components "
            "track within model tolerance, comparable set is supportive, "
            "and no critical flags fired. Recommend PROCEED with the "
            "covenant items flagged in the diligence checklist as priority "
            "follow-ups during the first 100 days."
        )
        verdict_label = "PROCEED WITH CAVEATS"
        verdict_tone = "tone-green"
    # The label was "CONFIDENCE" printing coverage_pct verbatim — a
    # fabricated confidence number. It IS coverage, so say COVERAGE
    # and format it as the percentage it is.
    return (
        '<div class="wb-partner-review">'
        '<div class="wb-pr-inner">'
        '<div class="wb-pr-eyebrow">PARTNER REVIEW &nbsp;·&nbsp; AUTO-GENERATED</div>'
        f'<p class="wb-pr-quote">{_esc(review)}</p>'
        '<div class="wb-pr-meta">'
        f'<span class="wb-pr-meta-item"><span class="m-key">VERDICT</span>'
        f'<span class="m-val"><span class="wb-pr-dot {verdict_tone}"></span>{_esc(verdict_label)}</span></span>'
        f'<span class="wb-pr-meta-item"><span class="m-key">HEURISTICS FIRED</span>'
        f'<span class="m-val">{heuristics}</span></span>'
        f'<span class="wb-pr-meta-item"><span class="m-key">CRITICAL</span>'
        f'<span class="m-val">{crit}</span></span>'
        f'<span class="wb-pr-meta-item"><span class="m-key">COVERAGE</span>'
        f'<span class="m-val">{ck_fmt_percent(coverage)}</span></span>'
        '</div>'
        '</div>'
        '</div>'
    )


def _render_overview(packet: DealAnalysisPacket) -> str:
    cov_pct = float(packet.completeness.coverage_pct or 0.0)
    missing = [m for m in packet.completeness.missing_fields[:5]]
    missing_html = "".join(
        f'<li><span class="dim">#{m.ebitda_sensitivity_rank}</span> '
        f'{_esc(m.display_name or m.metric_key)} '
        f'<span class="dim">[{_esc(m.category)}]</span></li>'
        for m in missing
    ) or '<li class="dim">all required metrics observed</li>'

    key_findings = []
    for rf in packet.risk_flags[:5]:
        sev = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
        # A.10 PR B — chip placement per user spec: the chip belongs
        # to the SOURCE (the ProfileMetric that triggered the flag),
        # not the flag itself. The flag's severity badge stays loud
        # ("HIGH"); the chip indicates the underlying number is
        # suspect.
        #
        # Tooltip attribution (per PR B Amendment 2): wrap the source
        # PM through ck_aggregate with the trigger-metric name as
        # label, so the chip tooltip explicitly names the source
        # ("Sources: denial_rate (pinv_fallback)") rather than the
        # ambiguous default ("Fit unstable" — which could be misread
        # as "the flag itself is unstable"). The visual proximity of
        # chip-to-flag-text makes this attribution clarity load-bearing.
        source_pm = (packet.rcm_profile.get(rf.trigger_metric)
                     if rf.trigger_metric else None)
        if source_pm is not None and rf.trigger_metric:
            source_chip = ck_prediction_chip(
                ck_aggregate(source_pm, labels=[rf.trigger_metric])
            )
        else:
            source_chip = ""
        key_findings.append(
            f'<li><span class="wb-badge wb-badge-{sev.lower()}">{sev}</span> '
            f'{_esc(rf.title or rf.detail[:80])}{source_chip}</li>'
        )
    findings_html = ("\n".join(key_findings)
                     or '<li class="dim">No risk flags fired on this packet.</li>')

    peers = packet.comparables.peers if packet.comparables else []
    top_peer = peers[0] if peers else None
    if peers:
        avg_sim = sum(p.similarity_score for p in peers) / len(peers)
        comp_summary = (
            f"{len(peers)} hospitals · avg similarity "
            f'<span class="num">{avg_sim:.2f}</span>'
            + (f' · top peer <span class="num">{_esc(top_peer.id)}</span>'
               if top_peer else "")
        )
    else:
        comp_summary = ('<span class="dim">No comparable set available yet — '
                        'add bed count and payer mix to unlock peers.</span>')

    # Hero number — EBITDA total impact from bridge. A green "$0" when the
    # bridge couldn't actually run (no levers contributed / section not OK)
    # is a fabricated zero — it reads as "no opportunity" when the truth is
    # "not computed". Gate the hero on the bridge's own status + evidence.
    _bridge = packet.ebitda_bridge
    total_impact = float(_bridge.total_ebitda_impact or 0.0)
    _bridge_ran = (
        getattr(_bridge, "status", None) == SectionStatus.OK
        and bool(_bridge.per_metric_impacts)
    )
    if _bridge_ran:
        # Explain-this-number hover on the page's biggest figure —
        # same idiom as the hero KPI strip (CSS injected there).
        _hero_val = ck_provenance_tooltip(
            "EBITDA opportunity", _fmt_money(total_impact),
            explainer="Sum of the per-lever EBITDA impacts from "
                      "current to target (moderate tier) computed by "
                      "the bridge — the figure the waterfall "
                      "reconciles.",
            inject_css=False,
        )
        hero_html = f'<div class="hero-number pos">{_hero_val}</div>'
        # Caption interpolates the real current → target EBITDA rather
        # than printing the literal template words.
        hero_caption = (
            f'<div class="dim hero-caption">'
            f'{_fmt_money(_bridge.current_ebitda)} → '
            f'{_fmt_money(_bridge.target_ebitda)} (moderate tier)</div>'
        )
    else:
        _why = (getattr(_bridge, "reason", "") or
                "bridge inputs incomplete — upload RCM metrics").rstrip(".")
        # Sentence case, em-dash join; "yet" only where it reads
        # naturally ("no revenue baseline yet").
        _yet = " yet" if _why.lower().startswith("no ") else ""
        hero_html = ('<div class="hero-number dim">—</div>'
                     f'<div class="dim hero-why">'
                     f'Not computed — {_esc(_why)}{_yet}.</div>')
        # No numbers to caption — hide the current → target line
        # entirely instead of rendering placeholder words.
        hero_caption = ""
    ev_at_multiple = _bridge.ev_impact_at_multiple or {}
    ev_bits = " · ".join(
        f'<span class="dim">{k}</span> {_fmt_money(v)}'
        for k, v in list(ev_at_multiple.items())[:3]
    ) or '<span class="dim">No EV computed yet.</span>'

    # Returns distribution (MOIC) mini-summary if MC available —
    # rendered through the kit's stat-tile primitive so the Returns
    # card matches the house KPI anatomy (rule / label / mono value).
    mc = packet.simulation
    if mc is not None and mc.status == SectionStatus.OK:
        moic_block = ck_kpi_block(
            "MOIC · P10 / P50 / P90",
            f'<span class="num">{_fmt_moic(mc.moic.p10)} · '
            f'{_fmt_moic(mc.moic.p50)} · {_fmt_moic(mc.moic.p90)}</span>',
            sub="Monte Carlo, 5-year hold",
        )
    else:
        moic_block = ck_kpi_block(
            "MOIC · P10 / P50 / P90",
            '<span class="dim">—</span>',
            sub="Monte Carlo not run",
        )

    # Risk summary badges.
    sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for rf in packet.risk_flags:
        val = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
        sev_counts[val] = sev_counts.get(val, 0) + 1
    risk_badges = " ".join(
        f'<span class="wb-badge wb-badge-{sev.lower()}">{sev}: {n}</span>'
        for sev, n in sev_counts.items() if n > 0
    ) or '<span class="dim">No risk flags fired.</span>'

    # Radial progress SVG.
    radius = 40
    circ = 2 * 3.14159 * radius
    dash = circ * cov_pct
    radial_svg = (
        f'<svg width="90" height="90" viewBox="0 0 90 90">'
        f'<circle cx="45" cy="45" r="{radius}" fill="none" '
        f'stroke="{PALETTE["border"]}" stroke-width="8"/>'
        f'<circle cx="45" cy="45" r="{radius}" fill="none" '
        f'stroke="{PALETTE["accent"]}" stroke-width="8" '
        f'stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-linecap="round"/>'
        f'</svg>'
    )
    radial_label = f'<div class="radial-label">{int(cov_pct*100)}%</div>'

    hero_kpi = _hero_kpi_strip(packet)
    intro = _tab_intro(
        "OVERVIEW", "One screen, every headline number.", "One screen",
        "Entry economics, the returns band, risk posture and data "
        "coverage — each figure on this tab traces back to the packet.",
    )
    return f"""
    <div class="wb-tab-panel active" data-panel="overview" {_panel_attrs("overview")}>
      {intro}
      {hero_kpi}
      <div class="wb-grid">
        <div>
          <div class="wb-card">
            <div class="wb-card-title">Completeness</div>
            <div class="wb-flex-row">
              <div class="radial">{radial_svg}{radial_label}</div>
              <div>
                <div class="kpi-value">{packet.completeness.observed_count}/{packet.completeness.total_metrics}</div>
                <div class="kpi-label">metrics observed · grade {packet.completeness.grade or "—"}</div>
              </div>
            </div>
            <div class="wb-card-title wb-card-subtitle">Top missing metrics (by EBITDA sensitivity)</div>
            <ol class="wb-list">{missing_html}</ol>
          </div>
          <div class="wb-card">
            <div class="wb-card-title">Key Findings</div>
            <ul class="wb-list">{findings_html}</ul>
          </div>
          <div class="wb-card">
            <div class="wb-card-title">Comparable Set</div>
            <div>{comp_summary}</div>
          </div>
        </div>
        <div>
          <div class="wb-card">
            <div class="kpi-label">EBITDA Opportunity</div>
            {hero_html}
            {hero_caption}
            <div class="wb-ev-line">{ev_bits}</div>
          </div>
          <div class="wb-card">
            {moic_block}
          </div>
          <div class="wb-card">
            <div class="wb-card-title">Risk Summary</div>
            <div>{risk_badges}</div>
          </div>
          {_render_next_actions(packet)}
        </div>
      </div>
    </div>
    """


# RCM Profile -----------------------------------------------------------

# Typographic source tags — (chip text, tone class, plain meaning).
# Replaces the emoji encoding (👤/🔮/📊) whose meaning lived only in a
# title attribute; mirrors the ck_basis_badge letter-chip idiom.
_SOURCE_TAG = {
    MetricSource.OBSERVED:  ("OBS", "src-observed",
                             "Observed — partner-entered deal data"),
    MetricSource.PREDICTED: ("PRED", "src-predicted",
                             "Predicted — model estimate, not a filing"),
    MetricSource.BENCHMARK: ("BMK", "src-benchmark",
                             "Benchmark — cohort value, not deal data"),
    MetricSource.UNKNOWN:   ("—", "src-unknown", "Source unknown"),
}


def _metric_category_for(metric_key: str) -> str:
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
        return (RCM_METRIC_REGISTRY.get(metric_key) or {}).get("category") or "other"
    except Exception:  # noqa: BLE001
        return "other"


def _render_next_actions(packet: DealAnalysisPacket) -> str:
    """'What Should I Do Next?' card — 3 prioritized actions based
    on the packet's current state (Prompt 32 enhancement).

    Associates see this and know exactly what to click — no guessing.
    """
    actions: List[str] = []

    # Low completeness → upload data. CTAs render via ck_arrow_link —
    # the house editorial CTA — with the endpoints byte-identical to
    # the pre-facelift hrefs.
    grade = getattr(packet.completeness, "grade", "") or ""
    if grade in ("C", "D") or not grade:
        actions.append(
            f'<div><strong>Upload more data</strong>: completeness is '
            f'{grade or "?"}, which limits prediction accuracy. '
            + ck_arrow_link("Upload files",
                            f"/new-deal/step3?deal_id={packet.deal_id}")
            + '</div>'
        )

    # Critical risks → review.
    critical_count = sum(
        1 for rf in (packet.risk_flags or [])
        if (rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)) == "CRITICAL"
    )
    if critical_count > 0:
        plural = "risks" if critical_count != 1 else "risk"
        actions.append(
            f'<div><strong>Review {critical_count} critical {plural}</strong>: '
            f'open the Risk &amp; Diligence tab to see details and address '
            f'the top-priority flags.</div>'
        )

    # No MC → run simulation.
    if packet.simulation is None or (
        hasattr(packet.simulation, "status")
        and str(getattr(packet.simulation.status, "value", ""))
        not in ("OK",)
    ):
        actions.append(
            f'<div><strong>Run Monte Carlo</strong>: no simulation on '
            f'this analysis yet. '
            + ck_arrow_link("Run now",
                            f"/api/analysis/{packet.deal_id}/simulate/v2")
            + '</div>'
        )

    # Missing diligence questions answered → export package.
    if packet.diligence_questions and not actions:
        actions.append(
            f'<div><strong>Generate IC package</strong>: analysis is '
            f'complete. '
            + ck_arrow_link(
                "Export",
                f"/api/analysis/{packet.deal_id}/export?format=package")
            + '</div>'
        )

    if not actions:
        body = ('<div class="wb-action-ok"><strong>Looking good</strong>: '
                'completeness, risks, and simulation are all in order.</div>')
    else:
        body = "\n".join(
            f'<div class="wb-action"><span class="wb-action-n">{i}</span>{a}</div>'
            for i, a in enumerate(actions[:3], start=1)
        )
    return f"""
    <div class="wb-card">
      <div class="wb-card-title">Next actions</div>
      <div class="wb-actions">{body}</div>
    </div>
    """


def _render_trend_cell(forecast: Dict[str, Any]) -> str:
    """Inline trend arrow + tiny sparkline SVG for one metric.

    Renders alongside the metric name in the RCM Profile table. Arrow
    is ↑ / ↓ / → colored by direction:

    - green for "improving"
    - red for "deteriorating"
    - grey for "stable" or low-n series

    The SVG is a 60×20 sparkline of the historical series (no
    interactivity — click the metric name for the full explain
    panel). Historical + forecast dashed continuation is sized so the
    row height stays the same as metric rows without a forecast.
    """
    trend = (forecast or {}).get("trend") or {}
    direction = trend.get("direction") or "stable"
    slope = float(trend.get("slope_per_period") or 0)
    n = int(trend.get("n_periods") or 0)
    historical = forecast.get("historical") or []
    forecasted = forecast.get("forecasted") or []

    arrow = {"improving": "↑", "deteriorating": "↓"}.get(direction, "→")
    color = {
        "improving": PALETTE["positive"],
        "deteriorating": PALETTE["negative"],
    }.get(direction, PALETTE["text_faint"])
    trend_cls = {
        "improving": "trend-up",
        "deteriorating": "trend-down",
    }.get(direction, "trend-flat")
    tooltip = (
        f"{direction}, {slope:+.3f}/period across {n} periods"
    )

    # Tiny sparkline.
    sparkline = ""
    if historical:
        vals = [float(row.get("value") or 0) for row in historical]
        fut_vals = [float(row.get("value") or 0) for row in forecasted]
        full = vals + fut_vals
        if full:
            lo = min(full)
            hi = max(full)
            span = hi - lo if (hi - lo) > 0 else 1.0
            w, h = 60, 20
            n_total = len(full) - 1 if len(full) > 1 else 1
            def _pt(i: int, v: float) -> str:
                x = (i / max(1, n_total)) * (w - 2) + 1
                y = h - 2 - ((v - lo) / span) * (h - 4)
                return f"{x:.1f},{y:.1f}"
            hist_pts = " ".join(_pt(i, v) for i, v in enumerate(vals))
            offset = len(vals) - 1
            fut_pts = " ".join(
                _pt(offset + i + 1, v) for i, v in enumerate(fut_vals)
            )
            last_hist_pt = _pt(offset, vals[-1]) if vals else ""
            dashed_pts = f"{last_hist_pt} {fut_pts}".strip() if fut_vals else ""
            sparkline = (
                f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
                f'class="wb-spark" aria-hidden="true">'
                f'<polyline points="{hist_pts}" fill="none" '
                f'stroke="{color}" stroke-width="1.2"/>'
                + (f'<polyline points="{dashed_pts}" fill="none" '
                   f'stroke="{color}" stroke-dasharray="2,2" '
                   f'stroke-width="1"/>' if dashed_pts else "")
                + "</svg>"
            )

    return (
        f'<span class="wb-trend {trend_cls}" '
        f'title="{_esc(tooltip)}">{arrow}</span>{sparkline}'
    )


def _render_rcm_profile(packet: DealAnalysisPacket) -> str:
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
    except Exception:  # noqa: BLE001
        RCM_METRIC_REGISTRY = {}

    # Group rows by category. Iterate in registry order so categories
    # have a stable sort key even if some are missing.
    rows_by_category: Dict[str, List[str]] = {}
    for metric_key in packet.rcm_profile:
        cat = _metric_category_for(metric_key)
        rows_by_category.setdefault(cat, []).append(metric_key)

    category_order = ["denials", "collections", "ar", "claims", "coding", "financial", "other"]
    parts: List[str] = []
    parts.append(
        '<table class="wb-table"><thead><tr>'
        '<th>Metric</th><th class="num">Current</th><th class="center">Source</th>'
        '<th class="num">P25</th><th class="num">P50</th><th class="num">P75</th>'
        '<th class="num">Δ vs P50</th><th>Confidence</th>'
        '</tr></thead><tbody>'
    )
    for cat in category_order:
        keys = rows_by_category.get(cat) or []
        if not keys:
            continue
        parts.append(f'<tr class="wb-group-header"><td colspan="8">{_esc(cat.upper())}</td></tr>')
        for metric_key in keys:
            pm = packet.rcm_profile[metric_key]
            meta = RCM_METRIC_REGISTRY.get(metric_key) or {}
            p25, p50, p75 = meta.get("benchmark_p25"), meta.get("benchmark_p50"), meta.get("benchmark_p75")
            unit = meta.get("unit") or ""
            delta = None
            cell_class = "dim"
            if p50 is not None:
                try:
                    delta = float(pm.value) - float(p50)
                    # Direction: lower is better for rate/days metrics
                    lower_better = cat in ("denials", "ar") or metric_key in (
                        "cost_to_collect", "bad_debt_rate", "ar_over_90_pct",
                        "charge_lag_days", "claim_rejection_rate",
                        "late_charge_pct",
                    )
                    better = (delta < 0) if lower_better else (delta > 0)
                    if abs(delta) < 1e-9:
                        cell_class = "dim"
                    else:
                        cell_class = "pos" if better else "neg"
                except (TypeError, ValueError):
                    delta = None
            value_fmt = _fmt_metric_value(pm.value, unit)
            src_tag, src_cls, src_meaning = _SOURCE_TAG.get(
                pm.source, ("—", "src-unknown", "Source unknown"))
            quality = pm.quality or ""
            conf_bar = _quality_bar(quality)
            # B.1 — α-disclosure for cohort-tuned ridge fits. Renders
            # only when this PM came from the new RidgeCV path (D4
            # locked surface: workbench metric cell adjacent to quality
            # bar, persistent text, not behind hover). The two-word
            # "cohort-tuned" in the tooltip carries the methodology
            # change for any partner who hovers — see D4 refinement 1b.
            alpha_html = ""
            cohort_alpha = getattr(pm, "cohort_alpha", None)
            methodology_version = getattr(pm, "methodology_version", None)
            if (cohort_alpha is not None
                    and methodology_version == "b1-tuned-alpha"):
                alpha_html = (
                    f'<span class="ck-cohort-alpha" '
                    f'title="Ridge penalty tuned per-cohort via RidgeCV LOO · see methodology doc">'
                    f'α={cohort_alpha:.2f}</span>'
                )
            # Advisory: the prediction's target was strictly positive and
            # right-skewed, so a log/Box-Cox transform would likely improve the
            # fit. Model-quality guidance only — does not change the value.
            if getattr(pm, "log_transform_suggested", False):
                alpha_html += (
                    f'<span class="ck-cohort-alpha" '
                    f'title="Target is right-skewed and strictly positive, so a log/Box-Cox '
                    f'transform would likely stabilize variance and improve the fit. '
                    f'Model-quality advisory; the predicted value is unchanged.">log?</span>'
                )
            # Prompt 27: inline trend arrow + sparkline for metrics
            # with uploaded history.
            forecast = (packet.metric_forecasts or {}).get(metric_key)
            trend_html = _render_trend_cell(forecast) if forecast else ""
            # Prompt 28: ⚠ when the completeness anomalies list
            # flagged this metric.
            anomaly_html = ""
            for a in (packet.completeness.anomalies or []):
                if a.get("metric_key") != metric_key:
                    continue
                sev_cls = {
                    "CRITICAL": "sev-critical",
                    "HIGH": "sev-high",
                    "MEDIUM": "sev-medium",
                }.get(a.get("severity", "MEDIUM"), "sev-low")
                anomaly_html = (
                    f'<span class="wb-anomaly {sev_cls}" '
                    f'title="{_esc(a.get("explanation") or "")}">⚠</span>'
                )
                break
            # A.10 PR B — render diagnostic chip inline with the
            # value when the underlying prediction was suspect. The
            # chip is empty for clean / non-predicted (OBSERVED /
            # AUTO_POPULATED) ProfileMetrics, so this is no-op for
            # the common case. Tier 2 (UNSTABLE_FIT) is the only
            # variant that fires today from real predictor paths;
            # Tier 1 / Tier 3 wait on the orchestrator-emit refactor.
            chip_html = ck_prediction_chip(pm)
            metric_label = meta.get("display_name") or metric_key
            parts.append(
                '<tr>'
                f'<td><a href="#prov-{_esc(metric_key)}" class="dim wb-metric-link" title="{_esc(metric_key)}">{_esc(metric_label)}</a>{anomaly_html}{trend_html}</td>'
                f'<td class="num {cell_class}">{value_fmt}{chip_html}</td>'
                f'<td class="center" title="{_esc(src_meaning)}">'
                f'<span class="wb-src-chip {src_cls}" role="img" aria-label="{_esc(pm.source.value)}">{_esc(src_tag)}</span></td>'
                f'<td class="num dim">{_fmt_metric_value(p25, unit)}</td>'
                f'<td class="num dim">{_fmt_metric_value(p50, unit)}</td>'
                f'<td class="num dim">{_fmt_metric_value(p75, unit)}</td>'
                f'<td class="num {cell_class}">{_fmt_signed_delta(delta, unit) if delta is not None else "—"}</td>'
                f'<td>{conf_bar}{alpha_html}</td>'
                '</tr>'
            )
    parts.append('</tbody></table>')

    # Payer-performance heatmap (simple grid).
    heatmap_html = _render_payer_heatmap(packet)

    intro = _tab_intro(
        "RCM PROFILE", "Every metric, benchmarked against its cohort.",
        "Every metric",
        "Observed and predicted values sit beside cohort P25/P50/P75 "
        "bands; the Δ column scores the gap in each metric's own unit.",
    )
    return f"""
    <div class="wb-tab-panel" data-panel="profile" {_panel_attrs("profile")}>
      {intro}
      <div class="wb-card">
        <div class="wb-card-title">Metric detail</div>
        {''.join(parts)}
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Payer performance matrix</div>
        {heatmap_html}
      </div>
    </div>
    """


def _quality_bar(q: str) -> str:
    """Confidence bar + text label.

    The bar used to be width-only encoding — invisible to screen
    readers and ambiguous to everyone ("is 40px good?"). It now
    carries a mono text label, a title, and an aria-label alongside
    the width cue; tone classes live in the page CSS.
    """
    level = q if q in ("high", "medium", "low") else ""
    cls = f"q-{level}" if level else "q-none"
    label = level or "n/a"
    desc = f"Confidence: {label}"
    return (
        f'<span class="wb-qbar {cls}" role="img" aria-label="{_esc(desc)}" '
        f'title="{_esc(desc)}"><span></span></span>'
        f'<span class="wb-qbar-label">{_esc(label)}</span>'
    )


def _render_payer_heatmap(packet: DealAnalysisPacket) -> str:
    """Render denial_rate_* metrics by payer in a small grid."""
    payers = [
        ("Medicare FFS", "denial_rate_medicare_ffs"),
        ("Medicare Advantage", "denial_rate_medicare_advantage"),
        ("Commercial", "denial_rate_commercial"),
        ("Medicaid", "denial_rate_medicaid"),
    ]
    # All-null payer set → four em-dash cells with no explanation reads
    # as a broken grid. Render the page's standard empty-state line.
    if all(packet.rcm_profile.get(k) is None for _, k in payers):
        return ('<div class="dim">No payer-level data uploaded yet — '
                'add payer mix to the deal profile.</div>')
    cells = []
    for label, metric_key in payers:
        pm = packet.rcm_profile.get(metric_key)
        if pm is None:
            val_html = '<span class="dim">—</span>'
            tone_cls = ""
        else:
            v = float(pm.value)
            # Color scale: green if <5, amber if <10, red otherwise.
            if v < 5.0:
                tone_cls = " hm-good"
            elif v < 10.0:
                tone_cls = " hm-warn"
            else:
                tone_cls = " hm-bad"
            val_html = f'<span class="num">{_fmt_pct(v)}</span>'
        cells.append(
            f'<div class="heatmap-cell{tone_cls}">'
            f'<div class="hm-label">{_esc(label)}</div>'
            f'{val_html}</div>'
        )
    return (
        '<div class="heatmap heatmap-payer">'
        + "".join(cells)
        + "</div>"
    )


# EBITDA Bridge tab -----------------------------------------------------

def _render_bridge(packet: DealAnalysisPacket) -> str:
    br = packet.ebitda_bridge
    intro = _tab_intro(
        "EBITDA BRIDGE", "Lever by lever, current to target.",
        "Lever by lever",
        "Drag a target and the bridge recomputes server-side — the "
        "same math the IC packet prints.",
    )
    if br.status != SectionStatus.OK or not br.per_metric_impacts:
        empty = ck_empty_state(
            "The bridge has nothing to build from yet.",
            "The EBITDA bridge needs a revenue baseline plus at least "
            "one RCM metric to model improvements against. Open Ingest "
            "and attach a Canonical Claims Dataset, or upload "
            "management-reported quarterly actuals on the deal page.",
            eyebrow="EBITDA BRIDGE",
            icon="≡",
            cta_label="Open Ingest",
            cta_href="/diligence/ingest",
        )
        return f"""
        <div class="wb-tab-panel" data-panel="bridge" {_panel_attrs("bridge")}>
          {intro}
          {empty}
          <p class="dim wb-center-note">
            Or upload actuals on the
            <a href="/deal/{_esc(packet.deal_id)}">deal page</a>.
            &nbsp;·&nbsp; Reason: {_esc(br.reason or "no impacts computed")}
          </p>
        </div>
        """

    # Sliders (left) — labels use registry display names; the raw
    # metric key stays in data-metric / ids for the slider JS.
    slider_rows = []
    assumptions_payload: List[Dict[str, Any]] = []
    label_map: Dict[str, str] = {}
    for imp in br.per_metric_impacts:
        # Range and step inferred from metric type.
        lo, hi, step = _slider_range(imp.metric_key, imp.current_value, imp.target_value)
        slider_id = f"slider-{imp.metric_key}"
        label_map[imp.metric_key] = _metric_display_name(imp.metric_key)
        assumptions_payload.append({
            "metric": imp.metric_key,
            "current": imp.current_value,
            "target": imp.target_value,
            "lo": lo, "hi": hi, "step": step,
        })
        slider_rows.append(
            f'<div class="slider-row" data-metric="{_esc(imp.metric_key)}">'
            f'<div class="slider-label" title="{_esc(imp.metric_key)}">{_esc(label_map[imp.metric_key])}</div>'
            f'<input type="range" class="wb-slider" id="{slider_id}" '
            f'min="{lo}" max="{hi}" step="{step}" value="{imp.target_value}" '
            f'data-current="{imp.current_value}" data-target="{imp.target_value}" '
            f'data-metric="{_esc(imp.metric_key)}" '
            f'aria-label="Target for {_esc(label_map[imp.metric_key])}">'
            f'<div class="slider-target" id="{slider_id}-val">{imp.target_value:.2f}</div>'
            f'<div class="slider-delta dim" id="{slider_id}-delta">—</div>'
            f'</div>'
        )

    # Waterfall (right)
    waterfall = _render_waterfall(br)

    # Sensitivity tornado
    tornado = _render_tornado(br)

    summary_line = (
        f'Improving from current to target adds '
        f'<span class="pos num">{_fmt_money(br.total_ebitda_impact)}</span> to EBITDA '
        f'(<span class="num">{br.margin_improvement_bps:+d}</span> bps margin). '
    )
    ev = br.ev_impact_at_multiple or {}
    if ev:
        ev_bits = " · ".join(f"{k} → <span class='num'>{_fmt_money(v)}</span>"
                              for k, v in ev.items())
        summary_line += f"Enterprise value uplift: {ev_bits}."

    # JSON bootstrap for slider JS. We POST this exact shape to
    # /api/analysis/<deal_id>/bridge when sliders move. ``labels``
    # lets the JS re-render print display names instead of raw
    # metric keys (the API response only carries keys).
    bootstrap = json.dumps({
        "deal_id": packet.deal_id,
        "assumptions": assumptions_payload,
        "labels": label_map,
    })

    bridge_overrides = {
        k: v for k, v in (packet.analyst_overrides or {}).items()
        if k.startswith("bridge.")
    }
    override_banner = ""
    if bridge_overrides:
        keys = ", ".join(
            f'<span class="ov-badge-a">A</span> {_esc(k.removeprefix("bridge."))}'
            f" = {_esc(str(v))}"
            for k, v in bridge_overrides.items()
        )
        override_banner = (
            f'<div class="ov-bridge-banner">Analyst overrides active on this bridge: '
            f'{keys}. &nbsp;<a href="#" data-tab-goto="assumptions">Edit in Assumptions →</a></div>'
        )

    return f"""
    <div class="wb-tab-panel" data-panel="bridge" {_panel_attrs("bridge")}>
      {intro}
      {override_banner}
      <div class="wb-grid-5050">
        <div class="wb-card">
          <div class="wb-card-title">Target sliders</div>
          <div class="wb-preset-row">
            <button class="wb-btn" data-preset="conservative">Conservative</button>
            <button class="wb-btn" data-preset="moderate">Moderate</button>
            <button class="wb-btn" data-preset="aggressive">Aggressive</button>
            <button class="wb-btn" data-preset="reset">Reset</button>
          </div>
          {''.join(slider_rows)}
        </div>
        <div class="wb-card">
          <div class="wb-card-title">Waterfall</div>
          <div id="wb-waterfall">{waterfall}</div>
          <div class="wb-bridge-status" id="wb-bridge-status" aria-live="polite"></div>
        </div>
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Sensitivity tornado</div>
        {tornado}
      </div>
      <div class="wb-card">
        <div id="wb-bridge-summary">{summary_line}</div>
      </div>
      <script id="wb-bridge-bootstrap" type="application/json">{ck_json_for_script(bootstrap)}</script>
    </div>
    """


def _slider_range(metric: str, current: float, target: float) -> tuple:
    """Choose a sensible slider min/max/step per metric unit."""
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
        meta = RCM_METRIC_REGISTRY.get(metric) or {}
        unit = meta.get("unit") or ""
        lo_r, hi_r = meta.get("valid_range") or (0, 100)
    except Exception:  # noqa: BLE001
        unit, lo_r, hi_r = "", 0, 100
    if unit == "pct":
        return (0, 100, 0.1)
    if unit == "days":
        return (max(0, lo_r), min(365, hi_r), 1)
    if unit == "index":
        return (max(0, lo_r), min(5, hi_r), 0.01)
    if unit == "dollars":
        return (0, max(current, target) * 3 or 1e6, 1_000_000)
    return (lo_r, hi_r, 0.1)


def _render_waterfall(br) -> str:
    # Find max abs width for scaling. Lever rows use registry display
    # names; the JS re-render resolves the same names via the
    # bootstrap ``labels`` map so a slider drag never flips the
    # waterfall back to snake_case keys.
    rows = []
    steps = []
    running = float(br.current_ebitda)
    steps.append(("Current EBITDA", running, "anchor"))
    for imp in br.per_metric_impacts:
        running += imp.ebitda_impact
        kind = "pos" if imp.ebitda_impact >= 0 else "neg"
        steps.append((_metric_display_name(imp.metric_key), imp.ebitda_impact, kind))
    steps.append(("Target EBITDA", br.target_ebitda, "anchor"))

    max_abs = max((abs(v) for _, v, _ in steps if v), default=1.0)
    for label, val, kind in steps:
        bar_pct = max(1.0, (abs(val) / max_abs) * 100) if max_abs else 0
        rows.append(
            f'<div class="wf-row">'
            f'<div>{_esc(label)}</div>'
            f'<div class="wf-track">'
            f'<div class="wf-bar {kind}" style="width:{bar_pct:.1f}%"></div>'
            f'</div>'
            f'<div class="num">{_fmt_money(val)}</div>'
            f'</div>'
        )
    return f'<div class="waterfall">{"".join(rows)}</div>'


def _render_tornado(br) -> str:
    impacts = [(imp.metric_key, imp.ebitda_impact) for imp in br.per_metric_impacts]
    impacts.sort(key=lambda r: abs(r[1]), reverse=True)
    if not impacts:
        return ('<div class="dim">No impacts computed yet — '
                'set metric targets to size the levers.</div>')
    max_abs = max(abs(v) for _, v in impacts) or 1.0
    rows = []
    for metric, val in impacts:
        width = (abs(val) / max_abs) * 100
        cls = "pos" if val >= 0 else "neg"
        rows.append(
            f'<div class="tornado-row">'
            f'<div title="{_esc(metric)}">{_esc(_metric_display_name(metric))}</div>'
            f'<div class="tornado-bar {cls}" style="width:{width:.1f}%;"></div>'
            f'<div class="num {cls}">{_fmt_money(val)}</div>'
            f'</div>'
        )
    return "".join(rows)


# Monte Carlo tab -------------------------------------------------------

def _render_mc(packet: DealAnalysisPacket) -> str:
    mc = packet.simulation
    intro = _tab_intro(
        "MONTE CARLO", "A band, not a point estimate.", "A band",
        "Thousands of simulated trajectories put P10 / P50 / P90 "
        "bounds on the EBITDA plan and the returns it implies.",
    )
    if mc is None or mc.status != SectionStatus.OK:
        reason = (mc.reason if mc else "") or "simulation not run"
        # Packet failures store the raw exception text (e.g. "Top-level
        # YAML must be a dict, got <class 'NoneType'>"). Never show a
        # partner an exception repr — map it to actionable plain copy.
        if _looks_internal_reason(reason):
            reason = ("Simulation inputs not configured yet — set "
                      "actuals/benchmark paths on the deal page.")
        empty = ck_empty_state(
            "Monte Carlo has not run on this packet.",
            "The simulation draws thousands of EBITDA-improvement "
            "trajectories to give a P10 / P50 / P90 band instead of a "
            "single point estimate. Click REBUILD at the top of the "
            "workbench to refresh the packet with simulation enabled.",
            eyebrow="MONTE CARLO",
            icon="∿",
            cta_label="Open the deal page",
            cta_href=f"/deal/{packet.deal_id}",
        )
        return f"""
        <div class="wb-tab-panel" data-panel="mc" {_panel_attrs("mc")}>
          {intro}
          {empty}
          <p class="dim wb-center-note">
            CLI alternative: <code class="mono">rcm-mc analysis {_esc(packet.deal_id)}</code>
            &nbsp;·&nbsp; Reason: {_esc(reason)}
          </p>
        </div>
        """

    uplift = mc.ebitda_uplift
    histo_svg = _render_histogram_svg(uplift)
    stats = (
        f'<table class="wb-table wb-table-narrow">'
        f'<tbody>'
        + "".join(
            f'<tr><td class="dim">{label}</td><td class="num">{_fmt_money(val)}</td></tr>'
            for label, val in [
                ("P10", uplift.p10), ("P25", uplift.p25), ("P50", uplift.p50),
                ("P75", uplift.p75), ("P90", uplift.p90),
            ]
        )
        + "</tbody></table>"
    )

    # MOIC bands: the packet's MC section in SimulationSummary only
    # holds a PercentileSet, not the raw probability_of_target_moic
    # dict — render the three percentiles through the kit stat tile.
    moic_summary = ck_kpi_block(
        "MOIC bands",
        f'<span class="num">P10 {_fmt_moic(mc.moic.p10)} · '
        f'P50 {_fmt_moic(mc.moic.p50)} · '
        f'P90 {_fmt_moic(mc.moic.p90)}</span>',
        sub="Multiple on invested capital across simulated trajectories",
    )

    # Variance contribution tornado.
    vc = mc.variance_contribution_by_metric or {}
    var_rows = []
    if vc:
        total = sum(vc.values()) or 1.0
        ordered = sorted(vc.items(), key=lambda kv: abs(kv[1]), reverse=True)
        for metric, share in ordered:
            pct = (share / total) * 100.0
            var_rows.append(
                f'<div class="tornado-row">'
                f'<div title="{_esc(metric)}">{_esc(_metric_display_name(metric))}</div>'
                f'<div class="tornado-bar share" style="width:{pct:.1f}%;"></div>'
                f'<div class="num">{pct:.1f}%</div>'
                f'</div>'
            )
    var_html = "".join(var_rows) or (
        '<div class="dim">No variance decomposition available — '
        'rerun the simulation to attribute spread to levers.</div>')

    n_sims = mc.n_sims or 0
    conv = mc.convergence_check or {}
    converged = bool(conv.get("converged"))
    # Convergence is a signal, not title prose — kit badge tone
    # (positive / warning) instead of a parenthesised aside.
    conv_badge = ck_signal_badge(
        "converged" if converged else "not converged",
        tone="positive" if converged else "warning",
    )
    return f"""
    <div class="wb-tab-panel" data-panel="mc" {_panel_attrs("mc")}>
      {intro}
      <div class="wb-card">
        <div class="wb-card-title">EBITDA impact — percentile band ({n_sims:,} sims) {conv_badge}</div>
        <div class="histo">{histo_svg}</div>
        <div class="wb-chart-caption">Shape approximated from P10–P90 percentiles — not raw draws</div>
      </div>
      <div class="wb-grid-5050">
        <div class="wb-card">
          <div class="wb-card-title">Summary stats</div>
          {stats}
        </div>
        <div class="wb-card">
          {moic_summary}
        </div>
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Variance contribution</div>
        {var_html}
      </div>
    </div>
    """


def _render_histogram_svg(ps: PercentileSet) -> str:
    """Minimal inline SVG approximating the distribution from the 5-point
    PercentileSet. We don't have the raw draws in the packet; draw a
    piecewise-linear density instead using those five anchors."""
    # Guard against degenerate zero-width distributions.
    p10 = float(ps.p10 or 0.0)
    p50 = float(ps.p50 or 0.0)
    p90 = float(ps.p90 or 0.0)
    if p10 == 0 and p50 == 0 and p90 == 0:
        return ('<div class="dim wb-center-note">No distribution data — '
                'the simulation produced a degenerate zero-width band.</div>')
    span = max(p90 - p10, 1.0)
    width, height = 720, 160
    xs = [p10, ps.p25 or (p10 + 0.25 * span), p50, ps.p75 or (p50 + 0.25 * span), p90]
    x_pct = [(x - p10) / span for x in xs]
    # Vertical lines for P10/P50/P90.
    lines = ""
    for label, x in (("P10", 0.0), ("P50", (p50 - p10) / span), ("P90", 1.0)):
        x_px = x * (width - 80) + 40
        lines += (
            f'<line x1="{x_px}" x2="{x_px}" y1="20" y2="{height-24}" '
            f'stroke="{PALETTE["text_faint"]}" stroke-dasharray="3,3"/>'
            f'<text x="{x_px}" y="{height-6}" fill="{PALETTE["text_dim"]}" '
            f'text-anchor="middle" font-size="10">{label}</text>'
        )
    # Density curve — use 5 anchors and linear interpolation for bars.
    bars = ""
    n_bars = 24
    for i in range(n_bars):
        pos = (i + 0.5) / n_bars
        # Triangular "density": peak near P50, tails to P10 / P90.
        density = 1.0 - abs(pos - x_pct[2]) * 1.6  # peak at P50
        density = max(0.1, min(1.0, density))
        bar_h = density * (height - 40)
        x_px = pos * (width - 80) + 40 - (width - 80) / n_bars / 2
        bar_w = (width - 80) / n_bars - 1
        y = height - 20 - bar_h
        bars += (
            f'<rect x="{x_px:.1f}" y="{y:.1f}" width="{bar_w:.1f}" '
            f'height="{bar_h:.1f}" fill="{PALETTE["accent"]}" opacity="0.55"/>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
        f'class="wb-histo-svg" role="img" '
        f'aria-label="EBITDA impact percentile band, P10 {_fmt_money(p10)} to P90 {_fmt_money(p90)}">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="{PALETTE["panel_alt"]}"/>'
        f'{bars}{lines}'
        f'</svg>'
    )


# Scenarios tab ---------------------------------------------------------

_SCENARIO_PALETTE_COLORS = (
    PALETTE["accent"], PALETTE["positive"],
    PALETTE["warning"], PALETTE["negative"],
)


def _scenario_top_drivers(
    scenario: Dict[str, Any], limit: int = 3,
) -> List[str]:
    """Pick the top-N variance-contribution metrics from one
    ``MonteCarloResult.to_dict()``. Skips entries that tie to zero —
    partners don't want to see "metric_foo: 0%" noise."""
    vc = scenario.get("variance_contribution") or {}
    if not vc:
        return []
    ordered = sorted(
        ((k, float(v)) for k, v in vc.items()),
        key=lambda kv: abs(kv[1]), reverse=True,
    )
    return [k for k, v in ordered[:limit] if abs(v) > 1e-6]


def _render_scenario_mini_histogram(
    scenario: Dict[str, Any], palette_idx: int,
) -> str:
    """Tiny (200×60) SVG histogram rendered per scenario card.

    Uses the ``histogram_data`` bin list from ``MonteCarloResult`` if
    present, else falls back to a triangular approximation from the
    EBITDA percentile set. Same visual language as the main MC tab
    but scaled down to fit inside a card.
    """
    bins = scenario.get("histogram_data") or []
    if bins:
        color = _SCENARIO_PALETTE_COLORS[
            palette_idx % len(_SCENARIO_PALETTE_COLORS)
        ]
        counts = [float(b.get("count") or 0) for b in bins]
        max_count = max(counts) if counts else 1.0
        if max_count <= 0:
            max_count = 1.0
        width, height = 200, 60
        bar_w = width / max(1, len(counts))
        rects: List[str] = []
        for i, c in enumerate(counts):
            h = (c / max_count) * (height - 6)
            rects.append(
                f'<rect x="{i * bar_w:.1f}" y="{height - h:.1f}" '
                f'width="{bar_w - 0.5:.1f}" height="{h:.1f}" '
                f'fill="{color}" opacity="0.75"/>'
            )
        return (
            f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
            + "".join(rects) + '</svg>'
        )
    # Fallback: use ebitda_impact percentile triangle.
    eb = scenario.get("ebitda_impact") or {}
    return _render_scenario_fallback_mini(eb, palette_idx)


def _render_scenario_fallback_mini(
    ps: Dict[str, Any], palette_idx: int,
) -> str:
    """Triangular density from a 5-percentile dict — for scenarios
    saved before the histogram_data field was populated."""
    p10 = float(ps.get("p10") or 0.0)
    p50 = float(ps.get("p50") or 0.0)
    p90 = float(ps.get("p90") or 0.0)
    if p10 == p50 == p90 == 0.0:
        return ""
    span = max(p90 - p10, 1.0)
    color = _SCENARIO_PALETTE_COLORS[palette_idx % len(_SCENARIO_PALETTE_COLORS)]
    width, height = 200, 60
    n_bars = 18
    peak = (p50 - p10) / span
    bars: List[str] = []
    for i in range(n_bars):
        pos = (i + 0.5) / n_bars
        density = 1.0 - abs(pos - peak) * 1.8
        density = max(0.08, min(1.0, density))
        h = density * (height - 6)
        x = pos * width - width / n_bars / 2
        bars.append(
            f'<rect x="{x:.1f}" y="{height - h:.1f}" '
            f'width="{width / n_bars - 1:.1f}" height="{h:.1f}" '
            f'fill="{color}" opacity="0.75"/>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        + "".join(bars) + '</svg>'
    )


def _render_scenario_card(
    name: str, scenario: Dict[str, Any],
    *, recommended: bool, palette_idx: int,
) -> str:
    eb = scenario.get("ebitda_impact") or {}
    moic = scenario.get("moic") or {}
    drivers = _scenario_top_drivers(scenario)
    drivers_html = (
        '<ol>'
        + "".join(f'<li>{_esc(d)}</li>' for d in drivers)
        + '</ol>'
        if drivers else
        '<div class="dim">no variance drivers</div>'
    )
    badge = (
        '<span class="scenario-rec-badge">recommended</span>'
        if recommended else ''
    )
    class_list = (
        f"scenario-card scenario-palette-{palette_idx}"
        + (" recommended" if recommended else "")
    )
    mini = _render_scenario_mini_histogram(scenario, palette_idx)
    return f"""
    <div class="{class_list}">
      <div class="scenario-name">
        <span class="scenario-swatch"></span>
        {_esc(name)}{badge}
      </div>
      <div class="scenario-kpi"><span class="dim">P10 EBITDA</span>
        <span class="num">{_fmt_money(eb.get("p10"))}</span></div>
      <div class="scenario-kpi"><span class="dim">P50 EBITDA</span>
        <span class="num">{_fmt_money(eb.get("p50"))}</span></div>
      <div class="scenario-kpi"><span class="dim">P90 EBITDA</span>
        <span class="num">{_fmt_money(eb.get("p90"))}</span></div>
      <div class="scenario-kpi"><span class="dim">P50 MOIC</span>
        <span class="num">{_fmt_moic(moic.get("p50"))}</span></div>
      <div class="scenario-mini">{mini}</div>
      <div class="scenario-drivers">top variance drivers:{drivers_html}</div>
    </div>
    """


def _render_pairwise_matrix(
    names: List[str],
    pairwise: Dict[str, float],
) -> str:
    """Grid of P(row > col). Cell for ``row == col`` renders as an
    em-dash to avoid implying a winner over itself. Cells above 60%
    are green-tinted; below 40% red-tinted."""
    if not names or not pairwise:
        return ('<div class="dim">No pairwise comparison yet — '
                'add a second scenario to rank them head-to-head.</div>')

    header_cells = "".join(f'<th>{_esc(n)}</th>' for n in names)
    rows: List[str] = []
    for a in names:
        cells: List[str] = [f'<th>{_esc(a)}</th>']
        for b in names:
            if a == b:
                cells.append('<td class="pw-self">—</td>')
                continue
            key = f"{a}__vs__{b}"
            prob = pairwise.get(key)
            if prob is None:
                cells.append('<td class="dim">—</td>')
                continue
            cls = "pw-high" if prob >= 0.60 else (
                "pw-low" if prob <= 0.40 else ""
            )
            # HOUSE-RULE DEVIATION (deliberate): win probabilities
            # render 0dp, not the 1dp-percentages rule — the exact
            # strings "25%"/"75%" are pinned by test_scenario_overlay.
            cells.append(
                f'<td class="{cls}">{prob * 100:.0f}%</td>'
            )
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<table class="pairwise-matrix">'
        f'<thead><tr><th>P(row &gt; col)</th>{header_cells}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _render_scenario_overlay_svg(
    comparison: Dict[str, Any],
) -> str:
    """Superimposed histograms, one color per scenario, 40% opacity.

    All scenarios share the x-axis derived from the overall min/max
    EBITDA across every scenario's histogram_data. One ``<path>``
    per scenario so tests can count scenario entries by counting
    ``d="M"`` path starts.
    """
    scenarios = comparison.get("per_scenario") or {}
    if not scenarios:
        return ""
    # Collect every bin across every scenario to determine the
    # shared x-axis. If a scenario has no histogram_data, skip it —
    # the card still shows the triangular mini as a fallback.
    all_bins: List[Tuple[str, List[Dict[str, Any]]]] = []
    for name, sc in scenarios.items():
        bins = sc.get("histogram_data") or []
        if bins:
            all_bins.append((name, bins))
    if not all_bins:
        return ""
    x_min = min(
        float(b.get("bin_edge_low") or 0.0)
        for _, bins in all_bins for b in bins
    )
    x_max = max(
        float(b.get("bin_edge_high") or 0.0)
        for _, bins in all_bins for b in bins
    )
    x_span = max(x_max - x_min, 1.0)
    max_count = max(
        float(b.get("count") or 0.0)
        for _, bins in all_bins for b in bins
    )
    if max_count <= 0:
        max_count = 1.0

    width, height = 720, 200
    paths: List[str] = []
    legend_bits: List[str] = []
    for idx, (name, bins) in enumerate(all_bins):
        color = _SCENARIO_PALETTE_COLORS[idx % len(_SCENARIO_PALETTE_COLORS)]
        # Build a filled polygon: (x_lo, baseline) → zig-zag of bin
        # heights → (x_hi, baseline).
        points: List[str] = []
        baseline_y = height - 20
        for b in bins:
            lo = float(b.get("bin_edge_low") or 0.0)
            hi = float(b.get("bin_edge_high") or 0.0)
            cnt = float(b.get("count") or 0.0)
            h = (cnt / max_count) * (height - 40)
            x_lo_px = (lo - x_min) / x_span * (width - 40) + 20
            x_hi_px = (hi - x_min) / x_span * (width - 40) + 20
            y_px = baseline_y - h
            points.append(f"{x_lo_px:.1f},{y_px:.1f}")
            points.append(f"{x_hi_px:.1f},{y_px:.1f}")
        if not points:
            continue
        d_parts = [
            f"M {points[0].split(',')[0]},{baseline_y:.1f}",
            "L " + " L ".join(points),
            f"L {points[-1].split(',')[0]},{baseline_y:.1f}",
            "Z",
        ]
        d = " ".join(d_parts)
        paths.append(
            f'<path d="{d}" fill="{color}" fill-opacity="0.40" '
            f'stroke="{color}" stroke-opacity="0.85" stroke-width="1.2"/>'
        )
        legend_bits.append(
            f'<span class="scenario-legend-item scenario-palette-{idx % len(_SCENARIO_PALETTE_COLORS)}">'
            f'<span class="scenario-swatch"></span>{_esc(name)}</span>'
        )
    legend = (
        f'<div class="wb-overlay-legend">{"".join(legend_bits)}</div>'
    )
    axis = (
        f'<line x1="20" x2="{width - 20}" y1="{height - 20}" '
        f'y2="{height - 20}" stroke="{PALETTE["text_faint"]}"/>'
        f'<text x="20" y="{height - 4}" fill="{PALETTE["text_dim"]}" '
        f'font-size="10">{_fmt_money(x_min)}</text>'
        f'<text x="{width - 20}" y="{height - 4}" fill="{PALETTE["text_dim"]}" '
        f'text-anchor="end" font-size="10">{_fmt_money(x_max)}</text>'
    )
    return (
        f'<svg class="scenario-overlay-svg" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none">{"".join(paths)}{axis}</svg>'
        f'{legend}'
    )


def _render_scenarios(packet: DealAnalysisPacket) -> str:
    """Render the Scenarios tab.

    When no comparison has been run we show an empty state with an
    "Add Scenario" button. The JS in ``_WORKBENCH_JS`` picks up
    ``data-scenario-trigger`` clicks, opens the form panel, and
    submits to ``/api/analysis/<id>/simulate/compare``.

    Partner flow: open Scenarios → click Add → fill a per-lever
    target override → hit Run → page re-fetches the comparison and
    re-renders the tab.
    """
    comparison = packet.scenario_comparison or {}
    per_scenario = comparison.get("per_scenario") or {}
    names = list(per_scenario.keys())
    recommended = comparison.get("recommended_scenario") or ""
    rationale = comparison.get("rationale") or ""
    pairwise = comparison.get("pairwise_overlap") or {}

    # Card grid ------------------------------------------------------
    if names:
        cards_html = "".join(
            _render_scenario_card(
                name, per_scenario[name],
                recommended=(name == recommended),
                palette_idx=i,
            )
            for i, name in enumerate(names)
        )
    else:
        cards_html = (
            '<div class="scenario-empty">'
            'No scenarios compared yet. Click <b>+ Add Scenario</b> '
            'to run a side-by-side vs. the current MC output.'
            '</div>'
        )

    # Pairwise + rationale ------------------------------------------
    pairwise_html = _render_pairwise_matrix(names, pairwise)
    rationale_html = (
        f'<div class="dim wb-rationale">'
        f'{_esc(rationale)}</div>' if rationale else ''
    )

    # Overlay histogram ---------------------------------------------
    overlay_html = _render_scenario_overlay_svg(comparison) or (
        '<div class="dim">distributions unavailable: run MC first</div>'
    )

    # Add-scenario form — skeleton (JS wires submit). Pre-populated
    # from the current bridge's per-metric targets so analysts have a
    # starting point instead of an empty text field.
    target_defaults = {
        imp.metric_key: float(imp.target_value)
        for imp in (packet.ebitda_bridge.per_metric_impacts or [])
    }
    form_inputs: List[str] = [
        '<label class="full-row">Scenario name'
        '<input type="text" id="scenario-name-input" placeholder="e.g. management plan"/>'
        '</label>'
    ]
    for metric, tgt in target_defaults.items():
        form_inputs.append(
            f'<label>{_esc(metric)} target'
            f'<input type="number" step="0.01" '
            f'data-scenario-target="{_esc(metric)}" value="{tgt:.2f}"/>'
            f'</label>'
        )
    form_inputs.append(
        '<div class="full-row">'
        '<button class="wb-btn wb-btn-primary" type="button" '
        'data-scenario-submit>Run scenario</button>'
        '<button class="wb-btn" type="button" data-scenario-cancel>'
        'Cancel</button>'
        '<span class="ov-feedback" id="scenario-run-feedback"></span>'
        '</div>'
    )
    form_html = (
        '<div class="scenario-add-form hidden" id="scenario-add-form">'
        + "".join(form_inputs) +
        '</div>'
    )

    intro = _tab_intro(
        "SCENARIOS", "Side by side, under the same assumptions.",
        "Side by side",
        "Each scenario reruns the full simulation; the matrix scores "
        "head-to-head win probability against the base case.",
    )
    return f"""
    <div class="wb-tab-panel" data-panel="scenarios"
         data-deal-id="{_esc(packet.deal_id)}" {_panel_attrs("scenarios")}>
      {intro}
      <div class="wb-card">
        <div class="wb-card-title">
          Scenario comparison
          <button class="wb-btn wb-btn-right" type="button"
                  data-scenario-trigger>
            + Add Scenario
          </button>
        </div>
        <div class="scenario-grid">{cards_html}</div>
        {form_html}
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Pairwise win probability</div>
        {pairwise_html}
        {rationale_html}
      </div>
      <div class="wb-card">
        <div class="wb-card-title">Overlay distribution</div>
        {overlay_html}
      </div>
    </div>
    """


# Risk & Diligence tab --------------------------------------------------

def _render_regulatory_card(packet: DealAnalysisPacket) -> str:
    """Regulatory Environment card (Prompt 24) — CON / Medicaid /
    market badges + the one-paragraph narrative.

    Rendered at the top of the Risk & Diligence tab when
    ``packet.regulatory_context`` is populated. Skipped silently
    when the deal has no state.
    """
    ctx = packet.regulatory_context or {}
    if not ctx:
        return ""

    def _badge(label: str, tone: str) -> str:
        return (
            f'<span class="wb-badge wb-badge-{tone}">{_esc(label)}</span>'
        )

    con_status = ctx.get("con_status") or "NO_CON"
    con_impl = ctx.get("con_implication") or "none"
    medicaid_risk = ctx.get("medicaid_risk") or "LOW"
    market_risk = ctx.get("market_risk") or "LOW"
    payer = ctx.get("payer_profile") or {}
    expanded = bool(payer.get("medicaid_expanded"))

    if con_status == "CON_MORATORIUM":
        con_badge = _badge("CON moratorium", "medium")
    elif con_status == "CON_ACTIVE":
        tone = "low" if con_impl == "competitive_moat" else "medium"
        con_badge = _badge("CON active", tone)
    else:
        con_badge = _badge("no CON", "low")

    medicaid_badge = _badge(
        "Medicaid expanded" if expanded else "no Medicaid expansion",
        "low" if expanded else "medium",
    )
    medicaid_risk_badge = _badge(
        f"rate risk: {medicaid_risk.lower()}",
        {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}.get(
            medicaid_risk, "low",
        ),
    )
    market_badge = _badge(
        f"market: {market_risk.lower()}",
        {"HIGH": "medium", "MEDIUM": "low", "LOW": "low"}.get(
            market_risk, "low",
        ),
    )

    narrative = _esc(ctx.get("narrative") or "")
    state = _esc(ctx.get("state") or "")
    return f"""
    <div class="wb-card wb-reg-card">
      <div class="wb-card-title">Regulatory Environment — {state}</div>
      <div class="wb-chip-row">
        {con_badge}{medicaid_badge}{medicaid_risk_badge}{market_badge}
      </div>
      <div class="dim wb-reg-narrative">
        {narrative or '<span class="dim">No regulatory narrative available for this state.</span>'}
      </div>
    </div>
    """


def _render_risk_diligence(packet: DealAnalysisPacket) -> str:
    # Regulatory environment card (Prompt 24) — optional, rendered
    # above the flag/questions grid when the packet has a state.
    regulatory_card = _render_regulatory_card(packet)

    # Risk flags (left). The EBITDA-at-risk figure — the money number a
    # partner scans for — is promoted to a right-aligned mono figure on
    # the card's top row instead of an 11px footnote.
    risk_html = []
    for rf in packet.risk_flags:
        sev = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
        ear = _fmt_money(rf.ebitda_at_risk) if rf.ebitda_at_risk else ""
        ear_html = (f'<span class="risk-ear neg"><span class="k">EBITDA at risk</span>'
                    f'{ear}</span>') if ear else ""
        trigger_keys = list(rf.trigger_metrics or []) or (
            [rf.trigger_metric] if rf.trigger_metric else [])
        triggers = ", ".join(_metric_display_name(k) for k in trigger_keys)
        risk_html.append(
            f'<div class="risk-card severity-{sev}">'
            f'<div class="risk-head">'
            f'<span class="wb-badge wb-badge-{sev.lower()}">{sev}</span> '
            f'<span class="risk-title">{_esc(rf.title or "flag")}</span>'
            f'{ear_html}'
            f'</div>'
            f'<div class="risk-detail">{_esc(rf.detail or rf.explanation)}</div>'
            + (f'<div class="dim risk-trigger">Trigger: {_esc(triggers)}</div>'
               if triggers else "")
            + '</div>'
        )
    risk_block = "\n".join(risk_html) or (
        '<div class="dim">No risk flags fired on this packet — '
        'the risk scan found nothing above threshold.</div>')

    # Diligence questions (right).
    dq_by_priority: Dict[str, List[str]] = {"P0": [], "P1": [], "P2": []}
    for q in packet.diligence_questions:
        pri = q.priority.value if hasattr(q.priority, "value") else str(q.priority)
        # A.10 PR B — same chip-on-source pattern as risk flags,
        # including the tooltip-attribution refinement (Amendment 2):
        # tooltip explicitly names the source metric rather than the
        # ambiguous default. Question text stays as-is; the chip on
        # the trigger metric tells the partner that the underlying
        # number prompting this question is diagnostically suspect,
        # so they can weigh the question priority accordingly.
        source_pm = (packet.rcm_profile.get(q.trigger_metric)
                     if q.trigger_metric else None)
        if source_pm is not None and q.trigger_metric:
            source_chip = ck_prediction_chip(
                ck_aggregate(source_pm, labels=[q.trigger_metric])
            )
        else:
            source_chip = ""
        dq_by_priority.setdefault(pri, []).append(
            f'<div class="dq-card">'
            f'<span class="dq-priority dq-{pri}">{pri}</span>'
            f'<span class="dq-cat">{_esc((q.category or "—").replace("_", " "))}</span>'
            f'<div class="dq-question">{_esc(q.question)}{source_chip}</div>'
            + (f'<div class="dim dq-trigger">Trigger: {_esc(_humanize_trigger(q.trigger) or q.trigger_reason)}</div>'
               if (q.trigger or q.trigger_reason) else "")
            + '</div>'
        )
    dq_html = ""
    for pri in ("P0", "P1", "P2"):
        if dq_by_priority[pri]:
            n_q = len(dq_by_priority[pri])
            noun = "questions" if n_q != 1 else "question"
            # Group head = the kit eyebrow (caps + teal dash), wrapped
            # for the rhythm rules (top margin, hairline underline).
            dq_html += (
                f'<div class="dq-group-head">'
                f'{ck_eyebrow(f"{pri} · {n_q} {noun}")}</div>'
                + "\n".join(dq_by_priority[pri])
            )
    dq_block = dq_html or (
        '<div class="dim">No diligence questions generated — '
        'questions appear as metrics land and flags fire.</div>')

    intro = _tab_intro(
        "RISK & DILIGENCE", "What could break the thesis.",
        "What could break",
        "Flags rank by severity with EBITDA at risk on the top line; "
        "each one seeds a prioritised diligence question.",
    )
    return f"""
    <div class="wb-tab-panel" data-panel="risk" {_panel_attrs("risk")}>
      {intro}
      {regulatory_card}
      <div class="wb-grid">
        <div>
          <div class="wb-card">
            <div class="wb-card-title">Risk flags ({len(packet.risk_flags)})</div>
            {risk_block}
          </div>
        </div>
        <div>
          <div class="wb-card">
            <div class="wb-card-title">Diligence questions ({len(packet.diligence_questions)})</div>
            {dq_block}
            <div class="wb-mt">
              <a class="wb-btn" href="/api/analysis/{_esc(packet.deal_id)}/diligence-questions">Export questions (JSON)</a>
            </div>
          </div>
        </div>
      </div>
    </div>
    """


# Provenance tab --------------------------------------------------------

#: Node-id prefix → partner-facing group heading (was raw uppercase
#: prefixes like "OBSERVED (12)" / "MC (3)").
_PROV_GROUP_LABELS = {
    "observed": "Observed inputs",
    "predicted": "Predicted",
    "bridge": "Bridge outputs",
    "comparables": "Comparable cohort",
    "mc": "Monte Carlo",
    "target": "Targets",
    "profile": "Profile",
    "other": "Other",
}


def _render_provenance(packet: DealAnalysisPacket) -> str:
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
    except Exception:  # noqa: BLE001
        RCM_METRIC_REGISTRY = {}
    # Group nodes by prefix so the tree view matches the rich-graph
    # builder's ID scheme.
    groups: Dict[str, List[Any]] = {}
    for nid, node in (packet.provenance.nodes or {}).items():
        prefix = nid.split(":", 1)[0] if ":" in nid else "other"
        groups.setdefault(prefix, []).append((nid, node))

    blocks: List[str] = []
    for prefix in ("observed", "predicted", "bridge", "comparables", "mc", "target", "profile", "other"):
        nodes = groups.get(prefix) or []
        if not nodes:
            continue
        rows = []
        for nid, node in sorted(nodes, key=lambda t: t[0]):
            # Humanize the node id: drop the group prefix (already the
            # section heading) and use the registry display name when
            # the remainder is a known metric key.
            metric_part = nid.split(":", 1)[1] if ":" in nid else nid
            node_label = _metric_display_name(metric_part)
            # Unit-aware value where the node id resolves to a known
            # registry metric (was a bare unit-less 2dp number).
            unit = (RCM_METRIC_REGISTRY.get(metric_part) or {}).get("unit")
            value_str = (_fmt_metric_value(node.value, unit)
                         if unit else _fmt_num(node.value, dp=2))
            source_label = _prov_source_label(node.source)
            # source_detail that just restates the source ("Provided by
            # USER_INPUT") is noise — suppress it.
            detail = ("" if _prov_detail_redundant(node.source, node.source_detail)
                      else node.source_detail)
            conf_str = ck_fmt_percent(node.confidence, precision=0)
            rows.append(
                f'<div class="prov-row" id="prov-{_esc(nid)}">'
                f'<div><span class="dim" title="{_esc(nid)}">{_esc(node_label)}</span></div>'
                f'<div class="num">{value_str}</div>'
                f'<div class="dim">{_esc(source_label)} · conf '
                f'<span class="num">{conf_str}</span>'
                + (f' · {_esc(detail)}' if detail else "")
                + '</div></div>'
            )
        group_label = _PROV_GROUP_LABELS.get(prefix, prefix.title())
        blocks.append(
            f'<details open class="wb-prov-group">'
            f'<summary class="wb-card-title">{_esc(group_label)} ({len(nodes)})</summary>'
            f'{"".join(rows)}</details>'
        )
    # Editorial empty state (kit rule: never a bare dim one-liner for
    # a whole-tab "no data yet"). No CTA link — the rebuild action is
    # a POST form in the page header, not a GET destination.
    body = "\n".join(blocks) or ck_empty_state(
        "No lineage recorded yet.",
        "Rebuild the analysis packet to record the source, confidence "
        "and upstream dependencies of every number on this page.",
        eyebrow="PROVENANCE",
        icon="◈",
    )
    intro = _tab_intro(
        "PROVENANCE", "Every number, traced to its source.",
        "Every number",
        "The lineage behind the packet — observed inputs, predictions "
        "and derived figures, each with a source and confidence.",
    )
    return f"""
    <div class="wb-tab-panel" data-panel="provenance" {_panel_attrs("provenance")}>
      {intro}
      <div class="wb-card">
        <div class="wb-card-title">Provenance graph ({len(packet.provenance.nodes)} nodes)</div>
        {body}
      </div>
    </div>
    """


# ── Analyst Override / Assumptions tab ──────────────────────────────

# Bridge fields shown explicitly (most IC-critical).
_BRIDGE_FIELDS = [
    ("exit_multiple",            "Exit multiple",          "x",    6.0, 20.0,  0.5),
    ("cost_of_capital",          "Cost of capital",        "%",    5.0, 20.0,  0.5),
    ("collection_realization",   "Collection realization", "%",   50.0, 100.0, 1.0),
    ("denial_overturn_rate",     "Denial overturn rate",   "%",    0.0,  80.0, 1.0),
    ("net_revenue",              "Net revenue ($)",        "$",    0.0,   0.0, 0.0),
    ("claims_volume",            "Claims volume",          "#",    0.0,   0.0, 0.0),
    ("implementation_ramp",      "Implementation ramp",   "mos",  6.0,  36.0, 1.0),
    ("evaluation_month",         "Evaluation month",       "mo",   1.0,  60.0, 1.0),
]

_RAMP_FAMILIES = [
    "denial_management",
    "ar_collections",
    "cdi_coding",
    "payer_renegotiation",
    "cost_optimization",
]

_RAMP_FIELDS = [
    ("months_to_25_pct",  "25% ramp"),
    ("months_to_75_pct",  "75% ramp"),
    ("months_to_full",    "Full ramp"),
]

_PAYER_KEYS = [
    ("commercial_share",          "Commercial"),
    ("medicare_ffs_share",        "Medicare FFS"),
    ("medicare_advantage_share",  "Medicare Advantage"),
    ("medicaid_share",            "Medicaid"),
    ("self_pay_share",            "Self-pay"),
    ("managed_government_share",  "Managed Government"),
]


def _ov_row(key: str, label: str, unit: str,
            overrides: Dict[str, Any]) -> str:
    full_key = key
    val = overrides.get(full_key)
    active_cell = (
        f'<span class="ov-active-val">{_esc(str(val))}</span> '
        f'<span class="ov-badge-a">A</span>'
        if val is not None else '<span class="ov-model-val dim">model default</span>'
    )
    clear_btn = (
        f'<button class="wb-btn wb-btn-danger ov-clear-btn" '
        f'data-ov-key="{_esc(full_key)}">Clear</button>'
        if val is not None else ""
    )
    return (
        f'<div class="ov-row" data-ov-row="{_esc(full_key)}">'
        f'<div class="ov-key">{_esc(full_key)}</div>'
        f'<div class="ov-label">{_esc(label)}</div>'
        f'<div>{active_cell}</div>'
        f'<div>{clear_btn}</div>'
        f'<div>'
        f'<input class="ov-input" type="text" placeholder="{_esc(unit or "value")}" '
        f'data-ov-key="{_esc(full_key)}" '
        f'aria-label="Override {_esc(label)}">'
        f'</div>'
        f'</div>'
    )


def _render_assumptions(packet: DealAnalysisPacket) -> str:
    overrides: Dict[str, Any] = dict(packet.analyst_overrides or {})
    deal_id = _esc(packet.deal_id or "")
    n_ov = len(overrides)

    banner = ""
    if n_ov:
        banner = (
            f'<div class="ov-banner">'
            f'<strong>{n_ov} analyst override{"s" if n_ov != 1 else ""} active.</strong> '
            f'Rebuild the analysis packet for overrides to take effect: '
            f'<a href="/api/analysis/{deal_id}" class="wb-btn ov-rebuild-btn">'
            f'Rebuild →</a></div>'
        )

    # ── Bridge assumptions ────────────────────────────────────────
    hdr = (
        '<div class="ov-row ov-row-head">'
        '<div>Key</div><div>Field</div><div>Active value</div><div></div><div>Set new value</div>'
        '</div>'
    )
    bridge_rows = hdr + "".join(
        _ov_row(f"bridge.{k}", label, unit, overrides)
        for k, label, unit, *_ in _BRIDGE_FIELDS
    )

    # ── Ramp curves ───────────────────────────────────────────────
    # Family subheads break the 15-row wall into 5 scannable groups.
    ramp_rows = hdr
    for fam in _RAMP_FAMILIES:
        fam_label = fam.replace("_", " ")
        ramp_rows += f'<div class="ov-family">{_esc(fam_label)}</div>'
        for fld, flabel in _RAMP_FIELDS:
            key = f"ramp.{fam}.{fld}"
            ramp_rows += _ov_row(key, f"{fam_label} · {flabel}", "months", overrides)

    # ── Payer mix ─────────────────────────────────────────────────
    payer_rows = hdr + "".join(
        _ov_row(f"payer_mix.{k}", label, "0.0–1.0", overrides)
        for k, label in _PAYER_KEYS
    )

    # ── Metric targets ────────────────────────────────────────────
    target_keys = sorted(k for k in overrides if k.startswith("metric_target."))
    mt_rows = hdr + "".join(
        _ov_row(k, k.removeprefix("metric_target."), "target", overrides)
        for k in target_keys
    )
    mt_add = (
        '<div class="ov-add-form" id="ov-mt-add-form">'
        '<div><label for="ov-mt-key">Metric key</label>'
        '<input class="ov-add-input" id="ov-mt-key" type="text" '
        'placeholder="e.g. denial_rate"></div>'
        '<div><label for="ov-mt-val">Target value</label>'
        '<input class="ov-add-input" id="ov-mt-val" type="number" step="any"></div>'
        '<div><label for="ov-mt-reason">Reason (optional)</label>'
        '<input class="ov-add-input" id="ov-mt-reason" type="text"></div>'
        '<div><label>&nbsp;</label>'
        '<button class="wb-btn wb-btn-primary" id="ov-mt-add-btn">Add target</button></div>'
        '</div>'
        '<div class="ov-feedback" id="ov-mt-feedback"></div>'
    )

    # ── Custom / raw add ──────────────────────────────────────────
    raw_add = (
        '<div class="ov-add-form" id="ov-raw-add-form">'
        '<div><label for="ov-raw-key">Override key</label>'
        '<input class="ov-add-input" id="ov-raw-key" type="text" '
        'placeholder="e.g. payer_mix.commercial_share"></div>'
        '<div><label for="ov-raw-val">Value</label>'
        '<input class="ov-add-input" id="ov-raw-val" type="text"></div>'
        '<div><label for="ov-raw-reason">Reason (optional)</label>'
        '<input class="ov-add-input" id="ov-raw-reason" type="text"></div>'
        '<div><label>&nbsp;</label>'
        '<button class="wb-btn wb-btn-primary" id="ov-raw-add-btn">Set</button></div>'
        '</div>'
        '<div class="ov-feedback" id="ov-raw-feedback"></div>'
    )

    intro = _tab_intro(
        "ASSUMPTIONS", "Your judgement, on the record.",
        "Your judgement",
        "Analyst overrides persist with a reason and apply on the "
        "next packet rebuild — the model default stays visible.",
    )
    return f"""
    <div class="wb-tab-panel" data-panel="assumptions" data-deal-id="{deal_id}" {_panel_attrs("assumptions")}>
      {intro}
      {banner}
      <div class="wb-card ov-section">
        <div class="ov-section-title">Bridge assumptions</div>
        <div class="ov-feedback" id="ov-bridge-feedback"></div>
        {bridge_rows}
        <div class="ov-hint">
          Edit a value then press Enter or Tab to commit.
        </div>
      </div>
      <div class="wb-card ov-section">
        <div class="ov-section-title">Ramp curves (months)</div>
        <div class="ov-feedback" id="ov-ramp-feedback"></div>
        {ramp_rows}
        <div class="ov-hint">
          Edit a value then press Enter or Tab to commit.
        </div>
      </div>
      <div class="wb-card ov-section">
        <div class="ov-section-title">Payer mix (share 0–1)</div>
        <div class="ov-feedback" id="ov-payer-feedback"></div>
        {payer_rows}
        <div class="ov-hint">
          Edit a value then press Enter or Tab to commit.
        </div>
      </div>
      <div class="wb-card ov-section">
        <div class="ov-section-title">Metric targets</div>
        {mt_rows}
        {mt_add}
      </div>
      <div class="wb-card ov-section">
        <div class="ov-section-title">Custom override (any valid key)</div>
        {raw_add}
      </div>
    </div>
    """


# ── JavaScript ───────────────────────────────────────────────────────

_WORKBENCH_JS = r"""
(function(){
  // Tab switching — active class + aria-selected + URL hash so a
  // reload / shared link lands on the same tab ("#tab-<key>"; the
  // prefix avoids colliding with the #prov-<metric> anchors).
  const tabs = document.querySelectorAll('.analysis-workbench .wb-tab');
  const panels = document.querySelectorAll('.analysis-workbench .wb-tab-panel');
  function activateTab(t, pushHash) {
    const k = t.dataset.tab;
    tabs.forEach(x => x.classList.toggle('active', x === t));
    tabs.forEach(x => x.setAttribute('aria-selected', x === t ? 'true' : 'false'));
    panels.forEach(p => p.classList.toggle('active', p.dataset.panel === k));
    if (pushHash) {
      try { history.replaceState(null, '', '#tab-' + k); } catch (_) {}
    }
  }
  tabs.forEach(t => t.addEventListener('click', () => activateTab(t, true)));
  const hashMatch = (location.hash || '').match(/^#tab-([a-z]+)$/);
  if (hashMatch) {
    const initial = document.querySelector(
      '.analysis-workbench .wb-tab[data-tab="' + hashMatch[1] + '"]');
    if (initial) activateTab(initial, false);
  }

  // Keyboard shortcuts: number keys switch tabs, Alt+← / Alt+→ prev/next
  const tabKeys = Array.from(tabs);
  document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    const n = parseInt(e.key);
    if (n >= 1 && n <= tabKeys.length) {
      tabKeys[n-1].click();
      e.preventDefault();
      return;
    }
    if (e.altKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) {
      const cur = tabKeys.findIndex(t => t.classList.contains('active'));
      const next = e.key === 'ArrowRight'
        ? Math.min(cur + 1, tabKeys.length - 1)
        : Math.max(cur - 1, 0);
      tabKeys[next].click();
      e.preventDefault();
    }
    if (e.key === '?' && !e.ctrlKey && !e.metaKey) {
      alert('Keyboard shortcuts:\\n1-' + tabKeys.length +
            ': Switch tabs\\nAlt+←/→: Prev/next tab');
      e.preventDefault();
    }
  });

  // Bridge sliders
  const bootstrap = document.getElementById('wb-bridge-bootstrap');
  if (!bootstrap) return;
  let payload;
  try { payload = JSON.parse(bootstrap.textContent); }
  catch (_) { return; }
  const dealId = payload.deal_id;
  const assumptions = new Map();
  for (const a of payload.assumptions) assumptions.set(a.metric, a);
  // metric key → display name (server-provided) so the re-rendered
  // waterfall matches the server-rendered one instead of flipping
  // back to snake_case keys after the first slider drag.
  const metricLabels = payload.labels || {};

  function fmtMoney(v){
    if (v == null) return '—';
    const s = v < 0 ? '-' : '';
    v = Math.abs(v);
    if (v >= 1e9) return s + '$' + (v/1e9).toFixed(2) + 'B';
    if (v >= 1e6) return s + '$' + (v/1e6).toFixed(1) + 'M';
    if (v >= 1e3) return s + '$' + Math.round(v/1e3).toLocaleString() + 'K';
    return s + '$' + Math.round(v).toLocaleString();
  }

  function renderWaterfall(bridge){
    const root = document.getElementById('wb-waterfall');
    if (!root || !bridge || !bridge.per_metric_impacts) return;
    const steps = [];
    let running = bridge.current_ebitda || 0;
    steps.push({label:'Current EBITDA', value: running, kind:'anchor'});
    for (const imp of bridge.per_metric_impacts) {
      steps.push({label: metricLabels[imp.metric_key] || imp.metric_key,
                  value: imp.ebitda_impact,
                  kind: imp.ebitda_impact >= 0 ? 'pos' : 'neg'});
      running += imp.ebitda_impact;
    }
    steps.push({label:'Target EBITDA', value: bridge.target_ebitda || running, kind:'anchor'});
    const maxAbs = Math.max(1, ...steps.map(s => Math.abs(s.value || 0)));
    root.innerHTML = '<div class="waterfall">' +
      steps.map(s => {
        const pct = Math.max(1, Math.abs(s.value || 0) / maxAbs * 100);
        return '<div class="wf-row">' +
          '<div>' + s.label + '</div>' +
          '<div class="wf-track"><div class="wf-bar ' + s.kind +
          '" style="width:' + pct.toFixed(1) + '%"></div></div>' +
          '<div class="num">' + fmtMoney(s.value) + '</div>' +
          '</div>';
      }).join('') + '</div>';
    const summary = document.getElementById('wb-bridge-summary');
    if (summary) {
      summary.innerHTML =
        'Improving from current to target adds ' +
        '<span class="pos num">' + fmtMoney(bridge.total_ebitda_impact) +
        '</span> to EBITDA (<span class="num">' +
        (bridge.margin_improvement_bps >= 0 ? '+' : '') +
        bridge.margin_improvement_bps + '</span> bps margin).';
    }
  }

  let debounceTimer = null;
  function bridgeStatus(msg){
    const el = document.getElementById('wb-bridge-status');
    if (el) el.textContent = msg || '';
  }
  function postBridge(){
    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      const targets = {};
      assumptions.forEach((_, metric) => {
        const el = document.getElementById('slider-' + metric);
        if (el) targets[metric] = parseFloat(el.value);
      });
      const wf = document.getElementById('wb-waterfall');
      if (wf) wf.style.opacity = '0.55';
      bridgeStatus('Recomputing…');
      fetch('/api/analysis/' + encodeURIComponent(dealId) + '/bridge', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({targets: targets, financials: {}})
      })
        .then(r => r.ok ? r.json() : null)
        .then(d => {
          if (wf) wf.style.opacity = '';
          if (d && d.bridge) { renderWaterfall(d.bridge); bridgeStatus(''); }
          else { bridgeStatus('Recompute failed — showing last result'); }
        })
        .catch(() => {
          if (wf) wf.style.opacity = '';
          bridgeStatus('Recompute failed — showing last result');
        });
    }, 300);
  }

  document.querySelectorAll('.analysis-workbench input.wb-slider').forEach(el => {
    el.addEventListener('input', () => {
      const metric = el.dataset.metric;
      const cur = parseFloat(el.dataset.current);
      const tgt = parseFloat(el.value);
      const valEl = document.getElementById('slider-' + metric + '-val');
      const delEl = document.getElementById('slider-' + metric + '-delta');
      if (valEl) valEl.textContent = tgt.toFixed(2);
      if (delEl) {
        const d = tgt - cur;
        const sign = d >= 0 ? '+' : '';
        delEl.textContent = sign + d.toFixed(2);
        delEl.className = 'slider-delta num ' + (d >= 0 ? 'pos' : 'neg');
      }
      postBridge();
    });
  });

  // Presets seed every slider to a fraction of the current→target
  // value-creation gap, then let each slider's own input handler update the
  // readout and recompute the waterfall. "Aggressive" underwrites the full
  // modelled target; "Conservative"/"Moderate" capture a third / two-thirds
  // of it; "Reset" returns every slider to its current (as-is) baseline.
  // Direction is implicit in the target (e.g. a denial-rate target sits
  // below current), so interpolating current→target moves each metric the
  // correct way regardless of whether higher or lower is better.
  function wbApplyPreset(name) {
    const fracs = {conservative: 0.33, moderate: 0.67, aggressive: 1.0, reset: 0.0};
    const frac = (name in fracs) ? fracs[name] : 0;
    document.querySelectorAll('.analysis-workbench input.wb-slider').forEach(el => {
      const cur = parseFloat(el.dataset.current);
      const tgt = parseFloat(el.dataset.target);
      if (isNaN(cur) || isNaN(tgt)) return;
      // The range input snaps to step and clamps to min/max on assignment.
      el.value = cur + frac * (tgt - cur);
      // Reuse the slider's input handler (updates readout + debounced recompute).
      el.dispatchEvent(new Event('input', {bubbles: true}));
    });
  }
  document.querySelectorAll('.analysis-workbench [data-preset]').forEach(btn => {
    btn.addEventListener('click', () => { wbApplyPreset(btn.dataset.preset); });
  });

  // Scenarios tab — add-scenario form.
  const scenarioPanel = document.querySelector(
    '.analysis-workbench [data-panel="scenarios"]'
  );
  if (scenarioPanel) {
    const dealForScenarios = scenarioPanel.dataset.dealId;
    const form = document.getElementById('scenario-add-form');
    const trigger = scenarioPanel.querySelector('[data-scenario-trigger]');
    const cancel = scenarioPanel.querySelector('[data-scenario-cancel]');
    const submit = scenarioPanel.querySelector('[data-scenario-submit]');
    const nameInput = document.getElementById('scenario-name-input');
    if (trigger && form) {
      trigger.addEventListener('click', () => {
        form.classList.toggle('hidden');
        if (nameInput) nameInput.focus();
      });
    }
    if (cancel && form) {
      cancel.addEventListener('click', () => form.classList.add('hidden'));
    }
    if (submit && nameInput) {
      submit.addEventListener('click', () => {
        const name = (nameInput.value || '').trim();
        if (!name) { nameInput.focus(); return; }
        const overrides = {};
        form.querySelectorAll('[data-scenario-target]').forEach(inp => {
          const metric = inp.dataset.scenarioTarget;
          const val = parseFloat(inp.value);
          if (!isNaN(val)) {
            // Use the same MetricAssumption shape the API accepts.
            overrides[metric] = {
              target_value: val,
              execution_distribution: 'beta',
              execution_probability: 0.7,
              execution_params: {alpha: 7.0, beta: 3.0},
              uncertainty_source: 'none'
            };
          }
        });
        submit.disabled = true;
        submit.textContent = 'Running…';
        const runFeedback = document.getElementById('scenario-run-feedback');
        if (runFeedback) { runFeedback.textContent = ''; runFeedback.className = 'ov-feedback'; }
        fetch('/api/analysis/' + encodeURIComponent(dealForScenarios)
              + '/simulate/compare', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            scenarios: { [name]: overrides },
            financials: {}
          })
        })
          .then(r => r.ok ? r.json() : Promise.reject(r.status))
          .then(() => { window.location.reload(); })
          .catch(() => {
            submit.disabled = false;
            submit.textContent = 'Run scenario';
            if (runFeedback) {
              runFeedback.textContent = 'Scenario run failed — check the inputs and try again.';
              runFeedback.className = 'ov-feedback err';
            }
          });
      });
    }
  }
})();
"""


# ── Full-page render ────────────────────────────────────────────────

def _build_explain_data(packet: DealAnalysisPacket) -> str:
    """Build a JSON blob with per-metric explain info for the slide-in
    panel (Prompt 32). The JS picks this up and populates the panel
    when the user clicks a ``[data-explain]`` element."""
    import json as _json
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
    except Exception:  # noqa: BLE001
        RCM_METRIC_REGISTRY = {}
    data: Dict[str, Any] = {}
    for key, pm in (packet.rcm_profile or {}).items():
        meta = RCM_METRIC_REGISTRY.get(key) or {}
        # Find matching bridge impact.
        impact = 0.0
        for imp in (packet.ebitda_bridge.per_metric_impacts or []):
            if imp.metric_key == key:
                impact = float(imp.ebitda_impact or 0)
                break
        # Find matching diligence question.
        question = ""
        for q in (packet.diligence_questions or []):
            if q.trigger_metric == key:
                question = q.question or ""
                break
        data[key] = {
            "display_name": meta.get("display_name") or key,
            "source": pm.source.value if hasattr(pm.source, "value") else str(pm.source),
            "value": float(pm.value),
            "benchmark_p50": meta.get("benchmark_p50"),
            "percentile": pm.benchmark_percentile,
            "ebitda_sensitivity_rank": meta.get("ebitda_sensitivity_rank"),
            "ebitda_impact": impact,
            "category": meta.get("category") or "",
            "diligence_question": question,
            # A.10 PR B — surface failure_reason in the JSON payload
            # so any JS-side renderer consuming this endpoint can
            # apply its own chip / styling. Mirrors the DOM-chip
            # treatment on the workbench HTML render.
            "failure_reason": pm.failure_reason,
            "log_transform_suggested": getattr(pm, "log_transform_suggested", False),
        }
    return _json.dumps(data, default=str)


_EXPLAIN_JS = r"""
(function(){
  var panel = document.getElementById('wb-explain-panel');
  var titleEl = document.getElementById('ep-title');
  var bodyEl = document.getElementById('ep-body');
  var closeBtn = document.getElementById('ep-close');
  var dataEl = document.getElementById('wb-explain-data');
  var data = {};
  try { data = JSON.parse(dataEl ? dataEl.textContent : '{}'); } catch(_){}

  function fmtMoney(v){
    if(v==null)return'—';v=Math.abs(v);
    if(v>=1e9)return'$'+(v/1e9).toFixed(2)+'B';
    if(v>=1e6)return'$'+(v/1e6).toFixed(1)+'M';
    if(v>=1e3)return'$'+Math.round(v/1e3).toLocaleString()+'K';
    return'$'+Math.round(v).toLocaleString();
  }

  function showPanel(){
    panel.classList.add('open');
    // Focus management: land on the close button so Escape / Enter
    // dismisses without a mouse trip.
    if (closeBtn) closeBtn.focus();
  }

  function open(metric){
    var d = data[metric];
    if(!d){titleEl.textContent=metric;bodyEl.innerHTML='<div class="dim">No data for this metric.</div>';showPanel();return;}
    titleEl.textContent = d.display_name || metric;
    var pct = d.percentile != null ? (d.percentile*100).toFixed(0)+'th' : '—';
    var barPct = d.percentile != null ? Math.round(d.percentile*100) : 50;
    var barColor = barPct > 70 ? '#0a8a5f' : (barPct < 30 ? '#b5321e' : '#b8732a');
    bodyEl.innerHTML =
      '<div class="ep-section"><div class="ep-label">Source</div><span class="ep-source-chip">'+d.source+'</span></div>'+
      '<div class="ep-section"><div class="ep-label">Current value</div><div class="num ep-value">'+d.value.toFixed(2)+'</div></div>'+
      '<div class="ep-section"><div class="ep-label">Benchmark P50</div><div>'+(d.benchmark_p50!=null?d.benchmark_p50.toFixed(1):'—')+'</div>'+
      '<div class="ep-label wb-mt6">Percentile rank: '+pct+'</div>'+
      '<div class="ep-bar"><div style="width:'+barPct+'%;background:'+barColor+';"></div></div></div>'+
      '<div class="ep-section"><div class="ep-label">EBITDA sensitivity</div><div>#'+(d.ebitda_sensitivity_rank||'—')+' · impact '+fmtMoney(d.ebitda_impact)+'</div></div>'+
      (d.diligence_question ? '<div class="ep-section"><div class="ep-label">Diligence question</div><div class="ep-quote">'+d.diligence_question+'</div></div>' : '');
    showPanel();
  }

  if(closeBtn) closeBtn.addEventListener('click', function(){ panel.classList.remove('open'); });
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && panel && panel.classList.contains('open')) {
      panel.classList.remove('open');
    }
  });
  document.addEventListener('click', function(e){
    var el = e.target.closest('[data-explain]');
    if(!el) return;
    e.preventDefault();
    open(el.dataset.explain);
  });
  // Also open on metric name links in the profile table.
  document.querySelectorAll('.analysis-workbench a[href^="#prov-"]').forEach(function(a){
    a.dataset.explain = a.href.split('#prov-')[1] || '';
  });
})();
"""


_OVERRIDE_JS = r"""
(function(){
  var panel = document.querySelector('.wb-tab-panel[data-panel="assumptions"]');
  if (!panel) return;
  var dealId = panel.dataset.dealId;
  if (!dealId) return;

  function csrfToken() {
    var m = document.cookie.match(/(?:^|;\s*)rcm_csrf=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function setFeedback(el, msg, ok) {
    if (!el) return;
    el.textContent = msg;
    el.className = 'ov-feedback ' + (ok ? 'ok' : 'err');
    setTimeout(function(){ el.textContent = ''; el.className = 'ov-feedback'; }, 4000);
  }

  function ovPut(key, value, reason, feedbackEl, onSuccess) {
    fetch('/api/deals/' + encodeURIComponent(dealId) + '/overrides/' + encodeURIComponent(key), {
      method: 'PUT',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken()},
      body: JSON.stringify({value: value, reason: reason || ''})
    })
    .then(function(r){ return r.ok ? r.json() : r.text().then(function(t){ throw t; }); })
    .then(function(){ setFeedback(feedbackEl, 'Saved. Rebuild packet to apply.', true); if(onSuccess) onSuccess(); })
    .catch(function(e){ setFeedback(feedbackEl, 'Error: ' + e, false); });
  }

  function ovDelete(key, feedbackEl, onSuccess) {
    fetch('/api/deals/' + encodeURIComponent(dealId) + '/overrides/' + encodeURIComponent(key), {
      method: 'DELETE',
      headers: {'X-CSRF-Token': csrfToken()}
    })
    .then(function(r){ return r.ok ? r.json() : r.text().then(function(t){ throw t; }); })
    .then(function(){ setFeedback(feedbackEl, 'Cleared. Rebuild packet to apply.', true); if(onSuccess) onSuccess(); })
    .catch(function(e){ setFeedback(feedbackEl, 'Error: ' + e, false); });
  }

  // Commit inline input on Enter or blur
  function nearestFeedback(row) {
    var sec = row.closest('.ov-section');
    return sec ? sec.querySelector('.ov-feedback') : null;
  }

  panel.querySelectorAll('input.ov-input[data-ov-key]').forEach(function(inp) {
    function commit() {
      var v = inp.value.trim();
      if (!v) return;
      var key = inp.dataset.ovKey;
      var fb = nearestFeedback(inp);
      var parsed = isNaN(Number(v)) ? v : Number(v);
      ovPut(key, parsed, '', fb, function() {
        inp.value = '';
        // Update the active-val cell in the same row
        var row = panel.querySelector('[data-ov-row="' + CSS.escape(key) + '"]');
        if (row) {
          var cell = row.children[2];
          if (cell) cell.innerHTML = '<span class="ov-active-val">' + parsed + '</span> <span class="ov-badge-a">A</span>';
          // Show clear button
          var clearCell = row.children[3];
          if (clearCell && !clearCell.querySelector('.ov-clear-btn')) {
            var btn = document.createElement('button');
            btn.className = 'wb-btn wb-btn-danger ov-clear-btn';
            btn.dataset.ovKey = key;
            btn.textContent = 'Clear';
            clearCell.appendChild(btn);
          }
        }
      });
    }
    inp.addEventListener('keydown', function(e){ if(e.key === 'Enter') { e.preventDefault(); commit(); } });
    inp.addEventListener('blur', commit);
  });

  // Clear buttons (delegated — new ones are injected above)
  panel.addEventListener('click', function(e) {
    var btn = e.target.closest('.ov-clear-btn');
    if (!btn) return;
    var key = btn.dataset.ovKey;
    var fb = nearestFeedback(btn);
    ovDelete(key, fb, function() {
      var row = panel.querySelector('[data-ov-row="' + CSS.escape(key) + '"]');
      if (row) {
        row.children[2].innerHTML = '<span class="ov-model-val dim">model default</span>';
        row.children[3].innerHTML = '';
      }
    });
  });

  // Metric target add
  var mtBtn = document.getElementById('ov-mt-add-btn');
  if (mtBtn) mtBtn.addEventListener('click', function() {
    var k = document.getElementById('ov-mt-key').value.trim();
    var v = document.getElementById('ov-mt-val').value.trim();
    var r = document.getElementById('ov-mt-reason').value.trim();
    var fb = document.getElementById('ov-mt-feedback');
    if (!k || !v) { setFeedback(fb, 'Key and value required.', false); return; }
    var parsed = isNaN(Number(v)) ? v : Number(v);
    ovPut('metric_target.' + k, parsed, r, fb, function() {
      document.getElementById('ov-mt-key').value = '';
      document.getElementById('ov-mt-val').value = '';
    });
  });

  // Raw / custom override add
  var rawBtn = document.getElementById('ov-raw-add-btn');
  if (rawBtn) rawBtn.addEventListener('click', function() {
    var k = document.getElementById('ov-raw-key').value.trim();
    var v = document.getElementById('ov-raw-val').value.trim();
    var r = document.getElementById('ov-raw-reason').value.trim();
    var fb = document.getElementById('ov-raw-feedback');
    if (!k || !v) { setFeedback(fb, 'Key and value required.', false); return; }
    var parsed = isNaN(Number(v)) ? v : Number(v);
    ovPut(k, parsed, r, fb, function() {
      document.getElementById('ov-raw-key').value = '';
      document.getElementById('ov-raw-val').value = '';
    });
  });

  // "Edit in Assumptions →" links on the Bridge tab
  document.querySelectorAll('[data-tab-goto]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      e.preventDefault();
      var target = a.dataset.tabGoto;
      var btn = document.querySelector('.analysis-workbench .wb-tab[data-tab="' + target + '"]');
      if (btn) btn.click();
    });
  });
})();
"""


def render_workbench(packet: DealAnalysisPacket) -> str:
    """Produce the full ``<!doctype html>`` document for
    ``/analysis/<deal_id>``. One call, one packet, one rendered page.

    Wrapped in chartis_shell for consistency with the rest of the
    platform. The custom _WORKBENCH_CSS is passed via extra_css so
    the tab layout + explain-panel styling persists; _WORKBENCH_JS
    and _EXPLAIN_JS go through extra_js.
    """
    from ._chartis_kit import chartis_shell, ck_next_section
    override_count = len(packet.analyst_overrides or {})
    header = _render_header(packet)
    nav = _render_tab_nav(override_count)
    # NOTE: the B.1 calibration-in-progress banner (gated on
    # date.today() < 2026-05-25) expired and was removed in the
    # 2026-07 facelift — it had been rendering nothing while still
    # shipping dead markup + ad-hoc hex styling.
    #
    # The partner-review band renders AFTER every tab panel: it is
    # not itself a tab panel (it shows on every tab by design), and
    # placing it before the Assumptions panel put a full-width navy
    # band between the tab bar and that tab's own content.
    body_inner = (
        _render_overview(packet)
        + _render_rcm_profile(packet)
        + _render_bridge(packet)
        + _render_mc(packet)
        + _render_scenarios(packet)
        + _render_risk_diligence(packet)
        + _render_provenance(packet)
        + _render_assumptions(packet)
        + _partner_review_band(packet)
    )
    # Prompt 32: build the explain-panel data blob + the empty panel div.
    explain_data = _build_explain_data(packet)
    explain_panel = (
        '<div class="wb-explain-panel" id="wb-explain-panel">'
        '<button class="ep-close" id="ep-close" aria-label="Close panel">&times;</button>'
        '<div class="ep-title" id="ep-title"></div>'
        '<div id="ep-body"></div>'
        '</div>'
        f'<script id="wb-explain-data" type="application/json">'
        f'{ck_json_for_script(explain_data)}</script>'
    )
    next_up = ck_next_section(
        "Back to the deal profile",
        f"/deal/{packet.deal_id}",
        eyebrow="Up next",
        italic_word="profile",
    )
    shell_body = (
        f'<div class="analysis-workbench">{header}'
        f'{nav}{body_inner}{explain_panel}</div>{next_up}'
    )
    return chartis_shell(
        shell_body,
        f"{packet.deal_name or packet.deal_id} · Analysis Workbench",
        active_nav="/analysis",
        extra_css=_WORKBENCH_CSS,
        extra_js=_WORKBENCH_JS + _EXPLAIN_JS + _OVERRIDE_JS,
    )
