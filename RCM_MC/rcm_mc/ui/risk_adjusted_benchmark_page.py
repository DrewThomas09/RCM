"""Risk-Adjusted Benchmarking surface — `/diligence/risk-adjusted-benchmark`.

Interactive companion to ``diligence.risk_adjustment``. A partner enters
the target's metric, its panel RAF, and a peer cohort's values; the page
returns the observed-to-expected (O/E) verdict that separates the
case-mix story from the operator story — the single most load-bearing
analytic in the stack, made usable without writing code.

Read-only: the form is GET (no state change), so a result URL is
shareable and the page can never 500 a partner — bad or empty input
falls back to the landing/worked-example state.
"""
from __future__ import annotations

import html
from typing import Dict, List, Optional, Tuple

from ..diligence.risk_adjustment import RiskAdjustedBenchmark, risk_adjust_metric
from ._chartis_kit import (
    chartis_shell,
    ck_kpi_block,
    ck_page_title,
    ck_panel,
    ck_section_header,
)

_ROUTE = "/diligence/risk-adjusted-benchmark"

# A worked example shown on the landing page — the canonical "sicker
# panel, not a worse operator" case from the module README.
_EXAMPLE = {
    "metric": "cost_pmpm",
    "target": "130",
    "raf": "1.30",
    "peers": "100, 110, 90, 105",
    "peer_rafs": "1.0, 1.0, 1.0, 1.0",
    "lower": "1",
}


def _parse_floats(text: str) -> List[float]:
    """Parse a comma/space-separated list of floats, skipping blanks."""
    out: List[float] = []
    for tok in text.replace("\n", ",").replace(" ", ",").split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.append(float(tok))
        except ValueError:
            continue
    return out


def _form(values: Dict[str, str]) -> str:
    """The GET input form, pre-filled from ``values`` (all escaped)."""
    def v(k: str) -> str:
        return html.escape(values.get(k, ""), quote=True)

    lower_sel_yes = "selected" if values.get("lower", "1") != "0" else ""
    lower_sel_no = "selected" if values.get("lower", "1") == "0" else ""
    return (
        f'<form method="get" action="{_ROUTE}" '
        'style="display:grid;gap:12px;max-width:640px">'
        '<label style="display:grid;gap:4px">'
        '<span style="font-size:13px;color:#3a424d">Metric name</span>'
        f'<input name="metric" value="{v("metric")}" placeholder="cost_pmpm" '
        'style="padding:8px;border:1px solid #c9c2b4;border-radius:6px"></label>'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">'
        '<label style="display:grid;gap:4px">'
        '<span style="font-size:13px;color:#3a424d">Target value</span>'
        f'<input name="target" value="{v("target")}" inputmode="decimal" '
        'style="padding:8px;border:1px solid #c9c2b4;border-radius:6px"></label>'
        '<label style="display:grid;gap:4px">'
        '<span style="font-size:13px;color:#3a424d">Target panel RAF</span>'
        f'<input name="raf" value="{v("raf")}" placeholder="1.00" '
        'inputmode="decimal" '
        'style="padding:8px;border:1px solid #c9c2b4;border-radius:6px"></label>'
        '</div>'
        '<label style="display:grid;gap:4px">'
        '<span style="font-size:13px;color:#3a424d">Peer values '
        '(comma-separated)</span>'
        f'<input name="peers" value="{v("peers")}" '
        'placeholder="100, 110, 90, 105" '
        'style="padding:8px;border:1px solid #c9c2b4;border-radius:6px"></label>'
        '<label style="display:grid;gap:4px">'
        '<span style="font-size:13px;color:#3a424d">Peer RAFs '
        '(optional, comma-separated — defaults to 1.0)</span>'
        f'<input name="peer_rafs" value="{v("peer_rafs")}" '
        'placeholder="1.0, 1.0, 1.0, 1.0" '
        'style="padding:8px;border:1px solid #c9c2b4;border-radius:6px"></label>'
        '<label style="display:grid;gap:4px">'
        '<span style="font-size:13px;color:#3a424d">Metric polarity</span>'
        '<select name="lower" '
        'style="padding:8px;border:1px solid #c9c2b4;border-radius:6px">'
        f'<option value="1" {lower_sel_yes}>Lower is better '
        '(cost, readmissions, ED)</option>'
        f'<option value="0" {lower_sel_no}>Higher is better '
        '(quality, gap-closure)</option>'
        '</select></label>'
        '<div><button type="submit" '
        'style="padding:10px 20px;background:#155752;color:#fff;border:none;'
        'border-radius:6px;font-weight:600;cursor:pointer">'
        'Run benchmark</button></div>'
        '</form>'
    )


def _result_panel(b: RiskAdjustedBenchmark) -> str:
    """Render the O/E benchmark result."""
    raw_gap = (b.raw_ratio - 1.0) * 100
    oe_gap = (b.oe_ratio - 1.0) * 100
    cm_gap = (b.case_mix_effect - 1.0) * 100
    kpis = "".join([
        ck_kpi_block("O/E Ratio", f"{b.oe_ratio:.2f}",
                     sub=f"{oe_gap:+.1f}% vs case-mix expectation"),
        ck_kpi_block("Verdict", b.verdict.value,
                     sub="after case-mix adjustment"),
        ck_kpi_block("Raw Gap to Peers", f"{raw_gap:+.1f}%",
                     sub="before adjustment"),
        ck_kpi_block("Case-Mix Effect", f"{cm_gap:+.1f}%",
                     sub="explained by panel acuity"),
    ])
    rows = [
        ("Target value", f"{b.target_value:,.2f}"),
        ("Target panel RAF", f"{b.target_raf:.2f}"),
        ("Peer mean value", f"{b.peer_mean_value:,.2f}"),
        ("Peer mean RAF", f"{b.peer_mean_raf:.2f}"),
        ("Case-mix expectation", f"{b.expected_value:,.2f}"),
        ("Percentile vs peers", f"{b.percentile_vs_peers * 100:.0f}th"),
        ("Peer cohort size", str(b.n_peers)),
    ]
    table = (
        "<table style='border-collapse:collapse;font-size:14px;margin-top:8px'>"
        + "".join(
            f"<tr><td style='padding:5px 18px 5px 0;color:#5b6470'>"
            f"{html.escape(k)}</td>"
            f"<td style='padding:5px 0;font-family:monospace;"
            f"font-variant-numeric:tabular-nums'>{html.escape(val)}</td></tr>"
            for k, val in rows
        )
        + "</table>"
    )
    body = (
        ck_section_header(html.escape(b.metric_name), eyebrow="O/E BENCHMARK")
        + f'<div class="ck-kpi-row">{kpis}</div>'
        + f"<p style='margin:14px 0 0;line-height:1.55'>{html.escape(b.headline)}</p>"
        + table
    )
    return ck_panel(body, title="Result", code=b.citation_key)


def render_risk_adjusted_benchmark_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    """Render the Risk-Adjusted Benchmarking page (landing or result)."""
    qs = qs or {}

    def first(k: str, d: str = "") -> str:
        return (qs.get(k) or [d])[0].strip()

    metric = first("metric") or "metric"
    target_raw = first("target")
    peers_raw = first("peers")
    raf_raw = first("raf") or "1.0"
    peer_rafs_raw = first("peer_rafs")
    lower = first("lower", "1") != "0"

    result_html = ""
    note = ""
    has_input = bool(target_raw and peers_raw)
    if has_input:
        result, err = _compute(
            metric, target_raw, raf_raw, peers_raw, peer_rafs_raw, lower,
        )
        if result is not None:
            result_html = _result_panel(result)
        else:
            note = (
                "<div style='margin:8px 0 16px;padding:10px 14px;"
                "background:#fcf3e9;border-left:3px solid #b8732a;"
                f"border-radius:4px'>{html.escape(err)}</div>"
            )

    # Form values: echo the user's input, or the example on a cold landing.
    if has_input:
        form_values = {
            "metric": metric, "target": target_raw, "raf": raf_raw,
            "peers": peers_raw, "peer_rafs": peer_rafs_raw,
            "lower": "1" if lower else "0",
        }
        example_html = ""
    else:
        form_values = dict(_EXAMPLE)
        # Show the worked example result so a cold landing isn't empty.
        ex = _compute(
            _EXAMPLE["metric"], _EXAMPLE["target"], _EXAMPLE["raf"],
            _EXAMPLE["peers"], _EXAMPLE["peer_rafs"], True,
        )[0]
        example_html = (
            ck_panel(
                "<p style='margin:0 0 10px;color:#3a424d'>Worked example — a "
                "target running 30% above peers on raw cost, but with a panel "
                "30% sicker (RAF 1.30). Risk adjustment shows it performs "
                "<strong>in line</strong> with expectation; the raw gap was "
                "case mix, not the operator.</p>"
                + (_result_panel(ex) if ex is not None else ""),
                title="Example",
            )
        )

    explainer = (
        "<p style='margin:0 0 14px;line-height:1.55;color:#3a424d'>"
        "Comparing a target's cost or outcome to peers without normalizing "
        "for case mix gets you fooled by a sicker (or healthier) panel. This "
        "divides observed performance by the case-mix expectation "
        "(peer rate per unit of RAF × the target's RAF) to give the "
        "<strong>observed-to-expected (O/E)</strong> ratio every payer and "
        "ACO uses. O/E ≈ 1.0 means the target performs as its case mix "
        "predicts; a gap that survives adjustment is an operator signal, "
        "not a panel artifact.</p>"
    )
    form_panel = ck_panel(explainer + _form(form_values),
                          title="Inputs", code="RA1")

    body = (
        ck_page_title(
            "Risk-Adjusted Benchmarking",
            eyebrow="DILIGENCE · CMS-HCC",
            meta="Observed-to-expected (O/E) vs a peer cohort, "
                 "normalized for case mix",
        )
        + note
        + result_html
        + form_panel
        + example_html
    )
    return chartis_shell(
        body, "Risk-Adjusted Benchmarking", active_nav="diligence",
        subtitle="Separate the case-mix story from the operator story",
    )


def _compute(
    metric: str, target_raw: str, raf_raw: str, peers_raw: str,
    peer_rafs_raw: str, lower: bool,
) -> Tuple[Optional[RiskAdjustedBenchmark], str]:
    """Validate inputs and run the benchmark. Returns (result, error);
    exactly one is meaningful. Never raises — the page must stay 200."""
    try:
        target_value = float(target_raw)
    except ValueError:
        return None, f"Could not parse target value '{target_raw}'."
    try:
        target_raf = float(raf_raw)
    except ValueError:
        return None, f"Could not parse target RAF '{raf_raw}'."
    if target_raf <= 0:
        return None, "Target RAF must be positive."
    peers = _parse_floats(peers_raw)
    if not peers:
        return None, "No peer values could be parsed."
    peer_rafs = _parse_floats(peer_rafs_raw) if peer_rafs_raw else [1.0] * len(peers)
    if len(peer_rafs) != len(peers):
        return None, (
            f"Peer RAF count ({len(peer_rafs)}) must match peer value "
            f"count ({len(peers)}), or be left blank."
        )
    if any(r <= 0 for r in peer_rafs):
        return None, "Peer RAFs must all be positive."
    try:
        b = risk_adjust_metric(
            metric or "metric", target_value=target_value,
            target_raf=target_raf, peer_values=peers, peer_rafs=peer_rafs,
            lower_is_better=lower,
        )
    except ValueError as e:
        return None, f"Benchmark failed: {e}"
    return b, ""
