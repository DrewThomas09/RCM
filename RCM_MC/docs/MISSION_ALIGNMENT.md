# Mission Alignment — What's Core, What's Peripheral

## The mission

**RCM due diligence intelligence for PE healthcare acquisitions.**

Concretely: an associate or partner at a healthcare-focused PE firm
is evaluating a hospital, physician group, or SNF for acquisition.
They need to (1) ingest the target's RCM data, (2) benchmark it
against HFMA norms and public comps, (3) identify revenue leakage
and the EBITDA improvement opportunity, (4) stress-test the thesis,
and (5) produce a signed IC deliverable.

Everything else is peripheral.

## What counts as CORE

Five concentric capabilities. A feature is core if it lives inside
one of these rings:

1. **Data ingestion from public + target sources** — 837/835 EDI,
   CSV claims, HCRIS, IRS 990, CMS public data, NPI registry.
2. **Predictive RCM analytics** — not just descriptive benchmarks.
   Claim-level denial prediction, A/R trajectory, cohort
   liquidation forecasts, contract-yield gap analysis.
3. **EBITDA bridge** — connecting RCM improvements to dollar
   EBITDA with Monte Carlo uncertainty bands and driver
   attribution.
4. **Comparable analysis** — public operator multiples, private
   PE transaction multiples, peer-distance scoring.
5. **IC-ready exports** — QoE memo, IC packet, counterfactual
   walkaway conditions.

## Module-by-module classification

### CORE (11 modules)

| Module | Ring | Status |
|---|---|---|
| `rcm_mc/diligence/ingest/` | #1 | Mature, 17 fixtures |
| `rcm_mc/diligence/benchmarks/` (KPIs, cohort, waterfall, repricer) | #2, #3 | Mature |
| `rcm_mc/diligence/integrity/` (CCD guardrails) | #1 | Mature |
| `rcm_mc/diligence/root_cause/` (denial drill-down) | #2 | Mature |
| `rcm_mc/diligence/denial_prediction/` **(NEW)** | #2 | Shipped alongside this doc |
| `rcm_mc/pe/rcm_ebitda_bridge.py` + `value_bridge_v2.py` | #3 | Mature |
| `rcm_mc/core/simulator.py` (Monte Carlo chassis) | #3 | Mature |
| `rcm_mc/diligence/deal_mc/` (5-yr forward + attribution) | #3 | Mature |
| `rcm_mc/market_intel/` (public comps + multiples) | #4 | Mature |
| `rcm_mc/exports/qoe_memo.py` | #5 | Mature |
| `rcm_mc/exports/ic_packet.py` | #5 | Mature |

### SUPPORTING — serves the mission but indirectly (9 modules)

These earn their keep because they catch deal-level risks that
destroy EBITDA cases. They are not RCM analytics strictly speaking
but a PE associate would miss revenue/cost if they weren't run.

| Module | Why it stays |
|---|---|
| `rcm_mc/diligence/regulatory/` (CPOM, NSA, TEAM, site-neutral, antitrust) | Regulatory headwinds are a direct EBITDA input; several RED states void deals |
| `rcm_mc/diligence/real_estate/` (Steward Score) | Sale-leaseback is the #1 underwriting blind spot; affects EBITDAR coverage |
| `rcm_mc/diligence/cyber/` (CyberScore + BI loss) | Post-Change Healthcare this is a bridge reserve line item |
| `rcm_mc/diligence/ma_dynamics/` (V28) | MA-exposed targets have V28 revenue compression that hits EBITDA directly |
| `rcm_mc/diligence/physician_comp/` (FMV + drift) | Comp is the largest cost line in physician-group deals |
| `rcm_mc/diligence/labor/` (wage inflation, synthetic FTE) | Wage inflation is an explicit bridge lever |
| `rcm_mc/diligence/referral/` (leakage + concentration) | Revenue-retention test |
| `rcm_mc/diligence/screening/bankruptcy_survivor.py` | Pre-NDA screen — kills bad deals before RCM analytics run |
| `rcm_mc/diligence/counterfactual/` | Translates findings into offer-shaping levers — enables the IC packet |

### PERIPHERAL — freeze feature development (7 modules)

These exist for reasons but do NOT earn continued investment of
build hours. Keep them running, fix breakage, but do not add
features.

| Module | Rationale for deprioritization |
|---|---|
| `rcm_mc/engagement/` (RBAC + comments + client portal + draft/publish) | SaaS ops surface. A real deployment needs it eventually but it's not what makes the product defensible. |
| `rcm_mc/compliance/` (HIPAA/SOC2 docs, PHI scanner, audit chain) | Infrastructure / sales enablement. Necessary for enterprise sale, not a diligence analytic. |
| `rcm_mc/integrations/chart_audit.py`, `contract_digitization.py` | Vendor stubs — swap for real HTTP clients only when a vendor is bought. |
| `rcm_mc/reports/exit_memo.py`, `lp_update.py`, etc. | Post-close lifecycle — out of scope for diligence tool. |
| `rcm_mc/portfolio/` (cohorts, health score, watchlist) | Phase-3 portfolio ops — distinct product surface. |
| `rcm_mc/ui/chartis/marketing_page.py` + UI v2 editorial rework | Branding, not analytics. |
| `rcm_mc/alerts/` | Post-close monitoring. |

### DEPRIORITIZATION POSTURE

- **Keep tests green** — no module is "deleted." Breaking Phase-3
  tests destroys 2,878 passing tests + the load-bearing
  DealAnalysisPacket that every core export consumes.
- **No new features** on PERIPHERAL modules.
- **All roadmap hours** go to the 11 CORE modules + 9 SUPPORTING
  when they feed the EBITDA bridge.
- **New feature proposals** must answer: which of the five
  concentric rings does this strengthen? If none → reject.

## Double-down targets (in priority order)

1. **Deeper CCD ingestion** — real 10M-claim-scale performance,
   data-quality gauntlet extensions, 278 / 277 / EOB support
   beyond 837/835.
2. **Predictive RCM analytics** — **claim-level denial prediction
   shipped with this doc**. Next: A/R trajectory time-series,
   contract-yield gap scoring, denial-category drift forecast.
3. **EBITDA bridge attribution** — ties the Deal MC variance
   attribution back to specific CCD cohorts/claims.
4. **Comparable analysis depth** — Real Seeking Alpha / PitchBook /
   Bloomberg adapter implementations when a partnership lands.
5. **IC packet artifact fidelity** — partner-editable sections,
   version history, draft-vs-final comparison.

## Anti-patterns to avoid

- ❌ Building another dashboard that doesn't feed the bridge
- ❌ Adding regulatory modules for specialties the platform's deal
  pipeline doesn't touch (e.g., pharma, medical devices)
- ❌ UI rewrites that don't add analytical depth
- ❌ SaaS features (user management, audit logs, workflow) ahead
  of the analytic features partners actually demo
- ❌ Vendor integrations without signed contracts
