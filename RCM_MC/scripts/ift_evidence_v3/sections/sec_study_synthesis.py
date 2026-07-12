"""Study_Synthesis (Run 4, outcome 6): the deck-facing thesis spine.

One executive tab that walks the interfacility-transport (IFT) investment
thesis as a sequence of MEASURED claims - demand, the measured floor, price and
its mileage load, input-cost risk, supply fragmentation, the subject company,
the structural return-leg driver, and the named risks. Every headline number is
a live green link to the tab that measures it, and every claim carries its
guardrail. No cell here is a new assertion: this tab summarises linked cells,
exactly like Investor_QA, and creates no evidence of its own.

It answers the reviewer's standing question for every page - "why is this here,
for the IFT study?" - at the whole-book level: it names what each major evidence
block contributes to the thesis and points at it.
"""

SHEETS = [{'name': 'Study_Synthesis',
           'question': 'What is the IFT investment thesis in one page, and '
                       'where does each measured claim live?'}]

# Each pillar: (title, claim, headline-formula, numfmt-key, home-tab, guardrail)
# headline is a live cross-tab reference to a VERIFIED cell; numfmt-key selects
# the format; home-tab drives a HYPERLINK navigation cell. A None headline means
# the pillar is structural and navigates to its home tab instead of a number.
PILLARS = [
    ('1. Demand is measured, not modeled',
     'Medicare fee-for-service billed this many hospital-to-hospital ground '
     'transports in 2024 - the hardest measured floor on IFT volume.',
     "='Medicare_IFT_Series'!$B$19", 'INT', 'Medicare_IFT_Series',
     'Carrier claims only; hospital institutional billing and Medicare '
     'Advantage are excluded, so this is a FLOOR on volume, not the market.'),
    ('2. One TAM cell is fully measured; the rest name their gap',
     'Claims-visible volume times the measured Medicare allowed per transport '
     'equals 2024 Medicare FFS interfacility allowed dollars, by construction.',
     "='Scenario_Matrix'!$B$16", 'USD', 'Scenario_Matrix',
     'This is the measured FLOOR, not the TAM. Every larger cell of the '
     'scenario grid is a bordered PENDING that names the dataset that closes '
     'it; mixing cells re-introduces double counting.'),
    ('3. Price carries mileage - and mileage is ~43-45% of it',
     'The measured Medicare allowed per transport INCLUDING A0425 mileage; '
     'base-only pricing silently drops this mileage share.',
     "='Medicare_IFT_Series'!$G$19", 'USD2', 'Derived_Rate_Card',
     'Every dollar cell in the book now ships as a base-only / mileage-loaded '
     'PAIR so the mileage share is never dropped (Scenario_Matrix Panel B2).'),
    ('4. The mileage load is derived, not assumed',
     'The loading factor (loaded allowed / base allowed per transport) is live '
     'and derived two ways - the MMT book and the national registry.',
     "='Derived_Rate_Card'!$B$36", 'X', 'Derived_Rate_Card',
     'The derivation is printed on Derived_Rate_Card; the factor is a measured '
     'ratio of two allowed-dollar series, not a rule of thumb.'),
    ('5. Input costs are tracked, never blended',
     'The statutory CY2026 ambulance payment update (AIF); diesel, wages and '
     'benefits are printed as separate measured series against it.',
     "='Payment_Rules'!$B$23", 'PCT1', 'Input_Cost_Index',
     'No composite input index (house rule). The spread between this update '
     'and measured input inflation is the margin-risk watch item.'),
    ('6. Supply is fragmented, so competition is local',
     'Distinct Medicare ground-ambulance billing organizations in 2024 - a '
     'large, slowly consolidating long tail.',
     "='Fragmentation_National'!$B$18", 'INT', 'Fragmentation_National',
     'National concentration is low; the real competitive set is per-state '
     'and per-corridor, so national shares understate local position.'),
    ('7. The subject company is measured, not asserted',
     'MMT consolidated Medicare FFS ambulance allowed dollars, 2024 vintage '
     '(two NPIs) - the measured book behind the diligence.',
     "='MMT_Medicare_Book'!$E$9", 'USD', 'MMT_Medicare_Book',
     'Medicare FFS only; the MA and facility-pay books are bounded on their '
     'own tabs, never summed into this figure.'),
    ('8. Return-leg demand concentrates structurally',
     'For-profit and lower-rated skilled-nursing facilities bounce patients '
     'back to hospitals more, and that is where the return transport '
     'originates - the structural cut of where demand lands.',
     None, None, 'SNF_ReturnLeg_Structure',
     'The join is on CMS claims quality measures (bounce-back / '
     'discharge-to-community rates), which are a demand PROXY, not transport '
     'counts.'),
    ('9. The risks are named and dated, not hand-waved',
     'The forward picture rests on a dated statutory add-on cliff, the '
     'Medicare-Advantage invisibility of half the book, and local labor '
     'depth - each a bounded lever or a bordered PENDING, never a point '
     'forecast.',
     None, None, 'Growth_Outlook_Shell',
     'Every forward lever sits on Scenario_Matrix Panel C (tornado) with '
     'public bounds, or stays a named PENDING; none is a typed guess.'),
]

NOT_CLAIMS = [
    'A single "the TAM is $X" number. The scenario grid is the answer; its '
    'one fully-measured cell is a floor and every larger cell names the public '
    'dataset that would close it.',
    'Any named roster of the subject company\'s customers, accounts or '
    'clients. The health-system material is a research cohort of '
    'representative multi-hospital health systems operating in the study '
    'footprint, selected for depth.',
    'Contract terms, performance metrics or survey statistics not tied to a '
    'public document. Unpriceable or unretrievable cells stay bordered PENDING '
    'naming their dataset.',
    'Commercial negotiated rates as fact. The MRF-forward price basis is a '
    'named PENDING awaiting Transparency-in-Coverage files; the blended basis '
    'awaits the Medicaid card and contract-rate extraction.',
]


def build(wb, ctx):
    lib = ctx['lib']
    fmt = {'INT': lib.FMT_INT, 'USD': lib.FMT_USD, 'USD2': lib.FMT_USD2,
           'PCT1': lib.FMT_PCT1, 'X': lib.FMT_X}
    ws = wb.create_sheet('Study_Synthesis')
    sb = lib.SheetBuilder(ws, 5, tab_color='FF00294C',
                          col_widths=[34, 60, 20, 26, 60])
    sb.title('Study synthesis: the IFT investment thesis as a sequence of '
             'measured claims, each linked to the tab that proves it')
    sb.subtitle('The question: what is the interfacility-transport thesis in '
                'one page, and where does each claim live? This is the deck '
                'spine - the walk from demand to price to the subject company '
                'to the named risks. Every headline number is a LIVE green '
                'link to its home tab (green = the cell recomputes with the '
                'workbook); every row carries its guardrail. Like Investor_QA '
                'and Slide_Feed, this tab summarises linked cells and creates '
                'NO evidence of its own - it is the map of what each block '
                'contributes to the study, not a new claim.', height=64)
    sb.note('HOW TO READ: a green number is the actual measured cell from the '
            'home tab, not a retyped figure, so it cannot drift from the '
            'evidence. A "->" link navigates to the home tab. The guardrail '
            'column states the one caveat that keeps each claim honest. The '
            '"what this study does NOT claim" panel below is the firewall in '
            'plain language.', height=34)
    sb.blank()

    sb.banner('The thesis, nine measured pillars (green = live cell on the '
              'home tab)')
    sb.headers(['Thesis pillar', 'The measured claim', 'Headline (live)',
                'Home tab', 'Interpretation guardrail'])
    for title, claim, headline, fk, home, guard in PILLARS:
        if headline:
            num_cell = (headline, 'link', fmt[fk])
        else:
            num_cell = (f'=HYPERLINK("#\'{home}\'!A1","see tab ->")', 'link')
        home_cell = (f'=HYPERLINK("#\'{home}\'!A1","{home}")', 'link')
        sb.row([(title, 'label'), (claim, 'text'), num_cell, home_cell,
                (guard, 'note')], wrap=True)
    sb.blank()

    sb.banner('What this study does NOT claim (the firewall, in plain '
              'language)')
    for i, t in enumerate(NOT_CLAIMS, 1):
        sb.row([(f'NOT {i}', 'label'), (t, 'text'), None, None, None],
               wrap=True)
    sb.blank()

    sb.banner('Read panel')
    sb.prose('What this tab is: the one-page synthesis that ties every major '
             'evidence block to its role in the IFT study, so a reader knows '
             'not just what each tab carries but why it is here. The nine '
             'pillars walk demand (measured Medicare volume), the one fully '
             'measured TAM floor, price and its mileage load, input-cost risk '
             'against the statutory update, supply fragmentation, the measured '
             'subject-company book, the structural return-leg driver, and the '
             'named forward risks. Each headline is a live cell, not a '
             'restatement, so the synthesis moves with the evidence; each '
             'guardrail names the one caveat that keeps the claim honest; and '
             'the firewall panel states in plain language what the study '
             'refuses to assert. For the full three-sentence answer to any of '
             'the twelve investor questions, see Investor_QA; for the '
             'exhibit-by-exhibit evidence status, see Slide_Feed.')

    # Pure synthesis tab, like Style_Standard: it summarises linked cells and
    # emits no facts, sources or findings of its own, so it adds no ledger IDs
    # and cannot renumber anything already shipped.
    return {'facts': [], 'sources': [], 'excluded': [], 'findings': [],
            'meta': {'pillars': len(PILLARS), 'not_claims': len(NOT_CLAIMS)}}
