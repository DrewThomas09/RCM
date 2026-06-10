# PAGE_INVENTORY — graded 2026-06-10 (Phase 0)

Evidence: scripts/route_walker.py walked 361 exact-match page routes on the
seeded demo (5 deals, 6,123-hospital HCRIS universe): **349 render 200, 0
tracebacks, 0 nan/None leaks**. 12 non-200s are POST-only endpoints hit with
GET (/pipeline/add, /quick-import, /audit/enter 403-by-design, etc.) — not
bugs. 332 pages carry the ILLUSTRATIVE data-universe chip somewhere on the
page (mostly in nav/sub-panels — the chip system itself is healthy).
Full TSV: /tmp/route_walk.tsv (regenerate any time; takes ~90s).

Users: 1 = Chartis consultant in live CDD · 2 = PE VP/principal · 3 = portfolio ops.

## Tier 1 — daily-driver surfaces (hand-graded)

| Page/Route | User | Data | Functional | Depth | Grade | Top fix |
|---|---|---|---|---|---|---|
| /target-screener (9 universes) | 1,2 | real (CMS HCRIS + 6 vendored Compare files) | works | deep (map/table/compare/saved/basis filter) | A− | per-row deal-attach action |
| /diligence/hcris-xray | 1,2 | real HCRIS | works | deep (peers, bands, gaps, flags) | A− | facility→rule exposure join (P8) |
| /portfolio | 3 | real deal store (fixed today) | works | medium | B | per-deal alert digest |
| /deal/<id> workbench | 1,2,3 | real packet + entered profile | works | deep | B+ | ENTERED-basis pass on observed-metric panels |
| /predictive-screener | 2 | real HCRIS + labeled ridge estimates | works | deep ("?" explainers, bounds) | A− | est_ar_days column lacks "?" |
| /command-center (/) | 2,3 | real HCRIS aggregates (band-fixed) | works | medium | B+ | drill-through links on KPIs |
| /market-data (+/map) | 1,2 | real HCRIS state aggregates (band-fixed today) | works | medium | B | county-level drilldown |
| /compare (deals) | 2,3 | real deal store | works | medium | B | percentile context vs peers (P4) |
| /regression (portfolio+HCRIS) | 1,2 | real | works | deep | B+ | overfit guard shipped today; surface holdout coverage in-UI |
| /import (quick import) | 2,3 | n/a (entry) | works | medium | B | entry-time range validation (⚠ exists only on display) |
| /ebitda-bridge/<ccn> | 1,2 | real HCRIS + labeled model | works | deep | B+ | exhibit-style export |
| /cms-sources, /data-catalog | 1 (internal) | real registry | works | medium | B | unify with gap registry → DQ dashboard (P11) |
| /alerts, /watchlist | 3 | real store | works | medium | B+ | vintage-diff alerts (P9) |
| /metric-glossary, /methodology | 1,2 | n/a docs | works | deep | A− | link from every KPI label (partial) |
| /regulatory-calendar | 1,2 | real curated YAML w/ source URLs | works | medium | B | facility-type → applicable-rule join (P8b) |

## Tier 2 — broad analytic catalog (~200 routes, walker-graded)

All render 200 with the editorial shell; the long tail (aco-economics,
biosimilars, cyber-risk, mgmt-comp, partner-economics, etc.) is explicitly
chip-labeled ILLUSTRATIVE — honest scaffolds awaiting real wiring. Graded
C as a class: functional, labeled, shallow-by-design until each gets its
data source (workstream G backlog). The data-public trackers with REAL
wiring (cost-structure, debt-service, payer-stress — HCRIS-attached via
?ccn=) grade B.

## Tier 3 — known non-pages

POST-only routes (12), /healthz//ready (infra), CSV endpoints (7 tiny-200s,
by design), /foo + /x (404 test fixtures in server routing).

## Conventions used in grading

- "real" data = traced to CMS HCRIS / vendored CMS Compare files / the deal
  store with provenance chips; "labeled" = ridge/conformal or illustrative
  chips present per the basis-badge system shipped earlier today.
- A beautiful page on fake data caps at D unless ILLUSTRATIVE-chipped
  (honest scaffolds cap at C).
