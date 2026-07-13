"""Run 5, Task 5.3: IFT_Software_Landscape - the dispatch, ePCR, billing and
transfer-center platforms operating in interfacility and EMS transport, plus the
request-cascade workflow that is the operational basis of the switching-cost
argument.

Every row is built from a public source (vendor site, PE/press release, or
marketplace listing) with a retrieval date in the row; nothing here comes from
any conversation. Vendor-reported install bases are labeled CLAIMED (tier C):
they are self-reported marketing figures, carried because they are the only
public numbers, not because they are independently verified.
"""

SHEETS = [{'name': 'IFT_Software_Landscape',
           'question': 'Which dispatch, ePCR, billing and transfer-center '
                       'platforms run interfacility transport, and what does '
                       'their workflow imply for switching costs?'}]

ACC = '2026-07-13'   # retrieval date for every source this pass

# Each vendor: (platform, category, scope, install_base_claim, ehr, ownership,
#               pricing, source_url)
VENDORS = [
    # -- EMS operations software: ePCR / records / billing / dispatch --------
    ('ImageTrend (Elite)', 'ePCR / records / billing',
     'ePCR (Elite), fire records, billing/RCM, CQI, and a hospital '
     'interoperability layer (Health Information Hub); integrates with '
     'third-party CAD rather than selling dispatch',
     'CLAIMED: "40+ states and nearly 3,000 customers"; "43 state EMS '
     'repositories run on ImageTrend"',
     'Demonstrated EMS-EHR interoperability with Epic at the HIMSS '
     'Interoperability Showcase; no Epic Showroom / Oracle Health listing found',
     'Welsh, Carson, Anderson & Stowe (PE), equity investment Feb 2023',
     'Not public',
     'prnewswire.com/news-releases/imagetrend-announces-strategic-growth-'
     'investment-from-welsh-carson-anderson--stowe-301743726.html'),
    ('ESO', 'ePCR / EHR / billing',
     'ePCR/EHR, Health Data Exchange (hospital interoperability), Fire RMS, '
     'patient registry, billing/RCM; CAD/dispatch via its Logis unit',
     'CLAIMED: "more than 10,000 agencies"; "250M records managed"',
     'Health Data Exchange described as supporting Epic and Cerner Millennium '
     'via FHIR (secondary sources); no first-party marketplace listing found',
     'Vista Equity Partners, strategic investment Mar 2021; acq. Logis (2024), '
     'Emergency Reporting (2021)',
     'Not public',
     'eso.com/ems/ehr/ ; eso.com/news/press-releases/eso-receives-strategic-'
     'investment-from-vista-equity-partners/'),
    ('Logis Solutions (by ESO)', 'CAD / dispatch / billing',
     'CAD (Logis IDS), billing, voice, inventory; explicitly supports '
     'non-emergency and interfacility transport dispatch and homecare',
     'Not publicly stated (aggregate); NSW Health hub case study "~800 '
     'requests for transports each day"',
     'Interoperable across records/ePCR/billing platforms via open APIs; no '
     'Epic/Cerner listing named',
     'Acquired by ESO (Vista Equity), Jul 2024',
     'Not public',
     'eso.com/news/press-releases/eso-acquires-logis-solutions/ ; '
     'logissolutions.net/case-studies/new-south-wales/'),
    ('ZOLL Data Systems', 'CAD / dispatch / ePCR / billing',
     'RescueNet integrated dispatch/CAD, ePCR/charting and billing; emsCharts '
     'ePCR (via the 2019 Golden Hour acquisition)',
     'CLAIMED: RescueNet "plays a role in more than 13 million EMS events '
     'annually"',
     'Hospital data exchange described generically; no Epic/Cerner marketplace '
     'listing verified',
     'ZOLL Medical Corporation, an Asahi Kasei Group company (Asahi Kasei '
     'acquired ZOLL Apr 2012)',
     'Not public',
     'zolldata.com/rescuenet ; zoll.com/.../press-release/2019/03/04/zoll-'
     'acquires-golden-hour-data-systems'),
    ('Traumasoft', 'All-in-one EMS / IFT',
     'Single cloud-native platform uniting CAD/dispatch, ePCR, billing, '
     'scheduling, fleet and HR - marketed to non-emergency and interfacility '
     'operators',
     'Not publicly stated',
     'Integrations with hospital and billing systems described; no Epic/Cerner '
     'marketplace listing found',
     'Serent Capital growth investment Apr 2024 (founded 2006, Portage MI)',
     'Not public',
     'traumasoft.com ; businesswire.com/news/home/20240410217650/en/'),
    ('AngelTrack', 'CAD / ePCR / billing',
     'Single-platform CAD/dispatch, ePCR and billing/RCM for EMS, fire and '
     'NEMT/interfacility operators; patient data flows directly into billing',
     'Not publicly stated',
     'HL7 / hospital interfaces described; no Epic/Cerner marketplace listing '
     'found',
     'Privately held (ownership not publicly disclosed)',
     'PUBLIC: tiered monthly, Bronze $778/mo (<=450 calls) to Gold $2,988/mo '
     '(<=4,000); $300/mo qualifying non-profits',
     'angeltrack.com/pricing/'),
    ('Beyond Lucid (MEDIVIEW / BEACON)', 'ePCR / prehospital HIE',
     'ePCR (MEDIVIEW) and a prehospital Health Information Exchange (BEACON) '
     'spanning ground/air critical care, non-emergency and interfacility '
     'transport',
     'CLAIMED: "30 U.S. states ... 300+ hospitals" on the BEACON network',
     'Reaches EHRs via HL7/CCD and a QHIN partner (MedAllies, TEFCA), announced '
     'Feb 2024; no Epic/Cerner marketplace listing',
     'Privately held / independent (founded 2009)',
     'Not public',
     'pulsara.com/beyond-lucid ; jems.com/ems-operations/ems-equipment-gear/'
     'beyond-lucid-technologies-selects-medallies-as-its-qualified-health-'
     'information-network-partner/'),
    ('Julota', 'Interoperability / care coordination',
     'Interoperability and care-coordination platform bridging EHR-to-EHR and '
     'EHR-to-ePCR, consent and closed-loop referrals (MIH/CP, co-responder)',
     'CLAIMED: "adopted in over 27 US states"',
     'Bridges disparate EHRs and EHR-ePCR; no specific Epic/Cerner marketplace '
     'listing found',
     'Privately held / independent (founded 2010)',
     'Not public',
     'julota.com/about-us/'),
    ('CentralSquare', 'Public-safety CAD / records',
     'Public-safety CAD and records (911/fire/EMS) used for emergency dispatch '
     'that feeds transport',
     'CLAIMED: "8,000+ agencies"; third-party "25% of all 911 calls '
     'nationwide"',
     'Public-safety integrations; no EMS-clinical Epic/Cerner listing',
     'Vista Equity Partners and Bain Capital',
     'Not public',
     'centralsquare.com'),
    ('Tyler Technologies', 'Enterprise CAD / fire-EMS records',
     'Enterprise public-safety CAD and fire/EMS ePCR/NFIRS/NERIS records',
     'Not publicly stated (no verified Tyler-wide agency count)',
     'Public-safety and records integrations; no EMS-clinical marketplace '
     'listing',
     'Public company (NYSE: TYL); acq. Emergency Networking (Jul 2025)',
     'Not public',
     'tylertech.com'),
    ('First Due (Locality Media)', 'Records / response / community risk',
     'Fire and EMS records, response and community-risk-reduction platform',
     'CLAIMED: "over 3,000 agencies"',
     'Records and hospital-data integrations; no Epic/Cerner marketplace '
     'listing',
     'Locality Media, Inc.; Serent Capital-backed; $355M growth investment led '
     'by JMI Equity (Aug 2025)',
     'Not public',
     'firstdue.com'),
    ('Golden Hour / emsCharts', 'Billing / ePCR',
     'EMS billing/RCM and ePCR (emsCharts); air and ground transport billing',
     'Not publicly stated',
     'HL7 hospital-EMR interfaces described; no Epic/Cerner marketplace listing',
     'emsCharts -> ZOLL Medical (2019) -> Digitech (2025; Digitech owned by '
     'Sarnova / Investor AB)',
     'Not public',
     'goldenhour.com (now Digitech EMS billing)'),
    # -- Transfer-center / interfacility brokering (hospital-to-hospital) -----
    ('Central Logic / ABOUT Healthcare', 'Transfer center / transport coord.',
     'Transfer-center orchestration: inbound/outbound transfers, bed and '
     'provider visibility, automated transport coordination and analytics',
     'CLAIMED: "800 hospitals and health systems ... touching 14% of U.S. '
     'hospital patients each year"; "93% customer retention"',
     'Multi-EHR transfer coordination (Arizona Surge Line spans varying EHRs); '
     'Microsoft AppSource listing; no Epic/Cerner listing confirmed',
     'Rubicon Technology Partners (PE), 2020; acq. Ensocare, Acuity Link, '
     'Edgility; rebranded ABOUT Healthcare 2021',
     'Not public',
     'prnewswire.com/news-releases/central-logic-saw-record-breaking-growth-'
     'awareness-and-momentum-in-2020-301223109.html ; abouthealthcare.com'),
    ('Motient (Mission Control)', 'Interfacility transfer coordination',
     'Interfacility transfer decision support (acuity scoring), destination '
     'sourcing and transport coordination; vendor-agnostic',
     'CLAIMED: "more than 5,000 patient transfers from 122 hospitals ... 2021"; '
     'Kansas statewide (115 hospitals, 130+ transport vendors)',
     'Vendor-agnostic transport layer; no EHR marketplace listing (transport, '
     'not EHR)',
     'Privately held / independent (formerly Cheyenne Mountain Software, '
     'renamed 2021)',
     'Not public (statewide deploys funded by state health departments)',
     'prnewswire.com/news-releases/motient-facilitates-over-5-000-patient-'
     'transfers-for-120-healthcare-providers-in-2021--301454183.html'),
    ('TeleTracking', 'Transfer / command center',
     'Centralized transfer/command center coordinating the right facility and '
     'mode of transportation (Transfer IQ, Capacity IQ)',
     'CLAIMED: "12MM patients served"; legacy "over 850 hospital clients ... '
     '350,000 beds"',
     'Bidirectional EMR data sharing described; no named Epic/Cerner '
     'marketplace listing confirmed',
     'Privately held; founder-owned (founded 1991)',
     'Not public',
     'teletracking.com/the-command-center/ ; teletracking.com/about/'),
]

# Request-cascade / SLA workflow, public product documentation.
WORKFLOW = [
    ('Electronic preferred-vendor request', 'Central Logic (v4.13)',
     'Transfer centers "integrate directly with the health system\'s '
     'transportation vendors so transport requests can be made electronically"; '
     'clinicians "choose from their preferred vendors" and review "key '
     'performance metrics associated with their preferred vendors"',
     'prnewswire.com/news-releases/central-logic-unveils-solution-update-to-'
     'further-speed-time-to-care-300884392.html'),
    ('Ranked-vendor broadcast / bid capture', 'VectorCare (ADI)',
     '"ADI broadcasts requests to contracted vendors simultaneously, captures '
     'bids and ETAs, applies routing rules, and books the optimal provider" '
     'on "fastest ETA, lowest cost, preferred vendor, or capacity balance" - '
     'the request-cascade model the switching-cost argument rests on',
     'vectorcare.com/feeds/service/patient-transportation-software ; '
     'vectorcare.com/solutions'),
    ('Destination + transport sourcing', 'Motient (Mission Control)',
     'Platform "locate[s] an available receiving facility and arrange[s] '
     'transport services" and coordinates across 130+ transport vendors, with '
     'near-real-time status',
     'prnewswire.com/news-releases/motient-facilitates-over-5-000-patient-'
     'transfers-for-120-healthcare-providers-in-2021--301454183.html'),
    ('Acceptance BEFORE dispatch (the SLA split)', 'AutoLaunch study '
     '(peer-reviewed)',
     'Dispatching the ambulance to the sending facility PRIOR TO patient '
     'acceptance by the receiving facility cut median IFT response time from '
     '27.5 to 19.9 minutes (N=1,881) - direct evidence that acceptance and '
     'pickup-to-completion are distinct, separately-timed steps',
     'tandfonline.com Prehospital Emergency Care 2022;26(5):739-745 (DOI '
     '10.1080/10903127.2021.1954271)'),
    ('Real-time status tracking', 'Logis (by ESO) / TeleTracking',
     'Hospital "customers ... readily track their request for service, watching '
     'in near-real-time the status of the ambulance and patient" (Logis); '
     'closed-loop status updates "throughout the transfer process" '
     '(TeleTracking)',
     'logissolutions.net/case-studies/new-south-wales/ ; '
     'teletracking.com/resources/transfer-iq/'),
]


def build(wb, ctx):
    lib = ctx['lib']
    accessed = ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    sources += [
        {'key': 'sw_ems_public', 'publisher': 'Vendor public record',
         'document': 'Public websites, private-equity and press releases, and '
                     'marketplace listings for EMS/interfacility operations '
                     'software (dispatch, ePCR, billing/RCM)',
         'vintage': f'Pages as retrieved {ACC}',
         'locator': 'Per-vendor URL printed in the Public source column of '
                    'each row',
         'supplies': 'The EMS operations software rows of IFT_Software_Landscape',
         'url': 'https://www.imagetrend.com/', 'tier': 'C', 'accessed': accessed,
         'powers': ['IFT_Software_Landscape']},
        {'key': 'sw_transfer_public', 'publisher': 'Vendor public record',
         'document': 'Public websites and press releases for hospital '
                     'transfer-center and interfacility brokering platforms '
                     '(Central Logic/ABOUT, Motient, TeleTracking)',
         'vintage': f'Pages as retrieved {ACC}',
         'locator': 'Per-vendor URL printed in the Public source column of '
                    'each row',
         'supplies': 'The transfer-center platform rows and the workflow panel',
         'url': 'https://www.centrallogic.com/our-solutions/', 'tier': 'C',
         'accessed': accessed, 'powers': ['IFT_Software_Landscape']},
    ]

    ws = wb.create_sheet('IFT_Software_Landscape')
    sb = lib.SheetBuilder(
        ws, 10,
        col_widths=[26, 22, 34, 30, 26, 26, 12, 3, 3, 44],
        tab_color='FF6B7C93')
    sb.title('Interfacility transport software: the dispatch, ePCR, billing '
             'and transfer-center platforms, from the public record')
    sb.subtitle('The stickiness chapter argues workflow integration; this tab '
                'supplies the market evidence for it. Each row is a platform '
                'operating in interfacility or EMS transport, built only from '
                'public sources - the vendor site, a private-equity or press '
                'release, or a marketplace listing - with the URL and retrieval '
                'date in the row. Install-base figures are vendor self-reported '
                '(CLAIMED, tier C), carried because they are the only public '
                'numbers, not because they are independently verified. The '
                'workflow panel below documents the request-cascade the '
                'switching-cost argument rests on, again from public product '
                'documentation only.')
    sb.note('DATA QUALITY: a public-record landscape, not a share model. It '
            'does not rank vendors by revenue or seat count (no public source '
            'supports that), and it does not assert market shares. Vendor '
            'claims are labeled CLAIMED; ownership and acquisition dates are '
            'from dated press/PE releases. "Not public" means the field is not '
            'disclosed publicly, never that it was estimated. No row or '
            'workflow line references any conversation.')
    sb.blank()

    # ---------------------------------------------------------- Panel A ---
    sb.banner('Panel A. The platforms (public record; install base = vendor '
              'CLAIMED unless noted)')
    sb.headers(['Platform', 'Category', 'Product scope',
                'Publicly-claimed install base', 'EHR integration (public)',
                'Ownership / parent', 'Pricing', '', '',
                'Public source (retrieved ' + ACC + ')'])
    for v in VENDORS:
        platform, cat, scope, base, ehr, own, price, url = v
        sb.row([(platform, 'label'), (cat, 'text'), (scope, 'text'),
                (base, 'text'), (ehr, 'text'), (own, 'text'), (price, 'text'),
                None, None, (url, 'note')], wrap=True, height=60)
    sb.blank()

    # ---------------------------------------------------------- Panel B ---
    sb.banner('Panel B. The request-cascade workflow (public product '
              'documentation) - the operational basis of the switching-cost '
              'argument')
    sb.headers(['Workflow element', 'Documented by', 'What the public source '
                'says', '', '', '', '', '', '',
                'Public source (retrieved ' + ACC + ')'])
    for w in WORKFLOW:
        element, who, what, url = w
        sb.row([(element, 'label'), (who, 'text'), (what, 'text'),
                None, None, None, None, None, None, (url, 'note')],
               wrap=True, height=56)
    sb.note('The acceptance-versus-completion distinction (a named SLA field on '
            'Contract_Corpus): transfer-center and dispatch platforms document '
            'a REQUEST/ACCEPTANCE step (a vendor accepts the trip) separately '
            'from PICKUP-TO-COMPLETION (the transport is performed). A contract '
            'response-time commitment governs acceptance; a pickup-to-'
            'completion commitment governs the transport itself - different '
            'terms that abstract to different SLA fields wherever public '
            'contracts specify them.')
    sb.blank()

    # ------------------------------------------------------- read panel ---
    n_claimed = sum(1 for v in VENDORS if v[3].startswith('CLAIMED'))
    sb.banner('Read panel')
    sb.prose(
        f'The interfacility software market splits into two layers, and {len(VENDORS)} '
        'platforms with a solid public record populate them. The EMS-operations '
        'layer - ePCR, CAD/dispatch and billing (ImageTrend, ESO with its Logis '
        'CAD unit, ZOLL, Traumasoft, AngelTrack, Beyond Lucid) - runs the truck '
        'and the claim. The hospital transfer-center layer (Central Logic/'
        'ABOUT, Motient, TeleTracking) sits upstream, orchestrating the '
        'hospital-to-hospital transfer and choosing the transport vendor - the '
        'demand-capture point for interfacility volume. Two structural facts '
        'stand out. First, the layer is consolidating under private equity: '
        'ESO (Vista), ImageTrend (Welsh Carson), CentralSquare (Vista and '
        'Bain), First Due (JMI), Central Logic (Rubicon), with ESO rolling up '
        'Logis and Emergency Reporting - the same roll-up pattern the '
        'fragmentation chapter tracks on the operator side. Second, the '
        'workflow is real and documented: transfer centers issue electronic '
        'requests to a ranked, preferred set of vendors, track status in near '
        'real time, and score vendors on performance (Central Logic, VectorCare, '
        'Motient, Logis) - the switching-cost mechanism the stickiness chapter '
        'asserts, now evidenced from public product documentation rather than '
        'claimed. What this tab does not do is rank the market: no public '
        'source supports a revenue or seat-share ordering, so none is asserted, '
        f'and the {n_claimed} install-base figures carried are vendor self-'
        'reported.')

    # ------------------------------------------------------------ facts ---
    facts += [
        {'metric': 'ESO EMS records platform install base (vendor-claimed)',
         'year': 2026, 'value': 10000, 'unit': 'agencies (CLAIMED, floor "more '
         'than")', 'basis': 'CLAIMED', 'tier': 'C',
         'source_keys': ['sw_ems_public'],
         'locator': 'IFT_Software_Landscape Panel A, ESO row',
         'lives_on': 'IFT_Software_Landscape',
         'cross_check': 'Vendor self-reported on eso.com; not independently '
                        'verified; carried as a public claim, not a measurement'},
        {'metric': 'Central Logic / ABOUT transfer-center reach '
                   '(vendor-claimed)', 'year': 2021, 'value': 0.14,
         'unit': 'share of US hospital patients touched (CLAIMED)',
         'basis': 'CLAIMED', 'tier': 'C', 'source_keys': ['sw_transfer_public'],
         'locator': 'IFT_Software_Landscape Panel A, Central Logic row',
         'lives_on': 'IFT_Software_Landscape',
         'cross_check': 'Vendor self-reported (800 hospitals; "14% of U.S. '
                        'hospital patients each year"); a marketing figure, '
                        'not an independent measurement'},
    ]

    # --------------------------------------------------------- findings ---
    findings += [
        {'id_hint': 111,
         'finding': 'The interfacility transport software market is a real, '
                    'two-layer, and rapidly PE-consolidating landscape, '
                    'documented here from public sources for '
                    f'{len(VENDORS)} platforms: an EMS-operations layer (ePCR, '
                    'CAD/dispatch, billing - ImageTrend, ESO/Logis, ZOLL, '
                    'Traumasoft, AngelTrack, Beyond Lucid) and a hospital '
                    'transfer-center layer that captures the transfer and picks '
                    'the transport vendor (Central Logic/ABOUT, Motient, '
                    'TeleTracking). Ownership is concentrating fast - ESO under '
                    'Vista, ImageTrend under Welsh Carson, CentralSquare under '
                    'Vista and Bain, First Due under JMI, Central Logic under '
                    'Rubicon - the same roll-up the fragmentation chapter '
                    'tracks on the operator side.',
         'numbers': 'Public-record landscape; 14 platforms, ownership from '
                    'dated PE/press releases (Panel A)',
         'sources': 'sw_ems_public; sw_transfer_public',
         'confidence': 'High on existence, category and ownership (dated public '
                       'sources); install-base figures are vendor-claimed',
         'guardrail': 'A landscape, not a share model. Install bases are vendor '
                      'self-reported (CLAIMED); no revenue or seat-share '
                      'ordering is asserted because no public source supports '
                      'one.'},
        {'id_hint': 112,
         'finding': 'The switching-cost mechanism the stickiness chapter '
                    'asserts is documented in public product literature: '
                    'transfer-center and dispatch platforms issue electronic '
                    'transport requests to a ranked, preferred set of vendors, '
                    'track status in near real time, and score vendors on '
                    'performance (Central Logic, VectorCare, Motient, Logis). '
                    'The request-cascade and preferred-vendor lists are the '
                    'operational basis of the argument, and the contract terms '
                    'split into a request/acceptance response-time commitment '
                    'and a distinct pickup-to-completion commitment.',
         'numbers': 'Workflow panel (Panel B): 4 documented elements, each '
                    'cited to a public product URL',
         'sources': 'sw_transfer_public; sw_ems_public',
         'confidence': 'High that the workflow is publicly documented; the '
                       'strength of any single switching cost is not quantified',
         'guardrail': 'Public product documentation describes the workflow; it '
                      'does not measure how binding the switching cost is in '
                      'practice, which no public source quantifies.'}]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings, 'meta': {'n_vendors': len(VENDORS)}}
