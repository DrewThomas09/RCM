"""MR1034: every shell script in scripts/ must at least parse.

Neither run_all.sh nor run_everything.sh is exercised by CI (they
drive interactive/server workflows), so a typo could sit unnoticed
until an analyst runs one. ``bash -n`` catches syntax rot cheaply;
the repo-root resolution test pins the MR1034 fix itself (the old
hardcoded ``/Users/...`` path broke everywhere but one laptop).
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class TestScriptsParse(unittest.TestCase):
    def test_scripts_dir_exists_and_has_scripts(self):
        scripts = sorted(_SCRIPTS_DIR.glob("*.sh"))
        self.assertTrue(scripts, f"no *.sh under {_SCRIPTS_DIR}")

    def test_every_script_passes_bash_n(self):
        for script in sorted(_SCRIPTS_DIR.glob("*.sh")):
            with self.subTest(script=script.name):
                proc = subprocess.run(
                    ["bash", "-n", str(script)],
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(
                    proc.returncode, 0,
                    f"bash -n failed for {script.name}: {proc.stderr}",
                )

    def test_run_everything_resolves_repo_root_not_hardcoded(self):
        src = (_SCRIPTS_DIR / "run_everything.sh").read_text()
        self.assertNotIn("/Users/", src, "hardcoded developer path is back")
        self.assertIn("BASH_SOURCE", src)


if __name__ == "__main__":
    unittest.main()
