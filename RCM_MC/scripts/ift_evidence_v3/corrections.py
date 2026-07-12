"""Targeted, logged corrections to copied v2.7 sheets.

Every change returns a change-log entry (tab, cell, old, new, why, class) so
V3_Change_Log carries the complete edit trail — the v2.7 ethos of keeping
corrections visible, applied to v2.7 itself.
"""


def _replace_in_sheet(ws, needle, replacement, why, cls, entries, max_hits=10):
    hits = 0
    for row in ws.iter_rows():
        for cell in row:
            v = cell.value
            if isinstance(v, str) and needle in v:
                new = v.replace(needle, replacement)
                entries.append({
                    'tab': ws.title, 'cell': cell.coordinate,
                    'old': (needle if len(v) > 120 else v),
                    'new': (replacement if len(v) > 120 else new),
                    'why': why, 'class': cls})
                cell.value = new
                hits += 1
                if hits >= max_hits:
                    return hits
    return hits


def apply_corrections(wb):
    """Apply C2/C4/C5 fixes (README and Source_Index are rebuilt elsewhere)."""
    entries = []

    # C2a — Methodology stale fact range
    _replace_in_sheet(
        wb['Methodology'],
        'Every fact carries a Fact ID (F01-F147)',
        'Every fact carries a Fact ID (F01-F165 in v2.7; v3 extends the ledger — see Fact_Ledger)',
        'Stale range: v2.7 ledger runs to F165, and v3 appends beyond it.',
        'correction', entries)

    # C2b — mangled "v1" API paths ("revision 1" artifact) across every tab that
    # prints a reproduce spec: a wrong endpoint breaks reproducibility.
    for tab in ('Methodology', 'Verification_Log', 'Source_Register', 'Medicare_PSPS',
                'Medicare_IFT_Series', 'Medicare_OD_Matrix', 'Supplier_Series_Raw'):
        _replace_in_sheet(
            wb[tab], 'data-api/revision 1/dataset', 'data-api/v1/dataset',
            'Text-mangling artifact: the CMS endpoint is /data-api/v1/dataset/... — '
            '"revision 1" was a find-replace casualty in v2.7 and breaks the printed '
            'reproduce spec.',
            'correction', entries)

    # C6 — the rev-5 consolidation note undercounted tabs and sources
    _replace_in_sheet(
        wb['Verification_Log'],
        'internally consistent at 43 tabs, 73 sources',
        'internally consistent at 47 tabs, 77 sources [corrected in v3: the rev-5 note '
        'undercounted the four client-alignment/connector tabs and sources S74-S77]',
        'The v2.7 file itself contains 47 sheets and sources through S77; the rev-5 '
        'self-description was stale.',
        'correction', entries)

    # C5 — Verification_Log Panel E stale contradiction
    _replace_in_sheet(
        wb['Verification_Log'],
        'It is NOT reflected in this workbook. Pull it before any external use.',
        'It IS reflected in this workbook on MedPAC_2026_Mandated [stale sentence '
        'corrected in v3: Panel A row 14 and source S31 record the report as pulled, '
        'read, and incorporated].',
        'Stale rev-1 sentence contradicted Panel A and the MedPAC_2026_Mandated tab.',
        'correction', entries)

    # C4 — Source_Register S31 stale duplicate note
    _replace_in_sheet(
        wb['Source_Register'],
        'NOT reflected in this workbook. It is the authoritative source on Medicare '
        'ground ambulance payment adequacy and should be pulled before external use.',
        'Initially logged as pending; subsequently pulled, read, and incorporated on '
        'MedPAC_2026_Mandated [stale pending text corrected in v3]. It is the '
        'authoritative source on Medicare ground ambulance payment adequacy.',
        'S31 carried contradictory notes (the rev-1 pending sentence was never '
        'deleted after the rev-2 incorporation).',
        'correction', entries)

    # DQ - stray Python-artifact strings copied from v2.7 (e.g. a literal
    # "None" a prior export left in a cell). Clearing them is a presentation
    # fix; logged here so the carried-cell fidelity gate excludes them and the
    # edit trail stays complete. apply_corrections runs before any v3 module
    # adds a tab, so this scans the carried v2.7 sheets only.
    _ARTIFACTS = {'None', 'nan', 'NaN', 'NaT', 'NULL', 'null'}
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.strip() in _ARTIFACTS:
                    entries.append({
                        'tab': ws.title, 'cell': cell.coordinate,
                        # describe rather than echo the bare token, so the
                        # presentation pass (which clears bare None/nan) does
                        # not later wipe the log cell documenting it.
                        'old': f'literal "{cell.value.strip()}"', 'new': '(blank)',
                        'why': 'Stray Python-artifact string copied from v2.7; '
                               'cleared for presentation (Run 3 P.5).',
                        'class': 'DQ'})
                    cell.value = None

    return entries
