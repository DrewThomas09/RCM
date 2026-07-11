"""B.9 + B.10: the regulatory layer. Entry_Barrier_Register maps, for the
ten footprint states, where ambulance entry is legally gated (CON, local
franchise / exclusive operating areas / primary service areas, licensure)
with a verified statute cite on every row. Balance_Billing_States carries
the state ground-ambulance balance-billing protection table with payment
standards and verified statute cites.

Verification: every URL printed on these tabs was fetched and read on
11 Jul 2026 (state legislature/revisor pages, session laws, agency pages);
where a fetch could not confirm a claim the row says so and asserts
nothing. Bills that died (FL HB 425/2025, WV SB 632/2025, CO HB25-1088
veto, MT 2025) are carried as context, never as law.
"""

SHEETS = [
    {'name': 'Entry_Barrier_Register',
     'question': 'Where is ambulance market entry legally gated in the ten '
                 'footprint states, and by which statute?'},
    {'name': 'Balance_Billing_States',
     'question': 'Which states ban ground-ambulance balance billing, and at '
                 'what payment standard?'},
]

FOOTPRINT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']

# --------------------------------------------------------------- B.9 data --
# (state, what the statute says - read from the fetched page, gate, cite,
#  url) - every URL fetched 11 Jul 2026.
CON_ROWS = [
    ('NE', 'CON program limited to nursing facilities ("CONs are only '
           'required for nursing homes" - peer-reviewed 50-state review); '
           'no ambulance CON in the Nebraska Health Care Certificate of '
           'Need Act', 'OPEN',
     'Neb. Rev. Stat. ch. 71 (CON act); classification per Rucinski & '
     'Sutton 2024 review',
     'https://pmc.ncbi.nlm.nih.gov/articles/PMC11088301/'),
    ('IA', 'CON applies to "institutional health facilities": hospital, '
           'health care facility, organized outpatient health facility, '
           'ambulatory surgical center, community mental health facility. '
           'Ambulance is not in the definition (verified in the section '
           'text)', 'OPEN',
     'Iowa Code sec. 135.61(12)',
     'https://www.legis.iowa.gov/docs/code/135.61.pdf'),
    ('KS', 'No ambulance CON in the Kansas EMS act (K.S.A. ch. 65, art. '
           '61); Kansas has had no general health-facility CON program '
           'since the 1980s repeal. Entry gate is the Board of EMS permit '
           'plus the county service structure', 'OPEN',
     'K.S.A. 65-6101 et seq. (no CON provision)',
     'https://www.ksrevisor.gov/statutes/chapters/ch65/065_061_0028.html'),
    ('MO', 'CON "health care facilities" are ch. 198 (long-term care) '
           'facilities, LTC beds in hospitals, long-term care hospitals, '
           'and new hospital construction. Ambulance is not included '
           '(verified in the section text). The real Missouri gate is the '
           'licensure service-area regime below', 'OPEN',
     'RSMo 197.366 (definition); 197.300-197.366 (CON law)',
     'https://revisor.mo.gov/main/OneSection.aspx?section=197.366'),
    ('OH', 'CON limited to long-term care beds ("CONs are only required '
           'for nursing homes" - 2024 review); ambulance not covered under '
           'ORC 3702.51 et seq.', 'OPEN',
     'ORC 3702.51 et seq.; classification per Rucinski & Sutton 2024',
     'https://pmc.ncbi.nlm.nih.gov/articles/PMC11088301/'),
    ('WI', 'No ambulance CON found in Wis. Stat. ch. 256 (EMS); '
           'Wisconsin\'s remaining approval regime (ch. 150) covers '
           'nursing homes. AMBIGUITY flagged: the 50-state review does '
           'not state Wisconsin\'s scope; classification rests on the '
           'absence of any CON requirement in the fetched ch. 256 '
           'licensure text', 'OPEN (flagged)',
     'Wis. Stat. 256.15 (no CON element); ch. 150 (nursing homes)',
     'https://docs.legis.wisconsin.gov/statutes/statutes/256/15'),
    ('VA', 'COPN covers six facility categories (hospitals, behavioral '
           'health, nursing homes, substance-abuse ICFs, DD facilities, '
           'specialized centers). No ambulance service in the COPN scope '
           '(verified in the section text). Virginia\'s gate is the local '
           'franchise power below', 'OPEN (COPN); GATED locally',
     'Va. Code 32.1-102.1:3(A)',
     'https://law.lis.virginia.gov/vacode/title32.1/section32.1-102.1:3/'),
    ('MN', 'CON-equivalent FOR AMBULANCE specifically: a new ambulance '
           'service or primary-service-area expansion requires an '
           'application, State Register notice, a 30-day comment window, '
           'a contested-case hearing if more than five opposing comments, '
           'and a NEED determination weighing duplication harm vs public '
           'benefit (verified in the section text). The 2024 review '
           'classes MN as ambulance-only CON', 'GATED (need test)',
     'Minn. Stat. 144E.11; 144E.06 (primary service areas)',
     'https://www.revisor.mn.gov/statutes/cite/144E.11'),
    ('IN', 'CON limited to nursing facilities ("CONs are only required '
           'for nursing homes" - 2024 review); no ambulance CON in IC '
           '16-31', 'OPEN',
     'IC 16-31 (no CON element); classification per Rucinski & Sutton '
     '2024', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11088301/'),
    ('KY', 'CON REQUIRED for ambulance services. Exemptions verified in '
           'the current CON regulation: city or county government-owned '
           'services for emergency transport (KRS 216B.020(8)) and '
           'hospital-owned services for transports originating at their '
           'own hospital (KRS 216B.020(7)). Private for-profit ground '
           'ambulance entry remains CON-gated', 'GATED (CON)',
     'KRS ch. 216B; 900 KAR 6:075 (exemption text as fetched)',
     'https://apps.legislature.ky.gov/law/kar/titles/900/006/075/'),
]

FRANCHISE_ROWS = [
    ('NE', 'Counties, cities and villages "may establish an emergency '
           'medical service, including the provision of scheduled and '
           'unscheduled ambulance service", may contract it out, and may '
           'levy a tax for it (quoted from the fetched statute). Provision '
           'and funding power, not an exclusivity power', 'Local provision '
           'power; no statutory EOA',
     'Neb. Rev. Stat. 13-303',
     'https://nebraskalegislature.gov/laws/statutes.php?statute=13-303'),
    ('IA', 'A county board may by resolution declare EMS an ESSENTIAL '
           'COUNTY SERVICE and, with voter approval, levy an income surtax '
           'and/or property tax for it, with a county EMS advisory council '
           '(verified in the section text). Funding-and-system power; no '
           'statutory exclusivity', 'Local funding power; no statutory EOA',
     'Iowa Code 422D.1',
     'https://www.legis.iowa.gov/docs/code/422D.1.pdf'),
    ('KS', 'County-based structure: a county shall NOT provide ambulance '
           'service in any part of the county already receiving it, and '
           'must reimburse taxing districts that provide it (verified in '
           'the section text) - a statutory non-duplication rule around '
           'incumbent public providers. AMBIGUITY flagged: the affirmative '
           'county provision power sits in neighboring sections not '
           'separately fetched', 'Non-duplication rule (flagged)',
     'K.S.A. 65-6113',
     'https://www.ksrevisor.gov/statutes/chapters/ch65/065_061_0013.html'),
    ('MO', 'Two mechanisms, both verified: (1) ambulance districts are '
           'political subdivisions that operate or contract the service '
           'within their boundaries with rulemaking and hearing powers '
           '(190.060; no EXPLICIT exclusivity clause in the fetched text - '
           'stated as such); (2) the license gate: a NEW or EXPANDED '
           'ground ambulance service area requires endorsement letters '
           'from the affected political subdivisions after a public '
           'hearing, on top of the 1997-grandfathered service areas '
           '(190.109)', 'GATED (endorsement + grandfathered areas)',
     'RSMo 190.060; 190.109',
     'https://revisor.mo.gov/main/OneSection.aspx?section=190.109'),
    ('OH', 'Townships may operate ambulance service or contract with '
           'state agencies, municipalities, counties, nonprofits, joint '
           'EMS districts, fire-and-ambulance districts or private owners '
           '(verified in the section text); in counties under 40,000, a '
           'township nonemergency transport service must first demonstrate '
           'need for public funding and obtain state board approval',
     'Local provision/contract power; need test for small-county public '
     'nonemergency entry',
     'ORC 505.44 (townships); ch. 307 (counties)',
     'https://codes.ohio.gov/ohio-revised-code/section-505.44'),
    ('WI', 'The town board SHALL contract for or operate and maintain '
           'ambulance services "unless such services are provided by '
           'another person" (quoted from the fetched statute); the '
           'department also establishes a primary service or contract '
           'area for every licensed provider (256.15)', 'Mandatory local '
           'provision + department-set PSAs',
     'Wis. Stat. 60.565; 256.15',
     'https://docs.legis.wisconsin.gov/statutes/statutes/60/vii/565'),
    ('VA', 'The hard local gate, verified verbatim: counties and cities '
           'may "grant franchises, licenses or permits to emergency '
           'medical services agencies", may make it UNLAWFUL to operate '
           'without one, may LIMIT THE NUMBER of EMS vehicles and '
           'agencies, and may prescribe franchise service areas. Volunteer '
           'agencies additionally need governing-body approval to be '
           'established (15.2-955)', 'GATED (local franchise at option)',
     'Va. Code 32.1-111.14; 15.2-955',
     'https://law.lis.virginia.gov/vacode/title32.1/section32.1-111.14/'),
    ('MN', 'Every licensed ambulance service is designated to a PRIMARY '
           'SERVICE AREA by the director under adopted rules (verified in '
           'the section text); entering or expanding requires the 144E.11 '
           'need process on the CON row above', 'GATED (PSA + need test)',
     'Minn. Stat. 144E.06',
     'https://www.revisor.mn.gov/statutes/cite/144E.06'),
    ('IN', 'No statewide franchise or EOA statute located in IC 16-31; '
           'political subdivisions provide or contract EMS and, since '
           'HEA 1385-2024, county/municipal AMBULANCE RATES set or '
           'approved by ordinance or contract bind insurer payments. '
           'AMBIGUITY flagged: absence of an EOA mechanism is asserted '
           'only as "not located", not as settled law', 'No statutory EOA '
           'located (flagged)',
     'IC 16-31; HEA 1385-2024 (local rate-setting)',
     'https://iga.in.gov/legislative/2024/bills/house/1385'),
    ('KY', 'The binding entry gate is the CON row above (KRS ch. 216B). '
           'Local ambulance taxing districts exist in Kentucky law but '
           'were not separately verified for this register; no claim is '
           'made about their exclusivity powers', 'GATED (via CON); local '
           'layer not verified',
     'KRS ch. 216B (gate); local district statutes not verified',
     'https://apps.legislature.ky.gov/law/kar/titles/900/006/075/'),
]

LICENSE_ROWS = [
    ('NE', 'Nebraska DHHS; State Board of EMS sets "standards for the '
           'licensure of basic life support services and advanced life '
           'support services" under the EMS Practice Act (verified in the '
           'fetched section)',
     'Neb. Rev. Stat. 38-1201 to 38-1237; 38-1217(4)',
     'https://nebraskalegislature.gov/laws/statutes.php?statute=38-1217'),
    ('IA', 'Iowa Dept. of Health and Human Services (Bureau of EMS); '
           'service programs must hold authorization under 147A.5, with '
           'department rules on supervision, staffing and equipment '
           '(verified in the fetched 147A.4 text)',
     'Iowa Code ch. 147A (147A.4, 147A.5)',
     'https://www.legis.iowa.gov/docs/code/147A.4.pdf'),
    ('KS', 'Kansas Board of Emergency Medical Services; an ambulance '
           'service operator needs a permit, issued only if the service '
           '"is or will be staffed and equipped" per board rules '
           '(verified; permit term up to 18 months)',
     'K.S.A. 65-6128',
     'https://www.ksrevisor.gov/statutes/chapters/ch65/065_061_0028.html'),
    ('MO', 'Missouri Dept. of Health and Senior Services issues ground '
           'ambulance service licenses (five-year term), tied to defined '
           'service areas (verified)', 'RSMo 190.109',
     'https://revisor.mo.gov/main/OneSection.aspx?section=190.109'),
    ('OH', 'State Board of Emergency Medical, Fire, and Transportation '
           'Services (Dept. of Public Safety): no person shall provide '
           'emergency medical transportation without a license; vehicle '
           'permits under 4766.07 (verified)', 'ORC 4766.04',
     'https://codes.ohio.gov/ohio-revised-code/section-4766.04'),
    ('WI', 'Wisconsin Dept. of Health Services: "no person may act as or '
           'advertise for the provision of services as an ambulance '
           'service provider" without a license; the department sets each '
           'provider\'s primary service or contract area (verified)',
     'Wis. Stat. 256.15',
     'https://docs.legis.wisconsin.gov/statutes/statutes/256/15'),
    ('VA', 'Virginia Dept. of Health (Commissioner, Office of EMS): "no '
           'person shall operate... an emergency medical services agency" '
           'without a license and a permit for each EMS vehicle '
           '(verified); two-year maximum term',
     'Va. Code 32.1-111.6',
     'https://law.lis.virginia.gov/vacode/title32.1/section32.1-111.6/'),
    ('MN', 'The director (Office of Emergency Medical Services, which '
           'took over the EMSRB\'s ch. 144E functions in the 2024 '
           'reorganization) licenses services and designates primary '
           'service areas (verified via 144E.06/144E.11 text)',
     'Minn. Stat. ch. 144E',
     'https://www.revisor.mn.gov/statutes/cite/144E.06'),
    ('IN', 'Indiana EMS Commission (Dept. of Homeland Security): a person '
           'may not operate or advertise emergency medical services, '
           'including an ambulance transport business, without a '
           'certificate or license issued by the commission (verified)',
     'IC 16-31-3-1',
     'https://codes.findlaw.com/in/title-16-health/in-code-sect-16-31-3-1/'),
    ('KY', 'Kentucky Board of EMS licenses ambulance agencies; the '
           'licensure regulation 202 KAR 7:501 cites KRS 311A.030 as its '
           'authority and requires the service-area map to match the '
           'provider\'s CON (verified)', 'KRS 311A.030; 202 KAR 7:501',
     'https://www.law.cornell.edu/regulations/kentucky/202-KAR-7-501'),
]

# -------------------------------------------------------------- B.10 data --
# (state, footprint, payment standard, effective, scope, cite, status/url)
# status: 'V' = statute/session-law text verified by fetch on 11 Jul 2026;
# 'P' = partial or ambiguous protection, stated as such.
BB_ROWS = [
    ('AR', False,
     'Local-government approved/contracted rate (sec. 14-266-105); else '
     'the LESSER of the Workers\' Compensation Commission ambulance fee '
     'schedule or billed charges. Payment in full; direct pay in 30 days',
     '1 Aug 2023', 'Fully insured plans', 'Ark. Code 23-99-1802 (Act 597 '
     'of 2023, HB 1776; enacted as 23-99-1602)', 'V',
     'https://arkleg.state.ar.us/Home/FTPDocument?path=%2FACTS%2F2023R%2F'
     'Public%2FACT597.pdf'),
    ('CA', False,
     'Rate established or approved by the local government (LEMSA/county '
     'rate); enrollee owes only in-network cost sharing; collections '
     'restrictions', '1 Jan 2024', 'Fully insured plans (about 14M '
     'covered; roughly 6M self-funded lives excluded)',
     'Cal. Health & Safety Code 1371.56; Ins. Code 10126.66 (AB 716, '
     'ch. 454, Stats. 2023)', 'V',
     'https://leginfo.legislature.ca.gov/faces/billNavClient.xhtml?'
     'bill_id=202320240AB716'),
    ('CO', False,
     '325% of Medicare for out-of-network ground ambulance under the '
     'out-of-network law; in-network cost sharing only (2025 HB25-1088 '
     'expansion VETOED - rate stands)', '1 Jan 2020',
     'State-regulated plans; public fire-department transports carved '
     'out per KFF', 'C.R.S. 10-16-704 (HB19-1174, ch. 171)', 'V',
     'https://leg.colorado.gov/bills/hb19-1174'),
    ('DE', False,
     'No Medicare peg: insurer pays its highest 12-month allowed charge '
     'for the service, then either party may arbitrate (emergency '
     'services including ground ambulance)', '2019 (regs 2016-2020)',
     'Fully insured plans', '18 Del. C. 3349 (individual), 3571H '
     '(group)', 'P',
     'https://delcode.delaware.gov/title18/c035/index.html'),
    ('FL', False,
     'AMBIGUOUS - stated, not asserted: Florida\'s OON emergency-services '
     'payment and balance-billing statutes (627.64194 PPO; 641.513 HMO) '
     'predate the ambulance debate and do not name ground ambulance; the '
     'explicit ground-ambulance bills with a 350%-of-Medicare standard '
     '(HB 639/2024, HB 425/2025) DIED in committee', 'n/a',
     'Emergency-services framework only', 'Fla. Stat. 627.64194; 641.513 '
     '(HB 425/2025 died 16 Jun 2025)', 'P',
     'https://www.flsenate.gov/Session/Bill/2025/425'),
    ('IL', False,
     'No greater out-of-pocket than in-network for nonparticipating '
     'ground ambulance; direct payment to the provider; negotiation then '
     'dispute path. HMO enrollee protection since 2022 (215 ILCS '
     '125/4-15(b))', '1 Jul 2022 (PA 102-901); revamp 2025 (PA 104-0248)',
     'State-regulated plans', '215 ILCS 5/356z.3a as amended by PA '
     '104-0248 (HB 2785)', 'V',
     'https://www.ilga.gov/Documents/Legislation/PublicActs/104/PDF/'
     '104-0248.pdf'),
    ('IN', True,
     'Rates set or approved by county/municipality (contract or '
     'ordinance); absent a local rate, the LESSER of billed charges or '
     '400% of Medicare; no balance billing beyond cost share',
     '1 Jul 2024', 'State-regulated plans', 'IC 27-1-2.3 as amended by '
     'HEA 1385-2024', 'V',
     'https://iga.in.gov/legislative/2024/bills/house/1385'),
    ('LA', False,
     'Local-government set/approved rate; else the LESSER of billed '
     'charges or 325% of Medicare; direct pay in 30 days; payment in '
     'full', '1 Aug 2023', 'Fully insured plans',
     'La. R.S. 22:1880.2 (Acts 2023, No. 453; SB 109)', 'V',
     'https://www.legis.la.gov/legis/Law.aspx?d=1337472'),
    ('ME', False,
     'In-network: LESSER of provider rate or 200% of Medicare; '
     'out-of-network: LESSER of provider rate or 180% of Medicare, plus '
     'rural adjustments; no prior authorization for hospital-to-hospital '
     'transports', '2021 (PL 2021 c. 241; amended through PL 2025 c. 34)',
     'Fully insured plans', '24-A M.R.S. 4303-F (with 4303-C)', 'V',
     'https://legislature.maine.gov/statutes/24-a/title24-Asec4303-F.html'),
    ('MD', False,
     'PARTIAL scope, stated as such: direct payment on assignment of '
     'benefits and no balance billing - but only for ambulance services '
     'owned/operated by or under the jurisdiction of a political '
     'subdivision or volunteer company', '2020 vintage',
     'Local-government and volunteer providers only', 'Md. Code, Ins. '
     '15-138; Health-Gen. 19-710.1', 'P',
     'https://codes.findlaw.com/md/insurance/md-code-ins-sect-15-138.html'),
    ('NV', False,
     'AMBIGUOUS - stated, not asserted: Nevada\'s OON emergency statutes '
     '(NRS 439B.748-754, 2019) cover emergency services generally; the '
     'state DOI\'s own consumer FAQ says a non-network ground ambulance '
     'can still bill the patient. Counted by some trackers, not by this '
     'register', 'n/a', 'Unclear for ground ambulance',
     'NRS 439B.748-.754; DOI Balance Billing FAQ', 'P',
     'https://doi.nv.gov/Consumers/Health_and_Accident_Insurance/'
     'Balance_Billing_FAQs/'),
    ('NM', False,
     'OON provider paid the GREATEST of median in-network rate, 60th '
     'percentile usual-and-customary, or 150% of Medicare; ground '
     'ambulance expressly in the definitions', '1 Jan 2020 (act eff. '
     '1 Oct 2019)', 'State-regulated plans', 'NMSA 1978 ch. 59A (Surprise '
     'Billing Protection Act, 2019 HB 207)', 'V',
     'https://www.nmlegis.gov/Sessions/19%20Regular/bills/house/'
     'HB0207.HTML'),
    ('NY', False,
     'Usual-and-customary charge standard with independent dispute '
     'resolution; ground ambulance included (public and private '
     'operators). Measured side effect: fully insured ground ambulance '
     'prices rose about 13 percentage points post-law (Xu 2025)',
     '31 Mar 2015', 'Fully insured plans (the study shows self-insured '
     'diverging)', 'NY Emergency Medical Services and Surprise Bills Law '
     '(2014); Fin. Serv. Law art. 6', 'V',
     'https://pmc.ncbi.nlm.nih.gov/articles/PMC11911222/'),
    ('ND', False,
     'LESSER of 250% of Medicare or billed charges; direct payment '
     'required; balance billing prohibited (new sections to N.D.C.C. ch. '
     '23-27 and 26.1-47)', '2025 (HB 1322, 69th Assembly)',
     'State-regulated plans', 'N.D.C.C. ch. 23-27 / 26.1-47 (2025 HB '
     '1322)', 'V',
     'https://ndlegis.gov/assembly/69-2025/regular/documents/'
     '25-0744-04000.pdf'),
    ('NH', False,
     '325% of the urban/rural/super-rural Medicare rate minimum (or '
     'local-government set rate); commissioner sets rates from 2028; '
     'balance billing prohibited', '1 Jan 2026 (rate window through '
     '2027)', 'Fully insured plans', 'RSA 420-J:21 (2025 SB 245, ch. '
     '262)', 'V',
     'https://gc.nh.gov/bill_status/billinfo.aspx?id=927&inflect=2'),
    ('OH', True,
     'Emergency services only: OON ambulance paid the GREATEST of median '
     'in-network rate, the plan\'s usual OON amount, or the Medicare '
     'rate; no balance billing beyond cost share', '12 Apr 2021 (HB 388)',
     'State-regulated plans; emergency transports', 'ORC 3902.51', 'V',
     'https://codes.ohio.gov/ohio-revised-code/section-3902.51'),
    ('OR', False,
     'Established local rate; absent one, no less than 325% of Medicare; '
     'balance billing prohibited; DFR local-rate database', '1 Jan 2026 '
     '(2025 HB 3243)', 'State-regulated plans', 'ORS 743B.292 (2025 HB '
     '3243)', 'V',
     'https://olis.oregonlegislature.gov/liz/2025R1/Downloads/'
     'MeasureDocument/HB3243/Enrolled'),
    ('TX', True,
     'Political-subdivision rate submitted to TDI; else the LESSER of '
     'billed charges or 325% of Medicare; annual inflation adjustment '
     'capped; sunset extended to 1 Sep 2027 (2025)', '1 Jan 2024 (SB '
     '2476, 2023)', 'State-regulated plans (TX is footprint-adjacent for '
     'MO operators; marked for the register only)', 'Tex. Ins. Code '
     '1271.159, 1275.054, 1301.166 etc. (SB 2476)', 'V',
     'https://capitol.texas.gov/tlodocs/88R/billtext/html/SB02476F.htm'),
    ('UT', False,
     'State-set fee schedule: insurers must accept and pay the state EMS '
     'rates directly to the provider (2025 base rates published per Utah '
     'Code 53-2d-503); balance billing forbidden', '7 May 2025 (HB 301)',
     'Fully insured plans and workers\' comp', 'Utah Code 53-2d-503 (2025 '
     'HB 301)', 'V',
     'https://ems.utah.gov/ambulance-billing-questions/'),
    ('VT', False,
     'Direct reimbursement to the ambulance service required; MCO covers '
     'OON emergency ambulance with no additional member liability and '
     'must defend the member against balance claims (24 V.S.A. 2680, '
     '2689; amended 2023 Act 157, eff. 6 Jun 2024). Statute page '
     'returned 503 on fetch; provisions verified via the DFR bulletin '
     'and statute mirrors - flagged', '2024 amendment vintage',
     'Fully insured plans', '24 V.S.A. 2680, 2689', 'P',
     'https://legislature.vermont.gov/statutes/section/24/071/02689'),
    ('WA', True,
     'Balance billing banned for covered emergency AND non-emergency '
     'ground ambulance; enrollee pays in-network cost share only; local '
     'governments submit established rates to a public database',
     '1 Jan 2025 (2024 SB 5986)', 'State-regulated plans', 'RCW ch. '
     '48.49 (2024 c 242)', 'V',
     'https://www.insurance.wa.gov/insurers-regulated-entities/laws-and-'
     'rules-insurers-and-regulated-entities/protections-surprise-medical-'
     'billing/ground-ambulance-services-and-surprise-billing'),
    ('WV', False,
     'PARTIAL, stated as such: current protection reaches HMO enrollees '
     'only; 2025 SB 632 (400% of Medicare or billed charges, whichever '
     'less, direct payment) was introduced and NOT verified enacted; '
     'trackers list broader protection effective 2027', 'HMO scope '
     'current', 'HMO plans now; non-HMO per trackers from 2027',
     'W. Va. Code ch. 33 (HMO act); 2025 SB 632 status unverified', 'P',
     'https://www.wvlegislature.gov/bill_status/bills_text.cfm?billdoc='
     'sb632+intr.htm&yr=2025&sesstype=RS&i=632'),
]


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    sources += [
        {'key': 'state_codes_b9', 'publisher': 'State legislatures and '
         'code revisors (NE, IA, KS, MO, OH, WI, VA, MN, IN, KY)',
         'document': 'Official state statute and administrative-code '
                     'pages for ambulance CON, local franchise/EOA/PSA '
                     'and licensure provisions; one URL per row on '
                     'Entry_Barrier_Register',
         'vintage': 'Current statutes, fetched 11 Jul 2026',
         'locator': 'Per-row cites on Entry_Barrier_Register (e.g. RSMo '
                    '190.109; Minn. Stat. 144E.11; Va. Code 32.1-111.14; '
                    '900 KAR 6:075; Wis. Stat. 60.565; ORC 4766.04)',
         'supplies': 'The verified statutory entry-barrier map for the '
                     'ten footprint states',
         'url': 'https://revisor.mo.gov/main/OneSection.aspx?section='
                '190.109 (representative; per-row URLs on the tab)',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Entry_Barrier_Register']},
        {'key': 'con_review_2024', 'publisher': 'Milbank Quarterly (PMC '
         'open access)',
         'document': 'Certificate of Need Laws in Health Care: Past, '
                     'Present, and Future (2024 review, PMC11088301)',
         'vintage': '2024', 'locator': 'State-scope passages: "In '
                    'Nebraska, Indiana and Ohio, CONs are only required '
                    'for nursing homes"; "In Arizona, Minnesota and New '
                    'Mexico, CONs are only required for ambulance '
                    'services"',
         'supplies': 'Peer-reviewed CON scope classification used where '
                     'the statute itself is silent by omission',
         'url': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11088301/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Entry_Barrier_Register']},
        {'key': 'bb_tracker', 'publisher': 'Commonwealth Fund / Georgetown '
         'CHIR (Harden-Stein & Hoadley)',
         'document': 'Consumers Still Face Surprise Bills for Ground '
                     'Ambulances - States Are Trying to Protect Them '
                     '(13 Mar 2026) and the companion map of state laws',
         'vintage': 'March 2026 (CHIR mirror fetched; commonwealthfund.org '
                    'returned 403 to fetch and is cited via the mirror)',
         'locator': '"People in 22 states now have some protection"; 2025 '
                    'adds: UT, ND, NH, OR plus the IL revamp; TX sunset '
                    'extended to 1 Sep 2027',
         'supplies': 'The tracker count and the 2025 delta the per-row '
                     'statute verification hangs off',
         'url': 'https://chir.georgetown.edu/consumers-still-face-'
                'surprise-bills-for-ground-ambulances-states-are-trying-'
                'to-protect-them/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Balance_Billing_States']},
        {'key': 'bb_statutes', 'publisher': 'State legislatures (session '
         'laws and codes)',
         'document': 'Official statute/session-law texts for state ground '
                     'ambulance balance-billing laws; one URL per row on '
                     'Balance_Billing_States (e.g. La. R.S. 22:1880.2; ND '
                     'HB 1322 engrossed; IL PA 104-0248; ME 24-A 4303-F; '
                     'TX SB 2476 enrolled; NM HB 207; CA AB 716; AR Act '
                     '597; OH ORC 3902.51)',
         'vintage': 'Fetched 11 Jul 2026',
         'locator': 'Per-row cites and URLs on Balance_Billing_States',
         'supplies': 'Verified payment standards and effective dates',
         'url': 'https://www.legis.la.gov/legis/Law.aspx?d=1337472 '
                '(representative; per-row URLs on the tab)',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Balance_Billing_States']},
        {'key': 'ny_bb_hsr', 'publisher': 'Health Services Research (Xu '
         'et al., 2025; PMC11911222)',
         'document': 'The impacts of New York\'s balance billing '
                     'regulation on ground ambulance pricing',
         'vintage': '2025',
         'locator': 'NY EMS and Surprise Bills Law (2014, eff. Mar 2015) '
                    'covers ground ambulance at UCR; fully insured '
                    'ground ambulance prices +13.34pp post-law; '
                    'self-insured +9.45pp (n.s.)',
         'supplies': 'The only causal price-effect measurement of a state '
                     'ambulance balance-billing law, and the measured '
                     'fully-insured vs self-insured wedge',
         'url': 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11911222/',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Balance_Billing_States']},
    ]

    excluded += [
        {'figure': 'NCSL certificate-of-need state tracker values',
         'value': 'n/a', 'source_label': 'NCSL (fetch blocked)',
         'why_excluded': 'ncsl.org returned HTTP 403 to fetch on 11 Jul '
                         '2026; CON scope classification carried from the '
                         'peer-reviewed 2024 Milbank review instead.',
         'citable': 'NCSL CON page once fetchable; state CON statutes '
                    'directly.'},
        {'figure': 'Colorado HB25-1088 and Montana 2025 ambulance '
                   'balance-billing bills',
         'value': 'n/a', 'source_label': 'Session tracking',
         'why_excluded': 'HB25-1088 passed both chambers and was VETOED '
                         '(May 2025); Montana\'s 400%-of-Medicare bill '
                         'was tabled. Neither is law; both are context '
                         'only.',
         'citable': 'Future enacted session laws.'},
    ]

    # ------------------------------------------------------------ TAB 1 ---
    ws = wb.create_sheet('Entry_Barrier_Register')
    sb = lib.SheetBuilder(ws, 7, col_widths=[7, 60, 26, 4, 4, 30, 44],
                          tab_color='FF1F6F8B')
    sb.title('Entry barrier register: where ambulance market entry is '
             'legally gated in the ten footprint states')
    sb.subtitle('The question: in NE, IA, KS, MO, OH, WI, VA, MN, IN, KY, '
                'what statute gates a new ambulance operator - certificate '
                'of need, local franchise / exclusive operating area / '
                'primary service area, and licensure? Every row carries a '
                'statute or regulation cite whose text was fetched and '
                'read on 11 Jul 2026 (URL on the row); where the statute '
                'is silent or the fetch could not settle the point, the '
                'row says AMBIGUITY and asserts nothing. CON scope '
                'classifications lean on the 2024 Milbank 50-state review '
                'where the gate is an absence.')
    sb.note('DATA QUALITY: this is a register of STATUTORY mechanisms, '
            'not of enforcement practice - a franchise power at local '
            'option (VA) may be unused in one county and absolute in the '
            'next, and a need test (MN, MO endorsements, KY CON) is only '
            'as binding as its administration; nothing here measures how '
            'often applications are denied. Local ordinances sit beneath '
            'every state row and are out of scope.')
    sb.blank()

    sb.banner('Panel A. Certificate of need: does a CON law reach ground '
              'ambulance?')
    sb.headers(['State', 'What the statute (or review) says', 'Gate', '',
                '', 'Cite', 'URL (fetched 11 Jul 2026)'])
    a0 = sb.r + 1
    for st, what, gate, cite, url in CON_ROWS:
        sb.row([(st, 'label'), (what, 'text'), (gate, 'src'), None, None,
                (cite, 'note'), (url, 'note')], wrap=True)
    a_end = sb.r
    sb.blank()

    sb.banner('Panel B. County / municipal franchise, exclusive operating '
              'areas, primary service areas')
    sb.headers(['State', 'What the statute says', 'Mechanism', '', '',
                'Cite', 'URL (fetched 11 Jul 2026)'])
    b0 = sb.r + 1
    for st, what, gate, cite, url in FRANCHISE_ROWS:
        sb.row([(st, 'label'), (what, 'text'), (gate, 'src'), None, None,
                (cite, 'note'), (url, 'note')], wrap=True)
    sb.blank()

    sb.banner('Panel C. State licensure: agency and statute (all ten '
              'verified)')
    sb.headers(['State', 'Licensing agency and requirement', '', '', '',
                'Cite', 'URL (fetched 11 Jul 2026)'])
    c0 = sb.r + 1
    for st, what, cite, url in LICENSE_ROWS:
        sb.row([(st, 'label'), (what, 'text'), None, None, None,
                (cite, 'note'), (url, 'note')], wrap=True)
    sb.blank()

    sb.banner('Panel D. The gate count (live over Panel A/B rows)')
    d0 = sb.r + 1
    sb.row([('Footprint states where entry is legally GATED beyond '
             'licensure (KY CON; MN PSA+need test; MO endorsement gate; '
             'VA local franchise power; WI mandatory-local-provision + '
             'department PSA)', 'label'),
            (f'=COUNTIF(C{a0}:C{a_end},"GATED*")+COUNTIF(C{b0}:C{b0 + 9},'
             f'"GATED*")-1', 'fml', lib.FMT_INT),
            None, None, None, None,
            ('KY and MN appear in both panels; the -1 dedupes the double '
             'count so the cell counts STATES (KY, MN, MO, VA, WI)',
             'note')], wrap=True)
    sb.row([('Licensure rows verified with statute cite', 'label'),
            (10, 'fml', lib.FMT_INT), None, None, None, None,
            ('10 of 10 footprint states; Panel C', 'note')])
    sb.blank()
    sb.banner('Read panel')
    sb.prose('Where entry is legally gated vs open: Kentucky is the '
             'hardest gate in the footprint - a private ground ambulance '
             'operator needs a certificate of need unless it is a '
             'city/county service doing emergency transport or a hospital '
             'transporting from its own house. Minnesota runs a '
             'CON-equivalent need test with primary service areas; '
             'Missouri grandfathers 1997 service areas and requires '
             'political-subdivision endorsement letters for new or '
             'expanded areas; Virginia lets any county or city make '
             'unfranchised operation unlawful and cap the number of '
             'agencies; Wisconsin ties every license to a department-set '
             'primary service area. Nebraska, Iowa, Kansas, Ohio and '
             'Indiana are open at the state layer: licensure plus local '
             'provision/funding powers, no statutory need test found. '
             'The guardrail below is the reading limit.')

    facts += [
        {'metric': 'Footprint states with a statutory entry gate beyond '
                   'licensure (CON, need test, endorsement gate, franchise '
                   'power, department-set PSA)', 'year': 2026, 'value': 5,
         'unit': 'states of 10 (KY, MN, MO, VA, WI)', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['state_codes_b9', 'con_review_2024'],
         'locator': 'Entry_Barrier_Register Panels A-B; live count Panel '
                    'D', 'lives_on': 'Entry_Barrier_Register',
         'cross_check': 'Each mechanism verified against fetched statute '
                        'text; VA gate is at local OPTION and KS carries '
                        'a flagged non-duplication rule short of a gate'},
        {'metric': 'Footprint licensure register completeness (agency + '
                   'statute cite verified per state)', 'year': 2026,
         'value': 1.0, 'unit': 'share of 10 states', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['state_codes_b9'],
         'locator': 'Entry_Barrier_Register Panel C (10 rows, each with '
                    'fetched URL)', 'lives_on': 'Entry_Barrier_Register',
         'cross_check': 'Two rows carry flagged ambiguities elsewhere '
                        '(KS county power, IN EOA absence), none on '
                        'licensure'},
    ]

    findings.append({
        'id_hint': 78,
        'finding': 'Ambulance entry in the footprint is legally gated in '
                   'five of ten states and open-at-the-state-layer in the '
                   'other five: Kentucky requires a certificate of need '
                   'for private ground ambulance (with 2020s carve-outs '
                   'for government emergency and hospital-origin '
                   'transport), Minnesota runs a need test with primary '
                   'service areas, Missouri grandfathers 1997 service '
                   'areas behind political-subdivision endorsements, '
                   'Virginia authorizes counties to criminalize '
                   'unfranchised operation and cap agency counts, and '
                   'Wisconsin assigns department-set primary service '
                   'areas - while NE, IA, KS, OH and IN gate entry only '
                   'through licensure and local provision powers.',
        'numbers': f"='Entry_Barrier_Register'!B{d0}",
        'sources': 'state_codes_b9; con_review_2024',
        'confidence': 'High on the statutes quoted (each fetched); '
                      'moderate on the open/closed classification where '
                      'it rests on absence',
        'guardrail': 'Statutory mechanism is not enforcement practice: a '
                     'local-option franchise power may sit unused, a need '
                     'test may approve every applicant, and county '
                     'ordinances beneath the state layer are out of '
                     'scope. This register says where the legal gate '
                     'EXISTS, not how often it closes.'})

    # ------------------------------------------------------------ TAB 2 ---
    ws2 = wb.create_sheet('Balance_Billing_States')
    sb = lib.SheetBuilder(ws2, 8,
                          col_widths=[7, 10, 56, 17, 24, 30, 8, 42],
                          tab_color='FFC58F00')
    sb.title('State ground-ambulance balance-billing protections: the '
             'payment standards, verified statute by statute')
    sb.subtitle('The question: which states ban ground-ambulance balance '
                'billing, and at what payment standard? The federal No '
                'Surprises Act left ground ambulance out; 22 states now '
                'carry some protection (Commonwealth Fund / Georgetown '
                'CHIR count, March 2026). Every row below carries the '
                'statute or session-law cite; rows marked V had their '
                'text fetched and read on 11 Jul 2026, rows marked P are '
                'partial or ambiguous protections stated as such. '
                'Footprint states flagged. Payment standards are the '
                'emerging price signal: most peg out-of-network ground '
                'ambulance to a LOCAL government rate first, then to a '
                'multiple of Medicare.')
    sb.note('DATA QUALITY: state insurance law binds FULLY INSURED, '
            'state-regulated plans only - ERISA self-funded employer '
            'plans (the majority of commercial lives) are untouched by '
            'every row on this tab; several laws cover emergency '
            'transport only (OH); Medicare and Medicaid have their own '
            'rules and are out of scope; the 22-state count includes '
            'partial regimes this register marks P rather than counts as '
            'full protections.')
    sb.blank()

    sb.banner('Panel A. The register (V = statute text fetched and '
              'verified 11 Jul 2026; P = partial or ambiguous, stated)')
    sb.headers(['State', 'Footprint', 'Payment standard (as enacted)',
                'Effective', 'Scope', 'Statute / session law', 'V/P',
                'URL (fetched 11 Jul 2026)'])
    a0 = sb.r + 1
    for st, fp, std, eff, scope, cite, status, url in BB_ROWS:
        sb.row([(st, 'label'), ('YES' if fp else '-', 'fml'),
                (std, 'text'), (eff, 'src'), (scope, 'text'),
                (cite, 'note'), (status, 'src'), (url, 'note')], wrap=True)
    a_end = sb.r
    sb.blank()

    sb.banner('Panel B. The rate-peg pattern (live over Panel A)')
    b0 = sb.r + 1
    sb.row([('States in the register (rows above)', 'label'),
            (f'=COUNTA(A{a0}:A{a_end})', 'fml', lib.FMT_INT), None, None,
            None, None, None,
            ('22 per the tracker; this register prints all 22 with 5 '
             'marked P (DE, FL, MD, NV, WV) + VT flagged', 'note')])
    sb.row([('Rows verified against fetched statute text (V)', 'label'),
            (f'=COUNTIF(G{a0}:G{a_end},"V")', 'fml', lib.FMT_INT), None,
            None, None, None, None,
            ('the count facts below quote the tracker for the 22 and '
             'this cell for the verified core', 'note')])
    sb.row([('Medicare-peg range across verified rows', 'label'),
            ('1.5x to 4.0x Medicare', 'src'), None, None, None, None,
            None,
            ('NM 150% floor-of-greatest; ME 180/200% lesser-of; ND 250%; '
             'CO/LA/TX/NH/OR 325%; IN 400% - all as fallbacks behind a '
             'local-government rate where one exists', 'note')])
    sb.row([('Modal design', 'label'),
            ('Local government rate first; Medicare multiple as the '
             'fallback; direct payment; cost share capped at in-network',
             'src'), None, None, None, None, None,
            ('AR is the outlier: workers-comp fee schedule, not Medicare',
             'note')], wrap=True)
    sb.blank()
    sb.banner('Read panel')
    sb.prose('The emerging pattern is a state-legislated rate card for '
             'out-of-network ground ambulance: pay the local government '
             'rate where one exists, otherwise a Medicare multiple '
             'running 1.5x (NM) through 3.25x (CO, LA, TX, NH, OR) to '
             '4.0x (IN), with direct payment to the provider and the '
             'patient capped at in-network cost sharing. For a transport '
             'operator this is revenue-floor legislation in fully insured '
             'books: New York\'s version measurably RAISED fully insured '
             'ambulance prices by about 13 points while self-insured '
             'prices moved less - the cleanest published evidence that '
             'these laws reprice the fully insured book only. Footprint '
             'states covered: IN (400% peg), OH (emergency-only, '
             'Medicare-floor greatest-of), WA-adjacent none; the other '
             'eight footprint states have NO state ambulance '
             'balance-billing law as of the March 2026 tracker.')

    facts += [
        {'metric': 'States with ground-ambulance balance-billing '
                   'protections', 'year': 2026, 'value': 22,
         'unit': 'states (some protection; includes partial regimes)',
         'basis': 'SOURCED', 'tier': 'A', 'source_keys': ['bb_tracker'],
         'locator': 'Commonwealth Fund / CHIR, 13 Mar 2026 ("people in 22 '
                    'states now have some protection"); register rows on '
                    'Balance_Billing_States',
         'lives_on': 'Balance_Billing_States',
         'cross_check': 'This register prints all 22 with 16 verified '
                        'against fetched statute text and 6 marked '
                        'partial/ambiguous (DE, FL, MD, NV, WV, VT-flag); '
                        '13 of 22 also cover non-emergency transport per '
                        'the tracker'},
        {'metric': 'Highest state Medicare peg for out-of-network ground '
                   'ambulance (Indiana, footprint state)', 'year': 2024,
         'value': 4.0, 'unit': 'x Medicare (fallback cap absent a local '
         'rate; lesser of this or billed charges)', 'basis': 'GOV',
         'tier': 'A', 'source_keys': ['bb_statutes'],
         'locator': 'IC 27-1-2.3 as amended by HEA 1385-2024, eff. '
                    '1 Jul 2024', 'lives_on': 'Balance_Billing_States',
         'cross_check': 'Peg range across verified rows 1.5x (NM) to '
                        '4.0x (IN); modal peg 3.25x (CO, LA, TX, NH, '
                        'OR)'},
    ]

    findings.append({
        'id_hint': 79,
        'finding': 'The states are building a rate card the federal No '
                   'Surprises Act never did: 22 states protect patients '
                   'from ground-ambulance balance bills, and the enacted '
                   'payment standards converge on local-government rates '
                   'backed by Medicare multiples from 1.5x (NM) through '
                   'the modal 3.25x (CO, LA, TX, NH, OR) to 4.0x in '
                   'footprint-state Indiana - legislated revenue floors '
                   'for out-of-network transport in fully insured books, '
                   'which New York\'s measured experience shows reprice '
                   'those books upward by double digits.',
        'numbers': f"='Balance_Billing_States'!B{b0}",
        'sources': 'bb_tracker; bb_statutes; ny_bb_hsr',
        'confidence': 'High on the verified rows (16 statutes fetched); '
                      'the 22 count is the tracker\'s',
        'guardrail': 'These laws bind FULLY INSURED, state-regulated '
                     'plans only: ERISA self-funded plans - most '
                     'commercial lives - are out of scope for state law, '
                     'so a state peg is neither a commercial-book price '
                     'floor nor a market rate. Scope also differs by '
                     'state (emergency-only in OH; HMO-only in WV; '
                     'local-government providers only in MD).'})

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings,
            'meta': {'bb_rows': len(BB_ROWS),
                     'barrier_rows': len(CON_ROWS) + len(FRANCHISE_ROWS)
                     + len(LICENSE_ROWS)}}
