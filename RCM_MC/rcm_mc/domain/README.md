# Domain

Healthcare revenue-cycle domain modeling: the economic ontology and custom metric registry. Provides the single source of truth for metric classification, causal relationships, and financial pathway mappings used across all downstream models.

| File | Purpose |
|------|---------|
| `econ_ontology.py` | Maps every platform metric to its revenue-cycle slot, P&L pathway, causal parents/children, and reimbursement sensitivity; the single source of truth for metric semantics |
| `custom_metrics.py` | User-defined custom KPI registration with metadata (unit, directionality, valid range) that extends the standard metric registry without shadowing it |

## Key Concepts

- **Explicit mappings over inference**: Every metric's classification is a hand-written dict entry defensible in IC, not auto-learned.
- **Single source of truth**: Any code that needs to know "is `denial_rate` lower-is-better?" or "does this metric move revenue or cost?" consults `econ_ontology`.
