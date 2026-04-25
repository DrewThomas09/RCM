# esg/

ESG-disclosure surfaces for fund-level reporting. Becoming required by major LPs (ILPA Diversity Metrics, EDCI, ISSB).

| File | Purpose |
|------|---------|
| `carbon.py` | Per-portco carbon-footprint estimate (Scope 1 + 2; Scope 3 stubbed) |
| `dei.py` | Diversity-equity-inclusion metrics (board, exec, workforce) per ILPA template |
| `governance.py` | Governance score — board independence, audit committee composition, related-party transactions |
| `disclosure.py` | Top-level ESG disclosure rendering for the LP report |
| `edci.py` | EDCI (ESG Data Convergence Initiative) metric calculator |
| `issb.py` | ISSB-IFRS-S2 climate-disclosure reporter |

## Why this lives in the platform

LPs are starting to require these metrics as part of the quarterly LP package. Calculating them deal-by-deal at year-end is a fire drill; rolling them into the platform's normal data flow makes them ambient.
