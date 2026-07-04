"""v22: polished filled-output writer (xlsxwriter).

The default openpyxl writer is correct but plain, and in write-only mode (needed
for 600k-row files) it cannot freeze panes or set reliable column widths.
xlsxwriter does both in constant-memory streaming mode, so this builds the same
deliverable but readable at a glance:

  * a leading SUMMARY sheet (rows, cell-state breakdown, billing-NPI confidence
    split, connector audit count) — the one-glance view;
  * Filled_Data with a styled frozen header, autofilter, fitted column widths,
    and per-cell colour that GROUPS the data by trust: observed cells plain,
    recovered cells light blue, best-guess cells amber, unrecoverable tokens
    grey — so "what can I stand behind" is visible without reading a single
    audit column;
  * Column_Guide, Fill_Summary, Could_Not_Fill, Token_Legend.

xlsxwriter is optional. report.write_filled falls back to the openpyxl writer if
it isn't installed, so nothing breaks.
"""

from __future__ import annotations

import pandas as pd

from .fill import TOK, NAP

# tokens that mean "no observable value" -> grey; best-guess -> amber (a lead)
_GREY_TOKENS = {v for k, v in TOK.items() if k != "bestguess"}
_AMBER_TOKENS = {TOK["bestguess"]}


def xlsxwriter_available() -> bool:
    try:
        import xlsxwriter  # noqa: F401
        return True
    except Exception:
        return False


def _col_widths(df, sample=400, lo=9, hi=44):
    """Fitted width per column from a sample of the data (capped)."""
    head = df.head(sample)
    widths = []
    for c in df.columns:
        m = len(str(c))
        if len(head):
            m = max(m, int(head[c].astype("string").fillna("").str.len().max() or 0))
        widths.append(max(lo, min(hi, m + 2)))
    return widths


def _cell_state(value, is_source_col):
    """Return a style key for a cell: 'grey' / 'amber' / 'blue' / None."""
    s = "" if value is None else str(value).strip()
    if s in _GREY_TOKENS:
        return "grey"
    if s in _AMBER_TOKENS:
        return "amber"
    if is_source_col:
        sl = s.lower()
        if sl.startswith(("recovered", "inferred")):
            return "blue"
        if sl == "best-guess":
            return "amber"
        if sl == "missing":
            return "grey"
    return None


def write_filled_pretty(result, out_path, which="statistical"):
    import xlsxwriter

    if which == "verified":
        filled, fs, gaps = result.filled_verified, result.fill_summary_verified, result.fill_gaps_verified
    elif which == "statistical_full":
        filled = getattr(result, "filled_statistical_full", None)
        fs, gaps = result.fill_summary, result.fill_gaps
    else:
        filled, fs, gaps = result.filled, result.fill_summary, result.fill_gaps
    if filled is None:
        filled = pd.DataFrame()
    attrs = fs.attrs if (fs is not None and not fs.empty) else {}
    stats = getattr(result, "stats", {}) or {}
    conn = getattr(result, "connector_status", []) or []

    wb = xlsxwriter.Workbook(out_path, {"constant_memory": True, "in_memory": True})

    # ---- formats ----
    f_title = wb.add_format({"bold": True, "font_size": 15, "font_color": "#1F3864"})
    f_sub = wb.add_format({"font_size": 10, "font_color": "#595959", "text_wrap": True, "valign": "top"})
    f_h = wb.add_format({"bold": True, "font_color": "white", "bg_color": "#1F4E78",
                         "border": 1, "border_color": "#D9D9D9", "align": "left", "valign": "vcenter"})
    f_h_audit = wb.add_format({"bold": True, "font_color": "white", "bg_color": "#2E75B6",
                               "border": 1, "border_color": "#D9D9D9", "valign": "vcenter"})
    f_grey = wb.add_format({"bg_color": "#F2F2F2", "font_color": "#7F7F7F"})
    f_amber = wb.add_format({"bg_color": "#FFF2CC"})
    f_blue = wb.add_format({"bg_color": "#DDEBF7"})
    f_plain = wb.add_format({})
    f_kh = wb.add_format({"bold": True, "font_color": "white", "bg_color": "#1F4E78", "border": 1})
    f_k = wb.add_format({"border": 1, "border_color": "#E0E0E0"})
    f_kb = wb.add_format({"border": 1, "border_color": "#E0E0E0", "bold": True})
    f_pct = wb.add_format({"border": 1, "border_color": "#E0E0E0", "num_format": "0.0%"})
    fills = {"grey": f_grey, "amber": f_amber, "blue": f_blue, None: f_plain}
    # number formats — commas make dollar and count columns readable at a glance
    f_money = wb.add_format({"num_format": "#,##0.00"})
    f_int = wb.add_format({"num_format": "#,##0"})
    f_year = wb.add_format({"num_format": "0"})
    f_k_num = wb.add_format({"border": 1, "border_color": "#E0E0E0", "num_format": "#,##0"})

    def _to_number(v):
        if v is None:
            return None
        if isinstance(v, (int, float)) and not (isinstance(v, float) and v != v):
            return v
        s = str(v).strip().replace(",", "").replace("$", "")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None

    def _numfmt_for(colname, series):
        nm = str(colname).lower()
        # never format identifiers as numbers — NPI/ZIP/codes must keep leading
        # zeros and no thousands separators
        if any(k in nm for k in ("npi", "zip", "code", "hcpcs", "ndc", "_id", "id_", "taxonomy", "ccn", "phone")):
            return None
        is_amount = any(k in nm for k in ("amt", "amount", "allow", "paid", "charge", "cost", "dollar", "reimb", "price"))
        is_count = any(k in nm for k in ("unit", "qty", "quantity", "count", "srvc", "servic", "benef", "days"))
        is_year = "year" in nm or nm.endswith("_yr") or nm == "yr"
        if not (is_amount or is_count or is_year):
            return None
        sample = series.dropna().astype("string").str.strip()
        sample = sample[sample.str.len() > 0].head(200)
        if len(sample) == 0:
            return None
        numlike = sample.str.match(r"^-?\$?[\d,]+(\.\d+)?$")
        if float(numlike.mean()) < 0.95:   # mostly numeric content required
            return None
        return f_year if is_year else (f_money if is_amount else f_int)

    # ================= SUMMARY (leading, one-glance) =================
    ws = wb.add_worksheet("Summary"); ws.set_tab_color("#2E7D32")
    ws.set_column(0, 0, 42); ws.set_column(1, 3, 18)
    ws.hide_gridlines(2)
    build = {
        "verified": "1 · CLOSED CLAIMS — observed values + direct lookups only (no inference)",
        "statistical": "2 · RECOVERED CLAIMS — + measured recovery (point-attributed, ~89% k-fold)",
        "statistical_full": "3 · STATISTICALLY FILLED — + best-guess estimates · REQUIRES REVIEW",
    }.get(which, "STATISTICAL")
    ws.write(0, 0, "NPI Recovery & Cleaner — Summary", f_title)
    ws.write(1, 0, f"Output: {build}", f_sub)
    r = 3

    n_rows = len(filled)
    n_cols_data = len([c for c in filled.columns if not str(c).startswith("_")])
    n_live = sum(1 for x in conn if x.get("ok"))
    n_tot = len(conn)

    def kv(label, value, bold=False):
        nonlocal r
        ws.write(r, 0, label, f_kb if bold else f_k)
        if isinstance(value, int) and not isinstance(value, bool):
            ws.write_number(r, 1, value, f_k_num)
        else:
            ws.write(r, 1, value, f_kb if bold else f_k)
        r += 1

    ws.write(r, 0, "AT A GLANCE", f_kh); ws.write(r, 1, "", f_kh); r += 1
    kv("Rows (deduplicated)", n_rows)
    kv("Original data columns", n_cols_data)
    kv("Duplicate rows removed", int(attrs.get("n_dupes_removed", 0)))
    kv("Blank data cells remaining", 0, bold=True)
    kv("Connectors live this run", f"{n_live} / {n_tot}" if n_tot else "audit skipped")
    r += 1

    # billing-NPI confidence split (dollar-weighted, from fill attrs)
    ws.write(r, 0, "BILLING NPI — how it was filled", f_kh); ws.write(r, 1, "rows", f_kh)
    ws.write(r, 2, "% of gap $", f_kh); r += 1
    blank_rows = int(attrs.get("blank_rows", 0) or 0)
    rows_split = [
        ("Observed in your source", int(stats.get("filled_rows_out", n_rows)) - blank_rows, None),
        ("Recovered — high confidence (point)", int(attrs.get("bill_high_rows", 0) or 0),
         attrs.get("bill_high_pct_dollars")),
        ("Best-guess (below bar, see _NPI_BestGuess)", int(attrs.get("bill_lowguess_rows", 0) or 0),
         attrs.get("bill_lowguess_pct_dollars")),
        ("Unrecoverable (token + reason)", int(attrs.get("bill_na_rows", 0) or 0),
         attrs.get("bill_na_pct_dollars")),
    ]
    for label, rows_n, pctd in rows_split:
        ws.write(r, 0, label, f_k); ws.write(r, 1, rows_n, f_k)
        if pctd is None:
            ws.write(r, 2, "", f_k)
        else:
            ws.write(r, 2, float(pctd) / 100.0, f_pct)
        r += 1
    r += 1

    # per-column fill (from fill_summary)
    if fs is not None and not fs.empty:
        ws.write(r, 0, "PER-COLUMN FILL", f_kh)
        ws.write(r, 1, "missing", f_kh); ws.write(r, 2, "filled", f_kh); ws.write(r, 3, "labeled", f_kh); r += 1
        for _, row in fs.iterrows():
            ws.write(r, 0, str(row.get("column", "")), f_k)
            ws.write(r, 1, int(row.get("missing_before", 0)), f_k)
            ws.write(r, 2, int(row.get("filled", 0)), f_k)
            ws.write(r, 3, int(row.get("still_NA", 0)), f_k)
            r += 1
    r += 1
    ws.write(r, 0, "Colour key in Filled_Data: ", f_sub); r += 1
    for label, fmt in [("  observed (your data / verified)", f_plain),
                       ("  recovered — high confidence", f_blue),
                       ("  best-guess — verify before use", f_amber),
                       ("  unrecoverable — see token + Token_Legend", f_grey)]:
        ws.write(r, 0, label, fmt); r += 1

    # ================= FILLED_DATA (formatted) =================
    ws2 = wb.add_worksheet("Filled_Data"); ws2.set_tab_color("#1F4E78")
    cols = list(filled.columns)
    if cols:
        widths = _col_widths(filled)
        for c, w in enumerate(widths):
            ws2.set_column(c, c, w)
        for c, name in enumerate(cols):
            ws2.write(0, c, str(name), f_h_audit if str(name).startswith("_") else f_h)
        ws2.set_row(0, 26)  # taller header band
        src_idx = {i for i, c in enumerate(cols) if str(c) == "_NPI_Source"}
        numfmt = [_numfmt_for(c, filled[c]) for c in cols]
        for ri, row in enumerate(filled.itertuples(index=False, name=None), start=1):
            for ci, v in enumerate(row):
                nf = numfmt[ci]
                if nf is not None:                       # numeric column: comma format, no token colour
                    fv = _to_number(v)
                    if fv is None:
                        ws2.write(ri, ci, "" if v is None else v)
                    else:
                        ws2.write_number(ri, ci, fv, nf)
                    continue
                state = _cell_state(v, ci in src_idx)
                val = "" if v is None else v
                if state:
                    ws2.write(ri, ci, val, fills[state])
                else:
                    ws2.write(ri, ci, val)
        ws2.freeze_panes(1, 1)                    # header row + first column
        ws2.autofilter(0, 0, len(filled), len(cols) - 1)
    else:
        ws2.write(0, 0, "(no rows)")

    # ================= COLUMN_GUIDE =================
    wsg = wb.add_worksheet("Column_Guide"); wsg.set_tab_color("#A6A6A6")
    wsg.set_column(0, 0, 26); wsg.set_column(1, 1, 90); wsg.set_column(2, 2, 30)
    wsg.write(0, 0, "HOW TO READ THIS FILE", f_title)
    guide_intro = [
        "Your original data, cleaned and made analysis-ready. Every column you uploaded is preserved.",
        "Columns starting with \"_\" were ADDED for analysis. Original columns are never silently overwritten "
        "with an estimate — any recovered billing NPI is marked in _NPI_Source and scored in _NPI_Confidence.",
        "Every data cell is populated: an observed value, a recovered value, or a specific token explaining why "
        "no value is observable (see the Token_Legend sheet). Filter _NPI_Source='original' for a clean subset.",
    ]
    rr = 1
    for line in guide_intro:
        wsg.write(rr, 0, "", f_plain); wsg.write(rr, 1, line, f_sub); rr += 1
    rr += 1
    wsg.write(rr, 0, "column", f_kh); wsg.write(rr, 1, "what it means", f_kh); wsg.write(rr, 2, "source", f_kh); rr += 1
    present = set(filled.columns)
    guide = [
        ("Billing_NPI_Final", "Cleaned billing NPI: your value where present and valid, else the recovered one (Luhn-validated).", "your data + recovery"),
        ("_NPI_Source", "original / recovered (point) / inferred (sibling) / best-guess / missing.", "recovery engine"),
        ("_NPI_Confidence", "Measured k-fold hit-rate for a recovered NPI; blank for 'original'.", "k-fold backtest"),
        ("_NPI_BestGuess", "Ranked candidate billers for below-bar rows — a lead to verify, never a fact.", "recovery engine"),
        ("_NPI_Deactivated", "NPPES deactivation date if the NPI is retired (blank/em-dash = active).", "CMS NPPES deactivation file"),
        ("_Billing_Parent_Group", "Parent operator this NPI rolls up to (PAC-ID + address/name/DBA + Splink fuzzy).", "NPPES clustering + Splink"),
        ("_Billing_Parent_NPI_Count", "How many distinct NPIs roll up to that parent. >1 = multi-entity operator.", "entity resolution"),
        ("_Drug_Ingredient", "Active ingredient(s), from NDC or drug-name text.", "RxNorm / NLM"),
        ("_Drug_Class", "Therapeutic class of the drug.", "RxNorm ATC"),
        ("_Benefit_Channel", "Medical (Part B) vs pharmacy (Part D) benefit — drives NPI interpretation.", "HCPCS routing"),
        ("_Billing_Facility_Affil", "Billing provider's facility affiliation(s).", "CMS Facility Affiliation"),
        ("_Facility_Ownership", "Ownership type of the affiliated hospital (a PE-relevant signal).", "CMS Hospital Info"),
        ("_Billing_All_Specialties", "Full taxonomy set from NPPES, not just the primary.", "CMS NPPES"),
        ("_Referring_PaidByDrugMaker", "'Y' if the referring physician took manufacturer payments for this drug (KOL flag).", "CMS Open Payments"),
        ("_Operator_Recovery_Precision", "Historical reliability of THIS operator label: how often, in the back-test, a row the engine attributed to this operator was truly that operator. Rides alongside _NPI_Confidence (tier-level); blank if the operator is UNMEASURABLE. NOT proof this specific row is right.", "Backtest_ByOperator"),
        ("_Operator_Recovery_Verdict", "The operator's leaderboard verdict (HIGH_CONFIDENCE_RECOVERABLE / MODERATE / LOW_CONFIDENCE / INSUFFICIENT_HOLDOUT / UNMEASURABLE). Operator-level read; use with _NPI_Confidence, never instead of it.", "Backtest_ByOperator"),
        ("_Cells_Filled", "Per-row provenance: which cells the tool filled, and how.", "this tool"),
    ]
    for col, desc, src in guide:
        if col not in present and col != "Billing_NPI_Final":
            continue
        wsg.write(rr, 0, col, f_kb); wsg.write(rr, 1, desc, f_k); wsg.write(rr, 2, src, f_k); rr += 1

    # ================= FILL_SUMMARY =================
    ws3 = wb.add_worksheet("Fill_Summary"); ws3.set_tab_color("#A6A6A6")
    ws3.set_column(0, 0, 34); ws3.set_column(1, 4, 16)
    ws3.write(0, 0, "FILL SUMMARY", f_title)
    note = str(attrs.get("method_note", ""))
    ws3.merge_range(1, 0, 1, 4, note, f_sub) if note else None
    rr = 3
    if fs is not None and not fs.empty:
        headers = list(fs.columns)
        for c, h in enumerate(headers):
            ws3.write(rr, c, str(h), f_kh)
        rr += 1
        for _, row in fs.iterrows():
            for c, h in enumerate(headers):
                v = row[h]
                ws3.write(rr, c, int(v) if (isinstance(v, (int, float)) and h != "pct_reduction") else v, f_k)
            rr += 1

    # ================= COULD_NOT_FILL =================
    ws4 = wb.add_worksheet("Could_Not_Fill"); ws4.set_tab_color("#A6A6A6")
    ws4.set_column(0, 0, 28); ws4.set_column(1, 1, 16); ws4.set_column(2, 2, 16); ws4.set_column(3, 3, 70)
    ws4.write(0, 0, "COULD NOT FILL — cells with no observable value (now carry a reason token)", f_title)
    rr = 2
    if gaps is not None and not gaps.empty:
        headers = list(gaps.columns)
        for c, h in enumerate(headers):
            ws4.write(rr, c, str(h), f_kh)
        rr += 1
        for _, row in gaps.iterrows():
            for c, h in enumerate(headers):
                ws4.write(rr, c, row[h], f_k)
            rr += 1

    wb.close()
    return out_path
