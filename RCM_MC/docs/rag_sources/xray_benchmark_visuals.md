# RAG source — X-Ray benchmark visuals (peer band, percentiles, z-scores)

Shared across HCRIS X-Ray and CMS Provider X-Ray (the `xray_kit` primitives).

**Peer band (box-plot).** A horizontal box from **P25 to P75** (the peer
interquartile range), a **median** tick, and a **target diamond** placed on the
axis. The diamond is colored by state: green when the target beats peers, red
when it lags, paper/ink when it sits inside the band. Reading it: diamond
*inside* the box = unremarkable; *outside* = an outlier worth diligence. The
band shows spread, not a pass/fail line.

**P25 / median / P75.** The 25th / 50th / 75th percentiles of the **peer
distribution** — they describe the peers, not the target. "Above P75" means
better than three-quarters of peers (on a higher-is-better metric); always read
with the metric's direction.

**Percentile (CMS Provider X-Ray).** A provider's mid-rank position within a
peer set, 0–100, higher = better. The CMS X-Ray shows it across **four peer
sets** — national, state, locality, ownership — each with its peer count, and
**`n/a` when fewer than 5 rated peers** (suppressed, never invented).

**z-score.** `z = (value − mean(peers)) / sd(peers)`, computed **only when
n ≥ 5 and sd > 0**. |z| ≥ 2 ≈ a ~2-sd outlier. Suppressed otherwise.

**Concentration (HHI).** `Σ shareₖ²` over provider-**count** shares — a
*composition* proxy, **not market share** (CMS public data has no
volume/revenue denominator).

**Honesty rules baked into the visuals.** The peer band renders an explicit
empty/dashed state when values can't be placed (no fabricated geometry); the
target diamond clamps to the axis; percentiles/z-scores suppress below n=5; and
every figure is peer deviation — never a forecast, causal claim, or
recommendation.
