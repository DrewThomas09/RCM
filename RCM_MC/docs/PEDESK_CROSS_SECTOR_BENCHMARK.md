# PEdesk cross-sector benchmark framework

_Phase 3 of the Guide-coverage loop. Implemented in
[`rcm_mc/data/cross_sector.py`](../rcm_mc/data/cross_sector.py); tests in
`tests/test_cross_sector_benchmark.py`._

## What it is

A normalization + computation layer that reads all **six live CMS verticals**
— Home Health, Hospice, SNF / Nursing Home, Dialysis, IRF, LTCH — through one
interface, so a single state can be benchmarked across every sector at once.
It is the data layer behind the north-star question:

> "Show me the best SNF, hospice, dialysis, and home-health operators in Texas
> by quality percentile, ownership profile, and local competition."

## Interface

```python
from rcm_mc.data.cross_sector import (
    SECTORS, sector_state_benchmark, cross_sector_state_summary)

cross_sector_state_summary("TX")          # -> [SectorStateBenchmark, ...] (6)
sector_state_benchmark("dialysis", "TX")  # -> SectorStateBenchmark | None
```

Each `SectorSpec` maps a vertical's loader, name/locality attributes, and its
**higher-is-better headline metric** (Home Health star rating, Hospice Care
Index, SNF overall stars, Dialysis 5-star, IRF/LTCH discharge-to-community).

## Each `SectorStateBenchmark` carries

| Field | Meaning |
|---|---|
| `provider_count` | providers in the state |
| `locality_count` | distinct localities (county; city for Home Health) |
| `rated_count` / `sample_size` | providers with a headline value |
| `missingness_pct` | share of providers missing the headline value |
| `headline_median` / `national_median` | state vs national median headline |
| `state_percentile` | rank of the state median among all states (0–100) |
| `quartiles` | state-level min / q1 / median / q3 / max |
| `ownership_mix` | `[(label, count)]` descending |
| `ownership_hhi` / `locality_hhi` | concentration **composition proxy** (0–10000) |
| `caveats` | sample-size, missingness, concentration, and the standing honesty caveat |

## Honesty rules (enforced in code + tests)

- **No synthetic data, no network** — counts/means/quartiles/percentile ranks
  over the vendored public CMS files only.
- **Concentration is a composition proxy, NOT market share** — HHI is computed
  over provider-**count** shares because CMS public data has no true
  volume/revenue/patient denominator. Labeled as such everywhere.
- **Percentile is peer deviation, never a recommendation or a causal claim.**
- **Sample size and missingness are always exposed**; percentile/median below
  `n=5` raise an explicit "unreliable at this sample size" caveat.
- **Lower-is-better metrics are excluded** from the cross-sector headline
  (they stay on their own vertical pages) so a "higher percentile = better"
  read holds across sectors.
- **No `$` figures** — none exist in these files.

## Layering

The module lives in `data/` and only calls other `data/` loaders. It never
imports `ui/` (which sits above it), so any future UI — a cross-sector "state
scorecard" page is the natural next surface — can render from it.

## Not yet built (honest)

- A UI page rendering the cross-sector scorecard (a `ui/` surface over this
  layer) — deliberately a follow-up; it is a new page, not a benchmark calc.
- Cross-sector roll-ups that would require a shared denominator (true market
  share, $ TAM) — **cannot** be built honestly from CMS public data.
