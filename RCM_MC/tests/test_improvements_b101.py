"""Tests for improvement pass B101: CLI version, migrations, metadata, cache.

CLI VERSION:
 1. CLI parser has --version flag.

MIGRATIONS:
 2. run_pending applies migrations to fresh DB.
 3. list_applied returns applied migration names.
 4. Re-running is idempotent.

PYPROJECT:
 5. Version matches __init__.__version__.

HCRIS CACHE:
 6. hcris_cache_age_days returns float or None.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore


class TestCLIVersion(unittest.TestCase):

    def test_parser_has_version(self):
        from rcm_mc.cli import build_arg_parser
        import io
        import contextlib
        ap = build_arg_parser()
        # --version causes SystemExit(0); capture it
        buf = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(buf):
                ap.parse_args(["--version"])
        self.assertEqual(ctx.exception.code, 0)
        output = buf.getvalue()
        from rcm_mc import __version__
        self.assertIn(__version__, output)


class TestMigrations(unittest.TestCase):

    def test_run_pending_on_fresh_db(self):
        from rcm_mc.infra.migrations import run_pending, list_applied
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            count = run_pending(store)
            self.assertGreater(count, 0)
            applied = list_applied(store)
            self.assertIn("deals_archived_at", applied)
        finally:
            os.unlink(tf.name)

    def test_idempotent(self):
        from rcm_mc.infra.migrations import run_pending
        tf = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tf.close()
        try:
            store = PortfolioStore(tf.name)
            first = run_pending(store)
            second = run_pending(store)
            self.assertEqual(second, 0)
        finally:
            os.unlink(tf.name)


class TestVersionSync(unittest.TestCase):

    def test_versions_match(self):
        from rcm_mc import __version__
        import tomllib
        from pathlib import Path
        toml_path = Path(__file__).parent.parent / "pyproject.toml"
        if toml_path.exists():
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
            toml_version = data.get("project", {}).get("version", "")
            self.assertEqual(__version__, toml_version)


class TestHCRISCacheAge(unittest.TestCase):

    def test_cache_age_returns_value(self):
        from rcm_mc.data.hcris import hcris_cache_age_days
        age = hcris_cache_age_days()
        # Returns None if file missing, float if present
        if age is not None:
            self.assertIsInstance(age, float)
            self.assertGreaterEqual(age, 0)


if __name__ == "__main__":
    unittest.main()
