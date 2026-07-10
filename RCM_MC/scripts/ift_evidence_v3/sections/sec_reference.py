"""Group R (part 1) — Reference: Connector_Estate_Map, Code_Vocabulary,
KPI_Dictionary, Regulatory_Register.

Data sources (all repo accessors / cache artifacts run or read at build time):
  * /home/user/RCM/connectors — registry.catalog() + all_registry_rows()
    (16 connectors / 204 registered datasets; counts pinned by unit tests)
  * rcm_mc.market_reports.ift_connectors.connector_estate_map() (probe registry)
  * ift_v3_cache/manifest.json — the live-pull provenance manifest (164 pulls,
    sha256 + UTC timestamps, all retrieved 2026-07-10)
  * rcm_mc/npi_cleaner/refdata.py — POS / UB-04 / RARC / modifier / NUCC
    taxonomy vocabularies (static public CMS/X12/NUBC/NUCC reference data)
  * rcm_mc/npi_cleaner/vendor_v49/npi_recovery/reference/
    mac_jurisdictions_seed.csv — MAC A/B jurisdiction seed
  * rcm_mc.market_reports.ift_research_data.AUTHORED_SECTIONS — 'kpis' and
    'regulatory' sections
  * rcm_mc.market_reports.ift_service_levels — service_levels() verbatim CFR
    quotes, edge_cases() (19), misconceptions() (12); 53-source module,
    verified July 2026

Zero invented numbers: connector rows are FRAMEWORK plumbing; probe rows carry
GOV citations only; pull rows carry counts of our own cached payloads (tier A);
the KPI tab is a definitions-only FRAMEWORK tab and says so in its subtitle.
"""
import csv
import json
import math
import os
import re
import sys

sys.path.insert(0, '/home/user/RCM/RCM_MC')
sys.path.insert(0, '/home/user/RCM')

NAVY = 'FF00294C'

SHEETS = [
    {'name': 'Connector_Estate_Map', 'tab_color': NAVY},
    {'name': 'Code_Vocabulary', 'tab_color': NAVY},
    {'name': 'KPI_Dictionary', 'tab_color': NAVY},
    {'name': 'Regulatory_Register', 'tab_color': NAVY},
]


def _h(text, chars_per_line=90, minimum=24):
    """Row height for wrapped prose (13.5pt per ~chars_per_line chars)."""
    if not text:
        return minimum
    lines = max(1, math.ceil(len(str(text)) / chars_per_line))
    return max(minimum, int(13.5 * (lines + 0.4)))


# ── data pulls ───────────────────────────────────────────────────────────────

def _load_estate():
    from connectors import registry
    cat = registry.catalog()
    rows = registry.all_registry_rows()
    assert cat['n_datasets'] == len(rows) == 204, 'registry count drifted'
    return cat, rows


def _load_probes():
    from rcm_mc.market_reports import ift_connectors as ic
    probes = ic.connector_estate_map()
    summary = ic.estate_summary(probes)
    return probes, summary


def _load_manifest(cache):
    man = json.load(open(os.path.join(cache, 'manifest.json')))
    fams = {}
    for key in sorted(man):
        m = re.match(r'(mup_national|mup_state|psps_agg|qcew_621910)_', key)
        fam = m.group(1) if m else key
        fams.setdefault(fam, []).append(man[key])
    return man, fams


def _load_refdata():
    from rcm_mc.npi_cleaner import refdata as rd
    return rd


def _load_mac_seed(repo):
    path = (repo + '/RCM_MC/rcm_mc/npi_cleaner/vendor_v49/npi_recovery/'
            'reference/mac_jurisdictions_seed.csv')
    return list(csv.DictReader(open(path)))


def _load_authored():
    from rcm_mc.market_reports import ift_research_data as rdmod
    out = {}
    for sec in rdmod.AUTHORED_SECTIONS:
        if sec['id'] in ('kpis', 'regulatory'):
            out[sec['id']] = sec
    return out


def _load_service_levels():
    from rcm_mc.market_reports import ift_service_levels as sl
    return {'levels': sl.service_levels(), 'edge_cases': sl.edge_cases(),
            'misconceptions': sl.misconceptions(),
            'n_by_basis': sl.n_by_basis(),
            'no_illustrative': sl.has_no_illustrative()}


# ── authored connector view (Panel A prose + live smoke-test results) ────────
# Live status + evidence: smoke tests run 2026-07-10 through the configured
# proxy (see inv_connectors §E); supplies text summarizes the registry slice.

_ESTATE_VIEW = {
    'cms_open_data': dict(ift='★', status='WORKS', supplies=(
        'data.cms.gov data-api — the IFT motherlode: PSPS Part B claim '
        'summaries (every ambulance HCPCS x carrier x modifier, 2010-2024), '
        'MUP Physician by Geography & Service (2013-2024), Market Saturation '
        '& Utilization (3 ambulance service types), PECOS FFS provider '
        'enrollment, Medicare Monthly Enrollment (ESRD), Hospital Service '
        'Area, post-acute utilization, HCRIS cost reports, POS/QIES facility '
        'universe, telehealth trends, dialysis/ESRD model data'),
        evidence=('PSPS 2024 /data/stats filter[HCPCS_CD]=A0428 -> found_rows'
                  '=14,977 of 14,377,293; MUP 2023 national A0428 row '
                  'returned (4,333 providers / 1,288,362 benes / 2,997,474 '
                  'services); PECOS ambulance filter -> found_rows=10,465; '
                  'DCAT /data.json 2.9MB, 158 datasets')),
    'provider_data': dict(ift='★', status='WORKS', supplies=(
        'CMS Provider Data Catalog / Care Compare (DKAN) — facility '
        'universes: hospital general information (with emergency_services '
        'flag), nursing homes, dialysis facilities, IRF, LTCH, hospice, home '
        'health, medical-equipment suppliers, plus quality files (HCAHPS, '
        'complications, MSPB). Snapshot of CURRENT facilities, not a series'),
        evidence=('hospital general / nursing home / dialysis queries -> 200 '
                  'with facility rows incl. emergency_services flag')),
    'cdc_data': dict(ift='★', status='WORKS', supplies=(
        'data.cdc.gov (Socrata/SODA) — Chronic Disease Indicators '
        '(cardiovascular / diabetes / CKD topics), PLACES county CKD '
        'prevalence, heart-disease & stroke mortality by county, mortality '
        'and vital-statistics series — the demand-severity layer under IFT'),
        evidence=('chronic disease indicators (hksd-2xuw) query -> 200 with '
                  'rows; no token needed at polite rates')),
    'medicaid_data': dict(ift='★', status='WORKS', supplies=(
        'data.medicaid.gov (DKAN) — managed-care programs by state 2024 '
        '(NEMT-brokerage proxy), Medicaid enrollment, NADAC / SDUD drug '
        'files. NEMT is boundary evidence only — a separate Medicaid benefit '
        'EXCLUDED from the IFT TAM by design'),
        evidence='managed care by state 2024 query -> 200'),
    'openfda': dict(ift='', status='WORKS', supplies=(
        'api.fda.gov — drug + device datasets (NDC, labels, enforcement, '
        '510(k), PMA). Not IFT-relevant; in-estate reference connector'),
        evidence='/drug/ndc.json -> 200'),
    'open_payments': dict(ift='', status='WORKS', supplies=(
        'CMS Open Payments (Sunshine Act, DKAN) — industry payments to '
        'clinicians. Not IFT-relevant'),
        evidence='catalog reachable -> 200'),
    'healthdata_gov': dict(ift='★', status='WORKS', supplies=(
        'healthdata.gov (HHS-wide Socrata) — hospital capacity/occupancy '
        'state + facility time series (HHS Protect; FROZEN ARCHIVE 2020-01 '
        'to 2024-04 — label the vintage), HHS-ID/CCN crosswalk, 23,080-'
        'dataset meta-catalog'),
        evidence=('hospital capacity state ts (sgxm-t72h) -> 200 (archive '
                  'row, 2021 sample)')),
    'cms_coverage': dict(ift='★', status='WORKS (bare GET)', supplies=(
        'CMS Medicare Coverage Database API — NCD/LCD coverage policy '
        '(ambulance LCDs e.g. L35162), proposed LCDs, articles, MAC '
        'contractor universe. Policy/denial-risk layer, not market numbers'),
        evidence=('bare GET /v1/reports/national-coverage-ncd -> 200 JSON; '
                  'naive ?page_size= params -> 400 (connector transport owns '
                  'the paging grammar — verify params before bulk)')),
    'healthcare_gov': dict(ift='', status='WORKS', supplies=(
        'Healthcare.gov QHP public-use files PY2026 (plan/rate/benefit '
        'PUFs). Not IFT-relevant'),
        evidence='PUF endpoints reachable -> 200'),
    'hrsa_data': dict(ift='★', status='WORKS', supplies=(
        'HRSA data downloads — HPSA primary care / dental / mental health '
        '(rural_status column -> rural add-on exposure), MUA, health-center '
        'sites. Current-designation snapshots, monthly cadence, no key'),
        evidence=('HPSA primary-care CSV -> 200, header verified ("HPSA '
                  'Name, HPSA ID, Designation Type, ...")')),
    'npi_registry': dict(ift='★', status='WORKS', supplies=(
        'NPPES NPI Registry v2.1 API — provider/org search, NUCC taxonomy '
        'fingerprints (ambulance 3416*, NEMT 3439*/3438*), practice '
        'addresses. VALIDATION ONLY for counts: hard 1,200-result ceiling '
        'per query (200/page, skip<=1000) and taxonomy filter accepts TEXT '
        'only, not codes'),
        evidence=('taxonomy_description=Ambulance&enumeration_type=NPI-2&'
                  'state=TX -> 200 real org rows; skip=1000 still returned '
                  '200 rows (cap confirmed: >1,200 orgs in TX alone); '
                  'taxonomy_description=341600000X -> API error 14')),
    'census_acs': dict(ift='★', status='BLOCKED (needs key)', supplies=(
        'US Census ACS 5-year profiles (2023 vintage) — total population, '
        'median age, median HH income, poverty, age 65+ (S0101_C01_030E), '
        'uninsured, by county/state/CBSA. 65+ only — no 85+ variable in the '
        'estate'),
        evidence=('every keyless request returns HTTP 200 with "Missing '
                  'Key" HTML; CENSUS_API_KEY is NOT set in this environment '
                  '— a free key would unblock')),
    'oig_leie': dict(ift='', status='WORKS', supplies=(
        'HHS OIG List of Excluded Individuals/Entities — full UPDATED.csv '
        '(NPI-joinable) + monthly supplements + reinstatements. Compliance '
        'screen for target diligence, not market data'),
        evidence='UPDATED.csv -> 200, header verified'),
    'bls_qcew': dict(ift='★', status='WORKS', supplies=(
        'BLS QCEW open CSV slices — NAICS 621910 (Ambulance Services) '
        'establishments / employment / wages, quarterly 2014Q1-2025Q4 and '
        'annual averages 2014-2025, national to county grain. No key'),
        evidence=('annual (qtr=a) and quarterly 621910.csv 2014-2025 -> 200, '
                  '323-394KB files')),
    'icd10': dict(ift='★', status='WORKS', supplies=(
        'NLM Clinical Tables — ICD-10-CM / ICD-10-PCS code search. '
        'Validates medical-necessity condition codes (N18 CKD, I63 stroke, '
        'Z99.2 dialysis dependence) — coding integrity, not market numbers'),
        evidence='icd10cm ?terms=N18 -> 200 with CKD stage codes'),
    'nih_reporter': dict(ift='', status='WORKS', supplies=(
        'NIH RePORTER v2 (POST JSON) — research grants + publications; '
        'marginal EMS/IFT research-funding color only'),
        evidence='POST /v2/projects/search -> 200, total=2,949,860 projects'),
}


# ══════════════════════════════════════════════════════════════════════════
# Tab 1 — Connector_Estate_Map
# ══════════════════════════════════════════════════════════════════════════

def _build_estate_map(wb, lib, cat, reg_rows, probes, summary, man, fams,
                      accessed, facts):
    ws = wb.create_sheet('Connector_Estate_Map')
    b = lib.SheetBuilder(
        ws, 10, col_widths=[15, 30, 26, 38, 62, 9, 16, 50, 6, 17],
        tab_color=NAVY)
    b.title('Connector estate map — 16 public-API connectors, 204 registered '
            'datasets, the IFT probe registry, and the live pulls behind v3')
    b.subtitle(
        'The question: what data machinery stands behind this workbook — '
        'which public healthcare APIs are wired into the repo, which of the '
        '204 registered datasets matter for interfacility transport, and '
        'which live pulls actually produced the numbers in v3? Panel A maps '
        'the connector estate (all 16 APIs smoke-tested live 2026-07-10); '
        'Panel B carries the IFT probe registry verbatim (FRAMEWORK plumbing '
        'with GOV citations, zero numbers); Panel C lists every live-pull '
        'family that fed this build, from the sha256-stamped pull manifest. '
        'This tab documents machinery — it asserts no market figures.',
        height=56)
    b.blank()

    # ── Panel A — the 16-connector estate ────────────────────────────────
    b.banner('A. The 16-connector estate — /home/user/RCM/connectors '
             '(registry.catalog() run at build time; live smoke tests '
             '2026-07-10)')
    b.headers(['#', 'Connector (registry key)', 'API label',
               'Base URL', 'What it supplies (IFT view)',
               'Datasets', 'Live status (2026-07-10)',
               'Live-check evidence (smoke test through configured proxy)',
               'IFT', 'Basis'])
    conns = sorted(cat['connectors'],
                   key=lambda c: (-c['n_datasets'], c['connector']))
    a0 = b.r + 1
    for i, c in enumerate(conns, start=1):
        view = _ESTATE_VIEW.get(c['connector'], {})
        txt = view.get('supplies', c['label'])
        b.row([
            (i, 'text', lib.FMT_INT),
            (c['connector'], 'label'),
            (c['label'], 'src'),
            (c['base_urls'][0], 'src'),
            (txt, 'text'),
            (c['n_datasets'], 'src', lib.FMT_INT),
            (view.get('status', 'not smoke-tested'), 'src'),
            (view.get('evidence', ''), 'note'),
            (view.get('ift', ''), 'label'),
            ('FRAMEWORK', 'note'),
        ], wrap=True, height=_h(txt, 58))
    a1 = b.r
    b.row([None, ('Estate totals (live formulas)', 'label'), None, None,
           ('Registered datasets across all connectors', 'label'),
           (f'=SUM(F{a0}:F{a1})', 'fml', lib.FMT_INT),
           (f'=COUNTIF(G{a0}:G{a1},"WORKS*")&" of "'
            f'&COUNTA(G{a0}:G{a1})&" APIs live"', 'fml'),
           ('COUNTIF over the live-status column; only census_acs is '
            'blocked (keyless)', 'note'), None, ('DERIVED', 'note')])
    r_tot = b.r
    b.note('Registry provenance: connectors.registry.catalog() and '
           'all_registry_rows() executed at build time returned 16 '
           'connectors / 204 datasets (equality asserted in the build '
           'script); the counts are pinned by the repo test suite '
           '(connectors/tests/test_estate_invariants.py). Beyond the 204 '
           'registered slices, 7 connectors also expose full open-data '
           'catalogs (data.cms.gov 158, Provider Data Catalog 234, Open '
           'Payments 74, Medicaid 541, Healthcare.gov 337, CDC ~1,500, '
           'healthdata.gov 23,080 datasets) through generic fetched-rows '
           'slots.', height=38)
    b.note('CRITICAL state-of-the-estate caveat: no ingested SQLite exists '
           'on disk (/home/user/RCM/var/connectors is absent), so every '
           'estate query and every Panel B probe returns empty '
           '("network-gated") today. All v3 numbers from this layer come '
           'from the LIVE pulls in Panel C — cached, sha256-stamped and '
           'timestamped — not from the connector databases.', height=32)

    # ── Panel B — IFT probe registry ─────────────────────────────────────
    b.blank()
    b.banner(f'B. IFT probe registry — rcm_mc.market_reports.ift_connectors.'
             f'connector_estate_map() run at build time ({len(probes)} '
             f'probes; FRAMEWORK plumbing + GOV citations, zero numbers)')
    b.headers(['Probe key', 'Probe title', 'Category', 'Connector -> '
               'dataset_id', 'IFT signal — why this dataset matters '
               '(verbatim; module notes appended)', 'Tier',
               'Status at build', 'Citation carried by the probe (verbatim '
               'source_label — all GOV)', '', 'Basis'])
    p0 = b.r + 1
    probe_rows = {}
    for p in probes:
        sig = p.ift_signal
        if p.note:
            sig += '  [NOTE: ' + p.note + ']'
        status = p.status
        if p.key == 'ambulance_enrollment':
            status += ' · FILTER DEFECT (see note below)'
        b.row([
            (p.key, 'label'),
            (p.title, 'src'),
            (p.category, 'src'),
            (f'{p.connector} -> {p.dataset_id}', 'src'),
            (sig, 'text'),
            (p.tier, 'src', lib.FMT_INT),
            (status, 'text'),
            (p.source_label, 'note'),
            None,
            ('FRAMEWORK · GOV cite', 'note'),
        ], wrap=True, height=_h(sig, 58))
        probe_rows[p.key] = b.r
    p1 = b.r
    b.row([None, ('Probes in registry (live COUNT)', 'label'), None, None,
           None, (f'=COUNT(F{p0}:F{p1})', 'fml', lib.FMT_INT), None,
           (f'By category: ' + ', '.join(
               f'{k} {v}' for k, v in summary.by_category), 'note'),
           None, ('DERIVED', 'note')])
    r_nprobes = b.r
    b.note('DEFECT (carried honestly, found in live verification '
           '2026-07-10): the ambulance_enrollment probe filters '
           'provider_type_desc = "AMBULANCE SERVICE SUPPLIER", but the live '
           'PECOS column value is "PART B SUPPLIER - AMBULANCE SERVICE '
           'SUPPLIER" — an equality filter returns 0 rows even after '
           'ingest. The corrected literal, run live against the PECOS '
           '/data/stats endpoint, returns 10,465 enrolled ambulance '
           'suppliers (Panel C, pecos_stats_check row; the same count is '
           'vendored from PPEF 2026.04.01 on PECOS_Suppliers_State). '
           'Second verify-at-ingest item: the hospital_capacity probe '
           'metric names an inpatient_beds_utilization column not present '
           'in the live state-ts sample — confirm the column at ingest.',
           height=48)
    b.note('Count note: the v3 design/inventory described "17 probes"; the '
           'registry as executed at build time yields ' + str(len(probes)) +
           ' — the count above is the live one, not the design note.',
           height=20)

    # ── Panel C — live pulls that fed v3 ─────────────────────────────────
    fam_meta = {
        'mup_national': (
            'Ambulance HCPCS national rows, all A04xx codes',
            'per-vintage UUIDs resolved live from DCAT; latest (2024): '),
        'mup_state': (
            'Ambulance HCPCS state rows, comparison pair 2019 + 2024, '
            '12 codes A0425-A0436',
            'per-vintage UUIDs from DCAT; latest (2024): '),
        'psps_agg': (
            'Part B line summaries incl. DENIED services, 7 ground codes, '
            'client-side aggregation of raw carrier rows',
            'per-vintage UUIDs from DCAT; latest (2024): '),
        'marketsat_state': ('3 ambulance service types; 15 rolling '
                            'reference periods 2020->2025 live in-data', ''),
        'enrollment_national_year': ('National x year enrollment incl. '
                                     'ESRD beneficiary columns', ''),
        'enrollment_state_year': ('State x year enrollment incl. '
                                  'AGED_ESRD / DSBLD_ESRD columns', ''),
        'pecos_stats_check': ('Row-count probe (/data/stats) with the '
                              'corrected ambulance filter literal', ''),
        'qcew_621910': ('NAICS 621910 Ambulance Services annual averages; '
                        'US000 national + statewide rows kept', ''),
    }
    order = ['mup_national', 'mup_state', 'psps_agg', 'marketsat_state',
             'enrollment_national_year', 'enrollment_state_year',
             'pecos_stats_check', 'qcew_621910', 'pdc_hospitals',
             'pdc_nursing_homes', 'pdc_dialysis', 'pdc_irf', 'pdc_ltch',
             'pdc_hospice', 'pdc_home_health']
    order = [f for f in order if f in fams] + \
            [f for f in sorted(fams) if f not in order]
    b.blank()
    b.banner(f'C. Live pulls that fed v3 — {len(order)} pull families, '
             f'{len(man)} cached artifacts (ift_v3_cache/manifest.json; '
             f'every artifact sha256-stamped, retrieved 2026-07-10 UTC)')
    b.headers(['Pull family (cache key prefix)', 'Dataset (publisher title)',
               'Vintages covered', 'Endpoint (latest-vintage UUID / DKAN id)',
               'Filters applied + selection notes', 'Cache files',
               'Pages fetched', 'Rows cached', '', 'Basis'])
    c0 = b.r + 1
    fam_row = {}
    for fam in order:
        entries = fams[fam]
        last = entries[-1]
        first = entries[0]
        yrs = sorted({e.get('data_year') for e in entries
                      if e.get('data_year')})
        if yrs:
            vint = (f'{yrs[0]}-{yrs[-1]} ({len(yrs)} vintages)'
                    if len(yrs) > 2 else ' + '.join(yrs))
        elif fam == 'marketsat_state':
            vint = '15 windows 2020->2025 (in-data)'
        elif fam.startswith('enrollment'):
            vint = '2013 -> latest (in-data YEAR)'
        elif fam == 'pecos_stats_check':
            vint = '2026Q1 snapshot'
        else:
            vint = 'current snapshot'
        ep = last.get('endpoint', '')
        if last.get('uuid') and len(entries) > 1:
            ep = (ep.split('/dataset/')[0] + '/dataset/{uuid}/data — ' +
                  fam_meta.get(fam, ('', ''))[1] + last['uuid'])
        elif last.get('dkan_id'):
            ep += '  (DKAN id ' + last['dkan_id'] + ')'
        filt = dict(first.get('filters', {}))
        codes = sorted({e.get('filters', {}).get('HCPCS_CD') or
                        e.get('filters', {}).get('HCPCS_Cd')
                        for e in entries} - {None})
        if len(codes) > 1:
            for k in ('HCPCS_CD', 'HCPCS_Cd'):
                if k in filt:
                    filt[k] = (f'{codes[0]}..{codes[-1]} ({len(codes)} '
                               f'codes, one artifact per code x vintage)')
        ftxt = '; '.join(f'{k}={v}' for k, v in filt.items())
        extra = fam_meta.get(fam, ('', ''))[0]
        if first.get('aggregation'):
            extra += ' · ' + first['aggregation']
        if first.get('note'):
            extra += ' · ' + first['note']
        if first.get('fields_kept'):
            extra += ' · fields kept: ' + ', '.join(first['fields_kept'])
        if first.get('purpose'):
            extra += ' · ' + first['purpose']
        extra = extra.strip(' ·')
        ftxt = ' — '.join(t for t in (ftxt, extra) if t)
        pages = sum(e.get('pages', 0) for e in entries)
        rows = sum(e.get('rows', 0) for e in entries)
        b.row([
            (fam, 'label'),
            (first.get('dataset', ''), 'src'),
            (vint, 'src'),
            (ep, 'src'),
            (ftxt, 'text'),
            (len(entries), 'src', lib.FMT_INT),
            (pages if pages else '—', 'src' if pages else 'note',
             lib.FMT_INT),
            (rows, 'src', lib.FMT_INT),
            None,
            ('GOV -> SOURCED', 'note'),
        ], wrap=True, height=_h(ftxt, 58))
        fam_row[fam] = b.r
    c1 = b.r
    b.row([('Totals (live formulas)', 'label'), None, None, None,
           ('Cached artifacts / pages / rows across all pull families',
            'note'),
           (f'=SUM(F{c0}:F{c1})', 'fml', lib.FMT_INT),
           (f'=SUMIF(G{c0}:G{c1},">0")', 'fml', lib.FMT_INT),
           (f'=SUM(H{c0}:H{c1})', 'fml', lib.FMT_INT),
           None, ('DERIVED', 'note')])
    r_ctot = b.r

    b.blank()
    b.note('Rows-cached column counts records in our cached payloads (after '
           'the stated filters/aggregation), not claims or dollars: e.g. '
           'the psps_agg families cache the raw carrier line rows that the '
           'PSPS_Denial_Series tab aggregates client-side, and '
           'pecos_stats_check caches a single found_rows probe result '
           '(10,465). Full per-pull detail — every UUID, filter set, page '
           'count, sha256 and UTC timestamp — is on the Pull_Manifest tab.',
           height=32)
    b.note('UUID discipline: data.cms.gov dataset UUIDs rotate across '
           'releases, so every UUID here was resolved from the live DCAT '
           'catalog (data.cms.gov/data.json) at pull time and recorded in '
           'the manifest. The hardcoded UUID constants in '
           'rcm_mc/data_public/cms_api_client.py DATASET_IDS were found '
           'stale/divergent in verification and were NOT used (see '
           'Excluded_Not_Sourced).', height=30)
    b.note('Known live-access limits carried from verification (2026-07-10): '
           'NPPES API caps at 1,200 results/query and rejects taxonomy '
           'CODES as filters (text only) — so NPPES API counts are '
           'validation-only, never headline supplier counts; Census ACS is '
           'blocked keyless (CENSUS_API_KEY unset); the HHS Protect '
           'hospital-capacity series is a frozen archive (2020-01 to '
           '2024-04); Care Compare files are current snapshots, not time '
           'series; the MCD coverage API rejects naive paging params.',
           height=40)
    b.note(f'Extraction: connectors.registry (Panel A), rcm_mc.market_'
           f'reports.ift_connectors (Panel B), ift_v3_cache/manifest.json '
           f'(Panel C) — all executed/read at build time, {accessed}.')

    lib.add_chart(
        ws, 'L6', 'Registered datasets by connector (registry.catalog(), '
        '2026-07-10)',
        f'Connector_Estate_Map!$B${a0}:$B${a1}',
        [('Registered datasets', f'Connector_Estate_Map!$F${a0}:$F${a1}')],
        kind='bar', width=26, height=11, y_fmt='#,##0',
        y_title='datasets in registry')
    lib.add_chart(
        ws, 'L30', 'Cached pull artifacts per live-pull family (v3 build, '
        '2026-07-10)',
        f'Connector_Estate_Map!$A${c0}:$A${c1}',
        [('Cache files', f'Connector_Estate_Map!$F${c0}:$F${c1}')],
        kind='bar', width=26, height=11, y_fmt='#,##0',
        y_title='cached artifacts')

    facts += [
        {'metric': 'Public-API connectors in the repo data estate',
         'year': '2026-07-10', 'value': cat['n_connectors'],
         'unit': 'connectors', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['connectors_registry'],
         'locator': 'connectors.registry.catalog() n_connectors; pinned by '
                    'connectors/tests/test_estate_invariants.py',
         'lives_on': 'Connector_Estate_Map',
         'cross_check': '16 Panel A rows rendered'},
        {'metric': 'Registered datasets across the connector estate',
         'year': '2026-07-10',
         'value_ref': f'Connector_Estate_Map!F{r_tot}',
         'unit': 'datasets', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['connectors_registry'],
         'locator': 'live SUM over Panel A dataset counts; '
                    'catalog() n_datasets = len(all_registry_rows()) = 204 '
                    'asserted at build',
         'lives_on': 'Connector_Estate_Map', 'cross_check': '204'},
        {'metric': 'Estate APIs verified live-reachable (smoke tests)',
         'year': '2026-07-10', 'value': '15 of 16', 'unit': 'APIs',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['connectors_registry'],
         'locator': 'Panel A live-status column (COUNTIF formula on-sheet); '
                    'only census_acs blocked (keyless)',
         'lives_on': 'Connector_Estate_Map',
         'cross_check': 'inv_connectors §E smoke-test table, 2026-07-10'},
        {'metric': 'IFT probes in the connector probe registry',
         'year': '2026-07-10',
         'value_ref': f'Connector_Estate_Map!F{r_nprobes}',
         'unit': 'probes', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_connectors_probes'],
         'locator': 'connector_estate_map() executed at build time; live '
                    'COUNT formula over Panel B tier column',
         'lives_on': 'Connector_Estate_Map',
         'cross_check': 'estate_summary total=18 (design note said 17)'},
        {'metric': 'Live-pull artifacts cached for v3',
         'year': '2026-07-10',
         'value_ref': f'Connector_Estate_Map!F{r_ctot}',
         'unit': 'artifacts', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['ift_v3_pull_manifest'],
         'locator': 'live SUM over Panel C cache-file counts; manifest.json '
                    'has 164 entries, each with sha256 + UTC timestamp',
         'lives_on': 'Connector_Estate_Map', 'cross_check': '164'},
        {'metric': 'Raw rows cached across all v3 live pulls',
         'year': '2026-07-10',
         'value_ref': f'Connector_Estate_Map!H{r_ctot}',
         'unit': 'rows', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['ift_v3_pull_manifest'],
         'locator': 'live SUM over Panel C rows-cached column',
         'lives_on': 'Connector_Estate_Map',
         'cross_check': 'python recompute 961,680 '
                        '(897,270 of it PSPS carrier lines)'},
        {'metric': 'Medicare-enrolled ambulance suppliers (PECOS live '
                   'cross-check with corrected filter literal)',
         'year': '2026Q1',
         'value_ref': f"Connector_Estate_Map!H{fam_row['pecos_stats_check']}",
         'unit': 'suppliers', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['cms_pecos_enrollment', 'ift_v3_pull_manifest'],
         'locator': 'PECOS /data/stats, filter PROVIDER_TYPE_DESC="PART B '
                    'SUPPLIER - AMBULANCE SERVICE SUPPLIER" -> '
                    'found_rows=10,465',
         'lives_on': 'Connector_Estate_Map',
         'cross_check': 'matches vendored PPEF 2026.04.01 national row '
                        '10,465 exactly (PECOS_Suppliers_State)'},
        {'metric': 'PSPS raw carrier line rows cached (2010-2024, 7 ground '
                   'codes)', 'year': '2010-2024',
         'value_ref': f"Connector_Estate_Map!H{fam_row['psps_agg']}",
         'unit': 'rows', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['cms_psps', 'ift_v3_pull_manifest'],
         'locator': '105 cached artifacts (15 vintages x 7 HCPCS); '
                    'aggregated client-side on PSPS_Denial_Series',
         'lives_on': 'Connector_Estate_Map',
         'cross_check': '897,270 rows (manifest sum)'},
    ]
    return {'a0': a0, 'a1': a1}


# ══════════════════════════════════════════════════════════════════════════
# Tab 2 — Code_Vocabulary
# ══════════════════════════════════════════════════════════════════════════

def _build_vocab(wb, lib, rd, mac_rows, accessed, facts):
    ws = wb.create_sheet('Code_Vocabulary')
    b = lib.SheetBuilder(
        ws, 8, col_widths=[24, 13, 46, 38, 50, 36, 34, 14],
        tab_color=NAVY)
    b.title('Code vocabulary — the ambulance/IFT codes beyond HCPCS: place '
            'of service, revenue centers, condition/value codes, remittance, '
            'modifiers, taxonomies, MACs')
    b.subtitle(
        'The question: which claim-form and registry code systems, beyond '
        'the A04xx HCPCS ladder already on Code_Crosswalks, identify '
        'ambulance activity in claims and provider data — and where does '
        'each code appear? Extends the v2.7 Code_Crosswalks tab with the '
        'machine-readable vocabularies vendored in the repo '
        '(rcm_mc/npi_cleaner/refdata.py — static public CMS/X12/NUBC/NUCC '
        'reference data, read at build time) plus the NUCC transport '
        'taxonomy constants and the MAC jurisdiction seed. Reference codes '
        'only — this tab carries no volumes or dollars.', height=52)
    b.blank()

    hdr = ['Code system', 'Code', 'Meaning (display description, verbatim '
           'from repo refdata)', 'Where it appears',
           'IFT relevance', 'Machine-readable repo source (extraction)',
           'Authority (citation)', 'Basis']

    def vrow(system, code, meaning, where, why, src, cite, basis='GOV',
             kind='src'):
        b.row([(system, 'text'), (code, 'label'), (meaning, kind),
               (where, 'text'), (why, 'text'), (src, 'note'),
               (cite, 'note'), (basis, 'note')],
              wrap=True, height=max(_h(why, 46), _h(meaning, 42)))
        return b.r

    v0 = None

    # A. Place of service
    b.banner('A. Place of Service (CMS POS code set) — professional claims')
    b.headers(hdr)
    v0 = b.r + 1
    vrow('CMS Place of Service', '41', rd.POS_NAMES['41'],
         'CMS-1500 / 837P professional claim, item 24B — the POS every '
         'ground ambulance supplier line carries',
         'The professional-claim fingerprint of ground ambulance: filter '
         'POS 41 to isolate land-ambulance lines in Part B claims data',
         'rcm_mc/npi_cleaner/refdata.py::POS_NAMES["41"]',
         'CMS Place of Service Code Set (maintained by CMS; HIPAA-adopted '
         'code set)')
    vrow('CMS Place of Service', '42', rd.POS_NAMES['42'],
         'CMS-1500 / 837P professional claim, item 24B',
         'Separates air/water ambulance lines from the ground book — the '
         'boundary of the ground-IFT scope used throughout this workbook',
         'rcm_mc/npi_cleaner/refdata.py::POS_NAMES["42"]',
         'CMS Place of Service Code Set')

    # B. Revenue centers
    b.blank()
    b.banner('B. UB-04 revenue centers (NUBC) — institutional claims')
    b.headers(hdr)
    vrow('UB-04 revenue center', '0540-0549',
         'Ambulance (category name for the full 054x range, verbatim from '
         'the repo range table (540, 549, "Ambulance"))',
         'UB-04 / 837I institutional claim, FL 42 revenue code',
         'How HOSPITAL-BASED ambulance activity shows up: '
         'institutionally-billed transports post to 054x revenue centers, '
         'not to a supplier claim — the reason supplier-file counts '
         'undercount total Medicare transports (see the reconciliation '
         'note on Service_Level_Economics)',
         'rcm_mc/npi_cleaner/refdata.py::REVENUE_CATEGORIES (range '
         '540-549); lookup revenue_category()',
         'NUBC UB-04 Data Specifications (National Uniform Billing '
         'Committee, AHA); HIPAA institutional claim code set',
         basis='GOV')

    # C. Condition codes
    b.blank()
    b.banner('C. UB-04 condition codes (NUBC) — FL 18-28')
    b.headers(hdr)
    vrow('UB-04 condition code', 'AK', rd.CONDITION_CODES['AK'],
         'UB-04 FL 18-28 on institutional ambulance claims',
         'Attests that AIR ambulance was medically required — the '
         'ground/air boundary marker on institutional claims',
         'rcm_mc/npi_cleaner/refdata.py::CONDITION_CODES["AK"]',
         'NUBC UB-04 Data Specifications')
    vrow('UB-04 condition code', 'AM', rd.CONDITION_CODES['AM'],
         'UB-04 FL 18-28',
         'Marks non-emergency medically necessary stretcher transport — '
         'directly the scheduled non-emergent IFT segment',
         'rcm_mc/npi_cleaner/refdata.py::CONDITION_CODES["AM"]',
         'NUBC UB-04 Data Specifications')
    vrow('UB-04 condition code', 'B2', rd.CONDITION_CODES['B2'],
         'UB-04 FL 18-28 on CAH claims',
         'Critical access hospital ambulance attestation — CAHs may bill '
         'ambulance under special rules when the nearest supplier is '
         'distant (35-mile rule); a rural-market structure marker',
         'rcm_mc/npi_cleaner/refdata.py::CONDITION_CODES["B2"]',
         'NUBC UB-04 Data Specifications')

    # D. Value codes
    b.blank()
    b.banner('D. UB-04 value codes (NUBC) — FL 39-41')
    b.headers(hdr)
    vrow('UB-04 value code', '32', rd.VALUE_CODES['32'],
         'UB-04 FL 39-41',
         'Flags multiple-patient ambulance transports (payment is prorated '
         'across patients on one trip). Disambiguation: this is the UB-04 '
         'VALUE code 32; the claim-line MODIFIER 32 in panel F below means '
         '"Mandated services" — the two are unrelated despite sharing the '
         'number',
         'rcm_mc/npi_cleaner/refdata.py::VALUE_CODES["32"]',
         'NUBC UB-04 Data Specifications')

    # E. Remittance
    b.blank()
    b.banner('E. Remittance advice remark codes (X12 RARC) — 835 remits')
    b.headers(hdr)
    vrow('RARC (remittance remark)', 'N114', rd.RARC_DESCRIPTIONS['N114'],
         'X12 835 electronic remittance advice, service-line remarks',
         'The ambulance-fee-schedule transition marker: N114 flags claims '
         'paid on the AFS blended rate — a historical payment-mechanics '
         'trace in older remittance data',
         'rcm_mc/npi_cleaner/refdata.py::RARC_DESCRIPTIONS["N114"]',
         'X12 Remittance Advice Remark Codes (maintained by X12, '
         'distributed via CMS/WPC)')

    # F. Modifiers
    b.blank()
    b.banner('F. Claim-line modifiers — ambulance-billing relevant subset '
             'in repo refdata')
    b.headers(hdr)
    vrow('Claim-line modifier', '32', rd.MODIFIER_MEANINGS['32'],
         'CMS-1500 / 837P line-level modifier',
         'Mandated services (e.g., court-ordered or payer-mandated '
         'transport). NOTE: the gap-inventory described modifier 32 as '
         '"multiple-patient transport" — that meaning belongs to UB-04 '
         'VALUE code 32 (panel D); the repo refdata meanings are carried '
         'verbatim here',
         'rcm_mc/npi_cleaner/refdata.py::MODIFIER_MEANINGS["32"]',
         'CPT Appendix A (AMA) / CMS claim-line modifier set')
    vrow('Claim-line modifier', 'GA', rd.MODIFIER_MEANINGS['GA'],
         'CMS-1500 / 837P line-level modifier',
         'ABN on file — the supplier warned the beneficiary the transport '
         'may not be covered; pairs with medical-necessity denials (42 CFR '
         '410.40) in the non-emergent book',
         'rcm_mc/npi_cleaner/refdata.py::MODIFIER_MEANINGS["GA"]',
         'CMS HCPCS Level II modifier set')
    vrow('Claim-line modifier', 'GY', rd.MODIFIER_MEANINGS['GY'],
         'CMS-1500 / 837P line-level modifier',
         'Statutorily excluded item/service — used e.g. with A0888 '
         '(non-covered ambulance mileage) to obtain a denial for secondary '
         'billing; part of the ambulance denial mechanics',
         'rcm_mc/npi_cleaner/refdata.py::MODIFIER_MEANINGS["GY"]',
         'CMS HCPCS Level II modifier set')
    b.note('Ambulance origin/destination modifier pairs (first position = '
           'origin, second = destination; e.g. H hospital, N SNF, E '
           'residential facility, D diagnostic site) live on the v2.7 '
           'Code_Crosswalks tab and are not duplicated here; repo refdata '
           'does not carry that set.', height=22)

    # G. Taxonomies
    b.blank()
    b.banner('G. NUCC provider taxonomies — Transportation (ambulance + '
             'NEMT boundary)')
    b.headers(hdr)
    tax_rows = [
        ('341600000X', rd.TAXONOMY_SPECIALTIES['341600000X'] +
         ' (parent transportation code)',
         'rcm_mc/npi_cleaner/refdata.py::TAXONOMY_SPECIALTIES + '
         'ift_connectors._AMBULANCE_TAXONOMIES',
         'The NPPES/PECOS supplier fingerprint: ambulance organizations '
         'enumerate under 3416* — the fragmentation denominator behind the '
         'supply tabs'),
        ('3416L0300X', 'Ambulance — Land Transport',
         'rcm_mc/market_reports/ift_connectors.py::_AMBULANCE_TAXONOMIES',
         'The IFT-relevant modality: ground/land ambulance suppliers'),
        ('3416A0800X', 'Ambulance — Air Transport',
         'rcm_mc/market_reports/ift_connectors.py::_AMBULANCE_TAXONOMIES',
         'Air ambulance — outside the ground-IFT scope of this workbook '
         '(and covered by the No Surprises Act, unlike ground)'),
        ('3416S0300X', 'Ambulance — Water Transport',
         'rcm_mc/market_reports/ift_connectors.py::_AMBULANCE_TAXONOMIES',
         'Water ambulance — de-minimis modality, carried for completeness'),
        ('343900000X', 'Non-emergency Medical Transport (VAN)',
         'rcm_mc/market_reports/ift_connectors.py::_NEMT_TAXONOMIES',
         'NEMT van suppliers — the ADJACENT Medicaid benefit (42 CFR '
         '431.53), deliberately EXCLUDED from the IFT TAM; enumerated here '
         'to make the boundary auditable'),
        ('343800000X', 'Secured Medical Transport (VAN)',
         'rcm_mc/market_reports/ift_connectors.py::_NEMT_TAXONOMIES',
         'Secured (behavioral-health) van transport — NEMT-side boundary '
         'code, excluded from the ambulance market'),
    ]
    for code, meaning, src, why in tax_rows:
        vrow('NUCC provider taxonomy', code, meaning,
             'NPPES enumeration record (primary/secondary taxonomy); PECOS '
             'enrollment; 837 claim rendering-provider taxonomy',
             why, src,
             'NUCC Health Care Provider Taxonomy code set v24.1, '
             'Transportation section')

    # H. MAC jurisdictions
    b.blank()
    b.banner('H. Medicare Administrative Contractor (MAC) A/B '
             'jurisdictions — who adjudicates ambulance claims (repo seed '
             'table, read at build time)')
    b.headers(['Contractor ID (seed)', 'Jurisdiction', 'Contractor name',
               'States covered', 'Notes (verbatim from seed)',
               'Machine-readable repo source', 'Authority (citation)',
               'Basis'])
    m0 = b.r + 1
    for r in mac_rows:
        b.row([
            (r['contractor_id'], 'label'),
            (r['jurisdiction'], 'src'),
            (r['contractor_name'], 'src'),
            (r['jurisdiction_states'], 'src'),
            (r['notes'], 'note'),
            ('rcm_mc/npi_cleaner/vendor_v49/npi_recovery/reference/'
             'mac_jurisdictions_seed.csv', 'note'),
            ('CMS A/B MAC jurisdiction map ("Who are the MACs", cms.gov)',
             'note'),
            ('GOV (seed)', 'note'),
        ], wrap=True, height=_h(r['notes'], 40))
    m1 = b.r
    b.row([('A/B jurisdictions in seed (live formula)', 'label'),
           (f'=SUMPRODUCT(--(D{m0}:D{m1}<>"HHH"))', 'fml', lib.FMT_INT),
           ('+ 1 national HHH (home health & hospice) MAC row', 'note'),
           None, None, None, None, ('DERIVED', 'note')])
    r_mac = b.r
    v1 = m1

    b.blank()
    b.note('Why MACs matter for IFT: ambulance LCDs (e.g. L35162) and '
           'medical-review behavior vary by MAC jurisdiction, so '
           'denial-risk exposure is jurisdiction-specific; the RSNAT prior-'
           'authorization model also rolled out MAC-by-MAC before going '
           'nationwide. The seed table is a vendored reference extract — '
           're-verify against the live CMS MAC page before circulating '
           'jurisdiction-critical analysis (contractor consolidations '
           'happen).', height=32)
    b.note('Basis discipline: every meaning string is carried VERBATIM from '
           'the repo machine-readable table named in the extraction column '
           '(display descriptions abbreviated by the repo module, not '
           'payer-contract language). POS/RARC/HCPCS-modifier sets are '
           'CMS-maintained or CMS-distributed; UB-04 codes are NUBC (AHA) '
           'and NUCC taxonomy is the NUCC committee — all HIPAA-adopted '
           'public code sets, chip GOV.', height=30)
    b.note(f'Extraction: rcm_mc/npi_cleaner/refdata.py (POS_NAMES, '
           f'REVENUE_CATEGORIES, CONDITION_CODES, VALUE_CODES, '
           f'RARC_DESCRIPTIONS, MODIFIER_MEANINGS, TAXONOMY_SPECIALTIES) + '
           f'ift_connectors taxonomy constants + MAC seed CSV — read at '
           f'build time, {accessed}.')

    n_vocab = 2 + 1 + 3 + 1 + 1 + 3 + 6  # panels A-G code rows
    facts += [
        {'metric': 'Ambulance/IFT code-vocabulary rows carried (POS, '
                   'revenue, condition, value, RARC, modifier, taxonomy)',
         'year': 'current code sets', 'value': n_vocab, 'unit': 'codes',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['refdata_vocab', 'nucc_taxonomy'],
         'locator': 'count of code rows in panels A-G (17)',
         'lives_on': 'Code_Vocabulary',
         'cross_check': '2+1+3+1+1+3+6 = 17'},
        {'metric': 'NUCC ambulance taxonomies (3416*)', 'year': 'v24.1',
         'value': 4, 'unit': 'codes', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['nucc_taxonomy', 'ift_connectors_probes'],
         'locator': 'NUCC Transportation section: 341600000X + '
                    'land/air/water children; ift_connectors.'
                    '_AMBULANCE_TAXONOMIES',
         'lives_on': 'Code_Vocabulary',
         'cross_check': 'NPPES live search accepts the text description '
                        '"Ambulance" (codes rejected as filters)'},
        {'metric': 'NUCC NEMT-boundary taxonomies (3439*/3438*)',
         'year': 'v24.1', 'value': 2, 'unit': 'codes', 'basis': 'GOV',
         'tier': 'B', 'source_keys': ['nucc_taxonomy',
                                      'ift_connectors_probes'],
         'locator': '343900000X NEMT van + 343800000X secured transport; '
                    'ift_connectors._NEMT_TAXONOMIES',
         'lives_on': 'Code_Vocabulary',
         'cross_check': 'NEMT excluded from IFT TAM throughout workbook'},
        {'metric': 'UB-04 revenue-center codes reserved for ambulance',
         'year': 'current NUBC set', 'value': '0540-0549 (10 codes)',
         'unit': 'code range', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['nubc_ub04', 'refdata_vocab'],
         'locator': 'REVENUE_CATEGORIES range (540, 549, "Ambulance")',
         'lives_on': 'Code_Vocabulary',
         'cross_check': 'revenue_category("0540")=="Ambulance" verified at '
                        'build'},
        {'metric': 'MAC A/B jurisdictions in the repo seed table',
         'year': 'seed (re-verify)',
         'value_ref': f'Code_Vocabulary!B{r_mac}',
         'unit': 'jurisdictions', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['cms_mac_jurisdictions'],
         'locator': 'live SUMPRODUCT over seed rows excluding the HHH '
                    'national row (13 rows total)',
         'lives_on': 'Code_Vocabulary',
         'cross_check': '12 A/B jurisdictions + 1 HHH row'},
    ]
    return {'v0': v0, 'v1': v1}


# ══════════════════════════════════════════════════════════════════════════
# Tab 3 — KPI_Dictionary
# ══════════════════════════════════════════════════════════════════════════

def _build_kpis(wb, lib, kpis, accessed, facts):
    ws = wb.create_sheet('KPI_Dictionary')
    b = lib.SheetBuilder(
        ws, 7, col_widths=[26, 34, 58, 34, 24, 52, 13],
        tab_color=NAVY)
    b.title('KPI dictionary — how interfacility transport performance is '
            'measured (definitions framework)')
    b.subtitle(
        'The question: which metrics measure an IFT operation, how is each '
        'computed, from which system, and who owns it? FRAMEWORK '
        'DEFINITIONS TAB — this is a template metric dictionary carried '
        'verbatim from the repo research module (AUTHORED_SECTIONS "kpis"); '
        'it contains ZERO benchmark values, targets or percentiles, because '
        'the source module publishes none ("a template dictionary, not '
        'benchmarked values"). Any number you expect here would be '
        'invented — see Excluded_Not_Sourced for what it would take to add '
        'benchmarks.', height=52)
    b.blank()

    # A. 32 tier definitions
    tiers = [s for s in kpis['subsections'] if s['kind'] == 'bullets']
    n_tier_defs = sum(len(s['bullets']) for s in tiers)
    b.banner(f'A. Metric definitions by KPI tier — {len(tiers)} tiers, '
             f'{n_tier_defs} metric definitions (verbatim)')
    b.headers(['KPI tier', 'Metric', 'Definition — what it measures and why',
               '', '', 'Tier source frame (verbatim from module)', 'Basis'])
    t0 = b.r + 1
    for s in tiers:
        first = True
        for bl in s['bullets']:
            name, _, defn = bl.partition(' — ')
            b.row([
                (s['heading'] if first else '', 'label'),
                (name, 'src'),
                (defn, 'text'),
                None, None,
                (s.get('source', '') if first else '', 'note'),
                ('FRAMEWORK', 'note'),
            ], wrap=True, height=_h(defn, 62))
            first = False
    t1 = b.r

    # B. worked dictionary
    worked = [s for s in kpis['subsections']
              if s['kind'] == 'table' and 'dictionary' in s['heading'].lower()
              ][0]
    b.blank()
    b.banner(f'B. {worked["heading"]} — {len(worked["rows"])} worked '
             f'metrics (metric / definition / formula / data source / '
             f'owner / why)')
    b.headers(['Metric', 'Definition', 'Formula (verbatim)', 'Data source',
               'Owner', 'Why it matters', 'Basis'])
    w0 = b.r + 1
    for row in worked['rows']:
        metric, defn, formula, dsrc, owner, why = row
        b.row([
            (metric, 'label'), (defn, 'text'), (formula, 'src'),
            (dsrc, 'text'), (owner, 'text'), (why, 'text'),
            ('FRAMEWORK', 'note'),
        ], wrap=True, height=max(_h(defn, 36), _h(why, 56), _h(formula, 60)))
    w1 = b.r

    # C. stakeholder scorecard
    score = [s for s in kpis['subsections']
             if s['kind'] == 'table' and 'stakeholder' in
             s['heading'].lower()][0]
    b.blank()
    b.banner(f'C. {score["heading"]} — {len(score["rows"])} stakeholder '
             f'scorecards')
    b.headers(['Stakeholder', 'Core objective', 'Headline KPIs', '', '',
               'Decision it informs', 'Basis'])
    s0 = b.r + 1
    for row in score['rows']:
        stakeholder, objective, kpi_list, decision = row
        b.row([
            (stakeholder, 'label'), (objective, 'text'), (kpi_list, 'src'),
            None, None, (decision, 'text'), ('FRAMEWORK', 'note'),
        ], wrap=True, height=max(_h(kpi_list, 62), _h(decision, 56)))
    s1 = b.r

    b.blank()
    b.row([('Definition counts (live formulas)', 'label'), None,
           (f'=COUNTA(B{t0}:B{t1})&" tier metric definitions + "'
            f'&COUNTA(A{w0}:A{w1})&" worked metrics + "'
            f'&COUNTA(A{s0}:A{s1})&" stakeholder scorecards"', 'fml'),
           None, None, None, ('DERIVED', 'note')])
    b.note('Why these definitions are legitimately carried on a sourced '
           'workbook: they are an analytic framework (measurement '
           'DEFINITIONS with stated formulas and data systems), not claimed '
           'market observations — there are no numbers to source. The '
           'module frames the hierarchy: provider-controlled availability/'
           'speed/workflow metrics roll up to what the ordering hospital '
           'buys — bed capacity, throughput, and cost (transport-'
           'attributable discharge-delay and ED-boarding hours are the '
           'bridge metrics).', height=32)
    b.note('Measurement-systems note (from the definitions themselves): '
           'speed/reliability metrics read off CAD/AVL timestamps; workflow '
           'metrics off telephony and transfer-center booking logs; '
           'financial-impact metrics off EHR flow milestones plus finance '
           'systems — i.e., auditing an operator against this dictionary is '
           'a systems-access diligence request, not a public-data pull.',
           height=30)
    b.note(f'Extraction: rcm_mc/market_reports/ift_research_data.py '
           f'AUTHORED_SECTIONS section id="kpis" (7 subsections: 5 bullet '
           f'tiers, 2 tables), read at build time {accessed}. Text carried '
           f'verbatim; only the "Name — definition" split is applied to '
           f'bullets.')

    facts += [
        {'metric': 'Worked KPI definitions (metric/definition/formula/'
                   'source/owner/why)', 'year': 'n/a',
         'value': len(worked['rows']), 'unit': 'metrics',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_research_authored'],
         'locator': 'AUTHORED_SECTIONS["kpis"] "Sample KPI dictionary '
                    '(worked metrics)" table, 12 rows x 6 cols',
         'lives_on': 'KPI_Dictionary',
         'cross_check': 'COUNTA formula on-sheet'},
        {'metric': 'Tier metric definitions across 5 KPI tiers',
         'year': 'n/a', 'value': n_tier_defs, 'unit': 'definitions',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_research_authored'],
         'locator': 'AUTHORED_SECTIONS["kpis"] bullet tiers: access 6, '
                    'speed 7, workflow 6, clinical 6, financial 7',
         'lives_on': 'KPI_Dictionary',
         'cross_check': '6+7+6+6+7 = 32'},
        {'metric': 'Stakeholder scorecards (function-level KPI '
                   'recommendations)', 'year': 'n/a',
         'value': len(score['rows']), 'unit': 'scorecards',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_research_authored'],
         'locator': 'AUTHORED_SECTIONS["kpis"] "Recommended metrics by '
                    'stakeholder" table, 5 rows x 4 cols',
         'lives_on': 'KPI_Dictionary', 'cross_check': ''},
        {'metric': 'Benchmark values published on this tab', 'year': 'n/a',
         'value': 0, 'unit': 'benchmarks', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_research_authored'],
         'locator': 'source module states "template dictionary, not '
                    'benchmarked values" — carried as-is, nothing invented',
         'lives_on': 'KPI_Dictionary',
         'cross_check': 'Excluded_Not_Sourced records what would make '
                        'benchmarks citable'},
    ]
    return {}


# ══════════════════════════════════════════════════════════════════════════
# Tab 4 — Regulatory_Register
# ══════════════════════════════════════════════════════════════════════════

def _chip(basis_text):
    t = basis_text.upper()
    if 'GOV' in t and 'FRAMEWORK' in t:
        return 'GOV / FWK'
    if 'GOV' in t:
        return 'GOV'
    if 'FRAMEWORK' in t:
        return 'FRAMEWORK'
    return basis_text


def _build_regulatory(wb, lib, reg, slv, accessed, facts):
    ws = wb.create_sheet('Regulatory_Register')
    b = lib.SheetBuilder(
        ws, 7, col_widths=[30, 60, 26, 54, 42, 40, 12],
        tab_color=NAVY)
    b.title('Regulatory register — the statute, regulation and manual stack '
            'that binds interfacility transport')
    b.subtitle(
        'The question: which rules govern who may operate, what gets '
        'covered, and how claims survive review — with the exact citation '
        'for every row? Panel A carries the 11-row GOV regulatory-'
        'requirements table verbatim from the repo research module; Panel B '
        'carries the four service-level definitions with VERBATIM 42 CFR '
        '414.605 quotes; Panels C/D carry the 19 level-determination edge '
        'cases and 12 misconception corrections from the 53-source '
        'ift_service_levels module (verified July 2026). Qualitative '
        'regulatory evidence — every row cites statute, CFR, manual '
        'section, scope model, or state code.', height=52)
    b.blank()

    # A. 11 GOV requirements
    req = reg['subsections'][0]
    b.banner(f'A. {req["heading"]} — {len(req["rows"])} requirement rows '
             f'(basis GOV; carried verbatim)')
    b.headers(['Area', 'Requirement', 'Who it binds', 'Why it matters',
               'Row basis + citation (verbatim from module)',
               'Primary authority', 'Basis'])
    cite_map = {
        'State EMS licensing': 'State EMS statutes/agencies (50-state '
                               'patchwork; no federal license)',
        'Staffing rules': 'State scope-of-practice rules; 42 CFR 410.41 '
                          '(vehicle & crew)',
        'Medicare ambulance medical necessity': '42 CFR 410.40; Medicare '
                                                'Benefit Policy Manual '
                                                'Ch. 10 (Pub. 100-02)',
        'Physician Certification Statement': '42 CFR 410.40(e)',
        'RSNAT prior authorization': 'CMS RSNAT prior-authorization model; '
                                     '42 U.S.C. 1395m(l)',
        'EMTALA': '42 U.S.C. 1395dd; 42 CFR 489.24(e)',
        'Medicaid NEMT': '42 CFR 431.53; 42 CFR 440.170',
        'No Surprises Act': 'No Surprises Act (CAA 2021), Division BB',
        'HIPAA': '45 CFR Parts 160/164',
        'Interstate transport': 'State licensure + reciprocity provisions',
        'Behavioral-health transport': 'State statutes (secure transport, '
                                       'custody, restraint rules)',
    }
    a0 = b.r + 1
    for row in req['rows']:
        area, requirement, who, why, basis = row
        auth = next((v for k, v in cite_map.items() if area.startswith(k)),
                    basis)
        b.row([
            (area, 'label'), (requirement, 'src'), (who, 'text'),
            (why, 'text'), (basis, 'note'), (auth, 'note'),
            (_chip(basis), 'note'),
        ], wrap=True, height=max(_h(requirement, 58), _h(why, 52)))
    a1 = b.r
    b.note('Full statutory citation block carried by the source table '
           '(verbatim): ' + req.get('source', ''), height=44)

    # B. service-level CFR definitions
    b.blank()
    b.banner('B. Service-level regulatory definitions — VERBATIM 42 CFR '
             '414.605 quotes (BLS / ALS1 / ALS2 / SCT), from '
             'ift_service_levels.service_levels()')
    b.headers(['Service level', 'HCPCS codes (code · label · RVU)',
               'Verbatim regulatory definition (quotation)',
               'Plain-English definition (module text)',
               'Sources cited by the definition fact', '', 'Basis'])
    b0 = b.r + 1
    for lv in slv['levels']:
        hc = '; '.join(f'{c} — {lbl} (RVU {rvu})' for c, lbl, rvu in lv.hcpcs)
        d = lv.definition
        srcs = ' · '.join(s.label for s in d.srcs)
        b.row([
            (f'{lv.name} ({lv.key})', 'label'),
            (hc, 'src'),
            ('"' + d.quote + '"', 'src'),
            (d.text, 'text'),
            (srcs, 'note'),
            None,
            (d.basis, 'note'),
        ], wrap=True, height=max(_h(d.quote, 58), _h(d.text, 52), 60))
    b1 = b.r
    b.note('Quotes are verbatim regulatory text as carried by the repo '
           'module (42 CFR 414.605 definitions; ellipses in the original '
           'excerpts). The ALS2 definition operates through counting rules '
           '(3+ IV medication administrations or one of eight named '
           'procedures — blood transfusion added as procedure #8 effective '
           'CY2025, 89 FR 98559); SCT requires care beyond the paramedic '
           'scope.', height=30)

    # C. edge cases
    b.blank()
    ec = slv['edge_cases']
    n_gov = sum(1 for e in ec if e.basis == 'GOV')
    b.banner(f'C. Level-determination edge cases — {len(ec)} scenarios '
             f'({n_gov} GOV, {len(ec) - n_gov} FRAMEWORK classification '
             f'logic over cited rules), from ift_service_levels.edge_cases()')
    b.headers(['Scenario', 'Likely level', 'Determinant (what decides it)',
               'Ambiguity / caveat', 'Sources', '', 'Basis'])
    c0 = b.r + 1
    for e in ec:
        srcs = ' · '.join(s.label for s in e.srcs)
        b.row([
            (e.scenario, 'label'), (e.likely_level, 'src'),
            (e.determinant, 'text'), (e.ambiguity, 'text'),
            (srcs, 'note'), None, (e.basis, 'note'),
        ], wrap=True, height=max(_h(e.determinant, 52), _h(e.ambiguity, 52),
                                 _h(srcs, 40)))
    c1 = b.r

    # D. misconceptions
    b.blank()
    mc = slv['misconceptions']
    b.banner(f'D. Misconceptions corrected — {len(mc)} myth/reality rows, '
             f'each sourced, from ift_service_levels.misconceptions()')
    b.headers(['Myth', 'Reality (sourced correction)', '', '', 'Sources',
               '', 'Basis'])
    d0 = b.r + 1
    for m in mc:
        srcs = ' · '.join(s.label for s in m.srcs)
        b.row([
            (m.myth, 'label'), (m.reality, 'src'), None, None,
            (srcs, 'note'), None, ('GOV-cited', 'note'),
        ], wrap=True, height=max(_h(m.reality, 58), _h(srcs, 40)))
    d1 = b.r

    # E. barrier synthesis (FRAMEWORK, labeled)
    b.blank()
    bar = reg['subsections'][1]
    b.banner(f'E. {bar["heading"]} — {len(bar["bullets"])} synthesis rows '
             f'(FRAMEWORK — analytic read over the GOV rows above, no '
             f'numbers)')
    b.headers(['Barrier', 'Synthesis (verbatim)', '', '', '', '', 'Basis'])
    for bl in bar['bullets']:
        name, _, rest = bl.partition(':')
        b.row([(name.strip(), 'label'), (rest.strip(), 'text'), None, None,
               None, None, ('FRAMEWORK', 'note')],
              wrap=True, height=_h(rest, 58))

    b.blank()
    b.row([('Register counts (live formulas)', 'label'),
           (f'=COUNTA(A{a0}:A{a1})&" requirement rows + "'
            f'&COUNTA(A{b0}:A{b1})&" CFR level definitions + "'
            f'&COUNTA(A{c0}:A{c1})&" edge cases + "'
            f'&COUNTA(A{d0}:A{d1})&" misconceptions"', 'fml'),
           None, None, None, None, ('DERIVED', 'note')])
    b.note('Module honesty audit carried with the rows: ift_service_levels '
           'reports ' + ', '.join(f'{k} {v}' for k, v in
                                  sorted(slv['n_by_basis'].items())) +
           ' facts and has_no_illustrative() == ' +
           str(slv['no_illustrative']) + ' — 53 unique sources, every one '
           'URL-linked, verified July 2026. FRAMEWORK rows here are '
           'classification logic over cited rules (no invented quantities), '
           'distinct from the renamed-ILLUSTRATIVE "FRAMEWORK" chips in the '
           'moat/competitive/insourcing modules, which are excluded from '
           'this workbook.', height=40)
    b.note('Tier note: all rows are tier B — carried from repo modules '
           'citing the named statutes/manuals; the underlying documents '
           'were not reopened for this build. The eCFR/statute URLs live in '
           'the module bibliography and the Source_Register.', height=22)
    b.note(f'Extraction: AUTHORED_SECTIONS section id="regulatory" (Panel A '
           f'+ E) and ift_service_levels.service_levels() / edge_cases() / '
           f'misconceptions() (Panels B-D) — run at build time {accessed}.')

    facts += [
        {'metric': 'Regulatory requirement rows binding IFT (statute-cited)',
         'year': 'current law', 'value': len(req['rows']), 'unit': 'rows',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_research_authored', 'cfr_410_40',
                         'usc_1395dd', 'medicaid_nemt', 'nsa_caa_2021',
                         'hipaa_45cfr', 'usc_1395m_l'],
         'locator': 'AUTHORED_SECTIONS["regulatory"] table, 11 rows x 5 '
                    'cols, per-row GOV basis',
         'lives_on': 'Regulatory_Register',
         'cross_check': 'COUNTA formula on-sheet'},
        {'metric': 'Service levels with verbatim 42 CFR 414.605 definitions',
         'year': 'current (2026)', 'value': 4, 'unit': 'levels',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_service_levels_mod', 'cfr_414_605'],
         'locator': 'service_levels() BLS/ALS1/ALS2/SCT definition facts, '
                    'each with quote + 3 sources',
         'lives_on': 'Regulatory_Register',
         'cross_check': 'ALS2 blood-transfusion trigger effective CY2025 '
                        '(89 FR 98559) noted'},
        {'metric': 'Level-determination edge-case scenarios',
         'year': 'current rules', 'value': len(slv['edge_cases']),
         'unit': 'scenarios', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_service_levels_mod', 'scope_model_2019',
                         'cfr_414_605'],
         'locator': 'edge_cases(): 19 rows, 13 GOV / 6 FRAMEWORK, each '
                    'citing regs/scope model',
         'lives_on': 'Regulatory_Register', 'cross_check': ''},
        {'metric': 'Misconceptions corrected with sourced rebuttals',
         'year': 'current rules', 'value': len(slv['misconceptions']),
         'unit': 'rows', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_service_levels_mod'],
         'locator': 'misconceptions(): 12 myth/reality rows, each with '
                    'source labels',
         'lives_on': 'Regulatory_Register',
         'cross_check': 'includes MedPOP CY2024-anchored corrections '
                        '(30.7% BLS-NE share; SCT 0.7%)'},
        {'metric': 'GOV facts in the underlying service-levels module '
                   '(honesty audit)', 'year': 'verified Jul 2026',
         'value': slv['n_by_basis'].get('GOV', 0), 'unit': 'facts',
         'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['ift_service_levels_mod'],
         'locator': 'ift_service_levels.n_by_basis(); '
                    'has_no_illustrative()==True; 53 URL-linked sources',
         'lives_on': 'Regulatory_Register',
         'cross_check': 'module summary() reports 109 facts total'},
    ]
    return {}


# ══════════════════════════════════════════════════════════════════════════
# build()
# ══════════════════════════════════════════════════════════════════════════

def build(wb, ctx):
    lib = ctx['lib']
    repo = ctx['repo']
    accessed = ctx['accessed']
    facts, notes = [], []

    cat, reg_rows = _load_estate()
    probes, summary = _load_probes()
    man, fams = _load_manifest(ctx['cache'])
    rd = _load_refdata()
    mac_rows = _load_mac_seed(repo)
    authored = _load_authored()
    slv = _load_service_levels()

    _build_estate_map(wb, lib, cat, reg_rows, probes, summary, man, fams,
                      accessed, facts)
    _build_vocab(wb, lib, rd, mac_rows, accessed, facts)
    _build_kpis(wb, lib, authored['kpis'], accessed, facts)
    _build_regulatory(wb, lib, authored['regulatory'], slv, accessed, facts)

    if len(probes) != 17:
        notes.append(f'ift_connectors.connector_estate_map() returned '
                     f'{len(probes)} probes at build time (design note '
                     f'said 17) — the live count is rendered.')
    notes.append('No ingested estate DB exists (var/connectors absent): '
                 'all probes network-gated; Panel C live pulls are the '
                 'evidence source.')

    sources = [
        {'key': 'connectors_registry',
         'publisher': 'RCM repo (top-level connectors package)',
         'document': 'connectors.registry — 16-connector / 204-dataset '
                     'public-API registry (stdlib vertical-slice '
                     'connectors over federal open-data APIs)',
         'vintage': 'runtime 2026-07-10',
         'locator': 'registry.catalog() + all_registry_rows(); counts '
                    'pinned by connectors/tests/test_estate_invariants.py',
         'url': 'repo:/home/user/RCM/connectors',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'ift_connectors_probes',
         'publisher': 'RCM repo (rcm_mc.market_reports)',
         'document': 'ift_connectors.connector_estate_map() — IFT probe '
                     'registry (18 probes at runtime), FRAMEWORK plumbing '
                     'with GOV fallback citations',
         'vintage': 'runtime 2026-07-10',
         'locator': 'rcm_mc/market_reports/ift_connectors.py (502 lines); '
                    'estate_summary() by_category',
         'url': 'repo:/home/user/RCM/RCM_MC/rcm_mc/market_reports/'
                'ift_connectors.py',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Connector_Estate_Map', 'Code_Vocabulary']},
        {'key': 'ift_v3_pull_manifest',
         'publisher': 'This build (live pulls from federal open-data APIs)',
         'document': 'ift_v3_cache/manifest.json — 164 pull artifacts with '
                     'endpoint, UUID, filters, pages, rows, sha256, UTC '
                     'timestamp',
         'vintage': '2026-07-10 (all pulls)',
         'locator': 'manifest keys mup_national_*/mup_state_*/psps_agg_*/'
                    'qcew_621910_*/marketsat_state/enrollment_*/'
                    'pecos_stats_check/pdc_*',
         'url': 'cache:ift_v3_cache/manifest.json',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'cms_mup_geo_service', 'publisher': 'CMS',
         'document': 'Medicare Physician & Other Practitioners — by '
                     'Geography and Service (ambulance HCPCS slices)',
         'vintage': '2013-2024 (12 annual vintages)',
         'locator': 'data.cms.gov data-api; per-vintage UUIDs in pull '
                    'manifest (2024: 0c75b0b3-b40f-4007-a5ac-f9f2fed95862)',
         'url': 'https://data.cms.gov/provider-summary-by-type-of-service/'
                'medicare-physician-other-practitioners/medicare-physician-'
                'other-practitioners-by-geography-and-service',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'cms_psps', 'publisher': 'CMS',
         'document': 'Physician/Supplier Procedure Summary (PSPS) — '
                     'ambulance HCPCS lines incl. denied services',
         'vintage': '2010-2024 (15 annual vintages)',
         'locator': 'data.cms.gov data-api; per-vintage UUIDs in pull '
                    'manifest (2024: 647c8fa8-5dd6-460d-a2ec-18faf15b3fb2)',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/physiciansupplier-procedure-summary',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'cms_market_saturation', 'publisher': 'CMS',
         'document': 'Market Saturation & Utilization State-County — 3 '
                     'ambulance service types',
         'vintage': '15 rolling reference periods 2020-2025 (in-data)',
         'locator': 'data.cms.gov data-api, UUID 8900b9c5-50b7-43de-9bdd-'
                    '0d7113a8355e',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/market-saturation-utilization',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'cms_monthly_enrollment', 'publisher': 'CMS',
         'document': 'Medicare Monthly Enrollment (state/national x year; '
                     'ESRD beneficiary columns)',
         'vintage': '2013 -> latest (in-data YEAR; pulled 2026-07-10)',
         'locator': 'data.cms.gov data-api, UUID d7fabe1e-d19b-4333-9eff-'
                    'e80e0643f2fd; filters BENE_GEO_LVL + MONTH=Year',
         'url': 'https://data.cms.gov/summary-statistics-on-beneficiary-'
                'enrollment/medicare-and-medicaid-reports/medicare-monthly-'
                'enrollment',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'cms_pecos_enrollment', 'publisher': 'CMS',
         'document': 'Medicare Fee-For-Service Public Provider Enrollment '
                     '(PECOS) — PART B SUPPLIER - AMBULANCE SERVICE '
                     'SUPPLIER',
         'vintage': '2026Q1 snapshot (stats probe 2026-07-10)',
         'locator': 'data.cms.gov data-api /data/stats, UUID 2457ea29-fc82-'
                    '48b0-86ec-3b0755de7515; found_rows=10,465',
         'url': 'https://data.cms.gov/provider-characteristics/medicare-'
                'provider-supplier-enrollment/medicare-fee-for-service-'
                'public-provider-enrollment',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'bls_qcew_621910', 'publisher': 'BLS',
         'document': 'Quarterly Census of Employment and Wages — NAICS '
                     '621910 (Ambulance Services), annual-average CSV '
                     'slices',
         'vintage': '2014-2025 (12 annual files)',
         'locator': 'data.bls.gov/cew/data/api/{year}/a/industry/'
                    '621910.csv; US000 + statewide rows kept',
         'url': 'https://data.bls.gov/cew/data/api/2025/a/industry/'
                '621910.csv',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'cms_pdc_care_compare', 'publisher': 'CMS',
         'document': 'Provider Data Catalog / Care Compare — 7 facility '
                     'general-information files (hospitals xubh-q36u, '
                     'nursing homes 4pq5-n9py, dialysis 23ew-n7w9, IRF '
                     '7t8x-u3ir, LTCH azum-44iv, hospice yc9t-dgbk, home '
                     'health 6jpm-sxkc)',
         'vintage': 'current snapshots, pulled 2026-07-10',
         'locator': 'data.cms.gov/provider-data DKAN datastore query API; '
                    'row counts 5,432 / 14,695 / 7,557 / 1,222 / 311 / '
                    '6,852 / 12,392',
         'url': 'https://data.cms.gov/provider-data/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'cms_dcat_catalog', 'publisher': 'CMS',
         'document': 'data.cms.gov DCAT catalog (data.json) — source of '
                     'truth for dataset vintages and per-release UUIDs',
         'vintage': 'live 2026-07-10 (158 datasets)',
         'locator': 'https://data.cms.gov/data.json; used to resolve every '
                    'per-vintage UUID in the pull manifest',
         'url': 'https://data.cms.gov/data.json',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Connector_Estate_Map']},
        {'key': 'refdata_vocab',
         'publisher': 'CMS / X12 / NUBC (carried via RCM repo refdata)',
         'document': 'Claims reference catalogs — POS code set, UB-04 '
                     'revenue/condition/value codes, RARC, claim-line '
                     'modifiers (static public reference data, '
                     'display-abbreviated)',
         'vintage': 'current code sets (repo vendored)',
         'locator': 'rcm_mc/npi_cleaner/refdata.py — POS_NAMES, '
                    'REVENUE_CATEGORIES, CONDITION_CODES, VALUE_CODES, '
                    'RARC_DESCRIPTIONS, MODIFIER_MEANINGS',
         'url': 'repo:/home/user/RCM/RCM_MC/rcm_mc/npi_cleaner/refdata.py',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Code_Vocabulary']},
        {'key': 'cms_pos_codeset', 'publisher': 'CMS',
         'document': 'Place of Service Code Set (POS 41 ambulance-land, '
                     '42 ambulance-air/water)',
         'vintage': 'current', 'locator': 'CMS POS code set page; codes '
                    '41/42 under transport',
         'url': 'https://www.cms.gov/medicare/coding-billing/place-of-'
                'service-codes/code-sets',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Code_Vocabulary']},
        {'key': 'nubc_ub04', 'publisher': 'NUBC (AHA)',
         'document': 'UB-04 Data Specifications — revenue codes 0540-0549 '
                     '(Ambulance), condition codes AK/AM/B2, value code 32',
         'vintage': 'current UB-04 set',
         'locator': 'FL 42 (revenue), FL 18-28 (condition), FL 39-41 '
                    '(value)',
         'url': 'https://www.nubc.org/',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Code_Vocabulary']},
        {'key': 'x12_rarc', 'publisher': 'X12 / CMS',
         'document': 'Remittance Advice Remark Codes — N114 (ambulance fee '
                     'schedule blended-rate transition)',
         'vintage': 'current RARC list',
         'locator': 'RARC N114, X12 external code list',
         'url': 'https://x12.org/codes/remittance-advice-remark-codes',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Code_Vocabulary']},
        {'key': 'nucc_taxonomy', 'publisher': 'NUCC',
         'document': 'Health Care Provider Taxonomy code set v24.1 — '
                     'Transportation: 341600000X + 3416L0300X/3416A0800X/'
                     '3416S0300X; NEMT 343900000X/343800000X',
         'vintage': 'v24.1',
         'locator': 'Transportation section; constants carried in '
                    'ift_connectors + refdata.TAXONOMY_SPECIALTIES',
         'url': 'https://taxonomy.nucc.org/',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Code_Vocabulary']},
        {'key': 'cms_mac_jurisdictions', 'publisher': 'CMS',
         'document': 'A/B MAC jurisdiction map ("Who are the MACs") — '
                     'carried via repo seed CSV (12 A/B jurisdictions + '
                     'HHH)',
         'vintage': 'repo seed (re-verify against live CMS page)',
         'locator': 'rcm_mc/npi_cleaner/vendor_v49/npi_recovery/reference/'
                    'mac_jurisdictions_seed.csv (13 rows)',
         'url': 'https://www.cms.gov/medicare/coding-billing/medicare-'
                'administrative-contractors-macs/whos-mac',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Code_Vocabulary']},
        {'key': 'ift_research_authored',
         'publisher': 'RCM repo (rcm_mc.market_reports)',
         'document': 'ift_research_data.AUTHORED_SECTIONS — "kpis" '
                     '(FRAMEWORK definitions, zero benchmarks) and '
                     '"regulatory" (11-row GOV table with statutory '
                     'citations)',
         'vintage': 'runtime 2026-07-10',
         'locator': 'sections id="kpis" (7 subsections) and '
                    'id="regulatory" (2 subsections)',
         'url': 'repo:/home/user/RCM/RCM_MC/rcm_mc/market_reports/'
                'ift_research_data.py',
         'tier': 'B', 'accessed': accessed,
         'powers': ['KPI_Dictionary', 'Regulatory_Register']},
        {'key': 'ift_service_levels_mod',
         'publisher': 'RCM repo (rcm_mc.market_reports)',
         'document': 'ift_service_levels — 109-fact / 53-source module '
                     '(service_levels(), edge_cases(), misconceptions()); '
                     'all sources URL-linked, verified July 2026; '
                     'has_no_illustrative()==True',
         'vintage': 'verified July 2026',
         'locator': 'service_levels() definition quotes; edge_cases() 19; '
                    'misconceptions() 12; n_by_basis()',
         'url': 'repo:/home/user/RCM/RCM_MC/rcm_mc/market_reports/'
                'ift_service_levels.py',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Regulatory_Register']},
        {'key': 'cfr_414_605', 'publisher': 'eCFR (GPO/OFR)',
         'document': '42 CFR 414.605 — ambulance services definitions '
                     '(BLS/ALS1/ALS2/SCT verbatim definitions)',
         'vintage': 'current (2026)',
         'locator': 'Title 42, Part 414, Subpart H, §414.605',
         'url': 'https://www.ecfr.gov/current/title-42/chapter-IV/'
                'subchapter-B/part-414/subpart-H/section-414.605',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Regulatory_Register']},
        {'key': 'cfr_410_40', 'publisher': 'eCFR (GPO/OFR)',
         'document': '42 CFR 410.40 — Medicare ambulance coverage, medical '
                     'necessity, PCS (subsection (e))',
         'vintage': 'current (2026)',
         'locator': 'Title 42, Part 410, §410.40',
         'url': 'https://www.ecfr.gov/current/title-42/chapter-IV/'
                'subchapter-B/part-410/subpart-B/section-410.40',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Regulatory_Register']},
        {'key': 'usc_1395dd', 'publisher': 'US Code (OLRC)',
         'document': 'EMTALA — 42 U.S.C. 1395dd (appropriate-transfer '
                     'requirements)',
         'vintage': 'current law',
         'locator': '42 U.S.C. §1395dd(c) transfer requirements',
         'url': 'https://uscode.house.gov/view.xhtml?req=granuleid:USC-'
                'prelim-title42-section1395dd',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Regulatory_Register']},
        {'key': 'usc_1395m_l', 'publisher': 'US Code (OLRC)',
         'document': '42 U.S.C. 1395m(l) — ambulance fee schedule statute '
                     '(incl. (12)-(13) ground add-ons)',
         'vintage': 'current law',
         'locator': '42 U.S.C. §1395m(l)',
         'url': 'https://uscode.house.gov/view.xhtml?req=granuleid:USC-'
                'prelim-title42-section1395m',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Regulatory_Register']},
        {'key': 'medicaid_nemt', 'publisher': 'eCFR (GPO/OFR)',
         'document': '42 CFR 431.53 / 440.170 — Medicaid NEMT assurance '
                     'and definition (separate benefit, IFT boundary)',
         'vintage': 'current (2026)',
         'locator': 'Title 42 §431.53; §440.170(a)',
         'url': 'https://www.ecfr.gov/current/title-42/chapter-IV/'
                'subchapter-C/part-431/subpart-B/section-431.53',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Regulatory_Register']},
        {'key': 'nsa_caa_2021', 'publisher': 'US Congress',
         'document': 'No Surprises Act (Consolidated Appropriations Act, '
                     '2021, Division BB) — ground ambulance excluded from '
                     'balance-billing protections',
         'vintage': 'Pub. L. 116-260 (2020)',
         'locator': 'CAA 2021 Division BB; ground ambulance under GAPB '
                    'advisory-committee study',
         'url': 'https://www.congress.gov/bill/116th-congress/house-bill/'
                '133',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Regulatory_Register']},
        {'key': 'hipaa_45cfr', 'publisher': 'eCFR (GPO/OFR)',
         'document': 'HIPAA privacy/security rules — 45 CFR Parts 160/164',
         'vintage': 'current (2026)',
         'locator': 'Title 45, Parts 160 and 164',
         'url': 'https://www.ecfr.gov/current/title-45/subtitle-A/'
                'subchapter-C',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Regulatory_Register']},
        {'key': 'scope_model_2019', 'publisher': 'NHTSA / NASEMSO',
         'document': 'National EMS Scope of Practice Model 2019 — '
                     'EMT/AEMT/paramedic skill boundaries used by the '
                     'edge-case panel',
         'vintage': '2019 (with 2021 change notices)',
         'locator': 'skill tables by certification level',
         'url': 'https://www.ems.gov/assets/National_EMS_Scope_of_Practice_'
                'Model_2019.pdf',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Regulatory_Register']},
    ]

    excluded = [
        {'figure': 'cms_api_client.DATASET_IDS hardcoded UUID constants',
         'value': 'e.g. provider_utilization_2022 = "8889d81e-...89bf"; '
                  'hospital_general_info = "64f5c2d5-..."',
         'source_label': 'rcm_mc/data_public/cms_api_client.py (ported '
                         'from DrewThomas09/cms_medicare)',
         'why_excluded': 'Stale/unverified: last-character divergence vs '
                         'the estate registry MUP UUID; the hospital UUID '
                         'points at the wrong API family (PDC DKAN, not '
                         'data-api). All v3 pulls resolved UUIDs from the '
                         'live DCAT catalog instead.',
         'what_would_make_citable': 'Re-resolve every constant from '
                                    'data.cms.gov/data.json and pin '
                                    'per-vintage UUIDs with a verification '
                                    'date.'},
        {'figure': 'NPPES API state-level ambulance supplier counts',
         'value': 'e.g. TX "Ambulance" NPI-2 search truncates at the hard '
                  '1,200-result ceiling (>1,200 orgs in TX alone)',
         'source_label': 'NPPES NPI Registry API v2.1 '
                         '(taxonomy_description text search)',
         'why_excluded': 'The API caps at 1,200 results per query '
                         '(200/page, skip<=1000) and rejects taxonomy '
                         'CODES as filters — state counts from it are '
                         'floors/truncations, not counts. Headline '
                         'supplier counts come from PECOS (10,465, '
                         'vendored + live-verified) instead.',
         'what_would_make_citable': 'Build the supplier universe from the '
                                    'NPPES monthly full-replacement '
                                    'dissemination file (~1GB bulk '
                                    'download), which has no result cap.'},
        {'figure': 'Synthetic NPPES verification universe (offline default '
                   'nppes.db)',
         'value': 'any provider counts from an nppes.db built without a '
                  'real monthly dissemination file',
         'source_label': 'RCM_MC/connectors/nppes/synth.py (real headers, '
                         'fake providers)',
         'why_excluded': 'ILLUSTRATIVE by construction — the offline build '
                         'generates synthetic providers for pipeline '
                         'verification; no real NPPES file is staged in '
                         'the repo.',
         'what_would_make_citable': 'Rebuild with --monthly pointing at a '
                                    'real CMS NPPES dissemination file and '
                                    'record its vintage.'},
        {'figure': 'IFT KPI benchmark values (targets, percentiles, '
                   'industry norms) for the KPI_Dictionary metrics',
         'value': 'none published — the tab deliberately carries zero '
                  'benchmark numbers',
         'source_label': 'ift_research_data AUTHORED_SECTIONS "kpis" '
                         '("template dictionary, not benchmarked values")',
         'why_excluded': 'The source module ships definitions and formulas '
                         'only; any benchmark value attached to them would '
                         'be invented. (The one adjacent published figure '
                         '— AIMHI 911 UHU survey mean ~0.51 — is a 911 '
                         'metric with no published IFT consensus, carried '
                         'with re-verify flags on the unit-economics '
                         'evidence, not here.)',
         'what_would_make_citable': 'Published NEMSIS/AIMHI/contract-SLA '
                                    'benchmark tables for IFT metrics, or '
                                    'operator CAD/AVL data via diligence.'},
        {'figure': 'MAC jurisdiction seed vintage',
         'value': '13-row seed CSV carried without a publication date',
         'source_label': 'mac_jurisdictions_seed.csv (npi_cleaner '
                         'vendor_v49 reference)',
         'why_excluded': 'Not excluded from display (it is on '
                         'Code_Vocabulary) but flagged: the seed has no '
                         'vintage stamp, so it is labeled "seed '
                         '(re-verify)" and no jurisdiction-critical claim '
                         'rests on it.',
         'what_would_make_citable': 'Re-verify the 12 A/B jurisdictions '
                                    'against the live CMS "Who are the '
                                    'MACs" page and stamp the access '
                                    'date.'},
    ]

    row_counts = {name: wb[name].max_row for name in wb.sheetnames}
    return {
        'facts': facts,
        'sources': sources,
        'excluded': excluded,
        'meta': {'notes': ' | '.join(notes), 'row_counts': row_counts},
    }
