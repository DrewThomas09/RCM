# Target Screener Workbench — component map & build plan

Turns `/target-screener` from a 3-mode router page into the real **Source
workflow**: a unified, PEdesk-native screening workbench across every real
CMS/provider universe we have onboarded.

```
Source → Target Screener → evaluate target → compare → just-missed scan
        → save screen → open profile / X-Ray → promote to Pipeline
```

## Handoff → PEdesk mapping

Source: `~/Downloads/workbench-full.html` — a **shell** that iframes six
screen files (not provided). It defines *structure + visual intent only*; the
screen bodies are recreated PEdesk-native. We take the structure, **not** the
delivery mechanism.

Explicitly rejected from the prototype:
- ❌ iframes / runtime HTML (`<iframe class="opt" src="screen-*.html">`)
- ❌ external Google Fonts / CDNs (`fonts.googleapis.com`, `Public Sans`)
- ❌ square-tile cartogram maps

Recreated with: `chartis_shell`, Chartis tokens/fonts (Source Serif 4 / Inter
Tight / JetBrains Mono already loaded by the shell), `ck_*` primitives, and the
real SVG US map (`render_us_geo_map`). Server-rendered first; `view=` query
param owns screen state; client JS only enhances.

### Six screens → `view=` states

| # | Prototype tab | `view=` | PEdesk realization |
|---|---|---|---|
| 01 | Main | `main` (default) | source/purpose header · vertical selector · real US map · filter panel · KPI strip · ranked provider table · source chips · active-filter chips · Guide · row actions (profile / X-Ray / compare / save) |
| 02 | Inspector | `inspector` | detail drawer for `?ccn=` — identity, source/status chips, key metrics, market + peer context, caveats, links (profile, HCRIS/CMS X-Ray, market profile), Guide suggested questions |
| 03 | Columns | `columns` | column picker + metric dictionary, grouped by category; per-metric source + availability count; visibility via query param |
| 04 | Compare | `compare` | compare basket from `?compare=ccn1,ccn2,…`; metric-by-metric; same-vertical full, cross-vertical shared-only ("not comparable" otherwise); source/status chips |
| 05 | Just missed | `missed` | threshold miss-distance scan — providers/markets that failed by 1–2 criteria; shows which + how far; "relax this filter to include N"; "data missing, not failed" |
| 06 | Saved screens | `saved` | shareable URL/query-param screens; honest "persistence not wired yet" state unless real storage exists |

Tab chrome: two groups — **Workbench states** (01–03) and **Linked screens**
(04–06) — italic serif numerals, italic-emphasis titles, mono sub-labels,
green-deep active underline, keyboard 1–6. All server-rendered links carrying
`view=`.

## Verticals → real loaders (the screening universe)

Each is a separate mode. **All real CMS public data.** Consistent loader
shape: `load_<vertical>_providers() -> Dict[ccn, Provider]` +
`load_<vertical>_quality() -> Dict[ccn, Dict[str, float|None]]`. Provider
dataclasses share: `ccn, name, address, city, state, (county), zip, ownership,
source, source_date`.

| Vertical | Loader module | Provider key fields | Quality/extra |
|---|---|---|---|
| Hospitals / HCRIS | `data/hcris.py`, `data/cms_hcris.py` | beds, NPR, margin, payer-day % | HCRIS financials, distress model, clusters |
| Home Health | `data/home_health.py` | ownership, cert date | `home_health_quality`, CAHPS |
| Hospice | `data/hospice.py` | county, ownership | `hospice_quality`, CAHPS |
| SNF / Nursing | `data/snf.py` (+ `snf_chow.py`) | certified_beds, avg_residents, provider_type, **sff_status** | `snf_quality`, CHOW/consolidation |
| Dialysis | `data/dialysis.py` | stations, **chain_owned/chain_org**, modalities | `dialysis_quality`, CAHPS |
| IRF | `data/irf.py` | county, ownership | `irf_quality` |
| LTCH | `data/ltch.py` | county, ownership | `ltch_quality` |
| Provider supply | `data/provider_supply.py` | NPPES/market supply (if onboarded) | density/gap |
| Market-only (county/state) | geo-intel `_METRICS`/`_raw` | demographics, MA, SDOH, shortage | all real public |

**Excluded as a target universe:** the historical deal corpus. It may appear
ONLY when explicitly labeled **BENCHMARK CORPUS / RESEARCH REFERENCE**, never
as an active target. The current `_load_corpus` screeners (sourcing/hospital/
predictive) search the public universe and are preserved/linked.

## Real US map (reuse, not squares)

Reuse `rcm_mc/ui/us_geo_map.py::render_us_geo_map(values, *, metric_label,
value_format, state_notes, accent_states, selected_state, state_link_template,
empty_message)` — the same real SVG choropleth `/portfolio/map` uses (emits
`usgeo-state` classes). It already supports:
- `state_link_template` → **click state to filter** the table (server round-trip via `state=`)
- `selected_state` → highlight current geography
- value-shaded layers + legend via `values` + `value_format`

Map layers (each data-backed or disabled with DATA REQUIRED):
provider count (always, from loader) · age 65+ · median HH income · private
insurance % · uninsured % (geo-intel ACS) · market opportunity score · MA
penetration · SDOH burden (CDC PLACES) · quality/ratings (vertical quality) ·
payer stress / ownership-consolidation where the source exists. County map is
a follow-up only if county geometry exists; otherwise state map + county
table/profile drilldown.

## Scoring (documented, real-metric, missingness-aware)

Each score is formula-documented, computed only from available real metrics,
labeled with source, and shows **DATA REQUIRED / insufficient data** when it
can't be computed. Not investment advice. Categories: `market_score`,
`quality_score`, `payer_score`, `access_score`, `compliance_risk_score`,
`consolidation_score`, and an `opportunity_score` (percentile blend of market
demand + payer attractiveness + supply gap + quality/operational headroom −
compliance penalty). No fake AI scores.

## Query-param contract (shareable, server-first)

`view` · `vertical` · `state` · `county` · `metric` · `layer` ·
`min_quality` · `max_uninsured` · `min_private_insurance` · `min_age65` ·
`min_income` · `min_market_score` · `ownership` · `provider_type` ·
`compare` (csv of ccns) · `sort` · `direction`. Server-rendered owns truth;
client JS may enhance.

## Incremental PR plan

1. **(this PR)** component map + build plan — docs only.
2. Six-screen `view=` shell — PEdesk-native tabs, no iframe/CDN, placeholder
   panels labeled, tests.
3. Real US map integration — `render_us_geo_map`, state click→`state=` filter,
   layer selector, legend.
4. Vertical selector + provider table from real loaders + source/missingness
   chips + profile/X-Ray links.
5. Compare basket (`compare=`) — same-vertical full, cross-vertical shared-only.
6. Just-missed scan — miss-distance logic, failed criteria + distance, relax-one.
7. Column picker / metric dictionary — grouped, source + availability per metric.
8. Inspector drawer — detail, peer/market context, X-Ray/profile links, Guide.
9. Saved screens — URL/shareable state; honest persistence caveat or real store.
10. Replicate across all verticals.
11. Guide/RAG context for every screen + vertical (what it's for, which data,
    how scores compute, why a target just missed, what's missing, not advice,
    how to promote to Pipeline).

## Invariants

No fake data · every row carries data-universe + source status + year +
missingness · no iframe prototype shipped · no external fonts/CDN · real US map
(no square cartogram) · historical deal corpus never an active target ·
`/login`/auth/deploy/env/secrets/Ollama/Tailscale/RAG-runtime untouched ·
#579/#580 parked.
