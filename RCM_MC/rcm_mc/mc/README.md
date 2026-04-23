# MC (Monte Carlo)

Monte Carlo simulation orchestration: deal-level and portfolio-level MC runs, convergence checking, scenario comparison, and result persistence. Builds on top of `core/simulator.py` to add prediction uncertainty, execution uncertainty, and cross-deal correlation.

---

## `ebitda_mc.py` — Two-Source Monte Carlo

**What it does:** The primary deal-level Monte Carlo simulator. Composes two independent uncertainty sources — prediction uncertainty and execution uncertainty — over the RCM EBITDA bridge to produce a full MOIC/IRR distribution.

**How it works:** For each of N draws (default 2,000): (1) **Prediction draw** — samples a "where will the target actually land" value from `Normal(target, σ_conformal)`, where σ is derived from the ridge predictor's conformal CI bounds treated as 5th/95th percentiles; (2) **Execution draw** — samples an achievement fraction from `Beta(α, β)` calibrated per lever family (denial management: Beta(7,3) → E[e]=0.70; AR/collections: Beta(8,2) → E[e]=0.80; CDI: Beta(6,4) → E[e]=0.60; payer renegotiation: Beta(5,5) → E[e]=0.50); (3) computes `final_value = current + (prediction_draw - current) × execution_draw`; (4) runs the v1 bridge with those final values to get EBITDA_i; (5) computes MOIC_i and IRR_i using `pe/pe_math.py`. Aggregates to `MonteCarloResult` with P5–P95 percentiles, probability of covenant breach, probability of each MOIC target, and a variance decomposition (correlation-squared, sums to 1.0). The vectorized NumPy path runs 100,000 draws in under a second.

**Data in:** `DealAnalysisPacket` metric profile with conformal CIs from `ml/ridge_predictor.py`; bridge coefficients from `pe/rcm_ebitda_bridge.py`; PE math from `pe/pe_math.py`; RNG child streams from `core/rng.py`.

**Data out:** `MonteCarloResult` written into `DealAnalysisPacket.simulation`.

---

## `v2_monte_carlo.py` — v2 Unit-Economics Monte Carlo

**What it does:** Monte Carlo over the v2 value bridge. Adds four dimensions the v1 MC doesn't model: collection realization rate, denial overturn rate, per-payer revenue leverage, and exit multiple uncertainty.

**How it works:** Builds on the same two-source structure as `ebitda_mc.py` but feeds draws through `pe/value_bridge_v2.py` instead of the v1 bridge. Additionally samples: `collection_realization ~ Beta(8,2)` (how much of the AR improvement translates to cash), `denial_overturn_rate ~ Beta(5,3)` (appeal success rate), `exit_multiple ~ Normal(base_multiple, 0.5)` (market timing risk). Carries four distinct output distributions: recurring EBITDA delta, one-time WC cash, EV from recurring only, total cash to equity. Enforces the invariant that WC cash is never multiplied into EV.

**Data in:** `DealAnalysisPacket` with reimbursement profile from `finance/reimbursement_engine.py`; v2 bridge from `pe/value_bridge_v2.py`; RNG streams from `core/rng.py`.

**Data out:** `V2MonteCarloResult` with four distribution summaries; written into the packet when the v2 path is enabled.

---

## `portfolio_monte_carlo.py` — Correlated Cross-Deal Monte Carlo

**What it does:** Runs Monte Carlo across all portfolio deals simultaneously, modeling cross-deal execution correlation and diversification benefit. Produces fund-level MOIC and IRR distributions that account for systematic risk.

**How it works:** Builds a correlation matrix across deals using deal-family groupings (hospital acute, behavioral health, etc.) with a default within-family execution correlation of 0.3. Uses Cholesky decomposition to generate correlated execution uncertainty draws. Runs each deal's bridge with its correlated execution factor. Aggregates to fund-level MOIC via the portfolio's invested capital weights. Runs tail-risk scenarios (simultaneous 30th-percentile execution across all deals).

**Data in:** All active portfolio deals' `DealAnalysisPacket` MC configs; invested capital per deal from `portfolio/store.py`; deal-family groupings from `domain/econ_ontology.py`.

**Data out:** `PortfolioMCResult` with fund-level distribution, diversification benefit, and tail-risk scenario results.

---

## `scenario_comparison.py` — Side-by-Side Scenario Comparator

**What it does:** Runs MC under multiple named scenarios (base / management / upside / downside) and compares them side-by-side. Computes pairwise win probabilities and selects a recommended scenario.

**How it works:** Accepts a list of `(scenario_name, mc_config)` pairs. Runs `ebitda_mc.py` for each. Computes `P(A beats B)` for each pair from the joint distribution (fraction of draws where A_MOIC > B_MOIC). Selects the recommended scenario using `mean_MOIC − risk_aversion × downside_σ` (default risk_aversion=0.5). Returns a `ScenarioComparison` with all distributions, pairwise matrices, and the recommended scenario name with rationale.

**Data in:** Multiple `DealAnalysisPacket` variants (one per scenario) from `scenarios/scenario_builder.py`.

**Data out:** `ScenarioComparison` rendered on the workbench Scenarios tab.

---

## `convergence.py` — Monte Carlo Convergence Checker

**What it does:** Verifies that the MC simulation has run enough draws for the P50 MOIC to be stable. Flags results as untrustworthy if the running P50 hasn't converged within tolerance.

**How it works:** Computes the running P50 MOIC after each batch of 100 draws. Checks that the absolute change in running P50 over the final 500 draws is below the tolerance threshold (default 0.01x). Returns a `ConvergenceReport` with `converged: bool`, the number of draws needed, and the final P50 stability band. The `MonteCarloResult` carries this report; the UI displays a warning badge when `converged=False`.

**Data in:** Array of per-draw MOIC values from `ebitda_mc.py`.

**Data out:** `ConvergenceReport` embedded in `MonteCarloResult`.

---

## `mc_store.py` — Monte Carlo Run Persistence

**What it does:** Append-only SQLite storage for MC run results. Provides a history of simulation outputs so partners can track how the distribution has evolved as new data arrived.

**How it works:** Stores `MonteCarloResult` JSON blobs in the `mc_runs` table keyed by `(deal_id, run_id, scenario_id, built_at)`. Never overwrites. `latest_run(deal_id)` returns the most recent result. `run_history(deal_id)` returns all runs sorted by build time for the diff view. Gzip-compresses blobs before storage.

**Data in:** `MonteCarloResult` objects from `ebitda_mc.py` or `v2_monte_carlo.py`.

**Data out:** Historical MC run blobs for the `/api/analysis/<id>/mc/history` endpoint.

---

## Key Concepts

- **Two uncertainty sources**: Prediction uncertainty (where is the target?) and execution uncertainty (will the team hit it?) are sampled independently and composed — not added. This preserves the full joint distribution.
- **Portfolio correlation**: Cross-deal execution correlation (default 0.3 within-family) captures systematic risk that per-deal MC misses. A bad macro environment hurts all denial-management initiatives simultaneously.
- **Convergence gating**: Results flagged as untrustworthy if running P50 hasn't stabilized within tolerance. Prevents partners from making decisions on noisy results.
- **Zero-variance identity lock**: When all uncertainty parameters collapse to their means, P50 MC exactly reproduces the deterministic bridge — tested as a regression invariant.
