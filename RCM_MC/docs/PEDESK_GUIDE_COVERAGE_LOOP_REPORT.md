# PEdesk Guide-coverage loop — final report

_Generated 2026-05-24. The loop that followed the six-vertical CMS loop,
refocused on the biggest product gap: **Guide/AI depth across the product**,
plus the cross-sector + investable-evidence + prediction-readiness layers._

## Mission

The prior loop shipped six CMS verticals but Guide coverage was only **87 of
320 routes**, and almost none were investment-grade. This loop's priority was
to **make the Guide work deeply** — starting with the live sectors — and to
build the analytic spine (cross-sector benchmarking, transparent evidence
scoring) and honestly audit prediction-readiness. No new verticals.

## Coverage: before → after

Classification by **context depth** (not the old binary curated/fallback):
*strong* = ≥8 suggested questions + interpretation guidance + limitations +
data sources; *partial* = curated but thin; *missing* = safe generic fallback.

| Bucket | Loop start | Loop end |
|---|---|---|
| **strong** | 4 | **17** |
| partial | 83 | 70 |
| missing | 233 | 233 |
| curated (strong+partial) | 87 | 87 |
| total page routes | 320 | 320 |

**Strong coverage more than quadrupled (4 → 17.)** Curated *count* held at 87
— this loop deepened existing contexts to investment-grade rather than adding
net-new curated routes; converting the 233 fallback routes is the next lever
(see "Recommended next PR").

## What shipped (all merged + deployed green)

| PR | main SHA | What |
|---|---|---|
| #617 | (docs) | Coverage audit v2 — strong/partial/missing classification |
| #618 | `a474f902` | Six live CMS verticals + Sector hub → strong; **fixed the stale Sector Intelligence map** (it tagged SNF/Dialysis as roadmap and omitted IRF/LTCH); retired an obsolete guard test |
| #619 | `2f365f39` | **Cross-sector benchmark framework** over all six verticals |
| #620 | `24e9cc66` | **Investable-evidence scoring v1** (transparent, peer-relative) |
| #621 | `f29706b7` | **Prediction-readiness audit** (labels per vertical) |
| #622 | `a7604443` | 10 core data/market/portfolio pages → strong (strong 7 → 17) |

## Contexts added / deepened (→ strong)

- **Verticals:** Home Health, Hospice (4→9 each), Sector Intelligence (3→9).
  SNF, Dialysis, IRF, LTCH were already strong.
- **Core pages:** /cms-sources, /cms-data-browser, /data/catalog,
  /benchmarks, /concentration-risk, /competitive-intel, /lp-dashboard,
  /market-rates, /portfolio, /pipeline.

## New analytic spine

- **Cross-sector benchmark framework** (`data/cross_sector.py`): one
  interface over all six verticals → per-state provider/locality counts,
  quality median + state percentile, ownership mix + HHI (composition proxy,
  not market share), locality concentration, **sample size + missingness**,
  and caveats. The data layer behind "best operators in <state> across
  sectors." 10 tests.
- **Investable-evidence scoring v1** (`data/investable_evidence.py`): a
  transparent, peer-relative `EvidenceProfile` — every component's raw value,
  peer percentile, guarded z-score (n≥5, sd>0), and weight exposed; a clearly-
  labelled evidence index (mean of available percentiles); SNF enforcement/
  staffing/ownership **risk flags surfaced separately, never folded in**. 9
  tests. Explicitly **not** a recommendation, revenue, market-share, or
  causal claim.

## RAG

RAG corpus **202 → 204** auto-derived Guide documents (the cross-sector +
investable-evidence framework docs are now indexed).

## Prediction-readiness (honest verdict)

**Panel-data-blocked.** Every vertical is a single dated snapshot, so
change/decline/closure/growth labels can't be built and SNF event flags are
concurrent (leak risk), not forward outcomes. The gating next step is
**snapshot retention** (a longitudinal spine), not model code. Full label
matrix + sourcing plan in `PEDESK_PREDICTION_READINESS.md`. The
investable-evidence layer is the correct, descriptive (non-forecast) ceiling
for today's data.

## Tests / deploys

- New tests this loop: `test_cross_sector_benchmark.py` (10),
  `test_investable_evidence.py` (9), plus updated sector + SNF-spine guards.
- Every code PR confirmed: CI test jobs green on 3.11 / 3.12 / 3.14, merged,
  deployed, `/healthz` 200. (Note: CI runs a ~175-test go-live subset; the new
  suites were validated locally before each merge.)

## Remaining uncovered routes

**233 routes still resolve to the safe fallback** (every page still answers
the Guide — just generically) and **70 remain partial**. The bulk are
low-traffic utility and diligence-subpage routes (`/diligence/*`,
`/portfolio/*`, admin/util pages).

## Recommended next PR

**Batch-upgrade the remaining partial pages (70) to strong, then begin
converting the highest-traffic *missing* routes to curated** — prioritizing
the `/diligence/*` family (deal-level analytic surfaces) and the
`/portfolio/*` family. In parallel, the highest-leverage data step is
**snapshot retention** to unlock the prediction labels. The natural new
product surface is a **cross-sector "state scorecard" UI** over
`data/cross_sector.py` — the north-star "best operators in Texas across
sectors" view (a `ui/` page, flagged for review since it's a new surface, not
a benchmark calc).
