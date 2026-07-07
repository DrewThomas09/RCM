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
  * **Denials / Compliance / Charge outliers / Dictionary** — the denial mix
    with the playbook, the OIG LEIE + PECOS screens, the per-HCPCS charge
    outliers, and the data dictionary (guarded; present when the run
    produced them) so the forwarded workbook carries the same verdict as
    the web UI, not a thinner one.
  * **NPPES** — live verification counts + recovered candidate NPIs (only when
    the cross-check ran).
  * **Scorecard** — the headline totals.
  * **WL &lt;rule&gt;** — per-rule worklists that lead with why-flagged +
    what-to-do and keep the largest-billed rows when a charge column exists.

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
        # Rule HITS, not rows — a row firing three rules contributes 3, so
        # the old "Rows flagged" label could exceed rows_out and read as
        # broken arithmetic next to the row counts above.
        ["Findings (rule hits, all rules)",
         sum((sc.get("sanity") or {}).values())],
        ["Source format", sc["delimiter"]],
    ]
    _fr0 = getattr(res, "flag_rows", None) or {}
    if _fr0:
        _distinct_flagged = len(set().union(*_fr0.values()))
        exec_rows.insert(6, ["Rows with ≥1 finding (worklist-capped)",
                             _distinct_flagged])
    _trend0 = sc.get("trend_alerts") or []
    if _trend0:
        exec_rows.append(_header(["Change vs previous run of this file", ""]))
        for _ta in _trend0[:8]:
            exec_rows.append([str(_ta), ""])
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

    # ---- Population marts (analytics.py) — the Tuva-class output in the
    #      shareable workbook, not just the web Population tab. ----
    _pop = sc.get("population") or {}
    if _pop:
        pop_rows: List[List[object]] = []
        _mix = _pop.get("service_mix") or {}
        if _mix.get("categories"):
            pop_rows.append(_header(["Care setting", "Lines", "% of file",
                                     "Charges"]))
            for c in _mix["categories"][:16]:
                pop_rows.append([f"{c['category']} — {c['subcategory']}",
                                 c["rows"], f"{c['pct']}%",
                                 round(float(c["charges"]), 2)])
        _enc = _pop.get("encounters") or {}
        if _enc:
            pop_rows.append(_header(["Encounters", ""]))
            pop_rows.append(["Total encounters", _enc.get("n_encounters", 0)])
            pop_rows.append(["Distinct patients", _enc.get("n_patients", 0)])
            _rd0 = _enc.get("readmissions") or {}
            if _rd0:
                pop_rows.append(
                    ["30-day readmissions",
                     f"{_rd0.get('readmissions_30d', 0)} of "
                     f"{_rd0.get('inpatient_stays', 0)} "
                     f"({_rd0.get('rate_pct')}%)"])
        _vol = _pop.get("volume") or {}
        if _vol.get("median_observed_pmpm") is not None:
            pop_rows.append(["Median observed PMPM",
                             round(float(_vol["median_observed_pmpm"]), 2)])
        _ci = _pop.get("coding_intensity") or {}
        if _ci:
            pop_rows.append(_header(["E&M coding intensity", ""]))
            pop_rows.append(["Established visits (99211-15)",
                             _ci.get("established_visits", 0)])
            pop_rows.append(["File average level",
                             _ci.get("file_avg_level", "—")])
            if _ci.get("provider_basis"):
                pop_rows.append(["Provider grain",
                                 f"{_ci['provider_basis']} NPI"])
            # File-vs-national established-visit mix — computed on every
            # run (refdata.EM_ESTABLISHED_NATIONAL_MIX) but previously
            # rendered nowhere.
            _fm = _ci.get("file_mix") or {}
            _nm = _ci.get("national_mix") or {}
            if _fm and _nm:
                _fm_tot = sum(int(v or 0) for v in _fm.values()) or 1
                pop_rows.append(_header(["E&M level", "File %",
                                         "National %"]))
                for _lvl in ("99211", "99212", "99213", "99214", "99215"):
                    _fp = round(100.0 * int(_fm.get(_lvl) or 0) / _fm_tot, 1)
                    _np = round(100.0 * float(_nm.get(_lvl) or 0.0), 1)
                    pop_rows.append([_lvl, f"{_fp}%", f"{_np}%"])
            if _ci.get("outliers"):
                pop_rows.append(_header(["High-intensity NPI", "Avg level"]))
                for o in _ci["outliers"][:10]:
                    pop_rows.append([o["npi"], o["avg_level"]])
        _cond = _pop.get("conditions") or {}
        if _cond.get("prevalence"):
            pop_rows.append(_header(["Chronic condition", "Prevalence %"]))
            for p in _cond["prevalence"][:12]:
                pop_rows.append([p["condition"], f"{p['pct']}%"])
        if pop_rows:
            sheets.append(Sheet("Population", pop_rows,
                                col_widths=[42, 14, 12, 14]))

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

    try:
        from . import refdata as _rd
    except Exception:  # noqa: BLE001
        _rd = None

    # ---- Denials (CARC mix + playbook) — present in the exec HTML but the
    #      forwarded .xlsx never carried it. ----
    _den = sc.get("denials") or {}
    if _den.get("top"):
        den_rows: List[List[object]] = [
            _header(["Denial / adjustment reasons", "", "", ""]),
        ]
        if _den.get("preventable_pct") is not None:
            den_rows.append(
                [f"{_den['preventable_pct']}% of classified denial volume "
                 "was preventable by a pre-submission screen", "", "", ""])
        den_rows.append(_header(["Code", "Meaning", "Rows", "Playbook"]))
        import re as _re
        _pfx = _re.compile(r"^(?:CO|OA|PI|PR|CR)[-\s]?(?=[A-Z]?\d)")
        for d in _den["top"][:15]:
            code = str(d.get("code") or "").strip().upper()
            bare = _pfx.sub("", code)
            meaning = ""
            if _rd is not None:
                meaning = (_rd.carc_description(code)
                           or _rd.carc_description(bare) or "")
            pb = ""
            if d.get("category"):
                pb = f"[{d['category']}] {d.get('action', '')}"
            elif _rd is not None and bare != code:
                pb2 = _rd.carc_playbook(bare)
                if pb2:
                    pb = f"[{pb2['category']}] {pb2.get('action', '')}"
            den_rows.append([d.get("code"), meaning,
                             int(d.get("count") or 0), pb])
        sheets.append(Sheet("Denials", den_rows,
                            col_widths=[10, 48, 10, 52]))

    # ---- Compliance (OIG LEIE + PECOS) — a workbook that says nothing
    #      about excluded billing NPIs is not "the same verdict as the
    #      web UI". Guarded: only when the screens ran. ----
    _comp = res.compliance or []
    comp_rows: List[List[object]] = []
    for s in _comp:
        if not isinstance(s, dict) or s.get("id") == "error":
            continue
        comp_rows.append(_header([str(s.get("label") or s.get("id")), ""]))
        comp_rows.append(["Available",
                          "yes" if s.get("available") else "no"])
        comp_rows.append(["NPIs checked", int(s.get("checked") or 0)])
        if "excluded" in s:
            comp_rows.append(["Excluded (OIG match)",
                              int(s.get("excluded") or 0)])
        if "not_enrolled" in s:
            comp_rows.append(["Not enrolled (PECOS)",
                              int(s.get("not_enrolled") or 0)])
        if "opted_out" in s:
            comp_rows.append(["Opted out", int(s.get("opted_out") or 0)])
        if s.get("excluded_billed_total") is not None:
            comp_rows.append(["Billed $ via excluded NPIs",
                              round(float(s["excluded_billed_total"]), 2)])
        if s.get("note"):
            comp_rows.append(["Note", str(s.get("note"))])
        for m in (s.get("matches") or [])[:25]:
            bits = [str(m.get("npi") or "")]
            for k in ("name", "excl_type", "excl_date"):
                if m.get(k):
                    bits.append(str(m[k]))
            if m.get("billed") is not None:
                bits.append(f"billed ${float(m['billed']):,.2f}")
            comp_rows.append(["  ⚠ excluded", " · ".join(bits)])
        comp_rows.append(["", ""])
    if comp_rows:
        sheets.append(Sheet("Compliance", comp_rows, col_widths=[30, 64]))

    # ---- Charge outliers (per-HCPCS 3×IQR screen) — web-UI-only before. ----
    _outl = res.outliers or []
    if _outl:
        out_rows: List[List[object]] = [
            _header(["HCPCS", "Lines", "Outliers", "Median $", "Max $"])]
        for o in _outl:
            out_rows.append([o.get("code"), int(o.get("n") or 0),
                             int(o.get("outliers") or 0),
                             round(float(o.get("median") or 0.0), 2),
                             round(float(o.get("max") or 0.0), 2)])
        out_rows.append(["Fences are Tukey far-out (3×IQR) within each "
                         "HCPCS code seen ≥10 times.", "", "", "", ""])
        sheets.append(Sheet("Charge outliers", out_rows,
                            col_widths=[10, 10, 10, 12, 12]))

    # ---- Data dictionary — previously only a separate CSV download. ----
    _dict = res.dictionary or []
    if _dict:
        dict_rows: List[List[object]] = [
            _header(["Column", "Detected role", "Fill %", "Distinct",
                     "Sample values"])]
        for e in _dict:
            dict_rows.append([
                e.get("column"), e.get("role") or "—",
                e.get("fill_pct"),
                e.get("distinct") if e.get("distinct") is not None
                else ">1000",
                " · ".join(str(s) for s in (e.get("samples") or [])[:3])])
        sheets.append(Sheet("Dictionary", dict_rows,
                            col_widths=[26, 16, 8, 10, 44]))

    # ---- Suggested fixes companion (v49 suggested_fixes) ----
    recs = res.suggestions_records
    if recs:
        cols = list(recs[0].keys())
        fix_rows = [_header(cols)]
        for rec in recs[:_MAX_DATA_ROWS]:
            fix_rows.append([rec.get(c, "") for c in cols])
        sheets.append(Sheet("Suggested fixes", fix_rows,
                            col_widths=[12] * min(len(cols), 12)))

    # ---- Per-rule worklist tabs: the flagged rows, ready to hand to the
    #      source-system owner (top 5 rules, 200 rows each). Each tab
    #      leads with WHY the rows are here and WHAT to do, and when a
    #      billed/charge column is detectable the 200-row cap keeps the
    #      LARGEST-billed rows (dollar-ranked) instead of arbitrary early
    #      file order. ----
    flag_rows = getattr(res, "flag_rows", None) or {}
    _row_billed: dict = {}
    _billed_ci = None
    if flag_rows and headers:
        try:
            # Lazy + guarded: a detection failure degrades to file order,
            # never breaks the workbook.
            from .engine import _detect_one as _det_one, _to_number as _to_n
            _billed_ci = _det_one(list(headers),
                                  ("billedamt", "billed", "chargeamt",
                                   "charge", "submittedamt", "amount"))
            if _billed_ci is not None:
                for _i, _r in enumerate(rows, start=1):
                    if _billed_ci < len(_r):
                        _v = _to_n(_r[_billed_ci])
                        if _v is not None:
                            _row_billed[_i] = _v
        except Exception:  # noqa: BLE001
            _row_billed = {}
    try:
        from . import rules as _rules2
    except Exception:  # noqa: BLE001
        _rules2 = None
    for rule, idxs in sorted(flag_rows.items(),
                             key=lambda kv: -len(kv[1]))[:5]:
        sel = list(idxs)
        by_dollars = bool(_row_billed)
        if by_dollars:
            sel.sort(key=lambda i: -_row_billed.get(i, 0.0))
        sel = sel[:200]
        idx_set = set(sel)
        by_idx = {}
        for i, r in enumerate(rows, start=1):
            if i in idx_set:
                by_idx[i] = r
        if not by_idx:
            continue
        wl: List[list] = []
        info = _rules2.describe(rule) if _rules2 else {}
        if info:
            wl.append([(f"[{info.get('severity', '')}] "
                        f"{info.get('title') or rule}", _H)])
            _rem = (info.get("remediation") or "").strip()
            if _rem:
                wl.append(["What to do: " + _rem])
        wl.append(_header(["_row"] + list(headers)))
        for i in sel:
            if i in by_idx:
                wl.append([i] + list(by_idx[i]))
        if len(idxs) > 200 or by_dollars:
            note = ""
            if by_dollars:
                # The generic 'amount' hint can land on a paid-type column
                # (remit-side files) — say WHICH column ranked the rows
                # rather than claiming "billed $" for money that isn't.
                _col = str(headers[_billed_ci]) if (
                    _billed_ci is not None and _billed_ci < len(headers)
                ) else ""
                if any(h in _col.lower()
                       for h in ("billed", "charge", "submitted")):
                    note = "Sorted by billed $ descending. "
                else:
                    note = (f"Sorted by {_col} descending "
                            "(largest dollars first). ")
            if len(idxs) > 200:
                note += (f"{len(idxs) - 200} more flagged row(s) in the "
                         "full worklist CSV download.")
            if note.strip():
                wl.append([note.strip()])
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

    # ---- Connectors (coverage counters + plan + reference sources) ----
    # Guarded like every optional sheet: renders only when the run produced
    # any connector payload, so an offline run's workbook doesn't grow an
    # empty tab. Coverage counters (rows_seen/rows_enriched) come from
    # resolve_drugs; plan states from connectors.plan(); source health from
    # advanced.reference_status (vendor_adapter embeds connector_status()).
    _conns = [c for c in (res.connectors or [])
              if isinstance(c, dict) and c.get("id") != "error"]
    _orf = res.order_referring or {}
    _plan = [p for p in (res.connector_plan or []) if isinstance(p, dict)]
    _refst = []
    try:
        _refst = [r for r in ((res.advanced or {}).get("reference_status")
                              or []) if isinstance(r, dict)]
    except Exception:  # noqa: BLE001 — advanced may be any shape
        _refst = []
    if _conns or _plan or _refst or (_orf and not _orf.get("error")):
        cn_rows: List[list] = []
        if _conns:
            cn_rows.append(_header(["Connector", "Cells seen", "Enriched",
                                    "Result"]))
            for c in _conns:
                cn_rows.append([str(c.get("label") or c.get("id") or ""),
                                int(c.get("rows_seen") or 0),
                                int(c.get("rows_enriched") or 0),
                                str(c.get("note") or "")])
            cn_rows.append(["", "", "", ""])
        if _orf and not _orf.get("error"):
            cn_rows.append(_header(["Ordering/referring screen", "Checked",
                                    "Active", "Not found"]))
            cn_rows.append([", ".join(str(x) for x in
                                      (_orf.get("columns") or [])),
                            int(_orf.get("checked") or 0),
                            int(_orf.get("active") or 0),
                            int(_orf.get("not_found") or 0)])
            cn_rows.append(["", "", "", ""])
        if _plan:
            cn_rows.append(_header(["Applicable source", "Mode", "State",
                                    "Why / what to do"]))
            for p in _plan:
                if not p.get("applies"):
                    continue
                cn_rows.append([str(p.get("name") or p.get("id") or ""),
                                str(p.get("mode") or ""),
                                str(p.get("state") or ""),
                                str(p.get("reason") or "")])
            cn_rows.append(["", "", "", ""])
        if _refst:
            cn_rows.append(_header(["Reference source", "Status", "Vintage",
                                    "Note"]))
            for r in _refst:
                cn_rows.append([str(r.get("name") or r.get("id") or ""),
                                str(r.get("status") or ""),
                                str(r.get("vintage") or ""),
                                str(r.get("note") or "")])
        sheets.append(Sheet("Connectors", cn_rows,
                            col_widths=[34, 12, 12, 64]))

    # ---- Recovery gaps (SAD jurisdiction + dollar-ranked gap inventory) --
    # advanced.sad / advanced.gaps come from the offline vendor_adapter run
    # (connectors front); guarded so files without them grow no empty tab.
    _adv = res.advanced if isinstance(res.advanced, dict) else {}
    _sad = _adv.get("sad") if isinstance(_adv.get("sad"), dict) else {}
    _gapsd = _adv.get("gaps") if isinstance(_adv.get("gaps"), dict) else {}
    if _sad.get("rollup") or _gapsd.get("inventory"):
        rg_rows: List[list] = []
        if _sad.get("rollup"):
            rg_rows.append(_header(["SAD jurisdiction verdict", "Rows",
                                    "Dollars", "% of $"]))
            for rr in _sad["rollup"]:
                if not isinstance(rr, dict):
                    continue
                rg_rows.append([str(rr.get("verdict") or ""),
                                int(rr.get("rows") or 0),
                                round(float(rr.get("dollars") or 0.0), 2),
                                rr.get("pct_dollars")])
            for ar in (_sad.get("ambiguous") or [])[:15]:
                if isinstance(ar, dict):
                    rg_rows.append([
                        "  ambiguous: " + str(ar.get("hcpcs")
                                              or ar.get("code") or ""),
                        int(ar.get("rows") or 0),
                        round(float(ar.get("dollars") or 0.0), 2), ""])
            if _sad.get("note"):
                rg_rows.append([str(_sad["note"]), "", "", ""])
            rg_rows.append(["", "", "", ""])
        if _gapsd.get("inventory"):
            rg_rows.append(_header(["Recoverable gap", "Rows", "Dollars",
                                    "Recoverability / route"]))
            for g in _gapsd["inventory"]:
                if not isinstance(g, dict):
                    continue
                rg_rows.append([
                    str(g.get("gap") or ""), int(g.get("rows") or 0),
                    round(float(g.get("dollars") or 0.0), 2),
                    " — ".join(x for x in (str(g.get("recoverability")
                                               or ""),
                                           str(g.get("route") or "")) if x)])
            if _gapsd.get("total_gap_dollars") is not None:
                rg_rows.append([
                    "Total gap dollars", "",
                    round(float(_gapsd.get("total_gap_dollars") or 0.0), 2),
                    ""])
            if _gapsd.get("plan"):
                rg_rows.append(["", "", "", ""])
                rg_rows.append(_header(["Resolution plan", "", "Priority $",
                                        "Action"]))
                for pl in _gapsd["plan"]:
                    if not isinstance(pl, dict):
                        continue
                    rg_rows.append([
                        str(pl.get("gap") or ""), "",
                        round(float(pl.get("priority_dollars") or 0.0), 2),
                        str(pl.get("action") or "")])
        sheets.append(Sheet("Recovery gaps", rg_rows,
                            col_widths=[40, 10, 14, 70]))

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
