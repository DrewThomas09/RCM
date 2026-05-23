"""Regression guard: directional analytic pages must not claim "IC-ready".

A rule-based / corpus-benchmarked analytic surface is a directional
diligence input, not a finished IC deliverable. The redflag scanner once
advertised "IC-ready" in its page-title subtitle (fixed); this canary
keeps that overclaim from creeping back into any data_public page header.

Scope: only ``meta=`` / ``subtitle=`` / ``eyebrow=`` strings on the
public analytic pages. The genuine IC Packet bundle (ui/chartis) is the
IC deliverable itself and is intentionally not covered here.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_DATA_PUBLIC = (
    Path(__file__).resolve().parents[1] / "rcm_mc" / "ui" / "data_public"
)

# A page-header argument (meta/subtitle/eyebrow) whose value asserts
# "IC-ready" / "IC ready".
_HEADER_ARG = re.compile(
    r"(?:meta|subtitle|eyebrow)\s*=\s*[^\n]*ic[-\s]?ready", re.IGNORECASE
)


class NoICReadyOverclaimTests(unittest.TestCase):
    def test_no_data_public_page_header_claims_ic_ready(self):
        offenders = []
        for path in sorted(_DATA_PUBLIC.glob("*_page.py")):
            text = path.read_text(encoding="utf-8")
            for m in _HEADER_ARG.finditer(text):
                line = text[: m.start()].count("\n") + 1
                offenders.append(f"{path.name}:{line}")
        self.assertEqual(
            offenders, [],
            "Directional analytic page headers must not claim 'IC-ready' "
            "(use 'directional, verify before IC'): " + ", ".join(offenders),
        )


if __name__ == "__main__":
    unittest.main()
