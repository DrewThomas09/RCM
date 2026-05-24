# RAG source — Provider X-Ray benchmarking: peer sets, percentiles, z-scores

X-Ray's benchmarks **reuse** the cross-sector framework (peer counts,
ownership/locality HHI, state percentile) and the investable-evidence layer
(per-metric percentile, guarded z-score, the transparent evidence index). No
new math is introduced.

**Peer sets.** The default peer set is **same-state, same-vertical rated
providers**. Locality (county; city for Home Health) narrows it further when
available. Ownership and size peer sets are used only when the field exists
and the sample is adequate.

**Percentile** is a provider's mid-rank position within its peer set, 0–100,
on a **higher-is-better** metric. It is **peer deviation, not a verdict** and
never an investment recommendation. Lower-is-better outcome rates (dialysis
mortality; IRF/LTCH readmission & Medicare-spend) are shown raw but excluded
from the higher=better index so the read stays directionally honest.

**z-score** `z = (x − mean(peers)) / sd(peers)` is computed **only when
n ≥ 5 and sd > 0**; otherwise it is suppressed ("insufficient peer sample").

**Quartiles** are used only when the peer set has n ≥ 5.

**Concentration (HHI)** `Σ shareₖ²` is computed over provider-**count** shares
(ownership type or locality). It is a **composition proxy, NOT market share** —
CMS public data has no true volume/revenue/patient denominator.

**Missingness** `missing_n / total_peer_n` is always surfaced; a high rate
raises a caveat so a median isn't over-read.

**The evidence index** is the mean of the *available* component percentiles
with equal, exposed weights — a peer-relative quality summary, never a
black-box score, with every component visible.
