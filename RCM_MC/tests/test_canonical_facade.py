"""Regression tests for canonical_facade hardening (Report-0264).

- MR1065: _move_to_canonical must not unlink the destination before
  the move — a crash in that window (with the source inside a
  TemporaryDirectory) destroyed BOTH copies of the artifact.
- MR1066: _record swallows manifest failures by design, but must log
  them; a silent skip means generated_exports quietly stops filling.
"""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from rcm_mc.exports.canonical_facade import _move_to_canonical, _record


class _BrokenStore:
    """Store whose connections always fail — simulates a manifest
    write outage (external-stub exception per CLAUDE.md testing rules)."""

    db_path = "/nonexistent/broken.db"

    def connect(self):
        raise RuntimeError("manifest store down")

    def init_db(self):
        raise RuntimeError("manifest store down")


class TestMoveToCanonical(unittest.TestCase):
    def test_overwrites_existing_without_pre_unlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp) / "exports" / "report.html"
            canonical.parent.mkdir(parents=True)
            canonical.write_text("OLD")
            produced = Path(tmp) / "produced.html"
            produced.write_text("NEW")
            out = _move_to_canonical(produced, canonical)
            self.assertEqual(out, canonical)
            self.assertEqual(canonical.read_text(), "NEW")
            self.assertFalse(produced.exists())

    def test_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp) / "a" / "b" / "c.html"
            produced = Path(tmp) / "src.html"
            produced.write_text("X")
            _move_to_canonical(produced, canonical)
            self.assertEqual(canonical.read_text(), "X")

    def test_source_never_lost_when_destination_locked(self):
        # MR1065 regression: if the move itself fails, the produced
        # file must still exist (the old code had already unlinked the
        # canonical copy by this point, so a failure lost both).
        with tempfile.TemporaryDirectory() as tmp:
            canonical_dir = Path(tmp) / "exports"
            canonical_dir.mkdir()
            canonical = canonical_dir / "report.html"
            canonical.write_text("OLD")
            produced = Path(tmp) / "produced.html"
            produced.write_text("NEW")
            os.chmod(canonical_dir, 0o500)  # read+exec only: move fails
            try:
                if os.access(canonical_dir / "probe", os.W_OK):
                    self.skipTest("running as privileged user; chmod no-op")
                try:
                    with self.assertRaises(Exception):
                        _move_to_canonical(produced, canonical)
                except self.failureException:
                    self.skipTest("filesystem ignores mode bits here")
                self.assertTrue(produced.exists(), "source lost on failed move")
                self.assertEqual(canonical.read_text(), "OLD")
            finally:
                os.chmod(canonical_dir, 0o700)


class TestRecordBestEffort(unittest.TestCase):
    def test_manifest_failure_is_logged_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "x.html"
            artifact.write_text("data")
            with self.assertLogs("rcm_mc.exports.canonical_facade",
                                 level="WARNING") as captured:
                _record(
                    _BrokenStore(),
                    deal_id="D1",
                    canonical=artifact,
                    fmt="html",
                )
            joined = "\n".join(captured.output)
            self.assertIn("manifest write failed", joined)
            self.assertIn("D1", joined)


if __name__ == "__main__":
    unittest.main()
