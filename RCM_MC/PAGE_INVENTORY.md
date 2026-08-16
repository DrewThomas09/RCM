# PAGE_INVENTORY — graded 2026-06-10 (Phase 0) · Tier-1 fixes re-checked 2026-06-12 (W2-191…200)

> **2026-08-16 — the Tier-2 long tail is now HIDDEN, not just chip-labelled.**
> The grading below still describes what each page *is*; it no longer
> describes what a reader is *offered*. Chip-labelling an illustrative page
> "honest scaffold" was the right call while the product was a diligence
> desk; it is the wrong call for a public-data verification surface, where a
> page of invented numbers undercuts the whole promise however honestly it
> is labelled. Those pages — plus the single-market study suites (TX
> infusion, IFT/MMT) and the sponsor-corpus tail — are now off every
> listing surface via `rcm_mc/ui/_surface_visibility`. They still SERVE:
> routes resolve, deep links work, and a page rejoins the catalog the day
> its live-data wiring lands (drop it from the set). Tier 1 is untouched.
>
> **2026-08-16b — second sweep: deal EXECUTION and single-sector studies.**
> The product framing tightened to *healthcare-PE deal tracking on top of
> aggregated CMS data*, with the X-rays at the centre. Two more classes went
> Hidden: the artifacts of RUNNING a transaction (IC packet, QoE memo, CDD
> hub + scope, expert calls, CIM cross-check, deal MC, covenant stress,
> checklists, LP reporting) as distinct from TRACKING one, and the bespoke
> single-sector studies (imaging atlas, the /market sector-report catalog)
> alongside the infusion + IFT suites already hidden. Two lines get
> re-litigated on every sweep and are pinned by name in
> `tests/test_hidden_surfaces.py`: *breadth, not subject* (a whole CMS
> program's Care Compare universe stays; a bespoke sector study does not)
> and *tracking, not execution*. Visible surface: 173 → 137.

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
| /target-screener (9 universes) | 1,2 | real (CMS HCRIS + 6 vendored Compare files) | works | deep (map/table/compare/saved/basis filter) | A | ✅ per-row +Deal (W2-194) |
| /diligence/hcris-xray | 1,2 | real HCRIS | works | deep (peers, bands, gaps, flags) | A | ✅ P8 reg exposure + exhibit roster (W2-185) |
| /portfolio | 3 | real deal store | works | medium | B+ | ✅ per-deal alert digest (W2-197) |
| /deal/<id> workbench | 1,2,3 | real packet + entered profile | works | deep | A− | ✅ ENTERED-basis pass (W2-199) |
| /predictive-screener | 2 | real HCRIS + labeled ridge estimates | works | deep ("?" explainers, bounds) | A− | est_ar_days column lacks "?" |
| /command-center (/) | 2,3 | real HCRIS aggregates (band-fixed) | works | medium | A− | ✅ KPI drill-throughs (W2-193) |
| /market-data (+/map) | 1,2 | real HCRIS state aggregates | works | medium | B+ | ✅ county drilldown links (W2-195) |
| /compare (deals) | 2,3 | real deal store | works | medium | B+ | ✅ P4 percentile-vs-book chips (W2-192) |
| /regression (portfolio+HCRIS) | 1,2 | real | works | deep | B+ | overfit guard shipped today; surface holdout coverage in-UI |
| /import (quick import) | 2,3 | n/a (entry) | works | medium | B+ | ✅ server-side bounds + comma fix (W2-191) |
| /ebitda-bridge/<ccn> | 1,2 | real HCRIS + labeled model | works | deep | A− | ✅ waterfall exhibit chrome (W2-196) |
| /cms-sources, /data-catalog | 1 (internal) | real registry | works | medium | B | unify with gap registry → DQ dashboard (P11) |
| /alerts, /watchlist | 3 | real store | works | medium | B+ | vintage-diff alerts (P9) |
| /metric-glossary, /methodology | 1,2 | n/a docs | works | deep | A− | KPI-label links extended (W2-200); long-tail pages remain |
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
