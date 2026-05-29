# Scenarios & Stress Engine — Partner-Facing Detail

How `/scenarios/design`, `/scenario-modeler`, and the underlying
`rcm_mc.scenarios.*` modules apply named shocks to a deal so the Guide
can answer "what happens if X", "how do I run a scenario", and "what's the
output of a stress test".

(See also `scenario_engine.md` for the architectural overview.)

## The two surfaces

- **`/scenarios/design`** — partner-facing scenario builder. Pick a
  preset shock library (Rate cut · Volume drop · Payer walkout · Cost
  pressure · Single-major customer loss) or compose a custom shock.
- **`/scenario-modeler`** — runs the designed scenario against a target
  deal and produces the EBITDA / IRR / MOIC / covenant impact.

## The shock vocabulary

PEdesk's scenario engine speaks in **levered shocks** applied to either
revenue or cost components:

### Revenue shocks
- **Payer rate cut** — % cut to a named payer's rates. Compounds with
  volume.
- **Payer walkout** — total loss of a named payer's contracts (set the
  payer share to 0).
- **Volume drop** — % drop in patient volume (encounter, admit, or
  case-day depending on sector).
- **MA shift** — % of commercial lives moves to MA (changes per-life
  economics).
- **Major customer loss** — concentration impact (e.g. lose the largest
  hospital client for a staffing firm).

### Cost shocks
- **Labor inflation** — % wage uplift, applied to labor-cost lines.
- **Supply inflation** — % uplift on supply / pharmacy costs.
- **Real-estate uplift** — % rent increase on lease renewal.
- **Compliance cost** — fixed-$ add to G&A.

### Combined shocks
- **Recession scenario** — bundled: volume drop + commercial mix shift
  + bad-debt uplift.
- **Reimbursement headwind** — bundled: rate cuts across multiple
  payers + MA shift.

## How the engine applies them

For each shocked deal:

1. Take the base case (revenue / cost / EBITDA) from the deal's analysis
   packet.
2. Apply each shock to its component line item; recompute total revenue
   and total cost.
3. Recompute EBITDA = revenue - cost, keeping fixed-cost ratios and
   variable-cost ratios from the base packet.
4. Push the shocked EBITDA through the deal's PE math: leverage, debt
   service, covenant ratios, equity returns.
5. Output the scenario delta from the base case.

The combination logic is **multiplicative on percentages, additive on
fixed-dollar shocks**. Two 5% revenue cuts to two different payers do
NOT equal a 10% revenue cut to one payer — they multiply through their
respective payer-share weights.

Exact implementation lives in `rcm_mc.scenarios.scenario_engine` and
`rcm_mc.scenarios.scenario_overlay`.

## Outputs

Per scenario the engine produces:
- **EBITDA delta** ($ and %).
- **MOIC delta** vs base case at planned exit year.
- **IRR delta** vs base case.
- **Covenant impact** — the binding covenant's new headroom %, plus a
  band (PASS / CAUTION / WARNING / FAIL).
- **Verdict** — PASS if all covenants stay above 15% headroom and IRR
  stays above hurdle; otherwise CAUTION/WARN/FAIL based on severity.

When multiple scenarios are run together, the engine produces a
waterfall: base → scenario 1 → scenario 2 → joint → terminal.

## Common partner questions

- *"What if commercial rates cut 5%?"* — Apply rate-cut shock to the
  commercial payer share; report EBITDA delta.
- *"What's the worst-case covenant headroom?"* — Apply the
  recession-scenario bundle; report binding-covenant headroom.
- *"Can the deal absorb the largest payer walking?"* — Apply payer-
  walkout for the largest commercial; report verdict.
- *"How do shocks compound?"* — Explain multiplicative-on-%-shares.

## Interpretation guidance

- Shocks are **deterministic** — treats the % as certain, not as one of
  many. For probability-weighted outcomes, partners should run a Monte
  Carlo via `/diligence/deal-mc` (see `monte_carlo_simulation.md`).
- Variable-cost ratios from the base packet may not hold at extreme
  shocks — the engine flags scenarios that push EBITDA below 60% of
  base as "outside-validation" range.
- Bundled scenarios are illustrative; partner judgment is needed to
  decide whether combining individual shocks reflects a credible joint
  state of the world.
- Covenant outcomes use the deal's actual covenant terms (from the
  credit agreement); a missing covenant schedule renders "covenant
  data not loaded" rather than a fake number.

## What it is NOT

- Not a probabilistic forecast — that's Monte Carlo's job
  (`/diligence/deal-mc`).
- Not an optimisation surface — won't tell you the optimal sponsor
  response to a shock.
- Not a market-shock model — assumes the deal's own economics are
  shocked, not the entire market simultaneously.

## Related surfaces

- `/scenarios/design` — preset scenario library.
- `/scenario-modeler` — apply to a specific deal.
- `/diligence/deal-mc` — Monte Carlo (probabilistic version).
- `/diligence/payer-stress` — pre-built payer-mix sensitivity.
- `/diligence/covenant-stress` — pre-built covenant-headroom sensitivity.
- `/bear-cases` — narrative bear-case library.
- `/methodology` — full documentation of the shock vocabulary and
  combination logic.
