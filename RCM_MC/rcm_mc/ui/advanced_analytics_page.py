"""Advanced Analytics surface — `/diligence/advanced-analytics`.

Read-only editorial page that makes the native analytics stack
(``diligence.advanced_analytics``) partner-visible and discoverable. It
runs the composition facade on a small, deterministic, clearly-labelled
*illustrative* deal so the page always renders, and surfaces:

    * the rolled-up EBITDA-at-risk and the count of marts that ran,
    * the citation-keyed findings list (one line per mart), and
    * an explainer of what each mart answers.

This is intentionally NOT wired to a specific deal's
``DealAnalysisPacket`` yet — it is the discoverability + worked-example
surface. Per-deal wiring (feeding a real CCD into the facade) is the
follow-up; this page gives partners the map and a live demo first.
"""
from __future__ import annotations

import html
from typing import Dict, List, Optional

from ..diligence.advanced_analytics import (
    AdvancedAnalyticsInputs,
    AdvancedAnalyticsResult,
    run_advanced_analytics,
)
from ..diligence.episodes import ClaimLine, EpisodeDefinition
from ..diligence.pmpm import PMPMPeriod
from ..diligence.policy_shock import PanelData
from ..diligence.quality_measures import evaluate_measure, get_measure
from ..diligence.risk_adjustment import Demographics
from ._chartis_kit import (
    chartis_shell,
    ck_kpi_block,
    ck_page_title,
    ck_panel,
    ck_section_header,
    ck_signal_badge,
)

# One line per shipped mart — the "what does this answer" map shown on
# the page so the stack is legible without reading the code.
_MART_GUIDE = [
    ("RA1", "Risk adjustment (CMS-HCC)",
     "Case-mix-normalized O/E benchmark — separates a sicker panel from an inefficient operator."),
    ("HB1", "Hierarchical benchmarking",
     "Empirical-Bayes shrinkage so a low-volume site isn't ranked an outlier on noise alone."),
    ("PM1", "Risk-adjusted PMPM trend",
     "Splits real cost inflation from case-mix drift; projects EBITDA-at-risk."),
    ("PS1", "Policy-shock evaluator (DiD)",
     "Quasi-experimental effect of OBBBA / MA / PFS shocks, with parallel-trends + placebo checks."),
    ("SV1", "Survival (retention / readmission)",
     "Kaplan-Meier + Cox hazards on time-to-event for VBC and patient-LTV theses."),
    ("EP1", "Episode-of-care grouping",
     "Anchor-triggered episodes + service-line P&L — the unit PE underwrites on."),
    ("QM1", "Quality measures (HEDIS/CQM)",
     "Gap-count to the next threshold + a weighted star composite."),
    ("SP1", "Spatial competition",
     "Huff capture, Moran's I / LISA, and new-entrant volume-at-risk — the rigorous service area."),
    ("RN1", "Referral network",
     "Shared-patient graph: PageRank hubs, broker betweenness, communities, captive-volume moat."),
    ("IN-BEN", "Billing-integrity screen",
     "Benford first-digit + first-two-digits test on billed amounts before any total is trusted."),
]


def _demo_inputs() -> AdvancedAnalyticsInputs:
    """A small, deterministic, illustrative deal that exercises every
    facade section. Fixed inputs (and a fixed RNG seed for the DiD
    panel) so the page renders identically every load — this is a
    worked example, not real deal data."""
    # A DiD panel: 40 markets, 6 periods, treated lose ~4% post-policy.
    import numpy as np
    rng = np.random.default_rng(7)
    units: List[str] = []
    periods: List[int] = []
    outcome: List[float] = []
    treated: List[bool] = []
    for u in range(40):
        is_tr = u < 20
        fe = rng.normal(100, 8)
        for t in range(6):
            y = fe + 2.0 * t + (-0.04 * fe if (is_tr and t >= 3) else 0.0)
            y += rng.normal(0, 0.4)
            units.append(f"m{u}")
            periods.append(t)
            outcome.append(float(y))
            treated.append(is_tr)
    policy_panel = PanelData(units, periods, outcome, treated, 3)

    return AdvancedAnalyticsInputs(
        panel=[
            (Demographics(78, "M"), ["E11.42", "I50.9", "J44.9"]),
            (Demographics(82, "F"), ["I50.9", "N18.5"]),
            (Demographics(69, "M"), ["E11.9"]),
            (Demographics(74, "F"), ["I25.10", "E11.42"]),
        ],
        unit_ids=["Clinic A", "Clinic B", "Clinic C", "Clinic D", "Clinic E"],
        unit_estimates=[1.92, 1.18, 1.05, 0.98, 1.02],
        unit_ses=[0.62, 0.05, 0.12, 0.12, 0.11],
        pmpm_periods=[
            PMPMPeriod("2023", 1000.0, 1.00),
            PMPMPeriod("2024", 1085.0, 1.05),
            PMPMPeriod("2025", 1180.0, 1.10),
        ],
        pmpm_periods_per_year=1.0,
        pmpm_annual_member_months=120_000,
        policy_panel=policy_panel,
        policy_exposed_revenue_usd=50_000_000,
        policy_att_is_pct=True,
        survival_durations=[12, 30, 45, 60, 75, 90, 90, 20, 35, 50],
        survival_events=[1, 1, 0, 1, 1, 0, 1, 1, 0, 1],
        episode_claims=[
            ClaimLine("p1", 100, 18000.0, "inpatient", revenue=21000.0),
            ClaimLine("p1", 130, 2200.0, "rehab", revenue=1800.0),
            ClaimLine("p2", 100, 26000.0, "surgery", revenue=30000.0),
            ClaimLine("p2", 120, 1500.0, "physician", revenue=1400.0),
        ],
        episode_definition=EpisodeDefinition(
            frozenset({"inpatient", "surgery"}), post_window_days=90,
        ),
        quality_results=[
            evaluate_measure(get_measure("HBA1C_CONTROL"), 640, 1000),
            evaluate_measure(get_measure("BP_CONTROL"), 690, 1000),
            evaluate_measure(get_measure("PLAN_ALL_READMIT"), 170, 1000),
        ],
        billed_amounts=(10 ** np.random.default_rng(3).uniform(0, 5, 3000)).tolist(),
    )


def _verdict_tone(res: AdvancedAnalyticsResult) -> str:
    """Map the integrity verdict to a signal-badge tone."""
    if res.integrity is None:
        return "neutral"
    return {
        "CONFORMING": "positive", "MARGINAL": "warning",
        "NONCONFORMING": "negative", "INSUFFICIENT": "neutral",
    }.get(res.integrity.verdict.value, "neutral")


def render_advanced_analytics_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    """Render the Advanced Analytics surface."""
    res = run_advanced_analytics(_demo_inputs())

    n_marts = sum(1 for s in (
        res.risk, res.hierarchical, res.pmpm, res.policy, res.survival,
        res.episodes, res.quality, res.integrity,
    ) if s is not None)

    # ── KPI strip ────────────────────────────────────────────────────
    ebitda_m = res.total_ebitda_at_risk_usd / 1e6
    integrity_label = (
        res.integrity.verdict.value if res.integrity is not None else "—"
    )
    kpis = "".join([
        ck_kpi_block("Marts Run", str(n_marts), sub="of 8 facade sections"),
        ck_kpi_block(
            "EBITDA at Risk", f"${ebitda_m:,.2f}M",
            sub="PMPM trend + adverse policy overlay",
        ),
        ck_kpi_block(
            "Panel RAF",
            f"{res.risk.mean_raf:.2f}" if res.risk else "—",
            sub="case-mix burden (1.00 = avg)",
        ),
        ck_kpi_block(
            "Billing Integrity", integrity_label,
            sub="Benford first-digit screen",
        ),
    ])
    kpi_panel = f'<div class="ck-kpi-row">{kpis}</div>'

    # ── Findings list ────────────────────────────────────────────────
    finding_items = "".join(
        f"<li style='margin:6px 0;line-height:1.5'>{html.escape(f)}</li>"
        for f in res.findings
    )
    findings_body = (
        ck_section_header("Findings", eyebrow="ILLUSTRATIVE DEAL")
        + f"<ul style='padding-left:20px;margin:0'>{finding_items}</ul>"
        + "<p style='margin-top:14px;font-size:13px;color:#5b6470'>"
        + "Each line is one mart's headline, prefixed with its provenance "
        + "citation key. Figures are from a fixed synthetic deal for "
        + "illustration — wire a real CCD into "
        + "<code>run_advanced_analytics</code> for live numbers.</p>"
    )
    findings_panel = ck_panel(findings_body, title="Composite Findings",
                              code="AA1")

    # ── Mart guide ───────────────────────────────────────────────────
    rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 12px;font-family:monospace;color:#155752;"
        f"white-space:nowrap'>[{html.escape(key)}]</td>"
        f"<td style='padding:6px 12px;font-weight:600'>{html.escape(name)}</td>"
        f"<td style='padding:6px 12px;color:#3a424d'>{html.escape(desc)}</td>"
        f"</tr>"
        for key, name, desc in _MART_GUIDE
    )
    guide_body = (
        ck_section_header("The stack", eyebrow="10 COMPOSING MARTS")
        + "<p style='margin:0 0 12px;color:#3a424d'>Each mart is native "
        + "(numpy + stdlib, zero new dependencies) and carries a "
        + "<code>source_module</code>/<code>citation_key</code> so every "
        + "number traces back through the provenance graph. The facade "
        + "composes whichever marts have inputs.</p>"
        + "<table style='border-collapse:collapse;width:100%;font-size:14px'>"
        + f"<tbody>{rows}</tbody></table>"
    )
    guide_panel = ck_panel(guide_body, title="What each mart answers")

    badge = ck_signal_badge(
        f"Integrity: {integrity_label}", tone=_verdict_tone(res),
    )

    body = (
        ck_page_title(
            "Advanced Analytics",
            eyebrow="DILIGENCE · NATIVE STACK",
            meta="Tuva/Myelin patterns, reimplemented natively · illustrative demo",
        )
        + f"<div style='margin:8px 0 18px'>{badge}</div>"
        + kpi_panel
        + findings_panel
        + guide_panel
    )
    return chartis_shell(
        body, "Advanced Analytics", active_nav="diligence",
        subtitle="Composed native analytics — risk adjustment → "
                 "shrinkage → PMPM → policy shock → survival → episodes → "
                 "quality → spatial → referral → integrity",
    )
