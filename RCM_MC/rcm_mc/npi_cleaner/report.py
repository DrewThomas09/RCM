"""Multi-tab .xlsx report for a cleaned claims file.

Restores the "download the finished workbook" experience the original v48
web tool offered — but built on PE Desk's own stdlib xlsx writer
(``rcm_mc.exports.xlsx_writer``) instead of the missing ``prettyxl`` /
``run_manifest`` report modules, so it needs no third-party dependency and no
network.

Sheets:
  * **Cleaned data** — the cleaned rows (with any ``recovered_billing_npi``
    column), capped so an enormous upload can't produce a multi-hundred-MB
    workbook; a note row states when it was truncated.
  * **NPI health** — per-column valid / blank / malformed / checksum tallies.
  * **Issues** — the real vendored field + consistency screen findings.
  * **NPPES** — live verification counts + recovered candidate NPIs (only when
    the cross-check ran).
  * **Scorecard** — the headline totals.

Text cells are written as inline strings, which Excel never evaluates as
formulas, so the workbook is inherently safe from CSV-injection.
"""
from __future__ import annotations

from typing import List

from ..exports.xlsx_writer import Sheet, write_xlsx

# Cap the data sheet so the workbook stays small; the CSV download always has
# the complete cleaned dataset.
_MAX_DATA_ROWS = 5000

_H = "header"  # header style id in xlsx_writer


def _header(cells: List[str]):
    return [(c, _H) for c in cells]


def build_workbook(res, headers: List[str], rows: List[List[str]]) -> bytes:
    """Assemble the report workbook bytes from a CleanResult + cleaned table."""
    sheets: List[Sheet] = []

    # ---- Scorecard (first, so it opens on the summary) ----
    sc = res.as_scorecard()
    score_rows = [
        _header(["Metric", "Value"]),
        ["Rows in", res.n_rows_in],
        ["Rows out", res.n_rows_out],
        ["Duplicates removed", res.n_dupes_removed],
        ["Cells trimmed", res.n_cells_trimmed],
        ["NPI cells", res.total_npi_cells],
        ["NPI valid", res.total_valid],
        ["NPI issues", res.total_issues],
        ["Billing-NPI issues", res.billing_issue_count()],
        ["NPI health %", sc["health_pct"]],
        ["Billing column", res.billing_column or "—"],
        ["Source format", sc["delimiter"]],
        ["Recovered NPIs written", len(res.recovered_rows)],
    ]
    sheets.append(Sheet("Scorecard", score_rows, col_widths=[26, 22]))

    # ---- NPI health per column ----
    health = [_header(["Column", "Cells", "Valid", "Blank",
                       "Malformed", "Checksum fail"])]
    for col, c in res.column_stats.items():
        health.append([col, c.get("cells", 0), c.get("valid", 0),
                       c.get("blank", 0), c.get("malformed", 0),
                       c.get("checksum", 0)])
    if len(health) == 1:
        health.append(["No NPI column detected", "", "", "", "", ""])
    sheets.append(Sheet("NPI health", health, col_widths=[28, 10, 10, 10, 12, 14]))

    # ---- Issues (real v49 engine: sized with $ exposure + verdict) ----
    adv = res.advanced or {}
    issues = [_header(["Issue", "Rows flagged", "% rows", "$ exposure",
                       "% $", "Signal"])]
    for it in adv.get("issues", []):
        issues.append([it.get("issue", ""), it.get("rows", 0),
                       it.get("pct_rows"), it.get("dollars"),
                       it.get("pct_dollars"), it.get("systematic", "")])
    if adv.get("repairs"):
        issues.append(["deterministic repairs applied",
                       adv["repairs"], "", "", "", "safe formatting fixes"])
    if len(issues) == 1:
        issues.append(["No coding/consistency findings "
                       "(or pandas engine unavailable)", "", "", "", "", ""])
    sheets.append(Sheet("Issues", issues, col_widths=[26, 13, 9, 14, 8, 52]))

    # ---- Suggested fixes companion (v49 suggested_fixes) ----
    recs = res.suggestions_records
    if recs:
        cols = list(recs[0].keys())
        fix_rows = [_header(cols)]
        for rec in recs[:_MAX_DATA_ROWS]:
            fix_rows.append([rec.get(c, "") for c in cols])
        sheets.append(Sheet("Suggested fixes", fix_rows,
                            col_widths=[12] * min(len(cols), 12)))

    # ---- NPPES verify + recover (only when it ran) ----
    nppes = res.nppes or {}
    if nppes.get("verify") or nppes.get("recover"):
        v = nppes.get("verify", {}) or {}
        np_rows = [
            _header(["NPPES verification", "Value"]),
            ["Checked", v.get("checked", 0)],
            ["Active", v.get("active", 0)],
            ["Not found / deactivated", v.get("not_found", 0)],
            ["", ""],
            [("Recovered candidates", _H), ("", _H)],
            _header(["Row", "Query → candidate NPI"]),
        ]
        for m in (nppes.get("recover", {}) or {}).get("matches", []):
            cands = m.get("candidates") or []
            if not cands:
                continue
            np_rows.append([m.get("row", ""),
                            f"{m.get('query','')} ({m.get('state','')}) → "
                            f"{cands[0]['npi']} {cands[0].get('name','')}"])
        sheets.append(Sheet("NPPES", np_rows, col_widths=[10, 60]))

    # ---- Cleaned data (last; capped) ----
    data_rows: List[list] = []
    if headers:
        data_rows.append(_header(headers))
        for r in rows[:_MAX_DATA_ROWS]:
            data_rows.append(list(r))
        if len(rows) > _MAX_DATA_ROWS:
            data_rows.append(
                [f"… {len(rows) - _MAX_DATA_ROWS} more rows omitted from this "
                 "workbook — the CSV download has the full dataset."])
    else:
        data_rows.append(["No data."])
    widths = [18] * min(len(headers), 20) if headers else None
    sheets.append(Sheet("Cleaned data", data_rows, col_widths=widths))

    return write_xlsx(sheets)
