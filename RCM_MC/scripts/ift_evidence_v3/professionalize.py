"""Professional-tone normalization of every tab's title and subtitle.

The v2.7/v3 house style opened each tab with a conversational frame - "The
question: ...", titles with " - the decision record" / ", measured:" flourishes,
rhetorical asides ("why should anyone trust this workbook?", "the walk from ...",
"at a glance"). This pass rewrites the title (A1) and subtitle (A2/A3) of every
tab into a declarative, source-forward register with no conversational tonality,
leaving the data, findings, ledgers and read panels untouched.

Marquee narrative tabs whose bodies also carry the old register get a bespoke
title/subtitle here; everything else falls to the systematic rules. Changes to
carried v2.7 tabs are returned so the verification gate can exclude those
title-block cells from carried-cell fidelity (they are presentation, not
evidence).
"""
import re

# ── subtitle: strip the conversational scope frame ──────────────────────────
_META = re.compile(
    r'^\s*the question(?:\s+here)?(?:\s+is)?(?:\s+simple)?\s*[:,\-]\s*', re.I)
_INTERROG = re.compile(r'^(.*?\?)(\s+)(.*)$', re.S)
_LEADS_QUESTION = re.compile(
    r'^\s*(what|how|which|who|whom|whose|why|where|when|whether|do|does|did|is|are|was|were|can|could|should|would|will)\b',
    re.I)
# meta lead-ins that name the tab instead of describing the evidence
_TAB_LEAD = re.compile(
    r'^\s*This tab (?:carries|is|holds|records|maps|shows|answers|gives|presents)\s+(?:the\s+)?',
    re.I)

# conversational phrases removed wherever they appear
_PHRASES = [
    (re.compile(r',?\s*\bstated plainly\b', re.I), ''),
    (re.compile(r'\s*\bat a glance\b', re.I), ''),
    (re.compile(r'\s*\bin one page\b', re.I), ''),
    (re.compile(r'\s*\bin plain language\b', re.I), ''),
    (re.compile(r'\s*\bat a stroke\b', re.I), ''),
]


def _cap(s):
    s = s.strip()
    return s[:1].upper() + s[1:] if s else s


def _clean(s):
    for rx, rep in _PHRASES:
        s = rx.sub(rep, s)
    s = s.replace('—', ' - ').replace('–', ' - ')
    s = re.sub(r'\s{2,}', ' ', s)
    s = re.sub(r'\s+([;:,.])', r'\1', s)
    return s.strip()


# Bespoke subtitles for the marquee narrative tabs (their bodies also carried
# the old register, so the systematic rules alone are not enough).
_SUBTITLE_MAP = {
    'Methodology':
        'The inclusion rule, why each evidence tab exists, the definitional '
        'choices that move the numbers, how each dataset was pulled so the '
        'workbook reproduces, and the rules for comparing figures. Sections 5 '
        'and 9 cover the pull pipeline, the verification gates and the audit '
        'path.',
    'Study_Synthesis':
        'The interfacility-transport thesis as nine measured pillars, from '
        'demand through price and the mileage load to the subject company and '
        'the named risks. Every headline is a live green link to its home tab '
        'and every row carries its guardrail; like Investor_QA and Slide_Feed, '
        'this tab summarises linked cells and creates no evidence of its own.',
}


def fix_subtitle(name, s):
    if not isinstance(s, str) or not s.strip():
        return s
    out = _META.sub('', s)
    # drop a leading interrogative scope sentence when a substantive sourced
    # remainder follows; the title and read panel already describe the tab.
    m = _INTERROG.match(out)
    if m and _LEADS_QUESTION.match(m.group(1)):
        remainder = m.group(3).strip()
        if len(remainder) >= 45 or re.search(
                r'\b(sources?|status rule|roll-up|method|methodology|scope)\b',
                remainder, re.I):
            out = remainder
        else:
            out = out.rstrip('?').strip()
    out = _TAB_LEAD.sub('', out)
    out = _clean(out)
    return _cap(out)


# ── title: strip the flourish register ──────────────────────────────────────
_TITLE_MAP = {
    'MMT_Medicare_Book':
        'Subject-company Medicare FFS ambulance book by NPI, 2013 / 2019 / 2024',
    'Study_Synthesis':
        'Study synthesis: the IFT investment thesis in nine measured pillars',
    'Input_Cost_Index':
        'Input-cost index: measured operating inputs against the Medicare '
        'payment update',
    'Fragmentation_National':
        'Fragmentation: the US Medicare ambulance biller universe, 12 vintages '
        '2013-2024',
    'Market_Share_Panels':
        'Market share: Medicare FFS ambulance billers in the ten footprint '
        'states, by vintage',
    'Utilization_Normalized':
        'Per-beneficiary utilization: the denominator behind half the decline',
}

_TITLE_RX = [
    (re.compile(r'\s*[-–]\s*the decision record\s*$', re.I), ''),
    (re.compile(r',\s*measured\s*:\s*the\s+', re.I), ': '),
    (re.compile(r',\s*measured\s*:\s*', re.I), ': '),
    (re.compile(r',\s*measured\b', re.I), ''),
    (re.compile(r':\s*the full certified registry', re.I), ': certified registry'),
    (re.compile(r'\s+[-–]+\s+the\s+', re.I), ': '),   # "X - the Y" flourish
    (re.compile(r'^\s*The\s+(input-cost index|subject company)\b', re.I),
     lambda m: m.group(1)[:1].upper() + m.group(1)[1:]),
]


def fix_title(name, t):
    if not isinstance(t, str) or not t.strip():
        return t
    if name in _TITLE_MAP:
        return _TITLE_MAP[name]
    out = t
    for rx, rep in _TITLE_RX:
        out = rx.sub(rep, out, count=1)
    # _clean also collapses the "  -  " double-spacing left by dash
    # sanitization, so titles read consistently; a no-op on already-clean ones.
    return _cap(_clean(out))


def professionalize(wb, carried=frozenset(), log=None):
    """Rewrite A1 title and A2/A3 subtitle on every tab. Returns the list of
    [tab, coord] cells changed on CARRIED v2.7 tabs, for the V1 exclusion."""
    n_t = n_s = 0
    carried_changes = []
    for name in wb.sheetnames:
        ws = wb[name]
        jobs = (('A1', lambda v: fix_title(name, v)),
                # A2 is the subtitle; marquee tabs get a bespoke rewrite there.
                ('A2', lambda v: _SUBTITLE_MAP.get(name) or fix_subtitle(name, v)),
                ('A3', lambda v: fix_subtitle(name, v)))
        for coord, fn in jobs:
            cell = ws[coord]
            old = cell.value
            if not isinstance(old, str) or not old.strip():
                continue
            new = fn(old)
            if new and new != old:
                cell.value = new
                if coord == 'A1':
                    n_t += 1
                else:
                    n_s += 1
                if name in carried:
                    carried_changes.append([name, coord])
    if log:
        log(f'professionalize: {n_t} titles, {n_s} subtitles rewritten '
            f'({len(carried_changes)} on carried tabs, excluded from V1)')
    return carried_changes
