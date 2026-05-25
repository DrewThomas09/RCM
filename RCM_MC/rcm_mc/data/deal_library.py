"""Deal Library loader + read API.

Loads the normalized company library (produced offline by
``scripts/ingest_deal_library_exports.py`` from user-licensed exports) into
SQLite, and exposes read helpers for the Deal Library page, Find Comps, and
modeling priors.

Provenance is first-class: every row carries source_system / source_file /
source_row_id and a missing_fields list, and missing numerics are stored as
NULL (never 0) so downstream code can honor missingness instead of inventing
values. The licensed CSV itself is never committed (see
data/vendor/deal_library/.gitignore) — only this loader and a synthetic test
fixture are tracked.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

_TEXT_COLS = [
    "company_id", "source_system", "source_batch_id", "source_file",
    "source_sheet", "source_row_id", "ticker", "company_name", "clean_name",
    "industry", "ownership_status", "sponsor_owner", "company_status",
    "website", "address", "geography", "state", "missing_fields",
    "provenance_note",
]
_NUM_COLS = ["enterprise_value", "ebitda", "revenue", "market_cap",
             "employees", "amount_raised", "completeness_score"]
_INT_COLS = ["duplicate_candidate"]
_ALL_COLS = _TEXT_COLS + _NUM_COLS + _INT_COLS

# Columns a user may sort/filter on from the page (allow-list → no SQL
# injection via sort param; everything else is rejected).
SORTABLE = {"company_name", "sponsor_owner", "industry", "state", "geography",
            "revenue", "ebitda", "enterprise_value", "amount_raised",
            "employees", "completeness_score", "company_status"}
FILTERABLE = {"source_system", "state", "company_status", "sponsor_owner",
              "industry", "geography"}


def _ensure_table(store: Any) -> None:
    cols_sql = ",\n  ".join(
        [f"{c} TEXT" for c in _TEXT_COLS]
        + [f"{c} REAL" for c in _NUM_COLS]
        + [f"{c} INTEGER" for c in _INT_COLS]
    )
    with store.connect() as con:
        con.execute(f"CREATE TABLE IF NOT EXISTS deal_library_companies (\n"
                    f"  {cols_sql},\n  PRIMARY KEY (company_id)\n)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_dlc_sponsor "
                    "ON deal_library_companies(sponsor_owner)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_dlc_state "
                    "ON deal_library_companies(state)")
        con.commit()


def _coerce(row: Dict[str, str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for c in _TEXT_COLS:
        v = row.get(c)
        out[c] = v if (v is not None and str(v) != "") else None
    for c in _NUM_COLS:
        v = row.get(c)
        try:
            out[c] = float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            out[c] = None
    for c in _INT_COLS:
        v = row.get(c)
        try:
            out[c] = int(float(v)) if v not in (None, "") else 0
        except (TypeError, ValueError):
            out[c] = 0
    return out


def load_companies_csv(store: Any, csv_path: str | Path) -> int:
    """Upsert the normalized ``deal_library_companies.csv`` into SQLite.
    Returns rows written. Idempotent on ``company_id``."""
    _ensure_table(store)
    p = Path(csv_path)
    placeholders = ",".join("?" for _ in _ALL_COLS)
    updates = ",".join(f"{c}=excluded.{c}" for c in _ALL_COLS if c != "company_id")
    n = 0
    with store.connect() as con, p.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rec = _coerce(row)
            con.execute(
                f"INSERT INTO deal_library_companies ({','.join(_ALL_COLS)}) "
                f"VALUES ({placeholders}) "
                f"ON CONFLICT(company_id) DO UPDATE SET {updates}",
                [rec.get(c) for c in _ALL_COLS],
            )
            n += 1
        con.commit()
    return n


# ── read API (page / comps / priors) ──────────────────────────────────────
def count(store: Any) -> int:
    _ensure_table(store)
    with store.connect() as con:
        return con.execute("SELECT COUNT(*) FROM deal_library_companies").fetchone()[0]


def source_breakdown(store: Any) -> List[Dict[str, Any]]:
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT source_system, COUNT(*) n FROM deal_library_companies "
            "GROUP BY source_system ORDER BY n DESC").fetchall()
    return [{"source_system": r[0], "n": r[1]} for r in rows]


def top_values(store: Any, column: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Frequency table for a categorical column (sponsor/industry/state/…).
    Column is allow-listed to prevent injection."""
    if column not in FILTERABLE:
        raise ValueError(f"not a filterable column: {column}")
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            f"SELECT {column}, COUNT(*) n FROM deal_library_companies "
            f"WHERE {column} IS NOT NULL AND {column} != '' "
            f"GROUP BY {column} ORDER BY n DESC LIMIT ?", (int(limit),)).fetchall()
    return [{"value": r[0], "n": r[1]} for r in rows]


def field_missingness(store: Any) -> Dict[str, float]:
    """Percent NULL per core numeric/text field — surfaced on the page so a
    user sees how sparse the licensed export actually is."""
    _ensure_table(store)
    fields = ["revenue", "ebitda", "enterprise_value", "amount_raised",
              "employees", "website", "ticker", "state", "sponsor_owner"]
    with store.connect() as con:
        total = con.execute("SELECT COUNT(*) FROM deal_library_companies").fetchone()[0]
        if not total:
            return {f: 0.0 for f in fields}
        out = {}
        for f in fields:
            empty = con.execute(
                f"SELECT COUNT(*) FROM deal_library_companies "
                f"WHERE {f} IS NULL OR {f} = ''").fetchone()[0]
            out[f] = round(100 * empty / total, 1)
    return out


def query(
    store: Any, *, filters: Optional[Dict[str, str]] = None,
    search: Optional[str] = None, sort_by: str = "company_name",
    sort_dir: str = "asc", limit: int = 50, offset: int = 0,
) -> Dict[str, Any]:
    """Filtered/sorted/paginated read for the page. All column names are
    allow-listed; values are parameter-bound. Returns ``{total, rows}``."""
    _ensure_table(store)
    where, params = [], []
    for col, val in (filters or {}).items():
        if col in FILTERABLE and val:
            where.append(f"{col} = ?")
            params.append(val)
    if search:
        where.append("(company_name LIKE ? OR sponsor_owner LIKE ? OR industry LIKE ?)")
        like = f"%{search}%"
        params += [like, like, like]
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sort_col = sort_by if sort_by in SORTABLE else "company_name"
    direction = "DESC" if str(sort_dir).lower() == "desc" else "ASC"
    # NULLs last for numeric sorts so missing values don't masquerade as lowest.
    null_order = f"({sort_col} IS NULL), " if sort_col in _NUM_COLS else ""
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    with store.connect() as con:
        total = con.execute(
            f"SELECT COUNT(*) FROM deal_library_companies{where_sql}", params
        ).fetchone()[0]
        cur = con.execute(
            f"SELECT * FROM deal_library_companies{where_sql} "
            f"ORDER BY {null_order}{sort_col} {direction} LIMIT ? OFFSET ?",
            params + [limit, offset])
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return {"total": total, "rows": rows}


# ── sponsor intelligence ───────────────────────────────────────────────────
# The dense, validated dimension of this dataset: ~99% of rows carry a parsed
# sponsor, across ~4,900 distinct sponsors (a mix of PE, VC/accelerators, and
# healthcare REITs — the broad "sponsor-backed" universe, not PE-buyout only).
def sponsor_count(store: Any, *, min_companies: int = 1,
                  name_like: Optional[str] = None) -> int:
    """Number of distinct sponsors matching the filters (for pagination)."""
    _ensure_table(store)
    where = ["sponsor_owner IS NOT NULL", "sponsor_owner != ''"]
    params: List[Any] = []
    if name_like:
        where.append("sponsor_owner LIKE ?")
        params.append(f"%{name_like}%")
    with store.connect() as con:
        rows = con.execute(
            f"SELECT sponsor_owner FROM deal_library_companies "
            f"WHERE {' AND '.join(where)} GROUP BY sponsor_owner "
            f"HAVING COUNT(*) >= ?", params + [int(min_companies)]).fetchall()
    return len(rows)


def sponsor_index(store: Any, *, limit: int = 100, offset: int = 0,
                  min_companies: int = 1, name_like: Optional[str] = None
                  ) -> List[Dict[str, Any]]:
    """Sponsors ranked by # of healthcare companies backed, with the
    current/prior split (read from the raw ownership_status). Useful as a
    sourcing / sponsor-activity map. ``name_like`` does a substring search;
    ``offset``/``limit`` paginate."""
    _ensure_table(store)
    where = ["sponsor_owner IS NOT NULL", "sponsor_owner != ''"]
    params: List[Any] = []
    if name_like:
        where.append("sponsor_owner LIKE ?")
        params.append(f"%{name_like}%")
    with store.connect() as con:
        rows = con.execute(
            f"""
            SELECT sponsor_owner,
                   COUNT(*) AS n_total,
                   SUM(CASE WHEN lower(ownership_status) LIKE '%current sponsor%'
                            THEN 1 ELSE 0 END) AS n_current,
                   SUM(CASE WHEN lower(ownership_status) LIKE '%prior sponsor%'
                            THEN 1 ELSE 0 END) AS n_prior
            FROM deal_library_companies
            WHERE {' AND '.join(where)}
            GROUP BY sponsor_owner
            HAVING n_total >= ?
            ORDER BY n_total DESC, sponsor_owner ASC
            LIMIT ? OFFSET ?
            """,
            params + [int(min_companies), max(1, min(int(limit), 500)), max(0, int(offset))],
        ).fetchall()
    return [{"sponsor": r[0], "n_total": r[1], "n_current": r[2],
             "n_prior": r[3]} for r in rows]


def sponsor_rollup(store: Any, sponsor: str) -> Dict[str, Any]:
    """One sponsor's healthcare footprint: company count, current/prior split,
    how many disclose revenue, and its top states. Returns ``n_total=0`` for an
    unknown sponsor (never invents)."""
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN lower(ownership_status) LIKE '%current sponsor%'
                            THEN 1 ELSE 0 END),
                   SUM(CASE WHEN lower(ownership_status) LIKE '%prior sponsor%'
                            THEN 1 ELSE 0 END),
                   SUM(CASE WHEN revenue IS NOT NULL THEN 1 ELSE 0 END)
            FROM deal_library_companies WHERE sponsor_owner = ?
            """, (sponsor,)).fetchone()
        states = con.execute(
            "SELECT state, COUNT(*) n FROM deal_library_companies "
            "WHERE sponsor_owner = ? AND state IS NOT NULL AND state != '' "
            "GROUP BY state ORDER BY n DESC LIMIT 6", (sponsor,)).fetchall()
    return {
        "sponsor": sponsor,
        "n_total": row[0] or 0,
        "n_current": row[1] or 0,
        "n_prior": row[2] or 0,
        "n_with_revenue": row[3] or 0,
        "top_states": [{"state": s[0], "n": s[1]} for s in states],
    }
