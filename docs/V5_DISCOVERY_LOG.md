# V5 Discovery Log

Per Rule Zero of the v5 transformation campaign: every loop runs the
discovery queries below before adding any new file. The output gets
appended here so future loops can find existing renderers / partials
/ pages instead of reinventing them. The single biggest waste is
reinventing a page that already lives in the repo.

## Discovery queries (run `bash docs/V5_DISCOVERY_LOG.run.sh` to refresh)

```bash
rg --type py "def render_" RCM_MC/ | head -200
rg --type py "def page_" RCM_MC/
rg --type py -n "<html|<body|<nav|<main|<table" RCM_MC/
ls RCM_MC/rcm_mc/_ui_kit.py RCM_MC/rcm_mc/templates/ RCM_MC/rcm_mc/partials/ RCM_MC/rcm_mc/components/ 2>/dev/null
rg --type py "shell\(" RCM_MC/ -l
rg --type py "DealAnalysisPacket|get_or_build_packet" RCM_MC/ -l
git log --all --diff-filter=A --name-only -- "*.py" | sort -u | grep -i -E "page|render|view|template"
```

## Snapshot — 2026-04-27T23:38:49Z

### Render functions (`def render_`)

623 render_* functions found

Top-level `render_*` callers (top 60 lines):

```text
RCM_MC/rcm_mc/screening/dashboard.py:def render_screening_dashboard(
RCM_MC/rcm_mc/ic_memo/render.py:def render_memo_markdown(memo: ICMemo) -> str:
RCM_MC/rcm_mc/ic_memo/render.py:def render_memo_html(memo: ICMemo) -> str:
RCM_MC/rcm_mc/esg/issb.py:def render_ifrs_s1(
RCM_MC/rcm_mc/esg/issb.py:def render_ifrs_s2(
RCM_MC/rcm_mc/esg/issb.py:def render_issb_markdown(report: ISSBStandardReport) -> str:
RCM_MC/rcm_mc/esg/issb.py:def render_lp_package_markdown(package: LPPackage) -> str:
RCM_MC/rcm_mc/esg/disclosure.py:def render_lp_disclosure(scorecard: EDCIScorecard) -> str:
RCM_MC/tools/build_dep_graph.py:def render_text_summary(edges: Dict[Tuple[str, str], int], file_counts: Counter) -> str:
RCM_MC/tools/build_dep_graph.py:def render_mermaid(edges: Dict[Tuple[str, str], int], file_counts: Counter,
RCM_MC/rcm_mc/portfolio_monitor/dashboard.py:def render_monitor_dashboard(
RCM_MC/rcm_mc/ui/management_scorecard_page.py:def render_management_scorecard_page(
RCM_MC/rcm_mc/ui/conference_page.py:def render_conference_roadmap(category: str = "all") -> str:
RCM_MC/rcm_mc/irr_attribution/ilpa.py:def render_lp_narrative(result: AttributionResult) -> str:
RCM_MC/rcm_mc/ui/compare_page.py:def render_compare_page(
RCM_MC/rcm_mc/ui/data_catalog_page.py:def render_data_catalog_page(store: Any) -> str:
RCM_MC/rcm_mc/ui/hospital_profile.py:def render_hospital_profile(
RCM_MC/rcm_mc/ui/denial_prediction_page.py:def render_denial_prediction_page(
RCM_MC/rcm_mc/ui/v5_status_page.py:def render_v5_status() -> str:
RCM_MC/rcm_mc/ui/verticals_page.py:def render_verticals() -> str:
RCM_MC/rcm_mc/exports/qoe_memo.py:def render_qoe_memo_html(
RCM_MC/rcm_mc/ui/team_page.py:def render_team_dashboard(db_path: str) -> str:
RCM_MC/rcm_mc/ui/analytics_pages.py:def render_causal_page(deal_id: str, deal_name: str, estimates: List[Dict[str, Any]]) -> str:
RCM_MC/rcm_mc/ui/analytics_pages.py:def render_counterfactual_page(deal_id: str, deal_name: str, result: Dict[str, Any]) -> str:
RCM_MC/rcm_mc/ui/analytics_pages.py:def render_benchmark_drift(drifts: List[Dict[str, Any]]) -> str:
RCM_MC/rcm_mc/ui/analytics_pages.py:def render_predicted_vs_actual(deal_id: str, deal_name: str,
RCM_MC/rcm_mc/exports/packet_renderer.py:    def render_diligence_memo_html(
RCM_MC/rcm_mc/exports/packet_renderer.py:    def render_diligence_memo_pptx(
RCM_MC/rcm_mc/exports/packet_renderer.py:    def render_deal_xlsx(
RCM_MC/rcm_mc/exports/packet_renderer.py:    def render_packet_json(self, packet: DealAnalysisPacket) -> str:
RCM_MC/rcm_mc/exports/packet_renderer.py:    def render_raw_data_csv(
RCM_MC/rcm_mc/exports/packet_renderer.py:    def render_lp_update_html(
RCM_MC/rcm_mc/exports/packet_renderer.py:    def render_diligence_questions_docx(
RCM_MC/rcm_mc/ui/demand_page.py:def render_demand_analysis(profile: Dict[str, Any]) -> str:
RCM_MC/rcm_mc/ui/deal_dashboard.py:def render_deal_dashboard(
RCM_MC/rcm_mc/exports/ic_packet.py:def render_ic_packet_html(
RCM_MC/rcm_mc/ui/data_refresh_page.py:def render_data_refresh_page(db_path: str) -> str:
RCM_MC/rcm_mc/ui/exports_index_page.py:def render_exports_index(db_path: str) -> str:
RCM_MC/rcm_mc/ic_binder/markdown.py:def render_markdown_binder(synthesis_result: Any) -> str:
RCM_MC/rcm_mc/exports/xlsx_renderer.py:def render_deal_xlsx(
RCM_MC/rcm_mc/ui/market_intel_page.py:def render_market_intel_page(
RCM_MC/rcm_mc/ui/compare.py:def render_comparison(
RCM_MC/rcm_mc/ic_binder/html.py:def render_html_binder(synthesis_result: Any,
RCM_MC/rcm_mc/ui/covenant_lab_page.py:def render_covenant_lab_page(
RCM_MC/rcm_mc/ui/bayesian_page.py:def render_bayesian_profile(
RCM_MC/rcm_mc/ui/regulatory_calendar_page.py:def render_regulatory_calendar_page(
RCM_MC/rcm_mc/exit_readiness/roadmap.py:def render_roadmap_markdown(roadmap: ReadinessRoadmap) -> str:
RCM_MC/rcm_mc/ui/quant_lab_page.py:def render_quant_lab(hcris_df: pd.DataFrame) -> str:
RCM_MC/rcm_mc/ui/feature_importance_viz.py:def render_importance_bar_chart(
RCM_MC/rcm_mc/ui/feature_importance_viz.py:def render_importance_panel(
RCM_MC/rcm_mc/ui/feature_importance_viz.py:def render_feature_importance_page(
RCM_MC/rcm_mc/pe_intelligence/bidder_landscape_reader.py:def render_bidder_landscape_markdown(
RCM_MC/rcm_mc/pe_intelligence/partner_voice_variants.py:def render_voices_markdown(bundle: VoiceBundle) -> str:
RCM_MC/rcm_mc/ui/hold_dashboard.py:def render_hold_dashboard(
RCM_MC/rcm_mc/diligence/_pages.py:def render_ingest_page(dataset: str = "") -> str:
RCM_MC/rcm_mc/diligence/_pages.py:def render_benchmarks_page(
RCM_MC/rcm_mc/diligence/_pages.py:def render_qoe_memo_page(
RCM_MC/rcm_mc/diligence/_pages.py:def render_root_cause_page(dataset: str = "") -> str:
RCM_MC/rcm_mc/diligence/_pages.py:def render_value_page(dataset: str = "") -> str:
RCM_MC/rcm_mc/ui/power_chart.py:def render_power_chart(
```

### Pages with module-level shell wrap (`shell(`)

```text

```

### Packet-driven renderers (`DealAnalysisPacket | get_or_build_packet`)

```text
RCM_MC/rcm_mc/pe/cms_advisory_bridge.py
RCM_MC/tools/v3_route_inventory.py
RCM_MC/rcm_mc/exports/packet_renderer.py
RCM_MC/rcm_mc/ui/data_catalog_page.py
RCM_MC/rcm_mc/exports/__init__.py
RCM_MC/rcm_mc/analysis/packet.py
RCM_MC/rcm_mc/exports/xlsx_renderer.py
RCM_MC/rcm_mc/ui/exports_index_page.py
RCM_MC/rcm_mc/exports/diligence_package.py
RCM_MC/rcm_mc/ui/compare.py
RCM_MC/rcm_mc/analysis/refresh_scheduler.py
RCM_MC/rcm_mc/analysis/packet_builder.py
RCM_MC/rcm_mc/ui/feature_importance_viz.py
RCM_MC/rcm_mc/analysis/__init__.py
RCM_MC/rcm_mc/analysis/analysis_store.py
RCM_MC/rcm_mc/dev/seed.py
RCM_MC/rcm_mc/infra/openapi.py
RCM_MC/tests/test_concurrent_analysis.py
RCM_MC/rcm_mc/cli.py
RCM_MC/tests/test_large_portfolio.py
RCM_MC/rcm_mc/provenance/graph.py
RCM_MC/tests/test_v2_monte_carlo.py
RCM_MC/tests/test_phase_j.py
RCM_MC/tests/test_integrations_full_stack.py
RCM_MC/tests/test_analysis_packet.py
RCM_MC/tests/test_provenance_graph.py
RCM_MC/tests/test_ui_pages.py
RCM_MC/tests/test_state_regulatory.py
RCM_MC/tests/test_temporal_forecaster.py
RCM_MC/tests/test_value_bridge_v2.py
RCM_MC/tests/test_pe_intelligence.py
RCM_MC/tests/test_lever_dependency.py
RCM_MC/tests/test_v5_status_page.py
RCM_MC/tests/test_deal_comparison_screening.py
RCM_MC/tests/test_hardening.py
RCM_MC/tests/test_deep_integration.py
RCM_MC/tests/test_sprint7.py
RCM_MC/tests/test_infra_hardening.py
RCM_MC/tests/test_full_analysis_workflow.py
RCM_MC/tests/test_packet_sparse_data.py
```

### UI partials / templates / components

(none of the canonical partial dirs present — partials live in rcm_mc/ui/_*.py helpers)

## How to use this log

When a future loop is about to ship a NEW renderer / partial / page:

1. Re-run the discovery snapshot above.
2. Search this file (and the snapshot) for the noun you're about to
   build (e.g. "covenant", "exit timing", "physician attrition").
3. If something matching exists — even partially — MIGRATE / EXTEND
   / RENAME it instead of building from scratch.
4. The commit message must say either:
   - `Discovery: existing renderer reused — <module>:<function>`, or
   - `Discovery: no existing renderer found; new file justified by <reason>`.

Building from scratch is the LAST RESORT.
