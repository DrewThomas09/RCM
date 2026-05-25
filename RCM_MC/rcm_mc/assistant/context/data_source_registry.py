"""PEdesk Guide data-source registry — conservative, read-only.

Explains what each data source is, where it likely appears in PEdesk,
what it's good for, its caveats, and whether it can stand alone as the
basis for an IC-ready conclusion. Where PEdesk's actual wiring isn't
established, fields say "Needs source documentation."
"""
from __future__ import annotations

from typing import Any, Dict, List

from .types import (
    DataConfidence,
    DataSourceContext,
    DataSourceType,
    SourceConfidence,
)

_NEEDS = "Needs source documentation."
_BASE_NOTES = [
    "PEdesk Guide is read-only — it explains this source, never ingests, "
    "refreshes, or modifies it.",
    "If PEdesk's actual use of this source isn't established here, say it "
    "needs source documentation rather than guessing.",
]

_T = DataSourceType
_DOCD = SourceConfidence.DOCUMENTED
_INFP = SourceConfidence.INFERRED_FROM_PAGE
_NV = SourceConfidence.NEEDS_VALIDATION
_PUB = DataConfidence.PUBLIC_BENCHMARK_DATA
_OBS = DataConfidence.OBSERVED_TARGET_DATA
_USR = DataConfidence.USER_ENTERED_DATA
_EST = DataConfidence.MODEL_ESTIMATE
_DEMO = DataConfidence.DEMO_OR_FIXTURE
_MIX = DataConfidence.MIXED
_UNK = DataConfidence.UNKNOWN


def _s(source_id: str, label: str, description: str, source_type: DataSourceType,
       **kw: Any) -> DataSourceContext:
    d: Dict[str, Any] = dict(
        update_cadence=_NEEDS,
        freshness_lag=_NEEDS,
        used_for=[_NEEDS],
        related_routes=[],
        related_metrics=[],
        strengths=[_NEEDS],
        limitations=[_NEEDS],
        provenance_notes=_NEEDS,
        source_confidence=_INFP,
        data_confidence=_UNK,
        aliases=[],
        ic_ready=None,
    )
    d.update(kw)
    return DataSourceContext(
        source_id=source_id, label=label, description=description,
        source_type=source_type, notes_for_assistant=list(_BASE_NOTES),
        last_reviewed_at="2026-05-22", owner="pedesk-guide", **d,
    )


_SOURCES: List[DataSourceContext] = [
    # ── Public / external ───────────────────────────────────────────
    _s("cms_hcris", "CMS HCRIS", "Medicare hospital cost-report filings — the "
       "public ground-truth financials/statistics for US hospitals.",
       _T.PUBLIC_DATASET, aliases=["hcris", "cms hcris", "cost report", "medicare cost report"],
       update_cadence="Annual (rolling CMS releases).",
       freshness_lag="Typically 1-2+ years behind the fiscal year.",
       used_for=["Screening the hospital universe; HCRIS X-Ray; benchmarks; comps."],
       related_routes=["/diligence/hcris-xray", "/screen", "/comparables"],
       related_metrics=["bed_count", "operating_margin", "labor_cost_ratio",
                       "cost_per_adjusted_discharge", "medicare_exposure",
                       "case_mix_index", "medicare_cost_report_year"],
       strengths=["Comprehensive, free, comparable across all US hospitals."],
       limitations=["Lags 1-2+ years; filing artifacts; cost-report quirks; "
                    "not a substitute for current target financials."],
       provenance_notes="Public CMS dataset; identify the cost-report YEAR shown.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cms_care_compare", "CMS Care Compare", "CMS public quality/outcomes "
       "ratings (e.g. Hospital/Star ratings).", _T.PUBLIC_DATASET,
       aliases=["care compare", "hospital compare", "star ratings"],
       update_cadence="Periodic CMS refreshes.",
       freshness_lag="Months to a year+.",
       used_for=["Quality/outcomes benchmarking."],
       related_metrics=["benchmark_percentile"],
       strengths=["Standardized public quality signal."],
       limitations=["Quality measures lag and don't capture all clinical nuance."],
       source_confidence=_INFP, data_confidence=_PUB, ic_ready=False),
    _s("medicare_utilization", "Medicare Utilization", "CMS Medicare claims/"
       "utilization datasets (provider/service volumes).", _T.PUBLIC_DATASET,
       aliases=["medicare claims", "provider utilization", "puf"],
       update_cadence="Annual.", freshness_lag="1-2+ years.",
       used_for=["Provider/market volume and service-mix analysis."],
       related_metrics=["provider_productivity", "referral_leakage"],
       strengths=["Population-level Medicare volume signal."],
       limitations=["Medicare-only; lags; not commercial volume."],
       source_confidence=_INFP, data_confidence=_PUB, ic_ready=False),
    _s("sec_edgar", "SEC EDGAR", "Public SEC filings (for public comparables / "
       "strategic acquirers).", _T.PUBLIC_DATASET,
       aliases=["edgar", "sec filings", "10-k", "10-q"],
       update_cadence="As filed.", freshness_lag="Near real-time at filing.",
       used_for=["Public-comp benchmarking."],
       strengths=["Audited public-company disclosures."],
       limitations=["Only public companies; limited private-target relevance."],
       source_confidence=_INFP, data_confidence=_PUB, ic_ready=False),
    _s("fred", "FRED", "Federal Reserve economic data (macro series).",
       _T.PUBLIC_DATASET, aliases=["federal reserve", "macro data"],
       update_cadence="Varies by series.", freshness_lag="Days to months.",
       used_for=["Macro context (rates, inflation)."],
       strengths=["Authoritative macro series."],
       limitations=["Macro context only; not deal-specific."],
       source_confidence=_INFP, data_confidence=_PUB, ic_ready=False),
    _s("irs_form_990", "IRS Form 990", "Nonprofit tax filings (for nonprofit "
       "health systems).", _T.PUBLIC_DATASET,
       aliases=["form 990", "990", "irs 990"],
       update_cadence="Annual.", freshness_lag="1-2+ years.",
       used_for=["Nonprofit-system financial context."],
       strengths=["Public financials for nonprofits not in HCRIS detail."],
       limitations=["Nonprofits only; lags; format inconsistencies."],
       source_confidence=_INFP, data_confidence=_PUB, ic_ready=False),
    _s("public_transaction_corpus", "Public Transaction Corpus", "PEdesk's "
       "corpus of realized PE-healthcare deals powering comps/benchmarks.",
       _T.PUBLIC_DATASET, aliases=["deal corpus", "corpus", "transaction corpus",
                                  "realized deals"],
       update_cadence=_NEEDS, freshness_lag=_NEEDS,
       used_for=["Comps, market rates, percentiles, sponsor track records, backtests."],
       related_routes=["/comparables", "/market-rates", "/comparable-outcomes",
                      "/library"],
       related_metrics=["ev_to_ebitda", "moic", "irr", "benchmark_percentile"],
       strengths=["Empirical realized-outcome basis for benchmarking."],
       limitations=["Has a real/synthetic split; thin segments are directional "
                    "only; coverage varies by sector."],
       provenance_notes="Corpus has a real vs synthetic provenance split — "
       "confirm which deals back a given figure.",
       source_confidence=_DOCD, data_confidence=_MIX, ic_ready=False),
    _s("public_market_data", "Public Market Data", "Public market pricing / "
       "trading data.", _T.PUBLIC_DATASET, aliases=["market data"],
       update_cadence="Varies.", freshness_lag="Varies.",
       used_for=["Market context / public-comp pricing."],
       strengths=["Market-based reference."],
       limitations=["Public-market relevance to private deals is limited."],
       source_confidence=_NV, data_confidence=_PUB, ic_ready=False),
    _s("regulatory_calendar_sources", "Regulatory Calendar Sources",
       "Sources behind the regulatory-event calendar.", _T.PUBLIC_DATASET,
       aliases=["regulatory calendar", "reg calendar"],
       update_cadence=_NEEDS, freshness_lag=_NEEDS,
       used_for=["Tracking regulatory events that could move a thesis."],
       related_routes=["/regulatory-calendar"],
       strengths=["Forward calendar of regulatory risk."],
       limitations=["Coverage/recency need source documentation."],
       source_confidence=_NV, data_confidence=_PUB, ic_ready=False),

    _s("benchmark_prior", "Benchmark Prior", "Peer/industry benchmark values "
       "used as a prior to fill gaps or contextualize a target.",
       _T.BENCHMARK_PRIOR, aliases=["benchmark", "prior", "industry benchmark",
                                   "peer benchmark"],
       update_cadence=_NEEDS, freshness_lag=_NEEDS,
       used_for=["Filling missing inputs; contextualizing observed values; "
                "stress/payer scenario priors."],
       related_routes=["/rcm-benchmarks", "/diligence/payer-stress",
                      "/diligence/benchmarks"],
       related_metrics=["benchmark_percentile", "imputation_share"],
       strengths=["Provides a defensible baseline when target data is thin."],
       limitations=["A prior is NOT the target — heavy reliance means the "
                    "result is benchmark-driven, not target-specific."],
       provenance_notes="Benchmark/prior values, not observed target data.",
       source_confidence=_INFP, data_confidence=_PUB, ic_ready=False),

    # ── Uploaded / target ───────────────────────────────────────────
    _s("canonical_claims_dataset", "Canonical Claims Dataset", "The normalized "
       "claims dataset assembled from a target's billing data.",
       _T.UPLOADED_TARGET_DATA, aliases=["claims", "claims dataset", "canonical claims"],
       update_cadence="Per engagement / data drop.", freshness_lag="As of the data drop.",
       used_for=["Denial prediction; RCM uplift; collections-leakage analysis."],
       related_routes=["/diligence/denial-prediction"],
       related_metrics=["denial_rate", "clean_claim_rate", "rcm_uplift",
                       "collections_leakage"],
       strengths=["Target-specific, claim-level granularity."],
       limitations=["Quality depends on the upload; mapping/normalization matters."],
       provenance_notes="Built from a target's own claims — observed target data.",
       source_confidence=_INFP, data_confidence=_OBS, ic_ready=True),
    _s("edi_837", "EDI 837 (Claims)", "X12 837 electronic claim submissions "
       "from the target.", _T.UPLOADED_TARGET_DATA,
       aliases=["837", "x12 837", "claim file", "837p", "837i"],
       update_cadence="Per data drop.", freshness_lag="As of the data drop.",
       used_for=["Claim-level denial / billing analysis."],
       related_routes=["/diligence/denial-prediction"],
       related_metrics=["denial_rate", "clean_claim_rate"],
       strengths=["Authoritative submitted-claim record."],
       limitations=["Needs pairing with 835 remits to see outcomes."],
       provenance_notes="Target's submitted claims (the billing side).",
       source_confidence=_INFP, data_confidence=_OBS, ic_ready=True),
    _s("edi_835", "EDI 835 (Remittance)", "X12 835 electronic remittance "
       "advice (payer payment/denial detail).", _T.UPLOADED_TARGET_DATA,
       aliases=["835", "x12 835", "remittance", "remit", "era"],
       update_cadence="Per data drop.", freshness_lag="As of the data drop.",
       used_for=["Denial reasons, payments, underpayment detection."],
       related_routes=["/diligence/denial-prediction"],
       related_metrics=["denial_rate", "net_collection_rate", "underpayment_rate"],
       strengths=["Authoritative payer-side payment/denial outcomes."],
       limitations=["Pair with 837 for full claim lifecycle."],
       provenance_notes="Payer remittance — the payment/denial outcome side.",
       source_confidence=_INFP, data_confidence=_OBS, ic_ready=True),
    _s("ehr_export", "EHR Export", "Clinical/operational export from the "
       "target's electronic health record.", _T.UPLOADED_TARGET_DATA,
       aliases=["ehr", "emr export", "clinical export"],
       used_for=["Clinical/operational and volume context."],
       related_metrics=["panel_size", "provider_productivity"],
       strengths=["Target-specific clinical/operational data."],
       limitations=["Export scope/quality varies widely by EHR and engagement."],
       data_confidence=_OBS, ic_ready=None),
    _s("provider_roster", "Provider Roster", "List of the target's providers "
       "with attributes (specialty, FTE, start dates).",
       _T.UPLOADED_TARGET_DATA, aliases=["roster", "physician roster", "provider list"],
       used_for=["Physician economics; attrition; productivity baselines."],
       related_routes=["/diligence/physician-eu", "/diligence/physician-attrition"],
       related_metrics=["physician_attrition", "wrvu", "panel_size",
                       "app_support_ratio"],
       strengths=["Ground truth for provider headcount/mix."],
       limitations=["Point-in-time; may not capture pending departures."],
       data_confidence=_OBS, ic_ready=True),
    _s("compensation_file", "Compensation File", "Provider compensation data "
       "from the target.", _T.UPLOADED_TARGET_DATA,
       aliases=["comp file", "compensation", "physician comp"],
       used_for=["Physician economics; comp-to-collections."],
       related_routes=["/diligence/physician-eu"],
       related_metrics=["compensation_to_collections", "provider_contribution_margin"],
       strengths=["Actual comp for physician-economics analysis."],
       limitations=["Comp structures are complex (bonus, draws); confirm scope."],
       data_confidence=_OBS, ic_ready=True),
    _s("payer_contracts", "Payer Contracts", "The target's payer contract terms "
       "/ fee schedules.", _T.UPLOADED_TARGET_DATA,
       aliases=["contracts", "payer contract", "fee schedule"],
       used_for=["Payer-stress; underpayment; rate analysis."],
       related_routes=["/diligence/payer-stress"],
       related_metrics=["payer_mix", "underpayment_rate", "commercial_payer_exposure"],
       strengths=["Authoritative contracted rates."],
       limitations=["Often incomplete; renegotiation timing matters."],
       data_confidence=_OBS, ic_ready=True),
    _s("monthly_actuals", "Monthly Actuals", "The target's/portfolio company's "
       "monthly actual financials.", _T.UPLOADED_TARGET_DATA,
       aliases=["actuals", "monthly financials", "monthlies"],
       update_cadence="Monthly.", freshness_lag="~1 month.",
       used_for=["Portfolio monitoring; value-plan realization tracking."],
       related_routes=["/portfolio/monitor"],
       related_metrics=["revenue", "ebitda", "adjusted_ebitda", "synergy_estimate"],
       strengths=["Most current observed financials."],
       limitations=["Unaudited; classification/cutoff can shift month to month."],
       data_confidence=_OBS, ic_ready=True),
    _s("seller_cim", "Seller CIM", "The seller's confidential information "
       "memorandum.", _T.SELLER_REPORTED, aliases=["cim", "deck", "teaser", "om"],
       used_for=["Initial framing; the seller's adjusted-EBITDA narrative."],
       related_routes=["/diligence/bridge-audit"],
       related_metrics=["adjusted_ebitda", "ebitda_bridge", "revenue"],
       strengths=["Seller's framing of the opportunity."],
       limitations=["Seller-prepared and inherently optimistic — verify, don't trust."],
       provenance_notes="Seller-reported; treat as a claim to be tested by QoE/diligence.",
       data_confidence=_USR, ic_ready=False),
    _s("qoe_report", "QoE Report", "Quality-of-earnings report vetting adjusted "
       "EBITDA and add-backs.", _T.SELLER_REPORTED,
       aliases=["qoe", "quality of earnings"],
       used_for=["Validating adjusted EBITDA / add-backs for the bridge."],
       related_routes=["/diligence/bridge-audit", "/diligence/qoe-memo"],
       related_metrics=["adjusted_ebitda", "ebitda_bridge"],
       strengths=["Independent-ish scrutiny of the earnings base."],
       limitations=["Scope/independence vary; confirm who commissioned it."],
       data_confidence=_MIX, ic_ready=True),
    _s("data_room_export", "Data Room Export", "Documents/exports from the "
       "deal data room.", _T.UPLOADED_TARGET_DATA,
       aliases=["data room", "vdr export", "dataroom"],
       used_for=["Diligence document evidence."],
       related_routes=["/diligence/deal"],
       strengths=["Primary diligence documents."],
       limitations=["Completeness/recency vary; seller controls contents."],
       data_confidence=_MIX, ic_ready=None),

    # ── Internal / system ───────────────────────────────────────────
    _s("deal_profile", "Deal Profile", "PEdesk's internal record of a deal's "
       "key attributes.", _T.SYSTEM_METADATA, aliases=["profile", "deal record"],
       used_for=["Seeding per-deal analyses and dashboards."],
       related_routes=["/diligence/deal"],
       strengths=["Single internal handle for a deal."],
       limitations=["Only as good as what was entered/imported."],
       data_confidence=_MIX, ic_ready=None),
    _s("analysis_run", "Analysis Run", "A stored run of the analysis packet "
       "for a deal.", _T.INTERNAL_MODEL_OUTPUT, aliases=["packet", "analysis", "run"],
       used_for=["Caching/serving a deal's computed analysis."],
       related_routes=["/analysis/<dealId>"],
       related_metrics=["model_estimate", "confidence_tier"],
       strengths=["Reproducible, audit-able computed output."],
       limitations=["A computed snapshot — re-run if inputs changed."],
       data_confidence=_EST, ic_ready=False),
    _s("model_output", "Model Output", "Output of a PEdesk model/estimator.",
       _T.INTERNAL_MODEL_OUTPUT, aliases=["model", "prediction", "estimate output"],
       used_for=["Predictions, scores, uplift/risk estimates across pages."],
       related_metrics=["model_estimate", "rcm_uplift", "risk_score",
                       "payer_stress_impact", "bridge_realization_probability"],
       strengths=["Consistent, scalable estimates."],
       limitations=["Estimates with uncertainty — never observed truth; "
                    "not a stand-alone IC basis."],
       provenance_notes="Internal model output — clearly an estimate, not observed.",
       data_confidence=_EST, ic_ready=False),
    _s("generated_export", "Generated Export", "Files PEdesk generates (CSV/"
       "Excel/PDF/memos).", _T.SYSTEM_METADATA, aliases=["export", "download"],
       used_for=["Deliverables (exports, memos, packets)."],
       strengths=["Shareable artifacts of platform output."],
       limitations=["Only as current as the run that produced them."],
       data_confidence=_MIX, ic_ready=None),
    _s("checklist_state", "Checklist State", "State of the diligence checklist "
       "for a deal.", _T.SYSTEM_METADATA, aliases=["checklist", "diligence checklist"],
       used_for=["Tracking diligence completion."],
       related_routes=["/diligence/checklist"],
       strengths=["Process/coverage tracking."],
       limitations=["Process state, not analytical data."],
       data_confidence=_OBS, ic_ready=None),
    _s("diligence_questions", "Diligence Questions", "The diligence-question "
       "ledger records.", _T.SYSTEM_METADATA, aliases=["questions", "question ledger"],
       used_for=["Tracking open diligence questions."],
       related_routes=["/diligence/questions"],
       strengths=["Running record of open items."],
       limitations=["Workflow data, not analytics."],
       data_confidence=_OBS, ic_ready=None),
    _s("audit_log", "Audit Log", "Unified log of user/system actions.",
       _T.SYSTEM_METADATA, aliases=["audit", "activity log"],
       update_cadence="Continuous (on action).", freshness_lag="Real-time.",
       used_for=["Accountability/audit trail."],
       related_routes=["/audit"],
       strengths=["Tamper-evident accountability."],
       limitations=["Operational metadata, not deal analytics."],
       data_confidence=_OBS, ic_ready=None),
    _s("engagement_record", "Engagement Record", "Record of a consulting/"
       "client engagement.", _T.SYSTEM_METADATA, aliases=["engagement", "portal record"],
       used_for=["Scoping engagement-level views/portals."],
       related_routes=["/engagements", "/portal/<engagementId>"],
       strengths=["Engagement-level organizing record."],
       limitations=["Metadata; specifics need source documentation."],
       data_confidence=_MIX, ic_ready=None),
    _s("portfolio_snapshot", "Portfolio Snapshot", "Live snapshot of the "
       "portfolio store (deal states, rollups).", _T.SYSTEM_METADATA,
       aliases=["portfolio", "snapshot", "rollup"],
       update_cadence="Live / on read.", freshness_lag="Current portfolio state.",
       used_for=["Command center, portfolio overview, risk scan, LP update."],
       related_routes=["/app", "/portfolio", "/portfolio/monitor",
                      "/portfolio/risk-scan"],
       related_metrics=["revenue", "ebitda", "moic", "irr"],
       strengths=["Current observed state of tracked deals."],
       limitations=["Reflects only what's tracked; single-machine store."],
       data_confidence=_OBS, ic_ready=True),

    # ── Special ─────────────────────────────────────────────────────
    _s("demo_fixture", "Demo Fixture", "Hardcoded illustrative/sample data used "
       "for demos and templates (NOT a real target's data).", _T.DEMO_FIXTURE,
       aliases=["demo", "fixture", "sample data", "illustrative"],
       update_cadence="Static.", freshness_lag="Not applicable.",
       used_for=["Illustrating page layouts/methodology where live data is absent."],
       strengths=["Shows what a page looks like populated."],
       limitations=["Representative ONLY — never a real portfolio/target figure; "
                    "never a basis for any conclusion."],
       provenance_notes="Illustrative template data; clearly not live/sourced.",
       source_confidence=_DOCD, data_confidence=_DEMO, ic_ready=False),
    # NOTE: deliberately NO bare "unknown" alias — a user asking about
    # "unknown" gets the not-found fallback, not this placeholder (still
    # reachable explicitly by id "unknown_source" / label "Unknown Source").
    _s("unknown_source", "Unknown Source", "Provenance not established for the "
       "data shown.", _T.UNKNOWN, aliases=[],
       update_cadence=_NEEDS, freshness_lag=_NEEDS,
       used_for=["Placeholder when a page's data lineage isn't documented."],
       strengths=[_NEEDS],
       limitations=["Provenance unknown — do not assert where the data came from."],
       provenance_notes=_NEEDS,
       source_confidence=_NV, data_confidence=_UNK, ic_ready=False),

    # ── Sector Intelligence: CMS Provider Data Catalog (public) ──────
    _s("cms_provider_data_catalog", "CMS Provider Data Catalog",
       "CMS's public Provider Data Catalog — agency/facility-level provider "
       "and quality datasets across care settings (the source family behind "
       "the Sector Intelligence pages).", _T.PUBLIC_DATASET,
       aliases=["provider data catalog", "pdc"],
       update_cadence="Refreshed by CMS on a rolling (often quarterly) basis.",
       freshness_lag="Months behind the reporting period.",
       used_for=["Sector market/provider/quality views (home health, hospice, …)."],
       related_routes=["/sector-intelligence", "/home-health", "/hospice"],
       strengths=["Free, comprehensive, comparable across Medicare-certified providers."],
       limitations=["Medicare-certified providers only; public quality data, "
                    "not commercial revenue or target-company financials."],
       provenance_notes="Public CMS dataset; cite the specific dataset id + release.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cms_home_health_provider_data", "CMS Home Health Care Agencies",
       "Vendored snapshot of CMS 'Home Health Care Agencies' (6jpm-sxkc): "
       "Medicare-certified agency identity, ownership, certification, and "
       "quality measures (star rating, timely initiation, functional "
       "improvement, discharge to community).", _T.PUBLIC_DATASET,
       aliases=["home health compare", "hha provider data", "6jpm-sxkc"],
       update_cadence="Rolling CMS releases (quarterly).",
       freshness_lag="Months behind the reporting period.",
       used_for=["The /home-health screener + state map."],
       related_routes=["/home-health"],
       related_metrics=["home_health_star_rating", "timely_initiation_of_care",
                        "discharge_to_community"],
       strengths=["Comprehensive public quality read across all Medicare-certified HHAs."],
       limitations=["Medicare-certified agencies only; commercial/private-pay "
                    "home care not represented; public quality, not financials; "
                    "claims-based ACH/ED measures are a separate dataset."],
       provenance_notes="CMS Provider Data Catalog dataset 6jpm-sxkc.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cms_hospice_provider_data", "CMS Hospice Provider Data",
       "Vendored snapshot of CMS 'Hospice - General Information' (yc9t-dgbk) + "
       "'Hospice - Provider Data' HIS measures (252m-zfp9): Medicare-certified "
       "hospice identity, ownership, and quality (Hospice Care Index, composite "
       "process, visits in last days).", _T.PUBLIC_DATASET,
       aliases=["hospice compare", "hospice provider data", "yc9t-dgbk", "252m-zfp9"],
       update_cadence="Rolling CMS releases (quarterly).",
       freshness_lag="Months behind the reporting period.",
       used_for=["The /hospice screener + state map."],
       related_routes=["/hospice"],
       related_metrics=["hospice_care_index", "hospice_composite_process",
                        "visits_in_last_days"],
       strengths=["Comprehensive public quality read across all Medicare-certified hospices."],
       limitations=["Medicare-certified hospices only; public quality, not "
                    "financials; CAHPS survey + length-of-stay/live-discharge "
                    "economics not in these files."],
       provenance_notes="CMS Provider Data Catalog datasets yc9t-dgbk + 252m-zfp9.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),

    # ── Real public datasets wired this session (committed PII-free aggregates,
    #    lru_cache loaders, no runtime network) ──────────────────────────────
    _s("cms_ffs_provider_enrollment", "CMS FFS Provider Enrollment",
       "Medicare-enrolled provider supply by state x provider type (PPEF).",
       _T.PUBLIC_DATASET, aliases=["provider supply", "ppef", "provider enrollment"],
       update_cadence="CMS rolling.", freshness_lag="Current extract.",
       used_for=["Provider-supply density / market-supply backdrop."],
       related_routes=["/provider-network", "/workforce-planning", "/market-intel/geo"],
       strengths=["Real national enrolled-provider universe (2.98M) by geography."],
       limitations=["FFS Medicare-enrolled only; not all providers; not quality."],
       provenance_notes="rcm_mc/data/provider_supply.py; registry cms_ffs_provider_enrollment.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cms_chow", "CMS Change of Ownership (CHOW)",
       "Medicare SNF + hospital ownership changes by state x year — a real "
       "consolidation / M&A-velocity signal.", _T.PUBLIC_DATASET,
       aliases=["chow", "ownership change", "consolidation"],
       update_cadence="CMS rolling.", freshness_lag="Through latest year.",
       used_for=["Consolidation velocity; antitrust/competitive context."],
       related_routes=["/concentration-risk", "/msa-concentration", "/competitive-intel",
                       "/antitrust-screener", "/market-intel/geo"],
       strengths=["Observed ownership-change counts (5,141 SNF + 755 hospital)."],
       limitations=["Buyer type unclassified (not PE-specific); not every transaction."],
       provenance_notes="rcm_mc/data/snf_chow.py; registry cms_snf_chow + cms_hospital_chow.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cms_ma_geo", "CMS Medicare Advantage Geographic Enrollment",
       "MA enrollment, dual-eligible share, and age by state.", _T.PUBLIC_DATASET,
       aliases=["medicare advantage", "ma enrollment", "dual eligible"],
       update_cadence="Annual.", freshness_lag="~1-2 years.",
       used_for=["Payer-mix / risk-adjustment / MA-market context."],
       related_routes=["/payer-concentration", "/risk-adjustment", "/medicaid-unwinding",
                       "/market-intel/geo"],
       strengths=["Real MA enrollment (29.7M) + dual-eligible share by state."],
       limitations=["MA only; geographic; not this deal's panel."],
       provenance_notes="rcm_mc/data/ma_data.py; registry cms_ma_geo_ry2025.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cms_open_payments", "CMS Open Payments",
       "Manufacturer/GPO payments to providers — device/pharma vendor scale.",
       _T.PUBLIC_DATASET, aliases=["open payments", "sunshine act", "manufacturer payments"],
       update_cadence="Annual.", freshness_lag="~1 year.",
       used_for=["Supply-vendor / device-manufacturer landscape."],
       related_routes=["/gpo-supply"],
       strengths=["Real $3.31bn manufacturer-payment universe; top vendors."],
       limitations=["Manufacturer-side only; PII-free aggregate; not GPO contract terms."],
       provenance_notes="rcm_mc/data/open_payments.py; registry cms_open_payments_2023.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cms_hcahps", "CMS HCAHPS Patient Experience",
       "Official CMS patient-experience survey top-box percentages by state.",
       _T.PUBLIC_DATASET, aliases=["hcahps", "patient survey", "patient experience"],
       update_cadence="Periodic CMS refreshes.", freshness_lag="Months to a year.",
       used_for=["Patient-experience benchmarking."],
       related_routes=["/patient-experience"],
       strengths=["Real regulator-published survey (feeds Stars/VBP)."],
       limitations=["State-level top-box; not this deal's facilities; national = state mean."],
       provenance_notes="rcm_mc/data/hcahps_data.py; CMS Care Compare 84jm-wiui; registry cms_hcahps_state.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cdc_places", "CDC PLACES (SDOH / health equity)",
       "Model-based full-population county estimates of SDOH + chronic disease, "
       "rolled to state/national prevalence.", _T.PUBLIC_DATASET,
       aliases=["places", "sdoh", "social determinants", "health equity"],
       update_cadence="Annual.", freshness_lag="~1-2 years.",
       used_for=["Health-equity / SDOH burden; demand-mix context."],
       related_routes=["/health-equity", "/telehealth-econ", "/market-intel/geo"],
       strengths=["Full-population SDOH (uninsured, food/transport insecurity)."],
       limitations=["Model-based estimates; area-level; not this deal's patients."],
       provenance_notes="rcm_mc/data/cdc_places_agg.py; CDC dataset i46a-9kgh; registry cdc_places_equity.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("hrsa_hpsa", "HRSA Health Professional Shortage Areas",
       "Designated primary-care shortage areas (HPSAs) + scores by state.",
       _T.PUBLIC_DATASET, aliases=["hpsa", "shortage area", "hrsa"],
       update_cadence="HRSA rolling.", freshness_lag="Current designations.",
       used_for=["Locum/staffing demand; retention-pressure backdrop."],
       related_routes=["/locum-tracker", "/workforce-retention"],
       strengths=["Real 7,635 designated PC HPSAs + shortage scores by state."],
       limitations=["Primary-care designations; area-level, not provider-specific."],
       provenance_notes="rcm_mc/data/hrsa_data.py; registry hrsa_hpsa_pc.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cms_mssp_aco", "CMS MSSP ACO Landscape",
       "Medicare Shared Savings Program ACOs, participant orgs, and risk-track mix.",
       _T.PUBLIC_DATASET, aliases=["mssp", "aco", "shared savings"],
       update_cadence="Annual.", freshness_lag="~1 year.",
       used_for=["Value-based / CIN shared-savings benchmark."],
       related_routes=["/cin-analyzer"],
       strengths=["Real 511 ACOs / 15,293 participant orgs / risk-track mix."],
       limitations=["MSSP only (not all value-based); ACO-level, not this CIN."],
       provenance_notes="rcm_mc/data/mssp_aco_data.py; registry cms_mssp_aco.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("civhc_rbp", "CIVHC Commercial-vs-Medicare (CO APCD)",
       "Colorado all-payer-claims reference-based-pricing: commercial price as "
       "% of Medicare by provider — the canonical contract/OON rate benchmark.",
       _T.PUBLIC_DATASET, aliases=["civhc", "rbp", "reference based pricing",
                                   "commercial percent of medicare", "qpa"],
       update_cadence="Annual.", freshness_lag="2021-2024 window.",
       used_for=["Payer-contract rate benchmark; NSA OON/QPA reference."],
       related_routes=["/payer-contracts", "/nsa-tracker", "/ref-pricing", "/payer-rate-trends"],
       strengths=["Real provider-level commercial-%-of-Medicare distribution."],
       limitations=["Colorado APCD (a reference benchmark, not national)."],
       provenance_notes="rcm_mc/data/payer_data.py (reference_pricing_summary); CIVHC/CO APCD.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("chr_county_demographics", "County Demographics (Census/ACS via CHR)",
       "Census/ACS county demographics (population, age 65+, income, poverty, "
       "uninsured, race/ethnicity, rural) republished keyless by County Health "
       "Rankings.", _T.PUBLIC_DATASET,
       aliases=["acs", "census demographics", "county health rankings", "chr"],
       update_cadence="Annual.", freshness_lag="ACS 5-yr pooled.",
       used_for=["Market demand fundamentals (population/age/income/uninsured)."],
       related_routes=["/market-intel/geo", "/market-data/state/CA"],
       strengths=["Real county+state demographics, FIPS preserved."],
       limitations=["ACS survey estimates; area-level, not provider-specific."],
       provenance_notes="rcm_mc/data/county_demographics.py; CHR analytic file; registry chr_county_demographics.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("cms_partd_drug_spending", "CMS Part D Spending by Drug",
       "Medicare Part D retail drug spend + per-dosage-unit price and its "
       "2019-2023 CAGR — a real drug-cost / price-inflation signal.",
       _T.PUBLIC_DATASET, aliases=["part d spending", "drug spending", "drug pricing",
                                   "drug price inflation"],
       update_cadence="Annual.", freshness_lag="~1-2 years (2023 DY).",
       used_for=["Drug-cost / price-inflation context (340B / drug-pricing)."],
       related_routes=["/drug-pricing-340b", "/tracker-340b"],
       strengths=["Real $275.9B Part D spend across 3,598 drugs + per-unit price CAGR."],
       limitations=["Part D RETAIL spend, NOT 340B ceiling prices; not this deal's formulary."],
       provenance_notes="rcm_mc/data/partd_drug.py; CMS Part D Spending by Drug; registry cms_partd_drug_spending.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("clinicaltrials_gov", "ClinicalTrials.gov Trial Landscape",
       "U.S. NLM clinical-trials registry counts (total / recruiting / "
       "interventional / by phase) — a trial-volume / site-demand signal.",
       _T.PUBLIC_DATASET, aliases=["clinicaltrials", "trials registry", "trial sites"],
       update_cadence="Continuous (registry).", freshness_lag="Near-real-time.",
       used_for=["Clinical-research-site demand / phase-mix context."],
       related_routes=["/trial-site-econ"],
       strengths=["Real 586K registered / 65K recruiting / 447K interventional studies."],
       limitations=["Registry counts, not this deal's sites or revenue; not 100% of trials."],
       provenance_notes="rcm_mc/data/clinical_trials.py; ClinicalTrials.gov v2 API; registry clinicaltrials_gov.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
    _s("oig_leie", "OIG LEIE Exclusions",
       "HHS OIG List of Excluded Individuals/Entities — the realized "
       "Medicare/Medicaid fraud-&-abuse / sanction record.", _T.PUBLIC_DATASET,
       aliases=["leie", "oig exclusions", "excluded providers", "sanctions"],
       update_cadence="Monthly.", freshness_lag="Current month.",
       used_for=["Fraud/abuse base rate; exclusion screening context."],
       related_routes=["/fraud-detection"],
       strengths=["Real 83K+ excluded entities by state / type / year (PII dropped)."],
       limitations=["Realized exclusions, NOT a prediction; not this deal's providers; names/NPI dropped at ingest."],
       provenance_notes="rcm_mc/data/oig_leie.py; oig.hhs.gov LEIE; registry oig_leie.",
       source_confidence=_DOCD, data_confidence=_PUB, ic_ready=False),
]

DATA_SOURCE_REGISTRY: Dict[str, DataSourceContext] = {
    s.source_id: s for s in _SOURCES
}
