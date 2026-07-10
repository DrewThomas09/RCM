"""Family: one tab per In-Depth question — InDepth_Q01 .. InDepth_Q10.

Source: rcm_mc.market_reports.ift_indepth (contract + aggregator) and its
content modules ift_indepth_q1 / q23 / q456 / q78 / q910. Each tab renders
one of the 10 study questions:
  Panel A — the answered evidence table: every cited fact-line (claim, basis
            chip exactly as the module labels it, re-verify flag, source,
            URL). Blue = literal carried from the named publisher source;
            FRAMEWORK lines are analytic scaffolds rendered black, and any
            FRAMEWORK line carrying a NUMBER is EXCLUDED (quarantined).
  Panel B — that question's subquestion Q&A registry (answered rows).
  Panel C — the honesty register: subquestions explicitly skipped with the
            diligence-request reason (79 across the 10 questions; 57 on Q8).
  Panel D — coverage & basis audit (live COUNTIF/COUNTA formulas) + chart.

Zero ILLUSTRATIVE by construction (module contract, test-enforced); the six
FRAMEWORK-chip lines that embed numbers (85%+ share-of-wallet, repatriation
~1:1, four-band cut-points, 20-metro band counts 11/7/2/0, vendor '2-3
hrs/shift') are excluded here and logged in `excluded`.
"""
import math
import re
import sys

sys.path.insert(0, '/home/user/RCM/RCM_MC')
sys.path.insert(0, '/home/user/RCM')

PURPLE = 'FF7A5195'

SHEETS = [{'name': f'InDepth_Q{n:02d}', 'tab_color': PURPLE}
          for n in range(1, 11)]


def _ht(*pairs):
    """Row height estimate for wrapped Arial-9 text: (text, col_width)."""
    lines = 1
    for text, w in pairs:
        t = str(text or '')
        cpl = max(8, int(w * 1.15))
        lines = max(lines, math.ceil(len(t) / cpl) if t else 1)
    return min(160, max(15, lines * 12 + 4))


# ── Source families: dedup register over the 183 distinct module source
#    strings. Order matters — first regex match wins.
#    (key, pattern, publisher, document, vintage, locator, supplies, url)
_FAM = [
    ('medpac_gadcs', r'MedPAC assessment of GADCS', 'MedPAC',
     'MedPAC assessment of CMS/RAND GADCS ground-ambulance cost data '
     '(Dec 2025)',
     'December 2025',
     'Assessment findings: strong inverse relationship between annual '
     'transport volume and cost per response; GADCS-based industry '
     'readings carried across Q1/Q2/Q5-Q10',
     'The volume-cost curve behind the density/scale argument', ''),
    ('gadcs', r'GADCS', 'CMS / RAND (via AAA + trade coverage)',
     'Ground Ambulance and Patient Billing (GADCS) Year 1-2 report + '
     'Year 1-4 appendix (Dec 2025) — RE-VERIFY: excerpt-grade captures '
     'via trade coverage, primary PDFs not reopened',
     'Year 1-2 (2024); Year 1-4 appendix Dec 2025',
     'Cost per transport $2,673 all / $3,127 governmental / $1,778 '
     'private FP; mean reimbursement $1,147; labor 70.7% (from 69% '
     'Y1-2); collect-nothing 19.7% (from 18.8%); Medicare+MA 42% of '
     'transport revenue',
     'The industry unit-economics benchmark set (P&L physics of ground '
     'ambulance)', 'https://ambulance.org/2025/12/09/cms-releases-new-gadcs-report/'),
    ('cms_afs', r'CMS AFS|Ambulance Fee Schedule|Claims Processing Manual',
     'CMS',
     'Ambulance Fee Schedule — RVU ladder, CY2025 conversion factor, '
     'mileage, Ambulance Inflation Factor (Claims Processing Manual '
     'ch.15; AFS PUF; RE-VERIFY CF/AIF against the PUF before '
     'circulation)',
     'CY2025-CY2026',
     'RVUs BLS 1.00 / BLS-E 1.60 / ALS1 1.20 / ALS1-E 1.90 / ALS2 2.75 '
     '/ SCT 3.25; CY2025 CF $278.98; ~$8/loaded-mile; AIF CY2025 +2.4% '
     '/ CY2026 +2.0%',
     'The Medicare payment-parameter spine (relative-value ladder + '
     'escalator)', ''),
    ('aha_fastfacts', r'AHA Fast Facts', 'American Hospital Association',
     'AHA Fast Facts on US Hospitals 2026 (FY2024 Annual Survey) — '
     'RE-VERIFY: excerpt-grade capture',
     '2026 edition (FY2024 data)',
     '70% of non-federal general acute hospitals system-affiliated '
     '(3,567 of 5,121, FY2024)',
     'The buyer-consolidation denominator (system-level contracting '
     'feasibility)', 'https://www.aha.org/statistics/fast-facts-us-hospitals'),
    ('medpac_pb', r'MedPAC', 'MedPAC',
     'Payment Basics: Ambulance Services Payment System (Oct 2024) + '
     'the SNF/IRF/LTCH payment-basics series',
     'October 2024 (2024 data year)',
     'Medicare FFS ground ambulance 11.3M transports, $5.3B payments, '
     '~10,600 billing organizations (2024); post-acute volumes ~1.8M '
     'SNF stays / ~383k IRF / ~90k LTCH',
     'The Medicare ambulance universe + post-acute volume denominators',
     'https://www.medpac.gov/wp-content/uploads/2024/10/MedPAC_Payment_Basics_24_ambulance_FINAL_SEC.pdf'),
    ('emtala', r'489\.24', 'CMS (eCFR)',
     '42 CFR 489.24 — EMTALA appropriate-transfer duties',
     'Current eCFR',
     'Transfer duty text: hospitals must effect appropriate transfers '
     'whether or not contracted transport capacity exists',
     'The statutory demand floor for urgent IFT',
     'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-G/part-489/subpart-B/section-489.24'),
    ('nemt_statute', r'431\.53|440\.170|1902\(a\)\(70\)|SMD 23-006',
     'CMS / Social Security Act',
     '42 CFR 431.53 / 440.170 (NEMT assurance of transportation); SSA '
     '1902(a)(70) + CMS SMD 23-006 (brokerage authority)',
     'Current statute/regulation',
     'NEMT is a federally mandated Medicaid benefit administered mostly '
     'through capitated brokers — the statutory boundary separating '
     'NEMT from IFT',
     'The NEMT market-boundary definition',
     'https://www.ecfr.gov/current/title-42/chapter-IV/subchapter-C/part-431/subpart-B/section-431.53'),
    ('cms_rsnat', r'RSNAT', 'CMS',
     'RSNAT prior-authorization program rules + model documents',
     'Nationwide since Aug 1, 2022',
     'Repetitive definition: 3+ round trips/10 days or 1+/week for 3+ '
     'weeks; affirmation covers 120 round trips/180 days',
     'The scheduling-definition + prior-auth rules for repetitive '
     'non-emergent transport', ''),
    ('benefit_policy', r'410\.40|Benefit Policy Manual|MAC guidance|'
     r'First Coast', 'CMS',
     '42 CFR 410.40(e)/(f) + Benefit Policy Manual ch.10 (§10.3 '
     'nearest-appropriate-facility; bed-confinement three-part test; '
     'PCS ≤60 days) + MAC guidance (First Coast)',
     'Current regulation/manual',
     'Medical-necessity gating, physician certification statements, '
     'and the nearest-appropriate-facility rule',
     'The reimbursement-gating rules every IFT claim clears', ''),
    ('afs_statute', r'414 subpart H|CAA 2026', 'CMS / Congress',
     '42 CFR 414 subpart H + CAA 2026 §6203 (ambulance add-ons; ESRD '
     'BLS cut)',
     'Add-ons extended through 2027; ESRD cut effective Oct 2018',
     'Super-rural +22.6% / urban +2% / rural +3% extended through '
     '2027; non-emergency dialysis BLS fee schedule −23%',
     'The geographic add-on and dialysis-cut payment rules', ''),
    ('cms_cert', r'CERT', 'CMS',
     'Comprehensive Error Rate Testing (CERT) 2024 Medicare FFS '
     'Supplemental Improper Payment Data — ambulance (RE-VERIFY: '
     'excerpt-grade capture)',
     '2024 report year',
     'Ambulance improper-payment rate 13.2% / $595.1M projected; 63.5% '
     'insufficient documentation / 27.5% medical necessity',
     'The documentation-risk split for transport claims', ''),
    ('cms_gapb', r'GAPB', 'CMS',
     'Ground Ambulance and Patient Billing (GAPB) Advisory Committee '
     'report',
     '2024',
     'Ground ambulance excluded from the No Surprises Act; committee '
     'recommends OON billing ban with cost-share capped at lesser of '
     '$100 or 10%',
     'The balance-billing policy trajectory', ''),
    ('ne_dhhs', r'NE DHHS', 'Nebraska DHHS',
     'Nebraska Statewide EMS Assessment 2023-24 (RE-VERIFY: '
     'excerpt-grade capture)',
     '2023-24 assessment cycle',
     '80%+ of NE EMS agencies all-volunteer; 31% of volunteer agencies '
     'adequately staffed; 28% expect to be unable to operate within 5 '
     'years; verbatim excess-agencies finding',
     'The volunteer-collapse evidence in the core geography',
     'https://dhhs.ne.gov/OEHS%20Program%20Documents/NE%20Statewide%20EMS%20Assessment%20v2024.pdf'),
    ('fair_health', r'FAIR Health', 'FAIR Health',
     'Ground ambulance out-of-network study (2022 claims)',
     '2023 (2022 data)',
     '~60% of ground ambulance rides out-of-network in 2022',
     'The payer-distance / OON structure of ambulance billing',
     'https://www.fairhealth.org/article/nearly-60-percent-of-ground-ambulance-rides-were-out-of-network-in-2022-according-to-new-fair-health-study'),
    ('hcci', r'HCCI|Health Care Cost Institute', 'Health Care Cost Institute',
     'Ground-ambulance commercial price analysis (ESI 2022 data)',
     '2022 data year',
     'Commercial base $718 vs Medicare $365 (2.0x); mileage $17 vs $8',
     'The commercial-vs-Medicare price relativity', ''),
    ('aimhi', r'AIMHI', 'AIMHI / EMS1',
     'AIMHI high-performance EMS benchmarking survey (via EMS1 '
     'coverage)',
     'As captured 2026-07-10',
     'Unit-hour utilization: 911 band 0.30-0.50; AIMHI survey mean '
     '0.508',
     'The UHU capacity-productivity benchmark', ''),
    ('hcup_transfers', r'Nikolla|Mueller|HCUP', 'AHRQ HCUP (via journals)',
     'Nikolla et al., J Emerg Med 2025 (HCUP NEDS 2018-2022 adult '
     'ED-to-ED transfers) + Hernandez-Boussard et al., J Patient Saf 2017 '
     '(HCUP NIS inpatient interhospital transfers)',
     'NEDS 2018-2022 pooled; NIS 2009 study (epub 2014)',
     '9,867,701 adult ED-to-ED transfers 2018-2022 (~1.97M/yr); 6.6% '
     'with critical procedures, rising OR 1.09/yr; ~1.5M/yr inpatient '
     'interhospital (~3.5% of admissions)',
     'The measured acute-IFT demand base',
     'https://doi.org/10.1016/j.jemermed.2025.12.020'),
    ('greenwood', r'Greenwood-Ericksen', 'JAMA Network Open',
     'Greenwood-Ericksen & Kocher, JAMA Network Open 2019 / 2021 '
     '(rural ED utilization; transfer propensity)',
     '2019 / 2021 (data 2005-2016)',
     'Rural ED visits 16.7M → 28.4M (2005-2016); ED transfer '
     'propensity rural 6.2% vs urban 2.0%',
     'The rural demand-shift series', ''),
    ('peters', r'Peters et al', 'Am J Emerg Med',
     'Peters et al., Am J Emerg Med 2026 (ED visits arriving by IFT)',
     '2026 (periods 2014-16 / 2017-19 / 2020-22)',
     'ED visits arriving by interfacility transport +15% (2017-19) and '
     '+35% (2020-22) vs the 2014-16 baseline',
     'The closest thing to a trendable IFT demand index', ''),
    ('lee_2026', r'Lee et al', 'Ann Emerg Med',
     'Lee et al., Ann Emerg Med 2026 (NHAMCS 2015-2022 ED boarding, '
     'admitted 65+)',
     '2026 (NHAMCS 2015-2022)',
     '85.2% of admitted 65+ boarded ≥2h; mean boarding 138 min (2018) '
     '→ 343 min (2022); 501 min with dementia',
     'The boarding-crisis trend the IFT queue drains into', ''),
    ('nhamcs', r'NHAMCS|NCHS', 'CDC NCHS',
     'National Hospital Ambulatory Medical Care Survey (NHAMCS) — ED '
     'transfer disposition shares',
     '2018 / 2021 survey years',
     '2.4% of ED visits ended in transfer (2021) vs 2.8% (2018) on '
     '~140-155M annual visits',
     'The national ED-transfer share mini-series', ''),
    ('ng_2017', r'\bNg et al', 'Stroke',
     'Ng et al., Stroke 2017 (stroke transfer door-in-door-out)',
     '2017',
     '82.8% of transfer time spent at the referring hospital; DIDO 106 '
     'min; 37.3% >120 min',
     'Stroke DIDO decomposition (referrer-side dwell)', ''),
    ('gwtg_2023', r'GWTG', 'JAMA',
     'Get With The Guidelines-Stroke analysis, JAMA 2023 (n=108,913)',
     '2023',
     'Prenotification −20.1 min; median DIDO 174 min; 27.3% within '
     '120 min',
     'The stroke-transfer coordination benchmark', ''),
    ('jamano_2024', r'JAMA Network Open 2024', 'JAMA Network Open',
     'Stroke DIDO decomposition study, JAMA Network Open 2024 '
     '(n=28,887)',
     '2024',
     'Mean DIDO 171.4 min = 18.3 door-to-imaging + 153.1 '
     'imaging-to-door',
     'Where transfer time actually goes (imaging-to-door dwell)', ''),
    ('wang_2011', r'Wang et al', 'JAMA',
     'Wang et al., JAMA 2011 (STEMI transfer DIDO and mortality, '
     'n=14,821)',
     '2011',
     'Median DIDO 68 min, 11% ≤30 min; in-hospital mortality 5.9% vs '
     '2.7%, adjusted OR 1.56 (95% CI 1.15-2.12)',
     'The mortality cost of slow transfers (STEMI)', ''),
    ('backer_2018', r'Backer', 'Prehosp Emerg Care',
     'Backer et al., Prehospital Emergency Care 2018 (CA crew '
     'detention, 830,637 transports, 2017)',
     '2018 (CA 2017 data)',
     '75% of CA hospitals detained crews >1h; 40% >2h; 33% >3h',
     'The crew-detention distribution (throughput failure at the '
     'hospital door)', ''),
    ('shaw_2025', r'Shaw', 'Prehosp Emerg Care',
     'Shaw et al., Prehospital Emergency Care 2025 (ESO 2024 records, '
     'n=7,237,606)',
     '2025 (2024 data)',
     'National median APOT 10.9 min (IQR 6.6-17.5); 3.3% of agencies '
     'had ≥25% of transports >30 min, urban-skewed',
     'The national offload-time distribution', ''),
    ('wasicek_2022', r'Wasicek', 'Plast Reconstr Surg',
     'Wasicek et al., Plast Reconstr Surg 2022 (NTDB 2007-2015 facial '
     'fracture transfers)',
     '2022 (NTDB 2007-2015)',
     'ED-discharge-on-arrival share of transfers +151% while operative '
     'intervention fell — secondary over-triage evidence',
     'The over-triage / avoidable-transfer signal', ''),
    ('landeiro_2019', r'Landeiro', 'The Gerontologist',
     'Landeiro et al., The Gerontologist 2019 (delayed-discharge '
     'systematic review, 64 studies)',
     '2019',
     'Delayed discharges weighted mean 22.8% of stays (range '
     '1.6-91.3%); cost $142-$31,935 PPP per case',
     'The delayed-discharge economics anchor', ''),
    ('gao_berland', r'Gao & Berland', 'Brown J Hosp Med',
     'Gao & Berland, Brown Journal of Hospital Medicine 2022',
     '2022',
     '3.5% of hospitalizations consumed 27.2% of 23,934 inpatient '
     'days; facility placement the top discharge barrier',
     'The bed-day concentration of discharge delays', ''),
    ('ego_2022', r'Ego et al', 'Ann Med Surg',
     'Ego et al., Annals of Medicine and Surgery 2022 (PACU discharge '
     'delays, 307-patient non-US cohort — magnitude only, caveat '
     'travels)',
     '2022',
     '61.2% of PACU discharge delays non-clinical; transport '
     'unavailability 11.1% (n=34), second to bed unavailability 22.5%',
     'The transport share of peri-operative flow delays', ''),
    ('acep_poll', r'ACEP', 'ACEP / Morning Consult',
     'ACEP / Morning Consult national boarding poll (Oct 2023, '
     'n=2,164)',
     'October 2023',
     '44% of US adults report prolonged post-ED waits (self or loved '
     'one); 16% report ≥13 hours',
     'The public-experience read on boarding',
     'https://www.emergencyphysicians.org/press-releases/2023/10-2-23-new-poll-half-of-emergency-physicians-say-hospital-boarding-has-increased'),
    ('pmc_discharge', r'PMC11023539', 'PubMed Central (single-site QI study)',
     'Single-site discharge-task QI study, PMC11023539 (RE-VERIFY; '
     'single site, caveat travels)',
     'As captured 2026-07-10',
     'Pending care-management/transportation the most frequent '
     'uncompleted discharge task (47%)',
     'The discharge-task bottleneck read', ''),
    ('kff_shf', r'KFF', 'KFF (on AHA survey data)',
     'KFF State Health Facts — hospital adjusted expenses per '
     'inpatient day (RE-VERIFY: expense proxy, not marginal cost)',
     '2023 data',
     'Hospital adjusted expense ~$3,132/inpatient day (nonprofit '
     '$3,288 / for-profit $2,529)',
     'The bed-day value anchor for delay economics', ''),
    ('aha_alos', r'AHA Issue Brief', 'American Hospital Association',
     'AHA Issue Brief, Dec 2022 (RE-VERIFY: excerpt-grade capture)',
     'December 2022',
     'Average length of stay +19% (2019→2022); +24% for patients '
     'discharged to post-acute care',
     'The ALOS deterioration series', ''),
    ('contreary', r'Contreary', 'JAMA Health Forum',
     'Contreary et al., JAMA Health Forum 2022 — RSNAT prior-auth '
     'model evaluation (ESRD cohort)',
     '2022',
     'doi:10.1001/jamahealthforum.2022.2093 — 61% reduction in '
     'probability of RSNAT use; 77% reduction in RSNAT spend '
     '($1,136/beneficiary-yr); 19% annual increase in emergency '
     'dialysis use',
     'The best natural experiment on transport payment policy',
     'https://doi.org/10.1001/jamahealthforum.2022.2093'),
    ('oig_351', r'OIG', 'HHS Office of Inspector General',
     'OEI-09-12-00351 (2015) — inappropriate payments and questionable '
     'billing for Medicare Part B ambulance transports (H1-2012 '
     'claims)',
     'Report 2015 (data H1-2012)',
     '$30.2M paid in one half-year with no Medicare service at origin '
     'or destination; 21% of suppliers met ≥1 of 7 '
     'questionable-billing measures; 4 metros = 18% of transports but '
     '52% of questionable ones',
     'The program-integrity findings block',
     'https://oig.hhs.gov/oei/reports/oei-09-12-00351.pdf'),
    ('ca_ab40', r'AB 40|EMSA', 'State of California / EMSA',
     'AB 40 (2023) ambulance patient offload time standard + EMSA APOT '
     'monitoring (RE-VERIFY flag carried)',
     '2023 statute; program current',
     'Offload not to exceed 30 minutes 90% of the time; monthly '
     'per-hospital EMSA monitoring',
     'The statutory offload-clock precedent',
     'https://emsa.ca.gov/apot/'),
    ('ca_eoa', r'1797\.224', 'State of California',
     'Health & Safety Code 1797.224 — exclusive operating areas via '
     'competitive award',
     'Current statute',
     'EOA competitive-award authority (+ state Medicaid contract '
     'records where cited)',
     'The 911 procurement-cadence precedent',
     'https://leginfo.legislature.ca.gov/faces/codes_displaySection.xhtml?lawCode=HSC&sectionNum=1797.224'),
    ('muni_contracts', r'Municipal EMS|911 contracting dossier|NFPA|'
     r'City of Lincoln', 'Municipal contract records',
     'Urban 911 EMS performance contracts (Pasadena TX; Multnomah '
     'County OR; San Diego/Falck) + NFPA 1710 norms + City of Lincoln '
     'EMS program records (RE-VERIFY: excerpt-grade, from the repo '
     'contracting dossier)',
     'Contracts as captured 2026-07-10',
     '8:59@90% urban fractile; Pasadena 14:59 cap; Multnomah penalties '
     'below 90%; San Diego/Falck $5,000 per response beyond 24 min; '
     'Lincoln F&R published rate schedule + EMS Oversight Authority',
     'The 911 SLA-and-penalty contract technology IFT lacks', ''),
    ('nemt_enforcement', r'Mississippi Today|State enforcement|'
     r'enforcement records|enforcement coverage', 'State records via press',
     'NEMT broker enforcement records — Mississippi Today Sep 2024 + '
     'NJ / GA state records (RE-VERIFY: press-carried)',
     'MS coverage Sep 2024; NJ 2017-22; GA 2018-20',
     'MS: ~3,000 of >52,000 monthly trips late/missed (~5.8%), ~3x '
     'the contractual limit; NJ fined Modivcare ~$1.7M; GA fined '
     'brokers >$1M',
     'The NEMT enforcement precedent rows', ''),
    ('nemt_contracts', r'Broker contract|TX HHSC|TX MTP|MTP contract|'
     r'NEMT contracting dossier|broker contracts', 'Texas HHSC + state '
     'NEMT broker contracts',
     'TX Medical Transportation Program contract terms + state NEMT '
     'broker standards (RE-VERIFY: excerpt-grade)',
     'As captured 2026-07-10',
     'TX 85% on-time benchmark with $15,000 penalty cap; broker '
     'contracts commonly ≥95% on-time standards with penalties',
     'The NEMT SLA precedent rows', ''),
    ('modivcare_ch11', r'Bankruptcy docket', 'U.S. Bankruptcy Court '
     'S.D. Tex. + deal coverage',
     'Modivcare Inc. Chapter 11 docket + coverage (RE-VERIFY)',
     'Filed Aug 20, 2025; emerged Dec 29, 2025',
     'Emergence cut >$1.1B of ~$1.4B funded debt',
     'The vendor-financial-stability precedent', ''),
    ('csh_results', r'CommonSpirit', 'CommonSpirit Health',
     'CommonSpirit FY2025 year-end results release (RE-VERIFY)',
     'FY2025 (release 2025)',
     'Operating loss $225M FY2025, improved from $875M FY2024',
     'The system-finance context for insourcing appetite', ''),
    ('chartis_sheps', r'Chartis|Sheps', 'Chartis + UNC Sheps Center',
     'Chartis rural health state-of-the-state + UNC Sheps Center rural '
     'hospital closures tracker (RE-VERIFY)',
     '2025 vintages',
     '194 rural hospital closures since 2005 (151 post-2010); 432 at '
     'risk; 331 rural hospitals dropped OB 2011-2024 (IA −22)',
     'The rural service-line contraction series', ''),
    ('jrh_2026', r'J Rural Health', 'Journal of Rural Health',
     'REH conversion adaptation study, J Rural Health 2026',
     '2026',
     '40-50 Rural Emergency Hospital conversions since Jan 2023, ~half '
     'in KS/TX/NE/OK; no inpatient beds, <24h stays, transfer '
     'agreements mandatory',
     'The REH structural transfer-demand driver', ''),
    ('niddk_usrds', r'NIDDK|USRDS', 'NIDDK / USRDS',
     'Kidney disease statistics (RE-VERIFY: excerpt-grade)',
     'As captured 2026-07-10',
     '>808,000 living with ESRD; ~68% on dialysis; 3 sessions/week',
     'The recurring dialysis-demand base',
     'https://www.niddk.nih.gov/health-information/health-statistics/kidney-disease'),
    ('cdc_samhsa', r'CDC/SAMHSA', 'CDC / SAMHSA',
     'ED utilization statistics (mental health)',
     'As captured 2026-07-10',
     '~6M mental-health-related ED visits/yr (~1 in 8 involve MH/SUD)',
     'The behavioral-transfer demand base', ''),
    ('cms_carecompare', r'Care Compare|Provider-of-Services', 'CMS',
     'Care Compare / Provider-of-Services files (via '
     'ift_clinical_demand.destination_supply())',
     'Snapshots as vendored 2026-07-10',
     '14,699 SNFs + 1,221 IRFs + 317 LTACHs + 12,392 HHAs + 6,852 '
     'hospices = 35,481 post-acute destinations',
     'The destination-supply node counts', ''),
    ('ne_press', r'Omaha World-Herald / Journal Star',
     'Omaha World-Herald / Lincoln Journal Star',
     'Nebraska statewide transfer-center coverage, Nov 2021 '
     '(RE-VERIFY: press-carried figures)',
     'November 2021 (COVID-era context)',
     '146 of 234 requested transfers confirmed (Sep 2021, 62%); 113 '
     'of 168 (Oct 2021, 67%)',
     'The only public IFT acceptance-shortfall gauge', ''),
    ('deal_press', r'Deal/IPO coverage|Deal press releases',
     'Deal press / trade coverage',
     'Sector transaction coverage: PE consolidation events 2022-2025 '
     '(MMT/Harbour Point, AmeriPro/Whistler, AMR/KKR) + GMR '
     'refinancing/IPO coverage (RE-VERIFY where flagged)',
     '2022-2026',
     'MMT/Harbour Point Jan 2022; AmeriPro/Whistler Feb 2025; GMR '
     '$5.4B 2025 refinancing → IPO valuation target cut to $3.3B '
     '(May 2026)',
     'The capital-structure context rows', ''),
    ('ameripro_pr', r'AmeriPro|PRNewswire', 'PRNewswire / AmeriPro Health',
     'AmeriPro Health acquires Priority Medical Transport — press '
     'release',
     'February 2025',
     'Whistler-backed AmeriPro enters NE: Lincoln, Red Willow, '
     'Buffalo, Dawson, Adams, Dodge, Platte counties',
     'The PE-backed challenger entry event',
     'https://www.prnewswire.com/news-releases/ameripro-health-acquires-priority-medical-transport-and-expands-midwest-presence-302372373.html'),
    ('mmt_web', r'mmtamb|Siouxland Chamber', 'MMT Ambulance (company '
     'self-report)',
     'mmtamb.com About Us + Siouxland Chamber directory entry '
     '(captured 2026-07-10)',
     '2026 site capture',
     '13 states, 2,800+ team members, 500+ vehicles, "over 35 years"; '
     'verbatim "not a 911 service" positioning',
     'Company scale claims + positioning (self-report, never a '
     'measurement)', 'https://mmtamb.com/about-us/'),
    ('court_dockets', r'Justia|CourtListener|NLRB',
     'U.S. District Courts (Justia / CourtListener) + NLRB',
     'Public dockets: Reust N.D. Ohio 1:20-cv-01548 (2020); Wroblewski '
     'E.D. Wis. 2:23-cv-00877 (2023); Meysenburg D. Neb. '
     '4:2024-cv-03107 (2024); NLRB 14-CA-251082 (Wichita 2019, closed)',
     'Filings 2019-2024; pulled 2026-07-10',
     'Three FLSA wage-and-hour suits in three districts + one NLRB ULP '
     'charge; outcomes sealed without PACER (stated)',
     'The labor-model litigation register',
     'https://dockets.justia.com/docket/nebraska/nedce/4:2024cv03107/103544'),
    ('revenue_estimators', r'Growjo|ZoomInfo|LeadIQ',
     'Growjo / ZoomInfo / LeadIQ (third-party estimators)',
     'Unaudited third-party revenue/headcount estimates for MMT — '
     'CONFLICT EXHIBIT, module-branded unusable for underwriting '
     '(RE-VERIFY)',
     '2026 captures',
     'Growjo $296.4M/784 employees; ZoomInfo $293.6M; LeadIQ '
     '$100-250M/~700 — ~3x spread, never blended, never a market '
     'number',
     'The revenue-estimate conflict exhibit (carried with its '
     'unusable label)',
     'https://growjo.com/company/Midwest_Medical_Transport'),
    ('omb_census', r'OMB 2023', 'OMB / U.S. Census Bureau',
     'OMB 2023 CBSA delineations × 2020 Census county populations',
     'OMB Bulletin 23-01; 2020 Census',
     'MMT legacy core: 22 counties, ~1.56M people across 7 CBSAs on '
     'the I-80 spine',
     'The legacy-core geography denominator', ''),
    ('mmt_press', r'Harbour Point|Lincoln International|'
     r'Lincoln Journal Star|Businesswire|Omaha World-Herald|'
     r'Columbus Telegram', 'Businesswire / Lincoln International / '
     'Lincoln Journal Star / Omaha World-Herald',
     'MMT deal + local-press corpus: Harbour Point recapitalization '
     'release (Jan 25, 2022); Lincoln International sell-side notice; '
     'LJS Feb 2015 sale coverage; OWH/Columbus Telegram founding '
     'retrospectives + Midwest MedAir coverage',
     '2015-2022 events; pages captured 2026-07-10',
     '200,000+ missions/yr, then-10-states (2022 release) vs "seven '
     'states and nearly 1,000 employees" (advisor) — conflict shown, '
     'never blended; founded 1987; 2015 sale: 350+ employees, 13 '
     'ground locations, 2 helicopter bases; MedAir 30,000 ground + '
     '400+ helicopter calls',
     'The MMT ownership/scale event record',
     'https://www.businesswire.com/news/home/20220125006174/en/'),
    ('repo_derived', r'mission_mix|ift_mmt footprint demand band',
     'rcm_mc derivation modules (equations stated in-text)',
     'ift_clinical_demand.mission_mix() (GOV condition volumes × '
     'authored transport-acuity tiers) + ift_mmt footprint demand '
     'band (ACADEMIC transfer counts ÷ GOV Census population shares)',
     'Computed 2026-07-10 from cited inputs',
     'Mission mix ~56% CCT/SCT/specialty / ~12% ALS / ~32% low-acuity; '
     'footprint demand band 3.47M measured national acute legs/yr '
     'allocated by population vs 65+ share',
     'The transparent DERIVED lines (equation stated in every claim)',
     ''),
    ('repo_framework', r'dead-end log|ift_study|ift_insourcing|ift_moat|'
     r'ift_clinical_demand|purchasing synthesis|VectorCare',
     'rcm_mc analytic frameworks (repo modules)',
     'ift_study registries, ift_insourcing classification model, '
     'ift_moat operator thesis, ift_clinical_demand scaffolds + the '
     '2026-07-10 research dead-end log — FRAMEWORK chip, TEXT ONLY '
     '(every numeric FRAMEWORK line is excluded from these tabs)',
     'Authored 2026-07-10',
     'Analytic scaffolds and documented not-founds; the absence of '
     'published data is itself the finding on these rows',
     'The honesty-register scaffolding (no numbers carried)', ''),
    ('footprint_web', r"Footprint|ift_geo|Children's Nebraska|CHI Health|"
     r'Bryan Health|System-page|ift_health_systems|City EMS pages',
     'Health-system / operator / municipal public web pages',
     'Footprint operator registry sweep (Children\'s Nebraska, CHI '
     'Health, Bryan Health, Mayo, Allina, Superior/Mount Carmel, '
     'AMR/UofL, Ryan Brothers, Omaha FD, city EMS pages) — RE-VERIFY '
     'heavy: public/company self-report',
     'Pages captured 2026-07-10',
     'Operator postures: Mayo ~70 units; Allina ~34,000 interfacility '
     'requests (2024); CHI Kearney 911 + AirCare; Children\'s CAMTS '
     'fleet; Omaha FD 18 ALS; Wichita ~77% flip to AMR (2022); '
     'embedded-coordinator exemplars',
     'The named-operator competitive registry', ''),
    ('local_press', r'System press releases|Local press coverage',
     'Local / system press',
     'Footprint consolidation + closure coverage (RE-VERIFY: '
     'press-carried)',
     '2018-2026 events; captured 2026-07-10',
     'Methodist-Fremont 2018 (50-yr lease); Bryan-Kearney Jan 2022; '
     'Bryan-Pender Jun 2025; UnityPoint-MercyOne Siouxland Sep 2025; '
     'CHI Council Bluffs L&D closure announced 2026-07-10',
     'The footprint M&A / closure event table', ''),
    ('nppes', r'NPPES', 'CMS',
     'NPPES NPI Registry — NE+IA ambulance-organization sweep (751 org '
     'NPIs, vendored 2026-07-10) + MMT organizational-NPI estate sweep '
     '(23 NPIs, 11 states) + company-web presence cross-sweep',
     'Registry snapshots pulled/vendored 2026-07-10',
     'NE 400 / IA 351 org NPIs; NE 5 vs IA 40+ hospital-owned; NE 58 '
     'private orgs; ~85-90% NE municipal/volunteer; MMT 23 active org '
     'NPIs with enumeration dates 2005-2024',
     'The supply-side and MMT-estate denominators',
     'https://npiregistry.cms.hhs.gov/'),
]

_FAM_RX = [(k, re.compile(p, re.I)) for (k, p, *_rest) in _FAM]


def _family(source_text):
    for k, rx in _FAM_RX:
        if rx.search(source_text):
            return k
    return ''


# Company/press/analyst material sometimes carries a SOURCED/GOV chip in the
# in-depth modules, which reads as "government dataset" on a sourced tab. When a
# line has NO dataset URL and its citation is unmistakably company/press/web
# material, re-chip it PUBLIC-WEB — the label the v3 convention reserves for
# exactly that class — so a company results release is never mistaken for a
# federal dataset. Dataset-cited lines (any URL, or GOV/AHRQ/CMS/MedPAC/journal
# families) are left exactly as the module labels them.
_WEB_SIGNAL = re.compile(
    r'public/company web|public/analyst|analyst read|results release|earnings|'
    r'press release|newsroom|company (?:web|site|blog)|captured \d{4}|'
    r'bankruptcy docket|court docket|coverage\)|news coverage|LinkedIn|'
    r'company web|web capture|self-reported|vendor (?:blog|marketing)',
    re.I)
_DATASET_SIGNAL = re.compile(
    r'CMS|AHRQ|HCUP|NEDS|NIS|MedPAC|NEMSIS|Census|BLS|CDC|NPPES|PECOS|'
    r'Fee Schedule|PSPS|GADCS|OIG|federal register|CFR|U\.S\.C', re.I)


def _display_basis(e):
    b = (e.basis or '').strip()
    if b in ('SOURCED', 'GOV') and not (e.url or '').strip():
        src = e.source or ''
        if _WEB_SIGNAL.search(src) and not _DATASET_SIGNAL.search(src):
            return 'PUBLIC-WEB'
    return b


# ── Excluded FRAMEWORK-numeric lines: metadata by block key ─────────────────
_EXCL_META = {
    'q2-moat': (
        "85%+ share-of-wallet operator target (seven-factor stickiness "
        "frame)", '85%+',
        'Operator-thesis framework target, not a market statistic',
        'An operator contract, KPI report or survey publishing '
        'share-of-wallet distributions'),
    'q3-movements': (
        'Repatriation/back-transfer runs ~1:1 with escalations', '~1:1',
        'No defensible national count exists — the module mirrors '
        'up-transfer volume as an analytic scaffold',
        'A published national origin-destination transfer matrix (e.g., '
        'an HCUP state-pair study)'),
    'q5-variants': (
        'Four-band insourcing spectrum (fully outsourced 0-5% / hybrid '
        'mostly-outsourced 5-50% / hybrid mostly-insourced 50-95% / fully '
        'insourced 95-100% of delivered volume)', 'band cut-points',
        'Authored classification bands (ift_insourcing model), not '
        'observed data',
        'A published taxonomy or survey adopting (or superseding) these '
        'bands'),
    'q5-prevalence': (
        '20-metro insourcing band counts: fully outsourced 11 / hybrid '
        'mostly-outsourced 7 / hybrid mostly-insourced 2 / fully '
        'insourced 0', '11 / 7 / 2 / 0',
        'Framework classification computed over the ift_geo operator '
        'registry — a coded read of sourced operator facts, not a survey '
        'result',
        'A primary survey or claims-based measurement of delivered-volume '
        'shares by metro'),
    'q7-labor': (
        "Vendor claim: nurses spend '2-3 hours per shift' on transport "
        'tasks', '2-3 hrs/shift',
        'Vendor marketing (VectorCare blog), module-labeled explicitly '
        'non-load-bearing',
        'An independent time-motion study of nursing transport-related '
        'tasks'),
    'q9-multivendor': (
        '85%+ share-of-wallet threshold below which a system keeps a '
        'second vendor warm', '85%+',
        'Operator-thesis framework threshold, not a market statistic',
        'Published share-of-wallet distributions from operator or system '
        'contracts'),
}


# ── Fact ledger candidates: the 2-3 strongest cited facts per question ──────
_FACTS = {
    1: [
        {'metric': 'Medicare FFS ground ambulance universe (transports / '
                   'payments / billing organizations)',
         'year': 2024,
         'value': '11.3M transports · $5.3B · ~10,600 organizations',
         'unit': 'mixed (see locator)', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['medpac_pb'],
         'locator': 'MedPAC Ambulance Payment Basics, Oct 2024 — Q1 block '
                    'q1-definitions: "11.3M transports, $5.3B, ~10,600 '
                    'organizations (2024)"',
         'cross_check': 'Same denominators power the $469 DERIVED average '
                        '($5.3B/11.3M) and the fragmentation read on '
                        'InDepth_Q07/Q09'},
        {'metric': 'Measured acute IFT base (adult ED-to-ED + inpatient '
                   'interhospital transfers)',
         'year': 2022,
         'value': '~1.97M/yr ED-to-ED (NEDS 2018-2022) + ~1.5M/yr '
                  'inpatient (NIS)',
         'unit': 'transfers/yr', 'basis': 'ACADEMIC', 'tier': 'B',
         'source_keys': ['hcup_transfers'],
         'locator': 'Nikolla et al., J Emerg Med 2025 '
                    '(doi:10.1016/j.jemermed.2025.12.020; HCUP NEDS '
                    '2018-2022, 9,867,701 pooled) + Hernandez-Boussard et al. '
                    'J Patient Saf 2017 (HCUP NIS 2009) — Q1 q1-definitions',
         'cross_check': 'Feeds the ift_mmt footprint demand band (3.47M '
                        'legs/yr) on InDepth_Q10'},
        {'metric': 'Ground ambulance out-of-network share',
         'year': 2022, 'value': '~60% of rides', 'unit': '% of rides',
         'basis': 'SOURCED', 'tier': 'B', 'source_keys': ['fair_health'],
         'locator': 'FAIR Health 2023 study of 2022 claims — Q1 '
                    'q1-customer',
         'cross_check': 'Pairs with GADCS 19.7% collect-nothing and the '
                        'NSA exclusion / GAPB rows on the same tab'},
    ],
    2: [
        {'metric': 'CA hospital crew-detention distribution (2017, '
                   '830,637 transports)',
         'year': 2017, 'value': '75% of hospitals >1h · 40% >2h · 33% >3h',
         'unit': '% of CA hospitals', 'basis': 'ACADEMIC', 'tier': 'B',
         'source_keys': ['backer_2018'],
         'locator': 'Backer et al., Prehosp Emerg Care 2018 — Q2 '
                    'crew-detention evidence',
         'cross_check': 'Consistent direction with Shaw 2025 national '
                        'APOT tail (3.3% of agencies ≥25% >30 min)'},
        {'metric': 'National median ambulance patient offload time '
                   '(APOT)',
         'year': 2024, 'value': '10.9 min median (IQR 6.6-17.5)',
         'unit': 'minutes', 'basis': 'ACADEMIC', 'tier': 'B',
         'source_keys': ['shaw_2025'],
         'locator': 'Shaw et al., Prehosp Emerg Care 2025, 7,237,606 '
                    'records (2024) — Q2 offload evidence',
         'cross_check': 'CA AB 40 statutory standard (30 min at 90%) '
                        'cited on the same tab'},
        {'metric': 'ED boarding of admitted 65+ (mean minutes, '
                   '2018→2022)',
         'year': 2022, 'value': '138 → 343 min (85.2% boarded ≥2h)',
         'unit': 'minutes (endpoint growth)', 'basis': 'ACADEMIC',
         'tier': 'B', 'source_keys': ['lee_2026'],
         'locator': 'Lee et al., Ann Emerg Med 2026 (NHAMCS 2015-2022) — '
                    'Q2 boarding evidence; 501 min with dementia',
         'cross_check': 'ACEP/Morning Consult poll (44%/16%) on '
                        'InDepth_Q07 gives the public-experience read'},
    ],
    3: [
        {'metric': 'Post-acute destination supply (national node count)',
         'year': 2026,
         'value': '35,481 destinations (14,699 SNF + 1,221 IRF + 317 '
                  'LTACH + 12,392 HHA + 6,852 hospice)',
         'unit': 'facilities', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['cms_carecompare'],
         'locator': 'CMS Care Compare / Provider-of-Services files via '
                    'ift_clinical_demand.destination_supply() — Q3 '
                    'destination evidence',
         'cross_check': 'MedPAC payment-basics volumes (~1.8M SNF / 383k '
                        'IRF / 90k LTCH stays) on the same tab'},
        {'metric': 'Rural ED visit volume (2005 → 2016)',
         'year': 2016, 'value': '16.7M → 28.4M visits',
         'unit': 'visits/yr (2-pt series)', 'basis': 'ACADEMIC',
         'tier': 'B', 'source_keys': ['greenwood'],
         'locator': 'Greenwood-Ericksen & Kocher, JAMA Network Open '
                    '2019/2021 — Q3 rural demand evidence (~4.9%/yr '
                    'endpoint growth)',
         'cross_check': 'Rural transfer propensity 6.2% vs urban 2.0% '
                        '(same authors) on InDepth_Q01/Q07'},
        {'metric': 'STEMI transfer DIDO and mortality',
         'year': 2011,
         'value': 'median DIDO 68 min; 11% ≤30 min; mortality 5.9% vs '
                  '2.7% (adj. OR 1.56)',
         'unit': 'minutes / % (n=14,821)', 'basis': 'ACADEMIC',
         'tier': 'B', 'source_keys': ['wang_2011'],
         'locator': 'Wang et al., JAMA 2011 — Q3 delay-consequence '
                    'evidence',
         'cross_check': 'Stroke DIDO family (Ng 2017; JAMA Netw Open '
                        '2024; GWTG 2023) carried on InDepth_Q02'},
    ],
    4: [
        {'metric': 'RSNAT prior-authorization natural experiment (ESRD '
                   'cohort)',
         'year': 2022,
         'value': '−61% probability of RSNAT use · −77% RSNAT spend '
                  '($1,136/beneficiary-yr) · +19%/yr emergency dialysis',
         'unit': 'effect sizes', 'basis': 'ACADEMIC', 'tier': 'B',
         'source_keys': ['contreary'],
         'locator': 'Contreary et al., JAMA Health Forum 2022 '
                    '(doi:10.1001/jamahealthforum.2022.2093) — Q4 payment '
                    'flow evidence',
         'cross_check': 'RSNAT definitions (CMS rules) cited on '
                        'InDepth_Q02; OIG utilization findings adjacent'},
        {'metric': 'OIG: payments with no Medicare service at origin or '
                   'destination (H1-2012)',
         'year': 2015, 'value': '$30.2M in one half-year',
         'unit': 'USD (half-year)', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['oig_351'],
         'locator': 'HHS OIG OEI-09-12-00351 (2015) — Q4 incentive '
                    'evidence; companion findings (21% of suppliers; 4 '
                    'metros 18%/52%) on InDepth_Q07',
         'cross_check': 'CERT 2024 split (13.2% / $595.1M / 63.5% / '
                        '27.5%) carried on InDepth_Q02/Q07'},
        {'metric': 'Bed-day value vs Medicare transport price mismatch',
         'year': 2024,
         'value': '~$3,132 adjusted expense per inpatient day vs $469 '
                  'Medicare average per transport (= $5.3B / 11.3M)',
         'unit': 'USD', 'basis': 'DERIVED', 'tier': 'B',
         'source_keys': ['kff_shf', 'medpac_pb'],
         'locator': 'KFF State Health Facts 2023 expense proxy '
                    '(re-verify) ÷ MedPAC Oct 2024 universe — equation '
                    'stated in the Q4 claim text ("1 bed-day ≈ 6-7 '
                    'transports")',
         'cross_check': 'Both inputs carried as separate cited lines on '
                        'the same tab'},
    ],
    5: [
        {'metric': 'Hospital-owned ambulance org NPIs — NE vs IA '
                   'contrast',
         'year': 2026, 'value': 'NE 5 (of 400) vs IA 40+ (of 351)',
         'unit': 'org NPIs', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['nppes'],
         'locator': 'CMS NPPES NE+IA ambulance-org sweep, vendored '
                    '2026-07-10 (751 org NPIs) — Q5 prevalence evidence',
         'cross_check': 'Same registry powers Competitor_Registry and '
                        'the InDepth_Q08 MMT estate'},
        {'metric': 'CommonSpirit operating loss trajectory',
         'year': 2025, 'value': '−$875M (FY2024) → −$225M (FY2025)',
         'unit': 'USD operating loss', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['csh_results'],
         'locator': 'CommonSpirit FY2025 results release (re-verify) — '
                    'Q5 capital-appetite evidence',
         'cross_check': 'Context for why systems avoid insourcing '
                        'capital: 2-pt trend, never extrapolated'},
        {'metric': 'Insourced-heavy comparators (scale of the '
                   'alternative)',
         'year': 2024,
         'value': 'Mayo Clinic Ambulance ~70 units; Allina Health EMS '
                  '~34,000 interfacility requests (2024)',
         'unit': 'units / requests', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['footprint_web'],
         'locator': 'Operator public pages via footprint registry, '
                    'captured 2026-07-10 (re-verify) — Q5 insourcing '
                    'evidence',
         'cross_check': 'Contrast rows: NE systems own 5 ambulance NPIs '
                        'total (same tab)'},
    ],
    6: [
        {'metric': 'Hospital system-affiliation share (buyer '
                   'consolidation)',
         'year': 2024, 'value': '70% (3,567 of 5,121 non-federal general '
                                'acute hospitals)',
         'unit': '% of hospitals', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['aha_fastfacts'],
         'locator': 'AHA Fast Facts 2026 (FY2024 Annual Survey; '
                    're-verify) — Q6 procurement-ownership evidence',
         'cross_check': 'Underpins system-level contracting logic on '
                        'InDepth_Q09'},
        {'metric': 'Ambulance Inflation Factor (contract escalator '
                   'precedent)',
         'year': 2026, 'value': '+2.4% (CY2025) · +2.0% (CY2026)',
         'unit': '%/yr', 'basis': 'GOV', 'tier': 'B',
         'source_keys': ['cms_afs'],
         'locator': 'CMS Ambulance Fee Schedule PUF (re-verify against '
                    'PUF) — Q6 contract-structure evidence',
         'cross_check': '2-point escalator series; never trended '
                        'forward'},
        {'metric': 'Modivcare Chapter 11 (vendor-stability precedent)',
         'year': 2025,
         'value': 'Filed Aug 20, 2025; emerged Dec 29, 2025 cutting '
                  '>$1.1B of ~$1.4B funded debt',
         'unit': 'event', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['modivcare_ch11'],
         'locator': 'S.D. Tex. bankruptcy docket + coverage (re-verify) '
                    '— Q6 evaluation-criteria evidence',
         'cross_check': 'GMR refinancing/IPO row on InDepth_Q10 gives '
                        'the 911-side analogue'},
    ],
    7: [
        {'metric': 'Nebraska statewide transfer-center confirmation rate '
                   '(measured shortfall)',
         'year': 2021,
         'value': '146 of 234 confirmed (62%, Sep 2021) · 113 of 168 '
                  '(67%, Oct 2021)',
         'unit': '% of requested transfers', 'basis': 'SOURCED',
         'tier': 'B', 'source_keys': ['ne_press'],
         'locator': 'Omaha World-Herald / Journal Star, Nov 2021 '
                    '(re-verify; COVID-era context travels) — Q7 '
                    'acceptance evidence',
         'cross_check': 'The only public IFT acceptance gauge in the '
                        'corpus — 2-point episode, never trended'},
        {'metric': 'PACU discharge delays attributable to transport '
                   'unavailability',
         'year': 2022,
         'value': '11.1% of delays (2nd after bed unavailability 22.5%); '
                  '61.2% of delays non-clinical',
         'unit': '% of delays', 'basis': 'ACADEMIC', 'tier': 'B',
         'source_keys': ['ego_2022'],
         'locator': 'Ego et al., Ann Med Surg 2022, 307-patient non-US '
                    'cohort (magnitude only — caveat carried) — Q7 flow '
                    'evidence',
         'cross_check': 'Discharge-task 47% single-site study '
                        '(PMC11023539) on InDepth_Q02 corroborates '
                        'direction'},
        {'metric': 'Average length of stay deterioration (2019 → 2022)',
         'year': 2022, 'value': '+19% overall; +24% for post-acute '
                                'discharges',
         'unit': '% change (endpoint)', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['aha_alos'],
         'locator': 'AHA Issue Brief, Dec 2022 (re-verify) — Q7 '
                    'hospital-flow evidence',
         'cross_check': 'Boarding trend 138→343 min (Lee 2026, '
                        'InDepth_Q02) moves the same direction'},
    ],
    8: [
        {'metric': 'MMT verified NPI estate vs company claim',
         'year': 2026,
         'value': '23 active org NPIs across 11 NPI states vs a 13-state '
                  'company claim',
         'unit': 'org NPIs / states', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['nppes'],
         'locator': 'CMS NPPES org-NPI sweep, pulled 2026-07-10 — Q8 '
                    'geography evidence (VA link unconfirmed, flagged)',
         'cross_check': 'Full row-level estate on MMT_NPI_Estate; '
                        'conflict stated on both tabs'},
        {'metric': 'MMT claimed operating scale',
         'year': 2026,
         'value': '200,000+ missions/yr (Jan 2022 release) · 500+ '
                  'vehicles · 2,800+ team members (2026 site)',
         'unit': 'claims (floors)', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['mmt_press', 'mmt_web'],
         'locator': 'Businesswire Harbour Point release Jan 25, 2022 + '
                    'mmtamb.com About Us captured 2026-07-10 — Q8 scope '
                    'evidence (self-report, never a measurement)',
         'cross_check': 'Advisor framed the 2022 deal as 7 states / '
                        '~1,000 employees — conflict carried, not '
                        'blended'},
        {'metric': 'MMT claimed headcount trajectory (self-reported '
                   'floors)',
         'year': 2026,
         'value': '350+ (2015, 1 state) → ~1,000 (2022, 7 states) → '
                  '2,800+ (2026, 13-state claim)',
         'unit': 'people (claimed floors)', 'basis': 'SOURCED',
         'tier': 'B', 'source_keys': ['mmt_press', 'mmt_web'],
         'locator': 'LJS Feb 2015 sale coverage; Lincoln International '
                    'notice 2022; mmtamb.com 2026 — Q8 workforce '
                    'evidence; definitions drift (employees → team '
                    'members), never trended forward',
         'cross_check': 'Same 3-point series charted on Company_Dossier '
                        'with the identical caveats'},
    ],
    9: [
        {'metric': 'GADCS mean cost per transport by ownership',
         'year': 2025,
         'value': '$2,673 all · $3,127 governmental · $1,778 private '
                  'for-profit',
         'unit': 'USD/transport', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['gadcs'],
         'locator': 'CMS/RAND GADCS Year 1-2 report via trade coverage '
                    '(re-verify) — Q9 alternative-economics evidence',
         'cross_check': 'MedPAC Dec 2025 volume-cost curve (same tab) '
                        'explains the governmental/private gap via '
                        'utilization'},
        {'metric': 'Unit-hour utilization benchmark (911 vs high-'
                   'performance)',
         'year': 2024, 'value': '911 band 0.30-0.50; AIMHI survey mean '
                                '0.508',
         'unit': 'UHU ratio', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['aimhi'],
         'locator': 'AIMHI benchmarking via EMS1 (as captured '
                    '2026-07-10) — Q9 shared-fleet evidence',
         'cross_check': 'The capacity-productivity argument against '
                        'shared 911 fleets for scheduled IFT'},
        {'metric': 'Omaha Fire Department 911 transport monopoly (city '
                   'ALS fleet)',
         'year': 2026, 'value': '18 ALS ambulances as primary city '
                                'transport',
         'unit': 'ambulances', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['footprint_web'],
         'locator': 'City EMS pages via the NPPES landscape sweep, '
                    '2026-07-10 (re-verify; public-web claim) — Q9 '
                    'traditional-EMS evidence',
         'cross_check': 'Municipal 911 posture rows corroborated by the '
                        'muni-contract precedent family'},
    ],
    10: [
        {'metric': 'Footprint demand band (measured national acute legs '
                   'allocated to the MMT footprint)',
         'year': 2026,
         'value': '3.47M measured national acute legs/yr (1.97M NEDS + '
                  '1.5M NIS) allocated by population vs 65+ share',
         'unit': 'legs/yr (national base)', 'basis': 'DERIVED',
         'tier': 'B', 'source_keys': ['repo_derived', 'hcup_transfers'],
         'locator': 'ift_mmt footprint demand band — ACADEMIC transfer '
                    'counts ÷ GOV Census shares, equation stated in the '
                    'Q10 claim text',
         'cross_check': 'Inputs cited separately on InDepth_Q01 '
                        '(NEDS/NIS) and Q8 (Census legacy core)'},
        {'metric': 'GMR capital-structure constraint (competitor '
                   'context)',
         'year': 2026,
         'value': 'IPO valuation target cut to $3.3B (May 2026) after '
                  'the $5.4B 2025 refinancing',
         'unit': 'USD', 'basis': 'SOURCED', 'tier': 'B',
         'source_keys': ['deal_press'],
         'locator': 'Deal/IPO coverage via the NPPES landscape sweep '
                    '(re-verify) — Q10 durability evidence',
         'cross_check': 'Modivcare Ch.11 (InDepth_Q06) gives the '
                        'NEMT-side analogue of vendor fragility'},
    ],
}


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, notes = [], [], [], []
    row_counts = {}

    try:
        from rcm_mc.market_reports import ift_indepth as idp
        qmap = {q.num: q for q in idp.questions()}
        cov = idp.coverage()
    except Exception as exc:  # degrade, never invent
        qmap, cov = {}, {}
        notes.append(f'ift_indepth import failed: {exc!r} — tabs emitted '
                     'as placeholders, no content invented')

    fam_powers = {}
    fam_url = {}
    unmatched = set()

    for n in range(1, 11):
        name = f'InDepth_Q{n:02d}'
        ws = wb.create_sheet(name)
        q = qmap.get(n)
        sb = lib.SheetBuilder(ws, 8, col_widths=[20, 54, 54, 13, 9, 30,
                                                 11, 36],
                              tab_color=PURPLE)
        if q is None:
            sb.title(f'In-Depth Q{n} — (module unavailable at build time)')
            sb.note('rcm_mc.market_reports.ift_indepth could not supply '
                    'this question when the workbook was built — the tab '
                    'is left empty rather than invented.')
            notes.append(f'{name}: question {n} missing at build')
            row_counts[name] = ws.max_row
            continue

        # ── split evidence: carried vs FRAMEWORK-numeric (excluded) ────────
        ev_rows, excl_rows = [], []
        for b in q.blocks:
            for e in b.evidence:
                if e.basis == 'FRAMEWORK' and re.search(r'\d', e.text):
                    excl_rows.append((b, e))
                else:
                    ev_rows.append((b, e))
        n_sub = sum(len(b.subqs) for b in q.blocks)
        n_ans = sum(1 for b in q.blocks for s in b.subqs if s.a)
        n_skip = sum(1 for b in q.blocks for s in b.subqs
                     if not s.a and s.skip)
        n_rv = sum(1 for _, e in ev_rows
                   if 're-verify' in (e.text + ' ' + e.source).lower())

        sb.title(f'In-Depth Q{q.num} — {q.title}')
        sb.subtitle(
            f'The question: {q.title} The module answers it across '
            f'{len(q.blocks)} conclusion-led blocks with {len(ev_rows)} '
            f'cited evidence lines carried here, {n_ans} of {n_sub} '
            f'subquestions answered and {n_skip} explicitly skipped as '
            f'diligence requests. One-line conclusion (verbatim): '
            f'"{q.storyline}" — Panel A carries every cited fact-line '
            'with its basis chip exactly as the module labels it (blue = '
            'literal carried from the named publisher source; FRAMEWORK '
            'rows are text-only analytic scaffolds rendered black, and '
            'every FRAMEWORK line carrying a NUMBER is excluded and '
            'quarantined on Excluded_Not_Sourced). Panel B is the '
            'subquestion Q&A registry — answers are the module\'s '
            'one-line syntheses of Panel A citations, black text, never '
            'blue. Panel C is the honesty register: subquestions the '
            'module refuses to answer from desk research. Panel D audits '
            'coverage with live formulas.', height=86)
        sb.blank()

        # ── Panel A — answered evidence ─────────────────────────────────────
        sb.banner(f'Panel A. Answered evidence — {len(ev_rows)} cited '
                  f'fact-lines carried ({len(excl_rows)} FRAMEWORK-numeric '
                  'lines excluded; see foot + Excluded_Not_Sourced)')
        sb.headers(['Block', 'Cited claim — the fact-line, verbatim from '
                    'the module (value embedded in text)', '', 'Basis',
                    'Re-verify', 'Source (as cited by the module)',
                    'Family', 'URL'])
        a0 = sb.r + 1
        for b, e in ev_rows:
            fam = _family(e.source)
            if fam:
                fam_powers.setdefault(fam, set()).add(name)
                if e.url and fam not in fam_url:
                    fam_url[fam] = e.url
            else:
                unmatched.add(e.source)
            rv = ('re-verify' if 're-verify' in
                  (e.text + ' ' + e.source).lower() else '')
            disp_basis = _display_basis(e)
            kind = 'text' if disp_basis == 'FRAMEWORK' else 'src'
            sb.row([
                (b.title, 'text'), (e.text, kind), None,
                (disp_basis, 'text'), (rv, 'note'), (e.source, 'note'),
                (fam or '—', 'note'), (e.url, 'note'),
            ], wrap=True, height=_ht((b.title, 20), (e.text, 54),
                                     (e.source, 30), (e.url, 36)))
        a1 = sb.r

        # ── Panel B — subquestion Q&A registry ─────────────────────────────
        sb.blank()
        sb.banner(f'Panel B. Subquestion Q&A registry — {n_ans} answered '
                  f'of {n_sub} (the {n_skip} skips sit in Panel C)')
        sb.headers(['Block', 'Subquestion', 'Answer (one line, verbatim '
                    'from the module)', 'Basis', '', 'Source', '', ''])
        b0 = sb.r + 1
        for b in q.blocks:
            for s in b.subqs:
                if not s.a:
                    continue
                sb.row([
                    (b.title, 'text'), (s.q, 'text'), (s.a, 'text'),
                    ('SYNTH', 'note'), None,
                    ('block citations — Panel A', 'note'), None, None,
                ], wrap=True, height=_ht((b.title, 20), (s.q, 54),
                                         (s.a, 54)))
        b1 = sb.r
        sb.note("Basis 'SYNTH': each answer is the module's one-line "
                "synthesis of the block's cited evidence (Panel A) — "
                'carried verbatim, black text (never blue): it is an '
                'authored reading, not an independent measurement. Any '
                'number inside an answer resolves to a Panel A citation.',
                height=26)

        # ── Panel C — honesty register (skips) ──────────────────────────────
        sb.blank()
        sb.banner(f'Panel C. Honesty register — {n_skip} subquestions '
                  'explicitly SKIPPED (diligence requests; the module '
                  'never invents)')
        c0 = c1 = None
        if n_skip:
            sb.headers(['Block', 'Subquestion (unanswered by design)',
                        'Skip reason — the data that would answer it',
                        'Basis', '', '', '', ''])
            c0 = sb.r + 1
            for b in q.blocks:
                for s in b.subqs:
                    if s.a or not s.skip:
                        continue
                    sb.row([
                        (b.title, 'text'), (s.q, 'text'), (s.skip, 'text'),
                        ('SKIP', 'note'), None, None, None, None,
                    ], wrap=True, height=_ht((b.title, 20), (s.q, 54),
                                             (s.skip, 54)))
            c1 = sb.r
        else:
            sb.note(f'None — all {n_sub} subquestions for this question '
                    'are answered (Panel B).')

        # ── Panel D — coverage & basis audit (live formulas) ────────────────
        sb.blank()
        sb.banner('Panel D. Coverage & basis audit — live formulas over '
                  'this tab')
        sb.headers(['Measure', 'Count', '', '', '', '', '', 'Note'])
        d0 = sb.r + 1
        chip_notes = {
            'GOV': 'CMS / MedPAC / CFR / state statute rows',
            'SOURCED': 'named non-government datasets/publishers (e.g. GADCS)',
            'ACADEMIC': 'peer-reviewed, mostly DOI-cited',
            'PUBLIC-WEB': 'company/press/analyst material — named and dated, '
                          'labeled not-a-dataset, re-verify flagged',
            'DERIVED': 'transparent arithmetic, equation stated in the '
                       'claim text',
            'FRAMEWORK': 'text-only scaffolds / documented not-founds — '
                         'no numbers carried',
        }
        for chip in ('GOV', 'SOURCED', 'ACADEMIC', 'PUBLIC-WEB', 'DERIVED',
                     'FRAMEWORK'):
            sb.row([
                (f'{chip} evidence lines', 'label'),
                (f'=COUNTIF($D${a0}:$D${a1},"{chip}")', 'fml', lib.FMT_INT),
                None, None, None, None, None, (chip_notes[chip], 'note'),
            ])
        d_basis_end = sb.r
        sb.row([('Evidence lines carried (total)', 'label'),
                (f'=COUNTA($D${a0}:$D${a1})', 'fml', lib.FMT_INT),
                None, None, None, None, None,
                (f'{len(excl_rows)} FRAMEWORK-numeric lines excluded '
                 'from this count by construction', 'note')])
        r_tot = sb.r
        sb.row([('Re-verify-flagged lines (excerpt-grade)', 'label'),
                (f'=COUNTIF($E${a0}:$E${a1},"re-verify")', 'fml',
                 lib.FMT_INT),
                None, None, None, None, None,
                ('reopen the primary documents before circulation',
                 'note')])
        r_rv = sb.r
        sb.row([('Subquestions answered (Panel B)', 'label'),
                (f'=COUNTA($B${b0}:$B${b1})', 'fml', lib.FMT_INT),
                None, None, None, None, None,
                (f'of {n_sub} total subquestions', 'note')])
        r_ans = sb.r
        if c0:
            sb.row([('Subquestions skipped (Panel C)', 'label'),
                    (f'=COUNTA($B${c0}:$B${c1})', 'fml', lib.FMT_INT),
                    None, None, None, None, None,
                    ('diligence requests — honesty over invention',
                     'note')])
        else:
            sb.row([('Subquestions skipped (Panel C)', 'label'),
                    ('(none)', 'note'), None, None, None, None, None,
                    ('all subquestions answered', 'note')])
        r_skip = sb.r

        # ── foot notes ──────────────────────────────────────────────────────
        sb.blank()
        if excl_rows:
            sb.note('Excluded from this tab (FRAMEWORK chip + embedded '
                    'numbers — quarantined on Excluded_Not_Sourced): ' +
                    ' | '.join(f'[{b.key}] "{e.text[:80]}..."'
                               for b, e in excl_rows),
                    height=14 + 12 * len(excl_rows))
        sb.note('Color/chip law on this tab: BLUE = literal carried from '
                'the named publisher source on the same row (GOV / '
                'SOURCED / ACADEMIC / DERIVED chips, exactly as the '
                'module labels them); BLACK = formula (Panel D) or '
                'non-sourced text (FRAMEWORK scaffolds, Panel B '
                'syntheses, Panel C skip reasons). DERIVED claim lines '
                'state their equation inside the claim text; their '
                'inputs are cited GOV/ACADEMIC lines. CMS-derived counts '
                'quoted inside claims inherit any small-cell suppression '
                'of their source files (floors, not exact).', height=38)
        sb.note(f'Re-verify: {n_rv} of {len(ev_rows)} carried lines are '
                'excerpt-grade captures per the dossier legend (GADCS '
                'via trade coverage, CERT, NE DHHS, KFF, AHA, municipal '
                'contracts, footprint registry) — the flag travels in '
                'the Re-verify column and the primary documents must be '
                'reopened before external circulation. Citations: the '
                'per-row Source + URL columns cite the original '
                'publisher; the Family column keys each row to its '
                'deduplicated Source_Register entry. Extraction: '
                'rcm_mc/market_reports/ift_indepth_q*.py::QUESTIONS via '
                f'ift_indepth.questions(), accessed {accessed}.',
                height=48)

        # ── chart: basis mix (live ranges on this tab) ──────────────────────
        lib.add_chart(
            ws, f'J{d0}',
            f'Q{q.num} evidence basis mix ({len(ev_rows)} carried lines)',
            f'{name}!$A${d0}:$A${d_basis_end}',
            [('Evidence lines', f'{name}!$B${d0}:$B${d_basis_end}')],
            kind='bar', width=18, height=9, y_fmt='#,##0')

        # ── returns: facts / excluded ───────────────────────────────────────
        for f in _FACTS.get(n, []):
            f = dict(f)
            f['lives_on'] = name
            facts.append(f)
        for b, e in excl_rows:
            fig, val, why, citable = _EXCL_META.get(b.key, (
                e.text[:90], '(numeric embedded in text)',
                'FRAMEWORK-labeled line carrying numbers — excluded by '
                'the zero-ILLUSTRATIVE rule',
                'a named publisher document or dataset producing the '
                'figure'))
            excluded.append({
                'figure': f'Q{q.num} [{b.key}] {fig}', 'value': val,
                'source_label': e.source, 'why_excluded': why,
                'what_would_make_citable': citable})

        row_counts[name] = ws.max_row

    # ── deduplicated source register (families actually cited on tabs) ─────
    for key, _pat, publisher, document, vintage, locator, supplies, url \
            in _FAM:
        tabs = sorted(fam_powers.get(key, ()))
        if not tabs:
            continue
        sources.append({
            'key': key, 'publisher': publisher, 'document': document,
            'vintage': vintage, 'locator': locator, 'supplies': supplies,
            'url': url or fam_url.get(key, ''), 'tier': 'B',
            'accessed': accessed, 'powers': tabs})

    if unmatched:
        notes.append('UNMATCHED source strings (no family — cited on-row '
                     'only): ' + ' | '.join(sorted(unmatched)))
    if cov:
        notes.append(f"ift_indepth.coverage(): {cov}")
    notes.append('FRAMEWORK-numeric exclusion rule: basis==FRAMEWORK and '
                 'any digit in the claim text — 6 lines expected '
                 '(85%+ share-of-wallet x2, repatriation ~1:1, four-band '
                 'cut-points, 20-metro band counts, vendor 2-3 hrs/shift).')

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'meta': {'notes': ' || '.join(notes) or 'ok',
                     'row_counts': row_counts}}
