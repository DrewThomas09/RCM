"""Run 7: fleet-license identification for IFT and all ambulance transport.

Three tabs answer one operational question a diligence desk keeps hitting: how
do you identify an ambulance operator's FLEET - the count of ambulances it is
licensed/permitted to run - and its license footprint, from PUBLIC records only?

Fleet_License_Route_Map - the method. "Fleet license" is not one object; it
decomposes into (1) the state SERVICE/agency license (operator authorization and
levels: BLS/ALS/SCT/air), (2) the per-VEHICLE permit each ambulance carries under
that service license at a level (ALS/BLS/dual) - the actual fleet-size unit,
(3) PERSONNEL licensure (EMT/paramedic/MICP) as a crew-capacity proxy, and
(4) federal enrollment routes - NPPES ambulance-organization taxonomy (identity),
PECOS/Medicare Part B supplier enrollment (billing authority), and FMCSA
USDOT/MCS-150 (interstate non-emergency motor-carrier vehicle inventory). The map
prints, per object, the public route, what it yields, whether it yields a
per-operator VEHICLE COUNT, and the access tier.

Fleet_License_State_Matrix - coverage. All 51 jurisdictions (50 states + DC): the
state EMS licensing authority, whether the service roster is public and by what
route (open-data API / PDF directory / portal lookup), the per-vehicle permit
regime, the verified NPPES operator floor, whether a per-operator fleet count is
publicly retrievable, and the honest access status. Where the fleet count sits
behind a portal or FOIA, the cell is bordered PENDING and names the registry that
would fill it.

Fleet_Size_Evidence - the landed numbers. The NPPES ambulance-organization
operator floor per jurisdiction (computed live from the manifested NPPES roster),
the taxonomy split (land / generic / air), the Missouri open-data service
directory counts (from the manifested Socrata pull), and the confirmed statewide
vehicle-license anchors (Texas' over 5,000 licensed ambulances, New Jersey's
~4,500 and Michigan's 3,847). Every number is public and re-derivable;
per-operator vehicle counts that are not public are PENDING with the named state
registry.

IFT_License_Tracker - the one-grid tracker. Per US jurisdiction, every public
ambulance/IFT license count in a single grid across four universes that must not
be summed: the NPPES operator-identity floor (all 51), the licensed-service count
where a state publishes one (TX, PA, CA, FL, MO, IA, MI), the licensed-vehicle
total where published (TX, NJ, MI), and the EMT and paramedic workforce with mean
wage from BLS
OEWS 2024 (SOC 29-2042 / 29-2043) so wages per state can be backed into. Every
unpublished service or vehicle count is bordered PENDING with the State_Matrix
route that fills it.

FIREWALL: public sources only. No operator is described as a customer/prospect of
any company. The NPPES floor is an identity floor, not a fleet count - a single
operator may hold many vehicle permits under one NPI, and one NPI is not one
ambulance; that confound is printed on every panel that uses it.
"""

SHEETS = [
    {'name': 'Fleet_License_Route_Map',
     'question': 'How do you identify an ambulance operator\'s fleet (licensed '
                 'vehicle count) and license footprint from public records - '
                 'what are the license objects and the route to each?'},
    {'name': 'Fleet_License_State_Matrix',
     'question': 'For all 51 US jurisdictions, is the ambulance service roster '
                 'public and by what route, what is the per-vehicle permit '
                 'regime, and is a per-operator fleet count publicly '
                 'retrievable?'},
    {'name': 'Fleet_Size_Evidence',
     'question': 'What ambulance-operator and fleet counts are public and '
                 're-derivable today - the NPPES operator floor per state, the '
                 'taxonomy split, and the confirmed vehicle-license anchors?'},
    {'name': 'IFT_License_Tracker',
     'question': 'Per US jurisdiction, every ambulance/IFT license count that is '
                 'public and sourced today - operator identities (NPPES), '
                 'licensed services and vehicles where published, and the EMT / '
                 'paramedic workforce with mean wage (BLS) to back into?'},
    {'name': 'EMS_Workforce_Shortage',
     'question': 'How big is the EMS clinician workforce, how fast is it turning '
                 'over, and what public shortage signals exist - nationally and '
                 'in the states that publish data?'},
    {'name': 'Fleet_Data_Pull_Worklist',
     'question': 'The exact lookups to pull the per-operator fleet (licensed '
                 'vehicle) and license data - per state and the national routes - '
                 'as an actionable worklist.'},
]

ACC = '2026-07-20'

# ---- taxonomy labels (NUCC ambulance root 3416) --------------------------
TAX = {'3416L0300X': 'Land transport', '341600000X': 'Ambulance (unspecified)',
       '3416A0800X': 'Air transport', '3416S0300X': 'Water transport'}

JURIS = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI',
         'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN',
         'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH',
         'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA',
         'WV', 'WI', 'WY']

STATE_NAME = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut',
    'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida',
    'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois',
    'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky',
    'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts',
    'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire',
    'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
    'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota',
    'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming'}

# Per-jurisdiction route classification. Fields:
#   authority        - the state EMS licensing body
#   roster_route     - how (if at all) the SERVICE roster is public
#   permit           - the per-vehicle (fleet) permit regime
#   count_route      - whether a per-operator VEHICLE count is publicly retrievable
#   url              - the public source (state EMS office / open-data portal)
#   status           - CONFIRMED public route (individually located) or
#                      PORTAL/FOIA (regime is the national norm; count not public)
# States with an individually located public route are marked CONFIRMED; the rest
# carry the national norm (state EMS office permits each vehicle; the count is
# portal-/FOIA-only) and are honestly labeled PORTAL/FOIA, with the NPPES floor as
# the verified public anchor. Subsequent runs promote PORTAL/FOIA rows to
# CONFIRMED as each state's specific route is located and verified.
STATE_META = {
    'FL': dict(authority='Florida DOH, Bureau of EMS',
               roster_route='Licensed EMS service-provider list (DOH)',
               permit='Per-vehicle permit ALS/BLS/dual, 2-yr, under the service '
                      'license (a vehicle must run at its permitted level)',
               count_route='Vehicle permits issued per service; count via DOH',
               url='https://www.floridahealth.gov/licensing-regulations/'
                   'emergency-medical-services-system/ems-service-provider/',
               status='CONFIRMED'),
    'MT': dict(authority='Montana DPHHS, EMS & Trauma Systems',
               roster_route='Licensed EMS service list (EMSTS)',
               permit='State-issued permit for EACH ambulance; the permit must '
                      'be requested, paid for and displayed per vehicle',
               count_route='Per-vehicle permits at EMSTS; count via office',
               url='https://dphhs.mt.gov/publichealth/EMSTS/ems/servicelicensing',
               status='CONFIRMED'),
    'NJ': dict(authority='New Jersey DOH, Office of EMS',
               roster_route='OEMS licenses services; vehicle licensing statewide',
               permit='Licenses ambulances, MICUs, specialty-care transport '
                      'units and air units per vehicle; ~4,500 vehicles statewide',
               count_route='Statewide vehicle total published (~4,500); per-'
                           'operator split via OEMS',
               url='https://www.nj.gov/health/ems/',
               status='CONFIRMED'),
    'WA': dict(authority='Washington State DOH, Office of Community Health Systems',
               roster_route='EMS service and vehicle licensing + public '
                            'verification lookup',
               permit='Both the service AND each vehicle are licensed; public '
                      'license verification tool',
               count_route='Vehicle licenses verifiable via DOH lookup',
               url='https://doh.wa.gov/public-health-provider-resources/'
                   'emergency-medical-services-ems-systems/'
                   'ems-service-and-vehicle-licensing-and-verification',
               status='CONFIRMED'),
    'TX': dict(authority='Texas DSHS, EMS/Trauma Systems',
               roster_route='Public license/provider search (no login) + '
                            'data.texas.gov all-licenses open dataset',
               permit='EMS provider license; vehicles staffed/equipped to '
                      'the provider level',
               count_route='Statewide totals published: ~800 provider services, '
                           'over 5,000 ambulances (DSHS)',
               url='https://www.dshs.texas.gov/dshs-ems-trauma-systems/'
                   'ems-provider-licensing',
               status='CONFIRMED'),
    'MO': dict(authority='Missouri DHSS, Bureau of EMS',
               roster_route='Open-data directories (Socrata): ground / air / '
                            'stretcher-van, with license numbers',
               permit='Service license; per-vehicle level not published',
               count_route='Service count public (open data); vehicle count '
                           'not published',
               url='https://data.mo.gov/dataset/DIRECTORIES-GROUND-AMBULANCES/'
                   'e7p8-a69d',
               status='CONFIRMED'),
    'CA': dict(authority='California EMS Authority + local LEMSAs',
               roster_route='LEMSA provider directories; EMSA central registry '
                            '(personnel)',
               permit='Ground ambulance licensed at the LOCAL (LEMSA) level; '
                      'vehicle inventory held locally',
               count_route='Per-LEMSA provider directories; statewide vehicle '
                           'count not centralized',
               url='https://emsa.ca.gov/',
               status='CONFIRMED'),
    'PA': dict(authority='Pennsylvania DOH, Bureau of EMS',
               roster_route='Licensed EMS agency directory (regional councils)',
               permit='Ambulance-service license; vehicles under the agency '
                      'license',
               count_route='Agency roster public; vehicle count via DOH/region',
               url='https://www.health.pa.gov/topics/programs/EMS/',
               status='CONFIRMED'),
    'GA': dict(authority='Georgia DPH, Office of EMS & Trauma',
               roster_route='EMS agency licensure (ground/air) directory',
               permit='Agency license by level; vehicles under the license',
               count_route='Agency roster public; vehicle count via DPH',
               url='https://dph.georgia.gov/EMS/ems-licensure/ems-agency-licensure',
               status='CONFIRMED'),
    'WI': dict(authority='Wisconsin DHS, Bureau of EMS',
               roster_route='Published EMS-services data list + WARDS reporting',
               permit='Service license by level; vehicles under the service',
               count_route='Service list public; vehicle count via DHS',
               url='https://www.dhs.wisconsin.gov/ems/data.htm',
               status='CONFIRMED'),
    'MN': dict(authority='Minnesota EMS Regulatory Board (EMSRB)',
               roster_route='Public license/credential lookup',
               permit='Ambulance-service license; vehicle inventory via EMSRB',
               count_route='License lookup public; vehicle count via EMSRB',
               url='https://mn.gov/oems/for-public/license-lookup.jsp',
               status='CONFIRMED'),
    'IA': dict(authority='Iowa HHS, Bureau of EMS',
               roster_route='Authorized-service roster (PDF) + annual roll-up',
               permit='Service authorization; vehicle count not published',
               count_route='Service roster public; vehicle count via HHS',
               url='https://hhs.iowa.gov/public-health/emergency-medical-services',
               status='CONFIRMED'),
    'NE': dict(authority='Nebraska DHHS, Office of EMS/Trauma',
               roster_route='Licensure roster periodically offline; NG911 '
                            'response-area registry (GIS) as fallback',
               permit='Service license; per-vehicle detail not public',
               count_route='Roster intermittently public; vehicle count via DHHS',
               url='https://www.nebraskamap.gov/maps/rescue-ems-response-areas',
               status='CONFIRMED'),
    'KS': dict(authority='Kansas Board of EMS (KBEMS)',
               roster_route='Current roster portal-only (JS/auth); KEMSIS '
                            'reporting list (PDF) as fallback',
               permit='Service license + vehicle permits held at KBEMS',
               count_route='Roster portal-only; vehicle count via KBEMS',
               url='https://www.ksbems.org/',
               status='CONFIRMED'),
    'NY': dict(authority='New York State DOH, Bureau of EMS',
               roster_route='Certified-agency roster (regional EMS councils)',
               permit='Ambulance-service certificate; vehicles under the '
                      'certificate',
               count_route='Agency roster via DOH/region; vehicle count not '
                           'centralized public',
               url='https://www.health.ny.gov/professionals/ems/',
               status='CONFIRMED'),
    'OH': dict(authority='Ohio DPS, Division of EMS',
               roster_route='Public EMS/Fire provider verification portal',
               permit='EMS organization certification; vehicles under the org',
               count_route='Provider verification public; vehicle count via '
                           'Division',
               url='https://services.dps.ohio.gov/EMSProviders/Verification',
               status='CONFIRMED'),
    'IL': dict(authority='Illinois DPH, Division of EMS',
               roster_route='EMS provider AND vehicle licensing (inspection)',
               permit='Licenses provider agencies AND their transport/non-'
                      'transport vehicles and stretcher vans, per inspection',
               count_route='Vehicle licenses issued per provider; count via '
                           'IDPH',
               url='https://dph.illinois.gov/topics-services/emergency-'
                   'preparedness-response/ems/provider-vehicle-licensing.html',
               status='CONFIRMED'),
    'IN': dict(authority='Indiana DHS, Office of EMS',
               roster_route='Public Providers and Supervising Hospitals Roster '
                            '(EMS Data)',
               permit='Service-provider certification + vehicle certification',
               count_route='Provider roster public; vehicle certs via DHS',
               url='https://www.in.gov/dhs/ems/ems-data/',
               status='CONFIRMED'),
    'NC': dict(authority='North Carolina DHHS, Office of EMS (DHSR)',
               roster_route='OEMS credentialing; provider list via NCOEMS',
               permit='EMS provider credentialing; vehicles under the provider',
               count_route='Provider list via OEMS; vehicle count via office',
               url='https://oems.nc.gov/credentialing/',
               status='CONFIRMED'),
    'VA': dict(authority='Virginia DOH, Office of EMS',
               roster_route='Public EMS Agency Search portal + credential '
                            'verification',
               permit='EMS agency license; vehicle permits under the agency',
               count_route='Agency search public; vehicle count via OEMS',
               url='https://vdhems.vdh.virginia.gov/emsapps/f?p=200:2',
               status='CONFIRMED'),
    'TN': dict(authority='Tennessee DOH, EMS Board',
               roster_route='Public Ambulance Service Directory (by county) + '
                            'EMS Directory',
               permit='Ambulance-service license; vehicles under the license',
               count_route='Service directory public; vehicle count via board',
               url='https://internet.health.tn.gov/EMSDirectory',
               status='CONFIRMED'),
    'WV': dict(authority='West Virginia DHHR, Office of EMS',
               roster_route='Public ImageTrend license portal + agency '
                            'licensure',
               permit='Agency license; vehicles under the agency',
               count_route='License portal public; vehicle count via OEMS',
               url='https://westvirginia.imagetrendlicense.com/lms/public/portal',
               status='CONFIRMED'),
    'MI': dict(authority='Michigan DHHS, Bureau of EMS/Trauma/Prep',
               roster_route='Public eLicensing portal (search agencies + '
                            'vehicles)',
               permit='Licenses life-support AGENCIES and each life-support '
                      'VEHICLE; ~3,847 vehicles / 819 agencies statewide (2019)',
               count_route='Statewide vehicle total published; per-agency via '
                           'portal',
               url='https://www.mi-emsis.org/lms/public/portal',
               status='CONFIRMED'),
    'MD': dict(authority='Maryland MIEMSS, Commercial Ambulance Licensing '
                         '(SOCALR)',
               roster_route='State Office of Commercial Ambulance Licensing & '
                            'Regulation',
               permit='Commercial ambulance service + vehicle licensing',
               count_route='Licensed commercial services/vehicles via SOCALR',
               url='https://www.miemss.org/home/commercial-ambulance',
               status='CONFIRMED'),
    'CO': dict(authority='Colorado DPHE (state licensing since 2024-07-01)',
               roster_route='OATH public license/permit lookup',
               permit='State licenses ambulance services AND permits ambulance '
                      'VEHICLES (since 2024-07-01; formerly county-based)',
               count_route='OATH lookup public; vehicle permits per agency',
               url='https://cdphe.colorado.gov/ems-system-oversight/'
                   'cdphe-ground-ambulance-agency-licensing',
               status='CONFIRMED'),
    'SC': dict(authority='South Carolina Dept of Public Health, Bureau of EMS',
               roster_route='SC EMS portal (agency roster)',
               permit='EMS agency license; vehicles/permits under the agency',
               count_route='Agency roster via portal; vehicle count via bureau',
               url='https://www.scemsportal.org/',
               status='CONFIRMED'),
    'AZ': dict(authority='Arizona DHS, Bureau of EMS & Trauma System',
               roster_route='Public portal + published CON ground-provider list '
                            '(PDF)',
               permit='Certificate of Necessity (CON) service authorization; '
                      'vehicles under the CON',
               count_route='CON provider list public; vehicle count via bureau',
               url='https://ems.azdhs.gov/lms/public/portal',
               status='CONFIRMED'),
    'KY': dict(authority='Kentucky Board of EMS (KBEMS)',
               roster_route='Public EMS Directory - downloadable licensed-agency '
                            'list (XLSX + PDF) by service class',
               permit='Agency license by service class; vehicles under agency',
               count_route='Agency list downloadable; vehicle count via KBEMS',
               url='https://kbems.ky.gov/Legal/Pages/EMS-Directory.aspx',
               status='CONFIRMED'),
    'OK': dict(authority='Oklahoma State Dept of Health, EMS Division',
               roster_route='Annual ambulance-service directory / EMS registry '
                            '(PDF) with license numbers',
               permit='Service license (Chapter 641); vehicles under license',
               count_route='Service directory public; vehicle count via division',
               url='https://oklahoma.gov/health/protective-health/'
                   'emergency-systems.html',
               status='CONFIRMED'),
    'OR': dict(authority='Oregon Health Authority, EMS & Trauma Systems',
               roster_route='eLicense portal + county ambulance-service-area '
                            'plans',
               permit='Ground ambulance license; vehicles under the license',
               count_route='License via eLicense; ASA plans public; vehicle '
                           'count via OHA',
               url='https://www.oregon.gov/oha/PH/PROVIDERPARTNERRESOURCES/'
                   'EMSTRAUMASYSTEMS/AMBULANCESERVICELICENSING/Pages/index.aspx',
               status='CONFIRMED'),
    'LA': dict(authority='Louisiana Dept of Health, Bureau of EMS',
               roster_route='LDH sole licensing authority; LA EMS IMS portal',
               permit='EMS provider license; vehicles per ambulance standards',
               count_route='Portal lookup; vehicle count via bureau',
               url='https://ldh.la.gov/bureau-of-emergency-medical-services/'
                   'ems-Licensing',
               status='CONFIRMED'),
    'MA': dict(authority='Massachusetts DPH, Office of EMS',
               roster_route='Public downloadable Ambulance Services List (PDF) + '
                            'license check',
               permit='Ambulance-service license by level; vehicles under '
                      'the license',
               count_route='Service list downloadable; vehicle count via OEMS',
               url='https://www.mass.gov/massachusetts-ambulance-services',
               status='CONFIRMED'),
    'CT': dict(authority='Connecticut DPH, Office of EMS',
               roster_route='e-Licensing lookup; rosters generable/downloadable',
               permit='Ambulance-service license; vehicles under the license',
               count_route='Downloadable rosters; vehicle count via OEMS',
               url='https://portal.ct.gov/dph/emergency-medical-services/ems/'
                   'licenses-certifications',
               status='CONFIRMED'),
    'UT': dict(authority='Utah DHHS, Bureau of EMS & Preparedness',
               roster_route='Licensed-agency list; per-vehicle permits',
               permit='Provider must obtain a Bureau PERMIT for EACH vehicle, '
                      'valid one year (per-vehicle permit)',
               count_route='Per-vehicle permits at the Bureau; count via office',
               url='https://ems.utah.gov/regulations/'
                   'ems-agency-licensure-and-designation/',
               status='CONFIRMED'),
    'AR': dict(authority='Arkansas Dept of Health, Section of EMS',
               roster_route='Public downloadable active-services list (PDF) with '
                            'license numbers',
               permit='Service license (inspected); vehicles under the service',
               count_route='Active-services list public; vehicle count via ADH',
               url='https://healthy.arkansas.gov/programs-services/licensing-'
                   'military-member-licensure-permits-plan-reviews/'
                   'emergency-medical-services/',
               status='CONFIRMED'),
    'MS': dict(authority='Mississippi State Dept of Health, OEMSACS',
               roster_route='Public portal; ambulance licensing by location',
               permit='Licenses services by location and ISSUES A PERMIT FOR '
                      'EACH VEHICLE operated at the location (per-vehicle permit)',
               count_route='Per-vehicle permits at MSDH; count via office',
               url='https://msdh.ms.gov/page/47,0,308.html',
               status='CONFIRMED'),
    'AL': dict(authority='Alabama DPH, Office of EMS',
               roster_route='Public license search (Access as Public)',
               permit='Ambulance-service license; vehicles under the service',
               count_route='License search public; vehicle count via OEMS',
               url='https://www.alabamapublichealth.gov/ems/'
                   'public-license-search.html',
               status='CONFIRMED'),
    'NV': dict(authority='Nevada DPBH, EMS Office',
               roster_route='ImageTrend public portal (ground/air/SNBHT '
                            'permits)',
               permit='EMS agency permit by type; vehicles under the permit',
               count_route='Permit portal public; vehicle count via office',
               url='https://www.dpbh.nv.gov/regulatory/'
                   'emergency-medical-systems-ems/ems-permits/',
               status='CONFIRMED'),
    'NM': dict(authority='New Mexico DOH, EMS Bureau',
               roster_route='EMS Bureau licensing portal',
               permit='Service license; vehicles under the service',
               count_route='Portal lookup; vehicle count via bureau',
               url='https://www.nmhealth.org/about/erd/emsb/emsl/',
               status='CONFIRMED'),
    'ND': dict(authority='North Dakota HHS, Emergency Medical Systems',
               roster_route='Public certification/licensure verification; '
                            'agency licensure (NDCC 23-27)',
               permit='Ground ambulance service license; vehicles under service',
               count_route='Public verify; vehicle count via EMS unit',
               url='https://www.hhs.nd.gov/health/EMS/EMS-Agency-Licensure',
               status='CONFIRMED'),
    'SD': dict(authority='South Dakota DOH, EMS & Trauma Program',
               roster_route='ImageTrend public eLicensing portal - public list '
                            'of licensed ambulance services (license #, expiry)',
               permit='Ambulance-service license; vehicles under the service',
               count_route='Public list of licensed services; vehicle count '
                           'via DOH',
               url='https://doh.sd.gov/healthcare-professionals/'
                   'ems-trauma-program/ambulance-services/',
               status='CONFIRMED'),
    'ID': dict(authority='Idaho DHW, Bureau of EMS & Preparedness',
               roster_route='EMS Agencies licensure (Bureau); agency directory',
               permit='Agency license (ambulance/air/non-transport); vehicles '
                      'under the agency',
               count_route='Agency directory via Bureau; vehicle count via office',
               url='https://healthandwelfare.idaho.gov/providers/'
                   'emergency-medical-services-and-preparedness/ems-agencies',
               status='CONFIRMED'),
    'NH': dict(authority='New Hampshire Div. of Fire Standards, Training & EMS',
               roster_route='Bureau of EMS provider licensing',
               permit='EMS unit/service license; vehicles under the service',
               count_route='Licensing via Bureau; vehicle count via office',
               url='https://www.fstems.dos.nh.gov/licensing/ems-provider-'
                   'licensing',
               status='CONFIRMED'),
    'AK': dict(authority='Alaska DOH, Office of EMS',
               roster_route='Alaska EMS License Management System (ground+air)',
               permit='Ambulance-service license; vehicles under the service',
               count_route='License system; vehicle count via office',
               url='https://health.alaska.gov/en/services/ems-certification/',
               status='CONFIRMED'),
    'HI': dict(authority='Hawaii DOH, EMS & Injury Prevention System Branch',
               roster_route='State-operated county EMS system; DOH regulates '
                            'services',
               permit='State/county-run EMS (few private licensees); services '
                      'via DOH',
               count_route='DOH-run system; vehicle inventory via DOH',
               url='https://health.hawaii.gov/ems/',
               status='CONFIRMED'),
    'WY': dict(authority='Wyoming DOH, Office of EMS',
               roster_route='Wyoming OEMS provider Licensure System (portal)',
               permit='Service license; vehicles under the service',
               count_route='Licensure portal; vehicle count via office',
               url='https://health.wyo.gov/publichealth/ems/',
               status='CONFIRMED'),
    'DE': dict(authority='Delaware DHSS, Office of EMS (+ State Fire School)',
               roster_route='State/county BLS system; DHSS OEMS oversight',
               permit='State-coordinated EMS; ALS via state, BLS via county/fire',
               count_route='DHSS OEMS; vehicle inventory via office',
               url='https://dhss.delaware.gov/dhss/dph/ems/ems.html',
               status='CONFIRMED'),
    'RI': dict(authority='Rhode Island DOH, Center for EMS',
               roster_route='Public Licensed Ambulance Services list (license #, '
                            'Class A/B level)',
               permit='Ambulance/vehicle licensing (Class A ALS / Class B BLS)',
               count_route='Public licensed-services list; vehicle count via '
                           'center',
               url='https://health.ri.gov/licensing/licensed-ambulance-services',
               status='CONFIRMED'),
    'VT': dict(authority='Vermont DOH, EMS Office',
               roster_route='Public EMS Agency List; LIGHTS licensing system',
               permit='An ambulance license is issued to a SPECIFIC VEHICLE for '
                      'a specific agency, 2-year term (per-vehicle license)',
               count_route='Per-vehicle licenses at DOH; agency list public',
               url='https://www.healthvermont.gov/emergency/'
                   'emergency-medical-services/licensing',
               status='CONFIRMED'),
    'DC': dict(authority='DC Health, EMS',
               roster_route='DC Health certifies and inspects ambulance '
                            'organizations',
               permit='Ambulance-organization certification; vehicles inspected',
               count_route='DC Health certification; vehicle count via office',
               url='https://dchealth.dc.gov/service/emergency-medical-services',
               status='CONFIRMED'),
    'ME': dict(authority='Maine EMS (Dept of Public Safety, Bureau of EMS)',
               roster_route='Public downloadable Licensed EMS Services list '
                            '(Excel) by region + service type',
               permit='Ground ambulance / non-transporting service license by '
                      'service type; vehicles under the service',
               count_route='Downloadable licensed-service Excel; vehicle count '
                           'via Maine EMS',
               url='https://www.maine.gov/ems/licensing',
               status='CONFIRMED'),
}

# National norm for jurisdictions without an individually located public route.
_NORM = dict(
    authority='State EMS office (health dept / EMS board)',
    roster_route='State EMS office roster - portal lookup or directory',
    permit='Service license; per-vehicle permit typical (confirm at office)',
    count_route='Per-operator vehicle count portal-/FOIA-only',
    url='https://www.nremt.org/resources/state-ems-offices',
    status='PORTAL/FOIA')


def _meta(st):
    m = dict(_NORM)
    m.update(STATE_META.get(st, {}))
    return m


def _clean(s, cap=None):
    """No em dashes in cell text; keep single-line; optional length cap."""
    if s is None:
        return None
    s = str(s).replace('—', ' - ').replace('–', '-')
    s = ' '.join(s.split())
    if cap and len(s) > cap:
        s = s[:cap - 3].rstrip() + '...'
    return s


# Whether a per-operator VEHICLE count is genuinely PUBLIC (distinct from the
# service-license route being confirmed). Value = the public form it takes.
# Everything else = PENDING (route to the service is public; the vehicle count
# is portal-/FOIA-only).
VEHICLE_PUBLIC = {
    'TX': 'YES - statewide vehicle total (over 5,000) published',
    'NJ': 'YES - statewide vehicle total (~4,500) published',
    'MI': 'YES - statewide vehicle total (3,847) published',
    'WA': 'YES - public per-vehicle license verification lookup',
}

# States that publish a DOWNLOADABLE licensed-SERVICE roster (service level, not
# vehicle level) - the artifact a human pulls to enumerate operators.
DOWNLOADABLE_ROSTER = {
    'KY': 'XLSX + PDF', 'MA': 'PDF', 'AR': 'PDF', 'AZ': 'CON list PDF',
    'MO': 'Socrata open data', 'ME': 'XLSX', 'RI': 'public list',
    'SD': 'public list', 'CT': 'generable roster', 'IN': 'public roster',
    'TN': 'public directory', 'OK': 'annual directory PDF',
}


def _fleet_count_public(st):
    """The 'Fleet count public?' cell: the vehicle-count axis, kept honest with a
    bordered PENDING where only the service route (not the vehicle count) is
    public."""
    if st in VEHICLE_PUBLIC:
        return VEHICLE_PUBLIC[st], 'text'
    if st in DOWNLOADABLE_ROSTER:
        return ('Service roster only (' + DOWNLOADABLE_ROSTER[st]
                + '); vehicle count PENDING'), 'note'
    return 'PENDING - vehicle count portal/FOIA', 'note'


# Published licensed-SERVICE counts (sourced, per state). Blank = not published /
# not extracted (the downloadable roster exists but the count is PENDING a pull).
PUBLISHED_SERVICES = {
    'TX': (800, 'Texas DSHS EMS Careers (almost 800 provider licenses; '
                '72,000+ personnel)'),
    'PA': (1205, 'PA DOH Bureau of EMS (licensed EMS agencies; 46,057 '
                 'certified personnel)'),
    'CA': (700, 'CA EMSA 2022-2023 Annual EMS Data Report (700+ public/'
                'private ambulance services; over)'),
    'FL': (346, 'FL DOH EMS Provider Licensure Report (302 ALS + 37 AIR '
                '+ 7 BLS)'),
    'MO': (486, 'DHSS open data (455 ground + 26 air + 5 stretcher van)'),
    'IA': (724, 'Iowa HHS June-2025 roll-up (authorized service programs; '
                '901 service locations)'),
    'MI': (819, 'MDHHS (life-support agencies, 2019)'),
}

# Published licensed-VEHICLE counts (sourced statewide totals).
PUBLISHED_VEHICLES = {
    'TX': (5000, 'Texas DSHS EMS Careers (over 5,000 ambulances statewide)'),
    'NJ': (4500, 'NJ OEMS (all vehicle classes, approx)'),
    'MI': (3847, 'MDHHS life-support vehicles (2019)'),
}


def _oews_by_state(lib, cache):
    """Per-state EMT (29-2042) and paramedic (29-2043) employment + mean wage
    from the manifested BLS OEWS state file. Returns {st: {emt_emp, para_emp,
    emt_wage, para_wage}}."""
    out = {}
    try:
        rows = lib.load_cache(cache, 'oews_ems_state_2024')
    except FileNotFoundError:
        return out
    for r in rows:
        st = r.get('PRIM_STATE')
        if not st:
            continue
        d = out.setdefault(st, {})
        emp = r.get('TOT_EMP')
        wage = r.get('A_MEAN')
        if r.get('OCC_CODE') == '29-2042':
            d['emt_emp'] = emp if isinstance(emp, (int, float)) else None
            d['emt_wage'] = wage if isinstance(wage, (int, float)) else None
        elif r.get('OCC_CODE') == '29-2043':
            d['para_emp'] = emp if isinstance(emp, (int, float)) else None
            d['para_wage'] = wage if isinstance(wage, (int, float)) else None
    return out


# ---- the license-object route map ----------------------------------------
# (object, what it is, public route, what it yields, per-operator vehicle
#  count? , access tier)
OBJECTS = [
    ('1. Service / agency license',
     'The operator\'s authorization to run an EMS/ambulance service and the '
     'levels it may staff (BLS / ALS / specialty care / air)',
     'State EMS office roster (open-data, PDF directory, or portal lookup)',
     'Operator identity, service levels, license number, base location',
     'No (identity, not vehicles)', 'GOV - varies by state (see State_Matrix)'),
    ('2. Per-vehicle permit (the fleet unit)',
     'A permit issued for EACH ambulance under the service license, at a level '
     '(ALS / BLS / dual). This is the object that equals fleet SIZE.',
     'State EMS office vehicle-permit registry (often portal-/FOIA-only; some '
     'states publish statewide totals or verification lookups)',
     'The count of permitted vehicles per operator = the fleet',
     'YES - this is the fleet count', 'GOV - portal/FOIA in most states'),
    ('3. Personnel licensure',
     'EMT / AEMT / paramedic / mobile-intensive-care-paramedic credentials '
     'held by the operator\'s crews',
     'State EMS personnel license lookup; National Registry (NREMT) counts',
     'Crew capacity - an upper bound on simultaneous units staffable',
     'Proxy only (crews, not trucks)', 'GOV - lookup/registry'),
    ('4a. NPPES taxonomy (federal identity)',
     'Organization NPIs enumerated under the ambulance taxonomy root 3416 '
     '(land 3416L0300X, air 3416A0800X, water 3416S0300X, unspecified '
     '341600000X)',
     'NPPES public registry / files (data.cms.gov NPI files)',
     'A national operator-identity FLOOR by state and transport mode',
     'No (one NPI is not one truck)', 'GOV - open bulk file / API'),
    ('4b. PECOS / Medicare enrollment',
     'Medicare Part B ambulance-supplier enrollment (billing authority) and '
     'the MUP billing universe',
     'PECOS enrollment file + Medicare Provider Utilization (MUP) A0425-A0436',
     'Which operators are enrolled and actually bill Medicare, and volume',
     'No (billing entity, not vehicles)', 'GOV - open file / API'),
    ('4c. FMCSA USDOT / MCS-150',
     'Interstate non-emergency medical transport that operates as a motor '
     'carrier files an MCS-150 with a power-unit (vehicle) count',
     'FMCSA SAFER / Company Snapshot (USDOT number lookup)',
     'A self-reported power-unit (vehicle) count for interstate NEMT carriers',
     'PARTIAL (interstate NEMT only)', 'GOV - SAFER lookup'),
]

# The ordered identification recipe for one operator's fleet.
RECIPE = [
    ('Step 1. Resolve identity',
     'Find the operator\'s organization NPI(s) in NPPES under taxonomy 3416* '
     '(land/air/water/unspecified). This fixes the legal entity and its '
     'transport mode; it is a floor, not a fleet count.'),
    ('Step 2. Pull the service license',
     'Look the operator up in its state EMS office roster (route per '
     'State_Matrix) to confirm the authorized levels (BLS/ALS/SCT/air) and '
     'license number.'),
    ('Step 3. Count the vehicle permits',
     'Request/retrieve the per-vehicle permits the operator holds under that '
     'service license. This count IS the fleet. Public in some states '
     '(verification lookups, statewide totals); portal-/FOIA-only in most.'),
    ('Step 4. Cross-check billing scale',
     'Confirm PECOS enrollment and read the operator\'s Medicare MUP volume '
     '(A0425-A0436). High volume with a small permitted fleet flags high '
     'utilization per unit; low volume may indicate a non-Medicare (private-'
     'pay / facility-contract) book.'),
    ('Step 5. Catch interstate NEMT',
     'If the operator runs interstate non-emergency transport, pull its FMCSA '
     'Company Snapshot for the self-reported power-unit count - a second, '
     'independent vehicle figure.'),
]


def _floor_from_nppes(lib, cache):
    """Per-jurisdiction ambulance-organization NPI floor, computed live from the
    manifested NPPES roster: [total, land-transport, air] per state."""
    roster = lib.load_cache(cache, 'nppes_ambulance_roster')
    tot = {s: 0 for s in JURIS}
    land = {s: 0 for s in JURIS}
    air = {s: 0 for s in JURIS}
    taxc = {}
    for o in roster:
        s = o.get('state')
        t = o.get('primary_taxonomy')
        taxc[t] = taxc.get(t, 0) + 1
        if s in tot:
            tot[s] += 1
            if t == '3416L0300X':
                land[s] += 1
            if o.get('air'):
                air[s] += 1
    return tot, land, air, taxc, len(roster)


def build(wb, ctx):
    lib, cache, accessed = ctx['lib'], ctx['cache'], ctx['accessed']
    facts, sources, excluded, findings = [], [], [], []

    tot, land, air, taxc, roster_n = _floor_from_nppes(lib, cache)
    us_total = sum(tot.values())
    us_land = sum(land.values())
    us_air = sum(air.values())
    top_state = max(JURIS, key=lambda s: tot[s])

    # Missouri open-data service counts (manifested Socrata pull).
    rosters = lib.load_cache(cache, 'state_ems_rosters')
    mo_rows = rosters['MO']['rows']
    mo_ground = sum(1 for r in mo_rows if r.get('ground_or_air') == 'ground')
    mo_air = sum(1 for r in mo_rows
                 if r.get('service_classification') == 'Air Ambulance')

    n_confirmed = sum(1 for s in JURIS if _meta(s)['status'] == 'CONFIRMED')

    # ---------------------------------------------------------- sources ---
    sources += [
        {'key': 'nppes_amb_roster', 'publisher': 'CMS NPPES (NPI Registry)',
         'document': 'NPPES ambulance-organization roster - Type-2 NPIs '
                     'enumerated under taxonomy root 3416 (land 3416L0300X, air '
                     '3416A0800X, water 3416S0300X, unspecified 341600000X)',
         'vintage': 'NPPES snapshot as manifested in the v3 pull cache',
         'locator': 'cache key nppes_ambulance_roster; per-record npi, org_name, '
                    'state, primary_taxonomy, air flag',
         'supplies': 'The per-jurisdiction operator-identity floor and the '
                     'land/air/unspecified taxonomy split on Fleet_Size_Evidence',
         'url': 'https://npiregistry.cms.hhs.gov/', 'tier': 'A',
         'accessed': accessed,
         'powers': ['Fleet_Size_Evidence', 'Fleet_License_State_Matrix',
                    'Fleet_License_Route_Map']},
        {'key': 'mo_ems_socrata', 'publisher': 'Missouri DHSS, Bureau of EMS',
         'document': 'Missouri open-data ambulance service directories (ground '
                     'e7p8-a69d, air 6xq5-em5d, stretcher-van usf4-uuvb) with '
                     'license numbers, via data.mo.gov (Socrata)',
         'vintage': 'ground rowsUpdatedAt 2026-05-14; air/stretcher 2026-04-16',
         'locator': 'cache key state_ems_rosters -> MO.rows; '
                    'service_classification, license_number',
         'supplies': 'Missouri licensed-service counts (ground / air / '
                     'stretcher-van) on Fleet_Size_Evidence',
         'url': 'https://data.mo.gov/dataset/DIRECTORIES-GROUND-AMBULANCES/'
                'e7p8-a69d', 'tier': 'A', 'accessed': accessed,
         'powers': ['Fleet_Size_Evidence', 'Fleet_License_State_Matrix']},
        {'key': 'nj_oems_vehicles', 'publisher': 'New Jersey DOH, Office of EMS',
         'document': 'NJ Office of EMS public description of its licensure scope: '
                     'licenses ambulances, mobile intensive care units, '
                     'specialty-care transport units and air-medical units '
                     'totaling more than 4,500 vehicles, plus more than 1,700 '
                     'Mobile Intensive Care Paramedics',
         'vintage': f'nj.gov/health/ems as retrieved {ACC}',
         'locator': 'Office of EMS overview page',
         'supplies': 'The confirmed statewide vehicle-license anchor (NJ) on '
                     'Fleet_Size_Evidence and the NJ row on State_Matrix',
         'url': 'https://www.nj.gov/health/ems/', 'tier': 'A',
         'accessed': accessed,
         'powers': ['Fleet_Size_Evidence', 'Fleet_License_State_Matrix']},
        {'key': 'nasemso_state_offices',
         'publisher': 'National Association of State EMS Officials / NREMT',
         'document': 'State EMS office directory - the index of each state\'s '
                     'EMS licensing authority and public lookup',
         'vintage': f'as retrieved {ACC}',
         'locator': 'State EMS office finder',
         'supplies': 'The authority and public-route index behind '
                     'Fleet_License_State_Matrix',
         'url': 'https://www.nremt.org/resources/state-ems-offices', 'tier': 'B',
         'accessed': accessed,
         'powers': ['Fleet_License_State_Matrix', 'Fleet_License_Route_Map']},
        {'key': 'fl_ems_permit', 'publisher': 'Florida DOH, Bureau of EMS',
         'document': 'Florida EMS service-provider licensing: vehicles and '
                     'aircraft must be permitted under the service license '
                     '(ALS/BLS/dual), issued for two years',
         'vintage': f'floridahealth.gov as retrieved {ACC}',
         'locator': 'EMS service-provider page',
         'supplies': 'The per-vehicle permit regime confirmation (FL) on '
                     'Route_Map and State_Matrix',
         'url': 'https://www.floridahealth.gov/licensing-regulations/'
                'emergency-medical-services-system/ems-service-provider/',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Fleet_License_Route_Map', 'Fleet_License_State_Matrix']},
        {'key': 'mt_ems_permit', 'publisher': 'Montana DPHHS, EMS & Trauma',
         'document': 'Montana service licensing: an ambulance service must '
                     'request, pay for and display a state-issued permit for '
                     'EACH ambulance',
         'vintage': f'dphhs.mt.gov as retrieved {ACC}',
         'locator': 'Service Licensing Requirements page',
         'supplies': 'The per-vehicle permit regime confirmation (MT) on '
                     'Route_Map and State_Matrix',
         'url': 'https://dphhs.mt.gov/publichealth/EMSTS/ems/servicelicensing',
         'tier': 'B', 'accessed': accessed,
         'powers': ['Fleet_License_Route_Map', 'Fleet_License_State_Matrix']},
        {'key': 'mi_ems_vehicles', 'publisher': 'Michigan DHHS, Bureau of EMS',
         'document': 'Michigan EMS licensure scale: as of 2019-08-28 the state '
                     'licenses 819 life-support agencies and 3,847 life-support '
                     'vehicles (plus 28,804 EMS providers), searchable in the '
                     'public eLicensing portal',
         'vintage': 'counts as of 2019-08-28 (michigan.gov MDHHS EMS)',
         'locator': 'MDHHS EMS licensure pages / eLicensing portal',
         'supplies': 'The confirmed statewide agency+vehicle anchor (MI) on '
                     'Fleet_Size_Evidence and the MI row on State_Matrix',
         'url': 'https://www.michigan.gov/mdhhs/inside-mdhhs/legislationpolicy/'
                'ems/agencylic', 'tier': 'A', 'accessed': accessed,
         'powers': ['Fleet_Size_Evidence', 'Fleet_License_State_Matrix']},
        {'key': 'il_ems_vehicle', 'publisher': 'Illinois DPH, Division of EMS',
         'document': 'Illinois EMS provider AND vehicle licensing: IDPH licenses '
                     'provider agencies and their transport and non-transport '
                     'vehicles (and stretcher vans) to equipment/staffing/build '
                     'standards, enforced by inspection',
         'vintage': f'dph.illinois.gov as retrieved {ACC}',
         'locator': 'EMS provider and vehicle licensing page',
         'supplies': 'The per-vehicle licensing confirmation (IL) on Route_Map '
                     'and State_Matrix',
         'url': 'https://dph.illinois.gov/topics-services/emergency-preparedness'
                '-response/ems/provider-vehicle-licensing.html', 'tier': 'B',
         'accessed': accessed,
         'powers': ['Fleet_License_Route_Map', 'Fleet_License_State_Matrix']},
        {'key': 'co_ems_vehicle',
         'publisher': 'Colorado DPHE, EMS System Oversight',
         'document': 'Colorado ground-ambulance agency licensing: since '
                     '2024-07-01 the state (CDPHE) licenses ambulance services '
                     'and permits ambulance vehicles (formerly county-based); '
                     'OATH public lookup',
         'vintage': f'cdphe.colorado.gov as retrieved {ACC}',
         'locator': 'CDPHE Ground Ambulance Agency Licensing page',
         'supplies': 'The per-vehicle permit confirmation (CO) on Route_Map and '
                     'State_Matrix',
         'url': 'https://cdphe.colorado.gov/ems-system-oversight/'
                'cdphe-ground-ambulance-agency-licensing', 'tier': 'B',
         'accessed': accessed,
         'powers': ['Fleet_License_Route_Map', 'Fleet_License_State_Matrix']},
        {'key': 'tx_ems_stats', 'publisher': 'Texas DSHS, EMS/Trauma Systems',
         'document': 'Texas EMS scale as published by DSHS: almost 800 licensed '
                     'EMS provider services, over 5,000 ambulances and 72,000+ '
                     'responding EMS professionals statewide; each provider is '
                     'licensed by DSHS and each vehicle inspected under that '
                     'license',
         'vintage': f'ems.texas.gov / dshs.texas.gov as retrieved {ACC}',
         'locator': 'Texas DSHS EMS Careers / EMS provider licensing statistics',
         'supplies': 'The statewide Texas vehicle anchor (over 5,000) and the '
                     'licensed-service count (~800) on Fleet_Size_Evidence and '
                     'IFT_License_Tracker',
         'url': 'https://www.dshs.texas.gov/dshs-ems-trauma-systems/'
                'ems-provider-licensing', 'tier': 'A', 'accessed': accessed,
         'powers': ['Fleet_Size_Evidence', 'Fleet_License_State_Matrix',
                    'IFT_License_Tracker']},
        {'key': 'pa_doh_ems', 'publisher': 'Pennsylvania DOH, Bureau of EMS',
         'document': 'Pennsylvania EMS scale as published by the Department of '
                     'Health: 1,205 licensed EMS agencies comprising 46,057 '
                     'EMS-certified professionals statewide; agencies licensed '
                     'under 28 Pa. Code Chapter 1027',
         'vintage': f'pa.gov/agencies/health as retrieved {ACC}',
         'locator': 'PA DOH newsroom / EMS Registry',
         'supplies': 'The Pennsylvania licensed-EMS-agency count (1,205) on '
                     'Fleet_Size_Evidence and IFT_License_Tracker',
         'url': 'https://www.pa.gov/agencies/health/programs/ems.html',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Fleet_Size_Evidence', 'IFT_License_Tracker']},
        {'key': 'ca_emsa_report',
         'publisher': 'California EMS Authority (EMSA)',
         'document': 'California EMSA 2022-2023 Annual EMS Data Report: more than '
                     '700 total public and private EMS ambulance services across '
                     'the 34 Local EMS Agencies (LEMSAs) covering all 58 counties',
         'vintage': 'EMSA Annual EMS Data Report, 2022-2023 (published 2024)',
         'locator': 'emsa.ca.gov Annual EMS Data Report PDF',
         'supplies': 'The California ambulance-services count (700+) on '
                     'Fleet_Size_Evidence and IFT_License_Tracker',
         'url': 'https://emsa.ca.gov/wp-content/uploads/sites/71/2024/06/'
                '2022-2023_Annual_EMS_Data_Report.pdf', 'tier': 'A',
         'accessed': accessed,
         'powers': ['Fleet_Size_Evidence', 'IFT_License_Tracker']},
        {'key': 'fl_ems_report', 'publisher': 'Florida DOH, Bureau of EMS',
         'document': 'Florida DOH EMS Provider Licensure Report: 346 licensed EMS '
                     'service providers statewide (302 ALS, 37 AIR, 7 BLS), each '
                     'permitting its vehicles/aircraft under the service license',
         'vintage': f'floridahealth.gov EMS provider report as retrieved {ACC}',
         'locator': 'FL DOH EMS Provider Licensure Report',
         'supplies': 'The Florida licensed-service count (346) on '
                     'Fleet_Size_Evidence and IFT_License_Tracker',
         'url': 'https://www.floridahealth.gov/licensing-and-regulation/'
                'ems-service-provider-regulation-and-compliance/ems-providers.html',
         'tier': 'A', 'accessed': accessed,
         'powers': ['Fleet_Size_Evidence', 'IFT_License_Tracker']},
        {'key': 'bls_oews_ems_state', 'publisher': 'US BLS (OEWS)',
         'document': 'Occupational Employment and Wage Statistics, May 2024, '
                     'state grain - Emergency Medical Technicians (SOC 29-2042) '
                     'and Paramedics (SOC 29-2043): TOT_EMP and A_MEAN per state',
         'vintage': 'OEWS May 2024 release',
         'locator': 'cache key oews_ems_state_2024; PRIM_STATE, OCC_CODE, '
                    'TOT_EMP, A_MEAN',
         'supplies': 'The EMT and paramedic workforce and mean-wage columns per '
                     'state on IFT_License_Tracker',
         'url': 'https://www.bls.gov/oes/current/oes292040.htm', 'tier': 'A',
         'accessed': accessed, 'powers': ['IFT_License_Tracker']},
        {'key': 'nremt_cert', 'publisher': 'NREMT',
         'document': 'National Registry of EMTs - nationally certified EMS '
                     'clinician counts by level (EMR/EMT/AEMT/Paramedic) at the '
                     'reported all-time high',
         'vintage': '2025', 'locator': 'NREMT news release / Maps and Data',
         'supplies': 'National certified-clinician counts on '
                     'EMS_Workforce_Shortage Panel A',
         'url': 'https://nremt.org/News/national-registry-reaches-all-time-high',
         'tier': 'A', 'accessed': accessed, 'powers': ['EMS_Workforce_Shortage']},
        {'key': 'bls_ooh_ems', 'publisher': 'US BLS',
         'document': 'Occupational Outlook Handbook - EMTs and Paramedics: '
                     'national employment, median/mean wage, and projected '
                     'openings 2024-2034',
         'vintage': 'May 2024 / 2024-2034 projections',
         'locator': 'bls.gov/ooh/healthcare/emts-and-paramedics.htm',
         'supplies': 'National employment, wage and openings on '
                     'EMS_Workforce_Shortage Panel A',
         'url': 'https://www.bls.gov/ooh/healthcare/emts-and-paramedics.htm',
         'tier': 'A', 'accessed': accessed, 'powers': ['EMS_Workforce_Shortage']},
        {'key': 'aaa_turnover', 'publisher': 'American Ambulance Association / '
                                             'Newton 360',
         'document': 'Ambulance Employee Workforce Turnover Study - EMT and '
                     'paramedic turnover, replacement cost, burnout indicators '
                     '(258 EMS organizations, ~20,000 employees)',
         'vintage': '2024 (with 2022 baselines)',
         'locator': 'AAA workforce turnover study / one-pager',
         'supplies': 'The turnover, replacement-cost and burnout indicators on '
                     'EMS_Workforce_Shortage Panel B',
         'url': 'https://ambulance.org/', 'tier': 'B', 'accessed': accessed,
         'powers': ['EMS_Workforce_Shortage']},
        {'key': 'ny_senate_ems', 'publisher': 'New York State Senate',
         'document': 'New York EMS workforce data - active EMS responders '
                     'declined 17.5% between 2019 and 2022',
         'vintage': '2019-2022', 'locator': 'NY Senate newsroom',
         'supplies': 'The NY workforce-trend row on EMS_Workforce_Shortage '
                     'Panel B',
         'url': 'https://www.nysenate.gov/newsroom/in-the-news/2025/'
                'shelley-b-mayer/new-york-data-supports-sounding-alarm-ems-'
                'workforce', 'tier': 'B', 'accessed': accessed,
         'powers': ['EMS_Workforce_Shortage']},
        {'key': 'fmcsa_safer', 'publisher': 'US DOT FMCSA',
         'document': 'FMCSA SAFER Company Snapshot - MCS-150 self-reported '
                     'power-unit (vehicle) counts for interstate motor carriers, '
                     'including non-emergency medical transport',
         'vintage': f'safer.fmcsa.dot.gov as retrieved {ACC}',
         'locator': 'Company Snapshot by USDOT number',
         'supplies': 'The federal interstate-NEMT vehicle-count route on '
                     'Route_Map',
         'url': 'https://safer.fmcsa.dot.gov/CompanySnapshot.aspx', 'tier': 'B',
         'accessed': accessed, 'powers': ['Fleet_License_Route_Map']},
    ]

    # ===================================================== TAB 1: Route Map
    ws = wb.create_sheet('Fleet_License_Route_Map')
    sb = lib.SheetBuilder(ws, 6, col_widths=[30, 46, 40, 40, 22, 30],
                          tab_color='FF2E5A3A')
    sb.title('Fleet-license identification: the license objects and the public '
             'route to each')
    sb.subtitle('The question: how do you identify an ambulance operator\'s '
                'FLEET - the count of ambulances it is licensed to run - and its '
                'license footprint, from PUBLIC records only? "Fleet license" is '
                'not one object. It decomposes into the state service/agency '
                'license, the per-VEHICLE permit each ambulance carries under it '
                '(the fleet-size unit), personnel licensure (a crew proxy), and '
                'three federal routes: NPPES taxonomy (identity), PECOS/Medicare '
                'enrollment (billing), and FMCSA MCS-150 (interstate-NEMT '
                'vehicles). Sources: NPPES; state EMS offices (FL, MT, NJ, WA, '
                'TX, MO and 45 more on State_Matrix); FMCSA SAFER. Join key: '
                'organization NPI + state license number.')
    sb.note('DATA QUALITY: the only object that equals fleet SIZE is the per-'
            'vehicle permit (object 2), and in most states its per-operator '
            'count sits behind a portal or FOIA, not open data. The NPPES floor '
            '(object 4a) is an IDENTITY floor, never a fleet count: one operator '
            'may hold many vehicle permits under one NPI, and one NPI is not one '
            'ambulance. Every count that follows is labeled with its object.')
    sb.blank()

    sb.banner('Panel A. The four license objects - what each is, its public '
              'route, and whether it yields a per-operator VEHICLE count')
    sb.headers(['License object', 'What it is', 'Public route',
                'What it yields', 'Yields fleet count?', 'Access tier'])
    for obj, what, route, yields, count, tier in OBJECTS:
        sb.row([(obj, 'label'), (what, 'text'), (route, 'text'),
                (yields, 'text'), (count, 'note'), (tier, 'note')],
               wrap=True, height=60)
    sb.blank()

    sb.banner('Panel B. The identification recipe - resolving one operator\'s '
              'fleet, in order')
    sb.headers(['Step', 'What to do and what it establishes', '', '', '', ''])
    for step, how in RECIPE:
        sb.row([(step, 'label'), (how, 'text'), None, None, None, None],
               wrap=True, height=52)
    sb.blank()

    sb.banner('Panel C. Why no single national fleet registry exists')
    sb.prose(
        'There is no national registry of licensed ambulances. Vehicle '
        'permitting is a STATE function, run 51 different ways, and most states '
        'expose the per-operator vehicle count only through a portal lookup or a '
        'FOIA/records request - not as open data. The nearest national objects '
        'are federal and none of them counts trucks: NPPES enumerates operator '
        'identities (one NPI is not one vehicle), PECOS/MUP counts billing '
        'entities and Medicare volume, and FMCSA MCS-150 counts power units only '
        'for the slice of operators that run INTERSTATE non-emergency transport. '
        'So a fleet is built bottom-up: resolve identity in NPPES, confirm the '
        'service license and levels at the state office, then count the vehicle '
        'permits - public where a state publishes a verification lookup or a '
        'statewide total (New Jersey\'s ~4,500 vehicles is the cleanest example), '
        'FOIA otherwise. State_Matrix records the route for all 51 jurisdictions; '
        'Fleet_Size_Evidence lands every count that is public today.')

    # ================================================ TAB 2: State Matrix
    ws2 = wb.create_sheet('Fleet_License_State_Matrix')
    sb2 = lib.SheetBuilder(ws2, 8,
                           col_widths=[16, 30, 34, 40, 14, 30, 40, 16],
                           tab_color='FF2E5A3A')
    sb2.title('Fleet-license route by jurisdiction: all 51 US jurisdictions')
    sb2.subtitle('The question: for every US jurisdiction, is the ambulance '
                 'service roster public and by what route, what is the per-'
                 'vehicle permit regime, and is a per-operator fleet count '
                 'publicly retrievable? Each row carries the state EMS licensing '
                 'authority, the roster route, the vehicle-permit regime, the '
                 'VERIFIED NPPES operator floor (Type-2 NPIs, from NPPES), '
                 'whether a fleet count is publicly retrievable, the public '
                 'source, and the access status. Sources: NPPES (floor); state '
                 'EMS offices; NREMT/NASEMSO office index. Join key: state + '
                 'organization NPI.')
    sb2.note('DATA QUALITY: all 51 jurisdictions now carry a CONFIRMED public '
             'LICENSING ROUTE (the state EMS authority + the specific public '
             'lookup/roster/portal), cited per row. That is a separate axis from '
             'the "Fleet count public?" column: a per-operator VEHICLE count is '
             'genuinely public in only a few states (TX, NJ and MI publish a '
             'statewide total; WA offers a public per-vehicle verification '
             'lookup); a dozen more publish a downloadable SERVICE roster (KY, '
             'MA, AR, AZ, MO, ME, RI, SD, CT, IN, TN, OK) which lists operators '
             'but not vehicle counts; elsewhere the vehicle count is portal-/'
             'FOIA-only and is bordered PENDING. The operator floor is an '
             'identity floor, not a fleet count.')
    sb2.blank()
    sb2.banner('Panel A. The 51-jurisdiction route matrix (operator floor = '
               'NPPES Type-2 ambulance NPIs; not a vehicle count)')
    sb2.headers(['Jurisdiction', 'EMS licensing authority', 'Service roster - '
                 'public route', 'Per-vehicle (fleet) permit regime',
                 'Operator floor (NPPES)', 'Fleet count public?',
                 'Public source', 'Access status'])
    matrix_first = sb2.r + 1
    for st in JURIS:
        m = _meta(st)
        fleet_pub, fleet_kind = _fleet_count_public(st)
        sb2.row([
            (f'{STATE_NAME[st]} ({st})', 'label'),
            (m['authority'], 'text'),
            (m['roster_route'], 'text'),
            (m['permit'], 'text'),
            (tot[st], 'src', lib.FMT_INT),
            (fleet_pub, fleet_kind),
            (m['url'], 'note'),
            (m['status'], 'note'),
        ], wrap=True, height=54)
    matrix_last = sb2.r
    sb2.blank()
    sb2.banner('Roll-up - live formulas over the matrix')
    sb2.row([('US operator floor (NPPES orgs, 51 juris)', 'label'),
             (f'=SUM(E{matrix_first}:E{matrix_last})', 'fml', lib.FMT_INT),
             None, None, None, None, None, None])
    sb2.row([('Jurisdictions with a CONFIRMED public licensing route', 'label'),
             (f'=COUNTIF(H{matrix_first}:H{matrix_last},"CONFIRMED")', 'fml',
              lib.FMT_INT),
             None, None, None, None, None, None])
    sb2.row([('Jurisdictions where the VEHICLE count is public (col F "YES")',
              'label'),
             (f'=COUNTIF(F{matrix_first}:F{matrix_last},"YES*")', 'fml',
              lib.FMT_INT),
             None, None, None, None, None, None])
    sb2.row([('Jurisdictions publishing a downloadable SERVICE roster', 'label'),
             (len(DOWNLOADABLE_ROSTER), 'src', lib.FMT_INT),
             None, None, None, None, None, None])
    sb2.blank()
    sb2.banner('Read panel')
    sb2.prose(
        'Fleet identification is a 51-way problem with no national shortcut. '
        'Every jurisdiction licenses ambulance SERVICES, and the near-universal '
        'design permits each VEHICLE under that service license - but the per-'
        'operator vehicle count is open data in only a handful of states and '
        'sits behind a portal or a records request in most. The verified public '
        'anchor that spans all 51 is the NPPES operator floor (identity, not '
        'trucks); the fleet count on top of it is retrieved state by state. All '
        '51 jurisdictions now carry a confirmed public licensing route, and the '
        'matrix records, per state, exactly which artifact a human pulls - a '
        'downloadable roster where one exists (KY, MA, AR, AZ, MO, ME, RI, SD, '
        'CT, IN, TN, OK), a statewide vehicle total (TX, NJ, MI), a per-vehicle '
        'verification lookup (WA), or the portal/FOIA path otherwise. This '
        'matrix is the routing table for that retrieval.')

    # ============================================ TAB 3: Fleet Size Evidence
    ws3 = wb.create_sheet('Fleet_Size_Evidence')
    sb3 = lib.SheetBuilder(ws3, 6, col_widths=[26, 18, 18, 18, 18, 40],
                           tab_color='FF2E5A3A')
    sb3.title('Fleet-size evidence: the operator and vehicle counts that are '
              'public and re-derivable today')
    sb3.subtitle('The question: what ambulance-operator and fleet counts can be '
                 'shown from public records right now? Panel A is the NPPES '
                 'operator-identity floor per jurisdiction (Type-2 NPIs under '
                 'taxonomy 3416*, computed live from the manifested NPPES '
                 'roster). Panel B is the national taxonomy split. Panel C lands '
                 'the confirmed vehicle-license anchors (Texas statewide over '
                 '5,000 licensed ambulances; New Jersey ~4,500 and Michigan '
                 '3,847; plus published service counts for PA, CA, FL, MO). '
                 'Sources: NPPES; Texas DSHS; nj.gov Office of EMS; MDHHS; PA '
                 'DOH; CA EMSA; FL DOH; data.mo.gov (Socrata). Join key: state + '
                 'organization NPI.')
    sb3.note('DATA QUALITY: Panel A counts NPI ORGANIZATIONS, not vehicles - it '
             'is a floor on operator identity. One operator may hold many '
             'vehicle permits under one NPI, and enumerations lag reality; the '
             'floor undercounts operators that bill only under an individual NPI '
             'and overcounts dormant enumerations. The NJ ~4,500 figure is the '
             'state office\'s own statewide vehicle total (all vehicle classes), '
             'not a per-operator count. Missouri counts are LICENSED SERVICES '
             '(open data), not vehicles.')
    sb3.blank()
    sb3.banner('Panel A. NPPES ambulance-organization operator floor by '
               'jurisdiction (Type-2 NPIs; NOT a vehicle count)')
    sb3.headers(['Jurisdiction', 'Operator floor', 'Land transport', 'Air (flag)',
                 'Other/unspec', 'Note'])
    a_first = sb3.r + 1
    for st in JURIS:
        other = tot[st] - land[st] - air[st]
        sb3.row([
            (f'{STATE_NAME[st]} ({st})', 'label'),
            (tot[st], 'src', lib.FMT_INT),
            (land[st], 'src', lib.FMT_INT),
            (air[st], 'src', lib.FMT_INT),
            (other, 'fml', lib.FMT_INT),
            ('operator identities, not vehicles', 'note'),
        ])
    a_last = sb3.r
    sb3.row([('United States (51 juris)', 'label'),
             (f'=SUM(B{a_first}:B{a_last})', 'fml', lib.FMT_INT),
             (f'=SUM(C{a_first}:C{a_last})', 'fml', lib.FMT_INT),
             (f'=SUM(D{a_first}:D{a_last})', 'fml', lib.FMT_INT),
             (f'=SUM(E{a_first}:E{a_last})', 'fml', lib.FMT_INT),
             ('sum of the jurisdiction rows', 'note')])
    sb3.blank()

    sb3.banner('Panel B. National taxonomy split (NPPES ambulance root 3416)')
    sb3.headers(['Taxonomy', 'Code', 'Org NPIs', 'Share of roster', '', ''])
    b_first = sb3.r + 1
    for code in ('3416L0300X', '341600000X', '3416A0800X', '3416S0300X'):
        n = taxc.get(code, 0)
        sb3.row([(TAX[code], 'label'), (code, 'src'), (n, 'src', lib.FMT_INT),
                 (n / roster_n if roster_n else 0, 'fml', lib.FMT_PCT1),
                 None, None])
    sb3.row([('All ambulance-root NPIs (all states + territories)', 'label'),
             ('3416*', 'note'), (roster_n, 'src', lib.FMT_INT),
             (1.0, 'fml', lib.FMT_PCT1), None, None])
    sb3.blank()

    sb3.banner('Panel C. Confirmed vehicle-license anchors (public state '
               'records)')
    sb3.headers(['Anchor', 'State', 'Object', 'Value', 'Unit', 'Source'])
    sb3.row([('Statewide licensed ambulances', 'label'), ('TX', 'src'),
             ('vehicle licenses', 'text'), (5000, 'src', lib.FMT_INT),
             ('vehicles (over 5,000; DSHS)', 'note'),
             ('Texas DSHS EMS Careers', 'note')], wrap=True, height=30)
    sb3.row([('Licensed EMS provider services', 'label'), ('TX', 'src'),
             ('service licenses', 'text'), (800, 'src', lib.FMT_INT),
             ('providers (almost 800; DSHS)', 'note'),
             ('Texas DSHS EMS Careers', 'note')], wrap=True, height=30)
    sb3.row([('Statewide licensed EMS vehicles', 'label'), ('NJ', 'src'),
             ('vehicle licenses', 'text'), (4500, 'src', lib.FMT_INT),
             ('vehicles (approx, all classes)', 'note'),
             ('nj.gov Office of EMS', 'note')], wrap=True, height=30)
    sb3.row([('Mobile Intensive Care Paramedics', 'label'), ('NJ', 'src'),
             ('personnel licenses', 'text'), (1700, 'src', lib.FMT_INT),
             ('MICPs (approx)', 'note'),
             ('nj.gov Office of EMS', 'note')], wrap=True, height=30)
    sb3.row([('Licensed GROUND ambulance services', 'label'), ('MO', 'src'),
             ('service licenses', 'text'), (mo_ground, 'src', lib.FMT_INT),
             ('services (open data)', 'note'),
             ('data.mo.gov e7p8-a69d', 'note')], wrap=True, height=30)
    sb3.row([('Licensed AIR ambulance services', 'label'), ('MO', 'src'),
             ('service licenses', 'text'), (mo_air, 'src', lib.FMT_INT),
             ('services (open data)', 'note'),
             ('data.mo.gov 6xq5-em5d', 'note')], wrap=True, height=30)
    sb3.row([('Statewide licensed life-support VEHICLES', 'label'), ('MI', 'src'),
             ('vehicle licenses', 'text'), (3847, 'src', lib.FMT_INT),
             ('vehicles (2019-08-28)', 'note'),
             ('michigan.gov MDHHS EMS', 'note')], wrap=True, height=30)
    sb3.row([('Licensed life-support AGENCIES', 'label'), ('MI', 'src'),
             ('service licenses', 'text'), (819, 'src', lib.FMT_INT),
             ('agencies (2019-08-28)', 'note'),
             ('michigan.gov MDHHS EMS', 'note')], wrap=True, height=30)
    sb3.row([('Ambulance operators (NPPES floor)', 'label'), ('MO', 'src'),
             ('org identities', 'text'), (tot['MO'], 'src', lib.FMT_INT),
             ('NPIs (identity floor)', 'note'),
             ('NPPES 3416*', 'note')], wrap=True, height=30)
    sb3.row([('Licensed EMS service providers', 'label'), ('FL', 'src'),
             ('service licenses', 'text'), (346, 'src', lib.FMT_INT),
             ('302 ALS + 37 AIR + 7 BLS', 'note'),
             ('FL DOH Licensure Report', 'note')], wrap=True, height=30)
    sb3.row([('Public + private ambulance services', 'label'), ('CA', 'src'),
             ('service licenses', 'text'), (700, 'src', lib.FMT_INT),
             ('700+ (2022-2023 report)', 'note'),
             ('CA EMSA Annual Data Report', 'note')], wrap=True, height=30)
    sb3.row([('Licensed EMS agencies', 'label'), ('PA', 'src'),
             ('service licenses', 'text'), (1205, 'src', lib.FMT_INT),
             ('agencies (46,057 personnel)', 'note'),
             ('PA DOH Bureau of EMS', 'note')], wrap=True, height=30)
    sb3.row([('Vehicles per agency (MI, statewide avg)', 'label'), ('MI', 'src'),
             ('ratio', 'text'), (3847 / 819, 'src', lib.FMT_DEC1),
             ('avg only, not a distribution', 'note'),
             ('3,847 vehicles / 819 agencies', 'note')], wrap=True, height=30)
    sb3.row([('Vehicles per provider (TX, statewide avg)', 'label'), ('TX', 'src'),
             ('ratio', 'text'), (5000 / 800, 'src', lib.FMT_DEC1),
             ('avg only, not a distribution', 'note'),
             ('5,000+ vehicles / ~800 providers', 'note')], wrap=True, height=30)
    sb3.blank()

    # bar chart: top-12 jurisdictions by operator floor
    order = sorted(JURIS, key=lambda s: tot[s], reverse=True)[:12]
    idx = {st: i for i, st in enumerate(JURIS)}
    # build a small contiguous helper block for the chart
    chart_hdr = sb3.r + 1
    sb3.banner('Panel D. Top-12 jurisdictions by operator floor (chart source)')
    sb3.headers(['Jurisdiction', 'Operator floor', '', '', '', ''])
    c_first = sb3.r + 1
    for st in order:
        sb3.row([(f'{st}', 'label'), (tot[st], 'src', lib.FMT_INT),
                 None, None, None, None])
    c_last = sb3.r
    lib.add_chart(ws3, f'D{chart_hdr}',
                  'Top-12 jurisdictions by ambulance-operator floor (NPPES)',
                  f"'Fleet_Size_Evidence'!$A${c_first}:$A${c_last}",
                  [('Operator floor (NPIs)',
                    f"'Fleet_Size_Evidence'!$B${c_first}:$B${c_last}")],
                  kind='bar', y_fmt=lib.FMT_INT)
    sb3.blank()
    sb3.banner('Read panel')
    sb3.prose(
        'Today, the public record supports a firm FLOOR and a growing set of clean '
        'vehicle anchors, not yet a national fleet census. The NPPES floor puts '
        f'roughly {us_total:,} ambulance-organization identities across the 51 '
        'jurisdictions, concentrated in the large states (Texas, Pennsylvania, '
        'Ohio, New York lead), but that counts legal entities, not trucks. Three '
        'states now publish a clean statewide VEHICLE total - Texas (over 5,000 '
        'licensed ambulances across almost 800 provider services), New Jersey '
        '(~4,500 vehicles) and Michigan (3,847) - and four more publish a '
        'statewide licensed-SERVICE count without the vehicle level (Pennsylvania '
        f'1,205 agencies, California 700+ services, Florida 346, Missouri '
        f'{mo_ground:,} ground services). The gap between the operator floor and '
        'an actual fleet census is exactly the per-vehicle-permit count that '
        'State_Matrix routes to state by state - the work this workbook extends '
        'run over run, and Texas at ~6.3 vehicles per provider confirms the NPPES '
        'operator floor systematically understates fleet size.')

    # ==================================================== TAB 4: License Tracker
    oews = _oews_by_state(lib, cache)
    ws4 = wb.create_sheet('IFT_License_Tracker')
    sb4 = lib.SheetBuilder(ws4, 8,
                           col_widths=[24, 16, 16, 30, 14, 16, 16, 16],
                           tab_color='FF2E5A3A')
    sb4.title('IFT license tracker: every public per-state license count, in '
              'one grid')
    sb4.subtitle('The question: for every US jurisdiction, what ambulance/IFT '
                 'license counts are PUBLIC and sourced today? Each row joins the '
                 'operator-identity floor (NPPES Type-2 NPIs), the licensed-'
                 'SERVICE count where a state publishes one, the licensed-VEHICLE '
                 'total where published, and the EMT and paramedic WORKFORCE with '
                 'mean wage (BLS OEWS May 2024, SOC 29-2042 / 29-2043) so wages '
                 'per state can be backed into. Sources: NPPES; state EMS offices '
                 '(published counts); BLS OEWS 2024. Join key: state. A blank '
                 'PENDING cell names where the count would come from.')
    sb4.note('DATA QUALITY: these are FOUR different universes and must not be '
             'summed across columns. Operator floor = NPI organizations '
             '(identity, not vehicles). Licensed services / vehicles = state '
             'credentials (published only where shown; else PENDING via the '
             'State_Matrix route). EMT / paramedic workforce = BLS OEWS JOBS '
             '(employment, not licenses or people - a person can hold two jobs, '
             'and a licensed clinician may not be employed). Wages are BLS mean '
             'annual. Blank workforce cells are BLS nondisclosure (small cell), '
             'not zero.')
    sb4.blank()
    sb4.banner('Panel A. Per-jurisdiction license + workforce tracker (do not '
               'sum across columns - four different universes)')
    sb4.headers(['Jurisdiction', 'Operator floor (NPPES)', 'Licensed services',
                 'Services source / note', 'Licensed vehicles',
                 'EMT jobs (BLS)', 'Paramedic jobs (BLS)', 'EMS mean wage (BLS)'])
    t_first = sb4.r + 1
    for st in JURIS:
        svc = PUBLISHED_SERVICES.get(st)
        veh = PUBLISHED_VEHICLES.get(st)
        o = oews.get(st, {})
        emt_e, para_e = o.get('emt_emp'), o.get('para_emp')
        # EMS mean wage: employment-weighted blend of EMT + paramedic where both
        # present, else whichever is present.
        ew, pw = o.get('emt_wage'), o.get('para_wage')
        wage = None
        if emt_e and para_e and ew and pw:
            wage = (emt_e * ew + para_e * pw) / (emt_e + para_e)
        elif ew:
            wage = ew
        elif pw:
            wage = pw
        svc_cell = ((svc[0], 'src', lib.FMT_INT) if svc
                    else ('PENDING', 'note'))
        svc_note = ((svc[1], 'note') if svc
                    else ('via State_Matrix route (roster/portal)', 'note'))
        veh_cell = ((veh[0], 'src', lib.FMT_INT) if veh
                    else ('PENDING', 'note'))
        sb4.row([
            (f'{STATE_NAME[st]} ({st})', 'label'),
            (tot[st], 'src', lib.FMT_INT),
            svc_cell, svc_note, veh_cell,
            ((emt_e, 'src', lib.FMT_INT) if emt_e is not None
             else ('n/d', 'note')),
            ((para_e, 'src', lib.FMT_INT) if para_e is not None
             else ('n/d', 'note')),
            ((wage, 'src', lib.FMT_USD) if wage else ('n/d', 'note')),
        ], wrap=True, height=26)
    t_last = sb4.r
    sb4.row([('United States (51 juris)', 'label'),
             (f'=SUM(B{t_first}:B{t_last})', 'fml', lib.FMT_INT),
             (f'=SUM(C{t_first}:C{t_last})', 'fml', lib.FMT_INT),
             ('published services only (subset)', 'note'),
             (f'=SUM(E{t_first}:E{t_last})', 'fml', lib.FMT_INT),
             (f'=SUM(F{t_first}:F{t_last})', 'fml', lib.FMT_INT),
             (f'=SUM(G{t_first}:G{t_last})', 'fml', lib.FMT_INT),
             ('col sums; wage is not summable', 'note')])
    sb4.blank()
    # national workforce totals for the read panel / facts
    us_emt = sum((oews.get(s, {}).get('emt_emp') or 0) for s in JURIS)
    us_para = sum((oews.get(s, {}).get('para_emp') or 0) for s in JURIS)
    sb4.banner('Panel B. What each column is (the four universes)')
    for lbl, desc in [
        ('Operator floor (NPPES)', 'Type-2 ambulance NPIs - legal entities, an '
         'identity floor. One operator may hold many vehicle permits under one '
         'NPI; one NPI is not one ambulance.'),
        ('Licensed services', 'State EMS service/agency licenses where the state '
         'publishes a count (TX, PA, CA, FL, MO, IA, MI here). Elsewhere PENDING '
         'via the State_Matrix roster/portal route.'),
        ('Licensed vehicles', 'State per-vehicle permits/licenses where a '
         'statewide total is published (TX, NJ, MI). This is the true fleet-size '
         'unit; elsewhere portal-/FOIA-only.'),
        ('EMT / paramedic jobs', 'BLS OEWS employment (SOC 29-2042 EMT, 29-2043 '
         'paramedic), May 2024. JOBS, not licenses or headcount; excludes '
         'self-employed and understates dual-role fire/EMS.'),
        ('EMS mean wage', 'BLS OEWS annual mean, employment-weighted across EMT '
         'and paramedic. The wage-per-state figure to back into.')]:
        sb4.row([(lbl, 'label'), (desc, 'text'), None, None, None, None, None,
                 None], wrap=True, height=40)
    sb4.blank()
    sb4.banner('Read panel')
    sb4.prose(
        'This is the single grid a diligence desk wants: per state, the operator '
        'floor, the licensed services and vehicles where a state publishes them, '
        'and the EMT and paramedic workforce with the wage to back into. The four '
        'columns are four universes and must never be summed together - identity '
        f'(NPPES: ~{us_total:,} operators), state credentials (services / '
        'vehicles), and BLS jobs (roughly '
        f'{us_emt:,} EMT and {us_para:,} paramedic jobs across the 51) each count '
        'a different thing. Where a licensed-service or vehicle count is not '
        'published it is bordered PENDING with the State_Matrix route that '
        'retrieves it, so the grid doubles as the worklist for filling every '
        'remaining cell.')

    # ================================================ TAB 5: Workforce/Shortage
    ws5 = wb.create_sheet('EMS_Workforce_Shortage')
    sb5 = lib.SheetBuilder(ws5, 6, col_widths=[34, 18, 18, 40, 4, 4],
                           tab_color='FF2E5A3A')
    sb5.title('EMS workforce and shortage: the clinician supply behind every '
              'ambulance fleet')
    sb5.subtitle('The question: how large is the EMS clinician workforce, how '
                 'fast does it turn over, and what public shortage signals exist? '
                 'A fleet is only as deployable as the crews that staff it, so '
                 'this tab pairs the national certified-clinician and employment '
                 'counts with the turnover and burnout indicators, and the few '
                 'states that publish a workforce trend. Sources: NREMT (national '
                 'certification); BLS OOH/OEWS 2024; American Ambulance '
                 'Association / Newton 360 2024 turnover study; NY State Senate. '
                 'Cross-reference: per-state EMT/paramedic jobs and wages live on '
                 'IFT_License_Tracker.')
    sb5.note('DATA QUALITY: national certification (NREMT) and employment (BLS) '
             'are DIFFERENT universes - a nationally certified clinician may hold '
             'a state license without a job, and BLS jobs exclude self-employed '
             'and understate dual-role fire/EMS. Turnover and burnout figures are '
             'from a voluntary industry survey (AAA/Newton 360), representative '
             'not census. Per-state shortage RATES are not uniformly published; '
             'the state rows here are the ones with a public figure - everything '
             'else is PENDING a state workforce report.')
    sb5.blank()
    sb5.banner('Panel A. National EMS clinician supply (NREMT certification + '
               'BLS employment)')
    sb5.headers(['Metric', 'Value', 'Vintage', 'Source / note', '', ''])
    for metric, val, vint, note, fmt in [
        ('Nationally certified EMS clinicians (all levels)', 598843, '2025',
         'NREMT all-time high', lib.FMT_INT),
        ('  of which EMT', 400911, '2025', 'NREMT (66.9%)', lib.FMT_INT),
        ('  of which Paramedic', 149841, '2025', 'NREMT (25.0%)', lib.FMT_INT),
        ('  of which AEMT', 30783, '2025', 'NREMT (5.1%)', lib.FMT_INT),
        ('  of which EMR', 17308, '2025', 'NREMT (2.9%)', lib.FMT_INT),
        ('EMT + paramedic JOBS (BLS employment)', 288580, 'May 2024',
         'BLS OOH; jobs not people', lib.FMT_INT),
        ('EMT + paramedic combined mean annual wage', 45260, 'May 2024',
         'BLS OEWS national', lib.FMT_USD),
        ('Projected annual openings, 2024-2034', 19000, '2024-2034',
         'BLS OOH (growth + replacement)', lib.FMT_INT),
    ]:
        sb5.row([(metric, 'label'), (val, 'src', fmt), (vint, 'src'),
                 (note, 'note'), None, None], wrap=True, height=22)
    sb5.blank()
    sb5.banner('Panel B. Shortage and turnover indicators (industry survey + '
               'state reports)')
    sb5.headers(['Indicator', 'Value', 'Vintage', 'Source / note', '', ''])
    for ind, val, vint, note, fmt in [
        ('Annual EMT/paramedic turnover (range)', '20-36%', '2022-2024',
         'AAA/Newton 360 turnover study (258 orgs, ~20,000 employees)', None),
        ('Paramedic turnover-intention', '28%', '2024',
         'peer-reviewed meta-analysis', None),
        ('Cost to replace one EMT', 5786, '2024', 'AAA/industry', lib.FMT_USD),
        ('Cost to replace one Paramedic', 8620, '2024', 'AAA/industry',
         lib.FMT_USD),
        ('EMS providers reporting burnout / compassion fatigue', '73%', '2024',
         'industry survey', None),
        ('Share planning to leave the field within 5 years', '37%', '2024',
         'industry survey', None),
        ('NY State active EMS responders, change 2019-2022', '-17.5%',
         '2019-2022', 'NY State Senate (workforce crisis)', None),
        ('Rural Michigan open EMT/paramedic vacancies', '500+', '2024',
         'CBS Detroit (rural MI)', None),
    ]:
        cell = ((val, 'src', fmt) if fmt else (val, 'src'))
        sb5.row([(ind, 'label'), cell, (vint, 'src'), (note, 'note'),
                 None, None], wrap=True, height=22)
    sb5.blank()
    sb5.banner('Panel C. Reading the supply against the fleet')
    sb5.prose(
        'The workforce is the binding constraint on fleet deployability, and it '
        'is under strain. Roughly 599,000 clinicians are nationally certified but '
        'only about 289,000 EMT and paramedic JOBS exist (BLS), and those jobs '
        'turn over 20-36% a year - full crew replacement every three to four '
        'years - against a backdrop of 73% reporting burnout and 37% planning to '
        'leave within five years. That is why a licensed vehicle is not a '
        'deployable unit: a permitted ambulance with no crew does not roll. The '
        'per-state EMT and paramedic job counts and wages on IFT_License_Tracker '
        'are the local read on this supply; where a state publishes a workforce '
        'trend (NY, MI here) it confirms the national direction. Per-state '
        'shortage rates are largely unpublished and are the next data to pull.')

    # ================================================ TAB 6: Pull Worklist
    ws6 = wb.create_sheet('Fleet_Data_Pull_Worklist')
    sb6 = lib.SheetBuilder(ws6, 5, col_widths=[22, 30, 40, 40, 44],
                           tab_color='FF2E5A3A')
    sb6.title('Fleet-data pull worklist: the exact lookups to retrieve the '
              'per-operator fleet and license data')
    sb6.subtitle('The question: what exactly do you look up, per jurisdiction, to '
                 'pull the operator/service roster and the per-operator licensed-'
                 'VEHICLE (fleet) count? This is the action checklist behind '
                 'Fleet_License_State_Matrix: for each state the EMS authority, '
                 'the roster pull, the vehicle-count pull, and the public URL; '
                 'plus the three national routes. Where a per-operator vehicle '
                 'count is not open data the cell says how to request it. Use '
                 'this to fill the PENDING cells on IFT_License_Tracker.')
    sb6.note('DATA QUALITY: these are retrieval instructions against PUBLIC state '
             'and federal sources, not asserted counts. State licensure portals '
             'are the authority; the FMCSA route covers only interstate non-'
             'emergency carriers (not 911 / intrastate); NPPES is operator '
             'identity, not vehicles. Verify the live URL - state EMS sites '
             'reorganize.')
    sb6.blank()
    sb6.banner('Panel A. National routes (work these first)')
    sb6.headers(['Route', 'What it yields', 'Exact lookup', 'Scope / caveat', ''])
    for route, yields, how, caveat in [
        ('FMCSA Motor Carrier Census',
         'Per-operator POWER_UNITS (vehicles) + DRIVERS',
         'data.transportation.gov "Company Census File" (dataset az4n-8mr2; also '
         'Motor Carrier Registrations 4a2k-zf79); filter operation/classification '
         'for ambulance / NEMT; read POWER_UNITS per USDOT number',
         'Interstate NEMT carriers only; self-reported; excludes 911/intrastate'),
        ('FMCSA SAFER Company Snapshot',
         'One operator\'s Power Units (vehicles)',
         'safer.fmcsa.dot.gov/CompanySnapshot.aspx - search by USDOT number or '
         'name; read the "Power Units" field',
         'One carrier at a time; interstate NEMT'),
        ('NPPES (operator identity floor, all 51)',
         'Organization NPIs per state + transport mode',
         'npiregistry.cms.hhs.gov - search Organization NPIs by taxonomy 3416 '
         '(Land 3416L0300X, Air 3416A0800X, Water 3416S0300X, Ambulance '
         '341600000X) and state',
         'Identity, not vehicles; one NPI is not one truck'),
    ]:
        sb6.row([(route, 'label'), (yields, 'text'), (how, 'text'),
                 (caveat, 'note'), None], wrap=True, height=54)
    sb6.blank()
    sb6.banner('Panel B. Per-state pull instructions (50 states + DC)')
    sb6.headers(['Jurisdiction', 'EMS licensing authority', 'Roster pull '
                 '(operator list)', 'Vehicle-count (fleet) pull', 'Public source'])
    for st in JURIS:
        meta = _meta(st)
        fp, _k = _fleet_count_public(st)
        # translate the fleet-count status into an action
        if st in VEHICLE_PUBLIC:
            action = VEHICLE_PUBLIC[st]
        elif st in DOWNLOADABLE_ROSTER:
            action = ('Download the ' + DOWNLOADABLE_ROSTER[st] + ' service '
                      'roster; then request the per-vehicle permit count from the '
                      'office')
        else:
            action = ('Request the per-vehicle permit list/count from the office '
                      '(portal/FOIA); ' + _clean(meta['count_route'], 60))
        sb6.row([
            (f'{STATE_NAME[st]} ({st})', 'label'),
            (_clean(meta['authority'], 60), 'text'),
            (_clean(meta['roster_route'], 90), 'text'),
            (action, 'note'),
            (meta['url'], 'note'),
        ], wrap=True, height=44)
    sb6.blank()
    sb6.banner('Panel C. Fastest wins')
    sb6.prose(
        'Start where the data is already public. Statewide licensed-VEHICLE '
        'totals are published for Texas (over 5,000), New Jersey (~4,500) and '
        'Michigan (3,847), and Washington has a public per-vehicle license-'
        'verification lookup. Statewide licensed-SERVICE counts are published '
        'for Texas (~800), Pennsylvania (1,205), California (700+), Florida '
        '(346), Iowa (724), Missouri (486) and Michigan (819). A '
        'downloadable licensed-SERVICE roster exists for Kentucky (XLSX+PDF), '
        'Maine (XLSX), Massachusetts, Arkansas and Arizona (PDF), Missouri '
        '(Socrata open data), and Rhode Island, South Dakota, Connecticut, '
        'Indiana, Tennessee and Oklahoma (public lists). For the true fleet count '
        'everywhere else, the per-vehicle-permit states (FL, MT, NJ, WA, IL, CO, '
        'MI, UT, MS, VT) hold a vehicle-level permit per ambulance - ask the '
        'office for the vehicle-permit register - and the FMCSA census closes the '
        'interstate-NEMT operators nationally.')

    # ------------------------------------------------------------ facts ---
    facts += [
        {'metric': 'US ambulance-operator floor (NPPES Type-2 NPIs, 51 juris)',
         'year': 2026, 'value': us_total, 'unit': 'organization NPIs',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['nppes_amb_roster'],
         'locator': 'Fleet_Size_Evidence Panel A, United States row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'Sum of per-jurisdiction NPPES 3416* org counts; an '
                        'identity floor, not a vehicle count (one NPI is not one '
                        'ambulance)'},
        {'metric': 'US ambulance land-transport organizations (NPPES 3416L0300X)',
         'year': 2026, 'value': us_land, 'unit': 'organization NPIs',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['nppes_amb_roster'],
         'locator': 'Fleet_Size_Evidence Panel A, land column US sum',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'Ground-transport identity floor; excludes air/water and '
                        'unspecified-ambulance NPIs'},
        {'metric': 'US ambulance-organization NPIs, all modes (taxonomy 3416*)',
         'year': 2026, 'value': roster_n, 'unit': 'organization NPIs',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['nppes_amb_roster'],
         'locator': 'Fleet_Size_Evidence Panel B, all-root row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'Full NPPES ambulance-root roster incl. territories; '
                        'land + unspecified + air + water'},
        {'metric': 'New Jersey statewide licensed EMS vehicles',
         'year': 2026, 'value': 4500, 'unit': 'vehicles (approx, all classes)',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['nj_oems_vehicles'],
         'locator': 'Fleet_Size_Evidence Panel C, NJ vehicles row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'NJ Office of EMS own statewide total (ambulances, MICUs, '
                        'SCTUs, air units); a state total, not per-operator'},
        {'metric': 'Missouri licensed ground ambulance services (open data)',
         'year': 2026, 'value': mo_ground, 'unit': 'licensed services',
         'basis': 'DERIVED', 'tier': 'A', 'source_keys': ['mo_ems_socrata'],
         'locator': 'Fleet_Size_Evidence Panel C, MO ground row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'Count of ground-classified rows in the data.mo.gov '
                        'directory; services, not vehicles'},
        {'metric': 'Michigan statewide licensed life-support vehicles',
         'year': 2019, 'value': 3847, 'unit': 'licensed vehicles',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['mi_ems_vehicles'],
         'locator': 'Fleet_Size_Evidence Panel C, MI vehicles row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'Michigan MDHHS own statewide count (819 agencies, 3,847 '
                        'vehicles as of 2019-08-28); a second clean state vehicle '
                        'anchor alongside New Jersey, not per-operator'},
        {'metric': 'Texas statewide licensed ambulances',
         'year': 2026, 'value': 5000, 'unit': 'ambulances (over 5,000)',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['tx_ems_stats'],
         'locator': 'Fleet_Size_Evidence Panel C, TX vehicles row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'Texas DSHS own statewide figure (over 5,000 ambulances '
                        'across almost 800 provider services); the largest clean '
                        'state vehicle anchor, a state total not per-operator'},
        {'metric': 'Texas licensed EMS provider services',
         'year': 2026, 'value': 800, 'unit': 'provider services (almost 800)',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['tx_ems_stats'],
         'locator': 'Fleet_Size_Evidence Panel C, TX services row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'Texas DSHS EMS Careers; pairs with over 5,000 ambulances '
                        'for ~6.3 vehicles per provider, showing the NPPES floor '
                        'understates fleet size'},
        {'metric': 'Pennsylvania licensed EMS agencies',
         'year': 2026, 'value': 1205, 'unit': 'licensed EMS agencies',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['pa_doh_ems'],
         'locator': 'Fleet_Size_Evidence Panel C, PA agencies row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'PA DOH Bureau of EMS statewide count (1,205 agencies, '
                        '46,057 certified personnel); a service count, not a '
                        'vehicle census'},
        {'metric': 'California public + private ambulance services',
         'year': 2023, 'value': 700, 'unit': 'ambulance services (700+)',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['ca_emsa_report'],
         'locator': 'Fleet_Size_Evidence Panel C, CA services row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'CA EMSA 2022-2023 Annual EMS Data Report (more than 700 '
                        'services across 34 LEMSAs / 58 counties); a service '
                        'count, not a vehicle census'},
        {'metric': 'Florida licensed EMS service providers',
         'year': 2026, 'value': 346, 'unit': 'licensed service providers',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['fl_ems_report'],
         'locator': 'Fleet_Size_Evidence Panel C, FL services row',
         'lives_on': 'Fleet_Size_Evidence',
         'cross_check': 'FL DOH EMS Provider Licensure Report (302 ALS + 37 AIR + '
                        '7 BLS = 346); a service count, vehicles permitted under '
                        'each service license'},
        {'metric': 'US jurisdictions with a CONFIRMED public licensing route '
                   'located', 'year': 2026,
         'value': sum(1 for s in JURIS if _meta(s)['status'] == 'CONFIRMED'),
         'unit': 'jurisdictions (of 51)', 'basis': 'SOURCED', 'tier': 'A',
         'source_keys': ['nasemso_state_offices'],
         'locator': 'Fleet_License_State_Matrix roll-up, CONFIRMED count',
         'lives_on': 'Fleet_License_State_Matrix',
         'cross_check': 'Each jurisdiction\'s state EMS authority and specific '
                        'public lookup/roster/portal located and cited; a '
                        'confirmed licensing ROUTE, distinct from whether the '
                        'vehicle COUNT is open (see col F)'},
        {'metric': 'US jurisdictions where the per-operator VEHICLE count is '
                   'publicly retrievable', 'year': 2026,
         'value': len(VEHICLE_PUBLIC),
         'unit': 'jurisdictions (of 51)', 'basis': 'SOURCED', 'tier': 'A',
         'source_keys': ['tx_ems_stats', 'nj_oems_vehicles', 'mi_ems_vehicles'],
         'locator': 'Fleet_License_State_Matrix col F "YES" rows',
         'lives_on': 'Fleet_License_State_Matrix',
         'cross_check': 'TX, NJ and MI publish a statewide vehicle total; WA '
                        'offers a public per-vehicle verification lookup - '
                        'elsewhere the vehicle count is portal-/FOIA-only '
                        '(bordered PENDING)'},
        {'metric': 'US jurisdictions publishing a downloadable licensed-SERVICE '
                   'roster', 'year': 2026, 'value': len(DOWNLOADABLE_ROSTER),
         'unit': 'jurisdictions (of 51)', 'basis': 'SOURCED', 'tier': 'A',
         'source_keys': ['nasemso_state_offices'],
         'locator': 'Fleet_License_State_Matrix col F, "Service roster" rows',
         'lives_on': 'Fleet_License_State_Matrix',
         'cross_check': 'Service-level rosters (KY, MA, AR, AZ, MO, ME, RI, SD, '
                        'CT, IN, TN, OK); a service list, not a vehicle count'},
        {'metric': 'US EMT jobs, 51-jurisdiction sum (BLS OEWS 29-2042)',
         'year': 2024, 'value': us_emt, 'unit': 'jobs (employment)',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['bls_oews_ems_state'],
         'locator': 'IFT_License_Tracker Panel A, EMT-jobs column US sum',
         'lives_on': 'IFT_License_Tracker',
         'cross_check': 'Sum of per-state OEWS EMT employment; jobs not licenses, '
                        'and states with nondisclosed cells are excluded (a floor)'},
        {'metric': 'US paramedic jobs, 51-jurisdiction sum (BLS OEWS 29-2043)',
         'year': 2024, 'value': us_para, 'unit': 'jobs (employment)',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['bls_oews_ems_state'],
         'locator': 'IFT_License_Tracker Panel A, paramedic-jobs column US sum',
         'lives_on': 'IFT_License_Tracker',
         'cross_check': 'Sum of per-state OEWS paramedic employment; jobs not '
                        'licenses; a floor excluding nondisclosed states'},
        {'metric': 'Nationally certified EMS clinicians (all levels)',
         'year': 2025, 'value': 598843, 'unit': 'certified clinicians',
         'basis': 'SOURCED', 'tier': 'A', 'source_keys': ['nremt_cert'],
         'locator': 'EMS_Workforce_Shortage Panel A, certified-clinicians row',
         'lives_on': 'EMS_Workforce_Shortage',
         'cross_check': 'NREMT reported all-time high (EMT 400,911; paramedic '
                        '149,841); certification, not state license or jobs'},
        {'metric': 'Cost to replace one paramedic',
         'year': 2024, 'value': 8620, 'unit': 'USD per separation',
         'basis': 'SOURCED', 'tier': 'B', 'source_keys': ['aaa_turnover'],
         'locator': 'EMS_Workforce_Shortage Panel B, paramedic replacement row',
         'lives_on': 'EMS_Workforce_Shortage',
         'cross_check': 'AAA/industry figure; pairs with 20-36% annual turnover '
                        'to size the retention cost per operator'},
    ]

    # --------------------------------------------------------- findings ---
    findings += [
        {'id_hint': 118,
         'finding': 'There is no national registry of licensed ambulances: '
                    'vehicle permitting is a state function run 51 different '
                    'ways, and the per-operator vehicle count - the true fleet-'
                    'size unit - is open data in only a handful of states and '
                    'portal-/FOIA-only in most. The verified public object that '
                    'spans all 51 jurisdictions is the NPPES operator-identity '
                    f'floor (about {us_total:,} ambulance-organization NPIs), '
                    'which is an identity floor, not a truck count. A fleet is '
                    'therefore built bottom-up: NPPES identity, then state '
                    'service license, then the vehicle-permit count.',
         'numbers': f"='Fleet_Size_Evidence'!B{a_last + 1}",
         'sources': 'nppes_amb_roster; nasemso_state_offices',
         'confidence': 'High on the floor and the no-national-registry structure; '
                       'the floor is a lower bound on operators, not a vehicle '
                       'count',
         'guardrail': 'The NPPES floor counts NPI organizations, not vehicles - '
                      'one operator may hold many vehicle permits under one NPI, '
                      'and one NPI is never one ambulance. Never read the floor '
                      'as a fleet size.'},
        {'id_hint': 119,
         'finding': 'The "fleet license" decomposes into four objects and only '
                    'one - the per-vehicle permit issued under a service license '
                    '(ALS/BLS/dual) - equals fleet SIZE. States confirmed to '
                    'permit each vehicle include Florida (2-yr ALS/BLS/dual '
                    'permits), Montana (a displayed permit per ambulance), New '
                    'Jersey (~4,500 licensed vehicles statewide), Washington '
                    '(service AND vehicle licensing with a public verification '
                    'lookup), Illinois (provider AND vehicle licensing by '
                    'inspection), Colorado (state vehicle permitting since '
                    '2024-07-01), Michigan (3,847 licensed vehicles), Utah (a '
                    'Bureau permit for each vehicle, valid one year), '
                    'Mississippi (a permit for each vehicle at each licensed '
                    'location) and Vermont (a license issued to a specific '
                    'vehicle). The federal routes do not count trucks: NPPES is '
                    'identity, PECOS/MUP is billing, and FMCSA MCS-150 counts '
                    'power units only for interstate non-emergency carriers.',
         'numbers': "Route_Map Panel A: object 2 (per-vehicle permit) is the "
                    "only fleet-size object; 4 confirmed per-vehicle-permit "
                    "states cited",
         'sources': 'fl_ems_permit; mt_ems_permit; nj_oems_vehicles; fmcsa_safer',
         'confidence': 'High that the per-vehicle permit is the fleet unit and '
                       'that these states permit per vehicle',
         'guardrail': 'A per-vehicle permit regime does not guarantee an OPEN '
                      'per-operator count; several confirmed-regime states still '
                      'release the count only by portal or FOIA.'},
        {'id_hint': 120,
         'finding': 'New Jersey is the cleanest public statewide vehicle anchor: '
                    'its Office of EMS reports licensing more than 4,500 vehicles '
                    '(ambulances, mobile intensive care units, specialty-care '
                    'transport units and air units) plus more than 1,700 Mobile '
                    'Intensive Care Paramedics. Set against New Jersey\'s NPPES '
                    f'operator floor of {tot["NJ"]:,} organizations, that implies '
                    'several licensed vehicles per operator on average - a '
                    'concrete illustration of why the operator floor understates '
                    'the fleet.',
         'numbers': "Fleet_Size_Evidence Panel C: NJ 4,500 vehicles / "
                    f"{tot['NJ']:,} NPPES operators",
         'sources': 'nj_oems_vehicles; nppes_amb_roster',
         'confidence': 'High on the NJ statewide total (state office figure); '
                       'the per-operator ratio is an average, not a distribution',
         'guardrail': 'The 4,500 is a statewide all-class vehicle total, not a '
                      'per-operator count, and the NPPES floor is organizations '
                      'not vehicles - the ratio is illustrative of the gap, not a '
                      'fleet-size estimate for any operator.'},
        {'id_hint': 121,
         'finding': 'Michigan is the second clean statewide vehicle anchor and '
                    'sharpens the operator-floor-vs-fleet gap: the state licenses '
                    '819 life-support agencies and 3,847 life-support vehicles '
                    '(2019), an average of roughly 4.7 licensed vehicles per '
                    'agency. Two independent states (NJ and MI) both show several '
                    'licensed vehicles per operator, confirming that the NPPES '
                    'operator floor systematically understates fleet size and '
                    'that the vehicle-permit count - not the operator count - is '
                    'the number a fleet valuation turns on.',
         'numbers': 'Fleet_Size_Evidence Panel C: MI 3,847 vehicles / 819 '
                    'agencies = ~4.7 vehicles per agency',
         'sources': 'mi_ems_vehicles; nj_oems_vehicles',
         'confidence': 'High on both state totals (state-office figures); the '
                       'per-agency ratio is a statewide average, not a '
                       'distribution',
         'guardrail': 'Statewide averages hide a skewed distribution (a few '
                      'large operators run most vehicles); the MI counts are '
                      '2019 vintage. Neither is a per-operator fleet figure.'},
        {'id_hint': 122,
         'finding': 'The IFT_License_Tracker puts every public per-state count in '
                    'one grid across four universes that must never be summed '
                    f'together: the NPPES operator floor (~{us_total:,} '
                    'organizations), the licensed-service and licensed-vehicle '
                    'counts states publish (TX, PA, CA, FL, MO, IA, MI services; '
                    'TX, NJ, MI vehicles), and the BLS EMS workforce (about '
                    f'{us_emt:,} EMT and {us_para:,} paramedic jobs across the 51, '
                    'with a per-state mean wage to back into). Every unpublished '
                    'service or vehicle count is bordered PENDING with the '
                    'State_Matrix route that fills it, so the grid is both the '
                    'evidence and the worklist.',
         'numbers': f"='IFT_License_Tracker'!F{t_last + 1}+"
                    f"'IFT_License_Tracker'!G{t_last + 1}",
         'sources': 'nppes_amb_roster; bls_oews_ems_state; mo_ems_socrata',
         'confidence': 'High on each sourced column; the four universes are not '
                       'additive and the workforce is jobs, not licenses',
         'guardrail': 'Do not sum across columns: NPPES counts entities, state '
                      'counts count credentials, BLS counts jobs. Workforce sums '
                      'are floors (nondisclosed states excluded) and understate '
                      'dual-role fire/EMS staffing.'},
        {'id_hint': 123,
         'finding': 'The workforce, not the vehicle, is the binding constraint on '
                    'fleet deployability - and it is under strain. About 599,000 '
                    'clinicians are nationally certified (NREMT) but only ~289,000 '
                    'EMT and paramedic JOBS exist (BLS), and those jobs turn over '
                    '20-36% a year (AAA/Newton 360), with 73% reporting burnout '
                    'and 37% planning to leave within five years. A permitted '
                    'ambulance with no crew does not roll, so fleet-license counts '
                    'must be read against this supply; the per-state EMT/paramedic '
                    'jobs and wages sit on IFT_License_Tracker.',
         'numbers': 'EMS_Workforce_Shortage Panel A/B: 598,843 certified vs '
                    '288,580 jobs; 20-36% turnover; replacement $5,786 EMT / '
                    '$8,620 paramedic',
         'sources': 'nremt_cert; bls_ooh_ems; aaa_turnover',
         'confidence': 'High on NREMT/BLS counts; turnover/burnout are voluntary-'
                       'survey representative figures, not a census',
         'guardrail': 'Certification, state licensure and employment are three '
                      'different universes and are not additive; per-state '
                      'shortage rates are largely unpublished (PENDING).'}]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings, 'meta': {'run': 7}}
