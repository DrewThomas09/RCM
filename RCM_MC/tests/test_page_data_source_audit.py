"""Data-integrity regression guard: no UNDISCLOSED data page outside backlog.

Runs the page data-source audit and asserts that the set of pages rendering
figures with NO source disclosure is a subset of a documented backlog. This
means the backlog can only shrink (as pages are fixed) — a NEW page that renders
data without a source/illustrative/data-required label fails CI. See
docs/DATA_VERIFICATION_POLICY.md.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# Snapshot of pages currently rendering data without disclosure (2026-05-25).
# This set may only SHRINK. Remove entries as pages get a source/illustrative/
# data-required label. Do NOT add to it without an explicit honest reason.
_KNOWN_BACKLOG = {
    "/backtest", "/base-rates", "/cms-data-browser", "/cms-sources",
    "/comparables", "/corpus-coverage", "/corpus-dashboard",
    "/data-sources-admin", "/deal-flow-heatmap", "/deal-search",
    "/deal-sourcing", "/entry-multiple", "/exit-timing", "/fund-attribution",
    "/gp-benchmarking", "/hold-analysis", "/hold-optimizer", "/ic-memo",
    "/ic-memo-generator", "/irr-dispersion", "/leverage-intel", "/lp-dashboard",
    "/lp-reporting", "/market-rates", "/module-index", "/portfolio-optimizer",
    "/portfolio-sim", "/return-attribution", "/scenario-mc", "/size-intel",
    "/sponsor-heatmap", "/tax-structure-analyzer", "/underwriting",
    "/value-backtester", "/vintage-perf",
}


class PageDataSourceAuditTests(unittest.TestCase):
    def test_no_new_undisclosed_data_pages(self):
        import json
        # Regenerate the audit fresh so the test reflects current code.
        r = subprocess.run([sys.executable, "scripts/audit_page_data_sources.py"],
                           cwd=_ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads((_ROOT / "data_quality" / "page_data_source_audit.json").read_text())
        flagged = {p["route"] for p in data["pages"] if p["flag"]}
        new = flagged - _KNOWN_BACKLOG
        self.assertEqual(new, set(),
                         f"New data-rendering page(s) with NO source disclosure: {sorted(new)}. "
                         f"Add a ck_source_purpose / ck_illustrative_note / DATA REQUIRED label.")


if __name__ == "__main__":
    unittest.main()
