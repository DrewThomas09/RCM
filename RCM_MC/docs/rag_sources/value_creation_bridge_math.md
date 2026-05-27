# Value-Creation & EBITDA Bridge Math

How PEdesk turns operating improvements into EBITDA and then into returns
(MOIC/IRR). Explains the backend so the Guide can answer "how is the bridge
built / how is MOIC computed / why this IRR".

## The EBITDA bridge (7 levers)
Starting (current) EBITDA + the sum of per-lever EBITDA contributions =
pro-forma EBITDA. Each lever's contribution is estimated as the gap between
the target's current KPI and a peer/benchmark target, multiplied by the
revenue or cost at risk for that lever (e.g. denial-rate gap × revenue exposed
to denials). Levers span revenue capture, cost, and working capital.
- Modules: `rcm_mc/pe/rcm_ebitda_bridge.py` (the 7-lever bridge),
  `rcm_mc/pe/pe_math.py` (returns math).

## Returns math
- Exit enterprise value = exit EBITDA × exit multiple.
- Equity proceeds = exit EV − net debt at exit.
- MOIC = equity proceeds / entry equity.
- IRR = the annualized rate r solving Σ cash_flow_t / (1+r)^t = 0 over the hold.
- Covenant headroom / leverage are tracked alongside (see the covenant_cushion
  and leverage metrics).

## How to read it
- Lever contributions are ASSUMPTIONS (benchmark gaps × exposure), not realized
  EBITDA — read the assumptions before quoting a number.
- Returns are dominated by entry/exit multiple and leverage; a small exit-
  multiple change moves MOIC/IRR a lot. Prefer flat-to-down exit assumptions.

## Caveats
- The bridge is a model of a value-creation plan, not a guarantee; discount for
  execution risk. Overlapping levers must be additive, not double-counted.
- Per-deal output over that deal's inputs — not an audited financial statement.
