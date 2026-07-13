"""Run_Log tab (extension order 1.3): the honest record of the v3.4 run.
One row per task attempt; ships in the final file. Also renders the
open-items register: every PENDING with the public dataset that clears it.
"""
import json
import os

SHEETS = [{'name': 'Run_Log',
           'question': 'What did the v3.4 run attempt, in what order, and '
                       'what happened?'}]

SCRATCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PENDING_REGISTER = [
    ('B.7 Hospital-at-Home participants',
     'CMS/QualityNet AHCAH live participant list',
     'JS-only Angular portal; the public PDF is a stale April 2021 snapshot',
     'QualityNet AHCAH portal export or a CMS FOIA-published roster'),
    ('B.6 / X-D MRF commercial-rate pilot',
     'Payer Transparency-in-Coverage in-network files (UHC NE+IA first)',
     'Multi-GB monthly indexes; parse not attempted inside this run window',
     'TiC index stream-parse, TIN-restricted to footprint states '
     '(receiving schema shipped on Commercial_Rate_MRF)'),
    ('IFT-specific facility-pay share',
     'No public source exists',
     'GADCS reports incidence and magnitude for ambulance overall, not IFT',
     'Claims-vendor panel with facility-remit flags, or primary buyer '
     'research (request specs on Engagement_Data_Map)'),
    ('B.3 Medicaid rate card, full footprint',
     'State Medicaid fee schedules (state-by-state files)',
     'Per-state file formats; only partially abstracted in this run',
     'Each state fee-schedule file named on the tab when it ships'),
    ('SAM.gov contract keyword corpus',
     'SAM.gov Opportunities/Contract Data APIs',
     'API key required (api.data.gov); not provisioned in this environment',
     'Free api.data.gov key; the state-portal corpus stands in meanwhile'),
    ('Run 5.5b Annual per-NPI Medicare book to twelve years',
     'MUP by Provider and Service, data-api NPI filter, 2014-2023',
     'Not pulled in this run window; the book stays three vintages '
     '(2013/2019/2024)',
     'Per-NPI MUP pulls for the estate NPIs plus the top-30 participants, '
     '2014-2023, then extend MMT_Medicare_Book to annual columns'),
    ('Run 5.4 Participant additions (Allegiance Mobile Health, PHI Air '
     'Medical)', 'NPPES / MUP / USAspending / press registry',
     'Resolution queue not run in this window',
     'The standing resolution pull for each NPI; PHI carries the air-boundary '
     'label'),
    ('Run 5.5a Commercial MRF rate (now formally closed)',
     'Licensed Transparency-in-Coverage feed',
     'Three public attempts failed (MRF_Attempt_Log): portals bot-blocked '
     '(403) or moved (404), reachable host returns only an index stub',
     'A licensed TiC feed or a payer index that resolves to the in-network '
     'rate file; interim anchor = balance-billing statutory pegs'),
]


def build(wb, ctx):
    lib = ctx['lib']
    rows = []
    p = os.path.join(SCRATCH, 'run_log.json')
    if os.path.exists(p):
        rows = json.load(open(p))

    ws = wb.create_sheet('Run_Log')
    sb = lib.SheetBuilder(ws, 6, col_widths=[8, 8, 40, 12, 60, 46],
                          tab_color='FF6B7C93')
    sb.title('Run log: the extension passes, task by task')
    sb.subtitle('The extension-order operating record: one row per task '
                'attempt with status and what it produced. Statuses: DONE, '
                'PARTIAL, PENDING-blocked (blocker named), '
                'SKIPPED-dependency. Times are UTC on the build day. This '
                'tab is the honest record of what the run did and did not '
                'finish; the open-items register below names the public '
                'dataset that clears every PENDING.')
    sb.blank()
    sb.banner('Task attempts')
    sb.headers(['Start', 'End', 'Task', 'Status', 'Produced', 'Notes'])
    for r in rows:
        sb.row([(r.get('start'), 'text'), (r.get('end'), 'text'),
                (r.get('task'), 'label'), (r.get('status'), 'text'),
                (r.get('produced'), 'text'), (r.get('notes'), 'note')],
               wrap=True, height=26)
    sb.blank()
    sb.banner('Open-items register: every PENDING, its blocker, and the '
              'public dataset that clears it')
    sb.headers(['Item', 'Dataset', 'Blocker', 'What clears it', '', ''])
    for item, ds, blocker, clears in PENDING_REGISTER:
        sb.row([(item, 'label'), (ds, 'text'), (blocker, 'text'),
                (clears, 'text'), None, None], wrap=True, height=30)
    sb.blank()
    sb.note('Governance: this tab is operational metadata, not evidence; '
            'it carries no facts and no sources by design.')
    return {'facts': [], 'sources': [], 'excluded': [], 'findings': [],
            'meta': {'rows': len(rows)}}
