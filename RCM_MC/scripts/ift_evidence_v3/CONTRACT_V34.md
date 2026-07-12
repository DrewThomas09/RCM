# v3.4 section-module contract (read fully before writing a module)

Every v3.4 analysis tab is a module in `sections/sec_<key>.py` exporting:

```python
SHEETS = [{'name': 'Tab_Name', 'question': 'one line'}]
def build(wb, ctx):
    ...
    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings, 'meta': {...}}
```

`ctx = {'lib': v3lib, 'repo': path, 'cache': cache_dir, 'accessed': '11 Jul 2026'}`.
Load pull artifacts with `ctx['lib'].load_cache(ctx['cache'], key)` (handles .json and .json.gz).

## House rules (non-negotiable)
1. Blue font ('src') = value hardcoded from a named dataset/document. Black
   ('fml') = a live Excel formula string starting with '='. Green ('link') =
   cross-tab reference formula. Use SheetBuilder: sb.title, sb.subtitle,
   sb.note, sb.prose, sb.banner, sb.headers, sb.row([...(value, kind, fmt)...]),
   sb.blank. Formats: lib.FMT_INT/FMT_USD/FMT_USD2/FMT_PCT1/FMT_PCT2/FMT_DEC1/
   FMT_DEC2/FMT_X.
2. NO em dashes anywhere in cell text. Use ' - '. Years as data cells are fine
   as ints; year LABELS in headers as text.
3. Every tab: title, subtitle stating THE QUESTION + sources + join keys,
   a DATA QUALITY note (sb.note) naming suppression/bias/scope caveats,
   panels via sb.banner, a final 'Read panel' banner with sb.prose, and at
   least one finding in the returned list.
4. No composite indices. Matched ratios only, each ratio's confound printed
   in the SAME row (a 'note' cell).
5. Derived comparisons print their caveat in the same row. A suppressed cell
   is a floor and says so. Never mix PSPS submitted with MUP final-action.
   The label ILLUSTRATIVE is banned; unpriceable = bordered PENDING cell
   (write the string 'PENDING' with kind 'note' and name the public dataset
   that would fill it).
6. Facts schema (each becomes F###): {'metric', 'year', 'value', 'unit',
   'basis' (GOV/SEC-A/ACADEMIC/SOURCED/PUBLIC-WEB/DERIVED/PENDING), 'tier'
   ('A' when verified against the primary), 'source_keys': [keys you
   registered in this module's sources], 'locator' (table/page/filter precise
   enough to re-find), 'lives_on': tab name, 'cross_check': one sentence}.
7. Sources schema (each becomes S###): {'key', 'publisher', 'document',
   'vintage', 'locator', 'supplies', 'url', 'tier', 'accessed',
   'powers': [tab names]}. Reuse an existing pull's data without a new source
   row ONLY if a prior module already registered that dataset AND you cite
   its tab; when in doubt register your own source row.
8. Findings schema: {'id_hint': int, 'finding': text, 'numbers': a LIVE
   formula string referencing a cell on your tab (never a typed number),
   'sources': 'key1; key2', 'confidence': short, 'guardrail': the
   interpretation limit, in plain words}.
9. FIREWALL: public sources only. Never describe any organization as a
   customer/prospect/account of any company. The health-system group is
   framed exactly as 'research cohort of representative multi-hospital
   health systems operating in the study footprint, selected for depth'.
   No contract terms, performance metrics, or survey statistics that are
   not tied to a public document.
10. Charts: use lib.add_chart(ws, anchor, title, cat_ref, series, kind=...,
    y_fmt=...) with series refs like "'Tab'!$B$5:$B$20". Single-axis only.
    Anchor charts to the RIGHT of data with a 14-row pitch or below the
    last row + 2; the global normalize pass resolves residual collisions.
11. Smoke-test before you finish: load the shipped workbook
    (/home/user/RCM/RCM_MC/deliverables/IFT_Sourced_Evidence_Master_v3_3.xlsx),
    call your build(wb, ctx) with ctx as above (cache='ift_v3_cache' relative
    to scratchpad), print fact/source/finding counts and your tab's max_row.
    It must run clean. Do NOT save the workbook.

## Data landmarks
- MUP provider grain: cache keys mup_provider_{year}_{code}, years currently
  2013/2019/2024 (more arriving: enumerate available years by probing keys),
  codes A0425-A0436. Fields: Rndrng_NPI, Rndrng_Prvdr_Last_Org_Name,
  Rndrng_Prvdr_First_Name, City, State_Abrvtn, Ent_Cd, HCPCS_Cd,
  Place_Of_Srvc, Tot_Benes, Tot_Srvcs, Tot_Bene_Day_Srvcs, Avg_Sbmtd_Chrg,
  Avg_Mdcr_Alowd_Amt, Avg_Mdcr_Pymt_Amt. Values arrive as strings.
- Ground base codes: A0426,A0427,A0428,A0429,A0433,A0434. Mileage A0425.
  Air A0430/A0431/A0435/A0436 (exclude from ground shares; boundary only).
- NPPES crosswalk of market participants: scratchpad/nppes_crosswalk.json
  {query: {group, best_npis, n_hits, confidence}} + cache key
  'nppes_participant_resolution' (full hits with taxonomy + city/state).
- Corridors: cache 'hsa_2025_corridors_top15' rows {provider_id (CCN), rank,
  zip, cases, days, charges}.
- Hospital roster: HCRIS panel gz at RCM_MC/rcm_mc/data/hcris.csv.gz (ccn,
  name, city, state, county, fiscal_year, beds, bed_days_available, ...);
  Care Compare hospitals in cache 'pdc_hospitals'.
- County demand: cache 'census_county_age_2024' (county 65+ by year),
  'places_county_{measure}' (chronic prevalence), MS_County tabs already in
  the workbook, QCEW county caches qcew_county? (probe), dialysis registry
  tab Dialysis_Registry in workbook.
- CBSA: tab CBSA_Crosswalk_Reference in the workbook (county FIPS -> CBSA).
- The 23 subject-company NPIs: scratchpad/v34_seed.json key 'mmt_npis'.
- Existing v3.4 modules to imitate: sections/sec_b1_facility_pay.py,
  sections/sec_a1_mmt.py (read them first).
