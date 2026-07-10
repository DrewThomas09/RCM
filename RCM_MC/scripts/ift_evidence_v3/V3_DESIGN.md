# IFT Sourced Evidence Master v3.0 — build design

## Product rule (inherited from v2.7, applied without exception)
A number enters only if a named publisher document or dataset produced it (GOV / SOURCED /
ACADEMIC / PUBLIC-WEB with the label shown), or an Excel formula computes it from numbers that
did (DERIVED, inputs named). Anything ILLUSTRATIVE / modeled / "rough" is quarantined on
Excluded_Not_Sourced with the reason. Blue font = hardcoded from a source. Black = formula.
Green = cross-tab link. Every headline figure gets a Fact ID (extending F165) resolved on
Fact_Ledger; every source gets an S-ID (extending S77) on Source_Register + Source_Index.

## Assembly
1. Faithful 1:1 copy of all 47 v2.7 tabs (values, formulas, styles, comments, merges,
   widths, freeze panes) — PROVEN: 11,386 cells, zero diffs after LibreOffice recalc.
2. Re-create the 37 v2.7 charts natively (parsed from chart XML; specs in v27_charts.json +
   v27_chart_anchors.json).
3. Targeted, enumerated corrections to stale v2.7 governance text (each logged on
   V3_Change_Log with old → new → why):
   C1 README: "43 tabs"→actual; "73 sources"→actual; revision table gains rev 6.
   C2 Methodology: "F01-F147" stale range; "data-api/revision 1/" mangled "v1" URLs.
   C3 Source_Index: title "77" vs subtitle "73" mismatch; tier counts recomputed; S62-S77
      re-sorted into the main block (footer moved below).
   C4 Source_Register: S31 duplicate/contradictory note resolved (stale rev-1 text removed,
      documented); S21/S28 same-document duplication noted in-place.
   C5 Verification_Log Panel E stale "NOT reflected in this workbook" contradiction fixed.
4. ~40 new tabs (below) + extended governance.

## New tab groups (order after existing sections; tab colors per group)

### Group M — Medicare claims depth (live pulls; tab color teal FF1F6F8B)
- MUP_Ambulance_National — MUP Physician by Geo & Service, National, HCPCS A0425-A0436,
  2013-2024 (12 vintages, per-year UUIDs from DCAT). Cols: year, code, POS, providers, benes,
  services, avg submitted/allowed/paid/stdzd. CAGR block (formulas), per-code trend flags.
  Charts: services by code group over time; avg allowed per service; provider counts.
- MUP_Ambulance_State — 2024 + 2019 state × code rows (comparison pair years), per-1,000
  normalization via Medicare enrollment; top/bottom state screens (formulas).
- PSPS_Denial_Series — PSPS 2010-2024, 7 ground codes (A0425-A0429, A0433, A0434):
  submitted vs denied services by code-year (client-side aggregation of raw rows, column-
  selected pulls). Denial-rate formulas; series charts. THE new evidence unique to v3.
- Market_Saturation_Ambulance — state grain × 15 rolling windows 2020-2025 × 3 ambulance
  service types: providers, FFS benes, users, payment. Trend + charts. (2,295 rows)
- Enrollment_ESRD_State — Medicare Monthly Enrollment state×year 2013-2025 ESRD benes
  (AGED_ESRD + DSBLD_ESRD); dialysis-demand series + charts. (754 rows)

### Group S — Supply depth (tab color teal)
- PECOS_Suppliers_State — vendored PPEF 2026.04.01 extract: 55 state rows + national 10,465
  "PART B SUPPLIER - AMBULANCE SERVICE SUPPLIER"; cross-check columns vs MUP provider counts.
- QCEW_EMS_Employment — BLS QCEW NAICS 621910 annual 2014-2025: national series
  (establishments, employment, wages, avg pay) + latest-year state table. CAGR + charts.
- NPPES_Registry_NE_IA — the 751-row NPPES ambulance-org registry (repo CSV, pulled
  2026-07-10), categorized municipal/private/hospital/air; summary block.
- Facility_Universe_State — Care Compare snapshots: hospitals (emergency_services flag),
  SNF, dialysis, IRF, LTCH, hospice, HHA — counts by state (derived from full pulls; raw
  counts cited to PDC datasets + access date). O/D node map.
- CHOW_Consolidation — CMS hospital + SNF change-of-ownership national+state series
  2016-2025 (vendored). Charts + CAGR.

### Group P — Payment depth (tab color navy FF00294C)
- GPCI_Localities — CY2025 Addendum E: 116 localities × PE GPCI; ambulance geographic
  factor = 0.7×PE_GPCI + 0.3 (DERIVED formula per row); state min/max screens.
- Derived_Rate_Card — RVU × CF × geographic factor worked rate card by HCPCS ×
  urban/rural/super-rural add-ons — ALL formulas from GOV inputs on-sheet.
- Service_Level_Economics — ift_service_levels: fee_rows(), medicare_mix(),
  payment_mechanics(), mix_readings() (~45 GOV+DERIVED rows; CY2026 rates, CY2024 volumes).
- Commercial_Context_APCD — CIVHC CO APCD (redistributable): commercial-as-%-of-Medicare
  summary, clearly labeled facility-claims / CO-only CONTEXT, never an ambulance rate.

### Group D — Demand & clinical depth (tab color purple FF7A5195)
- Condition_Transfer_Registry — 32-condition transfer matrix (ift_clinical_demand):
  condition, family, acuity, origin→destination, time window, national volume + per-row
  volume citation (23 GOV + 6 ACADEMIC; 3 FRAMEWORK rows carried with explicit chips,
  volumes only where published; modeled CAGR column EXCLUDED).
- Post_Acute_Supply_State — destination_supply(): SNF/IRF/LTACH/HHA/hospice provider
  counts, national + by state (~275 rows, SOURCED CMS provider files).
- Certification_Series — analytics.supply_trend() 6 provider classes, certification
  vintage series 1968-2025 (~280 points) + CAGR formulas + charts.
- State_Facility_Structure — analytics.state_breakdown() 6 classes: for-profit share,
  top-5 concentration, dialysis HHI 2,767 (~300 rows).
- Growth_Evidence_Registry — ift_growth_evidence.all_evidence(): 35 cited records, 8 themes,
  verbatim quotes + Kaufman Hall M&A series 2015-2025 + AHA system-affiliation series (charted).
- Demand_Evidence_Quotes — ift_demand_evidence.all_evidence(): 14 verbatim-quote records
  (GOV 4 / SOURCED 5 / ACADEMIC 4 / DERIVED 1).
- MA_Geo_Variation — vendored CMS MA state file 2022: ip/snf/er per-1,000 by state —
  published bounds for the TAM MA-utilization TEAM-INPUT row (cross-link to TAM_Model_National).
- Clinical_Benchmarks — in-depth §4.4: ~22 ACADEMIC DOI-cited rows (STEMI/stroke DIDO,
  offload, boarding trend, delayed-discharge economics).

### Group G — Geography & market structure (tab color purple)
- Metro_Structure_20 — ift_geo.all_metros(): 20 metros × SOURCED facility structure +
  footprint_rollup() national/state shares.
- County_Demography — ift_mmt: 22 GOV county rows, POP_2024_EST, county_growth 2020→2024 CAGR.
- CBSA_Crosswalk_Reference — OMB Bulletin 23-01 national county→CBSA crosswalk (1,915 rows;
  reference tab that closes v2.7 pending P3).
- HPSA_Rural_Designations — vendored HRSA HPSA state table (rural add-on exposure).

### Group C — Company & competitive (PUBLIC-WEB labeled; tab color grey FF555555)
- MMT_NPI_Estate — 23 SOURCED NPPES rows (addresses, DBAs, enumeration dates).
- Company_Dossier — ift_company: 16 cited sources, ownership timeline 1987-2026, court
  records, revenue-estimate conflict exhibit (labeled unusable), scale claims.
- Competitor_Registry — ift_npi_landscape.COMPETITORS: 7 cited profiles (~28 NPIs) +
  claims-pull recipe; supply-landscape rows from in-depth §4.6.
- Payment_Integrity — in-depth §4.5: CERT split, RSNAT natural experiment (−61%/−77%/+19%),
  OIG series (GOV).
- Contract_Benchmarks — in-depth §4.8: 911/NEMT SLA-and-penalty precedents + CA AB 40
  (re-verify flags carried).

### Group R — Reference & governance additions (tab color navy)
- Connector_Estate_Map — the 16-connector / 204-dataset estate + 17 IFT probes: dataset,
  endpoint, vintage, citation, live-verified status (2026-07-10), row potential. The
  "all the connectors" tab — machinery documented, no fake numbers.
- Pull_Manifest — every live pull for v3: endpoint, UUID, filters, pages, rows, sha256 of
  cached payload, UTC timestamp. Full reproducibility.
- Code_Vocabulary — extends Code_Crosswalks: POS 41/42, revenue centers 0540-0549,
  condition codes AK/B2, remittance N114, modifier 32, taxonomy 3416*/3439* (machine-readable
  sources in repo named).
- KPI_Dictionary — 12 worked metric definitions + 32 tier definitions + stakeholder
  scorecard (FRAMEWORK definitions, zero numbers — labeled).
- Regulatory_Register — 11 GOV statutory rows + service-level CFR verbatim quotes +
  edge cases/misconceptions (31 sourced qualitative rows).
- V3_Change_Log — every cell changed vs v2.7 (old → new → reason → verification).
- Verification_Log extensions (new panels): copy-fidelity proof (11,386 cells, 0 diffs),
  live-pull verification (per dataset: probe value vs pulled value), recompute audit
  (every DERIVED formula recomputed in python, tolerance, result), formatting audit.
- Fact_Ledger extension — new facts F166+ (headline values of every new tab, formulas
  referencing home tabs, source IDs, locators, cross-checks).
- Source_Register / Source_Index extensions — S78+ one row per new dataset/document with
  publisher, vintage, locator, URL, tier, access date, powers.
- Excluded_Not_Sourced extensions — new quarantine rows: repo lever composites
  (+2.9%/+3.0%/+6.0%/yr), demand_forecast "rough" age-band CAGRs, $6.5B/$18-22B TAM
  figures, per-trip $ assumptions, SAM/SOM 165.8x artifact, band %s, synthetic-NPPES
  warning, segment-attractiveness ratings — each with "what would make it citable".

## Numbering allocation (avoid collisions during parallel build)
Fact IDs:  M group F166-F209 · S group F210-F239 · P group F240-F269 · D group F270-F309 ·
           G group F310-F329 · C group F330-F349 · R group F350+
Source IDs: M S78-S89 · S S90-S99 · P S100-S107 · D S108-S125 · G S126-S131 · C S132-S141 ·
           R S142+
(Builders declare entries; integrator renumbers contiguously at assembly, preserving order.)

## Non-negotiables for every new tab
1. Title row + subtitle ("The question: …") + navy column headers (v3lib house style).
2. Basis column with chip on every value row; blue font ONLY for source-hardcoded values.
3. Source citation with exact locator (dataset, vintage, table/field, URL) — on-row or in
   a sources block at the sheet foot; every source registered with an S-ID.
4. Time series: trend-eligibility flag per row/segment; CAGR as an Excel formula
   ((end/start)^(1/n)-1) with the window named; break years flagged, never trended across.
5. Every series tab carries at least one native chart; chart series reference live ranges.
6. All derived cells are Excel formulas (never pasted results) so the workbook recomputes.
7. Suppression/floor caveats carried where CMS masks small cells.
8. No ILLUSTRATIVE numbers anywhere outside Excluded_Not_Sourced.

## Verification gates before ship
V1 copy fidelity: recalc copy vs v2.7 cached values — zero diffs (DONE at prototype).
V2 formula integrity: LibreOffice recalc of final v3 → zero Excel error cells.
V3 recompute audit: python recompute of every new DERIVED cell — match to 1e-9.
V4 pull audit: cached payloads re-aggregated independently; sha256s stable across two pulls.
V5 citation audit: adversarial agents verify each new S-ID resolves (URL live or repo file
   exists) and each fact's locator matches the cached data.
V6 illustrative scan: regex + agent sweep for banned patterns (TAM $6.5B etc.) on evidence tabs.
V7 page count: printed-page estimator ≥ 200 (baseline v2.7 alone ≈ 201; target ≥ 400).
V8 ledger integrity: F-IDs and S-IDs contiguous, unique, all referenced tabs exist;
   Source_Index counts recomputed and correct this time.
