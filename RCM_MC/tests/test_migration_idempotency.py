"""DB schema-migration idempotency proof.

Pins the cycle-12 Azure deploy-readiness row: every container
restart on Azure App Service triggers ``build_server`` which calls
``infra.migrations.run_pending`` on the persistent ``portfolio.db``.
That second-and-subsequent boot must produce **identical schema** to
the first — otherwise restart would corrupt the live DB or crash
the boot.

Two complementary checks:
1. **Runtime snapshot diff** — boot fresh DB, dump
   ``sqlite_master``, boot again on the same path, dump again,
   diff = empty. Also asserts no duplicate rows in ``_migrations``.
2. **Static convention check** — every ``CREATE TABLE`` in
   ``rcm_mc/`` carries ``IF NOT EXISTS`` so a re-boot never raises
   on an already-created table. Catches new tables added without
   the idempotent guard.
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from rcm_mc.infra.migrations import _MIGRATIONS, run_pending
from rcm_mc.portfolio.store import PortfolioStore


def _schema_snapshot(db_path: str) -> dict:
    """Dump every table+index DDL from sqlite_master, plus row counts.

    Skips internal sqlite tables. Returns a dict keyed by name so the
    test can assert specific entries when the diff fails — easier to
    debug than a single multi-line string compare.
    """
    import sqlite3
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' "
            "ORDER BY type, name"
        ).fetchall()
        snap: dict = {}
        for kind, name, sql in rows:
            snap[f"{kind}:{name}"] = (sql or "").strip()
        # Track _migrations row count so a duplicate insert would
        # surface as a snapshot diff even if DDL is identical.
        try:
            count = conn.execute(
                "SELECT COUNT(*) FROM _migrations"
            ).fetchone()[0]
            snap["_migrations:row_count"] = int(count)
        except Exception:
            pass
        return snap
    finally:
        conn.close()


class MigrationIdempotencyTests(unittest.TestCase):
    def test_run_pending_is_idempotent_on_persistent_db(self):
        """Apply migrations twice on the same DB; schema must not drift."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "portfolio.db")
            store = PortfolioStore(db_path)
            n_first = run_pending(store)
            snap_a = _schema_snapshot(db_path)

            # Second pass on the same DB — no new migrations should
            # apply, and the schema must be byte-identical.
            n_second = run_pending(store)
            snap_b = _schema_snapshot(db_path)

            self.assertGreaterEqual(n_first, 0)
            self.assertEqual(
                n_second, 0,
                "Second run_pending applied {n_second} migrations; "
                "must be 0 on a freshly-migrated DB.",
            )
            self.assertEqual(
                snap_a, snap_b,
                "Schema drifted between two run_pending calls — "
                "this means a non-idempotent CREATE/ALTER ran twice.",
            )

    def test_build_server_twice_on_same_db_no_drift(self):
        """End-to-end: build_server boot path is idempotent."""
        from rcm_mc.server import build_server
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "portfolio.db")
            # First boot — runs migrations + cleanup_expired_sessions
            # + DB self-test. No serve_forever; just construct.
            server_a, _ = build_server(port=0, db_path=db_path)
            server_a.server_close()
            snap_a = _schema_snapshot(db_path)

            # Second boot on the same DB
            server_b, _ = build_server(port=0, db_path=db_path)
            server_b.server_close()
            snap_b = _schema_snapshot(db_path)

            self.assertEqual(
                snap_a, snap_b,
                "build_server boot drifted schema across two starts.",
            )

    def test_migrations_registry_records_each_only_once(self):
        """_migrations table must not accumulate duplicate rows."""
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "portfolio.db")
            store = PortfolioStore(db_path)
            run_pending(store)
            run_pending(store)
            run_pending(store)
            import sqlite3
            con = sqlite3.connect(db_path)
            try:
                rows = con.execute(
                    "SELECT name, COUNT(*) AS n FROM _migrations "
                    "GROUP BY name HAVING n > 1"
                ).fetchall()
            finally:
                con.close()
            self.assertEqual(
                rows, [],
                f"Duplicate _migrations rows after three runs: {rows}",
            )


class CreateTableConventionTests(unittest.TestCase):
    """Static check: every CREATE TABLE in rcm_mc/ uses IF NOT EXISTS.

    A new table added without the guard would raise on the second
    boot when the table already exists from the first. Catches the
    Azure restart-corruption scenario at PR-time, not in production.
    """

    def _walk_create_tables(self):
        """Yield (file_path, line_no, table, guarded) for every real
        CREATE TABLE statement across ``rcm_mc/`` Python sources.

        A "real" statement is one whose table name is followed by
        ``(``, ``AS``, or whitespace-then-paren on the next line —
        proper SQL continuation. This filters out docstring prose
        like "CREATE TABLE here — schema migrations are later"
        which would otherwise false-positive as a missing
        ``IF NOT EXISTS`` guard.

        Both the SQL form (``CREATE TABLE IF NOT EXISTS foo (...)``)
        and unguarded form (``CREATE TABLE foo (...)``) are surfaced;
        the caller filters by the ``guarded`` flag.
        """
        # Match: CREATE TABLE [IF NOT EXISTS] [schema.]name then
        # whitespace then `(` or `AS`. The schema-prefix support is
        # for tuva_bridge's `raw_data."name"` qualifier.
        pattern = re.compile(
            r"""
            CREATE\s+TABLE
            (?P<guard>\s+IF\s+NOT\s+EXISTS)?     # optional guard
            \s+
            (?:["`]?\w+["`]?\s*\.\s*)?           # optional schema.
            ["`]?(?P<name>\w+)["`]?              # table name
            \s*                                  # whitespace before
            (?P<continuation>[(]|AS\s)           # ( or AS keyword
            """,
            re.IGNORECASE | re.VERBOSE | re.DOTALL,
        )
        rcm_mc_dir = Path(
            __import__("rcm_mc").__file__,
        ).parent
        for py in rcm_mc_dir.rglob("*.py"):
            if "__pycache__" in str(py):
                continue
            try:
                src = py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for m in pattern.finditer(src):
                guarded = m.group("guard") is not None
                table = m.group("name")
                upto = src[:m.start()]
                line_no = upto.count("\n") + 1
                yield (str(py.relative_to(rcm_mc_dir.parent)),
                       line_no, table, guarded)

    def test_every_create_table_uses_if_not_exists(self):
        unguarded = [
            (path, line, table)
            for path, line, table, guarded in self._walk_create_tables()
            if not guarded
        ]
        # The convention must hold across the entire package — any
        # one violation can break Azure restart.
        self.assertEqual(
            unguarded, [],
            "Found CREATE TABLE statements without IF NOT EXISTS:\n"
            + "\n".join(
                f"  {p}:{ln} — table {t!r}"
                for p, ln, t in unguarded
            )
            + "\nAdd IF NOT EXISTS so a second container boot doesn't "
            "raise on the already-created table.",
        )


class MigrationsRegistryShapeTests(unittest.TestCase):
    """Sanity-pin the migration registry so silent additions don't
    bypass the idempotency contract."""

    def test_each_migration_has_unique_name(self):
        names = [name for name, _ in _MIGRATIONS]
        self.assertEqual(
            len(names), len(set(names)),
            f"Duplicate migration names in registry: {names}",
        )

    def test_each_migration_sql_is_alter_or_create_index(self):
        # The registry holds delta migrations (column adds, indexes).
        # Full CREATE TABLE belongs in the per-feature module's
        # _ensure_table helper — which is naturally idempotent via
        # IF NOT EXISTS. New migration shapes should land here so the
        # idempotency review catches them.
        for name, sql in _MIGRATIONS:
            up = sql.upper().strip()
            self.assertTrue(
                up.startswith("ALTER TABLE")
                or up.startswith("CREATE INDEX")
                or up.startswith("CREATE UNIQUE INDEX"),
                f"Migration {name!r} uses an unexpected statement "
                f"shape: {sql[:80]}",
            )


if __name__ == "__main__":
    unittest.main()
