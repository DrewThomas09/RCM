"""Interactive Deal Screening — /deal-screening.

Exercises ``data_public/deal_screening_engine.screen_corpus(deals,
config)`` which runs every corpus deal through a rules-based screen
(EV/EBITDA sanity, Medicaid exposure, leverage, heuristic signal,
data completeness) and emits one of three decisions:

  PASS    — all thresholds cleared, heuristic signal green
  WATCH   — at least one soft flag; diligence should triage
  FAIL    — hard threshold failure; do not proceed

The page is interactive via query params — the partner can tighten
thresholds (max_composite_risk_score, max_ev_ebitda, max_medicaid_pct,
etc.) and see the decision mix shift live. Default thresholds match
ScreeningConfig() defaults.
"""
from __future__ import annotations

import html as _html
import urllib.parse as _urlparse
from collections import Counter
from typing import Any, Dict, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
)
from ._helpers import (
    empty_note,
    fmt_pct,
    load_corpus_deals,
    small_panel,
    verdict_badge,
)
from ._sanity import render_number

_EXPLAINER_CSS = """
.ck-ds-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:70ch;
margin:var(--sc-s-4) 0 var(--sc-s-5);}
.ck-ds-explainer em{color:var(--sc-teal-ink);font-style:italic;}
/* "How it works" 3-step framing — make the mental model explicit:
   your thesis = thresholds → corpus pass rate. */
.ds-howto{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 var(--sc-s-5,18px);}
.ds-step{flex:1;min-width:190px;border:1px solid var(--sc-rule,#d6cfc0);
border-radius:5px;padding:11px 14px;background:var(--sc-paper,#faf7f0);}
.ds-step-n{font-family:var(--sc-mono,JetBrains Mono),monospace;font-size:10px;
font-weight:700;letter-spacing:.1em;color:var(--sc-teal,#155752);}
.ds-step-t{font-family:var(--sc-sans,Inter Tight),sans-serif;font-weight:600;
font-size:13px;color:var(--sc-ink,#1a2332);margin:3px 0 2px;}
.ds-step-d{font-size:11.5px;line-height:1.45;color:var(--sc-text-dim,#5b6b7a);}
/* Bigger, clearer screening controls (were 10px labels / 100px inputs). */
.ds-controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
gap:14px 16px;align-items:end;}
.ds-field{display:flex;flex-direction:column;gap:5px;}
.ds-field-label{font-family:var(--sc-sans,Inter Tight),sans-serif;font-size:12px;
font-weight:600;color:var(--sc-text-dim,#5b6b7a);line-height:1.25;}
.ds-field-label .ds-unit{color:var(--sc-text-faint,#7a8699);font-weight:400;
font-size:10.5px;}
.ds-input,.ds-select{width:100%;box-sizing:border-box;background:var(--sc-paper,#faf7f0);
border:1px solid var(--sc-rule,#d6cfc0);color:var(--sc-ink,#1a2332);
font-family:var(--sc-mono,JetBrains Mono),monospace;font-size:13.5px;
padding:9px 11px;border-radius:5px;}
.ds-input:focus,.ds-select:focus{outline:none;border-color:var(--sc-teal,#155752);}
.ds-submit{background:var(--sc-teal,#155752);color:#fff;border:none;
font-family:var(--sc-sans,Inter Tight),sans-serif;font-size:12.5px;font-weight:600;
letter-spacing:.02em;padding:10px 20px;border-radius:5px;cursor:pointer;
align-self:end;}
.ds-submit:hover{filter:brightness(1.06);}
"""


def _title(n_pass: int = 0, n_watch: int = 0, n_fail: int = 0, total: int = 0) -> str:
    if total:
        meta = f"{n_pass} pass · {n_watch} watch · {n_fail} fail · {total} deals"
    else:
        meta = "PASS / WATCH / FAIL decision per corpus deal"
    return ck_page_title("Thesis Screening", eyebrow="THESIS SCREENING", meta=meta)


_DECISION_COLORS = {
    "PASS":    P["positive"],
    "WATCH":   P["warning"],
    "FAIL":    P["negative"],
    "UNKNOWN": P["text_faint"],
}


def _decision_badge(decision: str) -> str:
    col = _DECISION_COLORS.get(decision.upper(), P["text_dim"])
    return verdict_badge(decision.upper(), color=col)


def _heuristic_badge(signal: Optional[str]) -> str:
    s = str(signal or "").lower()
    col = {"green": P["positive"], "yellow": P["warning"],
           "red": P["negative"]}.get(s, P["text_faint"])
    return verdict_badge(s.upper() or "—", color=col)


def _controls_form(
    config: Dict[str, Any],
    filter_decision: str,
) -> str:
    # (key, label, unit-hint, one-line plain-English gloss). Labels carry the
    # gloss so a partner knows exactly which thesis lever each control is.
    fields = [
        ("max_composite_risk_score", "Max risk score", "0–100", "reject above"),
        ("watch_composite_risk_score", "Watch risk score", "0–100", "flag above"),
        ("max_ev_ebitda", "Max EV/EBITDA", "×", "valuation ceiling"),
        ("watch_ev_ebitda", "Watch EV/EBITDA", "×", "flag above"),
        ("min_moic_threshold", "Min MOIC", "×", "return floor"),
        ("max_medicaid_pct", "Max Medicaid", "0–1", "payer-mix ceiling"),
        ("min_ev_mm", "Min EV", "$M", "size floor"),
    ]
    inputs = []
    for key, label, unit, gloss in fields:
        val = config.get(key, "")
        unit_html = f' <span class="ds-unit">· {_html.escape(unit)}</span>' if unit else ""
        gloss_html = f'<br><span class="ds-unit">{_html.escape(gloss)}</span>' if gloss else ""
        inputs.append(
            f'<div class="ds-field">'
            f'<span class="ds-field-label">{_html.escape(label)}{unit_html}{gloss_html}</span>'
            f'<input class="ds-input" name="{key}" value="{val}" type="number" step="any">'
            f'</div>'
        )
    decision_options = "".join(
        f'<option value="{v}"{" selected" if v == filter_decision else ""}>{_html.escape(v or "All decisions")}</option>'
        for v in ("", "FAIL", "WATCH", "PASS")
    )
    inputs.append(
        f'<div class="ds-field">'
        f'<span class="ds-field-label">Show decision<br>'
        f'<span class="ds-unit">filter results</span></span>'
        f'<select class="ds-select" name="decision">{decision_options}</select>'
        f'</div>'
    )
    inputs.append(
        '<div class="ds-field">'
        '<button type="submit" class="ds-submit">Re-run screen &rarr;</button>'
        '</div>'
    )
    return (
        f'<form method="get" action="/deal-screening" class="ds-controls">'
        f'{"".join(inputs)}</form>'
    )


def _result_row(r: Any) -> str:
    decision = str(r.decision)
    col = _DECISION_COLORS.get(decision.upper(), P["text_dim"])
    signal = _heuristic_badge(r.heuristic_signal)
    fails = _html.escape(" · ".join(str(x) for x in (r.fail_reasons or [])[:2])) or "—"
    watches = _html.escape(" · ".join(str(x) for x in (r.watch_reasons or [])[:2])) or "—"
    reason = fails if r.fail_reasons else watches
    return (
        f'<tr>'
        f'<td style="color:{P["text"]};font-size:11.5px;">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:0.10em;margin-right:6px;">'
        f'{_html.escape(str(r.source_id or "—"))}</span>'
        f'{_html.escape(str(r.deal_name or "—"))}</td>'
        f'<td>{_decision_badge(decision)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{col};" data-val="{r.risk_composite or 0}">'
        f'{(r.risk_composite or 0):.1f}</td>'
        f'<td>{signal}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" '
        f'data-val="{r.data_completeness or 0}">{render_number(r.data_completeness, "data_completeness_pct")}</td>'
        f'<td style="color:{P["text_dim"]};font-size:11px;line-height:1.4;'
        f'white-space:normal;">{reason}</td>'
        f'</tr>'
    )


def _decision_strip(counts: Counter, total: int) -> str:
    tiles = []
    for key in ("PASS", "WATCH", "FAIL"):
        col = _DECISION_COLORS[key]
        n = counts.get(key, 0)
        pct = (n / total * 100.0) if total else 0.0
        tiles.append(
            f'<div style="flex:1;min-width:140px;background:{P["panel"]};'
            f'border:1px solid {col};border-left-width:4px;border-radius:3px;'
            f'padding:10px 14px;">'
            f'<div style="font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.15em;color:{P["text_faint"]};">{key}</div>'
            f'<div style="font-family:var(--ck-mono);font-size:26px;'
            f'font-weight:700;color:{col};margin-top:4px;'
            f'font-variant-numeric:tabular-nums;">{n}</div>'
            f'<div style="color:{P["text_dim"]};font-family:var(--ck-mono);'
            f'font-size:10px;margin-top:2px;'
            f'font-variant-numeric:tabular-nums;">'
            f'{pct:.1f}% of {total}</div>'
            f'</div>'
        )
    return (
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;">'
        f'{"".join(tiles)}</div>'
    )


def _parse_config(params: Dict[str, List[str]]) -> Any:
    from ...data_public.deal_screening_engine import ScreeningConfig
    cfg = ScreeningConfig()

    def _get(key: str, default: Any) -> Any:
        v = params.get(key, [""])[0].strip() if params.get(key) else ""
        if not v:
            return default
        try:
            return type(default)(v) if default is not None else float(v)
        except (TypeError, ValueError):
            return default

    cfg = ScreeningConfig(
        max_composite_risk_score=_get("max_composite_risk_score", cfg.max_composite_risk_score),
        watch_composite_risk_score=_get("watch_composite_risk_score", cfg.watch_composite_risk_score),
        max_ev_ebitda=_get("max_ev_ebitda", cfg.max_ev_ebitda),
        watch_ev_ebitda=_get("watch_ev_ebitda", cfg.watch_ev_ebitda),
        min_moic_threshold=_get("min_moic_threshold", cfg.min_moic_threshold),
        max_medicaid_pct=_get("max_medicaid_pct", cfg.max_medicaid_pct),
        require_ebitda_positive=cfg.require_ebitda_positive,
        require_hold_in_range=cfg.require_hold_in_range,
        min_ev_mm=_get("min_ev_mm", cfg.min_ev_mm),
    )
    return cfg


def render_deal_screening(
    store: Any = None,
    query: str = "",
    current_user: Optional[str] = None,
) -> str:
    try:
        from ...data_public.deal_screening_engine import (
            screen_corpus, ScreeningConfig,
        )
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Deal screening unavailable",
            empty_note(f"deal_screening_engine module failed: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            _title() + body, title="Thesis Screening",
            active_nav="/deal-screening",
            extra_css=_EXPLAINER_CSS,
        )

    corpus = load_corpus_deals()
    if not corpus:
        body = small_panel(
            "Deal screening — no corpus loaded",
            '<p style="font-size:13px;line-height:1.5;margin:0 0 8px;">'
            '<strong>No deal corpus is loaded yet.</strong> Deal Screening '
            'ranks the corpus deal library against your risk and valuation '
            'thresholds (composite risk, EV/EBITDA, MOIC) — so it needs a '
            'loaded corpus before it can score anything.</p>'
            '<p style="font-size:12px;margin:0;">'
            'Load the deal corpus from the Data Catalog, then reload this '
            'page.</p>',
            code="NIL",
        )
        return chartis_shell(
            _title() + body, title="Thesis Screening",
            active_nav="/deal-screening",
            extra_css=_EXPLAINER_CSS,
        )

    params = _urlparse.parse_qs(query or "")
    cfg = _parse_config(params)
    filter_decision = (params.get("decision", [""])[0] or "").upper()

    try:
        results = screen_corpus(corpus, cfg)
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Screening run failed",
            empty_note(f"screen_corpus raised: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            _title() + body, title="Thesis Screening",
            active_nav="/deal-screening",
            extra_css=_EXPLAINER_CSS,
        )

    counts = Counter(r.decision.upper() for r in results)

    # Apply decision filter for display, sort by risk descending
    filtered = results
    if filter_decision in ("PASS", "WATCH", "FAIL"):
        filtered = [r for r in results if r.decision.upper() == filter_decision]
    filtered_sorted = sorted(
        filtered,
        key=lambda r: (r.risk_composite or 0),
        reverse=True,
    )

    # Cap displayed rows
    display_cap = 200
    display = filtered_sorted[:display_cap]

    kpis = (
        ck_kpi_block("Corpus Deals", str(len(corpus)), "screened")
        + ck_kpi_block("Pass Rate",
                        fmt_pct(counts.get("PASS", 0) / len(results) if results else 0),
                        "clear all thresholds")
        + ck_kpi_block("Watch Rate",
                        fmt_pct(counts.get("WATCH", 0) / len(results) if results else 0),
                        "soft flags")
        + ck_kpi_block("Fail Rate",
                        fmt_pct(counts.get("FAIL", 0) / len(results) if results else 0),
                        "hard rejections")
        + ck_kpi_block("Showing", str(len(display)),
                        f"of {len(filtered)} matching filter")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    config_fields = {
        "max_composite_risk_score": cfg.max_composite_risk_score,
        "watch_composite_risk_score": cfg.watch_composite_risk_score,
        "max_ev_ebitda": cfg.max_ev_ebitda,
        "watch_ev_ebitda": cfg.watch_ev_ebitda,
        "min_moic_threshold": cfg.min_moic_threshold,
        "max_medicaid_pct": cfg.max_medicaid_pct,
        "min_ev_mm": cfg.min_ev_mm,
    }

    form_panel = small_panel(
        "Your thesis — set the thresholds",
        _controls_form(config_fields, filter_decision),
        code="FIT",
    )

    decision_strip = _decision_strip(counts, len(results))

    rows = "".join(_result_row(r) for r in display)
    results_table = (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>'
        f'<th>Deal</th>'
        f'<th>Decision</th>'
        f'<th class="num">Risk</th>'
        f'<th>Heuristic</th>'
        f'<th class="num">Data %</th>'
        f'<th>Top Reason</th>'
        f'</tr></thead>'
        f'<tbody>{rows}</tbody></table></div>'
    )

    title_block = _title(
        counts.get("PASS", 0), counts.get("WATCH", 0),
        counts.get("FAIL", 0), len(results),
    )
    n_deals = len(results)
    pass_rate = (counts.get("PASS", 0) / n_deals) if n_deals else 0.0
    explainer_html = (
        '<p class="ck-ds-explainer">'
        '<em>How would your thesis screen a representative deal set?</em> '
        f"Set your thesis as thresholds — max risk, valuation ceiling (EV/EBITDA), "
        f"return floor (MOIC), payer-mix and size limits — and PE Desk runs the full "
        f"{n_deals}-deal illustrative corpus against them. The <b>pass rate</b> is your "
        f"thesis&rsquo;s base rate: the share of the corpus that would clear it. A high "
        f"pass rate means a permissive thesis; a low one means you&rsquo;re selective. "
        f"Every deal&rsquo;s PASS / WATCH / FAIL verdict and reason is below. "
        f'For the real, source-linked deals, see '
        f'<a href="/verified-deals" style="color:inherit;text-decoration:underline;">Verified Deals</a>.'
        '</p>'
    )
    howto = (
        '<div class="ds-howto">'
        '<div class="ds-step"><div class="ds-step-n">STEP 1</div>'
        '<div class="ds-step-t">Set your thesis</div>'
        '<div class="ds-step-d">Enter the thresholds a deal must clear — risk, '
        'EV/EBITDA, MOIC, Medicaid, size.</div></div>'
        '<div class="ds-step"><div class="ds-step-n">STEP 2</div>'
        '<div class="ds-step-t">Screen the corpus</div>'
        f'<div class="ds-step-d">PE Desk scores all {n_deals} corpus deals against '
        'your thesis and labels each PASS / WATCH / FAIL.</div></div>'
        '<div class="ds-step"><div class="ds-step-n">STEP 3</div>'
        '<div class="ds-step-t">Read the pass rate</div>'
        f'<div class="ds-step-d">{pass_rate:.0%} of deals clear this thesis — your base '
        'rate. Tighten a lever and watch it move.</div></div>'
        '</div>'
    )

    body = (
        title_block
        + explainer_html
        + howto
        + kpi_strip
        + form_panel
        + ck_section_header(
            "DECISION MIX",
            f"across {len(results)} corpus deals under current thresholds",
        )
        + decision_strip
        + ck_section_header(
            "RANKED RESULTS",
            f"top {len(display)} by risk composite" + (
                f" · filter={filter_decision}" if filter_decision else ""
            ),
            count=len(filtered),
        )
        + small_panel(
            f"Screening output ({len(display)} of {len(filtered)})",
            results_table,
            code="OUT",
        )
    )

    return chartis_shell(
        body,
        title="Thesis Screening",
        active_nav="/deal-screening",
        extra_css=_EXPLAINER_CSS,
    )
