# regulatory/

Federal Register / CMS rule monitoring layer. Used by `diligence/regulatory_calendar/` to keep the curated event library current.

| File | Purpose |
|------|---------|
| `corpus.py` | Loads the regulatory document corpus from cached Federal Register dockets |
| `discovery.py` | Watches for newly-published rules that might affect existing thesis drivers |
| `score.py` | Scores rule relevance to a target's specialty / payer mix / geography |
| `tfidf.py` | Pure-numpy TF-IDF for matching new rules against existing thesis-driver descriptions |
| `topics.py` | Topic taxonomy: site-neutral, MA coding, IDR recalculation, HSR, CPOM, etc. |

## Refresh cadence

The curated event library at `diligence/regulatory_calendar/` is hand-tuned. This module is the **discovery layer** that surfaces candidate events for the next manual update — it does not auto-promote rules to the kill-switch library without human review.

For the active thesis-kill-switch UI, see [diligence/regulatory_calendar/](../diligence/regulatory_calendar/).
