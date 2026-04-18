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
    fields = [
        ("max_composite_risk_score", "Max Risk Score", "0-100"),
        ("watch_composite_risk_score", "Watch Threshold", "0-100"),
        ("max_ev_ebitda", "Max EV/EBITDA", "x"),
        ("watch_ev_ebitda", "Watch EV/EBITDA", "x"),
        ("min_moic_threshold", "Min MOIC", "x"),
        ("max_medicaid_pct", "Max Medicaid %", "0-1"),
        ("min_ev_mm", "Min EV ($M)", ""),
    ]
    inputs = []
    for key, label, unit in fields:
        val = config.get(key, "")
        inputs.append(
            f'<label style="display:flex;flex-direction:column;gap:2px;'
            f'font-family:var(--ck-mono);font-size:10px;color:{P["text_faint"]};">'
            f'<span style="letter-spacing:0.10em;">{_html.escape(label)}'
            + (
                f' <span style="color:{P["text_faint"]};font-size:9px;">· {unit}</span>'
                if unit else ""
            )
            + f'</span>'
            f'<input name="{key}" value="{val}" type="number" step="any" '
            f'style="width:100px;background:{P["panel_alt"]};'
            f'border:1px solid {P["border"]};color:{P["text"]};'
            f'font-family:var(--ck-mono);font-size:11px;padding:4px 6px;'
            f'border-radius:2px;">'
            f'</label>'
        )
    decision_options = "".join(
        f'<option value="{v}"{" selected" if v == filter_decision else ""}>{_html.escape(v or "All")}</option>'
        for v in ("", "FAIL", "WATCH", "PASS")
    )
    decision_input = (
        f'<label style="display:flex;flex-direction:column;gap:2px;'
        f'font-family:var(--ck-mono);font-size:10px;color:{P["text_faint"]};">'
        f'<span style="letter-spacing:0.10em;">Show Decision</span>'
        f'<select name="decision" style="background:{P["panel_alt"]};'
        f'border:1px solid {P["border"]};color:{P["text"]};'
        f'font-family:var(--ck-mono);font-size:11px;padding:4px 6px;'
        f'border-radius:2px;min-width:100px;">{decision_options}</select>'
        f'</label>'
    )
    inputs.append(decision_input)
    submit = (
        f'<button type="submit" style="background:{P["accent"]};color:#fff;'
        f'border:none;font-family:var(--ck-mono);font-size:10px;'
        f'font-weight:600;letter-spacing:0.10em;padding:6px 14px;'
        f'border-radius:3px;align-self:flex-end;cursor:pointer;'
        f'text-transform:uppercase;">Re-run Screen</button>'
    )
    return (
        f'<form method="get" action="/deal-screening" '
        f'style="display:flex;gap:10px;align-items:flex-end;flex-wrap:wrap;">'
        f'{"".join(inputs)}{submit}</form>'
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
            body, title="Deal Screening",
            active_nav="/deal-screening",
            subtitle="Module unavailable",
        )

    corpus = load_corpus_deals()
    if not corpus:
        body = small_panel(
            "Deal screening — no corpus",
            empty_note("No corpus available for screening."),
            code="NIL",
        )
        return chartis_shell(
            body, title="Deal Screening",
            active_nav="/deal-screening",
            subtitle="Corpus unavailable",
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
            body, title="Deal Screening",
            active_nav="/deal-screening",
            subtitle="Screen raised",
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
        "Screening controls",
        _controls_form(config_fields, filter_decision),
        code="CFG",
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

    intro = (
        f'<p style="color:{P["text_dim"]};font-size:12px;line-height:1.6;'
        f'margin-bottom:10px;">'
        f'Runs every corpus deal through <code style="color:{P["accent"]};'
        f'font-family:var(--ck-mono);">screen_corpus(deals, config)</code> and '
        f'returns one of PASS / WATCH / FAIL per deal. Tighten thresholds below '
        f'to see the decision mix shift, or filter to a specific decision. '
        f'Sortable by any column.</p>'
    )

    body = (
        intro
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
        title="Deal Screening",
        active_nav="/deal-screening",
        subtitle=f"{counts.get('PASS',0)} pass · {counts.get('WATCH',0)} watch · "
                 f"{counts.get('FAIL',0)} fail · {len(results)} total",
    )
