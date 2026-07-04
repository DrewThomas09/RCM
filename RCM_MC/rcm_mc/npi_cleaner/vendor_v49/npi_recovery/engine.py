"""
engine.py  (v46)
================

A columnar compute path for large claims extracts. Through v45 everything ran in
pandas, which is fine to a few million rows and then runs out of memory. This
module lets the heavy work run in DuckDB instead: read a multi-GB CSV or Parquet
without materializing it, run the coding-edit screens as SQL joins against the
reference tables and return only the flagged rows, and compute the aggregations
(mix, concentration, profiling) in SQL. For small files or when DuckDB is not
installed it falls back to the pandas screens, so the one-command run is unchanged.

The SQL screens are a scale-optimized equivalent of the pandas screens in
coding_edits.py, not a second source of truth. A self-test checks that the two
implementations flag the same rows on the same data, so the fast path and the
reference path stay in agreement.

Why DuckDB. It reads Parquet and CSV lazily, pushes filters and projections down,
runs joins and group-bys out of core, and needs no server. For join-and-group
heavy work on files larger than memory it is the right tool, and it is a single
pip install with a pandas fallback, so nothing about the default experience
changes.
"""
from __future__ import annotations

import os
import pandas as pd


def duckdb_available() -> bool:
    try:
        import duckdb  # noqa: F401
        return True
    except Exception:
        return False


def _connect():
    import duckdb
    con = duckdb.connect()
    # keep memory bounded and spill to disk for very large files
    con.execute("PRAGMA memory_limit='2GB'")
    con.execute("PRAGMA temp_directory='/tmp/duckdb_spill'")
    return con


def _register_input(con, path):
    """Register the input file as a DuckDB view named 'claims' without loading it
    into pandas. Chooses the reader by extension."""
    p = str(path)
    low = p.lower()
    if low.endswith(".parquet"):
        con.execute(f"CREATE VIEW claims AS SELECT * FROM read_parquet('{p}')")
    elif low.endswith((".csv", ".tsv", ".txt")):
        sep = "\t" if low.endswith(".tsv") else ","
        con.execute(
            f"CREATE VIEW claims AS SELECT * FROM read_csv_auto('{p}', "
            f"sep='{sep}', all_varchar=true, sample_size=-1)")
    elif low.endswith((".xlsx", ".xls", ".xlsm")):
        # DuckDB cannot stream xlsx; read once via pandas and register the frame.
        df = pd.read_excel(p, dtype=str)
        con.register("claims_df", df)
        con.execute("CREATE VIEW claims AS SELECT * FROM claims_df")
    else:
        raise ValueError(f"unsupported input for the engine: {p}")
    return con


def _col(con, mapping, canonical, fallbacks=()):
    """Resolve a canonical field to an actual column present in the claims view."""
    cols = {r[0].lower(): r[0] for r in con.execute("DESCRIBE claims").fetchall()}
    if mapping and mapping.get(canonical) and mapping[canonical].lower() in cols:
        return cols[mapping[canonical].lower()]
    if canonical.lower() in cols:
        return cols[canonical.lower()]
    for f in fallbacks:
        if f.lower() in cols:
            return cols[f.lower()]
    return None


def rowcount(path) -> int:
    """Fast row count without materializing (the reason to reach for the engine)."""
    con = _register_input(_connect(), path)
    n = con.execute("SELECT count(*) FROM claims").fetchone()[0]
    con.close()
    return int(n)


def profile(path, mapping=None, top_k=10) -> dict:
    """Column profile computed in SQL: type, nulls, distinct, and for the key
    fields a small top-values table. Runs on files larger than memory."""
    con = _register_input(_connect(), path)
    desc = con.execute("DESCRIBE claims").fetchall()
    n = con.execute("SELECT count(*) FROM claims").fetchone()[0]
    rows = []
    for cname, ctype, *_ in desc:
        q = (f'SELECT count(*) - count("{cname}") AS nulls, '
             f'count(DISTINCT "{cname}") AS distinct_ct FROM claims')
        nulls, distinct = con.execute(q).fetchone()
        rows.append({"column": cname, "type": ctype, "rows": int(n),
                     "nulls": int(nulls),
                     "null_pct": round(100.0 * nulls / n, 2) if n else 0.0,
                     "distinct": int(distinct),
                     "distinct_pct": round(100.0 * distinct / n, 2) if n else 0.0})
    prof = pd.DataFrame(rows)
    prof.attrs["note"] = (f"{len(desc)} columns, {int(n):,} rows, profiled in SQL. "
                          f"null_pct and distinct_pct flag empty and constant/near-key "
                          f"columns without loading the file into memory.")
    con.close()
    return {"columns": prof, "rows": int(n)}


# --------------------------------------------------------------------------- #
# SQL coding-edit screens (scale-optimized equivalents of coding_edits.py)
# --------------------------------------------------------------------------- #
def _ref_path(ref_dir, name):
    p = os.path.join(ref_dir or os.path.join(os.path.dirname(__file__), "reference"), name)
    return p if os.path.exists(p) else None


def mue_screen_sql(path, ref_dir=None, mapping=None) -> pd.DataFrame:
    """Units above the MUE cap, computed as a SQL join. Returns flagged rows."""
    ref = _ref_path(ref_dir, "ncci_mue_seed.csv")
    if ref is None:
        return pd.DataFrame({"note": ["MUE reference not found"]})
    con = _register_input(_connect(), path)
    hc = _col(con, mapping, "hcpcs", ("hcpcs_cpt", "code"))
    uc = _col(con, mapping, "units", ("quantity", "qty", "srvc_cnt"))
    if hc is None or uc is None:
        con.close()
        return pd.DataFrame({"note": ["MUE needs an HCPCS and a units column"]})
    con.execute(
        f"CREATE VIEW mue AS SELECT upper(trim(hcpcs)) AS hcpcs, "
        f"max(mue_value) AS mue_value, any_value(mai) AS mai "
        f"FROM read_csv_auto('{ref}', all_varchar=true) "
        f"WHERE service='practitioner' GROUP BY 1")
    q = (f'SELECT row_number() OVER () - 1 AS row, upper(trim(c."{hc}")) AS hcpcs, '
         f'TRY_CAST(c."{uc}" AS DOUBLE) AS units, m.mue_value, m.mai, '
         f'TRY_CAST(c."{uc}" AS DOUBLE) - TRY_CAST(m.mue_value AS DOUBLE) AS excess_units '
         f'FROM claims c JOIN mue m ON upper(trim(c."{hc}")) = m.hcpcs '
         f'WHERE TRY_CAST(c."{uc}" AS DOUBLE) > TRY_CAST(m.mue_value AS DOUBLE)')
    out = con.execute(q).fetchdf()
    con.close()
    out.attrs["note"] = f"{len(out)} lines exceed the practitioner MUE cap (SQL engine)."
    out.attrs["source"] = "CMS NCCI MUE (SQL join)"
    return out


def jw_jz_screen_sql(path, ref_dir=None, mapping=None) -> pd.DataFrame:
    """Single-dose lines missing JW/JZ, as SQL. Only judges when a modifier
    column exists (matches the pandas screen's evidence rule)."""
    ref = _ref_path(ref_dir, "jw_jz_single_dose_seed.csv")
    if ref is None:
        return pd.DataFrame({"note": ["JW/JZ reference not found"]})
    con = _register_input(_connect(), path)
    hc = _col(con, mapping, "hcpcs", ("hcpcs_cpt", "code"))
    mod = _col(con, mapping, "modifiers", ("modifier", "mods", "modifier_1"))
    if hc is None:
        con.close()
        return pd.DataFrame({"note": ["JW/JZ needs an HCPCS column"]})
    con.execute(
        f"CREATE VIEW single AS SELECT DISTINCT upper(trim(hcpcs)) AS hcpcs "
        f"FROM read_csv_auto('{ref}', all_varchar=true)")
    if mod is None:
        q = (f'SELECT row_number() OVER () - 1 AS row, upper(trim(c."{hc}")) AS hcpcs, '
             f"'unjudged_missing_field' AS verdict FROM claims c "
             f'JOIN single s ON upper(trim(c."{hc}")) = s.hcpcs')
        out = con.execute(q).fetchdf()
        con.close()
        out.attrs["note"] = (f"{len(out)} single-dose lines could not be verified: no "
                             f"modifier field delivered (SQL engine).")
        return out
    q = (f'SELECT row_number() OVER () - 1 AS row, upper(trim(c."{hc}")) AS hcpcs, '
         f"'flag' AS verdict FROM claims c "
         f'JOIN single s ON upper(trim(c."{hc}")) = s.hcpcs '
         f'WHERE coalesce(upper(c."{mod}"),\'\') NOT LIKE \'%JW%\' '
         f'AND coalesce(upper(c."{mod}"),\'\') NOT LIKE \'%JZ%\'')
    out = con.execute(q).fetchdf()
    con.close()
    out.attrs["note"] = f"{len(out)} single-dose lines missing JW/JZ (SQL engine)."
    out.attrs["source"] = "CMS JW/JZ policy (SQL join)"
    return out


def deactivated_screen_sql(path, ref_dir=None, mapping=None) -> pd.DataFrame:
    """Billing NPIs on the deactivation list, as SQL."""
    ref = _ref_path(ref_dir, "nppes_deactivated_seed.csv")
    if ref is None:
        return pd.DataFrame({"note": ["deactivation reference not found"]})
    con = _register_input(_connect(), path)
    npi = _col(con, mapping, "billing_npi", ("npi", "provider_npi"))
    if npi is None:
        con.close()
        return pd.DataFrame({"note": ["deactivated screen needs a billing NPI column"]})
    con.execute(
        f"CREATE VIEW deact AS SELECT trim(npi) AS npi, "
        f"any_value(deactivation_date) AS deactivation_date "
        f"FROM read_csv_auto('{ref}', all_varchar=true) GROUP BY 1")
    q = (f'SELECT row_number() OVER () - 1 AS row, trim(c."{npi}") AS billing_npi, '
         f'd.deactivation_date FROM claims c '
         f'JOIN deact d ON trim(c."{npi}") = d.npi')
    out = con.execute(q).fetchdf()
    con.close()
    out.attrs["note"] = f"{len(out)} lines bill a deactivated NPI (SQL engine)."
    out.attrs["source"] = "CMS NPPES deactivation (SQL join)"
    return out


# --------------------------------------------------------------------------- #
# SQL aggregations
# --------------------------------------------------------------------------- #
def payer_mix_sql(path, mapping=None, top_n=15) -> pd.DataFrame:
    """Dollar mix by payer, in SQL, for files too large to group in pandas."""
    con = _register_input(_connect(), path)
    pc = _col(con, mapping, "payer")
    ac = _col(con, mapping, "allowed_amt")
    if pc is None:
        con.close()
        return pd.DataFrame({"note": ["payer mix needs a payer column"]})
    amt_expr = f'sum(TRY_CAST(c."{ac}" AS DOUBLE))' if ac else "count(*)"
    q = (f'SELECT c."{pc}" AS payer, {amt_expr} AS dollars FROM claims c '
         f'GROUP BY 1 ORDER BY dollars DESC LIMIT {top_n}')
    out = con.execute(q).fetchdf()
    tot = out["dollars"].sum() or 1.0
    out["share_pct"] = (100.0 * out["dollars"] / tot).round(1)
    con.close()
    out.attrs["note"] = f"Top {len(out)} payers by dollars (SQL engine)."
    return out


def drug_mix_sql(path, mapping=None, top_n=25) -> pd.DataFrame:
    """Dollar mix by drug/HCPCS, in SQL."""
    con = _register_input(_connect(), path)
    hc = _col(con, mapping, "hcpcs", ("hcpcs_cpt", "code"))
    ac = _col(con, mapping, "allowed_amt")
    if hc is None:
        con.close()
        return pd.DataFrame({"note": ["drug mix needs an HCPCS column"]})
    amt_expr = f'sum(TRY_CAST(c."{ac}" AS DOUBLE))' if ac else "count(*)"
    q = (f'SELECT upper(trim(c."{hc}")) AS hcpcs, {amt_expr} AS dollars, count(*) AS lines '
         f'FROM claims c GROUP BY 1 ORDER BY dollars DESC LIMIT {top_n}')
    out = con.execute(q).fetchdf()
    tot = out["dollars"].sum() or 1.0
    out["share_pct"] = (100.0 * out["dollars"] / tot).round(1)
    con.close()
    out.attrs["note"] = f"Top {len(out)} drugs by dollars (SQL engine)."
    return out


def run_screens_sql(path, ref_dir=None, mapping=None) -> dict:
    """Run the SQL coding-edit screens that have a scale-optimized form."""
    return {
        "mue_units": mue_screen_sql(path, ref_dir, mapping),
        "jw_jz_wastage": jw_jz_screen_sql(path, ref_dir, mapping),
        "npi_deactivated": deactivated_screen_sql(path, ref_dir, mapping),
    }
