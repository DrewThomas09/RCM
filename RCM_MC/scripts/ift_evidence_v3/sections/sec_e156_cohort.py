"""E.1 / E.5 / E.6: cohort dossiers, footprint determination, landscape screen.

Three tabs from public records only.

System_Research_Cohort (E.1): one panel per system in the research cohort of
representative multi-hospital health systems operating in the study
footprint, selected for depth - roster size by the PRINTED Cohort_Corridors
Panel A name-match rules (mirrored here in lockstep), HCRIS beds and
inpatient days, ambulance cost-center pointer, corridor demand green-linked
into Cohort_Corridors, ED-timeliness placement pointer, REH participation
scanned from the CMS REH roster (AHCAH PENDING - JS portal), and the Form
990 Part VII Section B top-five-contractor observation (zero transport
matches across the parsed filings; floor stated).

Footprint_Determination (E.5): the subject company's operating-state list
derived from public sources under a PRINTED rule - a state is IN the
footprint when at least one NPPES registered practice location of the 23
estate NPIs exists in it; self-claims without a registration render as
claimed-not-registered rows. Canonical list compared against the
provisional 10-state list used by earlier tabs, differences printed.

Prospect_Landscape (E.6): additional multi-hospital systems in the
footprint, screened by measured transfer demand - hospital name families
(3+ hospitals) in the registered footprint states from the HCRIS roster,
ranked by HSA 2025 corridor volume with the Hub_Spoke_Map thresholds
mirrored for the hub count.
"""

import collections
import csv
import gzip
import json
import math
import os
import re

SHEETS = [
    {'name': 'System_Research_Cohort',
     'question': 'What does the public record measurably establish, system '
                 'by system, about the scale, corridor demand and transport '
                 'sourcing of the nine research-cohort systems?'},
    {'name': 'Footprint_Determination',
     'question': 'Which states is the subject company operating in, by a '
                 'printed public-evidence rule (NPPES registration first), '
                 'and how does the canonical list differ from the '
                 'provisional list earlier tabs used?'},
    {'name': 'Prospect_Landscape',
     'question': 'Which additional multi-hospital systems in the footprint '
                 'carry the largest measured transfer demand, screened from '
                 'public rosters and corridor files?'},
]

HCRIS_GZ = '/home/user/RCM/RCM_MC/rcm_mc/data/hcris.csv.gz'

COHORT_FRAME = ('research cohort of representative multi-hospital health '
                'systems operating in the study footprint, selected for depth')

PROV_FOOT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']
PROV_TABS = ('Market_Share_Panels; Insourcing_Bounds; '
             'HCRIS_Ambulance_CostCenters; County_Whitespace_Screens; '
             'Transfer_Delay_Burden (10-state list); Hub_Spoke_Map '
             '(11-state variant adding WY)')

BREADTH_HUB = 8   # mirrored from Hub_Spoke_Map Panel A


def _norm(n):
    return (n or '').upper().replace('.', '').replace("'", '')


# Printed name-match rules mirrored 1:1 from Cohort_Corridors Panel A
# (system, printed rule, confound, predicate(name_upper, state, city_upper)).
RULES = [
    ('Cleveland Clinic',
     "name contains 'CLEVELAND CLINIC'",
     'Under-match: regional hospitals not carrying the brand string are '
     'missed',
     lambda n, s, c: 'CLEVELAND CLINIC' in n),
    ('Inova',
     "name contains 'INOVA'",
     'Clean match on a distinctive brand',
     lambda n, s, c: 'INOVA' in n),
    ('CommonSpirit / CHI Health',
     "name contains 'CHI HEALTH' or 'COMMONSPIRIT'",
     'Footprint brand only: the NE/IA CHI Health division, not the '
     'national parent',
     lambda n, s, c: 'CHI HEALTH' in n or 'COMMONSPIRIT' in n),
    ('Nebraska Methodist',
     "(name contains 'METHODIST' and state = NE) or name contains "
     "'JENNIE EDMUNDSON'",
     'Flagship-CCN reporting may fold in units; IA METHODIST names '
     'excluded on purpose',
     lambda n, s, c: ('METHODIST' in n and s == 'NE')
     or 'JENNIE EDMUNDSON' in n),
    ('Premier Health (Dayton)',
     "state = OH and name contains 'MIAMI VALLEY HOSPITAL' or "
     "'UPPER VALLEY MEDICAL' or 'ATRIUM MEDICAL'",
     'Corporate brand absent from facility names; renames would silently '
     'drop out',
     lambda n, s, c: s == 'OH' and ('MIAMI VALLEY HOSPITAL' in n
                                    or 'UPPER VALLEY MEDICAL' in n
                                    or 'ATRIUM MEDICAL' in n)),
    ("Saint Luke's Health System (Kansas City)",
     "name (periods and apostrophes stripped) contains 'ST LUKE' or "
     "'SAINT LUKE', state in (MO, KS), city not in (St. Louis, "
     'Chesterfield, Marion)',
     "St. Louis-area St. Luke's is a different system (excluded by city); "
     'net under-match',
     lambda n, s, c: ('ST LUKE' in _norm(n) or 'SAINT LUKE' in n)
     and s in ('MO', 'KS')
     and c not in ('ST. LOUIS', 'SAINT LOUIS', 'CHESTERFIELD', 'MARION')),
    ('Froedtert',
     "name contains 'FROEDTERT'",
     'ThedaCare hospitals (2024 combination) do not carry the string and '
     'are missed',
     lambda n, s, c: 'FROEDTERT' in n),
    ('Baptist Health (KY/IN)',
     "name contains 'BAPTIST HEALTH' and state in (KY, IN)",
     'State filter keeps the KY/IN system; unrelated Baptist systems of '
     'other states excluded',
     lambda n, s, c: 'BAPTIST HEALTH' in n and s in ('KY', 'IN')),
    ('Ascension',
     "name contains 'ASCENSION'",
     'Not-yet-renamed hospitals missed; divested hospitals may persist in '
     'older roster rows',
     lambda n, s, c: 'ASCENSION' in n),
]

# Cohort_Corridors rule name -> cohort_990.json system label
SYS990 = {
    'Cleveland Clinic': 'Cleveland Clinic (OH)',
    'Inova': 'Inova Health System (VA)',
    'CommonSpirit / CHI Health': 'CommonSpirit Health / CHI Health (NE)',
    'Nebraska Methodist': 'Nebraska Methodist Health System (Omaha NE)',
    'Premier Health (Dayton)': 'Premier Health (Dayton OH)',
    "Saint Luke's Health System (Kansas City)":
        "Saint Luke's Health System (Kansas City MO)",
    'Froedtert': 'Froedtert Health (WI)',
    'Baptist Health (KY/IN)': 'Baptist Health (Kentucky/Indiana)',
    'Ascension': 'Ascension (multi-state)',
}

# Name-family grouping rule for the E.6 screen (printed on the tab).
GENERIC_FIRST = {
    'COMMUNITY', 'MEMORIAL', 'REGIONAL', 'GENERAL', 'COUNTY', 'UNIVERSITY',
    'GOOD', 'HOLY', 'SACRED', 'OUR', 'NEW', 'NORTH', 'SOUTH', 'EAST',
    'WEST', 'GREATER', 'GRAND', 'VALLEY', 'TWIN', 'LAKE', 'LAKES', 'MOUNT',
    'MT', 'UNITED', 'FIRST', 'GREAT', 'IOWA', 'OHIO', 'NEBRASKA',
    'MISSOURI', 'KANSAS', 'INDIANA', 'WISCONSIN', 'VIRGINIA', 'COLORADO',
    'SELECT', 'ENCOMPASS', 'KINDRED'}
GENERICISH_FAMS = {
    'MERCY', 'MARY', 'ST MARYS', 'ST LUKES', 'ST VINCENT', 'ST ELIZABETH',
    'ST JOSEPH', 'ST JOSEPHS', 'LUTHERAN', 'GENESIS', 'PRESBYTERIAN',
    'TRINITY', 'GOOD SAMARITAN', 'COMMUNITY HOSPITAL', 'ST FRANCIS'}


def _famkey(name):
    n = re.sub(r'[^A-Z0-9 ]', ' ', _norm(name))
    toks = [t for t in n.split() if t]
    if not toks:
        return None
    if toks[0] == 'THE' and len(toks) > 1:
        toks = toks[1:]
    if toks[0] == 'SAINT':
        toks[0] = 'ST'
    if toks[0] == 'ST' and len(toks) > 1:
        return 'ST ' + toks[1]
    if toks[0] == 'UNIVERSITY' and len(toks) > 2 and toks[1] == 'OF':
        return ' '.join(toks[:3])
    if toks[0] in GENERIC_FIRST and len(toks) > 1:
        return ' '.join(toks[:2])
    return toks[0]


def _acute(ccn):
    """Short-term acute (last four 0001-0879) or CAH (1300-1399) CCNs."""
    t = ccn[2:]
    if not t.isdigit():
        return False
    v = int(t)
    return v <= 879 or 1300 <= v <= 1399


def _pctile(sorted_vals, p):
    k = (len(sorted_vals) - 1) * p
    f, c = math.floor(k), math.ceil(k)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _load_rosters(lib, cache):
    """Latest-year HCRIS row per CCN (with beds/days) + Care Compare roster."""
    hcris = {}
    with gzip.open(HCRIS_GZ, 'rt') as f:
        for row in csv.DictReader(f):
            k = row['ccn']
            if k not in hcris or row['fiscal_year'] > hcris[k]['fy']:
                hcris[k] = {'fy': row['fiscal_year'],
                            'name': (row['name'] or '').upper(),
                            'state': row['state'],
                            'city': (row['city'] or '').upper(),
                            'beds': float(row['beds'] or 0),
                            'days': float(row['total_patient_days'] or 0)}
    pdc = {}
    for r in lib.load_cache(cache, 'pdc2_hospitals'):
        pdc[r['facility_id']] = {
            'name': (r.get('facility_name') or '').upper(),
            'state': r.get('state'),
            'city': (r.get('citytown') or '').upper()}
    return hcris, pdc


def _scan_cohort_panel_b(wb, names):
    """Row number of each system's Cohort_Corridors Panel B row.

    Panel B rows are the only rows where col A equals the system name, col E
    is a numeric (charges) and col F is a formula string - Panel A rows have
    E empty, Panel C rows have a formula in E, Panel D rows have a formula
    in E too. Returns {name: row_number}.
    """
    out = {}
    if 'Cohort_Corridors' not in wb.sheetnames:
        return out
    ws = wb['Cohort_Corridors']
    for row in ws.iter_rows(min_col=1, max_col=6):
        a, e, f = row[0].value, row[4].value, row[5].value
        if (a in names and a not in out
                and isinstance(e, (int, float))
                and isinstance(f, str) and f.startswith('=')):
            out[a] = row[0].row
    return out


def build(wb, ctx):
    lib = ctx['lib']
    cache = ctx['cache']
    scratch = os.path.dirname(cache)
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    # ---------------------------------------------------------------- data
    corr = lib.load_cache(cache, 'hsa_2025_corridors_top15')
    by_ccn = collections.defaultdict(list)
    for r in corr:
        by_ccn[r['provider_id']].append(r)
    hcris, pdc = _load_rosters(lib, cache)

    # per-CCN volume + breadth, national hub bar (mirrored from Hub_Spoke_Map)
    stats = {}
    for ccn, rows in by_ccn.items():
        rows = sorted(rows, key=lambda r: r['rank'])
        tot = sum(r['cases'] for r in rows)
        breadth, cum = 0, 0.0
        if tot > 0:
            for i, r in enumerate(rows, 1):
                cum += r['cases']
                if cum >= 0.8 * tot:
                    breadth = i
                    break
        stats[ccn] = (tot, breadth)
    vols = sorted(t for t, _ in stats.values())
    p90 = _pctile(vols, 0.90)
    hubs = {c for c, (t, b) in stats.items() if t >= p90 and b >= BREADTH_HUB}

    # cohort resolution (mirrored rules, both rosters)
    sys_ccns, rule_meta = {}, {}
    for name, rule, confound, pred in RULES:
        hits = set()
        for src in (hcris, pdc):
            for ccn, d in src.items():
                if pred(d['name'], d['state'], d['city']):
                    hits.add(ccn)
        sys_ccns[name] = hits
        rule_meta[name] = (rule, confound)
    cohort_all = set().union(*sys_ccns.values())

    # per-system roll-ups
    c990 = json.load(open(os.path.join(scratch, 'cohort_990.json')))
    recs990 = {r['system']: r for r in c990['systems']}
    reh = lib.load_cache(cache, 'reh_list')

    agg = {}
    for name in sys_ccns:
        ccns = sys_ccns[name]
        in_corr = sorted(c for c in ccns if c in by_ccn)
        cases = sum(stats[c][0] for c in in_corr)
        hrows = [hcris[c] for c in ccns if c in hcris]
        states = sorted({(hcris.get(c) or pdc.get(c))['state']
                         for c in ccns
                         if (hcris.get(c) or pdc.get(c)).get('state')})
        # REH scan: rows in the system's states; name-match by the same rule
        _, _, _, pred = next(r for r in RULES if r[0] == name)
        reh_in_states, reh_match = 0, []
        for row in reh:
            st = row.get('STATE')
            if st not in states:
                continue
            reh_in_states += 1
            nm = ((row.get('DOING BUSINESS AS NAME') or '')
                  + ' ' + (row.get('ORGANIZATION NAME') or '')).upper()
            if pred(nm, st, (row.get('CITY') or '').upper()):
                reh_match.append(f"{(row.get('DOING BUSINESS AS NAME') or row.get('ORGANIZATION NAME') or '').title()}"
                                 f" ({st}, converted {row.get('REH CONVERSION DATE', '?')})")
        # 990 stats
        r9 = recs990.get(SYS990[name], {})
        n_eins = len(r9.get('eins') or [])
        filings = [f for e in (r9.get('eins') or [])
                   for f in (e.get('filings') or [])]
        parsed = [f for f in filings if f.get('tax_year')]
        blocked = [f for f in filings if f.get('error')]
        floors = [f.get('contractors_gt100k_count') for f in parsed
                  if isinstance(f.get('contractors_gt100k_count'), int)]
        n_transport = sum(len(f.get('transport_contractors') or [])
                          for f in parsed)
        tax_years = sorted({f['tax_year'] for f in parsed})
        agg[name] = {
            'ccns': ccns, 'in_corr': in_corr, 'cases': cases,
            'beds': sum(h['beds'] for h in hrows),
            'days': sum(h['days'] for h in hrows),
            'n_hcris': len(hrows), 'states': states,
            'reh_in_states': reh_in_states, 'reh_match': reh_match,
            'n_eins': n_eins, 'n_parsed': len(parsed),
            'n_blocked': len(blocked),
            'floor_max': max(floors) if floors else 0,
            'n_transport': n_transport, 'tax_years': tax_years}
    order = sorted(agg, key=lambda k: -agg[k]['cases'])
    top_sys = order[0]
    tot_beds = sum(a['beds'] for a in agg.values())
    tot_days = sum(a['days'] for a in agg.values())
    tot_parsed = sum(a['n_parsed'] for a in agg.values())
    tot_eins = sum(a['n_eins'] for a in agg.values())
    tot_transport = sum(a['n_transport'] for a in agg.values())

    # estate registrations (E.5)
    est = json.load(open(os.path.join(scratch, 'estate_addresses.json')))
    st_info = collections.defaultdict(lambda: {'npis': set(), 'cities': set()})
    for v in est.values():
        locs = ([v['location']] if v.get('location') else []) \
            + (v.get('practice_locations') or [])
        for a in locs:
            st = a.get('state')
            if not st:
                continue
            st_info[st]['npis'].add(v['npi'])
            st_info[st]['cities'].add((a.get('city') or '').title())
    reg_states = sorted(st_info)
    reg_and_prov = sorted(set(reg_states) & set(PROV_FOOT))
    prov_only = sorted(set(PROV_FOOT) - set(reg_states))
    reg_only = sorted(set(reg_states) - set(PROV_FOOT))

    # USAspending evidence: award-grain extract + FY25 recipient roll-up
    usasp_awards = []
    p_raw = os.path.join(scratch, 'usaspending_v225_raw.json')
    if os.path.exists(p_raw):
        for r in json.load(open(p_raw)):
            if 'MIDWEST MEDICAL TRANSPORT' in (
                    r.get('Recipient Name') or '').upper():
                usasp_awards.append(r)
    usasp_pop = collections.defaultdict(list)
    for r in usasp_awards:
        usasp_pop[r.get('Place of Performance State Code')].append(r)
    usasp_fy25 = None
    try:
        for r in lib.load_cache(cache, 'usasp_v225_recipients_fy25')['results']:
            if 'MIDWEST MEDICAL TRANSPORT' in (r.get('name') or '').upper():
                usasp_fy25 = r
    except FileNotFoundError:
        pass

    # wayback availability probes (two artifacts, three domains)
    wb_foot = {}
    p_wbf = os.path.join(scratch, 'wayback_footprint.json')
    if os.path.exists(p_wbf):
        wb_foot = json.load(open(p_wbf))
    wb_avail = []
    p_wba = os.path.join(scratch, 'ems_rosters', 'wayback_avail.json')
    if os.path.exists(p_wba):
        wb_avail = json.load(open(p_wba))
    wba_domains = collections.defaultdict(set)
    for r in wb_avail:
        if r.get('timestamp'):
            wba_domains[r['domain']].add(r['timestamp'])

    # press registry probe (may land after this module is written)
    press_rows, press_date = None, None
    p_press = os.path.join(scratch, 'press_registry.json')
    if os.path.exists(p_press):
        try:
            raw = json.load(open(p_press))
            press_rows = raw if isinstance(raw, list) else \
                raw.get('rows') or raw.get('entries') or []
            if isinstance(raw, dict):
                press_date = raw.get('retrieved')
        except (ValueError, AttributeError):
            press_rows = None

    def press_hits(sys_name):
        """Registry rows citable on a system panel: the DOCUMENT itself
        must tie the system and the subject company (issuer is either
        party and the release text names the other)."""
        if not press_rows:
            return []
        toks = [t.upper() for t in re.split(r'[^A-Za-z]+', sys_name)
                if len(t) > 3]
        hits = []
        for row in press_rows:
            org = (row.get('org') or '').upper()
            doc = ((row.get('headline') or '') + ' '
                   + (row.get('what_it_establishes') or '')).upper()
            is_subject = 'MIDWEST MEDICAL' in org or 'MMT' in org
            is_system = any(t in org for t in toks)
            ties = (is_subject and any(t in doc for t in toks)) or \
                   (is_system and ('MIDWEST MEDICAL' in doc
                                   or 'MMT ' in doc or ' MMT' in doc))
            if ties:
                hits.append(row)
        return hits

    # tab-existence probes for green links vs text pointers
    def has(tab):
        return tab in wb.sheetnames
    panel_b = _scan_cohort_panel_b(wb, set(SYS990))

    # E.6 screen: name families in registered footprint states
    fams = collections.defaultdict(list)
    for ccn, d in hcris.items():
        if d['state'] in reg_states and ccn not in cohort_all and _acute(ccn):
            k = _famkey(d['name'])
            if k:
                fams[k].append(ccn)
    big = {k: v for k, v in fams.items() if len(v) >= 3}
    ranked = sorted(
        big.items(),
        key=lambda kv: -sum(stats.get(c, (0, 0))[0] for c in kv[1]))
    n_screened = len(big)

    def fam_row(key, ccns):
        cases = sum(stats.get(c, (0, 0))[0] for c in ccns)
        hub_n = sum(1 for c in ccns if c in hubs)
        states = sorted({hcris[c]['state'] for c in ccns})
        ex = max(ccns, key=lambda c: stats.get(c, (0, 0))[0])
        return cases, hub_n, states, hcris[ex]['name']

    top_fam, top_fam_ccns = ranked[0]
    top_fam_cases = fam_row(top_fam, top_fam_ccns)[0]

    website_quotes = [
        ('https://mmtamb.com/',
         'For over 35 years, MMT has partnered with some of the largest '
         'and most prestigious health systems across the country to '
         'provide patient ambulance transportation solutions to improve '
         'throughput.'),
        ('https://mmtamb.com/about-us/',
         'Our team of more than 2,800+ dedicated emergency medicine '
         'professionals is committed to providing optimal care to each '
         'patient and exceptional service to the health system partners '
         'within our communities.'),
        ('https://mmtamb.com/about-us/',
         'Empowered Local Leaders, Supported by a National Infrastructure.'),
    ]

    # ------------------------------------------------------------- sources
    sources += [
        {'key': 'e156_hcris_panel', 'publisher': 'CMS (HCRIS)',
         'document': 'Hospital cost report (HCRIS) panel, vendored extract '
                     'rcm_mc/data/hcris.csv.gz - ccn, name, city, state, '
                     'beds, total patient days, latest filed year per CCN',
         'vintage': 'FY2020-FY2022 cost reports',
         'locator': 'Latest fiscal-year row per CCN; names uppercased for '
                    'the printed match rules; beds and total_patient_days '
                    'summed per matched CCN set',
         'supplies': 'Cohort roster names, beds and inpatient days; the '
                     'E.6 grouping universe',
         'url': 'https://www.cms.gov/data-research/statistics-trends-'
                'reports/cost-reports',
         'tier': 'A', 'accessed': accessed,
         'powers': ['System_Research_Cohort', 'Prospect_Landscape']},
        {'key': 'e156_pdc_roster', 'publisher': 'CMS (Provider Data '
         'Catalog)',
         'document': 'Care Compare - Hospital General Information roster '
                     '(cache pdc2_hospitals)',
         'vintage': '2026 roster',
         'locator': 'facility_id joined as CCN; second roster for the '
                    'printed match rules (catches renames)',
         'supplies': 'Current hospital names for cohort CCN resolution',
         'url': 'https://data.cms.gov/provider-data/dataset/xubh-q36u',
         'tier': 'A', 'accessed': accessed,
         'powers': ['System_Research_Cohort']},
        {'key': 'e156_hsa_corridors', 'publisher': 'CMS',
         'document': 'Hospital Service Area file, 2025 release - top-15 '
                     'origin-ZIP corridor extract per hospital CCN (cache '
                     'hsa_2025_corridors_top15; full grain on '
                     'HSA_Corridors)',
         'vintage': '2025 (Medicare FFS inpatient claims)',
         'locator': 'Corridor cases summed per CCN; hub bar mirrored from '
                    'Hub_Spoke_Map Panel A (90th pct volume AND breadth '
                    '>= 8 of 15)',
         'supplies': 'Cohort corridor demand cross-checks and the E.6 '
                     'transfer-demand ranking',
         'url': 'https://data.cms.gov/summary-statistics-on-use-and-'
                'payments/medicare-service-type-reports/'
                'hospital-service-area',
         'tier': 'A', 'accessed': accessed,
         'powers': ['System_Research_Cohort', 'Prospect_Landscape']},
        {'key': 'e156_cohort_990', 'publisher': 'IRS via ProPublica '
         'Nonprofit Explorer',
         'document': 'Form 990 e-file XML, Part VII Section B (five '
                     'highest-compensated independent contractors), latest '
                     'two XML-available filings per resolved cohort EIN '
                     '(scratchpad cohort_990.json receipts)',
         'vintage': f'Tax years 2022-2024 as filed; pulled '
                    f'{c990.get("generated", "2026-07-11")}',
         'locator': 'ContractorCompensationGrp + '
                    'CntrctRcvdGreaterThan100KCnt per filing; keyword '
                    'screen printed in cohort_990.json '
                    'transport_keyword_regex',
         'supplies': 'The top-five-contractor transport observation and '
                     'the over-$100K contractor-count floor per filing',
         'url': 'https://projects.propublica.org/nonprofits/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['System_Research_Cohort']},
        {'key': 'e156_reh_list', 'publisher': 'CMS',
         'document': 'Rural Emergency Hospital enrollment roster (cache '
                     'reh_list): organization / DBA names, state, REH '
                     'conversion date',
         'vintage': '2026 enrollment file (48 REHs)',
         'locator': 'Rows with STATE in each cohort system\'s roster '
                    'states; name match by the same printed rule',
         'supplies': 'REH participation scan per cohort system',
         'url': 'https://data.cms.gov/provider-characteristics/hospitals-'
                'and-other-facilities/rural-emergency-hospitals',
         'tier': 'A', 'accessed': accessed,
         'powers': ['System_Research_Cohort']},
        {'key': 'e156_nppes_estate', 'publisher': 'CMS (NPPES API)',
         'document': 'NPPES registry API pulls for the 23 subject-company '
                     'estate NPIs (scratchpad estate_addresses.json): '
                     'primary practice location plus secondary practice '
                     'locations per NPI',
         'vintage': 'NPPES live registry, pulled 11 Jul 2026',
         'locator': 'address_purpose=LOCATION rows; state and city per '
                    'NPI; mailing addresses ignored',
         'supplies': 'The registration evidence behind the printed '
                     'footprint rule',
         'url': 'https://npiregistry.cms.hhs.gov/api/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Footprint_Determination']},
        {'key': 'e156_usasp_v225', 'publisher': 'USAspending.gov',
         'document': 'Federal award search, product/service code V225 '
                     '(ambulance services): spending_by_award extract '
                     '(scratchpad usaspending_v225_raw.json, 300 rows) and '
                     'spending_by_category recipient roll-ups FY23-FY25 '
                     '(cache usasp_v225_recipients_*)',
         'vintage': 'FY2023-FY2025 transactions',
         'locator': 'Rows where Recipient Name = MIDWEST MEDICAL '
                    'TRANSPORT COMPANY, LLC; Place of Performance State '
                    'Code per award',
         'supplies': 'Public place-of-performance evidence for the '
                     'footprint rows',
         'url': 'https://www.usaspending.gov/search',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Footprint_Determination']},
        {'key': 'e156_mmt_site', 'publisher': 'MMT Ambulance (subject '
         'company public website)',
         'document': 'mmtamb.com - home, about-us, what-we-do, '
                     'partnerwithus, contact and careers pages, fetched 11 '
                     'Jul 2026 (receipts mmt_live.html, mmt_about-us.html '
                     'et al. in scratchpad); legacy domain '
                     'midwestmedicaltransport.com observed parked at a '
                     'domain marketplace the same day',
         'vintage': 'Live site as of 11 Jul 2026',
         'locator': 'Verbatim sentences quoted on Panel C; no state-by-'
                    'state operating list is published on any checked page',
         'supplies': 'Self-claim rows (PUBLIC-WEB, labeled; no state '
                     'grain)',
         'url': 'https://mmtamb.com/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Footprint_Determination']},
        {'key': 'e156_wayback', 'publisher': 'Internet Archive',
         'document': 'Wayback Machine availability API probes: '
                     'midwestmedtrans.com (wayback_footprint.json - no '
                     'captures 2014-2026), midwestmedicaltransport.com and '
                     'mmtamb.com (ems_rosters/wayback_avail.json - '
                     'captures exist, incl. mmtamb.com 2023-2026)',
         'vintage': 'Probed 11 Jul 2026',
         'locator': 'archive.org/wayback/available responses per domain '
                    'and year; snapshot text NOT retrievable from this '
                    'environment (web.archive.org connection resets)',
         'supplies': 'The claimed-footprint time series status (PENDING)',
         'url': 'https://archive.org/wayback/available',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Footprint_Determination']},
    ]
    if press_rows is not None:
        sources.append(
            {'key': 'e156_press_registry', 'publisher': 'Issuer newsrooms '
             '(Business Wire; company news pages)',
             'document': 'Dated self-issued press releases of the tracked '
                         'market participants and the subject company '
                         f'(scratchpad press_registry.json, '
                         f'{len(press_rows)} rows; rendered on '
                         'Press_Footprint_Registry)',
             'vintage': f'Releases 2021-2026, retrieved '
                        f'{press_date or accessed}',
             'locator': 'Per-system scan: a release is citable on a '
                        'cohort panel only when its own text ties the '
                        'system and the subject company; zero such rows '
                        'exist',
             'supplies': 'The public press / case-study observation rows '
                         '(PUBLIC-WEB, URL and date per row)',
             'url': 'https://www.businesswire.com/',
             'tier': 'A', 'accessed': accessed,
             'powers': ['System_Research_Cohort']})

    # =====================================================================
    # TAB 1 - System_Research_Cohort
    # =====================================================================
    ws = wb.create_sheet('System_Research_Cohort')
    sb = lib.SheetBuilder(ws, 6, col_widths=[36, 14, 13, 13, 46, 48],
                          tab_color='FF1F6F8B')
    sb.title('System research cohort: what the public record establishes, '
             'system by system')
    sb.subtitle('The question: what does the public record measurably '
                'establish, per system, about scale (beds, inpatient '
                'days), corridor transfer demand, ambulance cost-center '
                'status, timeliness placement, REH/AHCAH participation '
                'and transport sourcing? Sources and join keys: hospital '
                'CCNs by the PRINTED name-match rules mirrored from '
                'Cohort_Corridors Panel A over the HCRIS panel and Care '
                'Compare roster; beds/days from HCRIS latest filed FY per '
                'CCN; corridor demand green-linked into Cohort_Corridors; '
                'REH roster scanned by state + the same rule; Form 990 '
                'Part VII Section B parsed from IRS e-file XML.',
                height=56)
    sb.note('FRAMING: the group studied on this tab is a ' + COHORT_FRAME
            + '. No organization on this tab is described as a customer, '
            'account or commercial counterparty of any company; every row '
            'is a public-document observation.', height=26)
    sb.note('DATA QUALITY: name-match rules over- and under-match as '
            'printed per panel (confound, not blocker); HCRIS beds/days '
            'are FY2020-FY2022 filings (pre-2024 combinations missed; '
            'admissions are NOT carried in the vendored extract - see the '
            'PENDING row); corridor demand is Medicare FFS inpatient only, '
            'truncated to top-15 origin ZIPs per hospital (a floor); Form '
            '990 Part VII discloses only the five highest-paid '
            'contractors over $100K, so absence of transport vendors '
            'there is a disclosure-window observation, never evidence of '
            'no vendor relationship.', height=48)
    sb.blank()

    # Panel A - cohort summary
    sb.banner('Panel A. Cohort summary (systems sorted by measured '
              'corridor demand)')
    sb.headers(['System', 'CCNs matched', 'Staffed beds (HCRIS latest FY)',
                'Inpatient days (HCRIS latest FY)',
                'Corridor cases (green link where built)', 'Note'])
    a0 = sb.r + 1
    atot = a0 + len(order)
    for i, name in enumerate(order):
        a = agg[name]
        if name in SYS990 and panel_b.get(SYS990[name]) is None \
                and panel_b.get(name) is None:
            corr_cell = (round(a['cases']), 'src', lib.FMT_INT)
            corr_note = ('corridor cases computed in-module; '
                         'Cohort_Corridors not present at build time'
                         if i == 0 else None)
        else:
            rn = panel_b.get(name) or panel_b.get(SYS990[name])
            corr_cell = (f"='Cohort_Corridors'!C{rn}", 'link', lib.FMT_INT)
            corr_note = ('corridor cases green-linked to Cohort_Corridors '
                         'Panel B' if i == 0 else None)
        sb.row([(name, 'label'),
                (len(a['ccns']), 'src', lib.FMT_INT),
                (round(a['beds']), 'src', lib.FMT_INT),
                (round(a['days']), 'src', lib.FMT_INT),
                corr_cell,
                (corr_note, 'note') if corr_note else None])
    sb.row([('Research cohort total', 'label'),
            (f'=SUM(B{a0}:B{atot - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(C{a0}:C{atot - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(D{a0}:D{atot - 1})', 'fml', lib.FMT_INT),
            (f'=SUM(E{a0}:E{atot - 1})', 'fml', lib.FMT_INT), None])
    sb.row([('Cohort admissions', 'label'), ('PENDING', 'note'), None, None,
            ('Admissions are not carried in the vendored HCRIS extract; '
             'public dataset that fills this cell: CMS HCRIS full SAS '
             'files, Worksheet S-3 Part I (admissions by payer)', 'note'),
            None], wrap=True, height=26)
    f990_rn = sb.r + 1
    sb.row([('Form 990 filings parsed (Part VII Section B, all nine '
             'systems)', 'label'),
            (tot_parsed, 'src', lib.FMT_INT),
            (tot_eins, 'src', lib.FMT_INT),
            (tot_transport, 'src', lib.FMT_INT),
            ('B = filings parsed, C = EINs resolved, D = ambulance / EMS '
             '/ medical-transport contractors found among the disclosed '
             'top-five across ALL parsed filings (keyword screen printed '
             'in cohort_990.json)', 'note'),
            ('the top-five window is the disclosure floor: vendors '
             'billing below each filer\'s fifth-highest contractor are '
             'invisible by design', 'note')], wrap=True, height=34)
    sb.note('COVERAGE: beds and inpatient days sum only the matched CCNs '
            'present in the vendored HCRIS panel (FY2020-FY2022 filings); '
            'CCNs matched via the Care Compare roster alone carry no cost '
            'report here, so Panel A beds and days are FLOORS of true '
            'system scale (per-panel detail rows print each system\'s '
            'HCRIS coverage).')
    sb.blank()

    # Panels B..J - per-system dossiers
    for i, name in enumerate(order):
        a = agg[name]
        rule, confound = rule_meta[name]
        sb.banner(f'Panel {chr(66 + i)}. {name}')
        sb.headers(['Item', 'Value', 'Value 2', 'Value 3',
                    'Detail / evidence', 'Note / confound'])
        sb.row([('Hospital roster (printed name-match rule)', 'label'),
                (len(a['ccns']), 'src', lib.FMT_INT),
                (len(a['in_corr']), 'src', lib.FMT_INT),
                None,
                (f'Rule: {rule}. B = CCNs matched (roster union), C = of '
                 'those, CCNs present in the HSA 2025 corridor file; '
                 f'{a["n_hcris"]} of {len(a["ccns"])} matched CCNs carry '
                 'an HCRIS cost report (beds/days coverage). '
                 f'States: {", ".join(a["states"])}', 'text'),
                (confound, 'note')], wrap=True, height=40)
        sb.row([('Ambulance cost-center status', 'label'),
                (f"='HCRIS_Ambulance_CostCenters'!A1" if
                 has('HCRIS_Ambulance_CostCenters') else 'PENDING',
                 'link' if has('HCRIS_Ambulance_CostCenters') else 'note'),
                None, None,
                ('see HCRIS_Ambulance_CostCenters: Worksheet A ambulance '
                 'cost-center flags per hospital CCN (join on the CCNs of '
                 'this panel)', 'text'),
                (None if has('HCRIS_Ambulance_CostCenters') else
                 'tab HCRIS_Ambulance_CostCenters not present at build '
                 'time; dataset: HCRIS Worksheet A ambulance lines',
                 'note')], wrap=True, height=28)
        cc_rn = panel_b.get(name) or panel_b.get(SYS990.get(name, ''))
        cname = name.replace('"', '""')
        if cc_rn:
            sb.row([('Corridor demand and breadth (green)', 'label'),
                    (f"='Cohort_Corridors'!C{cc_rn}", 'link', lib.FMT_INT),
                    (f"='Cohort_Corridors'!G{cc_rn}", 'link', lib.FMT_INT),
                    (f"=COUNTIF('Cohort_Corridors'!$A:$A,\"{cname}\")-3",
                     'link', lib.FMT_INT),
                    ('B = top-15 corridor cases (Cohort_Corridors Panel '
                     'B), C = implied transfer episodes at the linked '
                     'HCUP rate, D = system top origin ZIPs listed in '
                     'Panel D (breadth, max 15)', 'text'),
                    ('Medicare FFS inpatient floor; top-15 truncation '
                     'biases breadth down', 'note')], wrap=True, height=34)
        else:
            sb.row([('Corridor demand and breadth', 'label'),
                    (round(a['cases']), 'src', lib.FMT_INT),
                    None, None,
                    ('computed in-module from cache '
                     'hsa_2025_corridors_top15; green links activate once '
                     'Cohort_Corridors is built', 'text'),
                    ('Medicare FFS inpatient floor', 'note')],
                   wrap=True, height=28)
        sb.row([('Timeliness placement (ED congestion where transfers '
                 'land)', 'label'),
                (f"='Transfer_Delay_Burden'!A1" if
                 has('Transfer_Delay_Burden') else 'PENDING',
                 'link' if has('Transfer_Delay_Burden') else 'note'),
                None, None,
                ('see Transfer_Delay_Burden: OP-18b ED timeliness for the '
                 f'footprint states; this system\'s states: '
                 f'{", ".join(a["states"])}', 'text'),
                (None if has('Transfer_Delay_Burden') else
                 'tab Transfer_Delay_Burden not present at build time; '
                 'dataset: CMS Timely and Effective Care (OP-18b)',
                 'note')], wrap=True, height=28)
        reh_detail = ('; '.join(a['reh_match']) if a['reh_match'] else
                      'no name-matched REH conversions; '
                      f'{a["reh_in_states"]} REHs operate in the system '
                      f'states ({", ".join(a["states"])})')
        sb.row([('REH / AHCAH participation', 'label'),
                (len(a['reh_match']), 'src', lib.FMT_INT),
                (a['reh_in_states'], 'src', lib.FMT_INT),
                ('PENDING', 'note'),
                (f'B = REH conversions matching the printed rule, C = all '
                 f'REHs in the system states. {reh_detail}. D (AHCAH): '
                 'CMS Acute Hospital Care at Home approved-waiver list - '
                 'the current list renders only in a JS portal and the '
                 '2021 static PDF is stale (parked)', 'text'),
                ('REH name match carries the same confounds as the '
                 'roster rule', 'note')], wrap=True, height=40)
        sb.row([('Form 990 top-five contractors (transport screen)',
                 'label'),
                (a['n_transport'], 'src', lib.FMT_INT),
                (a['n_parsed'], 'src', lib.FMT_INT),
                (a['floor_max'], 'src', lib.FMT_INT),
                ('none in top-five disclosure window; floor stated. B = '
                 'transport-keyword contractor matches, C = filings '
                 f'parsed (tax years {", ".join(a["tax_years"]) or "-"}), '
                 'D = contractors over $100K in the largest filing (the '
                 'disclosure floor)'
                 + (' - see Cohort_990_Contractors'
                    if has('Cohort_990_Contractors') else
                    ' - detail tab: Cohort_990_Contractors (pointer; not '
                    'present at build time)'), 'text'),
                (f'{a["n_eins"]} EINs resolved'
                 + (f'; {a["n_blocked"]} newest filings XML-blocked '
                    '(bot-gated mirror), next-oldest parsed'
                    if a['n_blocked'] else ''), 'note')],
               wrap=True, height=40)
        if has('Cohort_990_Contractors'):
            sb.row([('990 contractor detail (green)', 'label'),
                    ("='Cohort_990_Contractors'!A1", 'link'),
                    None, None,
                    ('full per-filing contractor rows live on '
                     'Cohort_990_Contractors', 'text'), None])
        hits = press_hits(name)
        if hits:
            for j, h in enumerate(hits[:3]):
                url = h.get('url') or h.get('link') or ''
                date = h.get('date') or h.get('published') or ''
                title = (h.get('title') or h.get('headline') or
                         'press release')
                sb.row([('Public press / case-study reference' if j == 0
                         else '', 'label'),
                        ('PUBLIC-WEB', 'src'), (date, 'src'), None,
                        (f'{title} - {url}', 'src'),
                        ('cited only because the public document itself '
                         'ties the organizations; issuer\'s own release',
                         'note') if j == 0 else None], wrap=True,
                       height=26)
        elif press_rows is not None:
            sb.row([('Public press / case-study references', 'label'),
                    (0, 'src', lib.FMT_INT), None, None,
                    (f'press registry scanned ({len(press_rows)} dated '
                     f'public releases, retrieved {press_date or "?"}): '
                     'no public press or case-study document ties this '
                     'system to the subject company; full registry on '
                     'Press_Footprint_Registry', 'text'),
                    ('a row would appear here only if a public document '
                     'independently tied the organizations, citing that '
                     'document alone', 'note') if i == 0 else None],
                   wrap=True, height=28)
        else:
            sb.row([('Public press / case-study references', 'label'),
                    ('pointer', 'note'), None, None,
                    ('see Press_Footprint_Registry'
                     + ('' if has('Press_Footprint_Registry') else
                        ' (registry tab not present at build time; press '
                        'rows land there as PUBLIC-WEB entries with URL '
                        'and date)')
                     + '; a row appears here only if a public document '
                     'independently ties the organization to the subject '
                     'company, citing that document alone', 'text'),
                    None], wrap=True, height=28)
        sb.blank()

    sb.banner('Read panel')
    sb.prose('What the public record establishes for the cohort: scale '
             f'(about {round(tot_beds):,} staffed beds and '
             f'{round(tot_days) / 1e6:,.1f}M inpatient days across the '
             'matched rosters), measured corridor demand (led by '
             f'{top_sys} at {round(agg[top_sys]["cases"]):,} top-15 '
             'corridor cases), HCRIS ambulance cost-center flags, and REH '
             'participation. What it does NOT establish: transport vendor '
             f'relationships. Across {tot_parsed} parsed Form 990 filings '
             f'({tot_eins} EINs), zero ambulance / EMS / medical-'
             'transport contractors appear among the disclosed five '
             'highest-paid contractors, '
             + (f'none of the {len(press_rows)} dated public releases in '
                'the press registry ties a cohort system to the subject '
                'company, ' if press_rows is not None else '')
             + 'and the federal award record ties no cohort system to '
             'any specific transport vendor - the sourcing layer sits '
             'below the public disclosure floor. Every group reference '
             'on this tab means the ' + COHORT_FRAME + '.')

    t1_max = ws.max_row
    lib.add_chart(
        ws, 'H6', 'Cohort staffed beds by system (HCRIS latest FY)',
        f"'System_Research_Cohort'!$A${a0}:$A${atot - 1}",
        [('Staffed beds',
          f"'System_Research_Cohort'!$C${a0}:$C${atot - 1}")],
        kind='bar', y_fmt='#,##0')

    # =====================================================================
    # TAB 2 - Footprint_Determination
    # =====================================================================
    ws2 = wb.create_sheet('Footprint_Determination')
    sb = lib.SheetBuilder(ws2, 8,
                          col_widths=[7, 10, 32, 36, 28, 26, 24, 42],
                          tab_color='FF1F6F8B')
    sb.title('Footprint determination: the subject company\'s operating '
             'states from public evidence')
    sb.subtitle('The question: which states is the subject company '
                'operating in, by a printed public-evidence rule? '
                'Evidence columns: (a) NPPES registered practice '
                'locations of the 23 estate NPIs (pulled 11 Jul 2026), '
                '(b) USAspending place-of-performance states where a '
                'federal award names the company (PSC V225 extracts), '
                '(c) the current public website\'s self-claims (fetched '
                '11 Jul 2026), (d) Wayback Machine self-claim series. '
                'Join key: state; each row carries its own evidence.',
                height=52)
    sb.note('DATA QUALITY: an NPPES registration is a billing/practice '
            'registration, not proof of stations or service volume, and '
            'eight of the registered states rest on a single NPI '
            'registration each; the website publishes NO state-by-state '
            'operating list, so self-claims carry no state grain and are '
            'labeled as claims; cached USAspending pulls are top-50 '
            'recipient pages plus one 300-row award extract (absence '
            'from them is not zero); the Wayback self-claim series could '
            'not be extracted (host unreachable from this environment) '
            'and is PENDING.', height=46)
    sb.blank()

    sb.banner('Panel A. The printed rule')
    sb.prose('THE RULE: a state is IN the footprint when at least one '
             'NPPES registered practice location of the 23 subject-'
             'company estate NPIs exists in it. Website or Wayback '
             'self-claims WITHOUT a matching registration render as '
             '"claimed, not registered" rows and do NOT add states. '
             'USAspending place-of-performance corroborates but neither '
             'adds nor removes states on its own.', kind='label')
    sb.blank()

    sb.banner('Panel B. State-by-state evidence')
    sb.headers(['State', 'NPPES NPIs', 'Registered cities (NPPES)',
                'USAspending place-of-performance evidence',
                'Website self-claim', 'Wayback series', 'Footprint status',
                'Note'])
    reg_sorted = sorted(reg_states,
                        key=lambda s: (-len(st_info[s]['npis']), s))
    b0 = sb.r + 1
    for i, st in enumerate(reg_sorted):
        d = st_info[st]
        aw = usasp_pop.get(st) or []
        if aw:
            ev = '; '.join(
                f"{r['Awarding Agency']} {r['Contract Award Type'].lower()}"
                f" {r['Award ID']}, {r['Description'].title()}, "
                f"${r['Award Amount']:,.0f}, {r['Start Date']} to "
                f"{r['End Date']}" for r in aw)
        else:
            ev = 'none observed in cached V225 pulls'
        sb.row([(st, 'label'),
                (len(d['npis']), 'src', lib.FMT_INT),
                ('; '.join(sorted(d['cities'])), 'src'),
                (ev, 'src' if aw else 'note'),
                ('no state-grain claim published', 'note'),
                ('no extracted series (Panel D)', 'note'),
                ('IN footprint - registered', 'label'),
                ('award rows are public federal contract records naming '
                 'the company; cited from USAspending only'
                 if aw else None, 'note') if aw else None],
               wrap=True, height=30 if not aw else 40)
    for st in prov_only:
        sb.row([(st, 'label'), (0, 'src', lib.FMT_INT), ('-', 'note'),
                ('none observed in cached V225 pulls', 'note'),
                ('no state-grain claim published', 'note'),
                ('no extracted series (Panel D)', 'note'),
                ('NOT in footprint - no registration', 'text'),
                ('carried provisionally by earlier tabs as market-context '
                 'geography; no registered estate location', 'note')],
               wrap=True, height=28)
    sb.note('Recipient roll-up cross-check: the company appears in the '
            'FY2025 top-50 V225 recipient roll-up at '
            + (f"${usasp_fy25['amount']:,.0f}" if usasp_fy25 else 'n/a')
            + ' (USAspending spending_by_category); it is absent from the '
            'cached FY2023 and FY2024 top-50 pages, where absence means '
            'below the 50th recipient, not zero.')
    sb.blank()

    sb.banner('Panel C. Website self-claims (PUBLIC-WEB, labeled; no '
              'state grain)')
    sb.headers(['#', 'Accessed', 'Page', 'Verbatim self-claim', '', '',
                '', 'Note'])
    for j, (url, quote) in enumerate(website_quotes, 1):
        sb.row([(j, 'src', lib.FMT_INT), ('11 Jul 2026', 'src'),
                (url, 'src'), (quote, 'src'), None, None, None,
                ('self-claim by the subject company about itself; no '
                 'third party named; no state grain, so it adds no state '
                 'under the rule', 'note') if j == 1 else None],
               wrap=True, height=40)
    sb.row([(len(website_quotes) + 1, 'src', lib.FMT_INT),
            ('11 Jul 2026', 'src'), ('site-wide check', 'text'),
            ('No locations or state-by-state operating list is published '
             'on the current site (home, about-us, what-we-do, '
             'how-we-do-it, partnerwithus, contact, careers checked); '
             'careers listings are hosted on an external applicant-'
             'tracking portal (JS, not parsed). Legacy domain '
             'midwestmedicaltransport.com is parked at a domain '
             'marketplace; mmtamb.com is the live site.', 'src'),
            None, None, None, None], wrap=True, height=48)
    sb.blank()

    sb.banner('Panel D. Wayback self-claim series')
    sb.headers(['#', 'Domain', 'Availability-API result', 'Series status',
                '', '', '', 'Note'])
    sb.row([(1, 'src', lib.FMT_INT), ('midwestmedtrans.com', 'src'),
            ('no captures 2014-2026 (wayback_footprint.json; live DNS '
             'does not resolve)', 'src'),
            ('empty - domain appears never to have hosted the site',
             'text'), None, None, None,
            ('probed via archive.org/wayback/available; control domains '
             'returned captures normally', 'note')], wrap=True, height=30)
    for j, dom in enumerate(sorted(wba_domains), 2):
        ts = sorted(wba_domains[dom])
        sb.row([(j, 'src', lib.FMT_INT), (dom, 'src'),
                (f'{len(ts)} distinct capture timestamps returned '
                 f'({ts[0][:8]} to {ts[-1][:8]})', 'src'),
                ('PENDING', 'note'), None, None, None,
                ('captures exist but snapshot text is unreachable from '
                 'this environment (web.archive.org connection resets); '
                 'public key that fills this: Wayback CDX + snapshot '
                 'fetch of the locations/about pages', 'note')
                if j == 2 else None], wrap=True, height=30)
    sb.blank()

    sb.banner('Panel E. Canonical footprint and reconciliation against '
              'the provisional list')
    sb.headers(['Measure', 'States', 'List', '', '', '', '', 'Note'])
    e0 = sb.r + 1
    sb.row([('Canonical footprint (registered)', 'label'),
            (len(reg_states), 'src', lib.FMT_INT),
            (' '.join(reg_sorted), 'src'), None, None, None, None,
            ('the printed rule of Panel A applied to Panel B', 'note')])
    sb.row([('Provisional list used by earlier tabs', 'label'),
            (len(PROV_FOOT), 'src', lib.FMT_INT),
            (' '.join(PROV_FOOT), 'src'), None, None, None, None,
            ('set before E.5 ran; printed on each tab that used it',
             'note')])
    sb.row([('Registered AND provisional', 'label'),
            (len(reg_and_prov), 'src', lib.FMT_INT),
            (' '.join(reg_and_prov), 'src'), None, None, None, None,
            None])
    gap_rn = sb.r + 1
    sb.row([('Provisional, NOT registered', 'label'),
            (len(prov_only), 'src', lib.FMT_INT),
            (' '.join(prov_only), 'src'), None, None, None, None,
            ('these states carry NO registered estate location; earlier '
             'tabs used them as market-context geography only', 'note')],
           wrap=True, height=26)
    sb.row([('Registered, NOT provisional', 'label'),
            (len(reg_only), 'src', lib.FMT_INT),
            (' '.join(reg_only), 'src'), None, None, None, None,
            ('registered states the provisional slices did not carry; '
             'footprint-scoped tab counts are floors with respect to the '
             'registered estate', 'note')], wrap=True, height=26)
    sb.row([('Tabs that used the provisional list', 'label'), None,
            (PROV_TABS, 'text'), None, None, None, None, None],
           wrap=True, height=28)
    sb.prose('RECONCILIATION: the provisional list is neither a superset '
             'nor a subset of the registered list - it overlaps in '
             f'{len(reg_and_prov)} of {len(reg_states)} registered '
             f'states, carries {len(prov_only)} states with no '
             f'registration ({" ".join(prov_only)}) and misses '
             f'{len(reg_only)} registered states ({" ".join(reg_only)}). '
             'The A-tab state slices are unchanged: each tab prints its '
             'own state universe, its state-sliced measures describe '
             'MARKET structure (payment, supply, corridors) rather than '
             'estate presence, so the KS/MN/KY slices stand as market '
             'context, while footprint-scoped totals understate the '
             'registered estate in ' + ' '.join(reg_only) + ' and should '
             'be read as floors until the next refresh re-slices on the '
             'canonical list.')
    sb.blank()

    sb.banner('Read panel')
    sb.prose('The canonical footprint, by the printed rule, is '
             f'{len(reg_states)} states: {" ".join(reg_sorted)}. The '
             'evidence stack is asymmetric in an instructive way: '
             'registrations are precise and public (23 NPIs, '
             f'{sum(len(d["npis"]) for d in st_info.values())} '
             'state-registrations), the federal award record corroborates '
             'two states (IA, NE) with named V225 awards, and the '
             'company\'s own public site claims a national posture '
             'without naming a single state - so the registered list is '
             'the only state-grain public evidence available, and it '
             'differs from the working list earlier tabs used in '
             f'{len(prov_only) + len(reg_only)} states. What this is '
             'NOT: a service-area or volume map; a registration proves '
             'presence of a billing location, nothing more.')

    t2_max = ws2.max_row

    # =====================================================================
    # TAB 3 - Prospect_Landscape
    # =====================================================================
    ws3 = wb.create_sheet('Prospect_Landscape')
    sb = lib.SheetBuilder(ws3, 7,
                          col_widths=[26, 11, 16, 14, 12, 36, 46],
                          tab_color='FF1F6F8B')
    sb.title('Landscape screen: additional multi-hospital systems in the '
             'footprint, screened by measured transfer demand')
    sb.subtitle('The question: beyond the research cohort, which '
                'multi-hospital systems in the registered footprint '
                'states carry the largest measured transfer demand? '
                'Universe and joins: HCRIS panel hospitals (latest filed '
                'FY per CCN) in the canonical footprint states of '
                'Footprint_Determination, short-term acute and CAH CCN '
                'ranges only, cohort CCNs excluded, grouped into name '
                'families by the printed rule of Panel A; ranked by HSA '
                '2025 top-15 corridor cases summed over each family\'s '
                'CCNs, with hub CCNs counted at the Hub_Spoke_Map '
                'thresholds (mirrored). The group listed here is simply '
                'the set of additional multi-hospital systems in the '
                'footprint, screened by measured transfer demand.',
                height=64)
    sb.note('DATA QUALITY: name families are a SCREEN, not corporate '
            'attribution - shared brand words (Mercy, St. Marys, '
            'Community Hospital) can merge unrelated organizations and '
            'renames/affiliates split real systems, so per-row flags mark '
            'likely mixed families; corridor demand is Medicare FFS '
            'inpatient only, truncated to top-15 origin ZIPs per hospital '
            '(floors); HCRIS names are FY2020-FY2022 vintage (post-2022 '
            'renames missed); hub counts inherit the Hub_Spoke_Map '
            'construct and its truncation bias.', height=44)
    sb.blank()

    sb.banner('Panel A. The printed screen rules')
    sb.headers(['Rule', 'Value', '', '', '', 'Detail', ''])
    sb.row([('Universe', 'label'), None, None, None, None,
            ('HCRIS latest-FY hospitals with state in the canonical '
             f'footprint ({" ".join(sorted(reg_states))}); CCN last four '
             'digits 0001-0879 (short-term acute) or 1300-1399 (CAH)',
             'text'), None], wrap=True, height=28)
    sb.row([('Exclusion', 'label'),
            (len(cohort_all), 'src', lib.FMT_INT), None, None, None,
            ('CCNs matched by any Cohort_Corridors Panel A printed rule '
             '(B = excluded CCNs); the cohort is profiled on '
             'System_Research_Cohort instead', 'text'), None],
           wrap=True, height=28)
    sb.row([('Grouping', 'label'), None, None, None, None,
            ('name family = first token of the uppercased, '
             'punctuation-stripped hospital name, except: leading THE '
             'dropped; SAINT normalized to ST and joined with the next '
             'token; UNIVERSITY OF keeps three tokens; generic first '
             'tokens (COMMUNITY, MEMORIAL, REGIONAL, state names, etc.) '
             'keep two tokens', 'text'), None], wrap=True, height=36)
    sb.row([('Qualification', 'label'), (3, 'src', lib.FMT_INT),
            None, None, None,
            ('families with at least B hospitals in the universe '
             'qualify; ranked by corridor cases', 'text'), None])
    sb.row([('Hub bar (mirrored from Hub_Spoke_Map)', 'label'),
            (round(p90, 1), 'src', lib.FMT_DEC1),
            (BREADTH_HUB, 'src', lib.FMT_INT), None, None,
            ('B = national 90th-percentile top-15 corridor cases, C = '
             'breadth bar (ZIPs to 80% of cases); a family CCN is a hub '
             'when it clears both', 'text'), None], wrap=True, height=28)
    sb.blank()

    sb.banner('Panel B. Top 20 by measured transfer demand (corridor '
              'cases, Medicare FFS floor)')
    sb.headers(['Name family', 'Hospitals', 'States (footprint)',
                'Corridor cases (floor)', 'Hub CCNs',
                'Largest hospital in family (HCRIS name)',
                'Note / family caveat'])
    p0 = sb.r + 1
    for i, (key, ccns) in enumerate(ranked[:20]):
        cases, hub_n, states, ex_name = fam_row(key, ccns)
        flag = (key in GENERICISH_FAMS or len(states) >= 3)
        note = None
        if i == 0:
            note = ('flagged rows: shared-name family likely spans '
                    'unrelated organizations - screen, not corporate '
                    'attribution')
        elif flag:
            note = 'name-family caveat: may span unrelated organizations'
        sb.row([(key.title() + (' *' if flag else ''), 'label'),
                (len(ccns), 'src', lib.FMT_INT),
                (' '.join(states), 'src'),
                (round(cases), 'src', lib.FMT_INT),
                (hub_n, 'src', lib.FMT_INT),
                (ex_name.title(), 'src'),
                (note, 'note') if note else None],
               wrap=True, height=26)
    n_rn = sb.r + 1
    sb.row([('Families screened (3+ hospitals, all, not just top 20)',
             'label'),
            (n_screened, 'src', lib.FMT_INT), None,
            (f'=SUM(D{p0}:D{p0 + 19})', 'fml', lib.FMT_INT),
            (f'=SUM(E{p0}:E{p0 + 19})', 'fml', lib.FMT_INT),
            ('D and E sum the top-20 rows only (live)', 'note'), None])
    sb.blank()

    sb.banner('Panel C. County-whitespace adjacency')
    if has('County_Whitespace_Screens'):
        sb.row([('Whitespace adjacency (green)', 'label'),
                ("='County_Whitespace_Screens'!A1", 'link'), None, None,
                None,
                ('county-level demand-vs-supply whitespace screens live '
                 'on County_Whitespace_Screens; join a family\'s hospital '
                 'counties to its ranked county rows', 'text'), None],
               wrap=True, height=28)
    else:
        sb.row([('Whitespace adjacency', 'label'), ('PENDING', 'note'),
                None, None, None,
                ('pointer: County_Whitespace_Screens (not present at '
                 'build time); join key: hospital county FIPS from the '
                 'HCRIS panel', 'text'), None], wrap=True, height=28)
    sb.blank()

    sb.banner('Read panel')
    top3 = [k for k, _ in ranked[:3]]
    sb.prose('The screen, measured: '
             f'{n_screened} name families with three or more hospitals '
             'operate in the registered footprint states outside the '
             'research cohort, and measured transfer demand concentrates '
             'sharply at the top - led by '
             f'{top3[0].title()} ({round(top_fam_cases):,} top-15 '
             f'corridor cases), {top3[1].title()} and {top3[2].title()}. '
             'These are measured demand concentrations from public '
             'corridor files: additional multi-hospital systems in the '
             'footprint, screened by measured transfer demand. What this '
             'is NOT: corporate attribution (flagged families can span '
             'unrelated organizations), a transfer matrix (corridors '
             'measure inpatient draw), or any statement about any '
             'organization\'s vendors or relationships.')

    t3_max = ws3.max_row
    lib.add_chart(
        ws3, 'I6', 'Top 10 screened families by corridor cases (HSA 2025)',
        f"'Prospect_Landscape'!$A${p0}:$A${p0 + 9}",
        [('Corridor cases', f"'Prospect_Landscape'!$D${p0}:$D${p0 + 9}")],
        kind='bar', y_fmt='#,##0')

    # ----------------------------------------------------------- registers
    facts += [
        # Tab 1
        {'metric': 'Research-cohort aggregate staffed beds (HCRIS latest '
                   'filed FY, printed-rule matched CCNs)',
         'year': 2022, 'value': round(tot_beds), 'unit': 'beds',
         'basis': 'GOV', 'tier': 'A',
         'source_keys': ['e156_hcris_panel', 'e156_pdc_roster'],
         'locator': 'System_Research_Cohort Panel A total row (live sum '
                    'of nine system rows); HCRIS beds field, latest FY '
                    'per CCN',
         'lives_on': 'System_Research_Cohort',
         'cross_check': 'FY2020-FY2022 filings; name-match confounds '
                        'printed per panel'},
        {'metric': 'Research-cohort aggregate inpatient days (HCRIS '
                   'latest filed FY, matched CCNs)',
         'year': 2022, 'value': round(tot_days), 'unit': 'patient days',
         'basis': 'GOV', 'tier': 'A',
         'source_keys': ['e156_hcris_panel', 'e156_pdc_roster'],
         'locator': 'System_Research_Cohort Panel A total row; HCRIS '
                    'total_patient_days, latest FY per CCN',
         'lives_on': 'System_Research_Cohort',
         'cross_check': 'Admissions are PENDING (not in the vendored '
                        'extract; HCRIS S-3 Part I fills it)'},
        {'metric': f'Largest cohort system by measured corridor demand '
                   f'({top_sys})',
         'year': 2025, 'value': round(agg[top_sys]['cases']),
         'unit': 'top-15 corridor cases', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['e156_hsa_corridors', 'e156_hcris_panel',
                         'e156_pdc_roster'],
         'locator': 'System_Research_Cohort Panel A first data row, col E '
                    '(green-linked to Cohort_Corridors Panel B where '
                    'built)',
         'lives_on': 'System_Research_Cohort',
         'cross_check': 'Matches the Cohort_Corridors roll-up by '
                        'construction (same printed rules, same cache)'},
        {'metric': 'Cohort Form 990 filings parsed with ZERO ambulance / '
                   'EMS / medical-transport contractors among the '
                   'disclosed five highest-paid contractors',
         'year': 2024, 'value': tot_parsed, 'unit': 'filings',
         'basis': 'PUBLIC-WEB', 'tier': 'A',
         'source_keys': ['e156_cohort_990'],
         'locator': f'System_Research_Cohort Panel A 990 row (B{f990_rn}); '
                    f'{tot_eins} EINs, tax years 2022-2024, keyword '
                    'screen printed in cohort_990.json',
         'lives_on': 'System_Research_Cohort',
         'cross_check': 'Part VII Section B discloses only the top five '
                        'over $100K: an information floor, not evidence '
                        'of no vendor'},
        # Tab 2
        {'metric': 'Subject-company registered operating states (printed '
                   'rule: at least one NPPES estate practice location)',
         'year': 2026, 'value': len(reg_states), 'unit': 'states',
         'basis': 'GOV', 'tier': 'A',
         'source_keys': ['e156_nppes_estate'],
         'locator': f'Footprint_Determination Panel E row {e0} '
                    f'(states: {" ".join(reg_sorted)})',
         'lives_on': 'Footprint_Determination',
         'cross_check': 'Two states (IA, NE) independently corroborated '
                        'by named V225 federal awards'},
        {'metric': 'Provisional footprint states carried by earlier tabs '
                   'WITHOUT a registered estate location (KS MN KY)',
         'year': 2026, 'value': len(prov_only), 'unit': 'states',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['e156_nppes_estate'],
         'locator': f'Footprint_Determination Panel E row {gap_rn}; '
                    'reconciliation prose names the tabs',
         'lives_on': 'Footprint_Determination',
         'cross_check': f'Mirror gap: {len(reg_only)} registered states '
                        f'({" ".join(reg_only)}) were absent from the '
                        'provisional list; the live site publishes no '
                        'state-grain claim, so claimed-not-registered '
                        'states observable = 0'},
        # Tab 3
        {'metric': f'Top screened name family by measured transfer demand '
                   f'({top_fam.title()})',
         'year': 2025, 'value': round(top_fam_cases),
         'unit': 'top-15 corridor cases', 'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['e156_hsa_corridors', 'e156_hcris_panel'],
         'locator': f'Prospect_Landscape Panel B first data row (D{p0})',
         'lives_on': 'Prospect_Landscape',
         'cross_check': 'Family-caveat flag applies: a shared-name family '
                        'can span unrelated organizations'},
        {'metric': 'Name families with 3+ hospitals screened in the '
                   'registered footprint states (cohort excluded)',
         'year': 2025, 'value': n_screened, 'unit': 'name families',
         'basis': 'DERIVED', 'tier': 'A',
         'source_keys': ['e156_hcris_panel', 'e156_hsa_corridors'],
         'locator': f'Prospect_Landscape Panel B count row (B{n_rn}); '
                    'grouping rule printed in Panel A',
         'lives_on': 'Prospect_Landscape',
         'cross_check': 'Short-term acute + CAH CCN ranges only; HCRIS '
                        'FY2020-FY2022 name vintage'},
    ]

    findings += [
        {'id_hint': 93,
         'finding': 'What the public record does and does not establish '
                    'about transport sourcing at large multi-hospital '
                    'systems: the measurable side is real - the nine '
                    f'cohort systems aggregate about {round(tot_beds):,} '
                    'staffed beds, their corridor demand is priced live '
                    f'(led by {top_sys} at '
                    f'{round(agg[top_sys]["cases"]):,} top-15 cases), and '
                    'HCRIS ambulance cost-center flags are observable per '
                    'CCN - but the vendor layer is largely invisible: '
                    f'across {tot_parsed} parsed Form 990 filings '
                    f'({tot_eins} EINs), zero ambulance / EMS / '
                    'medical-transport contractors appear in any top-five '
                    'disclosure, '
                    + (f'zero of {len(press_rows)} dated public releases '
                       'in the press registry ties a cohort system to '
                       'the subject company, '
                       if press_rows is not None else '')
                    + 'and no public contract ties any cohort system to '
                    'a specific transport vendor. Transport sourcing at '
                    'these systems sits below the public disclosure '
                    'floor, so its absence from public records carries '
                    'no evidential weight either way.',
         'numbers': f"='System_Research_Cohort'!B{f990_rn}",
         'sources': 'e156_cohort_990; e156_hcris_panel; '
                    'e156_hsa_corridors; e156_pdc_roster; e156_reh_list'
                    + ('; e156_press_registry'
                       if press_rows is not None else ''),
         'confidence': 'High on what was measured; the invisibility claim '
                       'is a property of the disclosure regime, not an '
                       'inference about any vendor',
         'guardrail': 'Part VII Section B discloses only the five '
                      'highest-paid contractors over $100K per filing; '
                      'name-match rosters carry printed confounds; the '
                      'group is strictly a ' + COHORT_FRAME + ' and no '
                      'organization is described as anyone\'s customer '
                      'or account.'},
        {'id_hint': 94,
         'finding': 'The subject company\'s canonical public footprint is '
                    f'{len(reg_states)} states ({" ".join(reg_sorted)}), '
                    'determined by a printed rule - at least one NPPES '
                    'registered estate practice location - with IA and NE '
                    'independently corroborated by named federal V225 '
                    'awards. The working list earlier tabs used differs '
                    f'in {len(prov_only) + len(reg_only)} states: '
                    f'{" ".join(prov_only)} were carried without any '
                    f'registration and {" ".join(reg_only)} are '
                    'registered but were not sliced; the company\'s own '
                    'site claims a national posture without naming one '
                    'state, so registrations are the only state-grain '
                    'public evidence.',
         'numbers': f"='Footprint_Determination'!B{e0}",
         'sources': 'e156_nppes_estate; e156_usasp_v225; e156_mmt_site; '
                    'e156_wayback',
         'confidence': 'High on registrations (live NPPES pulls); '
                       'website and Wayback layers are labeled '
                       'self-claims and a PENDING series',
         'guardrail': 'A registration is a billing/practice location, '
                      'not a station, service area or volume; eight '
                      'states rest on a single NPI each; the Wayback '
                      'claimed-footprint series is unextracted '
                      '(PENDING).'},
        {'id_hint': 95,
         'finding': 'Measured transfer demand outside the research cohort '
                    f'concentrates in a screenable top tier: {n_screened} '
                    'multi-hospital name families operate in the '
                    'registered footprint states, led by '
                    f'{top3[0].title()} at {round(top_fam_cases):,} '
                    f'top-15 corridor cases, then {top3[1].title()} and '
                    f'{top3[2].title()} - additional multi-hospital '
                    'systems in the footprint, screened by measured '
                    'transfer demand, each row carrying its hub count '
                    'and family-caveat flag.',
         'numbers': f"='Prospect_Landscape'!D{p0}",
         'sources': 'e156_hcris_panel; e156_hsa_corridors',
         'confidence': 'Moderate: ranking is robust to the grouping rule '
                       'at the top, but flagged families can merge '
                       'unrelated organizations',
         'guardrail': 'A screen over public rosters and Medicare FFS '
                      'corridor floors - not corporate attribution, not '
                      'a transfer matrix, and no statement about any '
                      'organization\'s vendors, relationships or intent.'},
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'tabs': {'System_Research_Cohort': t1_max,
                              'Footprint_Determination': t2_max,
                              'Prospect_Landscape': t3_max},
                     'cohort_order': order,
                     'tot_beds': round(tot_beds),
                     'tot_days': round(tot_days),
                     'tot_990_parsed': tot_parsed,
                     'reg_states': reg_sorted,
                     'prov_only': prov_only, 'reg_only': reg_only,
                     'usasp_pop_states': sorted(usasp_pop),
                     'n_screened': n_screened,
                     'top_families': [(k, round(fam_row(k, v)[0]))
                                      for k, v in ranked[:5]],
                     'links': {'cohort_corridors': bool(panel_b),
                               'a5': has('HCRIS_Ambulance_CostCenters'),
                               'tdb': has('Transfer_Delay_Burden'),
                               'e23': has('Cohort_990_Contractors'),
                               'whitespace':
                                   has('County_Whitespace_Screens'),
                               'press': press_rows is not None}}}
