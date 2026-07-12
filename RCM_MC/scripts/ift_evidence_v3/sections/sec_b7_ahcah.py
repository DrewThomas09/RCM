"""B.7: the Acute Hospital Care at Home (AHCAH) participant layer.

CMS's AHCAH waiver lets an approved hospital deliver inpatient-level care in
the patient's home - admission-avoidance that reshapes transport demand at
both ends (fewer inbound ED-to-inpatient and inpatient-to-SNF legs; a new
mobile-integrated-health paramedic visit stream instead).

The CURRENT approved-hospital roster is NOT publicly machine-readable: the
CMS.gov list is the stale 4/5/2021 PDF, the QualityNet AHCAH Resources/Reports
pages are a JS portal (HTTP 403 to non-browser clients), and the current
AHCAH Hospital file is ResDAC Data-Use-Agreement gated. So the current roster
ships as a bordered PENDING panel naming the fillers, and the footprint slice
is anchored on the only public machine-readable roster (the 4/5/2021 snapshot,
cached ahcah_participants) with a hard vintage caveat.
"""

SHEETS = [{'name': 'Hospital_at_Home_Participants',
           'question': 'Which footprint hospitals run a CMS-approved Acute '
                       'Hospital Care at Home program (admission-avoidance '
                       'that reshapes transport demand)?'}]

FOOTPRINT = ['NE', 'IA', 'KS', 'MO', 'OH', 'WI', 'VA', 'MN', 'IN', 'KY']
SNAME = {'NE': 'Nebraska', 'IA': 'Iowa', 'KS': 'Kansas', 'MO': 'Missouri',
         'OH': 'Ohio', 'WI': 'Wisconsin', 'VA': 'Virginia', 'MN': 'Minnesota',
         'IN': 'Indiana', 'KY': 'Kentucky'}


def build(wb, ctx):
    from openpyxl.styles import Border, Side
    lib = ctx['lib']
    facts, sources, findings = [], [], []
    data = lib.load_cache(ctx['cache'], 'ahcah_participants')
    entries = data['footprint_entries']
    counts = data['footprint_counts_2021']

    sources.append(
        {'key': 'cms_ahcah_2021', 'publisher': 'CMS',
         'document': 'Acute Hospital Care at Home Program - Approved List of '
                     'Hospitals as of 4/5/2021 (the only public machine-'
                     'readable AHCAH roster)',
         'vintage': 'Snapshot dated 4 Apr 2021 (approval dates Nov 2020 - '
                    'Apr 2021)',
         'locator': 'Approved-list table, footprint-state rows (System / '
                    'Hospital / Approval Date); 53 systems, 116 hospitals, '
                    '29 states nationally',
         'supplies': 'Footprint AHCAH-approved hospitals at the 4/5/2021 '
                     'vintage (system, hospital, state, approval date)',
         'url': 'https://www.cms.gov/files/document/'
                'covid-acute-hospital-care-home-program-approved-list-hospitals.pdf',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Hospital_at_Home_Participants']})
    sources.append(
        {'key': 'cms_ahcah_current', 'publisher': 'CMS QualityNet / ResDAC',
         'document': 'AHCAH approved-facilities report (QualityNet) and AHCAH '
                     'Hospital file (ResDAC RIF) - the current-roster fillers',
         'vintage': 'Current program (waiver extended by the Consolidated '
                    'Appropriations Act, 2026); roster not publicly machine-'
                    'readable',
         'locator': 'QualityNet AHCAH Reports page (JS portal, HTTP 403 to '
                    'non-browser clients); ResDAC AHCAH Hospital file is '
                    'Data-Use-Agreement gated',
         'supplies': 'The current approved-hospital roster (PENDING - named '
                     'as the filler for Panel C)',
         'url': 'https://qualitynet.cms.gov/acute-hospital-care-at-home/reports',
         'tier': 'A', 'accessed': ctx['accessed'],
         'powers': ['Hospital_at_Home_Participants']})

    ws = wb.create_sheet('Hospital_at_Home_Participants')
    sb = lib.SheetBuilder(ws, 6, tab_color='FFB75D2A',
                          col_widths=[26, 40, 8, 15, 14, 34])
    sb.title('Hospital-at-Home (AHCAH) participants - the admission-avoidance '
             'layer')
    sb.subtitle('The question: which footprint hospitals hold a CMS Acute '
                'Hospital Care at Home (AHCAH) waiver - delivering inpatient-'
                'level care in the home, which avoids the inbound and '
                'onward transport legs a physical admission would generate? '
                'The CURRENT roster is not publicly machine-readable (JS '
                'portal + DUA-gated file), so it is a bordered PENDING panel; '
                'the footprint slice is anchored on the only public roster, '
                'the 4/5/2021 CMS snapshot (cache ahcah_participants). Join '
                'key: hospital / system name (CCN not published on the list) '
                'to the research-cohort roster and HCRIS.')
    sb.note('DATA QUALITY: the named participants are the 4 Apr 2021 snapshot '
            '(53 systems / 116 hospitals / 29 states nationally) - STALE by '
            'construction; participation has grown materially since and some '
            'hospitals may have exited, and the program lapsed and was '
            're-extended (Consolidated Appropriations Act, 2026). The current '
            'count is NOT stated here because no public machine-readable '
            'roster backs a specific figure - the current roster stays '
            'PENDING (Panel C, naming QualityNet + ResDAC). The public list '
            'carries NO CCN, so the cohort join is by name.')
    sb.blank()

    # ── Panel A: footprint slice (2021 public roster) ──
    sb.banner('Panel A. Footprint AHCAH-approved hospitals - the 4/5/2021 '
              'public snapshot (blue = read from the CMS list)')
    sb.headers(['Health system', 'Hospital (as listed)', 'St',
                'Approval date', '', 'Note'])
    order = {s: i for i, s in enumerate(FOOTPRINT)}
    for e in sorted(entries, key=lambda x: (order.get(x['state'], 99),
                                            x['approval_date'], x['hospital'])):
        hosp = e['hospital'] if e['hospital'] != '-' else '(system-level listing)'
        sb.row([(e['system'], 'src'), (hosp, 'src'), (e['state'], 'src'),
                (e['approval_date'], 'src'), None,
                ('system-level row on the CMS list' if e['hospital'] == '-'
                 else None, 'note')])
    sb.blank()

    # ── Panel B: state summary + total (live formula) ──
    sb.banner('Panel B. Footprint state summary (4/5/2021 snapshot)')
    sb.headers(['State', 'AHCAH hospitals/rows (2021)', '', '', '', 'Note'])
    b0 = sb.r + 1
    for st in FOOTPRINT:
        c = counts.get(st, 0)
        sb.row([(SNAME[st], 'src'), (c, 'src', lib.FMT_INT), None, None, None,
                ('no 2021 AHCAH approval on the public list'
                 if c == 0 else None, 'note')])
    tot_row = sb.r + 1
    sb.row([('Footprint total (2021 snapshot)', 'label'),
            (f'=SUM(B{b0}:B{b0 + len(FOOTPRINT) - 1})', 'fml', lib.FMT_INT),
            None, None, None,
            ('7 of 10 footprint states had at least one approval by 4/5/2021',
             'note')])
    sb.blank()

    # ── Panel C: current roster PENDING ──
    sb.banner('Panel C. Current approved-hospital roster (PENDING: filler '
              'dataset named per row)')
    sb.headers(['What is missing', 'Public dataset (filler)', '', 'Status',
                '', 'Blocker / route'])
    pend = Border(bottom=Side(style='dotted', color='FFB75D2A'),
                  top=Side(style='dotted', color='FFB75D2A'),
                  left=Side(style='dotted', color='FFB75D2A'),
                  right=Side(style='dotted', color='FFB75D2A'))
    pend_rows = [
        ('Current AHCAH approved-hospital roster (facility list)',
         'QualityNet AHCAH Reports (qualitynet.cms.gov/'
         'acute-hospital-care-at-home/reports)',
         'JS portal; HTTP 403 to non-browser clients'),
        ('Current AHCAH hospital file with CCN + approval date',
         'ResDAC AHCAH Hospital file (resdac.org/cms-data/files/'
         'ahcah-hospital)',
         'Research Identifiable File; Data-Use-Agreement gated (not public)'),
    ]
    for what, ds, blk in pend_rows:
        rn = sb.r + 1
        sb.row([(what, 'label'), (ds, 'text'), None, ('PENDING', 'note'),
                None, (blk, 'note')])
        for col in range(1, 7):
            ws.cell(row=rn, column=col).border = pend
    sb.blank()

    # ── chart + read panel ──
    lib.add_chart(ws, 'H' + str(b0),
                  'Footprint AHCAH-approved hospitals by state (4/5/2021)',
                  f"'Hospital_at_Home_Participants'!$A${b0}:$A${b0 + len(FOOTPRINT) - 1}",
                  [('AHCAH hospitals (2021)',
                    f"'Hospital_at_Home_Participants'!$B${b0}:$B${b0 + len(FOOTPRINT) - 1}")],
                  kind='bar')
    n_states = sum(1 for st in FOOTPRINT if counts.get(st, 0) > 0)
    sb.banner('Read panel')
    sb.prose('What is measured now: the 4/5/2021 CMS public roster placed '
             f'{len(entries)} approved AHCAH hospital rows in {n_states} of '
             'the ten footprint states - concentrated in Ohio (Cleveland '
             'Clinic and ProMedica), Minnesota (Allina and HealthPartners) '
             'and Wisconsin (Marshfield). Each AHCAH program substitutes '
             'home care for a physical admission, which removes the '
             'ED-to-inpatient and inpatient-to-SNF transport legs that '
             'admission would have generated, while adding a mobile-'
             'integrated-health paramedic visit stream (the waiver requires '
             'two in-person visits daily). The JOIN to the research cohort '
             'and HCRIS is by hospital/system name (the public list carries '
             'no CCN) to flag which cohort systems operate an AHCAH program '
             'and where admission-avoidance is dampening transport demand. '
             'What is NOT measured: the CURRENT roster - it is not publicly '
             'machine-readable (QualityNet JS portal; ResDAC DUA-gated file) '
             'and is carried as PENDING in Panel C; the 2021 snapshot '
             'understates present participation, but the current count is not '
             'stated here because no public machine-readable roster backs a '
             'specific figure (the current-roster fillers are named in '
             'Panel C).')

    facts += [
        {'metric': 'Footprint AHCAH-approved hospital rows on the CMS public '
                   'roster (4/5/2021 snapshot)',
         'year': 2021, 'value': len(entries), 'unit': 'hospital rows',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['cms_ahcah_2021'],
         'locator': 'Hospital_at_Home_Participants Panel A/B; footprint rows '
                    'of the 4/5/2021 CMS Approved List',
         'lives_on': 'Hospital_at_Home_Participants',
         'cross_check': 'Stale by construction; current roster PENDING '
                        '(Panel C, naming QualityNet + ResDAC); participation '
                        'has grown materially since but no public machine-'
                        'readable roster states the current count'},
        {'metric': 'Footprint states with at least one AHCAH-approved '
                   'hospital on the 4/5/2021 CMS public roster',
         'year': 2021, 'value': n_states, 'unit': 'of 10 states',
         'basis': 'GOV', 'tier': 'A', 'source_keys': ['cms_ahcah_2021'],
         'locator': 'Hospital_at_Home_Participants Panel B; states with a '
                    'non-zero 2021 count (OH, MN, WI, IN, IA, MO, VA)',
         'lives_on': 'Hospital_at_Home_Participants',
         'cross_check': 'NE, KS, KY had no 2021 approval on the public list'},
    ]
    findings.append({
        'id_hint': 105,
        'finding': 'Hospital-at-Home is a live admission-avoidance layer in '
                   'the footprint even on the stale public record: the '
                   f'4/5/2021 CMS roster shows {len(entries)} approved AHCAH '
                   f'hospital rows across {n_states} of the ten footprint '
                   'states (heaviest in OH, MN, WI), each substituting home '
                   'care for a physical admission and thereby removing the '
                   'inbound and onward transport legs that admission would '
                   'have generated. The CURRENT roster is not publicly '
                   'machine-readable and is carried as PENDING, so this is a '
                   'floor that understates present participation.',
        'numbers': f"='Hospital_at_Home_Participants'!B{tot_row}",
        'sources': 'cms_ahcah_2021; cms_ahcah_current',
        'confidence': 'High on the 2021 snapshot (read from the CMS PDF); the '
                      'current roster is PENDING and participation has grown',
        'guardrail': 'The named participants are the 4 Apr 2021 vintage and '
                     'understate current participation; the list has no CCN '
                     '(cohort join is by name); AHCAH substitution dampens '
                     'transport demand at these hospitals but the magnitude '
                     'is not quantified here.'})

    return {'facts': facts, 'sources': sources, 'excluded': [],
            'findings': findings,
            'meta': {'footprint_entries_2021': len(entries),
                     'footprint_states_2021': n_states,
                     'current_roster': 'PENDING'}}
