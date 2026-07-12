"""E.4 + X-E.3: the throughput-economics public spine (two tabs).

Tab 1, Throughput_Economics_Public (handoff E.4): the published evidence
under the category's value story - what a boarded ED bed costs or forgoes
(PMID-verified boarding-cost literature), what transfer delay does to
outcomes (the stroke door-in-door-out 174-minute JAMA figure is the anchor),
and the PUBLIC-WEB existence record for EHR-integrated transport ordering
(adoption existence only; performance claims excluded upstream).

Tab 2, GAO_OIG_Shelf (extension X-E.3): one row per GAO / HHS-OIG ambulance
report plus its headline statistics - the oversight record on payment
adequacy, utilization integrity, and the dialysis-transport fraud history
that produced the RSNAT prior-authorization machinery.

All figures transcribed from throughput_shelf.json (compiled 2026-07-11;
PMIDs verified via NCBI eutils esummary/efetch on 2026-07-11; GAO/OIG and
web pages fetched and read the same day). Rows carry their own citation
columns; source rows are registered only for publications promoted to facts.
"""

SHEETS = [
    {'name': 'Throughput_Economics_Public',
     'question': 'What does the published literature establish about the '
                 'cost of ED boarding and transfer delay, and does '
                 'EHR-integrated transport ordering publicly exist?'},
    {'name': 'GAO_OIG_Shelf',
     'question': 'What does the GAO / HHS-OIG oversight record establish '
                 'about ground ambulance payment adequacy and utilization '
                 'integrity?'},
]

ACCESS = '2026-07-11'

# --------------------------------------------------------------- tab 1 data
# (citation, year, PMID/DOI, figure description, (value, fmt),
#  (value2, fmt) or None, unit, exact locator, establishes-note)
A_ROWS = [
    ('Falvo 2007, Acad Emerg Med', 2007, 'PMID 17331916',
     'ED treatment capacity consumed by boarding over 12 months at one '
     '450-bed community hospital', (10397, 'INT'), None,
     'ED bed-hours per year', 'Abstract, Results section',
     'Canonical bed-hour opportunity-cost study'),
    ('Falvo 2007, Acad Emerg Med', 2007, 'PMID 17331916',
     'Additional patient encounters the recovered capacity could have '
     'accommodated', (3175, 'INT'), None, 'encounters per year',
     'Abstract, Results section', None),
    ('Falvo 2007, Acad Emerg Med', 2007, 'PMID 17331916',
     'Additional net revenue had that boarding capacity been recovered',
     (3960264, 'USD'), None, 'USD net revenue per year',
     'Abstract, Results section',
     'Implies about $381 per boarding bed-hour - derived LIVE in Panel D, '
     'never typed'),
    ('Bayley 2005, Ann Emerg Med', 2005, 'PMID 15671965',
     'Annual opportunity cost in lost hospital revenue from boarded chest '
     'pain patients, one urban university hospital', (168300, 'USD'), None,
     'USD per year', 'Abstract, Results section',
     'Extended ED stay showed no association with total hospital costs or '
     'LOS - the loss is ED throughput opportunity cost'),
    ('Bayley 2005, Ann Emerg Med', 2005, 'PMID 15671965',
     'Opportunity cost per patient waiting more than 3 hours for an '
     'inpatient bed', (204, 'USD'), None, 'USD per boarded patient',
     'Abstract, Results section', None),
    ('Pines 2011, Ann Emerg Med', 2011, 'PMID 21514004',
     'Additional daily revenue from a 1-hour reduction in ED boarding, by '
     'capturing left-without-being-seen and diverted-ambulance demand (low '
     'and high estimate)', (9693, 'USD'), (13298, 'USD'),
     'USD per hospital per day, per boarding-hour reduced',
     'Abstract, Results section',
     'The widely cited hospital-level revenue value of a boarding hour'),
    ('Pines 2011, Ann Emerg Med', 2011, 'PMID 21514004',
     'Net revenue per inpatient day: non-ED admissions (Value 1) vs ED '
     'admissions (Value 2)', (4118, 'USD'), (2268, 'USD'),
     'USD per inpatient day', 'Abstract, Results section',
     'Boarding displaces the higher-revenue non-ED admission; a revenue '
     'comparator, not a boarding cost'),
    ('Pines 2011, Ann Emerg Med', 2011, 'PMID 21514004',
     'Estimated net revenue gain per year from optimal bed-management '
     'policies (low and high)', (2700000, 'USD'), (3600000, 'USD'),
     'USD per year', 'Abstract, Results section',
     'Simulation plus regression at one inner-city teaching hospital, '
     '118,000 ED visits over 2 years'),
    ('Foley 2011, West J Emerg Med', 2011, 'PMID 21691525',
     'Annual saving from eliminating ED boarding of admitted adults, '
     'county hospital - CHARGES basis', (9800000, 'USD'), None,
     'USD charges per year', 'Abstract, Results and Conclusion',
     'Charge basis - never comparable to cost-basis rows; Brooklyn NY, '
     '2006-2007 data'),
    ('Foley 2011, West J Emerg Med', 2011, 'PMID 21691525',
     'Annual saving, university hospital - COST basis', (3900000, 'USD'),
     None, 'USD costs per year', 'Abstract, Results and Conclusion',
     'Extrapolates Krochmal and Riley: extended ED stay adds about 11.7 '
     'percent to total hospital LOS'),
    ('Foley 2011, West J Emerg Med', 2011, 'PMID 21691525',
     'Admitted adults held in the ED more than one day: county hospital, '
     '5.0 percent of admissions (Value 1); university hospital, 3.4 '
     'percent (Value 2)', (6205, 'INT'), (3017, 'INT'), 'patients per year',
     'Abstract, Results and Conclusion', None),
    ('Canellas 2024, Ann Emerg Med', 2024, 'PMID 38795079',
     'Total daily cost per boarded acute stroke patient, med/surg: '
     'boarding (Value 1) vs inpatient care (Value 2) - time-driven '
     'activity-based costing', (1856, 'USD'), (993, 'USD'),
     'USD per patient per day', 'Abstract, Results section',
     'The modern TDABC anchor (comprehensive stroke center); differences '
     'larger when traveler-nurse costs are included'),
    ('Canellas 2024, Ann Emerg Med', 2024, 'PMID 38795079',
     'Total daily cost, ICU: boarding (Value 1) vs inpatient care '
     '(Value 2)', (2267, 'USD'), (2165, 'USD'), 'USD per patient per day',
     'Abstract, Results section', None),
]
IX_FALVO_HOURS, IX_FALVO_REV, IX_CAN_MS, IX_CAN_ICU = 0, 2, 11, 12

B_ROWS = [
    ('Stamm 2023, JAMA', 2023, 'PMID 37581671',
     'ANCHOR: median door-in-door-out time at the referring hospital for '
     'stroke interhospital transfer - 108,913 patients, 1,925 US hospitals '
     '(IQR 116 to 276)', (174, 'INT'), None,
     'minutes of referring-hospital dwell per interfacility transfer',
     'Abstract, Results section',
     'Largest published measurement of interfacility transfer delay at '
     'sending hospitals - the ordering and dispatch friction window'),
    ('Stamm 2023, JAMA', 2023, 'PMID 37581671',
     'Share of transfers achieving the recommended door-in-door-out of '
     '120 minutes or less', (0.273, 'PCT1'), None, 'share of transfers',
     'Abstract, Results section', None),
    ('Chalfin 2007, Crit Care Med', 2007, 'PMID 17440421',
     'ICU mortality: ED boarding 6 hours or more before ICU transfer '
     '(Value 1) vs less (Value 2)', (0.107, 'PCT1'), (0.084, 'PCT1'),
     'share of patients', 'Abstract, Measurements and Main Results',
     'n = 50,322; multicenter Project IMPACT database, 2000-2003; the '
     'canonical transfer-delay outcome study'),
    ('Chalfin 2007, Crit Care Med', 2007, 'PMID 17440421',
     'In-hospital mortality: delayed (Value 1) vs not delayed (Value 2)',
     (0.174, 'PCT1'), (0.129, 'PCT1'), 'share of patients',
     'Abstract, Measurements and Main Results', None),
    ('Chalfin 2007, Crit Care Med', 2007, 'PMID 17440421',
     'Median hospital LOS: delayed (Value 1) vs not delayed (Value 2)',
     (7.0, 'DEC1'), (6.0, 'DEC1'), 'days',
     'Abstract, Measurements and Main Results', None),
    ('Singer 2011, Acad Emerg Med', 2011, 'PMID 22168198',
     'In-hospital mortality: boarding under 2 hours (Value 1) vs 12 hours '
     'or more (Value 2)', (0.025, 'PCT1'), (0.045, 'PCT1'),
     'share of admissions', 'Abstract, Results section',
     '41,256 admissions, single suburban academic ED, Oct 2005 to Sep '
     '2008; persisted after comorbidity adjustment'),
    ('Singer 2011, Acad Emerg Med', 2011, 'PMID 22168198',
     'Mean hospital LOS: boarding under 2 hours (Value 1) vs over 24 '
     'hours (Value 2)', (5.6, 'DEC1'), (8.7, 'DEC1'), 'days',
     'Abstract, Results section', None),
    ('Cardoso 2011, Crit Care', 2011, 'PMID 21244671',
     'Increased risk of ICU death per hour waiting for ICU admission '
     '(HR 1.015, 95 percent CI 1.006 to 1.023)', (0.015, 'PCT1'), None,
     'risk increase per hour of delay', 'Abstract, Results section',
     'The most quoted dose-response number in the ICU-delay literature; '
     'prospective cohort, 401 patients'),
    ('Cardoso 2011, Crit Care', 2011, 'PMID 21244671',
     'Fraction of mortality risk attributable to ICU delay (95 percent CI '
     '11.2 to 44.8)', (0.30, 'PCT1'), None, 'attributable fraction',
     'Abstract, Results section', None),
    ('Churpek 2016, J Hosp Med', 2016, 'PMID 27352032',
     'Critically ill ward patients whose ward-to-ICU transfer was delayed '
     'over 6 hours', (0.46, 'PCT1'), None, 'share of patients',
     'Abstract, Results section',
     'Five hospitals; objective eCART criterion for critical illness'),
    ('Churpek 2016, J Hosp Med', 2016, 'PMID 27352032',
     'In-hospital mortality: transfer delayed over 6 hours (Value 1) vs '
     'not (Value 2)', (0.332, 'PCT1'), (0.245, 'PCT1'), 'share of patients',
     'Abstract, Results section', 'Median LOS among survivors 13 vs 11 days'),
    ('Churpek 2016, J Hosp Med', 2016, 'PMID 27352032',
     'Adjusted increase in odds of in-hospital death per 1-hour increase '
     'in transfer delay', (0.03, 'PCT1'), None, 'odds increase per hour',
     'Abstract, Results section', None),
    ('GAO-09-347, Apr 2009', 2009, 'GAO-09-347',
     'ED patients triaged as needing to be seen IMMEDIATELY, 2006: average '
     'wait (Value 1, minutes); share of such visits exceeding the '
     'recommended time frame (Value 2)', (28, 'INT'), (0.739, 'PCT1'),
     'minutes; share of visits',
     'Highlights page figure; Appendix IV wait-time tables',
     'Government framing document: names boarding of admitted patients a '
     'core crowding indicator'),
    ('GAO-09-347, Apr 2009', 2009, 'GAO-09-347',
     'Average metropolitan ED wait to see a physician: 2003 (Value 1) vs '
     '2006 (Value 2)', (51, 'INT'), (60, 'INT'), 'minutes',
     'Highlights page figure; Appendix IV wait-time tables', None),
]
IX_STAMM = 0

# (platform x EHR - source type, published, establishes, url)
C_ROWS = [
    ('Lyft x Epic - Epic newsroom (EHR vendor primary)', '2020-10-13',
     'Health system staff can schedule Lyft rides for patients directly '
     'from the patient profile in Epic; patients do not need the Lyft app. '
     'Native EHR-integrated transport ordering exists in the largest US '
     'EHR.',
     'https://www.epic.com/epic/post/lyft-integrate-epic-enabling-ride-'
     'scheduling-within-ehr-workflow/'),
    ('Lyft x Epic - Healthcare Dive (trade press)', '2020-10-08',
     'Independent confirmation of the Lyft-Epic integration with named '
     'early adopters: Tampa General Hospital and Ochsner Health committed '
     'before the November 2020 launch. Named health system adoption, not '
     'performance.',
     'https://www.healthcaredive.com/news/lyft-integrates-with-epic-'
     'exponentially-growing-nemt-reach/586420/'),
    ('Uber Health x Cerner - GlobeNewswire (joint press release)',
     '2019-10-28',
     'Clinicians can arrange non-emergency medical transportation from '
     'within the Cerner EHR, with patient name, phone and pickup address '
     'auto-populated from the record; BayCare Health System named as a '
     'client. EHR-integrated ordering in the second major US EHR.',
     'https://www.globenewswire.com/news-release/2019/10/28/1936452/0/en/'
     'Uber-Health-and-Cerner-Announce-Plan-to-Help-Consumers-Gain-Easier-'
     'Access-to-Medical-Appointments.html'),
    ('Uber Health x Cerner - vendor page', 'undated (announced 2019)',
     'Vendor listing confirming the capability to arrange medical '
     'transportation using Uber Health directly from the Cerner EHR. '
     'Existence only; the page pickup-time marketing claims are excluded '
     'per shelf rules.',
     'https://www.uberhealth.com/us/en/api-integration/cerner/'),
    ('Roundtrip x Epic - PR Newswire (press release)', '2025-08-18',
     'A multi-modal medical transportation marketplace (rideshare through '
     'wheelchair van, stretcher and ALS/BLS ambulance) announced a '
     'FHIR-based Epic integration, developed with an integrated health '
     'system in Northern California. EHR-integrated ordering extends to '
     'ambulance-level interfacility modes.',
     'https://www.prnewswire.com/news-releases/roundtrip-launches-industry-'
     'leading-fhir-powered-ehr-integration-to-transform-transportation-'
     'workflows-302531326.html'),
    ('VectorCare x Epic - vendor page (/fhir)', 'undated vendor page',
     'Clinical staff can initiate patient transport requests, including '
     'ambulance and interfacility patient logistics, without leaving Epic '
     'via a SMART on FHIR app, with real-time vehicle status inside the '
     'EHR. Existence only; time-savings and customer-count claims are '
     'excluded per shelf rules.',
     'https://www.vectorcare.com/fhir'),
]

# --------------------------------------------------------------- tab 2 data
# (report_no, title, date, url, report-level note or None,
#  [(stat text, (value, fmt) or (text, None), detail or None, locator)])
GROUND_REPORTS = [
    ('OEI-03-90-02130',
     'Ambulance Services for Medicare End-Stage Renal Disease '
     'Beneficiaries: Medical Necessity', '1994-08',
     'https://oig.hhs.gov/oei/reports/oei-03-90-02130.pdf',
     'Earliest OIG evidence that dialysis ambulance utilization is an '
     'integrity hotspot; context for the later RSNAT model', [
         ('Dialysis-related ambulance claim allowances not meeting '
          'Medicare coverage guidelines for medical necessity',
          (0.70, 'PCT1'), '70 percent of dialysis-related transports '
          'reviewed',
          'Findings, p.4 of PDF (heading: Seventy percent of '
          'dialysis-related ambulance claim allowances did not meet '
          'Medicare coverage)'),
         ('Part B ambulance allowances for ESRD beneficiaries, 1991',
          (101000000, 'USD'), '75 percent went to fewer than 2 percent '
          '(2,573) of those beneficiaries',
          'Purpose/Background, pp.1-2 of PDF'),
     ]),
    ('GAO-07-383',
     'Ambulance Providers: Costs and Expected Medicare Margins Vary '
     'Greatly', '2007-05-23', 'https://www.gao.gov/products/gao-07-383',
     None, [
         ('Average cost per ground ambulance transport, 2004',
          (415, 'USD'), '95 percent CI $381 to $450; provider range $99 '
          'to $1,218',
          'Results in Brief and Highlights; full text at '
          'gao.gov/assets/a261088.html'),
         ('Expected 2010 Medicare margin, urban service areas',
          (-0.06, 'PCT1'), 'urban -6 percent (range -18 to +6); rural -1 '
          'percent (-13 to +12); super-rural -17 percent (-35 to +2)',
          'Table 4'),
         ('Survey base', (215, 'INT'), 'providers without shared costs, '
          'representing about 5,200 providers nationally',
          'Highlights and Methodology'),
     ]),
    ('GAO-13-6',
     'Ambulance Providers: Costs and Medicare Margins Varied Widely; '
     'Transports of Beneficiaries Have Increased', '2012-10-01',
     'https://www.gao.gov/products/gao-13-6', None, [
         ('Median cost per ground ambulance transport, 2010',
          (429, 'USD'), 'range $224 to $2,204',
          'Highlights, What GAO Found'),
         ('Median Medicare margin, 2010, WITH temporary add-on payments',
          (0.02, 'PCT1'), '-1 percent without the add-ons',
          'Highlights, What GAO Found'),
         ('Growth in Medicare FFS ground transports, 2004 to 2010',
          (0.33, 'PCT1'), 'BLS nonemergency +59 percent; super-rural BLS '
          'nonemergency +82 percent', 'Highlights, What GAO Found'),
     ]),
    ('OEI-09-12-00350',
     'Memorandum Report: Utilization of Medicare Ambulance Transports, '
     '2002-2011', '2013-09-24',
     'https://oig.hhs.gov/oei/reports/oei-09-12-00350.pdf', None, [
         ('Growth in Part B ambulance transports, 2002 to 2011',
          (0.69, 'PCT1'), 'total Medicare FFS beneficiaries grew just 7 '
          'percent; beneficiaries receiving transports +34 percent',
          'Summary, p.1'),
         ('Growth in dialysis-related transports, 2002 to 2011 - the '
          'fastest of any origin-destination category', (2.69, 'PCT1'),
          'from 753,741 transports in 2002',
          'Summary p.1 and finding section: The Number of '
          'Dialysis-Related Transports Increased 269 Percent'),
         ('Suppliers primarily providing BLS nonemergency transports, '
          '2002 to 2011', ('nearly 2x', None), 'nearly doubled',
          'Summary, p.1'),
     ]),
    ('OEI-09-12-00351',
     'Inappropriate Payments and Questionable Billing for Medicare Part B '
     'Ambulance Transports', '2015-09',
     'https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf', None, [
         ('Medicare Part B ambulance transport payments, 2012',
          (5800000000, 'USD'), 'almost double 2003',
          'Executive Summary, Why We Did This Study'),
         ('Payments for transports not meeting program requirements, '
          'first half of 2012', (24000000, 'USD'),
          'including $17 million to or from noncovered destinations; '
          'PLUS $30 million where the beneficiary received no Medicare '
          'services at pickup, drop-off, or anywhere else',
          'Executive Summary and Findings, pp.12-14'),
         ('Ambulance suppliers with questionable billing', (0.20, 'PCT1'),
          'about 1 in 5; more than half of questionable transports were '
          'for beneficiaries in four metropolitan areas',
          'Findings, pp.15-20'),
     ]),
    ('GAO-18-341',
     'Medicare: CMS Should Take Actions to Continue Prior Authorization '
     'Efforts to Reduce Spending', '2018-04-20',
     'https://www.gao.gov/products/gao-18-341',
     'RSNAT prior authorization targets repetitive nonemergency '
     'transports, dominated by dialysis runs; later made national by '
     'statute', [
         ('RSNAT (repetitive scheduled non-emergent ambulance transport) '
          'prior authorization: estimated potential savings, 3 initial '
          'demonstration states (NJ, PA, SC), implementation through '
          'March 2017', (349500000, 'USD'),
          'plus $38.0 million in 6 expansion states', 'Table 2, p.16'),
         ('Estimated savings from ALL prior authorization demonstrations '
          'through March 2017', (1100000000, 'USD'),
          'as high as about $1.9 billion at the top of the published '
          'range', 'Highlights, What GAO Found'),
         ('RSNAT provisional affirmation rate, Oct 2016 to Mar 2017',
          (0.66, 'PCT1'), 'up from 28 percent in Dec 2014 to May 2015',
          'p.12'),
     ]),
    ('A-09-17-03018',
     'Medicare Improperly Paid Providers for Nonemergency Ambulance '
     'Transports to Destinations Not Covered by Medicare', '2018-07-11',
     'https://oig.hhs.gov/oas/reports/region9/91703018.asp', None, [
         ('Improper payments for nonemergency transports to noncovered '
          'destinations, audit period', (8633940, 'USD'),
          '$8.7 million as rounded in the report',
          'What OIG Found summary and first recommendation on report '
          'page'),
         ('Improper claim lines that were transports to diagnostic or '
          'therapeutic sites (other than physician offices or hospitals) '
          'not originating from SNFs', (0.59, 'PCT1'), None,
          'What OIG Found summary on report page'),
     ]),
    ('A-09-18-03030',
     'Medicare Incorrectly Paid Providers for Emergency Ambulance '
     'Transports From Hospitals to Skilled Nursing Facilities',
     '2019-09-11',
     'https://oig.hhs.gov/oas/reports/region9/91803030.asp',
     'Small dollars but squarely interfacility (hospital to SNF) billing '
     'integrity', [
         ('Incorrect payments for hospital-to-SNF transports billed at '
          'EMERGENCY rates, CYs 2015-2017', (849170, 'USD'), None,
          'What OIG Found section on report page'),
         ('Projected additional incorrect payments if billing continued '
          'through CY 2018', (119548, 'USD'), None,
          'What OIG Found section on report page'),
     ]),
]

AIR_REPORTS = [
    ('GAO-17-637',
     'Air Ambulance: Data Collection and Transparency Needed to Enhance '
     'DOT Oversight', '2017-07-27',
     'https://www.gao.gov/products/gao-17-637',
     'AIR mode - boundary context only; never pooled with ground figures', [
         ('Median helicopter air ambulance charge per transport, 2014',
          (30000, 'USD'), 'approximately doubled from about $15,000 in '
          '2010', 'Highlights, What GAO Found'),
         ('Median Medicare payment per helicopter transport, 2014',
          (6502, 'USD'), None, 'Highlights, What GAO Found'),
         ('Share of industry helicopters operated by the three large '
          'independent providers, 2016', (0.73, 'PCT1'), None,
          'Highlights, What GAO Found'),
     ]),
    ('GAO-19-292',
     'Air Ambulance: Available Data Show Privately-Insured Patients Are '
     'Frequently Out of Network', '2019-03-20',
     'https://www.gao.gov/products/gao-19-292',
     'AIR mode; balance-billing exposure evidence preceding the No '
     'Surprises Act', [
         ('Out-of-network share of privately insured air ambulance '
          'transports, 2017', (0.69, 'PCT1'),
          'of about 20,700 transports in the data set',
          'Highlights, What GAO Found'),
         ('Median provider price for a helicopter transport, 2017',
          (36400, 'USD'), None, 'Highlights, What GAO Found'),
     ]),
]


def _ht(pairs):
    """Row height for wrapped cells: pairs of (text, chars-per-line)."""
    lines = 1
    for text, cpl in pairs:
        if text:
            lines = max(lines, -(-len(str(text)) // cpl))
    return lines * 11.5 + 3.5


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    def fmt(key):
        return {'INT': lib.FMT_INT, 'USD': lib.FMT_USD, 'USD2': lib.FMT_USD2,
                'PCT1': lib.FMT_PCT1, 'DEC1': lib.FMT_DEC1}.get(key)

    # ---------------------------------------------------------- sources ---
    sources += [
        {'key': 'canellas_2024',
         'publisher': 'Annals of Emergency Medicine (ACEP)',
         'document': 'Canellas MM, Jewell M, Edwards JL, Olivier D, '
                     'Jun-O\'Connell AH, Reznek MA. Measurement of Cost of '
                     'Boarding in the Emergency Department Using '
                     'Time-Driven Activity-Based Costing. Ann Emerg Med '
                     '2024;84(4):376-385',
         'vintage': '2024 publication; TDABC at a comprehensive stroke '
                    'center',
         'locator': 'Abstract, Results; PMID 38795079; DOI '
                    '10.1016/j.annemergmed.2024.04.012',
         'supplies': 'The modern per-day boarding cost anchor: $1,856 '
                     'med/surg boarding vs $993 inpatient; $2,267 ICU '
                     'boarding vs $2,165',
         'url': 'https://pubmed.ncbi.nlm.nih.gov/38795079/', 'tier': 'A',
         'accessed': accessed, 'powers': ['Throughput_Economics_Public']},
        {'key': 'stamm_2023', 'publisher': 'JAMA',
         'document': 'Stamm B, Royan R, Giurcanu M, Messe SR, Jauch EC, '
                     'et al. Door-in-Door-out Times for Interhospital '
                     'Transfer of Patients With Stroke. JAMA '
                     '2023;330(7):636-649',
         'vintage': '2023 publication; 108,913 transfers, 1,925 US '
                    'hospitals',
         'locator': 'Abstract, Results; PMID 37581671; DOI '
                    '10.1001/jama.2023.12739; open access PMC10427946',
         'supplies': 'Largest published measurement of interfacility '
                     'transfer delay at referring hospitals: median DIDO '
                     '174 minutes, 27.3% within 120 minutes',
         'url': 'https://pubmed.ncbi.nlm.nih.gov/37581671/', 'tier': 'A',
         'accessed': accessed, 'powers': ['Throughput_Economics_Public']},
        {'key': 'falvo_2007', 'publisher': 'Academic Emergency Medicine',
         'document': 'Falvo T, Grove L, Stachura R, Vega D, Stike R, '
                     'Schlenker M, Zirkin W. The opportunity loss of '
                     'boarding admitted patients in the emergency '
                     'department. Acad Emerg Med 2007;14(4):332-337',
         'vintage': '2007 publication; 12 months at one 450-bed community '
                    'hospital',
         'locator': 'Abstract, Results; PMID 17331916; DOI '
                    '10.1197/j.aem.2006.11.011',
         'supplies': 'The canonical bed-hour opportunity-cost figures: '
                     '10,397 boarding bed-hours, 3,175 forgone encounters, '
                     '$3,960,264 forgone net revenue per year',
         'url': 'https://pubmed.ncbi.nlm.nih.gov/17331916/', 'tier': 'A',
         'accessed': accessed, 'powers': ['Throughput_Economics_Public']},
        {'key': 'cardoso_2011', 'publisher': 'Critical Care (BioMed Central)',
         'document': 'Cardoso LT, Grion CM, Matsuo T, Anami EH, Kauss IA, '
                     'Seko L, Bonametti AM. Impact of delayed admission to '
                     'intensive care units on mortality of critically ill '
                     'patients: a cohort study. Crit Care 2011;15(1):R28',
         'vintage': '2011 publication; prospective cohort, 401 patients',
         'locator': 'Abstract, Results; PMID 21244671; DOI 10.1186/cc9975; '
                    'open access PMC3222064',
         'supplies': 'The dose-response number for delay: each hour '
                     'waiting for ICU admission associated with 1.5% '
                     'higher ICU death risk (HR 1.015)',
         'url': 'https://pubmed.ncbi.nlm.nih.gov/21244671/', 'tier': 'A',
         'accessed': accessed, 'powers': ['Throughput_Economics_Public']},
        {'key': 'epic_lyft_2020', 'publisher': 'Epic (EHR vendor newsroom)',
         'document': 'Lyft to Integrate with Epic, Enabling Ride '
                     'Scheduling within EHR Workflow (13 Oct 2020)',
         'vintage': 'Published 2020-10-13; fetched live 2026-07-11',
         'locator': 'Vendor newsroom post, full page',
         'supplies': 'EHR-vendor primary evidence that native '
                     'EHR-integrated transport ordering exists in the '
                     'largest US EHR (existence only)',
         'url': 'https://www.epic.com/epic/post/lyft-integrate-epic-'
                'enabling-ride-scheduling-within-ehr-workflow/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Throughput_Economics_Public']},
        {'key': 'uber_cerner_2019',
         'publisher': 'Uber Health / Cerner (GlobeNewswire joint release)',
         'document': 'Uber Health and Cerner Announce Plan to Help '
                     'Consumers Gain Easier Access to Medical Appointments '
                     '(28 Oct 2019)',
         'vintage': 'Published 2019-10-28; fetched live 2026-07-11',
         'locator': 'Joint press release, full page; BayCare Health '
                    'System named',
         'supplies': 'Primary press evidence of EHR-integrated transport '
                     'ordering in the second major US EHR (existence only)',
         'url': 'https://www.globenewswire.com/news-release/2019/10/28/'
                '1936452/0/en/Uber-Health-and-Cerner-Announce-Plan-to-Help-'
                'Consumers-Gain-Easier-Access-to-Medical-Appointments.html',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Throughput_Economics_Public']},
        {'key': 'gao_18_341',
         'publisher': 'US Government Accountability Office',
         'document': 'Medicare: CMS Should Take Actions to Continue Prior '
                     'Authorization Efforts to Reduce Spending, GAO-18-341 '
                     '(20 Apr 2018)',
         'vintage': 'Demonstration data through March 2017',
         'locator': 'Table 2, p.16 (RSNAT savings by state group); p.12 '
                    '(affirmation rates); Highlights',
         'supplies': 'The RSNAT outcome numbers: $349.5M estimated '
                     'savings in 3 states plus $38.0M in 6 expansion '
                     'states; affirmation rate 28% to 66%',
         'url': 'https://www.gao.gov/products/gao-18-341', 'tier': 'A',
         'accessed': accessed, 'powers': ['GAO_OIG_Shelf']},
        {'key': 'oei_09_12_00350',
         'publisher': 'HHS Office of Inspector General',
         'document': 'Memorandum Report: Utilization of Medicare Ambulance '
                     'Transports, 2002-2011, OEI-09-12-00350 (24 Sep 2013)',
         'vintage': 'Part B claims 2002-2011',
         'locator': 'Summary, p.1; finding section on dialysis-related '
                    'transports (+269 percent)',
         'supplies': 'The utilization arc: transports +69% vs '
                     'beneficiaries +7%; dialysis transports +269%, the '
                     'fastest origin-destination category',
         'url': 'https://oig.hhs.gov/oei/reports/oei-09-12-00350.pdf',
         'tier': 'A', 'accessed': accessed, 'powers': ['GAO_OIG_Shelf']},
        {'key': 'oei_09_12_00351',
         'publisher': 'HHS Office of Inspector General',
         'document': 'Inappropriate Payments and Questionable Billing for '
                     'Medicare Part B Ambulance Transports, '
                     'OEI-09-12-00351 (September 2015)',
         'vintage': '2012 claims (first half 2012 for improper-payment '
                    'review)',
         'locator': 'Executive Summary; Findings pp.12-20',
         'supplies': 'Program scale and integrity: $5.8B Part B ambulance '
                     'spend in 2012; $24M + $30M improper/no-service '
                     'payments in H1 2012; 1 in 5 suppliers with '
                     'questionable billing',
         'url': 'https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf',
         'tier': 'A', 'accessed': accessed, 'powers': ['GAO_OIG_Shelf']},
        {'key': 'oei_03_90_02130',
         'publisher': 'HHS Office of Inspector General',
         'document': 'Ambulance Services for Medicare End-Stage Renal '
                     'Disease Beneficiaries: Medical Necessity, '
                     'OEI-03-90-02130 (August 1994)',
         'vintage': '1991 Part B allowances; claim review circa 1993',
         'locator': 'Findings, p.4 of PDF; Purpose/Background pp.1-2',
         'supplies': 'The earliest marker of the dialysis-transport '
                     'integrity arc: 70% of dialysis claims failed '
                     'coverage review; $101M 1991 ESRD allowances, 75% to '
                     'under 2% of beneficiaries',
         'url': 'https://oig.hhs.gov/oei/reports/oei-03-90-02130.pdf',
         'tier': 'A', 'accessed': accessed, 'powers': ['GAO_OIG_Shelf']},
    ]

    # ==================================================== TAB 1: E.4 ======
    ws = wb.create_sheet('Throughput_Economics_Public')
    sb = lib.SheetBuilder(ws, 9,
                          col_widths=[28, 7, 17, 44, 11, 11, 19, 22, 38],
                          tab_color='FF4C7C2C')
    sb.title('Throughput economics, public spine: what a boarded bed and a '
             'delayed transfer cost, and where transport ordering lives')
    sb.subtitle('The question: what does the PUBLISHED literature establish '
                'about the cost of ED boarding and the outcome cost of '
                'transfer delay, and does EHR-integrated transport ordering '
                'publicly exist? Sources: peer-reviewed studies with PMIDs '
                'verified against NCBI eutils on 11 Jul 2026, one GAO '
                'framing report, and PUBLIC-WEB vendor/press pages fetched '
                'the same day (throughput_shelf.json). No join keys: this '
                'is an evidence shelf; every row carries its own citation, '
                'figure, unit and exact locator - that is its registration.')
    sb.note('DATA QUALITY: publication years span 2005 to 2024 and every '
            'dollar figure is nominal to its study year. Costing methods '
            'differ - TDABC (Canellas) vs charge-based (Foley county '
            'estimate) vs opportunity-cost revenue (Falvo, Bayley, Pines) - '
            'and sites are single hospitals or small panels, so figures '
            'are CONTEXTS for what boarding costs, not a rate card. '
            'Outcome studies are adjusted associations, not causal '
            'transport effects. Panel D pools ONLY within a single unit.')
    sb.blank()

    def shelf_row(cite, yr, pmid, desc, v1, v2, unit, loc, note):
        sb.row([(cite, 'text'), (yr, 'src'), (pmid, 'note'), (desc, 'text'),
                (v1[0], 'src', fmt(v1[1])) if v1 else None,
                (v2[0], 'src', fmt(v2[1])) if v2 else None,
                (unit, 'text'), (loc, 'note'),
                (note, 'note') if note else None],
               wrap=True,
               height=_ht([(desc, 40), (note, 34), (cite, 25), (unit, 17),
                           (loc, 20)]))

    # Panel A -------------------------------------------------------------
    sb.banner('Panel A. The boarding-cost shelf: every published figure, '
              'with its unit and exact locator (PMID-verified)')
    sb.headers(['Citation', 'Year', 'PMID / DOI', 'Published figure',
                'Value 1', 'Value 2', 'Unit', 'Exact locator',
                'What it establishes'])
    a0 = sb.r + 1
    for r in A_ROWS:
        shelf_row(*r)
    r_falvo_hours = a0 + IX_FALVO_HOURS
    r_falvo_rev = a0 + IX_FALVO_REV
    r_can_ms = a0 + IX_CAN_MS
    r_can_icu = a0 + IX_CAN_ICU
    sb.blank()

    # Panel B -------------------------------------------------------------
    sb.banner('Panel B. Transfer-delay outcome literature: what delay does '
              'to mortality and LOS (stroke DIDO 174 minutes is the anchor)')
    sb.headers(['Citation', 'Year', 'PMID / DOI', 'Published figure',
                'Value 1', 'Value 2', 'Unit', 'Exact locator',
                'What it establishes'])
    b0 = sb.r + 1
    for r in B_ROWS:
        shelf_row(*r)
    r_stamm = b0 + IX_STAMM
    sb.blank()

    # Panel C -------------------------------------------------------------
    sb.banner('Panel C. EHR-integrated transport ordering: the PUBLIC-WEB '
              'existence record (adoption existence only)')
    sb.headers(['Platform x EHR (source type)', '', 'Published',
                'What the public page establishes', '', '', '',
                'Access date', 'URL'])
    c0 = sb.r + 1
    for plat, pub, est, url in C_ROWS:
        sb.row([(plat, 'text'), None, (pub, 'src'), (est, 'src'), None,
                None, None, (ACCESS, 'src'), (url, 'note')],
               wrap=True, height=_ht([(est, 40), (plat, 25), (url, 34),
                                      (pub, 15)]))
    c_end = sb.r
    sb.row([('Public integration records on this shelf (live)', 'label'),
            None, None,
            ('Four distinct platform x EHR pairs (Lyft-Epic, Uber '
             'Health-Cerner, Roundtrip-Epic, VectorCare-Epic) across the '
             'two dominant US EHR vendors', 'note'),
            (f'=COUNTA($A${c0}:$A${c_end})', 'fml', lib.FMT_INT),
            None, ('records', 'text'), None, None],
           wrap=True, height=25)
    c_count = sb.r
    sb.note('Hard rule, applied upstream and carried here: '
            'adoption-existence only. These rows establish that the named '
            'integrations exist and which health systems are publicly '
            'named. No pickup-time, time-saving, or customer-count claims '
            'from vendor marketing pages are recorded (they sit on the '
            'shelf rejected list), and nothing here is a performance claim '
            'for any platform or operator.')
    sb.blank()

    # Panel D -------------------------------------------------------------
    sb.banner('Panel D. The published range, computed live - within a '
              'single unit only, never across units')
    sb.headers(['Live range row', '', '', 'How it is built',
                'Cell 1 / MIN', 'Cell 2 / MAX', 'Cell 3 / COUNT', 'Unit',
                'Caveat (same row)'])
    d1 = sb.r + 1
    sb.row([('Normalized per-bed-hour set (live)', 'label'), None, None,
            (f'Cell 1: Falvo forgone net revenue per boarding bed-hour '
             f'(=E{r_falvo_rev}/E{r_falvo_hours}). Cell 2: Canellas '
             f'med/surg boarding cost per hour (=E{r_can_ms}/24). Cell 3: '
             f'Canellas ICU boarding cost per hour (=E{r_can_icu}/24).',
             'text'),
            (f'=E{r_falvo_rev}/E{r_falvo_hours}', 'fml', lib.FMT_USD2),
            (f'=E{r_can_ms}/24', 'fml', lib.FMT_USD2),
            (f'=E{r_can_icu}/24', 'fml', lib.FMT_USD2),
            ('USD per bed-hour', 'text'),
            ('Falvo is forgone NET REVENUE per hour (2007); Canellas is '
             'TDABC COST per hour (2024) - same unit, different constructs '
             'and decades', 'note')],
           wrap=True, height=48)
    d2 = sb.r + 1
    sb.row([('Published per-BED-HOUR range (live)', 'label'), None, None,
            ('MIN / MAX / COUNT over the three normalized per-bed-hour '
             'cells above', 'text'),
            (f'=MIN(E{d1}:G{d1})', 'fml', lib.FMT_USD2),
            (f'=MAX(E{d1}:G{d1})', 'fml', lib.FMT_USD2),
            (f'=COUNT(E{d1}:G{d1})', 'fml', lib.FMT_INT),
            ('USD per bed-hour', 'text'),
            ('A context band, not a rate card: methods differ and years '
             'span 2007 to 2024', 'note')],
           wrap=True, height=36)
    d3 = sb.r + 1
    sb.row([('Published per-BED-DAY range (live)', 'label'), None, None,
            (f'MIN / MAX / COUNT over the Panel A per-patient-day BOARDING '
             f'cost cells only (E{r_can_ms} med/surg $1,856; E{r_can_icu} '
             f'ICU $2,267). The inpatient comparators in Value 2 are NOT '
             f'pooled.', 'text'),
            (f'=MIN(E{r_can_ms},E{r_can_icu})', 'fml', lib.FMT_USD),
            (f'=MAX(E{r_can_ms},E{r_can_icu})', 'fml', lib.FMT_USD),
            (f'=COUNT(E{r_can_ms},E{r_can_icu})', 'fml', lib.FMT_INT),
            ('USD per patient-day (boarded)', 'text'),
            ('TDABC only, one comprehensive stroke center - the sole '
             'published per-day cost measurement', 'note')],
           wrap=True, height=48)
    sb.note('Unit split across the 13 Panel A figure rows, printed so the '
            'guardrail is visible: 5 rows are USD per hospital-YEAR '
            '(Falvo revenue, Bayley annual, Pines bed-management, Foley '
            'county charges + university costs), 1 is USD per '
            'hospital-DAY per boarding-hour reduced (Pines), 1 is USD per '
            'boarded PATIENT (Bayley $204), 1 is revenue per inpatient '
            'day (Pines comparator), 2 are USD per patient-DAY boarded '
            '(Canellas), and 3 are volume/capacity counts (bed-hours, '
            'encounters, boarded patients). Figures in different units '
            'are NEVER averaged; the only live ranges are the two '
            'single-unit rows above.')
    sb.blank()

    sb.banner('Read panel')
    sb.prose('What is measured, and only from public documents: (1) the '
             'modern TDABC measurement prices a boarded med/surg '
             'patient-day at $1,856 against $993 for the same day of '
             'inpatient care, and an ICU boarding day at $2,267 (Canellas '
             '2024); (2) across two decades of methods, a boarded bed-hour '
             'is worth roughly $77 (TDABC cost, 2024) to $381 (opportunity '
             'net revenue, 2007) - computed live in Panel D and never '
             'blended across units; (3) delay has a published outcome '
             'dose-response: 1.5 percent higher ICU death risk per hour '
             'waiting (Cardoso), higher mortality bands with longer '
             'boarding (Chalfin, Singer, Churpek); (4) the interfacility '
             'transfer itself is slow at the sending door - median stroke '
             'door-in-door-out 174 minutes, with only 27.3 percent inside '
             'the recommended 120 (Stamm 2023, JAMA); and (5) '
             'EHR-integrated transport ordering publicly exists in both '
             'dominant US EHRs, extending to ambulance-level interfacility '
             'modes by 2025 (Panel C, existence only). Together: hospitals '
             'carry a measured, published throughput cost, and the '
             'ordering-and-dispatch window is a named, measured friction '
             'point. What this tab does NOT say: it quantifies no saving '
             'for any product and attributes no performance to any '
             'platform or operator.')

    facts += [
        {'metric': 'Total daily cost per boarded acute stroke patient, '
                   'med/surg boarding (TDABC)', 'year': 2024, 'value': 1856,
         'unit': 'USD per patient per day', 'basis': 'ACADEMIC',
         'tier': 'A', 'source_keys': ['canellas_2024'],
         'locator': 'Ann Emerg Med 2024;84(4):376-385, abstract Results; '
                    'PMID 38795079',
         'lives_on': 'Throughput_Economics_Public',
         'cross_check': 'Med/surg inpatient comparator $993 and ICU pair '
                        '$2,267 vs $2,165 in the same abstract; per-hour '
                        'normalization exists only as live formulas in '
                        'Panel D'},
        {'metric': 'Median door-in-door-out time at the referring '
                   'hospital, stroke interhospital transfer', 'year': 2023,
         'value': 174, 'unit': 'minutes', 'basis': 'ACADEMIC', 'tier': 'A',
         'source_keys': ['stamm_2023'],
         'locator': 'JAMA 2023;330(7):636-649, abstract Results; '
                    'PMID 37581671',
         'lives_on': 'Throughput_Economics_Public',
         'cross_check': 'IQR 116 to 276; only 27.3% of 108,913 transfers '
                        'from 1,925 hospitals met the recommended 120 '
                        'minutes'},
        {'metric': 'Forgone net revenue from ED capacity consumed by '
                   'boarding, one 450-bed community hospital',
         'year': 2007, 'value': 3960264, 'unit': 'USD per year',
         'basis': 'ACADEMIC', 'tier': 'A', 'source_keys': ['falvo_2007'],
         'locator': 'Acad Emerg Med 2007;14(4):332-337, abstract Results; '
                    'PMID 17331916',
         'lives_on': 'Throughput_Economics_Public',
         'cross_check': '10,397 boarding bed-hours and 3,175 forgone '
                        'encounters in the same abstract; about $381 per '
                        'bed-hour derived live on Panel D'},
        {'metric': 'Increased risk of ICU death per hour of waiting for '
                   'ICU admission', 'year': 2011, 'value': 0.015,
         'unit': 'risk increase per hour (HR 1.015)', 'basis': 'ACADEMIC',
         'tier': 'A', 'source_keys': ['cardoso_2011'],
         'locator': 'Crit Care 2011;15(1):R28, abstract Results; '
                    'PMID 21244671',
         'lives_on': 'Throughput_Economics_Public',
         'cross_check': '95% CI 1.006 to 1.023; attributable fraction of '
                        'mortality risk 30% (CI 11.2 to 44.8)'},
        {'metric': 'Public records establishing EHR-integrated patient '
                   'transport ordering (existence only)', 'year': 2026,
         'value': 6, 'unit': 'PUBLIC-WEB records (4 distinct platform x '
         'EHR pairs)', 'basis': 'PUBLIC-WEB', 'tier': 'A',
         'source_keys': ['epic_lyft_2020', 'uber_cerner_2019'],
         'locator': 'Panel C rows on Throughput_Economics_Public; count '
                    'is a live COUNTA on the tab; each row carries its '
                    'URL and access date',
         'lives_on': 'Throughput_Economics_Public',
         'cross_check': 'Covers both dominant US EHRs (Epic, Oracle '
                        'Cerner) and extends to ambulance-level '
                        'interfacility modes (Roundtrip 2025, VectorCare); '
                        'adoption existence only, no performance claims'},
    ]

    findings.append({
        'id_hint': 63,
        'finding': 'The published price of a boarded bed is a range, not a '
                   'number, and it is now computed live on the tab: '
                   'normalized within-unit, the literature brackets a '
                   'boarded bed-hour between about $77 (TDABC cost, 2024) '
                   'and about $381 (opportunity net revenue, 2007), and a '
                   'boarded patient-day at $1,856 to $2,267 (TDABC, 2024) '
                   '- alongside a mortality dose-response of 1.5% per '
                   'hour of ICU delay and a 174-minute median stroke '
                   'door-in-door-out at referring hospitals. That is the '
                   'public spine under the throughput value story.',
        'numbers': f"='Throughput_Economics_Public'!E{d2}",
        'sources': 'canellas_2024; falvo_2007; stamm_2023; cardoso_2011',
        'confidence': 'High that each figure is published as stated '
                      '(PMIDs verified against NCBI eutils); the range '
                      'itself is a context band across methods and years',
        'guardrail': 'Units are the guardrail: per-bed-hour and '
                     'per-bed-day ranges are computed separately, and '
                     'per-patient, per-hospital-day and per-hospital-year '
                     'figures are never pooled with them or with each '
                     'other. Costing methods (TDABC, charge-based, '
                     'opportunity-cost) are never averaged. This is not a '
                     'rate card and not a savings claim for any product '
                     'or operator.'})

    # ================================================== TAB 2: X-E.3 ======
    ws2 = wb.create_sheet('GAO_OIG_Shelf')
    sb2 = lib.SheetBuilder(ws2, 7,
                           col_widths=[16, 56, 11, 13, 34, 28, 26],
                           tab_color='FF6B7C93')
    sb2.title('The GAO / HHS-OIG ambulance shelf: three decades of '
              'oversight on payment adequacy and utilization integrity')
    sb2.subtitle('The question: what does the federal oversight record '
                 'establish about ground ambulance - are payments '
                 'adequate, where does utilization integrity break, and '
                 'what machinery resulted? Sources: 10 GAO and HHS-OIG '
                 'reports (1994-2019) from throughput_shelf.json, each '
                 'fetched and read on 11 Jul 2026. No join keys: one row '
                 'per report (number, title, date, URL) followed by its '
                 'headline statistics with exact locators - the rows are '
                 'their own registration.')
    sb2.note('DATA QUALITY: report years span 1994 to 2019, so every '
             'dollar figure is nominal to its own year - never '
             'inflation-blend, sum, or trend dollars across reports. GAO '
             'cost and margin figures are survey-based estimates with '
             'published CIs and ranges (printed in the same row). The two '
             'air-ambulance reports are mode-boundary context only and '
             'are never pooled with ground figures.')
    sb2.blank()

    rsnat_row = {'r': None}

    def report_block(rep):
        no, title, date, url, rep_note, stats = rep
        sb2.row([(no, 'src'), (title, 'src'), (date, 'src'), None,
                 (rep_note, 'note') if rep_note else None, None,
                 (url, 'note')],
                wrap=True, height=_ht([(title, 50), (rep_note, 30),
                                       (url, 24)]))
        for stat, val, detail, loc in stats:
            v, f = val
            cell = (v, 'src', fmt(f)) if f else (v, 'src')
            sb2.row([(no, 'note'), (stat, 'text'), None, cell,
                     (detail, 'src') if detail else None, (loc, 'note'),
                     None],
                    wrap=True, height=_ht([(stat, 50), (detail, 30),
                                           (loc, 25)]))
            if no == 'GAO-18-341' and stat.startswith('RSNAT (repetitive'):
                rsnat_row['r'] = sb2.r

    sb2.banner('Panel A. Ground ambulance oversight, in date order (report '
               'row, then its headline statistics)')
    sb2.headers(['Report no.', 'Title / headline statistic', 'Date',
                 'Value', 'Value detail (as published)', 'Exact locator',
                 'URL / note'])
    g0 = sb2.r + 1
    for rep in GROUND_REPORTS:
        report_block(rep)
    g_end = sb2.r
    sb2.blank()

    sb2.banner('Panel B. Air ambulance boundary reports (mode context '
               'only; never pooled with ground)')
    sb2.headers(['Report no.', 'Title / headline statistic', 'Date',
                 'Value', 'Value detail (as published)', 'Exact locator',
                 'URL / note'])
    x0 = sb2.r + 1
    for rep in AIR_REPORTS:
        report_block(rep)
    x_end = sb2.r
    sb2.blank()

    sb2.banner('Panel C. Shelf summary (live)')
    sb2.row([('Ground ambulance oversight reports (live)', 'label'), None,
             None, (f'=COUNTA(C{g0}:C{g_end})', 'fml', lib.FMT_INT),
             ('dates print only on report rows, so COUNTA over the date '
              'column counts reports, not statistic rows', 'note'), None,
             None], wrap=True, height=25)
    sb2.row([('Air boundary reports (live)', 'label'), None, None,
             (f'=COUNTA(C{x0}:C{x_end})', 'fml', lib.FMT_INT), None, None,
             None])
    sb2.row([('Report-date span', 'label'), None, None, None,
             ('1994-08 to 2019-09-11: dollar figures are nominal to their '
              'own years', 'note'), None, None])
    sb2.blank()

    sb2.banner('Read panel')
    sb2.prose('What the oversight record establishes about ground '
              'ambulance, read in date order. Payment adequacy has been '
              'genuinely contested for two decades: GAO 2007 projected '
              '2010 Medicare margins of -6 percent urban and -17 percent '
              'super-rural, and GAO 2012 found a +2 percent median margin '
              'that turned negative without the temporary add-on payments '
              '- the add-on politics that the GADCS data collection later '
              'formalized. Utilization integrity concentrates in exactly '
              'one place: scheduled non-emergency transport. OIG measured '
              'transports growing +69 percent against +7 percent '
              'beneficiary growth (2002-2011) with BLS nonemergency '
              'suppliers nearly doubling, then found $5.8B of 2012 spend '
              'with about 1 in 5 suppliers showing questionable billing. '
              'The dialysis strand runs the whole arc: 70 percent of '
              'dialysis claims failed coverage review in 1994, dialysis '
              'transports grew +269 percent by 2011, and the policy '
              'outcome is the RSNAT prior-authorization machinery - '
              '$349.5M estimated savings in three states, later made '
              'national by statute. What this is NOT: these are findings '
              'about a payment channel and its era, not about any '
              'operator, and the air rows are mode boundary only.')

    facts += [
        {'metric': 'RSNAT prior authorization, estimated potential '
                   'savings, 3 initial demonstration states (NJ, PA, SC)',
         'year': 2017, 'value': 349500000, 'unit': 'USD (nominal, '
         'implementation through March 2017)', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['gao_18_341'],
         'locator': 'GAO-18-341, Table 2, p.16',
         'lives_on': 'GAO_OIG_Shelf',
         'cross_check': 'Plus $38.0M in 6 expansion states on the same '
                        'table; provisional affirmation rate rose from '
                        '28% to 66% (p.12); the model was later made '
                        'national by statute'},
        {'metric': 'Growth in Medicare Part B dialysis-related ambulance '
                   'transports, 2002 to 2011', 'year': 2011, 'value': 2.69,
         'unit': 'growth over period (+269 percent)', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['oei_09_12_00350'],
         'locator': 'OEI-09-12-00350, Summary p.1 and dialysis finding '
                    'section',
         'lives_on': 'GAO_OIG_Shelf',
         'cross_check': 'From 753,741 transports in 2002; fastest of any '
                        'origin-destination category; all Part B '
                        'transports +69% vs beneficiaries +7% over the '
                        'same window'},
        {'metric': 'Medicare Part B ambulance transport payments, 2012',
         'year': 2012, 'value': 5800000000, 'unit': 'USD (nominal 2012)',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['oei_09_12_00351'],
         'locator': 'OEI-09-12-00351, Executive Summary (Why We Did This '
                    'Study)',
         'lives_on': 'GAO_OIG_Shelf',
         'cross_check': 'Almost double 2003; H1-2012 review found $24M '
                        'not meeting requirements plus $30M with no '
                        'Medicare services anywhere, and about 1 in 5 '
                        'suppliers with questionable billing'},
        {'metric': 'Dialysis-related ambulance claim allowances failing '
                   'Medicare medical-necessity coverage review',
         'year': 1994, 'value': 0.70, 'unit': 'share of reviewed '
         'dialysis-related transports', 'basis': 'GOV', 'tier': 'A',
         'source_keys': ['oei_03_90_02130'],
         'locator': 'OEI-03-90-02130, Findings p.4 of PDF',
         'lives_on': 'GAO_OIG_Shelf',
         'cross_check': '1991 ESRD ambulance allowances were $101M with '
                        '75% concentrated in fewer than 2% (2,573) of '
                        'beneficiaries - the earliest marker of the '
                        'dialysis integrity arc'},
    ]

    findings.append({
        'id_hint': 64,
        'finding': 'The oversight arc is one story told for three '
                   'decades: scheduled non-emergency (dialysis-heavy) '
                   'ground transport is where Medicare ambulance '
                   'integrity questions concentrate - 70% of dialysis '
                   'claims failed coverage review in 1994, dialysis '
                   'transports grew +269% over 2002-2011 while '
                   'beneficiaries grew 7%, and by 2012 a $5.8B program '
                   'showed about 1 in 5 suppliers with questionable '
                   'billing - and the RSNAT prior-authorization machinery '
                   '($349.5M estimated savings in three states, later '
                   'national by statute) is the policy outcome. Payment '
                   'adequacy ran the other way the whole time: GAO margin '
                   'work found breakeven-to-negative Medicare margins '
                   'held up by temporary add-ons.',
        'numbers': f"='GAO_OIG_Shelf'!D{rsnat_row['r']}",
        'sources': 'gao_18_341; oei_09_12_00350; oei_09_12_00351; '
                   'oei_03_90_02130',
        'confidence': 'High: government reports with hard numbers and '
                      'page-level locators, fetched and read',
        'guardrail': 'Integrity findings characterize a PAYMENT CHANNEL '
                     '(repetitive scheduled non-emergency transport under '
                     'Medicare Part B) and its era - never any operator, '
                     'and no figure here may be attached to any company. '
                     'Dollar figures are nominal to their report years '
                     'and must never be inflation-blended or summed '
                     'across reports.'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'shelf': 'throughput_shelf.json (compiled 2026-07-11; '
                              'PMIDs verified via NCBI eutils)',
                     'rejected_upstream': 13}}
