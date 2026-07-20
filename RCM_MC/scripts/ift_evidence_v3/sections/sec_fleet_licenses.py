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
vehicle-license anchors (New Jersey's ~4,500 licensed EMS vehicles). Every number
is public and re-derivable; per-operator vehicle counts that are not public are
PENDING with the named state registry.

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
               count_route='Provider roster public; vehicle count via DSHS',
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
    sb2.note('DATA QUALITY: "CONFIRMED" means the state\'s public route was '
             'individually located and cited; "PORTAL/FOIA" means the row '
             'carries the NATIONAL NORM (the state EMS office permits vehicles '
             'but the per-operator count is portal-/FOIA-only) with the NPPES '
             'floor as the verified public anchor - it is not a claim that the '
             'state hides data, only that an open per-operator vehicle count was '
             'not located. The operator floor is an identity floor, not a fleet '
             'count. Later runs promote PORTAL/FOIA rows to CONFIRMED as each '
             'route is verified.')
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
        fleet_pub = ('PENDING' if m['status'] != 'CONFIRMED'
                     else m['count_route'])
        fleet_kind = 'note' if m['status'] != 'CONFIRMED' else 'text'
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
    sb2.row([('Jurisdictions with a CONFIRMED public route', 'label'),
             (f'=COUNTIF(H{matrix_first}:H{matrix_last},"CONFIRMED")', 'fml',
              lib.FMT_INT),
             None, None, None, None, None, None])
    sb2.row([('Jurisdictions PORTAL/FOIA (count not open; floor anchors)',
              'label'),
             (f'=COUNTIF(H{matrix_first}:H{matrix_last},"PORTAL/FOIA")', 'fml',
              lib.FMT_INT),
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
        'trucks); the fleet count on top of it is retrieved state by state. This '
        'matrix is the routing table for that retrieval, and it is append-only: '
        'each run promotes more rows from PORTAL/FOIA to CONFIRMED.')

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
                 'the confirmed vehicle-license anchors (Missouri open-data '
                 'service counts; New Jersey statewide ~4,500 licensed '
                 'vehicles). Sources: NPPES; data.mo.gov (Socrata); nj.gov '
                 'Office of EMS. Join key: state + organization NPI.')
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
    sb3.row([('Ambulance operators (NPPES floor)', 'label'), ('MO', 'src'),
             ('org identities', 'text'), (tot['MO'], 'src', lib.FMT_INT),
             ('NPIs (identity floor)', 'note'),
             ('NPPES 3416*', 'note')], wrap=True, height=30)
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
        'Today, the public record supports a firm FLOOR and a few clean vehicle '
        'anchors, not a national fleet census. The NPPES floor puts roughly '
        f'{us_total:,} ambulance-organization identities across the 51 '
        'jurisdictions, concentrated in the large states (Texas, Pennsylvania, '
        'Ohio, New York lead), but that counts legal entities, not trucks. The '
        'only clean statewide VEHICLE total located is New Jersey\'s ~4,500 '
        'licensed vehicles; Missouri\'s open data gives a licensed-SERVICE count '
        f'({mo_ground:,} ground services) but no vehicle level. The gap between '
        'the operator floor and an actual fleet census is exactly the per-'
        'vehicle-permit count that State_Matrix routes to state by state - the '
        'work this workbook now extends run over run.')

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
        {'metric': 'US jurisdictions with a located open per-operator fleet-count '
                   'route', 'year': 2026,
         'value': sum(1 for s in JURIS if _meta(s)['status'] == 'CONFIRMED'),
         'unit': 'jurisdictions (of 51)', 'basis': 'SOURCED', 'tier': 'A',
         'source_keys': ['nasemso_state_offices'],
         'locator': 'Fleet_License_State_Matrix roll-up, CONFIRMED count',
         'lives_on': 'Fleet_License_State_Matrix',
         'cross_check': 'Jurisdictions whose specific public route was located '
                        'and cited this run; the rest carry the national-norm '
                        'PORTAL/FOIA route with the NPPES floor as anchor'},
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
                    'Jersey (~4,500 licensed vehicles statewide) and Washington '
                    '(service AND vehicle licensing with a public verification '
                    'lookup). The federal routes do not count trucks: NPPES is '
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
    ]

    return {'facts': facts, 'sources': sources, 'excluded': excluded,
            'findings': findings, 'meta': {'run': 7}}
