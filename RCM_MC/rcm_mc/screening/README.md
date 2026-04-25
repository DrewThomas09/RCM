# screening/

Bloomberg-style deal-screening dashboard at `/screening/dashboard`. Filters the hospital universe down to a workable shortlist before deep diligence runs.

| File | Purpose |
|------|---------|
| `dashboard.py` | Server-rendered screening dashboard — sortable / filterable / exportable list, density chips for "deals like this" |
| `filter.py` | `DealFilter` dataclass + composable predicates (state, beds, payer mix, margin, occupancy, etc.) |
| `predict.py` | Lightweight predictors used at screening — investability score, distress probability, denial-rate gap |

## Workflow

1. Analyst lands at `/screening/dashboard`
2. Applies filters (state / size / payer mix / quality)
3. Sorts by an investability or improvement-potential dimension
4. Drills into a candidate → Deal Profile v2 at `/deal/<id>`
5. From there, the `thesis_pipeline` orchestrator runs the 19-step deep diligence

The screening filter surface is intentionally lighter than the diligence surface — analysts are filtering thousands of hospitals, so per-candidate cost must stay under a few milliseconds.
