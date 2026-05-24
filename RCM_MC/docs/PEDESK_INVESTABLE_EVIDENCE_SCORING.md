# PEdesk investable-evidence scoring v1

_Phase 4 of the Guide-coverage loop. Implemented in
[`rcm_mc/data/investable_evidence.py`](../rcm_mc/data/investable_evidence.py);
tests in `tests/test_investable_evidence.py`. Builds on the cross-sector
framework ([`PEDESK_CROSS_SECTOR_BENCHMARK.md`](PEDESK_CROSS_SECTOR_BENCHMARK.md))._

## What it is

A **transparent, peer-relative evidence layer** for a single provider — the
opposite of a black-box score. It never produces an investment
recommendation; it shows the components and lets the analyst judge.

```python
from rcm_mc.data.investable_evidence import evidence_profile
ep = evidence_profile("nursing-homes", "676118")   # -> EvidenceProfile | None
```

## What an `EvidenceProfile` exposes

- **components** — each higher-is-better public quality metric, with:
  `raw_value`, `peer_percentile` (same-state rated peers), guarded `z_score`,
  `weight`, and a `note` (e.g. why it was suppressed).
- **evidence_index** — the mean of the *available* component percentiles
  (equal weights by default; every weight exposed). `None` when nothing is
  rated. Bounded 0–100.
- **risk_flags** — enforcement/staffing/ownership signals surfaced
  **separately** and never folded into the index. SNF (where the data
  exists): Special Focus Facility, abuse icon, ownership change <12mo, low
  staffing rating, enforcement penalties.
- **formula**, **weights_note**, **peer_set_label**, **sample_size**,
  **missingness**, **caveats**.

## Allowed inputs (only these)

- peer percentile (same-state peers)
- z-score **only when n ≥ 5 and sd > 0** (else suppressed)
- HHI / concentration proxy (via the cross-sector layer)
- quality distributions
- enforcement / staffing / ownership flags **where the data exists** (SNF)
- missingness / caveat flags

## Not allowed (asserted in tests)

- claiming an investment recommendation
- claiming commercial revenue
- claiming true market share
- claiming causal impact
- hiding raw components behind a single number

## Why a separate "risk flags" channel

Folding enforcement flags into one score would hide them. Flags (SFF, abuse
icon, penalties, low staffing, recent ownership change) are reported on their
own so a single bad signal is never averaged away — the analyst sees both the
peer-relative quality picture and the discrete red flags.

## Direction discipline

Only higher-is-better quality metrics enter the index. Lower-is-better outcome
rates (dialysis mortality/hospitalization/readmission/transfusion; IRF/LTCH
readmission & Medicare-spending-per-beneficiary) are excluded so a "higher =
better" read holds. They remain visible on each vertical's own page.

## Not yet built (honest)

- A UI surface rendering the evidence profile on each provider page
  (a `ui/` follow-up, not a scoring calc).
- Any *predictive* model — that waits on the Phase 5 label-readiness audit
  ([`PEDESK_PREDICTION_READINESS.md`](PEDESK_PREDICTION_READINESS.md)); this
  layer is descriptive peer evidence only, not a forecast.
