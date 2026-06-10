# FEATURE_MATRIX — Part V power features + workstreams vs reality (2026-06-10)

| Feature | Status | Where today | Users | Notes / gap |
|---|---|---|---|---|
| P1 Deal Workspace | PARTIAL | deals store, /deal/<id> workbench, watchlist, owners, deadlines, notes, stages | 1,2,3 | Deal exists as object; missing: global active-deal switcher carrying scoped context into screener/X-Ray/market pages |
| P2 CIM Cross-Check / Variance | MISSING | — | 1 | Highest-leverage gap. Estimators buildable from in-repo data: provider counts (screener universes), margins/payer-mix/volumes (HCRIS), market context (state aggregates) |
| P3 Market Sizing driver trees | MISSING | partial precedent: ebitda-bridge driver math, provenance trees | 1,2 | Epi-rate data (CDC/AHRQ) not in repo; a HCRIS-grounded "market revenue tree" per state/cohort is buildable now; full epi tree needs network vintage |
| P4 Peer-set / percentile engine | PARTIAL | X-Ray peer benchmarks (P25/50/75 + distance), screener compare | 1,2,3 | Missing: reusable "KPI vs peer percentile" chip + saved peer-set object reusable across modules |
| P5 Exhibit Factory | PARTIAL | CSV exports everywhere, packet renderer, print-friendly workbench | 1 | Missing: exhibit wrapper (title/units/source/numbering), copy-as-image, per-deal exhibit registry |
| P6 Geographic Intelligence | PARTIAL | /market-data/map, /portfolio/map (SVG choropleths) | 1,2 | Missing: facility pins, catchment rings, overlap shading |
| P7 Roll-Up Scenario Builder | MISSING | compare basket on screener is select-only | 2 | Buildable end-to-end on HCRIS now: N facilities → combined volumes/NPR/payer blend + state share/HHI delta |
| P8 Policy & Rate Intelligence | PARTIAL | /regulatory-calendar (curated, sourced YAML) | 1,2 | Missing: facility→applicable-rules join + per-facility exposure panel on X-Ray |
| P9 Monitoring/Watchlists/Alerts | PARTIAL | alerts lifecycle, watchlist, health trend | 3 | Missing: vintage-diff engine ("ownership changed", "fell p62→p44") |
| P10 Provenance & Audit | PARTIAL→STRONG | provenance graph + tooltips, source links to CMS origin, basis badges, gap dots, "?" calc explainers | all | Missing: one provenance MODAL pattern everywhere; coverage metric |
| P11 Data Quality Dashboard | PARTIAL | /cms-sources, data freshness pill, gap registry CLI | 1 internal | Missing: one screen joining vintages + row counts + null rates + gap census + pages-consuming |
| P12 Command Palette | SHIPPED | Cmd-K palette, route registry, tests | all | Entity (CCN/name) jump partial — verify + extend |
| P13 Honest Insight Bullets | PARTIAL | narrative generators on some pages | 1 | Missing: template+guard system as a primitive; coverage on top panels |
| P14 Performance | PARTIAL | ETags, gzip, p50/p95/p99 observability | all | No timing budget enforcement; route_walker shows most pages <1s on seeded data |

## Workstreams
- A UI polish: strong baseline (editorial system, basis badges). Remaining: exhibit affordances.
- B Accuracy: bands/bounds/coverage sweeps shipped earlier today; missing in-UI holdout coverage panel.
- C CDD deep: P2 + expert-call prep generator MISSING.
- D Playbooks: screener has 9 universes (ASC absent as such — closest is the
  vendored Compare verticals); HCRIS hospitals deepest. PPM/behavioral/SNF KPI depth varies.
- E HCIT: /hcit-platform page is ILLUSTRATIVE; CHPL API network-gated → backlog with source named.
- F Sourcing: screener + predictive screener strong; ownership/CHOW signal partial (snf_chow vendored).
- G Data realism: gap registry live (`rcm-mc data gaps`); medicaid S-3 re-ingest + POS bed backfill are the named network-gated fills.
- H Synthetic→real: 5 seeded demo deals are fictional names with realistic metrics — candidate: rebuild one demo deal on a real named CCN.
