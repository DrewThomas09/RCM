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

# Cap the workbook's data sheets — Excel itself stops at 1,048,576 rows
# and a multi-GB xlsx helps no one; a note row states the truncation and
# the CSV download always has the complete cleaned dataset.
_MAX_DATA_ROWS = 100_000

_H = "header"  # header style id in xlsx_writer


def _header(cells: List[str]):
    return [(c, _H) for c in cells]


def build_workbook(res, headers: List[str], rows: List[List[str]]) -> bytes:
    """Assemble the report workbook bytes from a CleanResult + cleaned table."""
    sheets: List[Sheet] = []
    sc = res.as_scorecard()

    # ---- Executive summary (first tab — the page a VP actually reads;
    #      mirrors the ?fmt=exec one-pager so the emailed .xlsx carries
    #      the same verdict + remediation as the web report). ----
    _q0 = sc.get("quality") or {}
    exec_rows = [
        _header(["NPI Claims Cleaner — executive summary", ""]),
        ["Grade", f"{_q0.get('letter', '—')} ({_q0.get('score', '—')}/100)"],
        ["Rows", f"{res.n_rows_in} in → {res.n_rows_out} out"],
        ["Duplicates removed", res.n_dupes_removed],
        ["Deterministic fixes applied", sum(res.repairs.values())],
        ["Rows flagged (all findings)",
         sum((sc.get("sanity") or {}).values())],
        ["Source format", sc["delimiter"]],
    ]
    _clm0 = sc.get("claims") or {}
    if _clm0.get("n_claims"):
        exec_rows.append(
            ["Distinct claims",
             f"{_clm0['n_claims']:,} · {_clm0.get('avg_lines')} lines/claim"])
    _sn0 = sc.get("sanity") or {}
    if _sn0:
        exec_rows.append(_header(["Top findings", "Rows"]))
        try:
            from . import rules as _rules_mod
        except Exception:  # noqa: BLE001 — registry missing → raw ids
            _rules_mod = None
        for rule, n in sorted(_sn0.items(), key=lambda kv: -kv[1])[:8]:
            info = _rules_mod.describe(rule) if _rules_mod else {}
            title = info.get("title") or rule
            sev = info.get("severity") or ""
            exec_rows.append([f"{title}" + (f"  [{sev}]" if sev else ""), n])
            rem = (info.get("remediation") or "").strip()
            if rem:
                exec_rows.append(["    → " + rem[:140], ""])
    _pq0 = sc.get("payer_quality") or []
    if _pq0:
        exec_rows.append(_header(["Quality by payer", "Clean %"]))
        for p in _pq0[:8]:
            exec_rows.append([f"{p['payer']} ({p['rows']:,} rows)",
                              f"{p['clean_pct']}%"])
    _creds0 = sc.get("credentials") or {}
    if _creds0:
        exec_rows.append(_header(["Credential mix", "Cells"]))
        for c, n in sorted(_creds0.items(), key=lambda kv: -kv[1])[:8]:
            exec_rows.append([c, n])
    _specs0 = sc.get("specialties") or []
    if _specs0:
        exec_rows.append(_header(["Specialty mix", "Rows"]))
        for s in _specs0[:8]:
            exec_rows.append([s.get("name") or s.get("code"), s.get("n")])
    sheets.append(Sheet("Summary", exec_rows, col_widths=[56, 16]))

    # ---- Scorecard ----
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

    # ---- Quality report card (grade + dimensions + top findings) so the
    #      shareable Excel deliverable carries the same verdict as the web UI.
    q = sc.get("quality") or {}
    dims = q.get("dimensions") or {}
    quality_rows = [
        _header(["Data-quality report card", ""]),
        ["Overall grade", f"{q.get('letter', '—')} · {q.get('score', '—')}/100"],
        ["Completeness %", dims.get("completeness", "—")],
        ["Validity %", dims.get("validity", "—")],
        ["Consistency %", dims.get("consistency", "—")],
        ["Uniqueness %", dims.get("uniqueness", "—")],
        ["Conformity %", dims.get("conformity", "—")],
        ["Cells changed (audit trail)", sc.get("changes_logged", 0)],
    ]
    _sanity = sc.get("sanity") or {}
    if _sanity:
        quality_rows.append(_header(["Top findings", "Rows"]))
        for rule, n in sorted(_sanity.items(), key=lambda kv: -kv[1])[:10]:
            quality_rows.append([rule, n])
    _payer = sc.get("payer") or {}
    if _payer.get("multi_spelling"):
        quality_rows.append(_header(["Payer spellings to reconcile", "Rows"]))
        for c in _payer["multi_spelling"][:6]:
            quality_rows.append(
                [f"{c['canonical']} ({c['n_variants']} spellings)",
                 c["total"]])
    _fill = [f for f in (sc.get("fill_rates") or []) if f["pct"] < 100.0]
    if _fill:
        quality_rows.append(_header(["Columns with blanks", "% filled"]))
        for f in sorted(_fill, key=lambda d: d["pct"])[:10]:
            quality_rows.append([f["column"], f["pct"]])
    sheets.append(Sheet("Quality", quality_rows, col_widths=[40, 18]))

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

    # ---- Per-rule worklist tabs: just the flagged rows, ready to hand to
    #      the source-system owner (top 5 rules, 200 rows each). ----
    flag_rows = getattr(res, "flag_rows", None) or {}
    for rule, idxs in sorted(flag_rows.items(),
                             key=lambda kv: -len(kv[1]))[:5]:
        idx_set = set(idxs[:200])
        wl = [_header(["_row"] + list(headers))]
        for i, r in enumerate(rows, start=1):
            if i in idx_set:
                wl.append([i] + list(r))
        if len(wl) > 1:
            sheets.append(Sheet(("WL " + rule)[:28], wl,
                                col_widths=[7] + [14] * min(len(headers), 11)))

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
