# docs/

Reference documents that don't belong in the numbered user guide (`readME/`) — canonical specs, the PE heuristics rulebook, domain deep-dives, and strategic planning.

**First time here?** Start with the repo-root **[README.md](../../README.md)** for a plain-English explanation of what the tool does, or **[WALKTHROUGH.md](../../WALKTHROUGH.md)** for a case study.

**Main documentation index**: [readME/README.md](../readME/README.md)

**New-module READMEs** (cycle-shipped diligence surfaces):
- [HCRIS X-Ray](../rcm_mc/diligence/hcris_xray/README.md)
- [Regulatory Calendar](../rcm_mc/diligence/regulatory_calendar/README.md)
- [Covenant Stress Lab](../rcm_mc/diligence/covenant_lab/README.md)
- [Bridge Auto-Auditor](../rcm_mc/diligence/bridge_audit/README.md)
- [Bear Case Auto-Generator](../rcm_mc/diligence/bear_case/README.md)
- [Payer Mix Stress](../rcm_mc/diligence/payer_stress/README.md)
- [Thesis Pipeline](../rcm_mc/diligence/thesis_pipeline/README.md)

---

## Reference specs

| File | What it is |
|------|-----------|
| [ANALYSIS_PACKET.md](ANALYSIS_PACKET.md) | Canonical spec for the `DealAnalysisPacket` dataclass — every field, its type, and what builds it |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture deep-dive: layer diagram, dependency rules, design decisions |
| [BENCHMARK_SOURCES.md](BENCHMARK_SOURCES.md) | Data source reference — CMS HCRIS, Care Compare, Utilization, IRS 990, SEC EDGAR field-by-field |
| [METRIC_PROVENANCE.md](METRIC_PROVENANCE.md) | How each metric traces back to its source, with confidence tiers |
| [MODEL_IMPROVEMENT.md](MODEL_IMPROVEMENT.md) | Known model limitations and the improvement roadmap (Tier 1–3) |
| [PE_HEURISTICS.md](PE_HEURISTICS.md) | PE partner rule catalog: 275+ named heuristics, failure patterns, and thesis-trap detectors used by the `pe_intelligence/` brain |
| [UI_KIT.md](UI_KIT.md) | Reference for the canonical UI primitives (buttons / cards / inputs / KPIs) and the semantic color system |
| [MISSION_ALIGNMENT.md](MISSION_ALIGNMENT.md) | What this product is for, who it serves, what we won't build |

---

## Strategic planning (Apr 2026 cycle)

Fifteen strategy documents written during the most recent autonomous-loop cycle. They are the load-bearing planning surface for the next 12+ months — the [PRODUCT_ROADMAP_6MO.md](PRODUCT_ROADMAP_6MO.md) picks the subset of these that actually ship May–Oct 2026; everything else is consciously deferred.

| File | What it covers |
|------|----------------|
| [PRODUCT_ROADMAP_6MO.md](PRODUCT_ROADMAP_6MO.md) | **6-month roadmap (May–Oct 2026)** — Q2 pre-beta hardening + 3 design partners; Q3 multi-tenancy + Cohort 1 run + Cohort 2 sales. Capacity-calibrated to ~0.6 → ~0.9 build FTE with explicit cuts |
| [BETA_PROGRAM_PLAN.md](BETA_PROGRAM_PLAN.md) | **3-cohort beta program** — Design Partners (n=3, white-glove) → Validation Beta (n=8-10, $50K pilot) → Pre-GA Beta (n=15-20, self-service). 4 objectives, ~$700K-1M budget, GA graduation criteria |
| [BUSINESS_MODEL.md](BUSINESS_MODEL.md) | **Monetization plan** — 3-tier pricing (per-seat / platform / deal-volume), unit economics, expansion-revenue motions |
| [PARTNERSHIPS_PLAN.md](PARTNERSHIPS_PLAN.md) | **Partnerships strategy** — Tier 1-4 partners with prioritization, outreach copy, integration scope per tier |
| [COMPETITIVE_LANDSCAPE.md](COMPETITIVE_LANDSCAPE.md) | **Competitive map** — Trilliant / Definitive / PitchBook / consultant overlap; positioning + how we win |
| [MULTI_ASSET_EXPANSION.md](MULTI_ASSET_EXPANSION.md) | **Beyond hospitals** — physician groups, ASCs, behavioral, post-acute. Sequencing + data-source map |
| [MULTI_USER_ARCHITECTURE.md](MULTI_USER_ARCHITECTURE.md) | **Deal teams** — auth, organizations, comments, presence, shared annotations. Phase 1 (auth + isolation) vs Phase 2 (collaboration) |
| [PHI_SECURITY_ARCHITECTURE.md](PHI_SECURITY_ARCHITECTURE.md) | **PHI handling** — BAA template, SOC 2 Type II plan, tenant isolation tiers (T1 → T3), customer-managed keys |
| [INTEGRATIONS_PLAN.md](INTEGRATIONS_PLAN.md) | **API + integrations** — public REST surface, Salesforce / Affinity / Slack hooks, ranked by customer pull |
| [REGULATORY_ROADMAP.md](REGULATORY_ROADMAP.md) | **18-month regulatory calendar** — OPPS / LEAD / ILPA / CPOM rule changes, modeling implications, kill-switch updates |
| [DATA_ACQUISITION_STRATEGY.md](DATA_ACQUISITION_STRATEGY.md) | **12-month data plan** — 13 candidate sources ranked by lift / effort, with refresh cadence + provenance posture |
| [LEARNING_LOOP.md](LEARNING_LOOP.md) | **Closed feedback loop** — predicted vs actual capture, calibration thresholds, model retraining cadence, fund-level shrinkage |
| [V2_PLAN.md](V2_PLAN.md) | **What we'd do differently** if rebuilding today; applied incrementally — no big-bang rewrite |
| [NEXT_CYCLE_PLAN.md](NEXT_CYCLE_PLAN.md) | **Top-5 features ranked** for the next short cycle (the input that fed the 6-month roadmap) |
| [MD_DEMO_SCRIPT.md](MD_DEMO_SCRIPT.md) | **10-minute demo script** for a PE managing director — every step works flawlessly on the fixture data |

---

## Cycle retros

| File | Cycle covered |
|------|---------------|
| [CYCLE_RETRO.md](CYCLE_RETRO.md) | Earlier cycle retrospective |
| [CYCLE_RETRO_2.md](CYCLE_RETRO_2.md) | |
| [CYCLE_RETRO_3.md](CYCLE_RETRO_3.md) | |
| [CYCLE_RETRO_4.md](CYCLE_RETRO_4.md) | Most recent retro |

---

## Reading order for someone new

1. **Repo-root [README.md](../../README.md)** — what this tool does in plain English
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** — how the layers fit together
3. **[ANALYSIS_PACKET.md](ANALYSIS_PACKET.md)** — the load-bearing dataclass everything renders from
4. **[PE_HEURISTICS.md](PE_HEURISTICS.md)** — the partner-rule catalog the engine sits on top of
5. **[PRODUCT_ROADMAP_6MO.md](PRODUCT_ROADMAP_6MO.md)** — what's shipping next
6. **[BETA_PROGRAM_PLAN.md](BETA_PROGRAM_PLAN.md)** — how we validate it with real PE firms
