# negotiation/

Deal-pricing negotiation support. Models bargaining range, outside options, and counter-offer math under uncertainty.

| File | Purpose |
|------|---------|
| `bargaining.py` | Nash bargaining and Rubinstein alternating-offer models for the price-discovery range |
| `distributions.py` | Counterparty-side reservation-price distributions (sponsor, strategic, hold-as-is) |
| `outside_options.py` | What's our BATNA? What's theirs? Walk-away points for each side |
| `counterfactual.py` | "If we offer $X with structure Y, what's the probability of acceptance + revised IRR?" |

## Output

A `NegotiationPlan` with:
- Recommended opening bid + reservation price
- Top-3 deal-shape variants (cash / earn-out / rollover) ranked by probability-weighted IRR
- The specific concessions to give last (high signal value, low IRR cost)

Used by the workbench Negotiation tab and the `bridge_audit/` module's counter-bid math.
