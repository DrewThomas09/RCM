"""Style_Standard: the written CIM-presentation standard (Run 3, Block U.1).

A reference tab stating the deck-ready formatting rules that the committed
format gate (format_gate.py) enforces on every build. Pure documentation - no
facts, sources or findings.
"""

SHEETS = [{'name': 'Style_Standard',
           'question': 'What is the formatting standard every tab must meet '
                       'to be pasteable into a CIM appendix?'}]

RULES = [
    ('Title block', 'Title in A1: Arial 15 bold, navy 00294C. The question '
     'line and the data-quality line in grey 9pt beneath it (rows 2-3).'),
    ('Panel headers', 'Panel/banner headers Arial 10 bold navy; table header '
     'rows white-on-navy fill.'),
    ('Body', 'Body Arial 9. Labels left-aligned, numbers right-aligned. '
     'Wrapped text with row heights sized so nothing clips.'),
    ('Source line', 'A source line under every panel naming the source IDs '
     'that power it.'),
    ('Numbers', 'Every numeric cell carries an explicit format: thousands '
     'separators on counts; dollars with $ and no decimals above 1,000 (two '
     'decimals only for per-unit rates); percentages at one decimal; zeros as '
     'dashes; years as bare text; no raw floats, no unformatted integers, no '
     'scientific notation.'),
    ('Layout', 'Gridlines off; freeze panes below the title block; column '
     'widths sized to content so nothing truncates or shows #####; cursor at '
     'A1; zoom 100 on save.'),
    ('Tab colours', 'Tab colours grouped by section (governance navy, demand '
     'teal, supply green, analysis slate, assembly amber, receiving/reference '
     'grey) matching the Index groupings; sheet order matches the Index.'),
    ('Charts', 'Every chart passes the V9 style gate plus: title present, '
     'axis labels present, single value axis, category axis on the bottom '
     '(left for horizontal bars) with explicit delete=0, no smoothed lines, '
     'no default-grey Excel styling.'),
    ('The gate', 'These rules are enforced by format_gate.py, committed beside '
     'the verification gates and run on every final build. No revision ships '
     'without the format gate passing and a render proof attached.'),
]


def build(wb, ctx):
    lib = ctx['lib']
    ws = wb.create_sheet('Style_Standard')
    sb = lib.SheetBuilder(ws, 2, tab_color='FF00294C', col_widths=[24, 116])
    sb.title('Style standard: the CIM-presentation rules every tab must meet')
    sb.subtitle('The question: what does a tab have to satisfy to be pasted '
                'into a confidential information memorandum appendix without '
                'edits? These rules are the written standard behind the '
                'committed format gate (format_gate.py); the gate checks them '
                'on every build and no revision ships unless it passes.')
    sb.blank()
    sb.banner('The rules')
    sb.headers(['Dimension', 'Rule'])
    for dim, rule in RULES:
        sb.row([(dim, 'label'), (rule, 'text')], wrap=True,
               height=15 * (1 + len(rule) // 90))
    sb.blank()
    sb.banner('Read panel')
    sb.prose('What this tab is: the presentation contract. The evidence tabs '
             'answer what the market looks like; this tab answers what a '
             'finished exhibit looks like. Every tab in this workbook is built '
             'to be screenshot-worthy at 100 percent zoom - a titled, sourced, '
             'cleanly formatted exhibit rather than a working file. The format '
             'gate turns that intent into a test: gridlines off, a section tab '
             'colour, freeze panes, a bold A1 title, and an explicit number '
             'format on every numeric cell, on all tabs, or the build fails.')
    return {'facts': [], 'sources': [], 'excluded': [], 'findings': [],
            'meta': {'rules': len(RULES)}}
