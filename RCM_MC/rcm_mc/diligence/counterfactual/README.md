# counterfactual/

**"What would change your mind?" advisor.** Given a current RED/CRITICAL finding, back-solves the minimum input change that flips the severity band.

## Design principle

**No fabrication.** Counterfactual answers are symbolic inverses against the threshold YAMLs already in the platform. If `covenant_stress` flags FAIL at 55% breach probability with threshold 50%, the counterfactual answers: "minimum EBITDA growth needed to bring breach probability to 49%." It solves for the input, it doesn't invent a new model.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring — "what would change your mind" engine. |
| `advisor.py` | **One counterfactual solver per risk module.** Symbolic inverse: current finding + threshold → minimum input delta that flips band. |
| `ccd_runner.py` | **CCD-driven runner.** Given a `CanonicalClaimsDataset`, extracts each solver's required inputs and returns a `CounterfactualSet`. Ties the advisor to the rest of the platform. |
| `bridge_integration.py` | **Feeds counterfactual savings into the v2 EBITDA bridge** as a new "reg-risk mitigated" lever. Doesn't touch bridge code — wraps output as another lever. |

## Partner use case

IC partner: "I don't believe the $17M EBITDA drag from regulatory risk. Show me why it isn't $5M."

Counterfactual solver: "To reach $5M drag instead of $17M, your thesis would need one of:
- Medicare share below 35% (currently 45%) — 10pp mix shift
- OR HOPD revenue below $30M annually (currently $45M) — $15M revenue reallocation
- OR the site-neutral CY2027 final rule delayed 12+ months (currently effective 2026-10-01)"

Partner now has a concrete set of "if these things happen, the deal works" assumptions to defend at IC. Stated explicitly, they're either defensible or they aren't.

## Where it plugs in

- **Bear Case** — counterfactual answers appear as "what would change your mind" attached to each CRITICAL finding
- **IC Packet** — counterfactual set auto-injects into the sensitivity section
- **Deal MC** — reg-risk-mitigated lever feeds back into the EBITDA bridge

## Tests

`tests/test_counterfactual*.py` — solver correctness per module + `CounterfactualSet` composition.
