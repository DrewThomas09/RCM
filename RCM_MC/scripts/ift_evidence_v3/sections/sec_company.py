"""Group C — Company & competitive (PUBLIC-WEB material loudly labeled).

Tabs: MMT_NPI_Estate (ift_company.MMT_NPI_LOCATIONS, 23 SOURCED NPPES rows),
Company_Dossier (ift_company: 16 cited sources, ownership timeline 1987-2026,
scale claims, court records, revenue-estimate CONFLICT EXHIBIT),
Competitor_Registry (ift_npi_landscape.COMPETITORS 7 profiles / 28 NPIs +
supply-landscape denominators), Payment_Integrity (CERT split, RSNAT natural
experiment, OIG 2002-11 + 2015 findings), Contract_Benchmarks (911/NEMT
SLA-and-penalty precedents + CA AB 40, re-verify flags loud).

EXCLUDED by design: every modeled market-share / moat-score / serviceable-
share column from ift_competitive / ift_moat / ift_insourcing (see excluded).
"""
import sys

sys.path.insert(0, '/home/user/RCM/RCM_MC')
sys.path.insert(0, '/home/user/RCM')

GREY = 'FF555555'

SHEETS = [
    {'name': 'MMT_NPI_Estate', 'tab_color': GREY},
    {'name': 'Company_Dossier', 'tab_color': GREY},
    {'name': 'Competitor_Registry', 'tab_color': GREY},
    {'name': 'Payment_Integrity', 'tab_color': GREY},
    {'name': 'Contract_Benchmarks', 'tab_color': GREY},
]


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, notes = [], [], [], []

    from rcm_mc.market_reports import ift_company as co
    from rcm_mc.market_reports import ift_npi_landscape as nl

    co_srcs = {s.key: s for s in (getattr(co, '_SOURCES', None)
                                  or tuple(co.SOURCES.values()))}

    def cs(key):
        """Company-source label + URL by key (ift_company.SOURCES)."""
        s = co_srcs[key]
        return s.label, s.url

    # ── Source register entries (integrator assigns S-IDs; keys stable) ─────
    sources += [
        {'key': 'nppes_mmt', 'publisher': 'CMS',
         'document': 'NPPES NPI Registry — organizational-NPI sweep for '
                     '"Midwest Medical Transport" + "Platte County Ambulance" '
                     '(taxonomy 341600000X unless noted per row)',
         'vintage': 'Registry snapshot pulled 2026-07-10',
         'locator': 'npiregistry.cms.hhs.gov API/UI search by organization '
                    'name; 23 active org NPIs captured with address, DBA, '
                    'enumeration date (where shown) and authorized official; '
                    'carried in rcm_mc/market_reports/ift_company.py::'
                    'MMT_NPI_LOCATIONS',
         'supplies': 'The verified MMT location estate: 23 NPIs across 11 '
                     'states (NE 4 / IA 9 / SD 2 / MO OH IN WI CO RI NC VA '
                     '1 each; VA link unconfirmed)',
         'url': 'https://npiregistry.cms.hhs.gov/',
         'tier': 'B', 'accessed': accessed,
         'powers': ['MMT_NPI_Estate', 'Company_Dossier']},
        {'key': 'nppes_neia', 'publisher': 'CMS',
         'document': 'NPPES NPI Registry — NE+IA ambulance-organization sweep '
                     "(taxonomy 'Ambulance', NPI-2 organizational), 751 org "
                     'NPIs; plus curated competitor-NPI lookups from the same '
                     'registry',
         'vintage': 'Vendored 2026-07-10',
         'locator': 'rcm_mc/market_reports/reference/'
                    'nppes_ambulance_orgs_ne_ia_20260710.csv (751 rows; '
                    'category column keyword-classified — caveat travels); '
                    'competitor NPI tuples in ift_npi_landscape.COMPETITORS',
         'supplies': 'The NE/IA supply-side denominator (751 org NPIs, '
                     'category x state matrix) and the 28 competitor NPIs',
         'url': 'https://npiregistry.cms.hhs.gov/',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Competitor_Registry']},
        {'key': 'hpc_2022', 'publisher': 'Businesswire / Harbour Point Capital',
         'document': "'Harbour Point Capital Completes Investment in Midwest "
                     "Medical Transport', press release",
         'vintage': 'Jan 25, 2022',
         'locator': 'Release text: scope quote (ALS/BLS IFT + specialty to '
                    'health systems, CAHs, LTC), 200,000+ missions/yr, '
                    'then-10-states framing',
         'supplies': '2022 recapitalization event + deal-time scale claims',
         'url': 'https://www.businesswire.com/news/home/20220125006174/en/',
         'tier': 'B', 'accessed': accessed, 'powers': ['Company_Dossier']},
        {'key': 'lincoln_intl', 'publisher': 'Lincoln International',
         'document': 'Sell-side transaction notice: Panorama Point / Dixon '
                     'Midland / ORIX sale of MMT to Harbour Point Capital',
         'vintage': '2022',
         'locator': 'Transaction page: "seven states and nearly 1,000 '
                    'employees" — conflicts with the 10-state release '
                    'framing; shown side-by-side, never blended',
         'supplies': 'Advisor-side 2022 scale framing (7 states, ~1,000 '
                     'employees)',
         'url': 'https://www.lincolninternational.com/transactions/'
                'panorama-point-partners-dixon-midland-and-orix-have-sold-'
                'midwest-medical-transport-to-harbour-point-capital/',
         'tier': 'B', 'accessed': accessed, 'powers': ['Company_Dossier']},
        {'key': 'mmt_web', 'publisher': 'MMT Ambulance (company self-report)',
         'document': 'mmtamb.com About Us / Careers pages + Siouxland Chamber '
                     'member directory entry',
         'vintage': '2026 (site as captured 2026-07-10)',
         'locator': 'About Us: 13 states, 2,800+ team members, 500+ vehicles, '
                    '"over 35 years"; Chamber directory: verbatim "not a 911 '
                    'service" positioning quote',
         'supplies': 'Current company scale claims + positioning (PUBLIC-WEB '
                     'self-report — never a measurement)',
         'url': 'https://mmtamb.com/about-us/',
         'tier': 'B', 'accessed': accessed, 'powers': ['Company_Dossier']},
        {'key': 'ciatto_2023', 'publisher': 'Businesswire / MMT Ambulance',
         'document': "'MMT Ambulance Appoints Chris Ciatto as New CEO', "
                     'press release',
         'vintage': 'Apr 5, 2023',
         'locator': 'Release text (CEO appointment; expansion-wave framing)',
         'supplies': '2023 leadership event on the ownership timeline',
         'url': 'https://www.businesswire.com/news/home/20230405005703/en/',
         'tier': 'B', 'accessed': accessed, 'powers': ['Company_Dossier']},
        {'key': 'mmt_local_news', 'publisher':
            'Lincoln Journal Star / Omaha World-Herald / Columbus Telegram',
         'document': 'Local press: "Private equity firm buys Nebraska '
                     'ambulance company" (LJS, Feb 2015); OWH retrospective '
                     'on the 2015 sale (founding story); OWH "Air ambulance '
                     'team adds Hastings-based helicopter" (Midwest MedAir)',
         'vintage': '2015 (sale + founding retrospective); MedAir article '
                    'undated on capture',
         'locator': 'Article text: 1987 founding ("with one ambulance, doing '
                    'a few transfers a week out of the Columbus Hospital"); '
                    '2015 sale detail (350+ employees, 13 ground locations, '
                    '2 helicopter bases); MedAir 30,000 ground + 400+ '
                    'helicopter calls in a reported year',
         'supplies': 'Founding + 2015 ownership events and deal-time scale',
         'url': 'https://journalstar.com/business/local/private-equity-firm-'
                'buys-nebraska-ambulance-company/article_f17387c0-ec6f-5872-'
                'b159-3c99a212dd03.html',
         'tier': 'B', 'accessed': accessed, 'powers': ['Company_Dossier']},
        {'key': 'court_dockets', 'publisher':
            'U.S. District Courts (via Justia / CourtListener) + NLRB',
         'document': 'Public dockets: Meysenburg v. MMT, D. Neb. '
                     '4:2024-cv-03107 (filed 2024-06-11); Wroblewski v. MMT, '
                     'E.D. Wis. 2:23-cv-00877 (filed 2023-07-03); Reust v. '
                     'MMT, N.D. Ohio 1:20-cv-01548 (filed 2020-07-14); NLRB '
                     'Case 14-CA-251082 (Wichita KS, filed 2019-11-04, '
                     'closed)',
         'vintage': 'Filings 2019-2024; docket pages pulled 2026-07-10',
         'locator': 'Docket captions + filing dates as listed; outcomes '
                    'sealed without PACER (stated on-sheet)',
         'supplies': 'The litigation register: 3 FLSA wage-and-hour suits + '
                     '1 NLRB ULP charge',
         'url': 'https://dockets.justia.com/docket/nebraska/nedce/'
                '4:2024cv03107/103544',
         'tier': 'B', 'accessed': accessed, 'powers': ['Company_Dossier']},
        {'key': 'revenue_estimators', 'publisher':
            'Growjo / ZoomInfo / LeadIQ (third-party estimators)',
         'document': 'Unaudited third-party revenue/headcount estimates for '
                     'MMT (three conflicting profiles)',
         'vintage': '2026 (LeadIQ as of Jun 2026)',
         'locator': 'Growjo $296.4M / 784 employees; ZoomInfo $293.6M / '
                    '1,000-5,000; LeadIQ $100M-$250M / ~700 — ~3x '
                    'disagreement; rendered ONLY as a conflict exhibit, '
                    'labeled not usable as fact',
         'supplies': 'The revenue-estimate CONFLICT EXHIBIT (quarantined; '
                     'no Fact_Ledger entry)',
         'url': 'https://growjo.com/company/Midwest_Medical_Transport',
         'tier': 'B', 'accessed': accessed, 'powers': ['Company_Dossier']},
        {'key': 'medpac_pb2024', 'publisher': 'MedPAC',
         'document': 'Payment Basics: Ambulance Services Payment System',
         'vintage': 'October 2024 (2024 data year)',
         'locator': 'Payment Basics text: Medicare FFS ground ambulance '
                    '11.3M transports, $5.3B payments, ~10,600 billing '
                    'organizations (2024)',
         'supplies': 'The national supplier-fragmentation denominator '
                     '(~10,600 orgs)',
         'url': 'https://www.medpac.gov/wp-content/uploads/2024/10/'
                'MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf',
         'tier': 'B', 'accessed': accessed, 'powers': ['Competitor_Registry']},
        {'key': 'ne_dhhs_ems', 'publisher': 'Nebraska DHHS',
         'document': 'Nebraska Statewide EMS Assessment (2023-24, v2024)',
         'vintage': '2023-24 assessment cycle (re-verify: excerpt-grade '
                    'capture)',
         'locator': 'Assessment findings: 80%+ of NE EMS agencies '
                    'all-volunteer; 31% of volunteer agencies report adequate '
                    'staffing; 28% expect to be unable to operate within 5 '
                    'years; verbatim excess-agencies quote',
         'supplies': 'The volunteer-collapse statistics + excess-agencies '
                     'finding',
         'url': 'https://dhhs.ne.gov/OEHS%20Program%20Documents/'
                'NE%20Statewide%20EMS%20Assessment%20v2024.pdf',
         'tier': 'B', 'accessed': accessed, 'powers': ['Competitor_Registry']},
        {'key': 'ameripro_pr', 'publisher': 'PRNewswire / AmeriPro Health',
         'document': "'AmeriPro Health Acquires Priority Medical Transport "
                     "and Expands Midwest Presence', press release",
         'vintage': 'February 2025',
         'locator': 'Release text: Whistler Capital-backed AmeriPro acquires '
                    'North Platte-based Priority Medical Transport; stated NE '
                    'counties Lincoln, Red Willow, Buffalo, Dawson, Adams, '
                    'Dodge, Platte',
         'supplies': 'The PE-backed challenger entry event + county list',
         'url': 'https://www.prnewswire.com/news-releases/ameripro-health-'
                'acquires-priority-medical-transport-and-expands-midwest-'
                'presence-302372373.html',
         'tier': 'B', 'accessed': accessed, 'powers': ['Competitor_Registry']},
        {'key': 'competitor_web', 'publisher':
            'Operator/municipal websites (per-profile source URLs)',
         'document': 'Air Methods (LifeNet of the Heartland program page); '
                     'City of Sioux City fire-rescue EMS page; Omaha Fire '
                     'Department EMS page; Children\'s Nebraska transport / '
                     'critical care page',
         'vintage': 'As captured 2026-07-10 (public-web; some figures '
                    'flagged dated/historical in the read text)',
         'locator': 'Per-profile source_url column on the tab; embedded '
                    'quantities (e.g. 18 ALS ambulances, 10,000+ patients/yr, '
                    '~35 vehicles historical) are PUBLIC-WEB claims',
         'supplies': 'The qualitative competitor reads (PUBLIC-WEB chips)',
         'url': 'https://www.airmethods.com/air-medical/program/'
                'lifenet-of-the-heartland/',
         'tier': 'B', 'accessed': accessed, 'powers': ['Competitor_Registry']},
        {'key': 'cms_mup_prov', 'publisher': 'CMS (data.cms.gov)',
         'document': 'Medicare Physician & Other Practitioners — by Provider '
                     'and Service (annual PUFs; claims-pull recipe target, '
                     'NO data carried)',
         'vintage': 'CY2020-CY2023 dataset UUIDs registered (2020 c957b49e-'
                    '1323-49e7-8678-c09da387551d; 2021 31dc2c47-f297-4948-'
                    'bfb4-075e1bec3a02; 2022 e650987d-01b7-4f09-b75e-'
                    'b0b075afbf98; 2023 92396110-2aed-4d63-a6a2-5d6207d46a29)',
         'locator': 'ift_npi_landscape.CLAIMS_RECIPE: endpoint template, '
                    'HCPCS A0425-A0434 filter grammar; egress to data.cms.gov '
                    'policy-blocked from this environment (proxy CONNECT 403 '
                    'verified 2026-07-10) — methods block only',
         'supplies': 'The documented next-pull spec that would join supplier '
                     'volumes/payments to the 751-NPI registry (methods, no '
                     'numbers)',
         'url': 'https://data.cms.gov/provider-summary-by-type-of-service/'
                'medicare-physician-other-practitioners',
         'tier': 'B', 'accessed': accessed, 'powers': ['Competitor_Registry']},
        {'key': 'cert_2024', 'publisher': 'CMS',
         'document': 'Comprehensive Error Rate Testing (CERT) — 2024 Medicare '
                     'FFS Supplemental Improper Payment Data, ambulance '
                     'service type (RE-VERIFY: excerpt-grade capture; reopen '
                     'the supplemental tables before circulation)',
         'vintage': '2024 report year',
         'locator': 'Ambulance improper-payment rate 13.2%; projected '
                    '$595.1M; error composition 63.5% insufficient '
                    'documentation / 27.5% medical necessity',
         'supplies': 'The improper-payment split on Payment_Integrity',
         'url': 'https://www.cms.gov/data-research/monitoring-programs/'
                'improper-payment-measurement-programs/'
                'comprehensive-error-rate-testing-cert',
         'tier': 'B', 'accessed': accessed, 'powers': ['Payment_Integrity']},
        {'key': 'contreary_2022', 'publisher': 'JAMA Health Forum',
         'document': 'Contreary K. et al., "Effect of Prior Authorization on '
                     'Repetitive Scheduled Non-Emergent Ambulance Transport" '
                     '(RSNAT model evaluation, ESRD cohort)',
         'vintage': '2022',
         'locator': 'doi:10.1001/jamahealthforum.2022.2093 — verbatim '
                    'effects: "61% reduction in the probability of RSNAT '
                    'use"; "77% reduction in RSNAT expenditures ($1136 per '
                    'beneficiary-year)"; "19% annual increase in the '
                    'probability of emergency dialysis use"',
         'supplies': 'The RSNAT natural-experiment table',
         'url': 'https://doi.org/10.1001/jamahealthforum.2022.2093',
         'tier': 'B', 'accessed': accessed, 'powers': ['Payment_Integrity']},
        {'key': 'cms_rsnat', 'publisher': 'CMS',
         'document': 'RSNAT prior-authorization program rules + MLN6805343 '
                     'fact sheet (Jan 2026)',
         'vintage': 'Program nationwide since Aug 1, 2022; fact sheet Jan '
                    '2026',
         'locator': 'Repetitive definition (3+ round trips in 10 days, or '
                    '1+/week for 3+ weeks); affirmation covers 120 round '
                    'trips / 180 days; national scope covers A0426 + A0428',
         'supplies': 'The RSNAT definitions block',
         'url': 'https://www.cms.gov/data-research/monitoring-programs/'
                'medicare-fee-service-compliance-programs/prior-authorization'
                '-and-pre-claim-review-initiatives/prior-authorization-'
                'repetitive-scheduled-non-emergent-ambulance-transport-rsnat',
         'tier': 'B', 'accessed': accessed, 'powers': ['Payment_Integrity']},
        {'key': 'oig_350', 'publisher': 'HHS Office of Inspector General',
         'document': 'OEI-09-12-00350 — "Utilization of Medicare Ambulance '
                     'Transports, 2002-2011"',
         'vintage': 'Report 2013 (data 2002-2011)',
         'locator': 'Report findings: Medicare ambulance transports +69% '
                    '2002-2011; dialysis-related transports +269% over the '
                    'same window',
         'supplies': 'The pre-RSNAT utilization-growth series (endpoint '
                     'growth; trend broken by RSNAT — flagged)',
         'url': 'https://oig.hhs.gov/oei/reports/oei-09-12-00350.asp',
         'tier': 'B', 'accessed': accessed, 'powers': ['Payment_Integrity']},
        {'key': 'oig_351', 'publisher': 'HHS Office of Inspector General',
         'document': 'OEI-09-12-00351 — "Inappropriate Payments and '
                     'Questionable Billing for Medicare Part B Ambulance '
                     'Transports" (first half of 2012 claims)',
         'vintage': 'Report 2015 (data H1-2012)',
         'locator': 'Findings: $24M paid for transports not meeting program '
                    'requirements; $30.2M where the beneficiary received no '
                    'Medicare service at origin or destination; $7.1M '
                    'level/destination mismatch; $4.3M SCT between '
                    'non-hospital origins/destinations; 21% (about 1 in 5) '
                    'of suppliers met >=1 of 7 questionable-billing measures; '
                    '4 metro areas = 18% of transports but 52% of '
                    'questionable transports (~$207M)',
         'supplies': 'The questionable-billing findings block',
         'url': 'https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf',
         'tier': 'B', 'accessed': accessed, 'powers': ['Payment_Integrity']},
        {'key': 'muni_911', 'publisher':
            'Municipal contract records (Pasadena TX; Multnomah County OR; '
            'City of San Diego / Falck)',
         'document': 'Urban 911 EMS performance contracts + NFPA 1710 norms '
                     '(RE-VERIFY: carried from the repo contracting dossier, '
                     'excerpt-grade; reopen the municipal documents before '
                     'circulation)',
         'vintage': 'Contracts current as captured 2026-07-10',
         'locator': '8:59 response at the 90% fractile (urban norm); '
                    'Pasadena TX 8:59/90% with 14:59 cap; Multnomah County '
                    'penalties below 90%; San Diego/Falck $5,000 per response '
                    'beyond 24 minutes',
         'supplies': 'The 911 SLA/penalty precedent rows',
         'url': '',
         'tier': 'B', 'accessed': accessed, 'powers': ['Contract_Benchmarks']},
        {'key': 'nemt_broker_tx', 'publisher':
            'Texas HHSC + state NEMT broker contracts',
         'document': 'Texas Medical Transportation Program contract terms; '
                     'state NEMT broker contract standards (RE-VERIFY: '
                     'excerpt-grade captures, no URL on file)',
         'vintage': 'As captured 2026-07-10',
         'locator': 'TX: 85% on-time-pickup benchmark with a $15,000 penalty '
                    'cap; broker contracts commonly run >=95% on-time-pickup '
                    'standards with penalties',
         'supplies': 'The NEMT SLA precedent rows',
         'url': '',
         'tier': 'B', 'accessed': accessed, 'powers': ['Contract_Benchmarks']},
        {'key': 'nemt_enforcement', 'publisher':
            'State enforcement records via Mississippi Today (Sep 2024) + '
            'NJ / GA state records',
         'document': 'NEMT broker enforcement coverage (RE-VERIFY: '
                     'press-carried state records)',
         'vintage': 'MS audit coverage Sep 2024; NJ fines 2017-22; GA fines '
                    '2018-20',
         'locator': 'Mississippi: ~3,000 of >52,000 monthly trips late or '
                    'missed (~5.8%), ~3x the contractual limit; NJ fined '
                    'Modivcare ~$1.7M (2017-22); GA fined brokers >$1M '
                    '(2018-20)',
         'supplies': 'The NEMT enforcement precedent rows',
         'url': '',
         'tier': 'B', 'accessed': accessed, 'powers': ['Contract_Benchmarks']},
        {'key': 'ca_ab40', 'publisher': 'State of California / EMSA',
         'document': 'AB 40 (2023) — ambulance patient offload time (APOT) '
                     'standard; EMSA APOT monitoring program (RE-VERIFY '
                     'flag carried from the repo module)',
         'vintage': '2023 statute; program current',
         'locator': 'Offload standard not to exceed 30 minutes 90% of the '
                    'time, with monthly per-hospital EMSA monitoring',
         'supplies': 'The statutory offload-clock precedent row',
         'url': 'https://emsa.ca.gov/apot/',
         'tier': 'B', 'accessed': accessed, 'powers': ['Contract_Benchmarks']},
        {'key': 'ca_hs_1797224', 'publisher': 'State of California',
         'document': 'Health & Safety Code section 1797.224 — exclusive '
                     'operating areas awarded through a competitive process',
         'vintage': 'Current statute',
         'locator': 'H&S 1797.224 (EOA competitive-award authority)',
         'supplies': 'The EOA procurement-cadence precedent row',
         'url': 'https://leginfo.legislature.ca.gov/faces/'
                'codes_displaySection.xhtml?lawCode=HSC&sectionNum=1797.224',
         'tier': 'B', 'accessed': accessed, 'powers': ['Contract_Benchmarks']},
        {'key': 'modivcare_ch11', 'publisher':
            'U.S. Bankruptcy Court S.D. Tex. (docket) + deal coverage',
         'document': 'Modivcare Inc. Chapter 11 (RE-VERIFY: docket + '
                     'coverage capture, no URL on file)',
         'vintage': 'Filed Aug 20, 2025; emerged Dec 29, 2025',
         'locator': 'Emergence cut >$1.1B of ~$1.4B funded debt — the '
                    'vendor-financial-stability precedent',
         'supplies': 'Context row: why vendor stability is an evaluation '
                     'criterion in transport contracts',
         'url': '',
         'tier': 'B', 'accessed': accessed, 'powers': ['Contract_Benchmarks']},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 1 — MMT_NPI_Estate
    # ════════════════════════════════════════════════════════════════════════
    locs = list(co.MMT_NPI_LOCATIONS)
    ws = wb.create_sheet('MMT_NPI_Estate')
    NC1 = 9
    sb = lib.SheetBuilder(
        ws, NC1, col_widths=[12, 42, 24, 15, 6, 14, 13, 12, 62],
        tab_color=GREY)
    sb.title('MMT NPI estate: the federally registered footprint '
             '(NPPES, pulled 2026-07-10)')
    sb.subtitle(
        'The question: which MMT (Midwest Medical Transport Company, LLC / '
        '"MMT Ambulance") locations are verifiable in the federal NPI '
        'registry — and how does that verified estate compare with the '
        'company\'s 13-state marketing claim? Every Panel A row is SOURCED '
        'from the CMS NPPES registry (org-NPI sweep for "Midwest Medical '
        'Transport" + "Platte County Ambulance", taxonomy 341600000X unless '
        'noted, pulled 2026-07-10). Roll-ups and the enumeration timeline '
        'are live formulas. Panel D web-listed stations are PUBLIC-WEB '
        'company self-report — kept separate and never added to the NPI '
        'counts.')
    sb.blank()
    sb.banner('Panel A. 23 active organizational NPIs (CMS NPPES registry '
              'sweep, 2026-07-10)')
    sb.headers(['NPI', 'NPPES organization name / DBA', 'Registered address',
                'City', 'State', 'Enumeration date', 'Estate class', 'Basis',
                'Note — authorized officials, Medicaid IDs, flags (verbatim '
                'from capture)'])
    a0 = sb.r + 1
    for l in locs:
        est = 'legacy core' if l.legacy_core else 'expansion'
        sb.row([
            (l.npi, 'src'), (l.name, 'src'), (l.address, 'src'),
            (l.city, 'src'), (l.state, 'src'),
            (l.enumerated if l.enumerated else '(not captured)',
             'src' if l.enumerated else 'note'),
            (est, 'src'), ('SOURCED', 'src'),
            (l.note, 'note'),
        ], wrap=True)
    a1 = sb.r
    r = sb.r + 1
    sb.row([('Total active org NPIs (live COUNTA)', 'label'),
            (f'=COUNTA(A{a0}:A{a1})', 'fml', lib.FMT_INT), None, None, None,
            None, None, None, ('DERIVED over the SOURCED rows', 'note')])
    r_npi_tot = sb.r
    r = sb.r + 1
    sb.row([('Legacy-core NPIs (NE / IA / SD)', 'label'),
            (f'=COUNTIF(G{a0}:G{a1},"legacy core")', 'fml', lib.FMT_INT),
            None, None, None, None, None, None,
            ('DERIVED — expected 15 (NE 4, IA 9, SD 2)', 'note')])
    r_legacy = sb.r
    r = sb.r + 1
    sb.row([('Expansion NPIs (MO OH IN WI CO RI NC VA)', 'label'),
            (f'=COUNTIF(G{a0}:G{a1},"expansion")', 'fml', lib.FMT_INT),
            None, None, None, None, None, None,
            ('DERIVED — expected 8 (1 per state; VA flagged)', 'note')])
    r_expan = sb.r
    r = sb.r + 1
    sb.row([('Distinct NPI states (live SUMPRODUCT)', 'label'),
            (f'=SUMPRODUCT(1/COUNTIF(E{a0}:E{a1},E{a0}:E{a1}))', 'fml',
             lib.FMT_INT),
            None, None, None, None, None, None,
            ('DERIVED — 11 NPI states vs the 13-state company claim '
             '(Company_Dossier)', 'note')])
    r_states = sb.r

    sb.blank()
    sb.banner('Panel B. State roll-up (live COUNTIF over Panel A)')
    sb.headers(['State', 'Org NPIs (COUNTIF)', 'Estate class', '', '', '', '',
                '', 'Note'])
    b0 = sb.r + 1
    state_class = {'NE': 'legacy core', 'IA': 'legacy core',
                   'SD': 'legacy core'}
    for st in co.npi_states():
        r = sb.r + 1
        note = ''
        if st == 'VA':
            note = ('Virginia Beach record 1922872134: same-org link '
                    'UNCONFIRMED (near-identical 800-number only) — treat '
                    'the 11-state span as a ceiling.')
        sb.row([
            (st, 'src'),
            (f'=COUNTIF($E${a0}:$E${a1},$A{r})', 'fml', lib.FMT_INT),
            (state_class.get(st, 'expansion'), 'text'),
            None, None, None, None, None, (note, 'note'),
        ], wrap=bool(note))
    b1 = sb.r
    r = sb.r + 1
    sb.row([('Total', 'label'), (f'=SUM(B{b0}:B{b1})', 'fml', lib.FMT_INT),
            None, None, None, None, None, None,
            (f'DERIVED — must equal B{r_npi_tot} (23)', 'note')])
    r_state_tot = sb.r

    sb.blank()
    sb.banner('Panel C. Enumeration timeline — dated NPIs only (8 of 23 '
              'carry an enumeration date in the capture)')
    sb.headers(['Year', 'NPIs enumerated (COUNTIF year*)',
                'Cumulative dated NPIs', '', '', '', '', '', 'Note'])
    c0 = sb.r + 1
    for yr in range(2005, 2025):
        r = sb.r + 1
        sb.row([
            (yr, 'text', lib.FMT_INT),
            (f'=COUNTIF($F${a0}:$F${a1},$A{r}&"*")', 'fml', lib.FMT_INT),
            (f'=SUM($B${c0}:$B{r})', 'fml', lib.FMT_INT),
            None, None, None, None, None, None,
        ])
    c1 = sb.r
    r = sb.r + 1
    sb.row([('(date not captured)', 'label'),
            (f'=COUNTIF($F${a0}:$F${a1},"(not captured)")', 'fml',
             lib.FMT_INT),
            None, None, None, None, None, None,
            ('15 of 23 NPI records had no enumeration date in the sweep — '
             'the timeline is a FLOOR of registration activity, not a '
             'volume series', 'note')], wrap=True)
    r_undated = sb.r
    sb.note('Trend eligibility: NO — enumeration events are registry '
            'registrations (entity restructures, DBAs and subparts included),'
            ' not operating volumes; 15 of 23 records are undated. Do not '
            'trend or CAGR this panel. Dated span runs 2005 (Platte County '
            'Ambulance predecessor, 2005-11-03) to 2024 (Kansas City MO, '
            '2024-03-18); the 2023-24 cluster (Des Moines Aug 2023, Omaha '
            'Nov 2023, KC Mar 2024) matches the post-2022 expansion wave on '
            'Company_Dossier.')

    sb.blank()
    sb.banner('Panel D. Web-listed stations NOT in the NPI estate — '
              'PUBLIC-WEB company self-report (subparts often bill under a '
              'parent NPI; never added to NPI counts)')
    sb.headers(['City', 'State', '', '', '', '', '', 'Basis', 'Note'])
    d0 = sb.r + 1
    for city, st in co.MMT_WEB_STATIONS:
        sb.row([(city, 'src'), (st, 'src'), None, None, None, None, None,
                ('PUBLIC-WEB', 'text'),
                ('Company site station listing (mmtamb.com), captured '
                 '2026-07-10', 'note')])
    d1 = sb.r
    r = sb.r + 1
    sb.row([('Web-listed stations (live COUNTA)', 'label'),
            (f'=COUNTA(A{d0}:A{d1})', 'fml', lib.FMT_INT), None, None, None,
            None, None, None, ('DERIVED', 'note')])
    r_web_tot = sb.r

    sb.blank()
    sb.note('Reconciliation flags (must travel): (1) the ift_company module '
            'docstring says "24 active organizational NPIs" but the record '
            'tuple and the company scale-claims row both carry 23 — this tab '
            'carries 23 and the discrepancy is queued for a fresh NPPES '
            're-pull. (2) Virginia Beach NPI 1922872134 ("Midwest Medical '
            'Transport LLC") is flagged: same-org link unconfirmed — the '
            '11-state NPI span is a ceiling, 10 confirmed. (3) NPPES shows '
            'registration, not activity: an NPI can be active with zero '
            'current volume.')
    sb.note('Citation: CMS NPPES NPI Registry (npiregistry.cms.hhs.gov), '
            'organizational-NPI sweep for "Midwest Medical Transport" + '
            '"Platte County Ambulance", taxonomy 341600000X unless noted in '
            'the row; registry snapshot pulled 2026-07-10. Extraction: '
            'rcm_mc/market_reports/ift_company.py::MMT_NPI_LOCATIONS / '
            f'legacy_core_locations() / expansion_locations(), {accessed}.')

    lib.add_chart(
        ws, f'K{b0}', 'MMT org NPIs by state (NPPES, 2026-07-10)',
        f'MMT_NPI_Estate!$A${b0}:$A${b1}',
        [('Org NPIs', f'MMT_NPI_Estate!$B${b0}:$B${b1}')],
        kind='bar', height=10)
    lib.add_chart(
        ws, f'K{b0 + 22}', 'Cumulative dated NPI enumerations, 2005-2024 '
        '(8 dated of 23 — a floor, not a volume series)',
        f'MMT_NPI_Estate!$A${c0}:$A${c1}',
        [('Cumulative dated NPIs', f'MMT_NPI_Estate!$C${c0}:$C${c1}')],
        kind='line', height=10)

    facts += [
        {'metric': 'MMT active organizational NPIs (verified estate)',
         'year': 2026, 'value_ref': f'MMT_NPI_Estate!B{r_npi_tot}',
         'unit': 'org NPIs', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['nppes_mmt'],
         'locator': 'NPPES org-NPI sweep 2026-07-10; live COUNTA over the '
                    '23 Panel A rows',
         'lives_on': 'MMT_NPI_Estate',
         'cross_check': 'ift_company.SCALE_CLAIMS carries 23; module '
                        'docstring says 24 — discrepancy flagged on-sheet'},
        {'metric': 'Distinct MMT NPI states (vs 13-state company claim)',
         'year': 2026, 'value_ref': f'MMT_NPI_Estate!B{r_states}',
         'unit': 'states', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['nppes_mmt'],
         'locator': 'Live SUMPRODUCT distinct-count over Panel A state '
                    'column = 11 (NE IA SD MO OH IN WI CO RI NC VA; VA '
                    'unconfirmed)',
         'lives_on': 'MMT_NPI_Estate',
         'cross_check': 'Company claims 13 states (Company_Dossier scale '
                        'claims) — a 2-state gap the registry cannot verify'},
        {'metric': 'MMT legacy-core NPIs (NE/IA/SD)',
         'year': 2026, 'value_ref': f'MMT_NPI_Estate!B{r_legacy}',
         'unit': 'org NPIs', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['nppes_mmt'],
         'locator': 'COUNTIF estate class = "legacy core" (15: NE 4, IA 9, '
                    'SD 2)',
         'lives_on': 'MMT_NPI_Estate',
         'cross_check': 'ift_company.legacy_core_locations() returns 15'},
        {'metric': 'MMT expansion-state NPIs (2023-24 wave)',
         'year': 2026, 'value_ref': f'MMT_NPI_Estate!B{r_expan}',
         'unit': 'org NPIs', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['nppes_mmt'],
         'locator': 'COUNTIF estate class = "expansion" (8: MO OH IN WI CO '
                    'RI NC VA, 1 each)',
         'lives_on': 'MMT_NPI_Estate',
         'cross_check': 'ift_company.expansion_locations() returns 8; VA '
                        'record flagged unconfirmed'},
        {'metric': 'Earliest MMT-lineage enumeration (Platte County '
                   'Ambulance predecessor)',
         'year': 2005, 'value': '2005-11-03', 'unit': 'date',
         'basis': 'SOURCED', 'tier': 'B', 'source_keys': ['nppes_mmt'],
         'locator': 'NPI 1689665143, Platte County Ambulance Company DBA '
                    'Midwest Medical Transport Co, enumerated 2005-11-03',
         'lives_on': 'MMT_NPI_Estate',
         'cross_check': 'Consistent with the 1987 founding story '
                        '(Company_Dossier) — NPPES itself only began 2005'},
        {'metric': 'MMT web-listed stations outside the NPI estate',
         'year': 2026, 'value_ref': f'MMT_NPI_Estate!B{r_web_tot}',
         'unit': 'stations', 'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['nppes_mmt'],
         'locator': '11 company-site station listings (8 NE + Iowa City, '
                    'Tea SD, Cincinnati OH) with no own NPI — subparts '
                    'typically bill under a parent NPI',
         'lives_on': 'MMT_NPI_Estate',
         'cross_check': 'ift_company.MMT_WEB_STATIONS (11); kept separate '
                        'from SOURCED NPI counts'},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 2 — Company_Dossier
    # ════════════════════════════════════════════════════════════════════════
    ws = wb.create_sheet('Company_Dossier')
    NC2 = 7
    sb = lib.SheetBuilder(
        ws, NC2, col_widths=[12, 32, 72, 16, 17, 48, 42], tab_color=GREY)
    sb.title('MMT company dossier — the public record only (PUBLIC-WEB '
             'labeled)')
    sb.subtitle(
        'The question: what does the PUBLIC record establish about Midwest '
        'Medical Transport Company (MMT Ambulance) — ownership since 1987, '
        'claimed scale, court records — and where do third-party estimates '
        'conflict so badly they must not be used? EVERY row on this tab is '
        'PUBLIC-WEB material (press releases, news coverage, company site, '
        'public court dockets) or the NPPES registry; nothing here is a '
        'government statistic or an audited number. Basis chips name the '
        'sub-class (PRESS = company/advisor self-report; NEWS = local press; '
        'COURT = public docket; ESTIMATE = quarantined third-party guess). '
        'Panel E is a CONFLICT EXHIBIT and is explicitly NOT usable as fact.')
    sb.blank()

    sb.banner('Panel A. Ownership & control timeline, 1987-2026 — 5 events, '
              'each with a named public source')
    sb.headers(['Year', 'Event', 'Detail (verbatim from capture)', '',
                'Basis', 'Source', 'URL'])
    pa0 = sb.r + 1
    ev_basis = {'founding': 'PUBLIC-WEB · NEWS', 'sale_2015':
                'PUBLIC-WEB · NEWS'}
    for ev in co.OWNERSHIP_TIMELINE:
        lab, url = cs(ev.source_key)
        sb.row([
            (ev.year, 'src'), (ev.event, 'src'), (ev.detail, 'src'),
            None,
            (ev_basis.get(ev.source_key, 'PUBLIC-WEB · PRESS'), 'text'),
            (lab, 'note'), (url, 'note'),
        ], wrap=True, height=52)
    pa1 = sb.r

    sb.blank()
    sb.banner('Panel B. Scale claims — company / advisor self-report, each '
              'labeled (never blend with the NPPES estate)')
    sb.headers(['#', 'Metric', 'Value (as claimed)', 'As of', 'Basis',
                'Source', 'URL'])
    pb0 = sb.r + 1
    claim_rows = {}
    for i, c in enumerate(co.SCALE_CLAIMS, start=1):
        lab, url = cs(c.source_key)
        chip = ('SOURCED · NPPES' if c.basis == 'NPPES'
                else 'PUBLIC-WEB · PRESS')
        r = sb.r + 1
        claim_rows[c.metric] = r
        sb.row([
            (i, 'text', lib.FMT_INT), (c.metric, 'src'), (c.value, 'src'),
            (c.as_of, 'src'), (chip, 'text'), (lab, 'note'), (url, 'note'),
        ], wrap=True, height=32)
    pb1 = sb.r
    sb.note('The load-bearing scale facts are exactly three classes — the '
            'NPPES estate (MMT_NPI_Estate tab), the deal-time press figures '
            '(Jan 2022), and the company\'s own site claims (2026) — each '
            'labeled. Known conflicts shown, never blended: 13-state claim '
            'vs 11 NPI states; 2022 release "10 states" vs sell-side '
            'advisor "seven states".')

    sb.blank()
    sb.banner('Panel C. Headcount trajectory as claimed — 3 self-reported '
              'endpoints (floors, definitions drift; indicative only)')
    sb.headers(['Year', 'Claimed headcount (floor)', 'Claim wording '
                '(verbatim class)', 'As of', 'Basis', 'Source', 'URL'])
    pc0 = sb.r + 1
    hc = [
        (2015, 350, '"350+ employees" at the 2015 sale (one state)',
         'Feb 2015', 'mmt_local_news', 'sale_2015'),
        (2022, 1000, '"nearly 1,000 employees" (sell-side advisor; 7 '
         'states)', 'Jan 2022', 'lincoln_intl', 'lincoln_intl'),
        (2026, 2800, '"2,800+ team members" (company site; 13-state claim)',
         '2026', 'mmt_web', 'about_us'),
    ]
    for yr, n, word, asof, _, skey in hc:
        lab, url = cs(skey)
        sb.row([
            (yr, 'src', lib.FMT_INT), (n, 'src', lib.FMT_INT),
            (word, 'src'), (asof, 'src'), ('PUBLIC-WEB · PRESS', 'text'),
            (lab, 'note'), (url, 'note'),
        ], wrap=True)
    pc1 = sb.r
    r = sb.r + 1
    sb.row([('Indicative CAGR 2015 -> 2026 (n=11)', 'label'),
            (lib.cagr_formula(f'B{pc1}', f'B{pc0}', 11), 'fml', lib.FMT_PCT1),
            ('DERIVED from the claimed floors — indicative ONLY: '
             'self-reported endpoints, "+" floors, and a definition change '
             '(employees -> team members); never trend forward.', 'note'),
            None, ('DERIVED', 'text'), None, None], wrap=True)
    r_cagr15 = sb.r
    r = sb.r + 1
    sb.row([('Indicative CAGR 2022 -> 2026 (n=4)', 'label'),
            (lib.cagr_formula(f'B{pc1}', f'B{pc0 + 1}', 4), 'fml',
             lib.FMT_PCT1),
            ('DERIVED from the claimed floors — same caveats; the 2022 '
             'figure is the advisor\'s "nearly 1,000".', 'note'),
            None, ('DERIVED', 'text'), None, None], wrap=True)
    r_cagr22 = sb.r

    sb.blank()
    sb.banner('Panel D. Litigation register — public dockets (outcomes '
              'sealed without PACER)')
    sb.headers(['Filed', 'Case', 'Court / docket', 'Nature', 'Status',
                'Source', 'URL'])
    pd0 = sb.r + 1
    for lit in co.LITIGATION:
        lab, url = cs(lit.source_key)
        sb.row([
            (lit.filed, 'src'), (lit.case, 'src'), (lit.court, 'src'),
            (lit.nature, 'src'), (lit.status, 'src'),
            ('PUBLIC-WEB · COURT (public docket)', 'note'), (url, 'note'),
        ], wrap=True, height=30)
    pd1 = sb.r
    sb.note('Pattern read (verbatim from the module, PUBLIC-WEB analytic '
            'text, not a fact): ' + co.LITIGATION_READ, height=44)

    sb.blank()
    sb.banner('Panel E. CONFLICT EXHIBIT — third-party revenue estimates. '
              'NOT USABLE AS FACT. Quarantined from the Fact_Ledger.')
    sb.headers(['#', 'Estimator', 'Estimate (revenue / headcount, as '
                'published)', 'As of', 'Basis', 'Source', 'URL'])
    pe0 = sb.r + 1
    for i, est in enumerate(co.REVENUE_ESTIMATES, start=1):
        lab, url = cs(est.source_key)
        sb.row([
            (i, 'text', lib.FMT_INT),
            (lab.split(' revenue')[0], 'src'), (est.value, 'src'),
            (est.as_of, 'src'),
            ('ESTIMATE — EXCLUDED as fact', 'note'), (lab, 'note'),
            (url, 'note'),
        ], wrap=True)
    pe1 = sb.r
    sb.note('Why this exhibit exists (verbatim module read, must travel): ' +
            co.REVENUE_ESTIMATE_READ + ' — Rendered side-by-side for '
            'diligence completeness only; also logged on '
            'Excluded_Not_Sourced.', height=56)

    sb.blank()
    sb.banner('Panel F. Positioning — company self-description (PUBLIC-WEB)')
    lab, url = cs('not911')
    sb.headers(['Item', '', 'Text (verbatim where quoted)', '', 'Basis',
                'Source', 'URL'])
    sb.row([('Positioning', 'label'), None, (co.POSITIONING, 'src'), None,
            ('PUBLIC-WEB · PRESS', 'text'), (lab, 'note'), (url, 'note')],
           wrap=True, height=44)
    r_pos = sb.r

    sb.blank()
    sb.banner('Panel G. Source registry for this dossier — all 16 public '
              'sources (verbatim quotes where actually observed)')
    sb.headers(['Key', 'Class', 'Source (label as registered)', '', '',
                'Verbatim quote (where observed)', 'URL'])
    pg0 = sb.r + 1
    for s in co_srcs.values():
        sb.row([
            (s.key, 'src'), (s.basis, 'src'), (s.label, 'src'), None, None,
            (s.quote if s.quote else '(no quote captured)',
             'src' if s.quote else 'note'),
            (s.url, 'note'),
        ], wrap=True, height=34)
    pg1 = sb.r
    r = sb.r + 1
    sb.row([('Sources (live COUNTA)', 'label'),
            (f'=COUNTA(A{pg0}:A{pg1})', 'fml', lib.FMT_INT),
            None, None, None, None, None])
    r_src_tot = sb.r
    sb.note('Class mix: NPPES 1, PRESS 5, NEWS 3, COURT 4, ESTIMATE 3. '
            'PRESS/NEWS = company, advisor or local-press claims — '
            'PUBLIC-WEB, never GOV. COURT = public dockets (Justia / '
            'CourtListener / NLRB). ESTIMATE = quarantined (Panel E). '
            'Extraction: rcm_mc/market_reports/ift_company.py::SOURCES / '
            'OWNERSHIP_TIMELINE / SCALE_CLAIMS / LITIGATION / '
            f'REVENUE_ESTIMATES / POSITIONING, {accessed}.')

    lib.add_chart(
        ws, f'I{pc0}', 'MMT claimed headcount, 2015 / 2022 / 2026 '
        '(self-reported floors — indicative only)',
        f'Company_Dossier!$A${pc0}:$A${pc1}',
        [('Claimed headcount (floor)', f'Company_Dossier!$B${pc0}:$B${pc1}')],
        kind='bar', height=10)

    facts += [
        {'metric': 'MMT founded (Platte County Ambulance, Columbus NE)',
         'year': 1987, 'value': 1987, 'unit': 'year',
         'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['mmt_local_news'],
         'locator': 'OWH/Columbus Telegram founding retrospective: "with one '
                    'ambulance, doing a few transfers a week out of the '
                    'Columbus Hospital" (Kim & Jill Wolfe)',
         'lives_on': 'Company_Dossier',
         'cross_check': 'Company site: "over 35 years" (2026); predecessor '
                        'NPI enumerated 2005 (NPPES began 2005)'},
        {'metric': 'MMT claimed states of operation (company site)',
         'year': 2026, 'value_ref':
             f"Company_Dossier!C{claim_rows['States of operation']}",
         'unit': 'states (claim)', 'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['mmt_web'],
         'locator': 'mmtamb.com About Us, captured 2026-07-10: 13 states',
         'lives_on': 'Company_Dossier',
         'cross_check': 'NPPES verifies 11 NPI states (10 confirmed + VA '
                        'flagged) — gap stated on both tabs'},
        {'metric': 'MMT claimed team members (company site)',
         'year': 2026, 'value_ref':
             f"Company_Dossier!C{claim_rows['Team members']}",
         'unit': 'people (claim, floor)', 'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['mmt_web'],
         'locator': 'mmtamb.com About Us, captured 2026-07-10: "2,800+"',
         'lives_on': 'Company_Dossier',
         'cross_check': 'All three third-party estimators disagree (700-784 '
                        'to 1,000-5,000) — conflict exhibit Panel E'},
        {'metric': 'MMT claimed missions per year (deal release)',
         'year': 2022, 'value_ref':
             f"Company_Dossier!C{claim_rows['Missions / year']}",
         'unit': 'missions/yr (claim)', 'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['hpc_2022'],
         'locator': 'Harbour Point release, Jan 25 2022: "200,000+ '
                    'missions/yr" (then-10-states framing)',
         'lives_on': 'Company_Dossier',
         'cross_check': 'Sell-side advisor framed the same deal as 7 states '
                        '/ ~1,000 employees — conflict carried, not blended'},
        {'metric': 'MMT federal wage-and-hour suits on public dockets '
                   '(2020-2024)',
         'year': 2024, 'value': 3, 'unit': 'FLSA suits',
         'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['court_dockets'],
         'locator': 'N.D. Ohio 1:20-cv-01548 (2020); E.D. Wis. '
                    '2:23-cv-00877 (2023); D. Neb. 4:2024-cv-03107 (2024); '
                    'plus NLRB 14-CA-251082 (2019, closed)',
         'lives_on': 'Company_Dossier',
         'cross_check': 'Outcomes sealed without PACER — stated; no '
                        'malpractice cases surfaced (recorded as not-found)'},
        {'metric': 'MMT claimed-headcount indicative CAGR 2015-2026',
         'year': 2026, 'value_ref': f'Company_Dossier!B{r_cagr15}',
         'unit': '%/yr (indicative)', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['mmt_local_news', 'lincoln_intl', 'mmt_web'],
         'locator': '(2,800/350)^(1/11)-1 as a live formula over the three '
                    'claimed floors — self-reported endpoints, definition '
                    'drift; indicative only, never trend forward',
         'lives_on': 'Company_Dossier',
         'cross_check': 'Endpoints: 350+ (2015, 1 state) / ~1,000 (2022, 7 '
                        'states) / 2,800+ (2026, 13-state claim)'},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 3 — Competitor_Registry
    # ════════════════════════════════════════════════════════════════════════
    comps = list(nl.COMPETITORS)
    ne = nl.counts_by_category('NE')
    ia = nl.counts_by_category('IA')
    cat_order = ['municipal-fire-volunteer', 'private', 'hospital-owned',
                 'air']

    ws = wb.create_sheet('Competitor_Registry')
    NC3 = 8
    sb = lib.SheetBuilder(
        ws, NC3, col_widths=[36, 15, 15, 11, 11, 64, 15, 42], tab_color=GREY)
    sb.title('Competitor registry: who else runs ambulances in NE/IA — '
             'profiles, NPIs, and the supply landscape')
    sb.subtitle(
        'The question: who competes for (or caps) the outsourced-IFT lane '
        'in the target operator\'s core geography — and how fragmented is '
        'the supply base beneath them? Panel A/B: 7 curated competitor '
        'profiles whose NPIs are SOURCED (CMS NPPES, 2026-07-10) and whose '
        'reads are PUBLIC-WEB with a per-profile source URL — embedded '
        'figures in the reads are public-web claims, flags travel. Panel C: '
        'the fragmentation denominators — the 751-org NE/IA NPPES sweep '
        '(SOURCED) against ~10,600 Medicare-billing organizations '
        'nationally (GOV, MedPAC). Panel D is a methods block only. All '
        'modeled market-share / moat-score columns from ift_competitive / '
        'ift_moat are EXCLUDED (see Excluded_Not_Sourced).')
    sb.blank()

    sb.banner('Panel A. 7 curated competitor profiles (NPIs SOURCED; reads '
              'PUBLIC-WEB, per-profile source URL)')
    sb.headers(['Competitor / group', 'Archetype', 'Base', 'NPIs (live '
                'COUNTIF Panel B)', 'Basis', 'Read (verbatim from capture — '
                'embedded figures are PUBLIC-WEB claims; historical figures '
                'flagged in-text)', '', 'Source URL'])
    qa0 = sb.r + 1
    # Panel B geometry is deterministic: Panel A rows + total + blank +
    # banner + header, then 28 NPI rows.
    n_npis = sum(len(c.npis) for c in comps)
    qb0 = qa0 + len(comps) + 1 + 1 + 1 + 1
    qb1 = qb0 + n_npis - 1
    for c in comps:
        r = sb.r + 1
        sb.row([
            (c.name, 'src'), (c.archetype, 'src'), (c.base, 'src'),
            (f'=COUNTIF($A${qb0}:$A${qb1},$A{r})', 'fml', lib.FMT_INT),
            ('PUBLIC-WEB read / SOURCED NPIs', 'text'),
            (c.read, 'src'), None, (c.source_url, 'note'),
        ], wrap=True, height=max(40, 13 * (len(c.read) // 62 + 1)))
    qa1 = sb.r
    r = sb.r + 1
    sb.row([('Total competitor NPIs (live SUM)', 'label'), None, None,
            (f'=SUM(D{qa0}:D{qa1})', 'fml', lib.FMT_INT), None,
            ('DERIVED — must equal the Panel B COUNTA below (28)', 'note'),
            None, None])
    r_comp_tot = sb.r

    sb.blank()
    sb.banner('Panel B. The 28 competitor NPIs (CMS NPPES, 2026-07-10)')
    sb.headers(['Competitor / group', 'NPI', 'Basis', '', '', '', '', ''])
    qb0_actual = sb.r + 1
    assert qb0_actual == qb0, f'Panel B start drifted: {qb0_actual} != {qb0}'
    for c in comps:
        for npi in c.npis:
            sb.row([(c.name, 'src'), (npi, 'src'), ('SOURCED', 'src'),
                    None, None, None, None, None])
    qb1_actual = sb.r
    assert qb1_actual == qb1, f'Panel B end drifted: {qb1_actual} != {qb1}'
    r = sb.r + 1
    sb.row([('NPIs (live COUNTA)', 'label'),
            (f'=COUNTA(B{qb0}:B{qb1})', 'fml', lib.FMT_INT),
            None, None, None, None, None, None])
    r_npib_tot = sb.r

    sb.blank()
    sb.banner('Panel C. Supply landscape — the fragmentation denominators '
              '(SOURCED NPPES sweep + GOV context)')
    sb.headers(['Category (keyword-classified — caveat below)', 'NE org '
                'NPIs', 'IA org NPIs', 'Total (=B+C)', 'Share of 751 '
                '(=D/total)', 'Source', 'Basis', 'URL'])
    qc0 = sb.r + 1
    n_cat = len(cat_order)
    r_tot751 = qc0 + n_cat  # total row lands right after the 4 categories
    for cat in cat_order:
        r = sb.r + 1
        sb.row([
            (nl.CATEGORY_LABELS[cat] + f' ({cat})', 'src'),
            (ne[cat], 'src', lib.FMT_INT), (ia[cat], 'src', lib.FMT_INT),
            (f'=B{r}+C{r}', 'fml', lib.FMT_INT),
            (f'=D{r}/$D${r_tot751}', 'fml', lib.FMT_PCT1),
            ('CMS NPPES sweep (taxonomy Ambulance, NPI-2, NE+IA), vendored '
             '2026-07-10', 'note'),
            ('SOURCED', 'text'),
            ('https://npiregistry.cms.hhs.gov/', 'note'),
        ], wrap=True)
    qc1 = sb.r
    r = sb.r + 1
    sb.row([('Total NE+IA ambulance org NPIs', 'label'),
            (f'=SUM(B{qc0}:B{qc1})', 'fml', lib.FMT_INT),
            (f'=SUM(C{qc0}:C{qc1})', 'fml', lib.FMT_INT),
            (f'=SUM(D{qc0}:D{qc1})', 'fml', lib.FMT_INT),
            (f'=D{r}/D{r}', 'fml', lib.FMT_PCT1),
            ('Expected NE 400 / IA 351 / total 751', 'note'),
            ('DERIVED', 'text'), None])
    assert sb.r == r_tot751, f'total-751 row drifted: {sb.r} != {r_tot751}'
    r_hosp = qc0 + cat_order.index('hospital-owned')
    r = sb.r + 1
    sb.row([('Hospital-ownership contrast: IA vs NE (=C/B on the '
             'hospital-owned row)', 'label'),
            (f'=B{r_hosp}', 'fml', lib.FMT_INT),
            (f'=C{r_hosp}', 'fml', lib.FMT_INT),
            (f'=C{r_hosp}/B{r_hosp}', 'fml', lib.FMT_X), None,
            ('NE 5 vs IA 40+ hospital-owned org NPIs — the ownership '
             'default flips at the state line: IA expansion means '
             'displacing hospital self-operation; NE means winning '
             'outsourcers', 'note'),
            ('DERIVED', 'text'), None], wrap=True)
    r_contrast = sb.r

    sb.blank()
    sb.headers(['National / state context', 'Value', '', '', '', 'Source',
                'Basis', 'URL'])
    r = sb.r + 1
    sb.row([('Ground ambulance organizations billing Medicare, national '
             '(2024) — published as "~10,600"', 'label'),
            (10600, 'src', lib.FMT_INT), None, None, None,
            ('MedPAC, Payment Basics: Ambulance Services, Oct 2024 (11.3M '
             'transports, $5.3B, ~10,600 organizations)', 'note'),
            ('GOV', 'text'),
            ('https://www.medpac.gov/wp-content/uploads/2024/10/'
             'MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf', 'note')],
           wrap=True)
    r_natl = sb.r
    r = sb.r + 1
    sb.row([('NE+IA org-NPI count as a share of the national org tail '
             '(unit caveat: NPIs vs billing orgs)', 'label'),
            (f'=D{r_tot751}/B{r_natl}', 'fml', lib.FMT_PCT1), None, None,
            None,
            ('DERIVED — numerator is registry org NPIs (small squads hold '
             '2-3 NPIs), denominator is Medicare-billing organizations; '
             'directional context only', 'note'),
            ('DERIVED', 'text'), None], wrap=True)
    r_share = sb.r
    r = sb.r + 1
    sb.row([('NE EMS agencies all-volunteer (share, floor)', 'label'),
            ('80%+', 'src'), None, None, None,
            ('NE DHHS Statewide EMS Assessment 2023-24 (re-verify: '
             'excerpt-grade capture)', 'note'),
            ('GOV (re-verify)', 'text'),
            ('https://dhhs.ne.gov/OEHS%20Program%20Documents/'
             'NE%20Statewide%20EMS%20Assessment%20v2024.pdf', 'note')],
           wrap=True)
    r_vol1 = sb.r
    r = sb.r + 1
    sb.row([('Volunteer agencies reporting adequate staffing', 'label'),
            (0.31, 'src', lib.FMT_PCT1), None, None, None,
            ('NE DHHS Statewide EMS Assessment 2023-24 (re-verify)', 'note'),
            ('GOV (re-verify)', 'text'), None])
    r_vol2 = sb.r
    r = sb.r + 1
    sb.row([('Volunteer agencies expecting to be UNABLE to operate within '
             '5 years', 'label'),
            (0.28, 'src', lib.FMT_PCT1), None, None, None,
            ('NE DHHS Statewide EMS Assessment 2023-24 (re-verify)', 'note'),
            ('GOV (re-verify)', 'text'), None], wrap=True)
    r_vol3 = sb.r
    r = sb.r + 1
    sb.row([('State-assessment verbatim (excess agencies)', 'label'),
            ('"Nebraska may have an excess of licensed EMS transporting '
             'agencies, which may be exacerbating shortages and creating '
             'inefficiencies"', 'src'), None, None, None,
            ('NE DHHS Statewide EMS Assessment 2023-24 (re-verify)', 'note'),
            ('GOV (re-verify)', 'text'), None], wrap=True, height=40)
    r_quote = sb.r
    r = sb.r + 1
    sb.row([('PE-backed challenger entry: AmeriPro Health acquires Priority '
             'Medical Transport (Feb 2025) — stated NE counties', 'label'),
            (7, 'src', lib.FMT_INT),
            ('counties', 'text'), None, None,
            ('PRNewswire, Feb 2025: Lincoln, Red Willow, Buffalo, Dawson, '
             'Adams, Dodge, Platte — incl. MMT\'s home county (Columbus)',
             'note'),
            ('PUBLIC-WEB · PRESS', 'text'),
            ('https://www.prnewswire.com/news-releases/ameripro-health-'
             'acquires-priority-medical-transport-and-expands-midwest-'
             'presence-302372373.html', 'note')], wrap=True, height=40)
    r_ameripro = sb.r

    sb.note('Registry caveats (travel with every count): (1) the category '
            'column is KEYWORD-classified from org names — squads straddle '
            'categories; (2) NPPES matches mailing OR practice address — 40 '
            'of 751 rows carry a non-NE/IA address state; (3) small squads '
            'hold 2-3 NPIs each, so 751 org NPIs OVERSTATES distinct '
            'agencies (686 distinct org names); (4) 21 rows carry '
            'non-ambulance primary taxonomies (hospitals/clinics with '
            'ambulance secondary). Counts from suppressed or swept files '
            'are floors/ceilings as flagged, never exact agency counts.')

    sb.blank()
    sb.banner('Panel D. Next pull — CMS claims recipe (METHODS ONLY, no '
              'data): would join supplier volumes/payments to the 751-NPI '
              'registry')
    sb.headers(['Recipe item', 'Value', '', '', '', '', 'Basis', ''])
    rec = nl.CLAIMS_RECIPE
    recipe_rows = [
        ('Dataset', rec['dataset']),
        ('CY2020 UUID', rec['uuids']['2020']),
        ('CY2021 UUID', rec['uuids']['2021']),
        ('CY2022 UUID', rec['uuids']['2022']),
        ('CY2023 UUID', rec['uuids']['2023']),
        ('Companion by-provider UUID', rec['companion_by_provider']),
        ('Companion by-geo UUID', rec['companion_by_geo']),
        ('Endpoint template', rec['endpoint']),
        ('HCPCS filter set', ', '.join(rec['hcpcs'])),
        ('Filter grammar example', rec['filter_example']),
        ('Status note', rec['note']),
    ]
    pd_0 = sb.r + 1
    for k, v in recipe_rows:
        sb.row([(k, 'label'), (v, 'text'), None, None, None, None,
                ('METHODS (no data)', 'note'), None],
               wrap=True, height=(40 if len(str(v)) > 90 else None))
    pd_1 = sb.r
    sb.note('Executing this recipe from an unblocked network yields a '
            '2020-2023 NE/IA supplier volume/payment time series (the '
            'future claims-measured CAGR table). No numbers are carried '
            'here because the pull has not run. Extraction: '
            'rcm_mc/market_reports/ift_npi_landscape.py::COMPETITORS / '
            'counts_by_category() / summary() / CLAIMS_RECIPE, '
            f'{accessed}.')

    lib.add_chart(
        ws, f'J{qc0}', 'NE vs IA ambulance org NPIs by category (NPPES '
        'sweep, 2026-07-10)',
        f'Competitor_Registry!$A${qc0}:$A${qc1}',
        [('NE', f'Competitor_Registry!$B${qc0}:$B${qc1}'),
         ('IA', f'Competitor_Registry!$C${qc0}:$C${qc1}')],
        kind='bar', height=11)

    facts += [
        {'metric': 'NE+IA ambulance organizational NPIs (supply '
                   'denominator)',
         'year': 2026, 'value_ref': f'Competitor_Registry!D{r_tot751}',
         'unit': 'org NPIs', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['nppes_neia'],
         'locator': 'NPPES sweep (taxonomy Ambulance, NPI-2, NE+IA) vendored '
                    '2026-07-10; live SUM = 751 (NE 400 / IA 351)',
         'lives_on': 'Competitor_Registry',
         'cross_check': 'ift_npi_landscape.summary() total_orgs = 751; 686 '
                        'distinct org names (multi-NPI squads caveat)'},
        {'metric': 'NE municipal/fire/volunteer org NPIs',
         'year': 2026, 'value_ref': f'Competitor_Registry!B{qc0}',
         'unit': 'org NPIs', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['nppes_neia'],
         'locator': 'NPPES sweep category matrix: 328 of 400 NE org NPIs '
                    '(keyword-classified)',
         'lives_on': 'Competitor_Registry',
         'cross_check': 'Consistent with the NE DHHS 80%+ all-volunteer '
                        'finding (same tab)'},
        {'metric': 'Hospital-owned ambulance org NPIs: IA vs NE',
         'year': 2026, 'value_ref': f'Competitor_Registry!C{r_hosp}',
         'unit': 'org NPIs (IA)', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['nppes_neia'],
         'locator': 'NPPES sweep: IA 40 vs NE 5 hospital-owned — the '
                    'sharpest measured ownership-model contrast',
         'lives_on': 'Competitor_Registry',
         'cross_check': 'Live ratio formula = 8.0x on the contrast row; '
                        'in-depth Q5 carries the same 40+ vs ~5 read'},
        {'metric': 'Ground ambulance organizations billing Medicare '
                   '(national)',
         'year': 2024, 'value_ref': f'Competitor_Registry!B{r_natl}',
         'unit': 'organizations (approx.)', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['medpac_pb2024'],
         'locator': 'MedPAC Payment Basics: Ambulance, Oct 2024 — "~10,600" '
                    'organizations (11.3M transports, $5.3B)',
         'lives_on': 'Competitor_Registry',
         'cross_check': 'PECOS ambulance-supplier extract (Group S tabs) '
                        'counts 10,465 Part B ambulance suppliers'},
        {'metric': 'Competitor NPIs carried across the 7 curated profiles',
         'year': 2026, 'value_ref': f'Competitor_Registry!D{r_comp_tot}',
         'unit': 'org NPIs', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['nppes_neia'],
         'locator': 'Live SUM of per-profile COUNTIFs over the 28-row Panel '
                    'B NPI list',
         'lives_on': 'Competitor_Registry',
         'cross_check': 'AMR 1 + AmeriPro 2 + Omaha locals 8 + Siouxland 1 '
                        '+ fire-based 6 + hospital-owned 3 + air 7 = 28'},
        {'metric': 'NE EMS agencies all-volunteer (floor)',
         'year': 2024, 'value': '80%+', 'unit': 'share of agencies (floor)',
         'basis': 'GOV', 'tier': 'B',
         'source_keys': ['ne_dhhs_ems'],
         'locator': 'NE DHHS Statewide EMS Assessment 2023-24 (re-verify: '
                    'excerpt-grade); companions: 31% adequately staffed, '
                    '28% expect unable to operate within 5 years',
         'lives_on': 'Competitor_Registry',
         'cross_check': 'NPPES matrix: 328 of 400 NE org NPIs are '
                        'municipal/fire/volunteer (82%)'},
        {'metric': 'AmeriPro/Priority stated Nebraska counties (Feb 2025 '
                   'entry)',
         'year': 2025, 'value_ref': f'Competitor_Registry!B{r_ameripro}',
         'unit': 'counties', 'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['ameripro_pr'],
         'locator': 'PRNewswire Feb 2025 release: Lincoln, Red Willow, '
                    'Buffalo, Dawson, Adams, Dodge, Platte',
         'lives_on': 'Competitor_Registry',
         'cross_check': 'Includes Platte County — MMT\'s founding county '
                        '(Company_Dossier)'},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 4 — Payment_Integrity
    # ════════════════════════════════════════════════════════════════════════
    ws = wb.create_sheet('Payment_Integrity')
    NC4 = 8
    sb = lib.SheetBuilder(
        ws, NC4, col_widths=[46, 12, 20, 60, 9, 16, 44, 40], tab_color=GREY)
    sb.title('Payment integrity: improper payments, the RSNAT natural '
             'experiment, and the OIG record')
    sb.subtitle(
        'The question: how large and how concentrated is the '
        'compliance/documentation risk in Medicare ambulance billing — and '
        'what actually happened to utilization when CMS enforced (RSNAT '
        'prior authorization)? Panel A: the CERT improper-payment split '
        '(GOV, re-verify flag carried). Panel B: RSNAT definitions (GOV) '
        'and the published natural-experiment effects with their EXACT '
        'definitions (ACADEMIC, DOI). Panel C: the OIG record — the '
        '2002-2011 utilization boom (the trend RSNAT then broke) and the '
        '2015 questionable-billing findings. Derived cells are live '
        'formulas.')
    sb.blank()

    sb.banner('Panel A. CERT 2024 — ambulance improper-payment split (GOV; '
              're-verify: excerpt-grade capture)')
    sb.headers(['Item', 'Value', 'Unit', 'Exact definition / wording',
                'Year', 'Basis', 'Source + locator', 'URL'])
    ca0 = sb.r + 1
    cert_url = ('https://www.cms.gov/data-research/monitoring-programs/'
                'improper-payment-measurement-programs/'
                'comprehensive-error-rate-testing-cert')
    r = sb.r + 1
    sb.row([('Ambulance improper-payment rate', 'label'),
            (0.132, 'src', lib.FMT_PCT1), ('of payments', 'text'),
            ('Projected improper-payment rate for ambulance services, CERT '
             '2024 supplemental data', 'text'),
            (2024, 'src', lib.FMT_INT), ('GOV (re-verify)', 'text'),
            ('CMS CERT 2024 Medicare FFS Supplemental Improper Payment '
             'Data, ambulance service type', 'note'), (cert_url, 'note')],
           wrap=True)
    r_cert_rate = sb.r
    r = sb.r + 1
    sb.row([('Projected improper payments', 'label'),
            (595.1, 'src', lib.FMT_DEC1), ('$ millions', 'text'),
            ('Projected dollars improperly paid for ambulance services',
             'text'),
            (2024, 'src', lib.FMT_INT), ('GOV (re-verify)', 'text'),
            ('CMS CERT 2024 supplemental data', 'note'), (cert_url, 'note')],
           wrap=True)
    r_cert_usd = sb.r
    r = sb.r + 1
    sb.row([('Error share: insufficient documentation', 'label'),
            (0.635, 'src', lib.FMT_PCT1), ('of improper $', 'text'),
            ('63.5% of the ambulance improper-payment error is insufficient '
             'documentation — the broken financial payload, not fraud',
             'text'),
            (2024, 'src', lib.FMT_INT), ('GOV (re-verify)', 'text'),
            ('CMS CERT 2024 supplemental data, error-category split',
             'note'), (cert_url, 'note')], wrap=True)
    r_cert_doc = sb.r
    r = sb.r + 1
    sb.row([('Error share: medical necessity', 'label'),
            (0.275, 'src', lib.FMT_PCT1), ('of improper $', 'text'),
            ('27.5% of the error is medical necessity — the over-tiering / '
             'coverage-gate audit trail', 'text'),
            (2024, 'src', lib.FMT_INT), ('GOV (re-verify)', 'text'),
            ('CMS CERT 2024 supplemental data, error-category split',
             'note'), (cert_url, 'note')], wrap=True)
    r_cert_mn = sb.r
    r = sb.r + 1
    sb.row([('Error share: residual (all other categories)', 'label'),
            (f'=1-B{r_cert_doc}-B{r_cert_mn}', 'fml', lib.FMT_PCT1),
            ('of improper $', 'text'),
            ('Live residual formula (=1 - 63.5% - 27.5%) — other CERT error '
             'categories (e.g. incorrect coding), not separately captured',
             'text'),
            (2024, 'text', lib.FMT_INT), ('DERIVED', 'text'),
            ('Formula over the two captured shares', 'note'), None],
           wrap=True)
    r_cert_res = sb.r
    r = sb.r + 1
    sb.row([('Implied improper $ from insufficient documentation', 'label'),
            (f'=B{r_cert_usd}*B{r_cert_doc}', 'fml', lib.FMT_DEC1),
            ('$ millions', 'text'),
            ('Live formula: projected improper $ x documentation share',
             'text'),
            (2024, 'text', lib.FMT_INT), ('DERIVED', 'text'),
            ('Formula over Panel A rows', 'note'), None], wrap=True)
    r_cert_docusd = sb.r
    r = sb.r + 1
    sb.row([('Implied improper $ from medical necessity', 'label'),
            (f'=B{r_cert_usd}*B{r_cert_mn}', 'fml', lib.FMT_DEC1),
            ('$ millions', 'text'),
            ('Live formula: projected improper $ x medical-necessity share',
             'text'),
            (2024, 'text', lib.FMT_INT), ('DERIVED', 'text'),
            ('Formula over Panel A rows', 'note'), None], wrap=True)
    r_cert_mnusd = sb.r

    sb.blank()
    sb.banner('Panel B. RSNAT — the definitions (GOV) and the natural '
              'experiment (ACADEMIC, exact published definitions)')
    sb.headers(['Item', 'Value', 'Unit', 'Exact definition / wording',
                'Year', 'Basis', 'Source + locator', 'URL'])
    rsnat_url = ('https://www.cms.gov/data-research/monitoring-programs/'
                 'medicare-fee-service-compliance-programs/prior-'
                 'authorization-and-pre-claim-review-initiatives/prior-'
                 'authorization-repetitive-scheduled-non-emergent-ambulance-'
                 'transport-rsnat')
    r = sb.r + 1
    sb.row([('"Repetitive" definition (what RSNAT covers)', 'label'),
            None, None,
            ('3+ round trips in 10 days, OR 1+ round trip per week for 3+ '
             'weeks — regulation literally presumes this demand is '
             'schedulable', 'src'),
            (2022, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('CMS RSNAT prior-authorization model rules', 'note'),
            (rsnat_url, 'note')], wrap=True)
    r_def1 = sb.r
    r = sb.r + 1
    sb.row([('Prior-auth affirmation coverage', 'label'),
            (120, 'src', lib.FMT_INT), ('round trips / 180 days', 'text'),
            ('One affirmative prior-authorization decision covers 120 round '
             'trips in a 180-day period', 'src'),
            (2022, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('CMS RSNAT rules + MLN6805343 fact sheet (Jan 2026)', 'note'),
            (rsnat_url, 'note')], wrap=True)
    r_def2 = sb.r
    r = sb.r + 1
    sb.row([('National scope', 'label'), None, None,
            ('Nationwide since Aug 1, 2022, covering exactly A0426 and '
             'A0428; skipping prior authorization routes claims to '
             'prepayment medical review', 'src'),
            (2022, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('CMS RSNAT program page + MLN6805343', 'note'),
            (rsnat_url, 'note')], wrap=True)
    r_def3 = sb.r
    doi_c = 'https://doi.org/10.1001/jamahealthforum.2022.2093'
    r = sb.r + 1
    sb.row([('Effect 1: probability of RSNAT use', 'label'),
            (-0.61, 'src', lib.FMT_PCT1), ('change', 'text'),
            ('Verbatim: "61% reduction in the probability of RSNAT use" — '
             'ESRD cohort, RSNAT model states vs comparison states', 'src'),
            (2022, 'src', lib.FMT_INT), ('ACADEMIC', 'text'),
            ('Contreary et al., JAMA Health Forum 2022 (RSNAT model '
             'evaluation)', 'note'), (doi_c, 'note')], wrap=True)
    r_eff1 = sb.r
    r = sb.r + 1
    sb.row([('Effect 2: RSNAT expenditures', 'label'),
            (-0.77, 'src', lib.FMT_PCT1), ('change', 'text'),
            ('Verbatim: "77% reduction in RSNAT expenditures for a total of '
             '$1136 per beneficiary-year"', 'src'),
            (2022, 'src', lib.FMT_INT), ('ACADEMIC', 'text'),
            ('Contreary et al., JAMA Health Forum 2022', 'note'),
            (doi_c, 'note')], wrap=True)
    r_eff2 = sb.r
    r = sb.r + 1
    sb.row([('Effect 3: emergency dialysis use (ESRD cohort)', 'label'),
            (0.19, 'src', lib.FMT_PCT1), ('annual change', 'text'),
            ('Verbatim: "19% annual increase in the probability of '
             'emergency dialysis use" — the cost-shift when scheduled '
             'transport is squeezed', 'src'),
            (2022, 'src', lib.FMT_INT), ('ACADEMIC', 'text'),
            ('Contreary et al., JAMA Health Forum 2022', 'note'),
            (doi_c, 'note')], wrap=True)
    r_eff3 = sb.r
    sb.note('Reading the experiment honestly: RSNAT proves scheduled '
            'repetitive transport demand responds hard to payment-side '
            'enforcement (-61% use / -77% spend), AND that suppressed '
            'transport partly re-emerges as costlier emergency utilization '
            '(+19%/yr emergency dialysis). Both directions matter for '
            'underwriting a scheduled-transport book.')

    sb.blank()
    sb.banner('Panel C. The OIG record — the 2002-2011 boom (trend RSNAT '
              'then broke) + the 2015 questionable-billing findings')
    sb.headers(['Item', 'Value', 'Unit', 'Exact definition / wording',
                'Year', 'Basis', 'Source + locator', 'URL'])
    oig350_url = 'https://oig.hhs.gov/oei/reports/oei-09-12-00350.asp'
    oig351_url = 'https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf'
    r = sb.r + 1
    sb.row([('Medicare ambulance transports, growth 2002-2011', 'label'),
            (0.69, 'src', lib.FMT_PCT1), ('endpoint growth', 'text'),
            ('Transports grew 69% over 2002-2011 (utilization study '
             'window)', 'text'),
            (2011, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('HHS OIG OEI-09-12-00350, "Utilization of Medicare Ambulance '
             'Transports, 2002-2011"', 'note'), (oig350_url, 'note')],
           wrap=True)
    r_g350a = sb.r
    r = sb.r + 1
    sb.row([('Dialysis-related transports, growth 2002-2011', 'label'),
            (2.69, 'src', lib.FMT_PCT1), ('endpoint growth', 'text'),
            ('Dialysis-related transports grew 269% over the same window — '
             'the concentration that triggered RSNAT', 'text'),
            (2011, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('HHS OIG OEI-09-12-00350', 'note'), (oig350_url, 'note')],
           wrap=True)
    r_g350b = sb.r
    r = sb.r + 1
    sb.row([('Implied CAGR, all transports (window 2002-2011, n=9)',
             'label'),
            (f'=(1+B{r_g350a})^(1/9)-1', 'fml', lib.FMT_PCT2),
            ('%/yr', 'text'),
            ('Live formula from the published endpoint growth', 'text'),
            (2011, 'text', lib.FMT_INT), ('DERIVED', 'text'),
            ('Formula over the OEI-09-12-00350 endpoint', 'note'), None],
           wrap=True)
    r_cagr350a = sb.r
    r = sb.r + 1
    sb.row([('Implied CAGR, dialysis-related (window 2002-2011, n=9)',
             'label'),
            (f'=(1+B{r_g350b})^(1/9)-1', 'fml', lib.FMT_PCT2),
            ('%/yr', 'text'),
            ('Live formula from the published endpoint growth', 'text'),
            (2011, 'text', lib.FMT_INT), ('DERIVED', 'text'),
            ('Formula over the OEI-09-12-00350 endpoint', 'note'), None],
           wrap=True)
    r_cagr350b = sb.r
    r = sb.r + 1
    sb.row([('Trend-eligible forward?', 'label'), ('NO', 'label'), None,
            ('SERIES BREAK: RSNAT prior authorization (model states Dec '
             '2014; nationwide Aug 1, 2022) deliberately broke this trend — '
             'the -61%/-77% effects in Panel B are the proof. NEVER '
             'extrapolate the 2002-2011 rates forward.', 'note'),
            None, ('FLAG', 'text'), None, None], wrap=True, height=40)
    r_break = sb.r
    r = sb.r + 1
    sb.row([('Paid for transports not meeting program requirements '
             '(half-year)', 'label'),
            (24.0, 'src', lib.FMT_DEC1), ('$ millions, H1-2012', 'text'),
            ('$24M paid in the first half of 2012 for transports that did '
             'not meet Medicare program requirements', 'text'),
            (2015, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('HHS OIG OEI-09-12-00351 (2015; H1-2012 claims)', 'note'),
            (oig351_url, 'note')], wrap=True)
    r_24m = sb.r
    r = sb.r + 1
    sb.row([('Paid where beneficiary received NO Medicare service at '
             'origin or destination (half-year)', 'label'),
            (30.2, 'src', lib.FMT_DEC1), ('$ millions, H1-2012', 'text'),
            ('$30.2M paid for transports where the beneficiary received no '
             'Medicare service at either end of the trip', 'text'),
            (2015, 'src', lib.FMT_INT), ('GOV (re-verify)', 'text'),
            ('HHS OIG OEI-09-12-00351 (carried via repo evidence module; '
             'reopen the PDF finding before circulation)', 'note'),
            (oig351_url, 'note')], wrap=True)
    r_302m = sb.r
    r = sb.r + 1
    sb.row([('Level / destination-modifier mismatch (half-year)', 'label'),
            (7.1, 'src', lib.FMT_DEC1), ('$ millions, H1-2012', 'text'),
            ('$7.1M paid where destination modifiers were inconsistent with '
             'the level billed — documentation must support the LEVEL, not '
             'just the trip', 'text'),
            (2015, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('HHS OIG OEI-09-12-00351', 'note'), (oig351_url, 'note')],
           wrap=True)
    r_71m = sb.r
    r = sb.r + 1
    sb.row([('SCT billed between non-hospital origins/destinations '
             '(half-year)', 'label'),
            (4.3, 'src', lib.FMT_DEC1), ('$ millions, H1-2012', 'text'),
            ('$4.3M of specialty-care transport billed where neither end '
             'was a hospital — definitionally suspect under 42 CFR 414.605',
             'text'),
            (2015, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('HHS OIG OEI-09-12-00351', 'note'), (oig351_url, 'note')],
           wrap=True)
    r_43m = sb.r
    r = sb.r + 1
    sb.row([('Suppliers meeting >=1 of 7 questionable-billing measures',
             'label'),
            (0.21, 'src', lib.FMT_PCT1), ('of suppliers', 'text'),
            ('About 1 in 5 ambulance suppliers exhibited at least one of '
             'seven questionable-billing patterns', 'text'),
            (2015, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('HHS OIG OEI-09-12-00351', 'note'), (oig351_url, 'note')],
           wrap=True)
    r_21pct = sb.r
    r = sb.r + 1
    sb.row([('Geographic concentration of questionable billing', 'label'),
            (0.52, 'src', lib.FMT_PCT1),
            ('of questionable transports', 'text'),
            ('Four metro areas accounted for 18% of transports but 52% of '
             'questionable transports (~$207M in the half-year) — '
             'enforcement risk is geographically concentrated, NOT uniform',
             'text'),
            (2015, 'src', lib.FMT_INT), ('GOV', 'text'),
            ('HHS OIG OEI-09-12-00351', 'note'), (oig351_url, 'note')],
           wrap=True, height=40)
    r_conc = sb.r
    sb.note('Re-verify flags carried from the repo modules: the CERT 2024 '
            'split and the $30.2M finding are excerpt-grade captures '
            '(marked "(re-verify)" in rcm_mc evidence lines); the '
            '$24M/$7.1M/$4.3M/21%/4-metro findings carry the primary OIG '
            'PDF citation via ift_service_levels. Extraction: '
            'rcm_mc/market_reports/ift_indepth*.py evidence lines + '
            'ift_service_levels.necessity_and_denials() / '
            f'classification_framework(), {accessed}.')

    lib.add_chart(
        ws, f'J{ca0}', 'CERT 2024 ambulance improper-payment error '
        'composition',
        None,
        [('Insufficient documentation',
          f'Payment_Integrity!$B${r_cert_doc}'),
         ('Medical necessity', f'Payment_Integrity!$B${r_cert_mn}'),
         ('Residual (other)', f'Payment_Integrity!$B${r_cert_res}')],
        kind='bar', height=9, y_fmt='0%')
    lib.add_chart(
        ws, f'J{r_def1 + 12}', 'RSNAT natural experiment: published effects '
        '(Contreary et al. 2022)',
        f'Payment_Integrity!$A${r_eff1}:$A${r_eff3}',
        [('Effect', f'Payment_Integrity!$B${r_eff1}:$B${r_eff3}')],
        kind='bar', height=10, y_fmt='0%')

    facts += [
        {'metric': 'Ambulance improper-payment rate (CERT)',
         'year': 2024, 'value_ref': f'Payment_Integrity!B{r_cert_rate}',
         'unit': 'share of payments', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['cert_2024'],
         'locator': 'CERT 2024 supplemental data, ambulance service type: '
                    '13.2% (re-verify flag carried)',
         'lives_on': 'Payment_Integrity',
         'cross_check': 'Projected $595.1M on the next row; 63.5/27.5 error '
                        'split'},
        {'metric': 'Projected ambulance improper payments (CERT)',
         'year': 2024, 'value_ref': f'Payment_Integrity!B{r_cert_usd}',
         'unit': '$M', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['cert_2024'],
         'locator': 'CERT 2024 supplemental data: $595.1M projected '
                    '(re-verify)',
         'lives_on': 'Payment_Integrity',
         'cross_check': '13.2% rate x the ambulance payment base; implied '
                        '$377.9M documentation / $163.7M necessity as live '
                        'formulas'},
        {'metric': 'CERT error share from insufficient documentation',
         'year': 2024, 'value_ref': f'Payment_Integrity!B{r_cert_doc}',
         'unit': 'share of improper $', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['cert_2024'],
         'locator': 'CERT 2024 error-category split: 63.5% (re-verify)',
         'lives_on': 'Payment_Integrity',
         'cross_check': 'Medical necessity 27.5%; residual 9.0% (live '
                        'formula)'},
        {'metric': 'RSNAT effect on probability of RSNAT use',
         'year': 2022, 'value_ref': f'Payment_Integrity!B{r_eff1}',
         'unit': 'change in probability', 'basis': 'ACADEMIC', 'tier': 'B',
         'source_keys': ['contreary_2022'],
         'locator': 'doi:10.1001/jamahealthforum.2022.2093 — verbatim "61% '
                    'reduction in the probability of RSNAT use" (ESRD '
                    'cohort, model vs comparison states)',
         'lives_on': 'Payment_Integrity',
         'cross_check': 'Paired with -77% spend and +19%/yr emergency '
                        'dialysis on adjacent rows'},
        {'metric': 'RSNAT effect on RSNAT expenditures',
         'year': 2022, 'value_ref': f'Payment_Integrity!B{r_eff2}',
         'unit': 'change ($1,136/beneficiary-yr)', 'basis': 'ACADEMIC',
         'tier': 'B', 'source_keys': ['contreary_2022'],
         'locator': 'Verbatim "77% reduction in RSNAT expenditures for a '
                    'total of $1136 per beneficiary-year"',
         'lives_on': 'Payment_Integrity',
         'cross_check': 'Same paper as effects 1 and 3 (single DOI)'},
        {'metric': 'RSNAT side-effect: emergency dialysis use',
         'year': 2022, 'value_ref': f'Payment_Integrity!B{r_eff3}',
         'unit': 'annual change in probability', 'basis': 'ACADEMIC',
         'tier': 'B', 'source_keys': ['contreary_2022'],
         'locator': 'Verbatim "19% annual increase in the probability of '
                    'emergency dialysis use" (ESRD cohort)',
         'lives_on': 'Payment_Integrity',
         'cross_check': 'The cost-shift direction — carried with the '
                        'suppression effects, never alone'},
        {'metric': 'Medicare ambulance transport growth 2002-2011 '
                   '(pre-RSNAT boom)',
         'year': 2011, 'value_ref': f'Payment_Integrity!B{r_g350a}',
         'unit': 'endpoint growth', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['oig_350'],
         'locator': 'OEI-09-12-00350: transports +69% 2002-2011; '
                    'dialysis-related +269%',
         'lives_on': 'Payment_Integrity',
         'cross_check': 'Implied CAGRs 6.0%/15.7% as live formulas; series '
                        'break flagged — RSNAT broke this trend'},
        {'metric': 'Suppliers with questionable-billing patterns (OIG)',
         'year': 2015, 'value_ref': f'Payment_Integrity!B{r_21pct}',
         'unit': 'share of suppliers', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['oig_351'],
         'locator': 'OEI-09-12-00351: 21% (about 1 in 5) met >=1 of 7 '
                    'measures; 4 metros = 18% of transports / 52% of '
                    'questionable (~$207M half-year)',
         'lives_on': 'Payment_Integrity',
         'cross_check': '$24M / $30.2M / $7.1M / $4.3M half-year findings '
                        'on adjacent rows'},
    ]

    # ════════════════════════════════════════════════════════════════════════
    # Tab 5 — Contract_Benchmarks
    # ════════════════════════════════════════════════════════════════════════
    ws = wb.create_sheet('Contract_Benchmarks')
    NC5 = 9
    sb = lib.SheetBuilder(
        ws, NC5, col_widths=[12, 30, 11, 46, 42, 11, 17, 40, 36],
        tab_color=GREY)
    sb.title('Contract benchmarks: the SLA-and-penalty technology adjacent '
             'transport markets already use')
    sb.subtitle(
        'The question: what enforceable service levels, penalties and '
        'statutory clocks already exist in the transport markets NEXT DOOR '
        'to hospital IFT (urban 911 contracts, Medicaid NEMT brokerage, '
        'California statute) — i.e. the contract technology IFT deals '
        'typically lack? LOUD CAVEAT: most rows are excerpt-grade captures '
        'from municipal/state records carried through the repo contracting '
        'dossier — every such row carries a RE-VERIFY flag and must be '
        'checked against the primary contract documents before external '
        'circulation. Basis chips are mixed GOV / SOURCED(PUBLIC-WEB '
        'record); nothing here is modeled.')
    sb.blank()

    sb.banner('Panel A. Precedent register — thresholds first (chartable), '
              'then penalties, enforcement and statutes')
    sb.headers(['Market', 'Jurisdiction / program', 'Contracted threshold',
                'Standard (detail)', 'Penalty / enforcement', 'Re-verify?',
                'Basis', 'Source', 'URL'])
    t0 = sb.r + 1
    bench_rows = [
        # (market, program, threshold, detail, penalty, reverify, basis,
        #  source, url) — threshold-carrying rows first for the chart.
        ('911', 'Urban norm (municipal contracts + NFPA 1710)', 0.90,
         '8:59 response at the 90% fractile — the standard urban '
         'performance-contract form', 'Penalty regimes typical (see rows '
         'below)', 'YES', 'SOURCED (muni records)', 'muni_911', ''),
        ('911', 'Pasadena, TX', 0.90,
         '8:59 at 90%, with a hard cap at 14:59', 'Contractual penalties on '
         'misses', 'YES', 'SOURCED (muni records)', 'muni_911', ''),
        ('911', 'Multnomah County, OR', 0.90,
         'Response-time compliance measured monthly', 'Penalties when '
         'compliance falls below 90%', 'YES', 'SOURCED (muni records)',
         'muni_911', ''),
        ('NEMT', 'State broker contracts (common form)', 0.95,
         '>=95% on-time-pickup standards in broker contracts',
         'Liquidated damages / penalties per contract', 'YES',
         'SOURCED (contract records)', 'nemt_broker_tx', ''),
        ('NEMT', 'Texas HHSC Medical Transportation Program', 0.85,
         '85% on-time-pickup benchmark', 'Penalty cap $15,000 — committed '
         'performance as a contract term', 'YES', 'GOV (re-verify)',
         'nemt_broker_tx', ''),
        ('Offload statute', 'California AB 40 (2023) / EMSA APOT', 0.90,
         'Ambulance patient offload time not to exceed 30 minutes, 90% of '
         'the time', 'Monthly per-hospital EMSA monitoring — the state had '
         'to legislate the arrival clock', 'YES', 'GOV (re-verify)',
         'ca_ab40', 'https://emsa.ca.gov/apot/'),
        ('911', 'City of San Diego / Falck', None,
         'Per-response outlier clock: responses beyond 24 minutes',
         '$5,000 per response beyond 24 minutes', 'YES',
         'SOURCED (muni records)', 'muni_911', ''),
        ('NEMT', 'Mississippi Medicaid broker (audit finding)', None,
         'OBSERVED performance, not a standard: ~3,000 of >52,000 monthly '
         'trips late or missed (~5.8%) — roughly 3x the contractual limit',
         'State audit exposure; coverage Sep 2024', 'YES',
         'SOURCED (press-carried)', 'nemt_enforcement', ''),
        ('NEMT', 'New Jersey Medicaid (enforcement record)', None,
         'Broker performance enforcement, 2017-2022',
         'NJ fined Modivcare ~$1.7M over 2017-22', 'YES',
         'SOURCED (press-carried)', 'nemt_enforcement', ''),
        ('NEMT', 'Georgia Medicaid (enforcement record)', None,
         'Broker performance enforcement, 2018-2020',
         'GA fined brokers >$1M over 2018-20', 'YES',
         'SOURCED (press-carried)', 'nemt_enforcement', ''),
        ('EOA statute', 'California H&S Code 1797.224', None,
         'Exclusive operating areas awarded through a competitive process — '
         'the statutory procurement cadence for emergency ambulance zones',
         'Award/retention is the enforcement lever', 'no',
         'GOV', 'ca_hs_1797224',
         'https://leginfo.legislature.ca.gov/faces/codes_displaySection.'
         'xhtml?lawCode=HSC&sectionNum=1797.224'),
        ('Context', 'Modivcare Inc. Chapter 11 (S.D. Tex.)', None,
         'Filed Aug 20, 2025; emerged Dec 29, 2025 cutting >$1.1B of ~$1.4B '
         'funded debt — why vendor financial stability is an evaluation '
         'criterion in transport contracting',
         'n/a (context row)', 'YES', 'SOURCED (docket + coverage)',
         'modivcare_ch11', ''),
    ]
    src_doc = {s['key']: s['document'] for s in sources}
    thr_rows = []
    for mkt, prog, thr, det, pen, rev, basis, skey, url in bench_rows:
        r = sb.r + 1
        if thr is not None:
            thr_rows.append(r)
        sb.row([
            (mkt, 'src'), (prog, 'src'),
            ((thr, 'src', lib.FMT_PCT1) if thr is not None else None),
            (det, 'src'), (pen, 'src'),
            (rev, 'label' if rev == 'YES' else 'text'),
            (basis, 'text'),
            (src_doc[skey].split(' (RE-VERIFY')[0][:120], 'note'),
            (url, 'note'),
        ], wrap=True, height=40)
    t1 = sb.r
    thr0, thr1 = thr_rows[0], thr_rows[-1]

    sb.blank()
    sb.note('RE-VERIFY discipline (must travel with every flagged row): '
            'the 911 and NEMT rows are carried from the repo in-depth '
            'evidence modules, which captured them from municipal contract '
            'records, state program terms and press-carried state '
            'enforcement records WITHOUT reopening the primary documents — '
            'the repo marks each "(re-verify)". No URL is on file for the '
            'Pasadena / Multnomah / San Diego / TX HHSC / MS / NJ / GA '
            'rows. Treat every flagged figure as excerpt-grade until the '
            'primary contract or audit document is pulled.')
    sb.note('Why this table exists: hospital IFT agreements typically lack '
            'committed, penalty-backed service levels; the adjacent 911 and '
            'NEMT markets prove the contract technology (fractile response '
            'standards, on-time-pickup benchmarks, per-event fines, '
            'statutory offload clocks) is real, enforceable and already '
            'operating. Extraction: rcm_mc/market_reports/ift_indepth_q23 / '
            '_q456 / _q78 / _q910 evidence lines (Q2/Q5/Q6/Q7/Q9/Q10), '
            f'{accessed}.')

    lib.add_chart(
        ws, f'K{t0}', 'Contracted performance thresholds next door to IFT '
        '(fractile / on-time / offload compliance)',
        f'Contract_Benchmarks!$B${thr0}:$B${thr1}',
        [('Contracted threshold',
          f'Contract_Benchmarks!$C${thr0}:$C${thr1}')],
        kind='bar', height=10, y_fmt='0%')

    facts += [
        {'metric': 'Texas Medicaid NEMT on-time-pickup benchmark',
         'year': 2026, 'value_ref': f'Contract_Benchmarks!C{thr_rows[4]}',
         'unit': 'on-time share', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['nemt_broker_tx'],
         'locator': 'TX HHSC Medical Transportation Program contract terms: '
                    '85% benchmark, $15,000 penalty cap (re-verify)',
         'lives_on': 'Contract_Benchmarks',
         'cross_check': 'Broker-contract common form >=95% on adjacent row'},
        {'metric': 'San Diego / Falck per-response penalty',
         'year': 2026, 'value': 5000, 'unit': '$ per response beyond 24 min',
         'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['muni_911'],
         'locator': 'San Diego municipal contract records via repo dossier '
                    '(re-verify; no URL on file)',
         'lives_on': 'Contract_Benchmarks',
         'cross_check': 'Same register carries Pasadena 8:59/90% cap 14:59 '
                        'and Multnomah below-90% penalties'},
        {'metric': 'California AB 40 ambulance patient offload standard',
         'year': 2023, 'value_ref': f'Contract_Benchmarks!C{thr_rows[5]}',
         'unit': 'compliance threshold (30-min offload)', 'basis': 'GOV',
         'tier': 'B', 'source_keys': ['ca_ab40'],
         'locator': 'AB 40 (2023) / EMSA APOT: <=30 minutes 90% of the '
                    'time, monthly per-hospital monitoring (re-verify)',
         'lives_on': 'Contract_Benchmarks',
         'cross_check': 'emsa.ca.gov/apot program page cited; the one '
                        'statutory offload clock in the register'},
        {'metric': 'Mississippi NEMT broker observed miss rate',
         'year': 2024, 'value': '~5.8%', 'unit': 'monthly trips late/missed',
         'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['nemt_enforcement'],
         'locator': 'Mississippi Today (Sep 2024): ~3,000 of >52,000 '
                    'monthly trips, ~3x the contractual limit (re-verify)',
         'lives_on': 'Contract_Benchmarks',
         'cross_check': 'Enforcement companions: NJ ~$1.7M (2017-22), GA '
                        '>$1M (2018-20)'},
        {'metric': 'NJ Medicaid NEMT enforcement fines vs Modivcare',
         'year': 2022, 'value': '~$1.7M', 'unit': 'fines 2017-2022',
         'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['nemt_enforcement'],
         'locator': 'State enforcement records via press (re-verify; no '
                    'URL on file)',
         'lives_on': 'Contract_Benchmarks',
         'cross_check': 'Modivcare later filed Ch.11 (Aug 2025) — context '
                        'row on the same tab'},
        {'metric': 'NEMT broker contract on-time standard (common form)',
         'year': 2026, 'value_ref': f'Contract_Benchmarks!C{thr_rows[3]}',
         'unit': 'on-time share', 'basis': 'PUBLIC-WEB', 'tier': 'B',
         'source_keys': ['nemt_broker_tx'],
         'locator': 'State broker contract standards: >=95% on-time pickup '
                    'with penalties (re-verify)',
         'lives_on': 'Contract_Benchmarks',
         'cross_check': 'TX 85% benchmark is the enforce-with-cap variant'},
    ]

    # ── Excluded (group-level quarantine records) ────────────────────────────
    excluded += [
        {'figure': 'Per-metro moat composite scores + strong/moderate/weak '
                   'verdicts',
         'value': 'composite 1.00-3.00 per 20 metros; verdicts strong 6 / '
                  'moderate 12 / weak 2',
         'source_label': 'ift_moat.market_moat_scores() — 6 of 7 factors '
                         'are authored ordinal reads; basis string renamed '
                         '"FRAMEWORK" from ILLUSTRATIVE on 2026-07-10',
         'why_excluded': 'A mean of authored ordinals looks numeric but '
                         'measures nothing; only the density inputs are '
                         'SOURCED and those live on Metro_Structure_20',
         'what_would_make_citable': 'Claims-measured market shares per '
                                    'metro (CMS MUP/PSPS supplier-grain '
                                    'pulls) replacing authored ordinals'},
        {'figure': '85%+ share-of-wallet stickiness target',
         'value': '85%+',
         'source_label': 'ift_moat.moat_factors() — operator-thesis target '
                         '(FRAMEWORK label)',
         'why_excluded': 'A thesis target, not a measured market statistic '
                         '— the module says so explicitly',
         'what_would_make_citable': 'Measured share-of-wallet from customer '
                                    'contracts or claims volumes'},
        {'figure': 'Serviceable-share s(m) and contestability tiers per '
                   'metro',
         'value': 's(m) 0.12-0.30 by archetype (e.g. Omaha 0.22)',
         'source_label': 'ift_competitive.market_competition() / '
                         'ift_analytics.sam_formula — modeled share levers',
         'why_excluded': 'ILLUSTRATIVE share assumptions (renamed '
                         'FRAMEWORK); contaminate any number they touch',
         'what_would_make_citable': 'Claims-measured serviceable volumes at '
                                    'supplier grain'},
        {'figure': 'Insourcing band counts and volume-share bands per metro',
         'value': 'fully outsourced 11 / hybrid mostly-outsourced 7 / '
                  'hybrid mostly-insourced 2 / fully insourced 0; band '
                  'cut-points 0-5/5-50/50-95/95-100%',
         'source_label': 'ift_insourcing.market_insourcing() / '
                         'insourcing_framework() — classification over '
                         'PUBLIC-WEB operator reads',
         'why_excluded': 'Framework classification presented as counts; '
                         'cut-points are authored, not observed',
         'what_would_make_citable': 'A survey or claims measurement of '
                                    'insourced transport-volume shares'},
        {'figure': 'MMT third-party revenue estimates (as usable figures)',
         'value': 'Growjo $296.4M / ZoomInfo $293.6M / LeadIQ $100-250M',
         'source_label': 'ift_company.REVENUE_ESTIMATES (Growjo / ZoomInfo '
                         '/ LeadIQ, 2026, unaudited)',
         'why_excluded': '~3x disagreement on revenue AND headcount; the '
                         'module brands them "unusable for underwriting" — '
                         'shown ONLY as the Company_Dossier conflict '
                         'exhibit, never as a fact',
         'what_would_make_citable': 'Audited financials or management '
                                    'accounts in diligence'},
        {'figure': 'AMR Omaha fleet/headcount ("~35 vehicles, ~90 '
                   'employees")',
         'value': '~35 vehicles / ~90 employees',
         'source_label': 'ift_npi_landscape.COMPETITORS AMR read — flagged '
                         '"dated figure, treat as historical" in-module',
         'why_excluded': 'Historical public-web description of the '
                         'Rural/Metro-era operation; kept verbatim inside '
                         'the read text with its flag, not carried as a '
                         'current fact',
         'what_would_make_citable': 'Current AMR Omaha fleet/staffing from '
                                    'GMR filings or a state EMS license '
                                    'roster'},
    ]

    meta = {
        'notes': 'Group C built from ift_company / ift_npi_landscape / '
                 'ift_indepth evidence lines (+ OIG-351 detail via '
                 'ift_service_levels primary citation). PUBLIC-WEB material '
                 'labeled loudly per tab; all modeled competitive scores '
                 'excluded. Known reconciliation items carried on-sheet: '
                 '23-vs-24 NPI docstring discrepancy; VA Beach NPI '
                 'unconfirmed; 13-state claim vs 11 NPI states; 2022 deal '
                 '10-states vs 7-states framing; CERT/OIG-30.2M/muni-NEMT '
                 'rows are excerpt-grade re-verify. ' +
                 ('; '.join(notes) if notes else ''),
        'row_counts': {n: wb[n].max_row for n in
                       [s['name'] for s in SHEETS]},
    }
    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'meta': meta}
