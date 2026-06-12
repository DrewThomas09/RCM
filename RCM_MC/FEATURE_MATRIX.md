# FEATURE_MATRIX — Part V power features + workstreams vs reality (2026-06-10 · statuses re-checked 2026-06-12)

| Feature | Status | Where today | Users | Notes / gap |
|---|---|---|---|---|
| P1 Deal Workspace | PARTIAL | deals store, /deal/<id> workbench, watchlist, owners, deadlines, notes, stages | 1,2,3 | Deal exists as object; missing: global active-deal switcher carrying scoped context into screener/X-Ray/market pages |
| P2 CIM Cross-Check / Variance | SHIPPED | /diligence/cim-crosscheck — claims vs HCRIS estimates, variance flags, credibility index, memo/CSV export, claim-percentile chips | 1 | LOG #2, W2-138, W2-182 |
| P3 Market Sizing driver trees | SHIPPED | /diligence/tam-sam (96-industry catalogue, scenarios, xlsx), Texas infusion driver chain, national scan; CDC PLACES/ACS epi wired live w/ fallback | 1,2 | TAM/SAM sprint + waves #52–78 |
| P4 Peer-set / percentile engine | SHIPPED (chip) | ck_peer_percentile chip — X-Ray, CIM claims, /compare-vs-book; honesty guards (n<8) | 1,2,3 | Saved peer-set OBJECT still open |
| P5 Exhibit Factory | SHIPPED (wrapper) | ExhibitFactory: CIM table, roll-up, X-Ray peer roster, screener compare, EBITDA-bridge waterfall; print page rules; /exhibit composer + chart exports | 1 | Per-deal exhibit REGISTRY still open |
| P6 Geographic Intelligence | PARTIAL | /market-data/map, /portfolio/map (SVG choropleths) | 1,2 | Missing: facility pins, catchment rings, overlap shading |
| P7 Roll-Up Scenario Builder | SHIPPED | /pipeline/rollup — combined volumes/NPR/payer blend, HHI before/after, antitrust note, save-to-deal notes (ROLL-UP chip) | 2 | LOG #3, #19, W2-183 |
| P8 Policy & Rate Intelligence | SHIPPED (join) | facility→rule exposure panel on X-Ray; Texas reg/reimbursement environment section | 1,2 | LOG #6, W2-159 |
| P9 Monitoring/Watchlists/Alerts | SHIPPED (diff) | vintage-diff on saved screens + row-level ?diff= detail; per-deal alert digest on /portfolio | 3 | LOG #18, W2-197. Ownership-CHOW diff alerts still open |
| P10 Provenance & Audit | PARTIAL→STRONG | provenance graph + tooltips, source links to CMS origin, basis badges, gap dots, "?" calc explainers | all | Missing: one provenance MODAL pattern everywhere; coverage metric |
| P11 Data Quality Dashboard | SHIPPED | /data-quality — sources × vintage, live row counts, null rates, staleness chips (CURRENT/AGING/STALE), gap census | 1 internal | LOG #5, #15 |
| P12 Command Palette | SHIPPED | Cmd-K palette + CCN entity jump + provider name search | all | LOG #17, P12b verified 2026-06-12 |
| P13 Honest Insight Bullets | SHIPPED (primitive) | ck_insight_bullets (guarded, copy-to-clipboard) on /portfolio + /state-profile | 1 | W2-189. Long-tail panel coverage open |
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
