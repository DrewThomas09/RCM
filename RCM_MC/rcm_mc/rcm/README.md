# RCM (Revenue Cycle Management)

Revenue cycle management operational modeling: claim distributions, initiative libraries, optimization, tracking, and cross-deal rollup. Bridges the gap between simulated EBITDA impact and the specific operational initiatives a deal team executes.

---

## `claim_distribution.py` — Claim Bucket Builder

**What it does:** Builds lognormal claim-size bucket distributions per payer and models per-bucket denial rates for the simulation engine.

**How it works:** `build_claim_distribution(payer_config)` — fits a lognormal distribution to claim sizes using method-of-moments from the config's `claim_mean` and `claim_std` parameters. Discretizes into 5 size buckets (micro: <$500, small: $500–2K, medium: $2K–10K, large: $10K–50K, major: >$50K). Each bucket gets a per-bucket denial rate (larger claims have different denial patterns than smaller ones). Returns a `ClaimBucketDistribution` used by `core/simulator.py`.

**Data in:** Payer configuration dict from `infra/config.py` with claim size and denial rate parameters.

**Data out:** `ClaimBucketDistribution` for `core/simulator.py` claim-level simulation.

---

## `initiatives.py` — Initiative Library Loader

**What it does:** Loads the standard RCM initiative library from `configs/initiatives_library.yaml`. Provides 8–12 named initiatives (denial management, CDI program, payer renegotiation, AR acceleration, etc.) with their parameter deltas, costs, ramp curves, and confidence ratings.

**How it works:** `load_initiatives_library(path)` — reads the YAML via `pyyaml`, returns the `initiatives` list. `get_initiative(initiatives, id)` — finds by id. Each initiative dict has: `id`, `name`, `category`, `affected_params` (dict of metric → target delta), `annual_cost_mm` (implementation cost), `ramp_curve` (family name for `pe/ramp_curves.py`), `confidence` (0–1 analyst confidence weight). Falls back to an empty list if the YAML is not found (non-critical for unit tests).

**Data in:** `configs/initiatives_library.yaml` from the project root.

**Data out:** Initiative dicts consumed by `initiative_optimizer.py`, `value_creation_plan.py`, and the 100-day plan builder.

---

## `initiative_optimizer.py` — Initiative ROI Ranker

**What it does:** Ranks initiatives by EBITDA uplift, EV uplift, payback period, and confidence using N+1 simulation runs (one baseline + one per initiative). Returns a prioritized initiative stack.

**How it works:** `optimize_initiatives(config, initiatives, store)` — runs the baseline simulation once. For each initiative: builds a modified config with the initiative's `affected_params` deltas applied, runs a second simulation, computes the marginal EBITDA uplift vs. baseline. Ranks by: `score = (ebitda_uplift × confidence) / payback_months`. Returns a ranked `InitiativeRanking` list with per-initiative ROI metrics. Handles dependency ordering via `pe/lever_dependency.py` for initiatives with causal relationships.

**Data in:** Base simulation config from `infra/config.py`; initiative library from `initiatives.py`; simulation engine from `core/kernel.py`.

**Data out:** Ranked `InitiativeRanking` list for the value creation plan builder and the "Which initiative first?" workbench panel.

---

## `initiative_tracking.py` — Hold-Period Initiative Attribution

**What it does:** Per-initiative quarterly attribution during the hold period: actual dollar impact vs. the underwritten plan with variance reporting. Answers "is the denial management initiative on track?"

**How it works:** `initiative_variance_report(deal_id, store)` — loads quarterly actuals from `deals/deal_sim_inputs.py`, loads the underwritten plan from `analysis_runs`, matches actuals to initiatives using metric overlap heuristics (denial rate improvement maps to denial management initiative), and computes per-initiative actual EBITDA impact vs. plan. Returns a `InitiativeVarianceReport` with per-initiative status (on-track / at-risk / behind) and cumulative dollar variance.

**Data in:** Quarterly actual metric snapshots from `deals/deal_sim_inputs.py`; underwritten initiative targets from `analysis_runs` cache.

**Data out:** `InitiativeVarianceReport` for the hold-period tracking panel.

---

## `initiative_rollup.py` — Cross-Deal Initiative Performance Rollup

**What it does:** Aggregates initiative performance across all portfolio deals to identify systematic playbook issues. "Payer renegotiation is running at 45% of underwriting across 6 deals — is this a playbook problem?"

**How it works:** Queries all active deals' `InitiativeVarianceReport` objects from the store. Groups by initiative category. Computes mean and median realization rates per category. Flags categories where median realization < 60% across 3+ deals as a systematic playbook issue. Returns a `PlaybookRollup` for the Fund Learning page.

**Data in:** Initiative variance reports from `initiative_tracking.py` for all active portfolio deals.

**Data out:** `PlaybookRollup` for the Fund Learning page and `ml/fund_learning.py`.

---

## Key Concepts

- **Initiative library as config**: Standard initiatives are defined in YAML with affected parameters, delta distributions, costs, and ramp curves — not hard-coded in Python.
- **N+1 optimization**: Each initiative is evaluated by running the full simulation with and without it, producing honest marginal-impact rankings (not additive approximations).
- **Portfolio-level pattern recognition**: If 6 of 8 deals running the same initiative are lagging, the problem is the playbook, not the deal — `initiative_rollup.py` surfaces this.
