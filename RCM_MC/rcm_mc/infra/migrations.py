"""Schema migration registry.

Collects all ALTER TABLE / CREATE INDEX migrations in one place
with idempotent execution. Each migration runs inside a try/except
so already-applied changes are silently skipped (SQLite's ALTER TABLE
raises if the column already exists).

A migration's action may also be a callable taking the open connection
— used for changes ALTER TABLE cannot express, like the MR1059 FK
rebuild below (SQLite cannot add ON DELETE CASCADE to an existing FK).

Call ``run_pending(store)`` on server startup or store init to ensure
all migrations are applied.
"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Tuple, Union

logger = logging.getLogger(__name__)


# ── MR1057/MR1058/MR1059: deal-children FK CASCADE rebuild ────────────────
#
# The CASCADE clauses on these child tables only exist in fresh-DB DDL
# (CREATE TABLE IF NOT EXISTS is a no-op on live schemas), so any DB
# created before the FK hardening still has bare or missing FKs and
# silently orphans rows on deal deletion. SQLite cannot ALTER an FK, so
# each table is rebuilt via the documented 12-step pattern: purge
# orphans, create the corrected table under a temp name, copy the
# column intersection, drop the old table, rename, recreate indexes —
# all with foreign_keys OFF so sibling FK clauses are untouched.
#
# The DDL templates below are deliberate copies of the table schemas
# owned by deal_sim_inputs.py, deal_owners.py, health_score.py,
# deal_deadlines.py, watchlist.py, deal_tags.py, note_tags.py and
# portfolio_snapshots.py; the convergence test in
# tests/test_deal_children_fk_migration.py fails if either side drifts.
# They intentionally lack IF NOT EXISTS: each is instantiated under a
# fresh temp name that must not pre-exist.
_CASCADE_REBUILDS: List[Dict[str, Any]] = [
    {
        "table": "deal_sim_inputs",
        "parent": "deals",
        "purge": ("DELETE FROM deal_sim_inputs WHERE deal_id NOT IN "
                  "(SELECT deal_id FROM deals)"),
        "ddl": """CREATE TABLE {name} (
                deal_id TEXT PRIMARY KEY,
                actual_path TEXT NOT NULL,
                benchmark_path TEXT NOT NULL,
                outdir_base TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )""",
        "indexes": [],
    },
    {
        "table": "deal_owner_history",
        "parent": "deals",
        "purge": ("DELETE FROM deal_owner_history WHERE deal_id NOT IN "
                  "(SELECT deal_id FROM deals)"),
        "ddl": """CREATE TABLE {name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                owner TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )""",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_deal_owner_deal "
            "ON deal_owner_history(deal_id, assigned_at DESC)",
        ],
    },
    {
        "table": "deal_health_history",
        "parent": "deals",
        "purge": ("DELETE FROM deal_health_history WHERE deal_id NOT IN "
                  "(SELECT deal_id FROM deals)"),
        "ddl": """CREATE TABLE {name} (
                deal_id TEXT NOT NULL,
                at_date TEXT NOT NULL,
                score INTEGER NOT NULL,
                band TEXT NOT NULL,
                PRIMARY KEY (deal_id, at_date),
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )""",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_deal_health_history_date "
            "ON deal_health_history(deal_id, at_date DESC)",
        ],
    },
    {
        "table": "deal_deadlines",
        "parent": "deals",
        "purge": ("DELETE FROM deal_deadlines WHERE deal_id NOT IN "
                  "(SELECT deal_id FROM deals)"),
        "ddl": """CREATE TABLE {name} (
                deadline_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                label TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                notes TEXT NOT NULL DEFAULT '',
                owner TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )""",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_deal_deadlines_due "
            "ON deal_deadlines(status, due_date)",
            "CREATE INDEX IF NOT EXISTS idx_deal_deadlines_owner "
            "ON deal_deadlines(owner, status)",
        ],
    },
    {
        "table": "deal_stars",
        "parent": "deals",
        "purge": ("DELETE FROM deal_stars WHERE deal_id NOT IN "
                  "(SELECT deal_id FROM deals)"),
        "ddl": """CREATE TABLE {name} (
                deal_id TEXT PRIMARY KEY,
                starred_at TEXT NOT NULL,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )""",
        "indexes": [],
    },
    {
        "table": "deal_tags",
        "parent": "deals",
        "purge": ("DELETE FROM deal_tags WHERE deal_id NOT IN "
                  "(SELECT deal_id FROM deals)"),
        "ddl": """CREATE TABLE {name} (
                tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )""",
        "indexes": [
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_deal_tags_unique "
            "ON deal_tags(deal_id, tag)",
            "CREATE INDEX IF NOT EXISTS idx_deal_tags_tag ON deal_tags(tag)",
        ],
    },
    {
        "table": "note_tags",
        "parent": "deal_notes",
        "purge": ("DELETE FROM note_tags WHERE note_id NOT IN "
                  "(SELECT note_id FROM deal_notes)"),
        "ddl": """CREATE TABLE {name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                note_id INTEGER NOT NULL,
                tag TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(note_id) REFERENCES deal_notes(note_id)
                    ON DELETE CASCADE
            )""",
        "indexes": [
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_note_tags_unique "
            "ON note_tags(note_id, tag)",
            "CREATE INDEX IF NOT EXISTS idx_note_tags_tag "
            "ON note_tags(tag)",
        ],
    },
    {
        "table": "deal_snapshots",
        "parent": "deals",
        "purge": ("DELETE FROM deal_snapshots WHERE deal_id NOT IN "
                  "(SELECT deal_id FROM deals)"),
        "ddl": """CREATE TABLE {name} (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                created_at TEXT NOT NULL,
                run_dir TEXT,
                entry_ebitda REAL,
                entry_multiple REAL,
                exit_multiple REAL,
                hold_years REAL,
                moic REAL,
                irr REAL,
                entry_ev REAL,
                exit_ev REAL,
                covenant_leverage REAL,
                covenant_headroom_turns REAL,
                covenant_status TEXT,
                concerning_signals INTEGER,
                favorable_signals INTEGER,
                notes TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )""",
        "indexes": [
            "CREATE INDEX IF NOT EXISTS idx_snapshots_deal "
            "ON deal_snapshots(deal_id, created_at DESC)",
        ],
    },
]


def _has_cascade_fk(con: Any, table: str, parent: str) -> bool:
    rows = con.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    for row in rows:
        # sqlite3.Row or tuple: table name is column 2, on_delete column 6
        r_table = row["table"] if hasattr(row, "keys") else row[2]
        r_ondel = row["on_delete"] if hasattr(row, "keys") else row[6]
        if r_table == parent and str(r_ondel).upper() == "CASCADE":
            return True
    return False


def _rebuild_deal_children_fks(con: Any) -> None:
    """One-shot MR1059 rebuild: converge live DBs onto the CASCADE DDL.

    Skips tables that are missing (lazily created later with correct
    DDL) or already converged, so re-running is always safe.
    """
    con.commit()  # PRAGMA foreign_keys is a no-op inside a transaction
    con.execute("PRAGMA foreign_keys = OFF")
    try:
        for spec in _CASCADE_REBUILDS:
            table = spec["table"]
            exists = con.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not exists or _has_cascade_fk(con, table, spec["parent"]):
                continue
            tmp = f"_mr1059_new_{table}"
            con.execute("BEGIN IMMEDIATE")
            try:
                con.execute(spec["purge"])
                con.execute(f"DROP TABLE IF EXISTS {tmp}")
                con.execute(spec["ddl"].format(name=tmp))
                old_cols = [
                    r[1] for r in
                    con.execute(f"PRAGMA table_info({table})").fetchall()
                ]
                new_cols = [
                    r[1] for r in
                    con.execute(f"PRAGMA table_info({tmp})").fetchall()
                ]
                common = [c for c in new_cols if c in old_cols]
                col_list = ", ".join(common)
                con.execute(
                    f"INSERT INTO {tmp} ({col_list}) "
                    f"SELECT {col_list} FROM {table}"
                )
                con.execute(f"DROP TABLE {table}")
                con.execute(f"ALTER TABLE {tmp} RENAME TO {table}")
                for idx_sql in spec["indexes"]:
                    con.execute(idx_sql)
                con.commit()
                logger.info("MR1059 rebuild applied: %s", table)
            except Exception:
                con.rollback()
                logger.warning("MR1059 rebuild failed for %s", table,
                               exc_info=True)
    finally:
        con.execute("PRAGMA foreign_keys = ON")

_MIGRATIONS: List[Tuple[str, Union[str, Callable[[Any], None]]]] = [
    ("deals_archived_at",
     "ALTER TABLE deals ADD COLUMN archived_at TEXT"),
    ("audit_events_request_id",
     "ALTER TABLE audit_events ADD COLUMN request_id TEXT"),
    ("deal_notes_deleted_at",
     "ALTER TABLE deal_notes ADD COLUMN deleted_at TEXT"),
    ("deal_deadlines_owner",
     "ALTER TABLE deal_deadlines ADD COLUMN owner TEXT NOT NULL DEFAULT ''"),
    # B.1 — methodology versioning on the prediction ledger.
    # Existing rows backfill to 'pre-b1' via the DEFAULT clause.
    # New rows tagged 'b1-tuned-alpha' by record_prediction() default.
    # See rcm_mc/analysis/thresholds.py for the version-keyed threshold
    # tables and rcm_mc/ml/prediction_ledger.py for the write path.
    ("predictions_methodology_version",
     "ALTER TABLE predictions ADD COLUMN methodology_version TEXT DEFAULT 'pre-b1'"),
    ("predictions_cohort_alpha",
     "ALTER TABLE predictions ADD COLUMN cohort_alpha REAL"),
    # MR1057/MR1058/MR1059 — must run after the ADD COLUMN entries above
    # (deal_deadlines_owner in particular) so the rebuild copies the full
    # current column set.
    ("deal_children_fk_cascade_rebuild", _rebuild_deal_children_fks),
]


def run_pending(store: Any) -> int:
    """Execute all pending migrations. Returns count applied."""
    store.init_db()
    applied = 0
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS _migrations (
                name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )"""
        )
        con.commit()
        for name, sql in _MIGRATIONS:
            row = con.execute(
                "SELECT 1 FROM _migrations WHERE name = ?", (name,),
            ).fetchone()
            if row:
                continue
            from datetime import datetime, timezone
            try:
                if callable(sql):
                    sql(con)
                else:
                    con.execute(sql)
                con.commit()
                logger.info("migration applied: %s", name)
            except Exception:
                pass
            con.execute(
                "INSERT OR IGNORE INTO _migrations (name, applied_at) VALUES (?, ?)",
                (name, datetime.now(timezone.utc).isoformat()),
            )
            con.commit()
            applied += 1
    return applied


def list_applied(store: Any) -> List[str]:
    """Return names of already-applied migrations."""
    store.init_db()
    try:
        with store.connect() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS _migrations "
                "(name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            rows = con.execute(
                "SELECT name FROM _migrations ORDER BY name"
            ).fetchall()
        return [r["name"] for r in rows]
    except Exception:
        return []
