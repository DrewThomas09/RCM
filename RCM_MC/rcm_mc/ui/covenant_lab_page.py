"""Covenant & Capital Structure Stress Lab page.

Route: ``/diligence/covenant-stress``

Partner-facing visualizations:
    * Stacked bar: per-quarter breach probability by covenant
    * Timeline SVG: covenant headroom trajectory with threshold lines
    * Debt-service cliff chart: quarterly interest + amort stack
    * Equity-cure size table with first-cure-quarter
    * Partner voice headline + rationale
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional, Sequence

from ..diligence.covenant_lab import (
    CovenantStressResult, DEFAULT_COVENANTS, default_lbo_stack,
    run_covenant_stress,
)
from ..diligence.covenant_lab.simulator import (
    QuarterlyCovenantCurve,
)
from ._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_header, ck_section_intro, ck_signal_badge, ck_source_purpose,
)
from .power_ui import (
    benchmark_chip, bookmark_hint, deal_context_bar,
    export_json_panel, interpret_callout, provenance, sortable_table,
)


# 2026-05-28 style-sweep · strict Tier-1 5-block head for the four
# covenant-lab render paths (rendered report / landing form / err
# state / main intro). Plus a "Copy share link" usability button
# inlined in the head's actions area so partners can deep-link a
# specific scenario to teammates with one click.
_CV_HEAD_CSS = """
<style>
.cv-head{padding:0 0 28px;margin:0 0 24px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac);}
.cv-head .head-row{display:flex;justify-content:space-between;
  align-items:flex-start;gap:32px;}
.cv-head .head-left{flex:1;min-width:0;}
.cv-head .head-actions{display:flex;gap:8px;flex-shrink:0;
  align-items:flex-start;}
.cv-head .head-actions a,.cv-head .head-actions button{
  font:500 11px/1 var(--sc-sans,Inter),sans-serif;letter-spacing:.08em;
  text-transform:uppercase;color:var(--ink,#16263a);
  background:var(--paper-card,#fefcf3);border:1px solid var(--rule,#c9bf9c);
  border-radius:2px;padding:9px 14px;text-decoration:none;cursor:pointer;
  transition:background .12s,border-color .12s;}
.cv-head .head-actions a:hover,.cv-head .head-actions button:hover{
  background:var(--paper-hi,#fbf6e8);border-color:var(--rule-hi,#b6a87f);}
.cv-head .eyebrow{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.18em;text-transform:uppercase;
  color:var(--green-deep,#154e36);display:flex;align-items:center;
  gap:12px;margin:0 0 18px;}
.cv-head .eyebrow .dash{width:24px;height:1px;
  background:var(--green-deep,#154e36);}
.cv-head h1{font:400 40px/1.05 var(--sc-serif,Georgia),serif;
  letter-spacing:-.015em;color:var(--ink,#16263a);margin:0 0 14px;}
/* Verdict-card subhead (as_subhead): smaller than the page heading so the
   results view reads page-title then verdict, keeping one page heading. */
.cv-head h2{font:400 27px/1.1 var(--sc-serif,Georgia),serif;
  letter-spacing:-.01em;color:var(--ink,#16263a);margin:0 0 12px;}
.cv-head .meta{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted,#7a8595);margin:0 0 18px;}
.cv-head .lede{font:400 italic 16.5px/1.55 var(--sc-serif,Georgia),serif;
  color:var(--ink-2,#2b3e54);max-width:68ch;margin:0 0 18px;}
.cv-head .lede em{color:var(--green-deep,#154e36);font-style:italic;}
.cv-head .legend{display:flex;gap:24px;list-style:none;padding:0;
  margin:0;font:400 12.5px/1 var(--sc-sans,Inter),sans-serif;
  color:var(--ink-2,#2b3e54);flex-wrap:wrap;}
.cv-head .legend li{display:flex;align-items:center;}
.cv-head .legend .dot{width:8px;height:8px;border-radius:50%;
  display:inline-block;margin-right:10px;}
.cv-head .legend .dot.live{background:var(--green-deep,#154e36);}
.cv-head .legend .dot.computed{background:var(--ink-deep,#0e1a29);}
.cv-head .legend .dot.needs{background:var(--coral,#b04a3a);}
.cv-head .legend .dot.illustrative{background:var(--gold,#a08227);}
@media (max-width:960px){
  .cv-head h1{font-size:32px;}
  .cv-head .head-row{flex-direction:column;}
}
</style>
<script>
/* Copy-share-link helper — single source of truth for the editorial
 * head's "Copy share link" button across covenant-lab + payer-stress.
 * The button copies window.location.href to clipboard via the modern
 * navigator.clipboard API. Falls back to a textarea+execCommand path
 * for older browsers. Surfaces a 2-second toast confirmation in the
 * button itself so the partner sees the action took. */
(function(){
  if (window.__rcmCopyShareLinkInstalled) return;
  window.__rcmCopyShareLinkInstalled = true;
  function bind(){
    document.querySelectorAll('[data-rcm-share-link]').forEach(function(btn){
      btn.addEventListener('click', function(ev){
        ev.preventDefault();
        var url = window.location.href;
        var original = btn.textContent;
        var ok = function(){
          btn.textContent = 'Copied ✓';
          setTimeout(function(){ btn.textContent = original; }, 1800);
        };
        var fail = function(){
          btn.textContent = 'Copy failed';
          setTimeout(function(){ btn.textContent = original; }, 1800);
        };
        if (navigator.clipboard && navigator.clipboard.writeText){
          navigator.clipboard.writeText(url).then(ok, fail);
        } else {
          try {
            var ta = document.createElement('textarea');
            ta.value = url; document.body.appendChild(ta);
            ta.select(); document.execCommand('copy');
            document.body.removeChild(ta); ok();
          } catch(e){ fail(); }
        }
      });
    });
  }
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', bind);
  } else { bind(); }
})();
</script>
"""


def _cv_head(
    eyebrow: str,
    title: str,
    *,
    meta: str,
    lede_italic_phrase: str,
    lede_body: str,
    actions_html: str = "",
    as_subhead: bool = False,
) -> str:
    """Strict Tier-1 5-block head for a covenant-lab render path.

    ``as_subhead`` renders the title as an ``<h2>`` (subhead size) — used by
    the verdict card on the results view, which sits under the page
    masthead, so the page keeps a single ``<h1>`` (editorial-head invariant).

    ``actions_html`` is optional extra HTML for the right-side actions
    column (Copy share link, Open in IC memo, etc.). Use the
    ``data-rcm-share-link`` attribute on a button to wire the
    auto-installed clipboard-copy handler.
    """
    actions_block = (
        f'<div class="head-actions">{actions_html}</div>'
        if actions_html else ""
    )
    _tag = "h2" if as_subhead else "h1"
    return (
        _CV_HEAD_CSS
        + '<header class="cv-head">'
        '<div class="head-row">'
        '<div class="head-left">'
        f'<div class="eyebrow"><span class="dash"></span>'
        f'{html.escape(eyebrow)}</div>'
        f'<{_tag}>{title}</{_tag}>'
        f'<div class="meta">{html.escape(meta)}</div>'
        f'<p class="lede"><em>{html.escape(lede_italic_phrase)}</em> '
        f'{lede_body}</p>'
        '</div>'
        f'{actions_block}'
        '</div>'
        '<ul class="legend">'
        '<li><span class="dot live"></span>Live data</li>'
        '<li><span class="dot computed"></span>Computed</li>'
        '<li><span class="dot needs"></span>Needs data</li>'
        '<li><span class="dot illustrative"></span>Illustrative</li>'
        '</ul>'
        '</header>'
    )


# ────────────────────────────────────────────────────────────────────
# Industry peer benchmarks — healthcare PE underwriting norms
# ────────────────────────────────────────────────────────────────────
#
# Sourced from S&P LCD quarterly LBO data + PE industry surveys.
# Refresh annually.  Partners use these as the "is this deal tight?"
# reference — the answer spreadsheets don't surface natively.

_LEVERAGE_PEER_LOW = 5.5               # × EBITDA — below = conservative
_LEVERAGE_PEER_HIGH = 7.0              # × EBITDA — above = aggressive
_LEVERAGE_PEER_MEDIAN = 6.4

_DSCR_PEER_LOW = 1.25
_DSCR_PEER_HIGH = 1.75
_DSCR_PEER_MEDIAN = 1.50

_ICR_PEER_LOW = 2.00
_ICR_PEER_HIGH = 3.25
_ICR_PEER_MEDIAN = 2.50

_BREACH_PROB_TIGHT = 0.10             # banks want < 10% at closing
_BREACH_PROB_WATCH = 0.25
_BREACH_PROB_FAIL = 0.50

# Peer median rate is the blended floating-rate cost PE healthcare
# deals carried in 2025/2026.  Used as the "your rate vs peers" chip.
_BLENDED_RATE_PEER_MEDIAN = 0.085


# ────────────────────────────────────────────────────────────────────
# Scoped CSS (cl- prefix)
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.cl-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.cl-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.cl-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.cl-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.cl-panel{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 20px;margin-bottom:16px;}}
/* 2026-05-28 batch 35 · Tier-4 trope removal — drops decorative
   3px accent stripe on .cl-callout; flat hairline panel instead. */
.cl-callout{{background:{pa};padding:12px 16px;border:1px solid {bd};
border-radius:2px;font-size:12px;color:{td};line-height:1.65;
max-width:880px;margin-top:12px;}}
.cl-verdict-card{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:18px 22px;margin-top:14px;position:relative;overflow:hidden;}}
.cl-verdict-card::before{{content:"";position:absolute;top:0;left:0;right:0;
height:3px;background:linear-gradient(90deg,var(--tone),{ac});}}
.cl-verdict-PASS{{--tone:{po};}}
.cl-verdict-WATCH{{--tone:{wn};}}
.cl-verdict-FAIL{{--tone:{ne};}}
.cl-verdict-badge{{display:inline-block;padding:4px 12px;border-radius:3px;
font-size:11px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;
background:var(--tone);color:#fff;}}
.cl-verdict-headline{{font-size:17px;color:{tx};font-weight:600;
line-height:1.45;margin-top:12px;}}
.cl-verdict-rationale{{font-size:12px;color:{td};line-height:1.55;
margin-top:8px;max-width:900px;}}
.cl-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
gap:14px;margin-top:14px;}}
.cl-kpi__label{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};font-weight:600;margin-bottom:3px;}}
.cl-kpi__val{{font-size:22px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;color:{tx};}}
.cl-kpi__val.neg{{color:{ne};}}
.cl-kpi__val.pos{{color:{po};}}
.cl-form-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:14px;}}
.cl-form-field label{{display:block;font-size:10px;color:{tf};
letter-spacing:1.2px;text-transform:uppercase;font-weight:600;margin-bottom:4px;}}
.cl-form-field input,.cl-form-field select{{width:100%;
background:{pa};color:{tx};border:1px solid {bd};padding:8px 10px;
border-radius:3px;font-family:"JetBrains Mono",monospace;font-size:13px;}}
.cl-form-submit{{margin-top:18px;padding:10px 20px;background:{bp};
color:#fff;border:0;border-radius:3px;font-size:12px;letter-spacing:1.3px;
text-transform:uppercase;font-weight:700;cursor:pointer;}}
.cl-form-submit:hover{{filter:brightness(1.15);}}
.cl-chips-row{{display:flex;gap:24px;flex-wrap:wrap;margin-top:16px;}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"], bp=P["navy"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Visualisations
# ────────────────────────────────────────────────────────────────────

def _breach_probability_chart(
    curves: Sequence[QuarterlyCovenantCurve],
    quarters: int,
    width: int = 920, height: int = 300,
) -> str:
    """Stacked lines: one per covenant, x=quarter, y=breach prob."""
    if not curves:
        return ""
    by_cov: Dict[str, List[QuarterlyCovenantCurve]] = {}
    for c in curves:
        by_cov.setdefault(c.covenant_name, []).append(c)
    for lst in by_cov.values():
        lst.sort(key=lambda c: c.quarter_idx)

    pad_l, pad_r, pad_t, pad_b = 56, 130, 28, 42
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)

    def x(q: int) -> float:
        return pad_l + (q / max(1, quarters - 1)) * inner_w

    def y(p: float) -> float:
        return pad_t + inner_h - min(1.0, max(0.0, p)) * inner_h

    # Threshold lines
    grid_lines = []
    for gp in (0.25, 0.50, 0.75):
        yp = y(gp)
        grid_lines.append(
            f'<line x1="{pad_l}" y1="{yp:.1f}" '
            f'x2="{pad_l + inner_w}" y2="{yp:.1f}" '
            f'stroke="{P["border"]}" stroke-width="1" '
            f'stroke-dasharray="2,3" opacity="0.5"/>'
        )
        grid_lines.append(
            f'<text x="{pad_l - 6}" y="{yp + 3:.1f}" '
            f'text-anchor="end" font-size="9" '
            f'fill="{P["text_faint"]}">{int(gp*100)}%</text>'
        )

    # Covenant colors
    palette = [
        P["negative"], P["warning"], P["accent"], P["positive"],
    ]
    lines = []
    legend_items = []
    for i, (name, pts) in enumerate(sorted(by_cov.items())):
        color = palette[i % len(palette)]
        path_d = "M " + " L ".join(
            f"{x(p.quarter_idx):.1f},{y(p.breach_probability):.1f}"
            for p in pts
        )
        lines.append(
            f'<path d="{path_d}" stroke="{color}" stroke-width="2.5" '
            f'fill="none"/>'
        )
        # Dots
        for p in pts:
            tip = (
                f"{name} Y{p.year}Q{p.quarter_idx%4+1}\\n"
                f"Breach prob {p.breach_probability*100:.0f}%\\n"
                f"Median metric {p.median_metric:.2f} vs "
                f"threshold {p.threshold:.2f}"
            )
            lines.append(
                f'<circle cx="{x(p.quarter_idx):.1f}" '
                f'cy="{y(p.breach_probability):.1f}" r="3" '
                f'fill="{color}" stroke="{P["panel"]}" '
                f'stroke-width="1"><title>'
                f'{html.escape(tip)}</title></circle>'
            )
        legend_items.append(
            f'<g transform="translate({pad_l + inner_w + 12},'
            f'{pad_t + i * 22})">'
            f'<rect width="10" height="10" fill="{color}"/>'
            f'<text x="16" y="9" font-size="11" '
            f'fill="{P["text"]}">{html.escape(name)}</text>'
            f'</g>'
        )

    # X-axis labels
    x_labels = []
    for q in range(0, quarters, 4):
        xc = x(q)
        x_labels.append(
            f'<text x="{xc:.1f}" y="{pad_t + inner_h + 14}" '
            f'text-anchor="middle" font-size="10" '
            f'fill="{P["text_faint"]}" '
            f'font-family="JetBrains Mono,monospace">'
            f'Y{q//4 + 1}</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px;height:auto;" '
        f'role="img" aria-label="Covenant breach probability">'
        f'<rect x="0" y="0" width="{width}" height="{height}" '
        f'fill="{P["panel"]}"/>'
        + "".join(grid_lines) + "".join(lines)
        + "".join(legend_items) + "".join(x_labels)
        + '</svg>'
    )


def _debt_service_chart(
    schedule,
    width: int = 920, height: int = 220,
) -> str:
    """Stacked bars: per-quarter interest + amort."""
    if not schedule:
        return ""
    quarters = len(schedule)
    max_ds = max(
        (s.total_debt_service for s in schedule), default=1.0,
    )
    pad_l, pad_r, pad_t, pad_b = 60, 20, 22, 38
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)
    bar_w = inner_w / max(quarters, 1)

    bars = []
    for s in schedule:
        x0 = pad_l + s.quarter_idx * bar_w
        total = s.total_debt_service
        h_total = (total / max_ds) * inner_h if max_ds > 0 else 0
        h_int = (s.total_interest / max_ds) * inner_h if max_ds > 0 else 0
        h_amort = (
            s.total_scheduled_amort / max_ds * inner_h
            if max_ds > 0 else 0
        )
        # Stack: interest bottom, amort middle, commit top
        y_int = pad_t + inner_h - h_int
        y_amort = y_int - h_amort
        bars.append(
            f'<rect x="{x0+1:.1f}" y="{y_int:.1f}" '
            f'width="{bar_w-2:.1f}" height="{h_int:.1f}" '
            f'fill="{P["negative"]}"/>'
        )
        bars.append(
            f'<rect x="{x0+1:.1f}" y="{y_amort:.1f}" '
            f'width="{bar_w-2:.1f}" height="{h_amort:.1f}" '
            f'fill="{P["warning"]}"/>'
        )
        bars.append(
            f'<rect x="{x0+1:.1f}" y="{pad_t}" '
            f'width="{bar_w-2:.1f}" '
            f'height="{inner_h}" fill="transparent">'
            f'<title>Y{s.year}Q{s.quarter_in_year}: '
            f'${total/1e6:.2f}M debt service '
            f'(${s.total_interest/1e6:.2f}M int, '
            f'${s.total_scheduled_amort/1e6:.2f}M amort)</title>'
            f'</rect>'
        )
    # Axes labels
    y_labels = []
    for i in range(4):
        t = i / 3
        val = max_ds * (1 - t)
        yp = pad_t + t * inner_h
        y_labels.append(
            f'<text x="{pad_l - 6}" y="{yp + 3:.1f}" '
            f'text-anchor="end" font-size="10" '
            f'fill="{P["text_faint"]}" '
            f'font-family="JetBrains Mono,monospace">'
            f'${val/1e6:.1f}M</text>'
        )
    legend = (
        f'<g transform="translate({pad_l + 8},{pad_t + 4})">'
        f'<rect width="10" height="10" fill="{P["negative"]}"/>'
        f'<text x="16" y="9" font-size="11" '
        f'fill="{P["text"]}">Interest</text>'
        f'<rect x="80" width="10" height="10" fill="{P["warning"]}"/>'
        f'<text x="96" y="9" font-size="11" '
        f'fill="{P["text"]}">Amortization</text>'
        f'</g>'
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;height:auto;">'
        f'<rect x="0" y="0" width="{width}" height="{height}" '
        f'fill="{P["panel"]}"/>'
        + "".join(bars) + "".join(y_labels) + legend
        + '</svg>'
    )


# ────────────────────────────────────────────────────────────────────
# Composed blocks
# ────────────────────────────────────────────────────────────────────

def _verdict_card(res: CovenantStressResult) -> str:
    if res.max_breach_probability >= 0.5:
        verdict = "FAIL"
        badge_color = P["negative"]
    elif res.max_breach_probability >= 0.25:
        verdict = "WATCH"
        badge_color = P["warning"]
    else:
        verdict = "PASS"
        badge_color = P["positive"]

    # Plain-English interpretation of the max breach probability vs
    # the typical PE-bank underwriting norms.
    max_prob = res.max_breach_probability
    if max_prob >= _BREACH_PROB_FAIL:
        breach_plain = (
            "Above PE-bank acceptable ceiling (>50% breach). Lenders "
            "typically re-price, tighten, or walk at this level."
        )
        breach_tone = "bad"
    elif max_prob >= _BREACH_PROB_WATCH:
        breach_plain = (
            "Watch-list territory (25-50% breach). Negotiate cushion "
            "or step-down deferral at term sheet — don't sign as-is."
        )
        breach_tone = "warn"
    elif max_prob >= _BREACH_PROB_TIGHT:
        breach_plain = (
            "Tight but bankable (10-25% breach). In the zone PE banks "
            "accept with covenant cushion."
        )
        breach_tone = "warn"
    else:
        breach_plain = (
            "Investment-grade comfort (<10% breach). Clears bank "
            "underwriting norms without covenant concessions."
        )
        breach_tone = "good"

    early_q = res.earliest_50pct_quarter
    early_label = (
        f"Y{early_q//4+1}Q{early_q%4+1}"
        if early_q is not None else "never"
    )

    # Peer benchmark chip — rendered under the KPI grid so partners
    # see "your 45% breach vs 10% bank target" at a glance.
    max_prob_chip = benchmark_chip(
        value=max_prob * 100,
        peer_low=_BREACH_PROB_TIGHT * 100,
        peer_high=_BREACH_PROB_WATCH * 100,
        higher_is_better=False,
        format_spec=".0f",
        suffix="%",
        label="Max Breach Probability",
        peer_label="bank-acceptable band",
    )

    max_prob_val = provenance(
        f"{max_prob*100:.0f}%",
        source="Covenant stress simulator",
        formula="max across covenants × quarters of breach probability",
        detail=(
            f"Computed across {res.n_paths} synthetic EBITDA paths "
            f"× {res.quarters} quarters × {len(res.per_covenant_curves) // max(1, res.quarters)} covenants. "
            f"PE-bank underwriting norm: <10% at close, <25% all-in."
        ),
    )

    badge_tone = {
        "FAIL": "negative",
        "WATCH": "warning",
        "PASS": "positive",
    }.get(verdict, "neutral")
    # 2026-05-28 sweep · strict 5-block head + usability lift:
    # "Copy share link" so partners can deep-link this scenario to
    # teammates, plus a contextual cross-link to the IC memo and the
    # bear case for the same deal — closes the analytical loop.
    actions_html = (
        '<button type="button" data-rcm-share-link>Copy share link</button>'
        '<a href="/ic-memo">Open IC memo →</a>'
        '<a href="/bear-cases">Open bear case →</a>'
    )
    intro = _cv_head(
        eyebrow=f"Covenant Stress · {verdict}",
        title=html.escape(res.headline),
        meta=(
            f"VERDICT {verdict} · MAX BREACH PROB {max_prob*100:.0f}% · "
            f"{res.n_paths:,} PATHS · EARLIEST 50% {early_label}"
        ),
        lede_italic_phrase=(
            "How close this deal is to a covenant breach."
        ),
        lede_body=html.escape(res.rationale),
        actions_html=actions_html,
        # Verdict card sits under the page masthead on the results view —
        # render as a subhead (h2) so the page keeps a single <h1>.
        as_subhead=True,
    )
    badge = ck_signal_badge(verdict, tone=badge_tone)
    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Max Breach Prob", max_prob_val,
            sub="vs <10% bank target · <25% acceptable",
            help={
                "definition": (
                    "Highest probability across simulated paths "
                    "that ANY covenant (DSCR, leverage, fixed-"
                    "charge) breaches in any quarter of the test "
                    "horizon. Banks typically want this below 10%; "
                    "25% is the deal-killer threshold for most "
                    "credit committees."
                ),
            },
        )
        + ck_kpi_block(
            "Earliest 50% Breach", early_label,
            sub="quarter any covenant first crosses 50% breach probability",
            help={
                "definition": (
                    "First quarter where breach probability for any "
                    "covenant exceeds 50% — the moment the credit "
                    "agreement starts forcing decisions (waiver, "
                    "amendment, or default). Earlier is worse."
                ),
            },
        )
        + ck_kpi_block(
            "Simulated Paths", f"{res.n_paths:,}",
            sub="synthetic EBITDA trials",
            help={
                "definition": (
                    "Number of forward EBITDA paths the stress "
                    "simulator generated. Each path is a complete "
                    "quarter-by-quarter realization combining the "
                    "deal's historical EBITDA variance with "
                    "forward-looking initiative impact."
                ),
                "citation": "rcm_mc/mc/ebitda_mc.py",
            },
        )
        + ck_kpi_block(
            "Quarters Tested", f"{res.quarters}",
            sub=f"{res.quarters//4}-year horizon",
        )
        + "</div>"
    )
    return (
        f'<div class="cl-verdict-card cl-verdict-{verdict}">'
        f'<p class="ck-section-body">{badge}</p>'
        f'{intro}'
        + kpis
        + interpret_callout(
            "Plain-English read:", breach_plain, tone=breach_tone,
        )
        + '</div>'
    )


def _covenant_detail_table(res: CovenantStressResult) -> str:
    headers = [
        "Covenant", "Peak Breach %", "Peak Quarter",
        "50% First At", "25% First At",
        "Median Cure $", "Breach Path %", "Interpretation",
    ]
    rows = []
    sort_keys = []
    by_cov: Dict[str, List[QuarterlyCovenantCurve]] = {}
    for c in res.per_covenant_curves:
        by_cov.setdefault(c.covenant_name, []).append(c)
    cures_by_name = {c.covenant_name: c for c in res.equity_cures}
    first_by_name = {f.covenant_name: f for f in res.first_breach}

    def _colored(text: str, color: str) -> str:
        return (
            f'<span style="color:{color};font-weight:700;">'
            f'{html.escape(text)}</span>'
        )

    for name in sorted(by_cov):
        curves = by_cov[name]
        peak = max(curves, key=lambda x: x.breach_probability)
        fb = first_by_name.get(name)
        ec = cures_by_name.get(name)
        q50 = fb.first_50pct_breach_quarter if fb else None
        q25 = fb.first_25pct_breach_quarter if fb else None
        q50_lbl = (
            f"Y{q50//4+1}Q{q50%4+1}" if q50 is not None else "—"
        )
        q25_lbl = (
            f"Y{q25//4+1}Q{q25%4+1}" if q25 is not None else "—"
        )
        # Color-code the peak breach cell by PE-bank underwriting band
        pct = peak.breach_probability
        if pct >= _BREACH_PROB_FAIL:
            pct_color = P["negative"]
            interp = (
                "FAIL — renegotiate covenant or walk"
            )
            interp_color = P["negative"]
        elif pct >= _BREACH_PROB_WATCH:
            pct_color = P["warning"]
            interp = "WATCH — cushion needed at term sheet"
            interp_color = P["warning"]
        elif pct >= _BREACH_PROB_TIGHT:
            pct_color = P["warning"]
            interp = "TIGHT — bankable with cushion"
            interp_color = P["warning"]
        else:
            pct_color = P["positive"]
            interp = "PASS — clears bank norms"
            interp_color = P["positive"]

        # Color 50%-quarter amber/red based on how soon it hits
        if q50 is not None:
            year_50 = q50 // 4 + 1
            q50_color = (
                P["negative"] if year_50 <= 2
                else P["warning"] if year_50 <= 4
                else P["text_dim"]
            )
            q50_display = _colored(q50_lbl, q50_color)
        else:
            q50_display = _colored("never", P["positive"])

        cure_str_raw = (
            f"${ec.median_cure_usd/1e6:.1f}M"
            if ec and ec.median_cure_usd is not None else "—"
        )
        # Cure size color: large cure = bad
        if ec and ec.median_cure_usd and ec.median_cure_usd > 25_000_000:
            cure_display = _colored(cure_str_raw, P["negative"])
        elif ec and ec.median_cure_usd and ec.median_cure_usd > 10_000_000:
            cure_display = _colored(cure_str_raw, P["warning"])
        elif ec and ec.median_cure_usd:
            cure_display = _colored(cure_str_raw, P["positive"])
        else:
            cure_display = cure_str_raw

        breach_frac_str = (
            f"{ec.breach_path_fraction*100:.0f}%"
            if ec else "—"
        )
        rows.append([
            html.escape(name),
            _colored(f"{pct*100:.0f}%", pct_color),
            f"Y{peak.year}Q{peak.quarter_idx%4+1}",
            q50_display, q25_lbl, cure_display,
            breach_frac_str,
            _colored(interp, interp_color),
        ])
        sort_keys.append([
            name,
            peak.breach_probability,
            peak.quarter_idx,
            q50 if q50 is not None else 9999,
            q25 if q25 is not None else 9999,
            ec.median_cure_usd if ec and ec.median_cure_usd else 0,
            ec.breach_path_fraction if ec else 0,
            pct,
        ])
    return sortable_table(
        headers, rows, sort_keys=sort_keys,
        name="covenant_stress_detail",
        caption=(
            "Green/amber/red cells reflect PE-bank underwriting "
            "thresholds — click any column to sort, CSV exports "
            "auto-wired."
        ),
    )


def _capital_stack_table(res: CovenantStressResult) -> str:
    tranches = res.capital_stack_summary.get("tranches", [])
    headers = [
        "Tranche", "Type", "Principal", "Term", "Spread bps",
        "Amort", "Lien",
    ]
    rows = []
    for t in tranches:
        amort = (
            "IO + bullet" if all(a == 0 for a in t["amortization_schedule"][:-1])
            else "1% + bullet" if t["amortization_schedule"] and
                 t["amortization_schedule"][0] <= 0.02
            else "Straight-line"
        )
        rows.append([
            html.escape(t["name"]),
            t["kind"],
            f"${t['principal_usd']/1e6:,.1f}M",
            f"{t['term_years']}y",
            f"+{t['spread_bps']:.0f}",
            amort,
            f"L{t['lien_priority']}",
        ])
    return sortable_table(
        headers, rows,
        name="capital_stack_summary",
        caption="Capital stack · senior-first",
    )


def _equity_cure_panel(res: CovenantStressResult) -> str:
    if not res.equity_cures:
        return ""
    rows = []
    for ec in res.equity_cures:
        if ec.median_cure_usd is None:
            continue
        first_q = ec.first_cure_quarter
        q_lbl = (
            f"Y{first_q//4+1}Q{first_q%4+1}"
            if first_q is not None else "—"
        )
        rows.append(
            f'<tr>'
            f'<td>{html.escape(ec.covenant_name)}</td>'
            f'<td class="mono">{q_lbl}</td>'
            f'<td class="mono cad-neg">${ec.median_cure_usd/1e6:.2f}M</td>'
            f'<td class="mono cad-warn">${ec.p75_cure_usd/1e6:.2f}M</td>'
            f'<td>{ec.breach_path_fraction*100:.0f}% of paths</td>'
            f'</tr>'
        )
    if not rows:
        return ck_panel(
            '<p class="ck-section-body">'
            'No covenant breaches across the simulated paths — '
            'equity cure not required in any scenario.</p>',
            title="Equity cure sizing",
        )
    return ck_panel(
        '<table class="cad-table"><thead><tr>'
        '<th>Covenant</th><th>First Cure Q</th>'
        '<th>Median Cure</th><th>P75 Cure</th>'
        '<th>Breach Path %</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        '<p class="ck-section-body">'
        '<strong>How to read:</strong> '
        'For leverage covenants the cure equals the debt paydown '
        'that drops leverage to threshold; for coverage covenants '
        'it\'s the synthetic EBITDA add allowed by the credit '
        'agreement ("yank-the-bank" provision, capped at ~25% of '
        'LTM EBITDA). P75 shows the right-tail scenario — the '
        'partner should underwrite equity capacity for at least '
        'P75.</p>',
        title="Equity cure sizing · partner sponsor capital required",
    )


# ────────────────────────────────────────────────────────────────────
# Landing form
# ────────────────────────────────────────────────────────────────────

def _landing(qs: Optional[Dict[str, List[str]]] = None) -> str:
    form = """
<form method="get" action="/diligence/covenant-stress" class="cl-wrap">
  <div class="cl-panel">
    <div class="cl-section-label" style="margin-top:0;">
      Deal structure · covenant package</div>
    <div class="cl-form-grid">
      <div class="cl-form-field"><label>Deal name</label>
        <input name="deal_name" value="Meadowbrook Health System"/></div>
      <div class="cl-form-field"><label>Entry EBITDA (Y0 USD)</label>
        <input name="ebitda_y0" value="67500000"/></div>
      <div class="cl-form-field"><label>EBITDA growth (CAGR)</label>
        <input name="ebitda_growth" value="0.06"/></div>
      <div class="cl-form-field"><label>EBITDA vol (σ)</label>
        <input name="ebitda_sigma" value="0.15"/></div>
      <div class="cl-form-field"><label>Total debt (USD)</label>
        <input name="total_debt_usd" value="300000000"/></div>
      <div class="cl-form-field"><label>Revolver capacity (USD)</label>
        <input name="revolver_usd" value="40000000"/></div>
      <div class="cl-form-field"><label>Revolver initial draw %</label>
        <input name="revolver_draw_pct" value="0.30"/></div>
      <div class="cl-form-field"><label>Term (years)</label>
        <input name="term_years" value="6"/></div>
      <div class="cl-form-field"><label>Base rate (annual)</label>
        <input name="base_rate" value="0.055"/></div>
      <div class="cl-form-field"><label>Leverage covenant opening (×)</label>
        <input name="leverage_ceiling" value="7.5"/></div>
      <div class="cl-form-field"><label>Leverage covenant step (×/yr)</label>
        <input name="leverage_step" value="0.5"/></div>
      <div class="cl-form-field"><label>DSCR covenant floor (×)</label>
        <input name="dscr_floor" value="1.25"/></div>
      <div class="cl-form-field"><label>Interest coverage floor (×)</label>
        <input name="icr_floor" value="1.75"/></div>
      <div class="cl-form-field"><label>Quarters to simulate</label>
        <input name="quarters" value="20"/></div>
      <div class="cl-form-field"><label>Regulatory overlay (Y-by-Y, $M)</label>
        <input name="reg_overlay" value="0,0,-9.9,-9.95,0,0"/></div>
    </div>
    <button class="cl-form-submit" type="submit">
      Run covenant stress</button>
  </div>
</form>
"""
    # 2026-05-28 sweep · strict 5-block head for the landing form path.
    landing_hero = _cv_head(
        eyebrow="Covenant & Capital Stack Stress Lab",
        title="When does your thesis hit a covenant cliff?",
        meta=(
            "DEAL MC × CAPITAL STACK × COVENANT PACKAGE · "
            "PER-QUARTER BREACH PROBABILITY"
        ),
        lede_italic_phrase=(
            "When the covenant cliff hits — by quarter."
        ),
        lede_body=(
            "Takes the Deal MC EBITDA cone, overlays your capital "
            "stack and covenant package, and produces per-quarter "
            "breach-probability curves for each covenant. Optionally "
            "applies the Regulatory Calendar overlay so partners see "
            "exactly how a V28 cut in CY2027 tightens the 2027 "
            "leverage covenant. Output names the first breach "
            "quarter and sizes the equity cure."
        ),
    )
    body = (
        _scoped_styles()
        + '<div class="cl-wrap">'
        + deal_context_bar(qs or {}, active_surface="covenant")
        + landing_hero
        + ck_panel(form, title="Stack and covenant inputs")
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Covenant Stress Lab",
        subtitle="Capital stack × covenant × calendar",
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def render_covenant_lab_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}

    def first(k: str, default: str = "") -> str:
        return (qs.get(k) or [default])[0].strip()

    def fnum(k: str, d: Optional[float] = None) -> Optional[float]:
        v = first(k)
        if not v:
            return d
        try:
            return float(v)
        except ValueError:
            return d

    if not first("total_debt_usd") and not first("ebitda_y0"):
        return _landing(qs)

    # Use explicit-None fallback rather than `or`-coerced, since a
    # user who supplied 0 intentionally would otherwise be silently
    # upgraded to the 67.5M default, hiding the zero-input bug.
    ebitda_y0 = fnum("ebitda_y0")
    if ebitda_y0 is None:
        ebitda_y0 = 67_500_000.0
    total_debt = fnum("total_debt_usd")
    if total_debt is None:
        total_debt = 350_000_000.0
    growth = fnum("ebitda_growth", 0.06) or 0.06
    sigma = fnum("ebitda_sigma", 0.15) or 0.15

    # Guard: covenant stress is only defined for positive EBITDA
    # and non-zero debt.  When the user lands here from a HCRIS
    # X-Ray on a negative-margin hospital, we'd otherwise produce
    # a nonsensical "FAIL" verdict on empty math.
    if ebitda_y0 <= 0 or total_debt <= 0:
        # 2026-05-28 sweep · strict 5-block head for the error path.
        err_intro = _cv_head(
            eyebrow="Covenant Stress Lab",
            title="Cannot run stress on this input.",
            meta=(
                f"INPUTS REJECTED · EBITDA "
                f"${ebitda_y0/1e6:,.1f}M · "
                f"DEBT ${total_debt/1e6:,.0f}M"
            ),
            lede_italic_phrase="The math doesn't run on these inputs.",
            lede_body=(
                f"Covenant stress requires positive Y0 EBITDA and "
                f"non-zero total debt. You supplied EBITDA "
                f"${ebitda_y0/1e6:,.1f}M and debt ${total_debt/1e6:,.0f}M. "
                "Targets with negative operating margins cannot "
                "service covenant-bearing debt — partners should "
                "underwrite either a restructured target or a "
                "higher equity check before running this module."
            ),
            actions_html=(
                '<a href="/diligence/covenant-stress">← Back to form</a>'
            ),
        )
        return chartis_shell(
            _scoped_styles()
            + '<div class="cl-wrap">'
            + deal_context_bar(qs, active_surface="covenant")
            + err_intro
            + '<p class="ck-section-body">'
            + '<a href="/diligence/covenant-stress" class="ck-link">'
            + '← Back to form</a></p></div>',
            "Covenant Stress — invalid inputs",
        )
    revolver = fnum("revolver_usd", 0.0) or 0.0
    revolver_draw = fnum("revolver_draw_pct", 0.0) or 0.0
    term_years = int(fnum("term_years", 6) or 6)
    base_rate = fnum("base_rate", 0.055) or 0.055
    lev_ceiling = fnum("leverage_ceiling", 7.5) or 7.5
    lev_step = fnum("leverage_step", 0.5) or 0.5
    dscr_floor = fnum("dscr_floor", 1.25) or 1.25
    icr_floor = fnum("icr_floor", 2.25) or 2.25
    quarters = int(fnum("quarters", 24) or 24)
    deal_name = first("deal_name") or "Target Deal"

    # Regulatory overlay parsing
    overlay_raw = first("reg_overlay")
    overlay: Optional[List[float]] = None
    if overlay_raw:
        try:
            overlay = [
                float(x.strip()) * 1_000_000
                for x in overlay_raw.split(",")
                if x.strip()
            ]
        except ValueError:
            overlay = None

    # Build EBITDA bands from y0 + growth + sigma
    bands: List[Dict[str, float]] = []
    for y in range(term_years):
        p50 = ebitda_y0 * ((1 + growth) ** y)
        bands.append({
            "p25": p50 * (1 - sigma * 0.675),
            "p50": p50,
            "p75": p50 * (1 + sigma * 0.675),
        })

    # Build capital stack
    stack = default_lbo_stack(
        total_debt_usd=total_debt,
        revolver_usd=revolver,
        revolver_draw_pct=revolver_draw,
        term_years=term_years,
    )

    # Custom covenant package
    from ..diligence.covenant_lab import CovenantDefinition, CovenantKind
    custom_cov = (
        CovenantDefinition(
            name="Net Leverage",
            kind=CovenantKind.NET_LEVERAGE,
            opening_threshold=lev_ceiling,
            step_down_schedule=tuple(
                (y, lev_ceiling - lev_step * (y - 1))
                for y in range(2, term_years + 1)
                if lev_ceiling - lev_step * (y - 1) > 1.0
            ),
            cushion_pct=0.15,
        ),
        CovenantDefinition(
            name="DSCR",
            kind=CovenantKind.DSCR,
            opening_threshold=dscr_floor,
            cushion_pct=0.15,
        ),
        CovenantDefinition(
            name="Interest Coverage",
            kind=CovenantKind.INTEREST_COVERAGE,
            opening_threshold=icr_floor,
            step_down_schedule=((3, icr_floor + 0.25),),
            cushion_pct=0.15,
        ),
    )

    res = run_covenant_stress(
        ebitda_bands=bands,
        capital_stack=stack,
        covenants=custom_cov,
        rate_path_annual=[base_rate] * quarters,
        quarters=quarters,
        regulatory_overlay_usd_by_year=overlay,
    )

    # Peer-anchored snapshot chips — sits at the top of the page so
    # a first-time reader sees target vs peer at a glance before
    # they descend into the simulator detail.
    entry_leverage = (
        stack.total_funded_usd / max(ebitda_y0, 1.0)
    )
    leverage_chip = benchmark_chip(
        value=entry_leverage,
        peer_low=_LEVERAGE_PEER_LOW,
        peer_high=_LEVERAGE_PEER_HIGH,
        higher_is_better=False,
        format_spec=".2f",
        suffix="×",
        label="Entry Leverage",
        peer_label="PE healthcare LBO band",
    )
    rate_chip = benchmark_chip(
        value=base_rate * 100,
        peer_median=_BLENDED_RATE_PEER_MEDIAN * 100,
        higher_is_better=False,
        format_spec=".1f",
        suffix="%",
        label="Base Rate",
        peer_label="2025/2026 LBO median",
    )
    max_prob_chip = benchmark_chip(
        value=res.max_breach_probability * 100,
        peer_low=_BREACH_PROB_TIGHT * 100,
        peer_high=_BREACH_PROB_WATCH * 100,
        higher_is_better=False,
        format_spec=".0f",
        suffix="%",
        label="Max Breach Prob",
        peer_label="bank-acceptable band",
    )

    # 2026-05-28 sweep · strict 5-block head for the main intro path.
    # Includes the same share-link + cross-link actions as the rendered
    # report.
    main_intro_actions = (
        '<button type="button" data-rcm-share-link>Copy share link</button>'
        '<a href="/ic-memo">Open IC memo →</a>'
        '<a href="/bear-cases">Open bear case →</a>'
    )
    main_intro = _cv_head(
        eyebrow="Covenant Stress Lab",
        title=f"Capital-stack covenant cliff — {html.escape(deal_name)}",
        meta=(
            f"{len(stack.tranches)} TRANCHES · "
            f"${stack.total_funded_usd/1e6:.0f}M FUNDED · "
            f"{len(custom_cov)} COVENANTS · "
            f"{res.n_paths:,} PATHS"
        ),
        lede_italic_phrase=(
            "The capital-stack vs the covenant package, simulated."
        ),
        lede_body=(
            f"{len(stack.tranches)} tranches modeled across "
            f"{len(custom_cov)} covenants and {res.n_paths:,} "
            "simulated paths. The headline below names the first "
            "breach quarter and sizes the equity cure."
        ),
        actions_html=main_intro_actions,
    )
    chips_strip = (
        '<div class="cl-chips-row">'
        f'{leverage_chip}{rate_chip}{max_prob_chip}'
        '</div>'
    )
    hero = main_intro + chips_strip + _verdict_card(res)

    # Derive a plain-English headline for the breach chart: the
    # earliest covenant to cross each threshold.
    first_25 = min(
        (c for c in res.first_breach
         if c.first_25pct_breach_quarter is not None),
        key=lambda c: c.first_25pct_breach_quarter or 9999, default=None,
    )
    first_50 = min(
        (c for c in res.first_breach
         if c.first_50pct_breach_quarter is not None),
        key=lambda c: c.first_50pct_breach_quarter or 9999, default=None,
    )
    chart_plain_parts = []
    if first_50 and first_50.first_50pct_breach_quarter is not None:
        q = first_50.first_50pct_breach_quarter
        chart_plain_parts.append(
            f'First covenant to hit 50% breach probability is '
            f'<strong style="color:{P["negative"]};">'
            f'{html.escape(first_50.covenant_name)}</strong> in '
            f'<strong>Y{q//4+1}Q{q%4+1}</strong>.'
        )
    if (
        first_25 and first_25.first_25pct_breach_quarter is not None
        and (not first_50 or
             first_25.covenant_name != first_50.covenant_name)
    ):
        q = first_25.first_25pct_breach_quarter
        chart_plain_parts.append(
            f' Earliest to show any material stress is '
            f'<strong>{html.escape(first_25.covenant_name)}</strong> '
            f'in Y{q//4+1}Q{q%4+1} (25%).'
        )
    if not chart_plain_parts:
        chart_plain_parts.append(
            f'<span style="color:{P["positive"]};">No covenant '
            f'crosses 25% breach probability across the '
            f'{quarters//4}-year horizon.</span> The capital stack '
            f'comfortably clears bank underwriting norms.'
        )
    chart_plain = "".join(chart_plain_parts)

    breach_inner = (
        _breach_probability_chart(res.per_covenant_curves, quarters)
        + '<p class="ck-eyebrow">'
        '<span class="cad-pos">● &lt;10% breach — bank comfortable</span> &nbsp; '
        '<span class="cad-warn">● 10-25% — tight but bankable</span> &nbsp; '
        '<span class="cad-warn">● 25-50% — negotiate cushion</span> &nbsp; '
        '<span class="cad-neg">● ≥50% — re-price or walk</span>'
        '</p>'
        + interpret_callout("Plain-English read:", chart_plain)
        + '<p class="ck-section-body">'
        '<strong>How to read:</strong> '
        'Each line is one covenant. Y-axis is probability of '
        'breach across simulated EBITDA paths in that quarter; '
        'X-axis is quarters from close. Dashed lines mark 25%, '
        '50%, 75% probability thresholds. Hover any dot for the '
        'exact metric value. A line rising sharply through 50% '
        'is the covenant to negotiate at the LOI — reset, cushion, '
        'or step-down deferral.</p>'
    )
    breach_panel = ck_panel(
        breach_inner,
        title="Per-quarter breach probability — all covenants",
    )

    # Plain-English read of the debt-service cliff: identify the
    # peak quarterly debt service and translate it to an "EBITDA
    # required to cover" metric.
    peak_ds_q = max(
        res.debt_schedule, key=lambda s: s.total_debt_service,
        default=None,
    )
    ds_plain = ""
    if peak_ds_q is not None:
        peak_ds = peak_ds_q.total_debt_service
        peak_year = peak_ds_q.year
        peak_q = peak_ds_q.quarter_in_year
        # Annualized debt-service burden
        ds_annual = peak_ds * 4
        required_ebitda = ds_annual * _DSCR_PEER_MEDIAN
        ds_plain = (
            f'Peak quarterly debt service is '
            f'<strong>${peak_ds/1e6:.2f}M</strong> in '
            f'<strong>Y{peak_year}Q{peak_q}</strong> '
            f'(${ds_annual/1e6:.1f}M annualized). '
            f'At a 1.5× DSCR floor, the target needs '
            f'<strong>${required_ebitda/1e6:.1f}M LTM EBITDA</strong> '
            f'in that quarter to stay inside the covenant.'
        )

    ds_inner = (
        _debt_service_chart(res.debt_schedule)
        + (interpret_callout("Plain-English read:", ds_plain)
           if ds_plain else "")
        + '<p class="ck-section-body">'
        '<strong>How to read:</strong> '
        'Each bar is one quarter of debt service. Red is '
        'interest on outstanding balance; amber is scheduled '
        'amortization. TLB/unitranche bullets concentrate '
        'amortization in the final year — that spike is where '
        'refinance risk concentrates. Flat interest early = '
        'floating-rate base stable; steepening = rate-path stress.</p>'
    )
    ds_panel = ck_panel(
        ds_inner, title="Debt service cliff — quarterly stack",
    )

    cov_detail = ck_panel(
        _covenant_detail_table(res),
        title="Covenant detail — peak breach + first-at",
    )

    stack_detail = ck_panel(
        _capital_stack_table(res),
        title="Capital stack detail",
    )

    reg_note = ""
    if overlay and any(x != 0 for x in overlay):
        total_reg = sum(overlay)
        reg_inner = (
            '<p class="ck-section-body">'
            f'Applied ${total_reg/1e6:+.2f}M cumulative EBITDA '
            f'drag from the Regulatory Calendar across the '
            f'{len(overlay)}-year horizon. Year-by-year overlay: '
            + ", ".join(f"Y{i+1} ${x/1e6:+.2f}M" for i, x in enumerate(overlay))
            + '. These drags subtract from EBITDA before '
            'covenant testing — partners see the compounded '
            'regulatory × covenant stress in one view.</p>'
        )
        reg_note = ck_panel(
            reg_inner, title="Regulatory calendar overlay applied",
        )

    cross_link = ck_panel(
        '<p class="ck-section-body">'
        '<a href="/diligence/deal-mc" class="ck-link">→ Deal MC</a> '
        'produced the EBITDA cone that feeds this lab · '
        '<a href="/diligence/regulatory-calendar" class="ck-link">'
        '→ Regulatory Calendar</a> produced the overlay applied '
        'above · <a href="/diligence/exit-timing" class="ck-link">'
        '→ Exit Timing</a> uses the same leverage path for '
        'refinance feasibility.</p>',
        title="Cross-reference",
    )

    body = (
        _scoped_styles()
        + '<div class="cl-wrap">'
        + deal_context_bar(qs, active_surface="covenant")
        + ck_source_purpose(
            purpose="Stress-test covenant headroom (DSCR / leverage) against EBITDA and rate shocks before underwriting the debt package.",
            universe="user-deals",
            confidence="derived",
            source="Your entered deal capital structure + covenant terms × modeled shock scenarios — a calculator on your inputs, not the lender's actual compliance certificate.",
            next_action="Confirm the real covenant terms with management / lender",
        )
        + hero
        + reg_note
        + breach_panel
        + ds_panel
        + _equity_cure_panel(res)
        + cov_detail
        + stack_detail
        + cross_link
        + export_json_panel(
            '<div class="cl-section-label" style="margin-top:22px;">'
            'JSON export — full stress report</div>',
            payload=res.to_dict(),
            name=f"covenant_stress_{deal_name.replace(' ', '_')}",
        )
        + bookmark_hint()
        + ck_next_section(
            "Stage the bear case",
            "/diligence/bear-case",
            eyebrow="Continue —",
            italic_word="bear",
        )
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Covenant Stress",
        subtitle=(
            f"{deal_name} · max breach "
            f"{res.max_breach_probability*100:.0f}%"
        ),
    )
