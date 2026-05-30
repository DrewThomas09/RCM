"""PEdesk Guide metric registry — conservative, read-only.

Standard textbook formulas (EV/EBITDA, EBITDA margin, leverage, days in
AR, …) are stated with formula_confidence = ``inferred`` (the formula is
the standard definition; whether PEdesk computes it exactly that way is
inferred, not confirmed from code). Proprietary / model-derived metrics
keep formula = "Needs source documentation." + ``needs_validation``.
No precise formula is invented for anything model-specific.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .types import (
    DataConfidence,
    FormulaConfidence,
    MetricContext,
    SourceConfidence,
)

_NEEDS = "Needs source documentation."
_BASE_NOTES = [
    "PEdesk Guide is read-only and explanatory — it never computes, "
    "re-runs, or alters this metric.",
    "If the exact PEdesk formula or data lineage isn't in this entry, say "
    "it needs source documentation rather than inventing it.",
]

# shorthands
_DOC = FormulaConfidence.DOCUMENTED
_INF = FormulaConfidence.INFERRED
_NV = FormulaConfidence.NEEDS_VALIDATION
_NA = FormulaConfidence.NOT_APPLICABLE
_OBS = DataConfidence.OBSERVED_TARGET_DATA
_PUB = DataConfidence.PUBLIC_BENCHMARK_DATA
_USR = DataConfidence.USER_ENTERED_DATA
_EST = DataConfidence.MODEL_ESTIMATE
_MIX = DataConfidence.MIXED
_UNK = DataConfidence.UNKNOWN


def _m(metric_id: str, label: str, aliases: List[str], definition: str,
       why: str, interp: str, **kw: Any) -> MetricContext:
    d: Dict[str, Any] = dict(
        formula=_NEEDS,
        formula_confidence=_NV,
        source_types=[_UNK],
        common_misread=_NEEDS,
        caveats=[_NEEDS],
        related_metrics=[],
        related_routes=[],
        source_confidence=SourceConfidence.INFERRED_FROM_PAGE,
        data_confidence=_UNK,
    )
    d.update(kw)
    return MetricContext(
        metric_id=metric_id, label=label, aliases=aliases,
        definition=definition, why_it_matters=why,
        diligence_interpretation=interp,
        notes_for_assistant=list(_BASE_NOTES),
        last_reviewed_at="2026-05-22", owner="pedesk-guide", **d,
    )


_METRICS: List[MetricContext] = [
    # ── Financial / PE ──────────────────────────────────────────────
    _m("revenue", "Revenue", ["net revenue", "net patient revenue", "npr", "top line"],
       "Net patient/operating revenue — the cash-realizable top line.",
       "The base every margin and multiple is taken against.",
       "Confirm it's NET (after contractual allowances/bad debt), not gross charges.",
       source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["revenue_growth", "ebitda_margin"],
       related_routes=["/pipeline", "/diligence/value", "/portfolio",
                       "/cost-structure", "/diligence/qoe-memo"]),
    _m("revenue_growth", "Revenue Growth", ["growth", "topline growth", "yoy growth"],
       "Period-over-period percentage change in revenue.",
       "Organic growth is a core driver of the value-creation thesis.",
       "Separate organic growth from acquired/roll-up growth and rate vs volume.",
       formula="(revenue_t - revenue_{t-1}) / revenue_{t-1}", formula_confidence=_INF,
       source_types=[_OBS], data_confidence=_MIX, related_metrics=["revenue"],
       related_routes=["/pipeline", "/diligence/value", "/sector-momentum",
                       "/portfolio"]),
    _m("ebitda", "EBITDA", ["earnings before interest taxes depreciation amortization"],
       "Operating earnings before interest, taxes, depreciation, amortization.",
       "The cash-earnings base for multiples, leverage, and the bridge.",
       "Reported EBITDA differs from ADJUSTED EBITDA — confirm which is shown.",
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["adjusted_ebitda", "ebitda_margin", "ev_to_ebitda"],
       related_routes=["/diligence/value", "/pipeline/bridge",
                       "/diligence/qoe-memo", "/cost-structure"]),
    _m("adjusted_ebitda", "Adjusted EBITDA", ["adj ebitda", "pro forma ebitda", "qoe ebitda"],
       "EBITDA after add-backs/normalizations (one-offs, owner comp, pro-forma).",
       "The number deals are actually priced on; QoE exists to vet it.",
       "Every add-back is a negotiation — scrutinize quality and recurrence.",
       source_types=[_OBS, _USR], data_confidence=_MIX,
       caveats=["Add-backs are judgmental; aggressive add-backs inflate value."],
       related_metrics=["ebitda", "ebitda_bridge", "value_creation_opportunity"],
       related_routes=["/diligence/bridge-audit", "/diligence/qoe-memo"]),
    _m("ebitda_margin", "EBITDA Margin", ["margin", "ebitda %"],
       "EBITDA as a percentage of revenue.",
       "Profitability and operating-leverage read; drives margin-expansion theses.",
       "A thin/negative margin can be a turnaround base, not a disqualifier.",
       formula="EBITDA / revenue", formula_confidence=_INF,
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["ebitda", "operating_margin", "revenue"],
       related_routes=["/cost-structure", "/diligence/value",
                       "/diligence/benchmarks", "/portfolio"]),
    _m("enterprise_value", "Enterprise Value", ["ev", "tev"],
       "Total enterprise value (equity + net debt) of the business.",
       "The price tag the return math is built on.",
       "EV vs equity value differ by net debt — don't conflate.",
       formula="equity value + net debt (- cash)", formula_confidence=_INF,
       source_types=[_OBS, _EST], data_confidence=_MIX,
       related_metrics=["ev_to_ebitda", "ebitda", "debt"],
       related_routes=["/pipeline/bridge", "/comparables", "/entry-multiple",
                       "/exit-multiple", "/diligence/value"]),
    _m("ev_to_ebitda", "EV / EBITDA", ["ev/ebitda", "entry multiple", "ebitda multiple", "turns"],
       "Enterprise value divided by EBITDA — the headline valuation multiple.",
       "Entry multiple is the single biggest lever on returns.",
       "Compare against the right comp set (sector/size); a 'cheap' multiple may reflect risk.",
       formula="enterprise_value / EBITDA", formula_confidence=_INF,
       source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["enterprise_value", "ebitda", "exit_multiple"],
       related_routes=["/market-rates", "/comparables"]),
    _m("leverage", "Leverage", ["net leverage", "debt/ebitda", "turns of debt"],
       "Net debt as a multiple of EBITDA.",
       "Sets covenant headroom and amplifies both returns and downside risk.",
       "Compare against covenant max; high leverage on thin EBITDA is fragile.",
       formula="net debt / EBITDA", formula_confidence=_INF,
       source_types=[_OBS, _EST], data_confidence=_MIX,
       related_metrics=["debt", "covenant_cushion", "ebitda"],
       related_routes=["/diligence/covenant-stress"]),
    _m("debt", "Debt", ["total debt", "gross debt", "borrowings"],
       "Total/net interest-bearing debt in the capital structure.",
       "The denominator of deleveraging and the covenant base.",
       "Gross vs net debt (net of cash) differ — confirm which.",
       source_types=[_OBS, _EST], data_confidence=_MIX,
       related_metrics=["leverage", "covenant_cushion"],
       related_routes=["/cap-structure", "/debt-service",
                       "/covenant-headroom", "/debt-financing"]),
    _m("covenant_cushion", "Covenant Cushion", ["covenant headroom", "headroom", "cushion"],
       "How far EBITDA (or leverage) can move before a covenant trips.",
       "Thin cushion means a small EBITDA miss triggers a technical breach.",
       "Cushion shrinks fast under stress — read it against the stress scenarios.",
       source_types=[_EST], data_confidence=_MIX,
       related_metrics=["leverage", "debt", "payer_stress_impact"],
       related_routes=["/diligence/covenant-stress"]),
    _m("moic", "MOIC", ["multiple of invested capital", "multiple", "moc", "cash on cash"],
       "Total value returned to equity divided by equity invested.",
       "The dollar-return headline, less hold-sensitive than IRR.",
       "Gross vs net (after fees/carry) MOIC differ materially.",
       formula="total value to equity / invested equity", formula_confidence=_INF,
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["irr", "exit_multiple", "hold_period"],
       related_routes=["/comparable-outcomes", "/market-rates"]),
    _m("irr", "IRR", ["internal rate of return", "levered irr", "net irr", "gross irr"],
       "Annualized internal rate of return on the equity cash flows.",
       "The time-weighted return; the conventional ~20% PE-healthcare hurdle.",
       "IRR is hold-sensitive and flatters early distributions; pair with MOIC.",
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["moic", "hold_period"],
       related_routes=["/irr-dispersion"]),
    _m("exit_multiple", "Exit Multiple", ["exit ev/ebitda", "terminal multiple"],
       "The EV/EBITDA assumed at exit.",
       "Multiple expansion/compression is a major returns driver and assumption risk.",
       "An assumed exit multiple above entry must be justified, not assumed.",
       formula="exit enterprise_value / exit EBITDA", formula_confidence=_INF,
       source_types=[_EST, _PUB], data_confidence=_EST,
       related_metrics=["ev_to_ebitda", "moic"],
       related_routes=["/exit-multiple", "/diligence/exit-timing",
                       "/diligence/value", "/multiple-decomp"]),
    _m("hold_period", "Hold Period", ["hold", "hold years", "holding period"],
       "Years from acquisition close to exit.",
       "Sets the compounding window; PE-healthcare median is ~5-6 years.",
       "Short holds often imply distress or a strategic premium; long holds, a slower thesis.",
       formula="exit date - entry date (years)", formula_confidence=_INF,
       source_types=[_EST], data_confidence=_EST, related_metrics=["irr", "moic"],
       related_routes=["/hold-analysis", "/diligence/exit-timing",
                       "/hold-optimizer"]),
    _m("synergy_estimate", "Synergy Estimate", ["synergies", "cost synergies", "revenue synergies"],
       "Estimated cost/revenue synergies (often in a roll-up/platform thesis).",
       "Synergies underpin multiple-arbitrage and platform value-creation cases.",
       "Synergy estimates are routinely optimistic; weight by execution risk.",
       source_types=[_EST], data_confidence=_EST,
       caveats=["Cross-sell/revenue synergies carry high execution risk."],
       related_metrics=["value_creation_opportunity", "ebitda_bridge"],
       related_routes=["/pmi-integration", "/rollup-economics",
                       "/bolton-analyzer", "/diligence/value"]),
    _m("value_creation_opportunity", "Value Creation Opportunity",
       ["vco", "value opportunity", "ev uplift", "value creation"],
       "Estimated EBITDA/EV upside from the value-creation plan.",
       "Quantifies the upside thesis the deal is underwritten on.",
       "It is a model estimate of POTENTIAL, not realized or guaranteed value.",
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["ebitda_bridge", "synergy_estimate", "rcm_uplift",
                       "bridge_realization_probability"],
       related_routes=["/diligence/value", "/diligence/bridge-audit"]),
    _m("ebitda_bridge", "EBITDA Bridge", ["bridge", "value bridge", "ebitda walk"],
       "Decomposition of EBITDA from current to a pro-forma/target across "
       "value-creation levers.",
       "Shows where uplift comes from and how much each lever contributes.",
       "Gross lever impact differs from probability-weighted/realized impact.",
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["adjusted_ebitda", "value_creation_opportunity",
                       "bridge_realization_probability", "rcm_uplift"],
       related_routes=["/diligence/bridge-audit"]),

    # ── Revenue cycle ───────────────────────────────────────────────
    _m("denial_rate", "Denial Rate", ["initial denial rate", "idr", "denials"],
       "Share of submitted claims initially denied by payers.",
       "The starting point of RCM leakage; every downstream lever sits below it.",
       "Initial vs final (post-appeal) denial rate are very different numbers.",
       formula="denied claims / total claims submitted", formula_confidence=_INF,
       source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["clean_claim_rate", "rcm_uplift", "collections_leakage"],
       related_routes=["/diligence/denial-prediction"]),
    _m("net_collection_rate", "Net Collection Rate", ["ncr", "net collections"],
       "Net payments collected as a share of the amount allowed to be collected.",
       "Measures how much of collectible revenue actually lands.",
       "Net vs gross collection rate differ; net excludes contractual allowances.",
       formula="net payments / (charges - contractual adjustments)", formula_confidence=_INF,
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["gross_collection_rate", "bad_debt_rate"],
       related_routes=["/diligence/benchmarks", "/diligence/value",
                       "/rcm-benchmarks", "/diligence/qoe-memo"]),
    _m("gross_collection_rate", "Gross Collection Rate", ["gcr", "gross collections"],
       "Payments as a share of gross charges.",
       "A coarse collections read; heavily affected by chargemaster levels.",
       "GCR is distorted by gross-charge inflation — net collection rate is more meaningful.",
       formula="payments / gross charges", formula_confidence=_INF,
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["net_collection_rate"]),
    _m("days_in_ar", "Days in A/R", ["dar", "days sales outstanding", "dso", "ar days"],
       "Average days revenue sits in accounts receivable before collection.",
       "Working-capital and collections-efficiency signal; lower is better.",
       "Spikes can reflect a billing-system change or payer slowdown, not just inefficiency.",
       formula="accounts receivable / (net revenue / 365)", formula_confidence=_INF,
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["net_collection_rate", "collections_leakage"],
       related_routes=["/diligence/benchmarks", "/diligence/root-cause",
                       "/rcm-benchmarks", "/diligence/value"]),
    _m("clean_claim_rate", "Clean Claim Rate", ["ccr", "first-pass rate", "first pass yield"],
       "Share of claims accepted on first submission without rework.",
       "High clean-claim rate means less denial rework and faster cash.",
       "Definitions of 'clean' vary by system; confirm the denominator.",
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["denial_rate", "rcm_uplift"],
       related_routes=["/diligence/benchmarks", "/diligence/denial-prediction",
                       "/rcm-benchmarks", "/diligence/value"]),
    _m("bad_debt_rate", "Bad Debt Rate", ["bad debt", "write-off rate"],
       "Share of revenue written off as uncollectible.",
       "Direct leakage; rising self-pay/high-deductible plans push it up.",
       "Bad debt vs charity care are different write-off categories.",
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["net_collection_rate", "collections_leakage"]),
    _m("underpayment_rate", "Underpayment Rate", ["underpayments", "payer underpayment"],
       "Share/amount of claims paid below the contracted rate.",
       "Recoverable leakage — a common RCM value-creation lever.",
       "Requires contract modeling to detect; absence of a flag isn't absence of underpayment.",
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["payer_mix", "rcm_uplift"]),
    _m("payer_mix", "Payer Mix", ["payor mix", "payer concentration", "mix"],
       "Distribution of revenue/volume across Medicare, Medicaid, commercial, self-pay.",
       "The single biggest driver of reimbursement and pricing power.",
       "Day-mix vs revenue-mix differ; commercial share drives economics.",
       source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["medicare_exposure", "medicaid_exposure",
                       "commercial_payer_exposure", "payer_stress_impact"],
       related_routes=["/diligence/payer-stress", "/payer-intelligence"]),
    _m("medicare_exposure", "Medicare Exposure", ["medicare share", "medicare %", "medicare mix"],
       "Share of revenue/volume from Medicare.",
       "Government rates are administratively set; high exposure caps pricing power.",
       "Medicare Advantage vs traditional Medicare behave differently.",
       formula="Medicare revenue (or days) / total", formula_confidence=_INF,
       source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["payer_mix", "medicaid_exposure"]),
    _m("medicaid_exposure", "Medicaid Exposure", ["medicaid share", "medicaid %", "medicaid mix"],
       "Share of revenue/volume from Medicaid.",
       "Lowest-reimbursing payer; high exposure pressures margins.",
       "Medicaid expansion/redetermination shifts can move this materially.",
       formula="Medicaid revenue (or days) / total", formula_confidence=_INF,
       source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["payer_mix", "medicare_exposure"]),
    _m("commercial_payer_exposure", "Commercial Payer Exposure",
       ["commercial share", "commercial mix", "commercial %"],
       "Share of revenue/volume from commercial payers.",
       "Highest-reimbursing payer; commercial share is the pricing-power engine.",
       "Single-payer concentration within commercial is a hidden risk.",
       formula="commercial revenue (or days) / total", formula_confidence=_INF,
       source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["payer_mix", "payer_stress_impact"]),
    _m("rcm_uplift", "RCM Uplift", ["revenue cycle uplift", "rcm opportunity", "rcm ebitda uplift"],
       "Estimated EBITDA improvement from revenue-cycle interventions.",
       "Quantifies the core operational value-creation lever in RCM-led deals.",
       "It is a MODEL ESTIMATE of opportunity, not realized improvement.",
       source_types=[_EST], data_confidence=_EST,
       caveats=["Estimate from current metrics vs benchmark targets; realization is uncertain."],
       related_metrics=["denial_rate", "days_in_ar", "collections_leakage",
                       "ebitda_bridge"],
       related_routes=["/diligence/denial-prediction", "/predictive-screener"]),
    _m("collections_leakage", "Collections Leakage", ["revenue leakage", "collections leakage"],
       "Estimated collectible revenue lost to denials, underpayments, write-offs.",
       "Sizes the recoverable RCM opportunity.",
       "An estimate of recoverable dollars, not a guaranteed recovery.",
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["denial_rate", "bad_debt_rate", "underpayment_rate",
                       "rcm_uplift"]),

    # ── Provider / physician ────────────────────────────────────────
    _m("physician_attrition", "Physician Attrition", ["provider attrition", "physician turnover", "md turnover"],
       "Rate at which physicians/providers leave the group.",
       "Provider departures destroy revenue and referral relationships fast.",
       "Key-physician concentration matters more than the average rate.",
       source_types=[_OBS, _EST], data_confidence=_MIX,
       related_metrics=["referral_leakage", "panel_size"],
       related_routes=["/diligence/physician-attrition"]),
    _m("provider_productivity", "Provider Productivity", ["productivity", "provider output"],
       "Output per provider (often wRVU- or visit-based).",
       "Drives revenue capacity and the de-novo/expansion case.",
       "Specialty-mix differences make cross-provider comparison tricky.",
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["wrvu", "panel_size", "provider_contribution_margin"],
       related_routes=["/diligence/physician-eu"]),
    _m("wrvu", "wRVU", ["work rvu", "rvu", "work relative value unit", "wrvus"],
       "Work Relative Value Unit — CMS productivity unit for physician work.",
       "The standard currency for physician productivity and compensation.",
       "wRVU is WORK rvu only — not total RVU (which adds practice-expense/malpractice).",
       source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["provider_productivity", "compensation_to_collections"],
       related_routes=["/diligence/physician-eu"]),
    _m("compensation_to_collections", "Compensation-to-Collections",
       ["comp to collections", "comp ratio", "comp/collections"],
       "Provider compensation as a share of the collections they generate.",
       "Core physician-economics ratio; high ratios compress group margin.",
       "Benchmarks vary widely by specialty and employment model.",
       formula="provider compensation / provider collections", formula_confidence=_INF,
       source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["provider_contribution_margin", "wrvu"],
       related_routes=["/diligence/physician-eu"]),
    _m("provider_contribution_margin", "Provider Contribution Margin",
       ["contribution margin", "provider margin"],
       "Margin a provider contributes after direct costs (incl. comp).",
       "Shows which providers/sites are economically additive.",
       "Allocation of shared/overhead costs changes the answer.",
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["compensation_to_collections", "provider_productivity"]),
    _m("panel_size", "Panel Size", ["patient panel", "panel"],
       "Number of patients attributed to a provider/practice.",
       "Capacity and continuity proxy; supports volume forecasts.",
       "Attributed vs active panel differ; stale panels overstate capacity.",
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["provider_productivity", "referral_leakage"]),
    _m("referral_leakage", "Referral Leakage", ["network leakage", "out-of-network referrals"],
       "Share of referrals leaving the network/system.",
       "Lost downstream revenue; a CIN/network value-creation target.",
       "Leakage can be clinically appropriate; not all leakage is recoverable.",
       source_types=[_OBS, _EST], data_confidence=_MIX,
       related_metrics=["panel_size", "physician_attrition"]),
    _m("app_support_ratio", "APP Support Ratio", ["app ratio", "advanced practice ratio", "app:md ratio"],
       "Ratio of advanced practice providers (NP/PA) to physicians.",
       "A care-model/efficiency lever; higher APP leverage can lift margin.",
       "Optimal ratio is specialty- and regulation-dependent.",
       source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["provider_productivity"]),

    # ── Hospital / HCRIS ────────────────────────────────────────────
    _m("bed_count", "Bed Count", ["beds", "licensed beds", "staffed beds"],
       "Number of hospital beds (licensed or staffed).",
       "Scale proxy used for sizing and peer-matching.",
       "Licensed vs staffed vs available beds differ; occupancy uses available.",
       source_types=[_PUB], data_confidence=_PUB,
       related_metrics=["occupancy_rate"], related_routes=["/diligence/hcris-xray"]),
    _m("occupancy_rate", "Occupancy Rate", ["occupancy", "bed occupancy"],
       "Patient days as a share of available bed days.",
       "Capacity-utilization signal for a hospital.",
       "Seasonal and case-mix swings make point-in-time occupancy noisy.",
       formula="patient days / available bed days", formula_confidence=_INF,
       source_types=[_PUB], data_confidence=_PUB,
       related_metrics=["bed_count", "case_mix_index"],
       related_routes=["/diligence/hcris-xray"]),
    _m("cost_per_adjusted_discharge", "Cost per Adjusted Discharge",
       ["cost per discharge", "cpad", "cost/adjusted discharge"],
       "Operating cost per case, adjusted for outpatient volume.",
       "Core hospital efficiency benchmark.",
       "Case-mix and the outpatient adjustment factor drive comparability.",
       source_types=[_PUB], data_confidence=_PUB,
       related_metrics=["labor_cost_ratio", "case_mix_index", "operating_margin"],
       related_routes=["/diligence/hcris-xray"]),
    _m("labor_cost_ratio", "Labor Cost Ratio", ["labor ratio", "labor % of revenue", "labor cost %"],
       "Labor cost as a share of net revenue.",
       "Labor is the largest hospital cost; the key margin lever.",
       "Agency/locum reliance inflates it and is often reducible.",
       formula="labor cost / net revenue", formula_confidence=_INF,
       source_types=[_PUB, _OBS], data_confidence=_MIX,
       related_metrics=["operating_margin", "cost_per_adjusted_discharge"],
       related_routes=["/diligence/hcris-xray"]),
    _m("operating_margin", "Operating Margin", ["op margin", "operating income margin"],
       "Operating income as a share of revenue.",
       "Bottom-line operating health from public filings.",
       "HCRIS operating margin lags real-time and includes filing artifacts.",
       formula="operating income / revenue", formula_confidence=_INF,
       source_types=[_PUB, _OBS], data_confidence=_MIX,
       related_metrics=["ebitda_margin", "labor_cost_ratio"],
       related_routes=["/diligence/hcris-xray"]),
    _m("medicare_cost_report_year", "Medicare Cost Report Year",
       ["hcris year", "cost report year", "filing year"],
       "The fiscal year of the CMS HCRIS cost report being shown.",
       "Tells you how current (or stale) the public hospital data is.",
       "HCRIS filings lag 1-2+ years; always check the year before relying on it.",
       formula_confidence=_NA, source_types=[_PUB], data_confidence=_PUB,
       related_metrics=["operating_margin"], related_routes=["/diligence/hcris-xray"]),
    _m("case_mix_index", "Case Mix Index", ["cmi", "case mix"],
       "Average DRG weight — acuity/complexity of the patient population.",
       "Normalizes cost and reimbursement comparisons for acuity.",
       "Higher CMI legitimately raises cost-per-case; don't read it as inefficiency.",
       source_types=[_PUB], data_confidence=_PUB,
       related_metrics=["cost_per_adjusted_discharge", "occupancy_rate"]),

    # ── Risk / model ────────────────────────────────────────────────
    _m("risk_score", "Risk Score", ["deal risk score", "risk rating"],
       "A composite model score summarizing deal risk.",
       "A fast triage signal across the portfolio/pipeline.",
       "It is a model composite, not a probability — read the components.",
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["bankruptcy_pattern_match", "confidence_tier"]),
    _m("data_coverage_score", "Data Coverage Score", ["coverage score", "completeness score"],
       "How complete the underlying data is for an analysis.",
       "Low coverage means downstream numbers lean on priors/imputation.",
       "High coverage isn't accuracy — only completeness.",
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["imputation_share", "confidence_tier"]),
    _m("confidence_tier", "Confidence Tier", ["confidence", "data quality grade", "confidence grade"],
       "A graded confidence level (e.g. A-D) for an estimate or page.",
       "Tells the reader how much weight to put on the figures.",
       "A high tier reflects data quality, not investment merit.",
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["data_coverage_score", "imputation_share"]),
    _m("imputation_share", "Imputation Share", ["imputed share", "% imputed", "imputation"],
       "Share of inputs filled from priors/benchmarks rather than observed data.",
       "High imputation means the result is benchmark-driven, not target-specific.",
       "More imputation = more reliance on priors over the actual target.",
       source_types=[_EST, _PUB], data_confidence=_EST,
       related_metrics=["data_coverage_score", "model_estimate"]),
    _m("model_estimate", "Model Estimate", ["estimate", "predicted value", "ml estimate"],
       "A value produced by a platform model rather than observed.",
       "Distinguishes computed predictions from reported/observed figures.",
       "Always an estimate with uncertainty — never treat as observed truth.",
       formula_confidence=_NA, source_types=[_EST], data_confidence=_EST,
       related_metrics=["confidence_tier", "benchmark_percentile"]),
    _m("benchmark_percentile", "Benchmark Percentile", ["percentile", "peer percentile", "pXX"],
       "Where a target sits in the distribution of a peer/corpus benchmark.",
       "Contextualizes a raw number against the relevant cohort.",
       "Percentiles over a thin cohort swing on individual deals — check n.",
       source_types=[_PUB], data_confidence=_PUB,
       related_metrics=["model_estimate"],
       related_routes=["/market-rates", "/comparables"]),
    _m("bankruptcy_pattern_match", "Bankruptcy Pattern Match",
       ["distress match", "failure pattern", "bankruptcy similarity"],
       "Similarity of a deal's signature to historical distressed/failed cases.",
       "Flags historical-analogue distress risk the bull case may ignore.",
       "A high match is a prompt to investigate, not a verdict of failure.",
       source_types=[_EST], data_confidence=_MIX,
       related_metrics=["risk_score"],
       related_routes=["/diligence/deal-autopsy", "/screening/bankruptcy-survivor"]),
    _m("payer_stress_impact", "Payer Stress Impact", ["payer stress", "reimbursement stress impact"],
       "Estimated EBITDA/return impact under adverse payer-mix or rate scenarios.",
       "Sizes downside sensitivity to the top healthcare risk driver.",
       "A scenario estimate, not a forecast; depends on the assumed shock.",
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["payer_mix", "commercial_payer_exposure", "covenant_cushion"],
       related_routes=["/diligence/payer-stress"]),
    _m("bridge_realization_probability", "Bridge Realization Probability",
       ["realization probability", "probability of achievement", "lever probability"],
       "Estimated probability that a value-creation lever / bridge is achieved.",
       "Converts gross lever impact into a probability-weighted, defensible number.",
       "Probabilities are model assumptions — gross vs weighted impact differ a lot.",
       source_types=[_EST], data_confidence=_EST,
       related_metrics=["ebitda_bridge", "value_creation_opportunity", "rcm_uplift"],
       related_routes=["/diligence/bridge-audit"]),

    # ── Sector Intelligence: Home Health + Hospice (CMS public quality) ──
    _m("home_health_star_rating", "Home Health Star Rating",
       ["quality of patient care star rating", "hha star rating", "hh star rating"],
       "CMS Home Health Care quality-of-patient-care star rating (1-5) per "
       "Medicare-certified agency.",
       "A quick public quality read across a fragmented agency market.",
       "Public benchmark only — not the target's own outcomes; confirm the "
       "agencies in scope match the deal.",
       source_types=[_PUB], data_confidence=_PUB,
       related_routes=["/home-health"]),
    _m("timely_initiation_of_care", "Timely Initiation of Care",
       ["timely care", "timely initiation", "started care timely"],
       "Share of patients whose home-health team began care in a timely "
       "manner (publicly reported HH process measure).",
       "Operational responsiveness signal; weak timeliness can flag intake/"
       "staffing issues.",
       "Process measure, not outcomes or revenue; CMS-reported, not target data.",
       source_types=[_PUB], data_confidence=_PUB,
       related_routes=["/home-health"]),
    _m("discharge_to_community", "Discharge to Community (HH)",
       ["dtc", "discharge to community rate"],
       "Risk-standardized rate of home-health patients discharged to the "
       "community (publicly reported HH outcome).",
       "A headline outcome measure for home-health quality.",
       "Risk-standardized public measure; not the target's internal results.",
       source_types=[_PUB], data_confidence=_PUB,
       related_routes=["/home-health"]),
    _m("hospice_care_index", "Hospice Care Index",
       ["hci", "care index", "hospice care index overall"],
       "CMS Hospice Care Index — a composite of ten care-pattern indicators "
       "(0-10) per Medicare-certified hospice.",
       "A single public read on hospice care patterns across a fragmented "
       "market; outlier indices can flag compliance/quality concerns.",
       "Composite of process/pattern indicators, not outcomes or economics; "
       "CMS-reported, not target data.",
       source_types=[_PUB], data_confidence=_PUB,
       related_routes=["/hospice"]),
    _m("hospice_composite_process", "Hospice Composite Process Measure",
       ["his composite", "composite process measure", "hospice composite"],
       "Share of patients who received all applicable HIS care processes at "
       "admission (publicly reported hospice composite).",
       "A bundled admission-quality signal for hospice diligence.",
       "Process composite, not outcomes; public benchmark, not target actuals.",
       source_types=[_PUB], data_confidence=_PUB,
       related_routes=["/hospice"]),
    _m("visits_in_last_days", "Hospice Visits in Last Days of Life",
       ["visits last days", "visits in the last days of life"],
       "Share of patients with hospice visits in the last days of life "
       "(publicly reported HIS measure).",
       "End-of-life engagement signal relevant to hospice quality/compliance.",
       "Public process measure; not the target's own staffing/visit data.",
       source_types=[_PUB], data_confidence=_PUB,
       related_routes=["/hospice"]),
]

# ── Added metrics (standard textbook definitions; formula_confidence=INFERRED
#    where the formula is the standard one but PEdesk's exact computation isn't
#    confirmed from code; NOT_APPLICABLE for externally-defined composites). ──
_METRICS.extend([
    _m("hhi", "Herfindahl-Hirschman Index (HHI)",
       ["herfindahl", "hhi", "market concentration", "concentration index"],
       "Market-concentration index: the sum of squared market shares of all "
       "competitors in a market.",
       "The standard antitrust/market-structure gauge — high HHI means a "
       "concentrated (less competitive, often more pricing-power) market; low "
       "HHI means fragmented (roll-up runway).",
       "Read the scale: shares as percentages give 0–10,000 (DOJ: <1,500 "
       "unconcentrated, 1,500–2,500 moderate, >2,500 concentrated); shares as "
       "fractions give 0–1. Confirm which scale a page uses before comparing.",
       formula="sum over competitors of (market_share_i)^2",
       formula_confidence=_INF, source_types=[_PUB, _EST], data_confidence=_MIX,
       related_metrics=["benchmark_percentile"],
       related_routes=["/concentration-risk", "/market-intel"]),
    _m("concentration_ratio", "Concentration Ratio (CR3 / CR5)",
       ["cr3", "cr5", "concentration ratio", "top-n share"],
       "Combined market share of the largest N competitors (CR3 = top 3, "
       "CR5 = top 5).",
       "A simpler concentration read than HHI — how much of a market the few "
       "biggest players control.",
       "CRn ignores the distribution below the top N; pair with HHI. A high CR3 "
       "in a target's market signals entrenched incumbents.",
       formula="sum of market shares of the top N competitors",
       formula_confidence=_INF, source_types=[_PUB, _EST], data_confidence=_MIX,
       related_metrics=["hhi"], related_routes=["/concentration-risk"]),
    _m("dscr", "Debt Service Coverage Ratio (DSCR)",
       ["dscr", "debt service coverage", "coverage ratio"],
       "Cash available for debt service divided by total debt service "
       "(interest + scheduled principal) over a period.",
       "The core covenant/solvency test — DSCR below ~1.0x means the business "
       "isn't generating enough cash to cover its debt payments.",
       "Definitions of the numerator vary (EBITDA vs operating cash flow vs "
       "EBITDA−capex); confirm which a page uses. DSCR is only meaningful once "
       "real cash-flow and debt-service figures are loaded.",
       formula="operating cash flow / (interest + scheduled principal)",
       formula_confidence=_INF, source_types=[_OBS, _USR], data_confidence=_MIX,
       related_metrics=["leverage", "debt", "covenant_cushion"],
       related_routes=["/debt-service", "/covenant-headroom"]),
    _m("tvpi", "TVPI (Total Value to Paid-In)",
       ["tvpi", "total value to paid-in", "gross multiple", "total value mult"],
       "Total value (cumulative distributions + residual NAV) divided by "
       "capital paid in by LPs.",
       "The headline fund-level multiple LPs track — total value created per "
       "dollar called, realized and unrealized combined.",
       "TVPI includes UNREALIZED NAV, so it can flatter a young fund; read it "
       "alongside DPI (realized cash) and the fund's age.",
       formula="(cumulative distributions + residual NAV) / paid-in capital",
       formula_confidence=_INF, source_types=[_USR, _OBS], data_confidence=_MIX,
       related_metrics=["dpi", "rvpi", "moic", "irr"],
       related_routes=["/lp-dashboard", "/dpi-tracker"]),
    _m("dpi", "DPI (Distributions to Paid-In)",
       ["dpi", "distributions to paid-in", "realized multiple", "cash-on-cash"],
       "Cumulative cash distributions to LPs divided by capital paid in.",
       "The realized-cash truth of fund performance — money actually returned, "
       "with no unrealized marks.",
       "A low DPI on an older fund is a real concern; on a young fund it's "
       "expected (the j-curve). DPI + RVPI = TVPI.",
       formula="cumulative distributions / paid-in capital",
       formula_confidence=_INF, source_types=[_USR, _OBS], data_confidence=_MIX,
       related_metrics=["tvpi", "rvpi", "moic"],
       related_routes=["/lp-dashboard", "/dpi-tracker"]),
    _m("rvpi", "RVPI (Residual Value to Paid-In)",
       ["rvpi", "residual value to paid-in", "unrealized multiple"],
       "Residual (unrealized) NAV divided by capital paid in.",
       "The unrealized half of TVPI — value still in the ground that exits "
       "must convert to cash.",
       "RVPI is a MARK, not cash; its reliability depends on how conservatively "
       "the GP carries NAV. DPI + RVPI = TVPI.",
       formula="residual NAV / paid-in capital",
       formula_confidence=_INF, source_types=[_USR, _EST], data_confidence=_MIX,
       related_metrics=["tvpi", "dpi"], related_routes=["/lp-dashboard"]),
    _m("cms_star_rating", "CMS Five-Star Rating",
       ["star rating", "five-star", "overall rating", "cms stars",
        "quality rating"],
       "CMS's 1–5 star composite quality rating for a provider (nursing home, "
       "dialysis facility, hospital, etc.).",
       "A standardized, public quality signal — relevant to reimbursement "
       "(e.g. MA bonus), survey risk, and reputational diligence.",
       "It is CMS's OWN composite methodology (health inspection, staffing, "
       "quality measures), refreshed on CMS's schedule and can lag; it is a "
       "quality signal, NOT a financial or revenue metric.",
       formula="CMS composite methodology (externally defined)",
       formula_confidence=_NA, source_types=[_PUB], data_confidence=_PUB,
       related_metrics=["home_health_star_rating"],
       related_routes=["/nursing-homes", "/dialysis", "/ma-star"]),
    _m("days_cash_on_hand", "Days Cash on Hand",
       ["days cash on hand", "dcoh", "liquidity days", "cash days"],
       "Number of days a provider could cover operating expenses from cash and "
       "short-term investments at the current burn rate.",
       "A core liquidity/solvency gauge — low days cash on hand is an early "
       "distress signal, especially for thin-margin providers.",
       "Excludes access to revolver/credit; a low figure with ample undrawn "
       "liquidity is less alarming than it looks. Needs real balance-sheet "
       "data to compute.",
       formula="(cash + short-term investments) / (annual operating expenses "
       "/ 365)",
       formula_confidence=_INF, source_types=[_OBS, _USR], data_confidence=_MIX,
       related_metrics=["dscr", "covenant_cushion"],
       related_routes=["/treasury", "/debt-service"]),
])

# ── Batch 2 of added metrics (standard operational / credit / liquidity
#    definitions; INFERRED where the formula is the standard one). ──
_METRICS.extend([
    _m("length_of_stay", "Average Length of Stay (ALOS)",
       ["alos", "length of stay", "los", "avg length of stay"],
       "Average number of days a patient stays per admission over a period.",
       "A core efficiency/throughput gauge — shorter ALOS (at constant "
       "quality) frees capacity and improves margin; rising ALOS can signal "
       "acuity shifts or discharge friction.",
       "Read ALOS WITH acuity/case-mix — a higher ALOS at higher case-mix is "
       "expected, not inefficiency. Compare against the same service line.",
       formula="total patient days / total admissions (discharges)",
       formula_confidence=_INF, source_types=[_OBS, _PUB], data_confidence=_MIX,
       related_metrics=["case_mix_index", "occupancy_rate", "bed_count"]),
    _m("readmission_rate", "30-Day Readmission Rate",
       ["readmission rate", "30-day readmission", "readmissions"],
       "Share of discharges followed by an unplanned readmission within 30 "
       "days.",
       "A quality + cost signal tied to CMS penalties (HRRP) and a marker of "
       "care-transition effectiveness.",
       "CMS's published rate is RISK-ADJUSTED and condition-specific; a raw "
       "readmissions/discharges ratio is not directly comparable to it. Treat "
       "the CMS figure as its own methodology.",
       formula="unplanned 30-day readmissions / eligible discharges "
       "(CMS publishes a risk-adjusted version)",
       formula_confidence=_INF, source_types=[_PUB, _OBS], data_confidence=_MIX,
       related_metrics=["discharge_to_community", "length_of_stay",
                        "cms_star_rating"]),
    _m("cost_to_charge_ratio", "Cost-to-Charge Ratio (CCR)",
       ["cost to charge", "cost-to-charge ratio", "cost charge ratio"],
       "Ratio of a provider's costs to its gross charges, from the Medicare "
       "cost report.",
       "Used to estimate actual cost behind billed charges (charges are list "
       "prices, not realized revenue); a building block for cost analytics.",
       "Charges are not revenue and CCR varies widely by department; an "
       "aggregate CCR hides departmental spread. Cost-report based, so it lags.",
       formula="total costs / total gross charges (HCRIS)",
       formula_confidence=_INF, source_types=[_PUB], data_confidence=_PUB,
       related_metrics=["operating_margin", "cost_per_adjusted_discharge"],
       related_routes=["/cost-structure"]),
    _m("current_ratio", "Current Ratio",
       ["current ratio", "working capital ratio"],
       "Current assets divided by current liabilities — a short-term "
       "liquidity gauge.",
       "Flags whether a business can cover near-term obligations; <1.0x means "
       "current liabilities exceed current assets.",
       "A snapshot that ignores timing and access to revolver/credit; pair "
       "with days cash on hand and the cash-conversion cycle.",
       formula="current assets / current liabilities",
       formula_confidence=_INF, source_types=[_OBS, _USR], data_confidence=_MIX,
       related_metrics=["days_cash_on_hand", "cash_conversion_cycle"],
       related_routes=["/working-capital", "/treasury"]),
    _m("gross_margin", "Gross Margin",
       ["gross margin", "gross profit margin"],
       "Revenue less direct cost of services, as a percentage of revenue.",
       "The first-line profitability read before overhead — isolates "
       "service-delivery economics from SG&A.",
       "For provider businesses 'cost of services' (clinical labor, supplies) "
       "is defined inconsistently; confirm what's in/out before comparing. "
       "Distinct from operating and EBITDA margin.",
       formula="(revenue - cost of services) / revenue",
       formula_confidence=_INF, source_types=[_OBS, _USR], data_confidence=_MIX,
       related_metrics=["ebitda_margin", "operating_margin",
                        "provider_contribution_margin"],
       related_routes=["/unit-economics", "/cost-structure"]),
    _m("capex_intensity", "Capex Intensity",
       ["capex intensity", "capex / revenue", "capital intensity"],
       "Capital expenditure as a percentage of revenue.",
       "How capital-hungry the business is — high capex intensity reduces free "
       "cash flow and the cash available for debt service / distributions.",
       "Separate maintenance vs growth capex; a high figure driven by growth "
       "capex is an investment choice, not a structural burden. Lumpy "
       "year-to-year.",
       formula="capital expenditures / revenue",
       formula_confidence=_INF, source_types=[_OBS, _USR], data_confidence=_MIX,
       related_metrics=["ebitda", "revenue", "days_cash_on_hand"],
       related_routes=["/capex-budget"]),
    _m("fixed_charge_coverage", "Fixed-Charge Coverage Ratio (FCCR)",
       ["fccr", "fixed charge coverage", "fixed-charge coverage"],
       "Cash available for fixed charges divided by total fixed charges "
       "(interest + scheduled principal + lease/rent).",
       "A stricter covenant test than DSCR because it includes lease "
       "obligations — important for lease-heavy provider models.",
       "Definitions of the numerator vary (EBITDA vs EBITDA−unfinanced capex); "
       "confirm which the credit agreement uses. Needs real fixed-charge data.",
       formula="(EBITDA - unfinanced capex) / (interest + principal + leases)",
       formula_confidence=_INF, source_types=[_OBS, _USR], data_confidence=_MIX,
       related_metrics=["dscr", "interest_coverage", "leverage",
                        "covenant_cushion"],
       related_routes=["/debt-service", "/covenant-headroom"]),
    _m("interest_coverage", "Interest Coverage Ratio",
       ["interest coverage", "ebitda / interest", "times interest earned"],
       "EBITDA divided by interest expense over a period.",
       "How comfortably operating earnings cover the cost of debt; a fast read "
       "on whether leverage is sustainable.",
       "Ignores principal amortization (DSCR/FCCR capture that); high coverage "
       "with a near-term maturity wall can still be risky.",
       formula="EBITDA / interest expense",
       formula_confidence=_INF, source_types=[_OBS, _USR], data_confidence=_MIX,
       related_metrics=["dscr", "fixed_charge_coverage", "leverage", "debt"],
       related_routes=["/debt-service", "/covenant-headroom"]),
    _m("cash_conversion_cycle", "Cash Conversion Cycle (CCC)",
       ["ccc", "cash conversion cycle", "cash cycle"],
       "Days to convert operating investment into cash: days sales "
       "outstanding + days inventory − days payable outstanding.",
       "The net working-capital drag in days — lower (or negative) frees cash; "
       "in provider RCM the DSO/AR-days leg usually dominates.",
       "Inventory is small for most providers, so CCC is largely an AR/AP "
       "story; needs real balance-sheet/AR data to compute.",
       formula="DSO + DIO - DPO",
       formula_confidence=_INF, source_types=[_OBS, _USR], data_confidence=_MIX,
       related_metrics=["days_in_ar", "net_collection_rate", "current_ratio"],
       related_routes=["/working-capital"]),
    _m("net_debt", "Net Debt",
       ["net debt", "net financial debt"],
       "Total interest-bearing debt minus cash and cash equivalents.",
       "The leverage figure that actually matters for EV and covenants — cash "
       "on hand offsets gross debt.",
       "Not all cash is freely available (restricted/escrow); confirm what's "
       "netted. Net debt feeds leverage (net debt / EBITDA) and equity value "
       "(EV − net debt).",
       formula="total interest-bearing debt - cash & equivalents",
       formula_confidence=_INF, source_types=[_OBS, _USR], data_confidence=_MIX,
       related_metrics=["debt", "leverage", "enterprise_value"],
       related_routes=["/debt-service", "/cap-structure"]),
    # ── Portfolio-operations metrics ──────────────────────────────
    # Health score is a first-class composite the portfolio dashboards
    # surface; adding it lets the Guide answer 'how is the health
    # score computed' with real content. The covenant-cushion concept
    # already lives at covenant_cushion (line 129) so we don't
    # duplicate it; portfolio/monitor's page context references that
    # canonical id.
    _m("health_score", "Health Score", ["deal health", "composite health"],
       "Composite 0-100 score per deal that combines plan-realization, "
       "covenant cushion, alert posture, and trend slope into a single "
       "monitoring number.",
       "The single read partner reach for during the morning portfolio "
       "scan — replaces opening 8 separate dials.",
       "Heuristic, not predictive — pair with the active-alert detail "
       "before acting. 80+ = green, 60-79 = amber, <60 = red.",
       formula="weighted blend of: plan realization %, covenant cushion "
               "%, active alert count, and 4-quarter trend slope. Weights "
               "documented in rcm_mc.deals.health_score; subject to "
               "calibration review each quarter.",
       formula_confidence=_INF, source_types=[_OBS], data_confidence=_MIX,
       related_metrics=["covenant_cushion", "ebitda", "adjusted_ebitda"],
       related_routes=["/portfolio/monitor", "/my/AT", "/dashboard",
                       "/watchlist"]),
])

METRIC_REGISTRY: Dict[str, MetricContext] = {m.metric_id: m for m in _METRICS}

# ── Formula completion ─────────────────────────────────────────────────
# Fill every remaining placeholder formula with an HONEST value, so the Guide
# can answer "how is X computed" on every metric. Three honest categories:
#   _INF  — standard textbook definition (the formula is standard; PEdesk's
#           exact computation is inferred, not confirmed from code);
#   _NA   — no formula applies (a count, an identifier, a label, or an
#           externally-defined CMS composite — stated as such, not invented);
#   _NV   — a proprietary/model-derived score with NO closed-form formula; we
#           describe the approach at a truthful level and DO NOT fabricate one.
# (metric_id -> (formula_text, formula_confidence))
_FORMULA_PATCHES: Dict[str, Any] = {
    # Standard definitions (INFERRED)
    "ebitda": ("net income + interest + taxes + depreciation + amortization "
               "(≈ operating income + D&A)", _INF),
    "adjusted_ebitda": ("EBITDA + non-recurring / normalizing add-backs "
                        "(one-time, owner, and run-rate adjustments)", _INF),
    "revenue": ("gross patient revenue − contractual allowances − bad debt "
                "(= net patient revenue)", _INF),
    "irr": ("the discount rate r solving Σ cash_flow_t / (1+r)^t = 0", _INF),
    "debt": ("sum of interest-bearing obligations (net debt = gross debt − "
             "cash & equivalents)", _INF),
    "covenant_cushion": ("headroom to the covenant — e.g. (max-leverage "
                         "covenant − current leverage), or the EBITDA decline "
                         "tolerable before a breach", _INF),
    "ebitda_bridge": ("starting EBITDA + Σ (per-lever EBITDA contributions) = "
                      "pro-forma EBITDA", _INF),
    "bad_debt_rate": ("bad-debt write-offs / gross patient revenue", _INF),
    "clean_claim_rate": ("claims accepted on first submission (no edits/"
                         "rejections) / total claims submitted", _INF),
    "underpayment_rate": ("underpaid claim amount / contracted (expected) "
                          "amount", _INF),
    "collections_leakage": ("expected collectible revenue − actual collections, "
                            "attributable to denials, underpayments and "
                            "write-offs", _INF),
    "cost_per_adjusted_discharge": ("total operating cost / adjusted discharges "
                                    "(discharges grossed up for outpatient "
                                    "volume)", _INF),
    "case_mix_index": ("sum of DRG weights / number of cases", _INF),
    "benchmark_percentile": ("percentile rank (0–100) of the target's value "
                             "within the peer distribution", _INF),
    "payer_mix": ("share of revenue (or volume) by payer class "
                  "(Medicare / Medicaid / commercial / self-pay); classes "
                  "sum to 100%", _INF),
    "app_support_ratio": ("advanced-practice providers (NP + PA) / physicians",
                          _INF),
    "physician_attrition": ("providers departing in the period / average "
                            "provider headcount (annualized)", _INF),
    "provider_contribution_margin": ("(provider-attributable revenue − direct "
                                     "costs) / provider revenue", _INF),
    "provider_productivity": ("output per provider FTE (e.g. wRVUs or visits "
                              "per FTE)", _INF),
    "referral_leakage": ("referrals directed outside the network / total "
                         "referrals", _INF),
    "data_coverage_score": ("populated required inputs / total required inputs",
                            _INF),
    "imputation_share": ("imputed (prior/benchmark-filled) inputs / total "
                         "inputs", _INF),
    "timely_initiation_of_care": ("home-health patients whose care began within "
                                  "2 days of start-of-care / eligible patients "
                                  "(CMS measure definition)", _INF),
    "visits_in_last_days": ("hospice patients with a visit in the last 3 (and "
                            "7) days of life / decedents (CMS measure "
                            "definition)", _INF),
    "hospice_composite_process": ("patients who received ALL applicable "
                                  "admission care-process measures / eligible "
                                  "patients (CMS composite)", _INF),
    # No formula applies (NOT_APPLICABLE) — counts, identifiers, labels,
    # externally-defined CMS composites.
    "bed_count": ("a count of licensed/staffed beds — not a computed ratio",
                  _NA),
    "panel_size": ("a count of attributed patients — not a computed ratio",
                   _NA),
    "wrvu": ("CMS-assigned work RVU per CPT/HCPCS code (set by the Medicare "
             "fee schedule, not computed by PEdesk)", _NA),
    "medicare_cost_report_year": ("an identifier — the HCRIS cost-report "
                                  "fiscal year, not a computed metric", _NA),
    "confidence_tier": ("a graded label (e.g. A–D), not a numeric formula", _NA),
    "model_estimate": ("a provenance category (the value came from a model), "
                       "not a metric with a formula", _NA),
    "home_health_star_rating": ("CMS Home Health quality-of-patient-care "
                                "composite methodology (externally defined)",
                                _NA),
    "hospice_care_index": ("CMS Hospice Care Index — composite of 10 indicators "
                           "(externally defined by CMS)", _NA),
    "discharge_to_community": ("CMS risk-standardized rate (CMS's "
                               "risk-adjustment model, externally defined)",
                               _NA),
    # Proprietary / model-derived — NO closed-form formula; described honestly,
    # not fabricated (formula_confidence stays NEEDS_VALIDATION).
    "rcm_uplift": ("model estimate ≈ Σ (KPI gap closed × revenue at risk); "
                   "assumption-driven, not a closed-form figure", _NV),
    "value_creation_opportunity": ("model estimate = Σ value-creation lever "
                                   "contributions; assumption-driven, not "
                                   "closed-form", _NV),
    "synergy_estimate": ("analyst/model estimate of cost + revenue synergy "
                         "dollars; not a closed-form figure", _NV),
    "payer_stress_impact": ("modeled EBITDA/return delta under an adverse "
                            "payer-rate scenario; scenario output, not "
                            "closed-form", _NV),
    "bridge_realization_probability": ("model-estimated (calibrated) "
                                       "probability a lever is realized; not a "
                                       "closed-form ratio", _NV),
    "bankruptcy_pattern_match": ("model similarity between the deal's financial "
                                 "signature and historical distress cases; not "
                                 "a closed-form ratio", _NV),
    "risk_score": ("weighted composite of risk-flag signals (model-defined "
                   "weights); not a single closed-form ratio", _NV),
}
for _mid, (_f, _conf) in _FORMULA_PATCHES.items():
    _m_obj = METRIC_REGISTRY.get(_mid)
    if _m_obj is not None:
        _m_obj.formula = _f
        _m_obj.formula_confidence = _conf

# ── Caveat completion ──────────────────────────────────────────────────
# `caveats` IS sent to the model (guide_prompt_builder), so a placeholder
# degrades answers. Fill every metric still on the default with honest,
# standard analytical cautions (general domain knowledge, not fabricated
# specifics). Applied only where caveats are still the placeholder.
_CAVEAT_PATCHES: Dict[str, List[str]] = {
    "revenue": ["Confirm NET (after contractual allowances/bad debt), not gross charges.",
                "Mixes payer classes with very different realization rates."],
    "revenue_growth": ["Organic vs M&A-driven growth are very different — separate them.",
                       "A single year is noisy; prefer a multi-year CAGR."],
    "ebitda": ["Reported vs adjusted EBITDA can differ materially — confirm which.",
               "Excludes capex and working-capital needs, which can be large for providers."],
    "adjusted_ebitda": ["Add-backs are where aggression hides — scrutinise each one.",
                        "Run-rate adjustments assume a future that may not materialise."],
    "ebitda_margin": ["Compare within the same sub-sector; margin norms vary widely.",
                      "Thin provider margins make the ratio sensitive to small cost swings."],
    "enterprise_value": ["EV and equity value differ by net debt — don't conflate.",
                        "Depends on the EBITDA/multiple inputs, which are assumptions."],
    "ev_to_ebitda": ["A 'cheap' multiple can reflect real risk, not a bargain.",
                    "Compare against the right size/sector comp set."],
    "exit_multiple": ["Underwriting flat-to-down vs entry is the disciplined assumption.",
                     "Multiple expansion is market-driven and outside the GP's control."],
    "moic": ["Gross vs net (of fees/carry) MOIC differ — confirm which.",
            "MOIC ignores time; pair with IRR."],
    "irr": ["IRR is time-sensitive and can be flattered by early distributions.",
           "Assumes reinvestment at the IRR; pair with MOIC and DPI."],
    "leverage": ["Gross vs net leverage differ — confirm which.",
                "High leverage on thin/cyclical EBITDA is fragile."],
    "debt": ["Distinguish gross vs net (of cash) debt.",
            "Watch maturity timing, not just the level."],
    "covenant_cushion": ["A thin cushion can flip to a breach on a small EBITDA miss.",
                        "Definition depends on the specific covenant in the credit agreement."],
    "hold_period": ["Realised hold often exceeds plan; model sensitivity to a longer hold.",
                   "Longer holds drag IRR even as MOIC compounds."],
    "ebitda_bridge": ["Lever contributions are assumptions until realised.",
                     "Overlapping levers can double-count — confirm they're additive."],
    "synergy_estimate": ["Synergies are routinely over-estimated and under-delivered.",
                        "Separate cost (high-confidence) from revenue (lower) synergies."],
    "value_creation_opportunity": ["A modelled upside, not a commitment — discount for execution risk.",
                                   "Sensitive to the benchmark targets chosen."],
    "denial_rate": ["Initial vs final denial rate differ — confirm which.",
                   "Varies by payer mix and service line; compare like-for-like."],
    "net_collection_rate": ["Sensitive to the write-off window and payer mix.",
                           "Near-ceiling values leave little improvement headroom."],
    "gross_collection_rate": ["Driven by charge-master pricing, so weakly comparable across providers.",
                             "Net collection rate is the more meaningful figure."],
    "clean_claim_rate": ["Definitions of 'clean' vary by clearinghouse/payer.",
                        "A high rate can still hide downstream denials."],
    "days_in_ar": ["Inflated by old uncollectible balances unless aged/scrubbed.",
                  "Compare within payer mix; Medicaid-heavy AR runs longer."],
    "bad_debt_rate": ["Bad debt vs charity care are classified differently — confirm.",
                     "Policy changes can shift the rate without operational change."],
    "underpayment_rate": ["Requires an accurate contract model to detect underpayments.",
                         "Some 'underpayments' are legitimate contractual adjustments."],
    "collections_leakage": ["An estimate of recoverable revenue, not a guaranteed gain.",
                          "Double-counting across denial/underpayment/write-off buckets is a risk."],
    "case_mix_index": ["Higher CMI reflects acuity, not inefficiency — read LOS/cost with it.",
                      "Coding intensity can inflate CMI without real acuity change."],
    "cost_per_adjusted_discharge": ["The outpatient adjustment method materially moves it.",
                                   "Compare against peers of similar acuity (CMI)."],
    "occupancy_rate": ["Licensed vs staffed beds change the denominator.",
                      "Seasonal swings make a single snapshot misleading."],
    "operating_margin": ["HCRIS filing artifacts (opex ≫ revenue) can distort it — scrub outliers.",
                       "State-funded/psychiatric facilities follow different economics."],
    "payer_mix": ["Day-based vs revenue-based mix differ; revenue mix matters more for economics.",
                "Medicaid and Medicare reimburse below commercial — mix drives margin."],
    "medicare_exposure": ["Medicare rate updates often lag inflation — a margin risk.",
                        "Day-share vs revenue-share exposure differ."],
    "medicaid_exposure": ["Medicaid often reimburses below cost; high exposure pressures margin.",
                        "State-by-state Medicaid policy varies widely."],
    "commercial_payer_exposure": ["Commercial rates are the margin engine but contract-renewal-sensitive.",
                                 "Concentration in one commercial payer is a risk."],
    "payer_stress_impact": ["A scenario output — only as valid as the rate-cut assumption.",
                          "Does not model volume or mix responses to rate changes."],
    "physician_attrition": ["A few departures swing small-group attrition sharply.",
                          "Voluntary vs involuntary attrition mean different things."],
    "provider_productivity": ["wRVU vs visit-based productivity aren't comparable.",
                            "Higher productivity can trade off against quality/access."],
    "provider_contribution_margin": ["Allocation of shared/overhead costs drives the result.",
                                    "Negative contribution may still be strategically justified."],
    "compensation_to_collections": ["Sensitive to the collections definition and lag.",
                                   "Comp models (wRVU vs collections) change the ratio's meaning."],
    "labor_cost_ratio": ["Contract/agency labor can spike it temporarily.",
                       "Compare within service line; acuity drives staffing."],
    "referral_leakage": ["Requires referral-tracking data many providers lack.",
                       "Some leakage is clinically appropriate, not lost revenue."],
    "rcm_uplift": ["A modelled estimate from benchmark gaps — not realised EBITDA.",
                 "Assumes targets are achievable for this specific provider."],
    "bridge_realization_probability": ["A calibrated model estimate, not a guarantee.",
                                      "Realisation depends on execution the model can't see."],
    "panel_size": ["Attribution method (claims vs roster) changes the count.",
                 "Panel size alone says nothing about acuity or revenue."],
    "app_support_ratio": ["Optimal ratio is specialty-specific; no universal target.",
                        "Scope-of-practice rules vary by state."],
    "benchmark_percentile": ["Percentile depends entirely on the peer set chosen.",
                           "Being at P50 isn't 'good' or 'bad' without context."],
    "risk_score": ["A composite — read the underlying flags, not just the score.",
                 "Model weights are assumptions; treat as directional."],
    "confidence_tier": ["A graded label, not a precise probability.",
                      "Reflects data completeness, not whether the thesis is right."],
    "data_coverage_score": ["High coverage of wrong/stale data is still poor quality.",
                          "Required-field set is a judgement call."],
    "imputation_share": ["High imputation means the figure leans on priors, not the target.",
                       "Imputed values inherit the prior's biases."],
    "model_estimate": ["A model output, not an observed value — carries model error.",
                     "Confidence depends on the input data quality."],
    "bankruptcy_pattern_match": ["Similarity to past distress is not a prediction of failure.",
                               "Survivorship/selection bias in the historical set."],
    "wrvu": ["wRVU values are CMS-set and revised annually.",
           "wRVUs measure work, not revenue or profitability."],
    "adjusted_ebitda_": [],  # guard (no such id) — ignored
    "bed_count": ["Licensed vs staffed beds differ; staffed is the operational figure.",
                "Bed count alone doesn't indicate occupancy or revenue."],
    "discharge_to_community": ["CMS risk-standardised — not directly comparable to a raw rate.",
                             "Reflects post-acute outcomes, not financial performance."],
    "home_health_star_rating": ["CMS methodology, refreshed on CMS's schedule — can lag.",
                              "A quality signal, not a financial metric."],
    "hospice_care_index": ["A composite of 10 indicators — read the components.",
                         "Public quality data, not the target's own operations data."],
    "hospice_composite_process": ["Process (did they do it) ≠ outcome (did it help).",
                                "Admission-window measure; not ongoing care quality."],
    "timely_initiation_of_care": ["A process measure tied to CMS's 2-day window definition.",
                                "Public, risk-unadjusted; compare cautiously."],
    "visits_in_last_days": ["End-of-life engagement signal, not staffing/visit volume data.",
                          "CMS measure definition — not the target's internal data."],
    "medicare_cost_report_year": ["HCRIS lags — the 'latest' year is not the current quarter.",
                                "Filing year, not a performance metric."],
    "imputation_share_": [],  # guard
    # Metrics added in earlier batches (#975/#984) whose caveats field defaulted.
    "hhi": ["Check the scale (0–10,000 for %-shares vs 0–1 for fractions) before comparing.",
           "Depends entirely on how the market is defined (geography/service line)."],
    "concentration_ratio": ["CRn ignores the distribution below the top N — pair with HHI.",
                           "Market definition drives the result."],
    "dscr": ["Numerator definition varies (EBITDA vs OCF vs EBITDA−capex) — confirm the credit agreement's.",
            "Only meaningful with real cash-flow and debt-service figures."],
    "tvpi": ["Includes unrealised NAV, so it flatters young funds — read with DPI.",
            "NAV marks are GP estimates, not cash."],
    "dpi": ["Low DPI is normal early (j-curve) but a concern on an older fund.",
           "Realised cash only — says nothing about remaining upside."],
    "rvpi": ["A mark, not cash; reliability depends on NAV conservatism.",
            "Must convert to cash via exits to count."],
    "cms_star_rating": ["CMS's own composite methodology, refreshed on CMS's schedule — can lag.",
                       "A quality signal, not a financial/revenue metric."],
    "days_cash_on_hand": ["Excludes undrawn revolver/credit access — can look worse than it is.",
                         "Needs real balance-sheet data to compute."],
    "length_of_stay": ["Read with case mix — higher acuity justifies a longer stay.",
                      "Compare within the same service line."],
    "readmission_rate": ["CMS's published rate is risk-adjusted — not comparable to a raw ratio.",
                       "Condition-specific; an aggregate hides variation."],
    "cost_to_charge_ratio": ["Charges are list prices, not revenue; CCR varies widely by department.",
                           "Cost-report based, so it lags."],
    "current_ratio": ["A snapshot that ignores timing and revolver access.",
                     "Pair with days cash on hand and the cash-conversion cycle."],
    "gross_margin": ["'Cost of services' is defined inconsistently for providers — confirm scope.",
                   "Distinct from operating and EBITDA margin."],
    "capex_intensity": ["Separate maintenance vs growth capex — they mean different things.",
                      "Lumpy year-to-year; use a multi-year view."],
    "fixed_charge_coverage": ["Numerator definition varies — confirm the credit agreement's.",
                            "Includes leases, so stricter than DSCR for lease-heavy models."],
    "interest_coverage": ["Ignores principal amortisation — DSCR/FCCR capture that.",
                        "High coverage with a near-term maturity wall can still be risky."],
    "cash_conversion_cycle": ["For most providers it's largely an AR/AP story (inventory is small).",
                            "Needs real balance-sheet/AR data."],
    "net_debt": ["Not all cash is freely available (restricted/escrow) — confirm what's netted.",
               "Feeds leverage and equity value (EV − net debt)."],
}
for _mid, _cav in _CAVEAT_PATCHES.items():
    _m_obj = METRIC_REGISTRY.get(_mid)
    if _m_obj is not None and _cav and (
            list(_m_obj.caveats or []) == [_NEEDS] or not _m_obj.caveats):
        _m_obj.caveats = list(_cav)


# ── Coverage backfill (2026-05-27) ─────────────────────────────────────────
# Standard RCM / CMS metrics that live pages reference but the registry lacked,
# so the Guide can now explain them quantitatively (real definitions, no
# fabrication). Plus synonym aliases so common on-page KPI labels resolve to
# the metric that already exists (e.g. "Weighted MOIC" → moic).
_COVERAGE_METRICS = [
    _m(
        "cost_to_collect", "Cost to Collect",
        ["cost to collect", "cost-to-collect", "cost to collect rate",
         "rcm cost ratio", "cost of collections"],
        "The total cost of running the revenue cycle as a share of cash "
        "collected (the HFMA MAP key) — e.g. $0.03 of RCM cost per $1 collected.",
        "It is the headline efficiency metric for a revenue-cycle operation; an "
        "RCM roll-up or turnaround thesis often hinges on moving it toward "
        "best-in-class.",
        "Lower is better — HFMA strong performers run roughly 2-4%. Scope drives "
        "comparability: confirm whether vendor fees, IT, and which functions are "
        "included before benchmarking.",
        formula="total revenue-cycle cost / total cash collected",
        formula_confidence=_DOC,
        source_types=[_OBS], data_confidence=_OBS,
        caveats=["Scope varies (in-house vs outsourced, which functions count) "
                 "— normalize before comparing.",
                 "A low ratio with rising denials/AR can be false economy."],
        related_metrics=["net_collection_rate", "days_in_ar", "denial_rate"],
    ),
    _m(
        "medicare_spending_per_beneficiary", "Medicare Spending per Beneficiary",
        ["mspb", "medicare spending per beneficiary", "spending per beneficiary"],
        "CMS efficiency measure: price-standardized, risk-adjusted Medicare "
        "spending for an episode (3 days before to 30 days after an inpatient "
        "stay), expressed as a ratio to the national median (1.00 = at median).",
        "Flags whether a hospital is a high- or low-cost provider per episode — "
        "a payer-leverage, value-based-care, and efficiency signal.",
        "1.00 = national median; >1 costlier than peers, <1 more efficient. It "
        "is CMS's own price/risk-adjusted composite — read it, don't recompute "
        "it.",
        formula="CMS price-standardized, risk-adjusted episode spending ÷ "
        "national median (CMS composite)",
        formula_confidence=_NA,
        source_types=[_PUB], data_confidence=_PUB,
        caveats=["A CMS-published composite — not recomputed here.",
                 "Episode window is fixed (3 days pre to 30 days post "
                 "admission); it is not total cost of care."],
        related_metrics=["cost_per_adjusted_discharge", "readmission_rate"],
    ),
]
for _cm in _COVERAGE_METRICS:
    METRIC_REGISTRY.setdefault(_cm.metric_id, _cm)

# Synonym aliases → existing metrics (unambiguous; each maps to exactly one).
_ALIAS_EXTEND_COVERAGE: Dict[str, List[str]] = {
    "moic": ["weighted moic", "p50 moic", "median moic"],
    "irr": ["weighted irr", "median irr", "after-tax irr"],
    "days_in_ar": ["days in ar"],
    "value_creation_opportunity": ["value-creation opportunity", "value-creation"],
}
for _mid, _al in _ALIAS_EXTEND_COVERAGE.items():
    _o = METRIC_REGISTRY.get(_mid)
    if _o is not None:
        for _a in _al:
            if _a not in _o.aliases:
                _o.aliases.append(_a)
