"""Regression tests for the deals FK-correctness pass (Report-0263).

Covers three TRIAGE items fixed together:

- MR1068: ``PortfolioStore.delete_deal`` previously listed four child
  tables under wrong names (deal_owners / deal_stages / health_scores /
  watchlist) plus five phantoms, with a blanket except swallowing the
  "no such table" errors — silently orphaning rows on pre-CASCADE DBs.
- MR1058: deal_tags / note_tags / deal_snapshots FKs upgraded to
  ON DELETE CASCADE in fresh-DB DDL.
- MR1059: live DBs created before the CASCADE DDL converge via the
  one-shot rebuild migration (orphan purge + table rebuild + index
  recreation), registered as ``deal_children_fk_cascade_rebuild``.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.infra.migrations import _CASCADE_REBUILDS, run_pending

# The 8 tables the MR1059 rebuild owns, with their FK parent.
_REBUILT = {spec["table"]: spec["parent"] for spec in _CASCADE_REBUILDS}

# Legacy (pre-CASCADE) DDL as it shipped before the FK hardening: same
# columns, bare or missing FK clauses. This is what a live partner DB
# created in early 2026 actually contains.
_LEGACY_DDL = {
    "deal_sim_inputs": """CREATE TABLE deal_sim_inputs (
        deal_id TEXT PRIMARY KEY,
        actual_path TEXT NOT NULL,
        benchmark_path TEXT NOT NULL,
        outdir_base TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL)""",
    "deal_owner_history": """CREATE TABLE deal_owner_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deal_id TEXT NOT NULL,
        owner TEXT NOT NULL,
        assigned_at TEXT NOT NULL,
        note TEXT NOT NULL DEFAULT '')""",
    "deal_health_history": """CREATE TABLE deal_health_history (
        deal_id TEXT NOT NULL,
        at_date TEXT NOT NULL,
        score INTEGER NOT NULL,
        band TEXT NOT NULL,
        PRIMARY KEY (deal_id, at_date))""",
    "deal_deadlines": """CREATE TABLE deal_deadlines (
        deadline_id INTEGER PRIMARY KEY AUTOINCREMENT,
        deal_id TEXT NOT NULL,
        label TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open',
        created_at TEXT NOT NULL,
        completed_at TEXT,
        notes TEXT NOT NULL DEFAULT '',
        owner TEXT NOT NULL DEFAULT '')""",
    "deal_stars": """CREATE TABLE deal_stars (
        deal_id TEXT PRIMARY KEY,
        starred_at TEXT NOT NULL)""",
    "deal_tags": """CREATE TABLE deal_tags (
        tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
        deal_id TEXT NOT NULL,
        tag TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(deal_id) REFERENCES deals(deal_id))""",
    "note_tags": """CREATE TABLE note_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        note_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(note_id) REFERENCES deal_notes(note_id))""",
    "deal_snapshots": """CREATE TABLE deal_snapshots (
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
        FOREIGN KEY(deal_id) REFERENCES deals(deal_id))""",
}


def _fk_map(con, table):
    """{parent_table: on_delete} for a table's FKs."""
    rows = con.execute(f"PRAGMA foreign_key_list({table})").fetchall()
    return {r["table"]: str(r["on_delete"]).upper() for r in rows}


def _build_legacy_db(db_path):
    """A pre-CASCADE portfolio DB with one real deal and orphans."""
    store = PortfolioStore(db_path)
    store.init_db()
    with store.connect() as con:
        # Legacy DBs predate per-connection FK enforcement — orphans got in
        # because nothing stopped them. Recreate that world faithfully.
        con.execute("PRAGMA foreign_keys = OFF")
        con.execute(
            "INSERT OR IGNORE INTO deals (deal_id, name) VALUES ('D1', 'Deal One')"
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_notes (
                note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                body TEXT NOT NULL,
                author TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                deleted_at TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id))"""
        )
        for ddl in _LEGACY_DDL.values():
            con.execute(ddl)
        now = "2026-01-01T00:00:00+00:00"
        con.execute("INSERT INTO deal_notes (note_id, deal_id, body, created_at) VALUES (1, 'D1', 'note', ?)", (now,))
        # Orphan note for a deal that no longer exists (pre-FK DBs have these)
        con.execute("INSERT INTO deal_notes (note_id, deal_id, body, created_at) VALUES (99, 'GONE', 'orphan', ?)", (now,))
        seed = [
            ("INSERT INTO deal_sim_inputs VALUES ('D1', '/a.yaml', '/b.yaml', '', ?)", (now,)),
            ("INSERT INTO deal_sim_inputs VALUES ('GONE', '/a.yaml', '/b.yaml', '', ?)", (now,)),
            ("INSERT INTO deal_owner_history (deal_id, owner, assigned_at) VALUES ('D1', 'alex', ?)", (now,)),
            ("INSERT INTO deal_owner_history (deal_id, owner, assigned_at) VALUES ('GONE', 'sam', ?)", (now,)),
            ("INSERT INTO deal_health_history VALUES ('D1', '2026-01-01', 80, 'green')", ()),
            ("INSERT INTO deal_health_history VALUES ('GONE', '2026-01-01', 10, 'red')", ()),
            ("INSERT INTO deal_deadlines (deal_id, label, due_date, created_at) VALUES ('D1', 'IC memo', '2026-02-01', ?)", (now,)),
            ("INSERT INTO deal_deadlines (deal_id, label, due_date, created_at) VALUES ('GONE', 'stale', '2026-02-01', ?)", (now,)),
            ("INSERT INTO deal_stars VALUES ('D1', ?)", (now,)),
            ("INSERT INTO deal_stars VALUES ('GONE', ?)", (now,)),
            ("INSERT INTO deal_tags (deal_id, tag, created_at) VALUES ('D1', 'rcm', ?)", (now,)),
            ("INSERT INTO deal_tags (deal_id, tag, created_at) VALUES ('GONE', 'stale', ?)", (now,)),
            ("INSERT INTO note_tags (note_id, tag, created_at) VALUES (1, 'followup', ?)", (now,)),
            ("INSERT INTO note_tags (note_id, tag, created_at) VALUES (99, 'orphan', ?)", (now,)),
            ("INSERT INTO deal_snapshots (deal_id, stage, created_at) VALUES ('D1', 'loi', ?)", (now,)),
            ("INSERT INTO deal_snapshots (deal_id, stage, created_at) VALUES ('GONE', 'exit', ?)", (now,)),
        ]
        for sql, params in seed:
            con.execute(sql, params)
        # The orphan note itself must go too or note_tags' purge would
        # keep the orphan tag alive through a still-orphaned note.
        con.execute("DELETE FROM deal_notes WHERE deal_id = 'GONE'")
        con.commit()
    return store


class TestLegacyRebuildMigration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "legacy.db")
        self.store = _build_legacy_db(self.db)
        run_pending(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_eight_tables_converge_to_cascade(self):
        with self.store.connect() as con:
            for table, parent in _REBUILT.items():
                fks = _fk_map(con, table)
                self.assertEqual(
                    fks.get(parent), "CASCADE",
                    f"{table} FK to {parent} should be CASCADE, got {fks}",
                )

    def test_orphans_purged_and_real_rows_preserved(self):
        with self.store.connect() as con:
            for table in _REBUILT:
                key = "note_id" if table == "note_tags" else "deal_id"
                if table == "note_tags":
                    orphans = con.execute(
                        "SELECT COUNT(*) c FROM note_tags WHERE note_id NOT IN "
                        "(SELECT note_id FROM deal_notes)"
                    ).fetchone()["c"]
                else:
                    orphans = con.execute(
                        f"SELECT COUNT(*) c FROM {table} WHERE deal_id NOT IN "
                        "(SELECT deal_id FROM deals)"
                    ).fetchone()["c"]
                self.assertEqual(orphans, 0, f"{table} still has orphans ({key})")
            # Real rows survived with values intact
            row = con.execute(
                "SELECT owner FROM deal_owner_history WHERE deal_id='D1'"
            ).fetchone()
            self.assertEqual(row["owner"], "alex")
            row = con.execute(
                "SELECT actual_path FROM deal_sim_inputs WHERE deal_id='D1'"
            ).fetchone()
            self.assertEqual(row["actual_path"], "/a.yaml")
            self.assertEqual(con.execute(
                "SELECT COUNT(*) c FROM note_tags").fetchone()["c"], 1)

    def test_indexes_recreated(self):
        expected = {
            "idx_deal_owner_deal", "idx_deal_health_history_date",
            "idx_deal_deadlines_due", "idx_deal_deadlines_owner",
            "idx_deal_tags_unique", "idx_deal_tags_tag",
            "idx_note_tags_unique", "idx_note_tags_tag",
            "idx_snapshots_deal",
        }
        with self.store.connect() as con:
            names = {
                r["name"] for r in con.execute(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                ).fetchall()
            }
        self.assertTrue(expected.issubset(names), expected - names)

    def test_foreign_key_check_clean(self):
        with self.store.connect() as con:
            violations = con.execute("PRAGMA foreign_key_check").fetchall()
        self.assertEqual([tuple(v) for v in violations], [])

    def test_rerun_is_noop(self):
        run_pending(self.store)  # marked applied; second run must not blow up
        with self.store.connect() as con:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) c FROM deal_owner_history").fetchone()["c"], 1)

    def test_raw_deals_delete_now_cascades(self):
        with self.store.connect() as con:
            # deal_notes keeps NO ACTION by design (soft-delete UX), so a
            # raw deals delete is still blocked while a note row exists —
            # that is the delete-policy matrix working, not a bug.
            with self.assertRaises(Exception):
                con.execute("DELETE FROM deals WHERE deal_id='D1'")
            con.rollback()
            # Deleting the note first must cascade its note_tags (MR1058)…
            con.execute("DELETE FROM deal_notes WHERE deal_id='D1'")
            self.assertEqual(con.execute(
                "SELECT COUNT(*) c FROM note_tags").fetchone()["c"], 0)
            # …after which the deals delete cascades every rebuilt child.
            con.execute("DELETE FROM deals WHERE deal_id='D1'")
            con.commit()
            for table in _REBUILT:
                self.assertEqual(
                    con.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"],
                    0, f"{table} rows survived a cascading deals delete",
                )


class TestRebuiltSchemaMatchesModuleDDL(unittest.TestCase):
    """Drift guard: the DDL copies in migrations.py must stay identical
    to what the owning modules create on a fresh DB."""

    @staticmethod
    def _normalized_schema(con, table):
        sql = con.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()["sql"]
        sql = sql.replace('"', "").replace("IF NOT EXISTS ", "")
        return re.sub(r"\s+", " ", sql).strip()

    def test_schemas_identical(self):
        from rcm_mc.deals.deal_notes import record_note
        from rcm_mc.deals.note_tags import add_note_tag
        from rcm_mc.deals.deal_tags import add_tag
        from rcm_mc.deals.watchlist import star_deal
        from rcm_mc.deals.deal_owners import assign_owner
        from rcm_mc.deals.deal_deadlines import add_deadline
        from rcm_mc.deals.deal_sim_inputs import set_inputs
        from rcm_mc.deals.health_score import _ensure_history_table
        from rcm_mc.portfolio.portfolio_snapshots import register_snapshot

        with tempfile.TemporaryDirectory() as tmp:
            fresh_db = os.path.join(tmp, "fresh.db")
            fresh = PortfolioStore(fresh_db)
            fresh.init_db()
            fresh.upsert_deal("D1")
            note_id = record_note(fresh, deal_id="D1", body="n")
            add_note_tag(fresh, note_id, "t")
            add_tag(fresh, "D1", "t")
            star_deal(fresh, "D1")
            assign_owner(fresh, deal_id="D1", owner="alex")
            add_deadline(fresh, deal_id="D1", label="x", due_date="2026-02-01")
            set_inputs(fresh, deal_id="D1", actual_path="/a", benchmark_path="/b")
            _ensure_history_table(fresh)
            register_snapshot(fresh, "D1", "loi")

            legacy_db = os.path.join(tmp, "legacy.db")
            legacy = _build_legacy_db(legacy_db)
            run_pending(legacy)

            with fresh.connect() as fc, legacy.connect() as lc:
                for table in _REBUILT:
                    self.assertEqual(
                        self._normalized_schema(fc, table),
                        self._normalized_schema(lc, table),
                        f"{table}: migrations.py DDL drifted from module DDL",
                    )


class TestDeleteDealEndToEnd(unittest.TestCase):
    def test_delete_deal_clears_every_child(self):
        from rcm_mc.deals.deal_notes import record_note
        from rcm_mc.deals.note_tags import add_note_tag
        from rcm_mc.deals.deal_tags import add_tag
        from rcm_mc.deals.watchlist import star_deal
        from rcm_mc.deals.deal_owners import assign_owner
        from rcm_mc.deals.deal_deadlines import add_deadline
        from rcm_mc.deals.deal_sim_inputs import set_inputs
        from rcm_mc.portfolio.portfolio_snapshots import register_snapshot

        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            store.init_db()
            store.upsert_deal("D1")
            note_id = record_note(store, deal_id="D1", body="tagged note")
            add_note_tag(store, note_id, "followup")
            add_tag(store, "D1", "rcm")
            star_deal(store, "D1")
            assign_owner(store, deal_id="D1", owner="alex")
            add_deadline(store, deal_id="D1", label="IC", due_date="2026-02-01")
            set_inputs(store, deal_id="D1", actual_path="/a", benchmark_path="/b")
            register_snapshot(store, "D1", "loi")

            # MR1068 regression: with the old wrong-name list this either
            # orphaned rows or failed outright on the tagged note.
            self.assertTrue(store.delete_deal("D1"))

            checks = [
                "deal_notes", "note_tags", "deal_tags", "deal_stars",
                "deal_owner_history", "deal_deadlines", "deal_sim_inputs",
                "deal_snapshots",
            ]
            with store.connect() as con:
                self.assertIsNone(con.execute(
                    "SELECT 1 FROM deals WHERE deal_id='D1'").fetchone())
                for table in checks:
                    self.assertEqual(
                        con.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"],
                        0, f"{table} not cleared by delete_deal",
                    )

    def test_delete_deal_on_minimal_db(self):
        # Lazily-created child tables may not exist at all; delete_deal
        # must tolerate exactly that ("no such table") and nothing else.
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            store.init_db()
            store.upsert_deal("D1")
            self.assertTrue(store.delete_deal("D1"))
            self.assertFalse(store.delete_deal("D1"))


if __name__ == "__main__":
    unittest.main()
