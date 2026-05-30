"""Invariant — no data_public renderer emits a slash-dual page H1.

The 2026-05-29 audit (§5) flagged ~30 data_public pages carrying
``X / Y Tracker``-style slash-dual H1s. PRs #1156-#1163 collapsed
34 of them across seven editorial-cleanup batches.

This test locks the cleanup in by failing CI if any future PR
introduces a `ck_page_title("... / ...", ...)` call in a
data_public page. It is a static-source check — fast, no server,
no DB.

Known exceptions (slash-duals where the two halves name genuinely
distinct ideas) are listed in ``_KNOWN_DISTINCT_TITLES``; future
audits can either rewrite those or extend the allowlist with a
justification comment.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


# Slash-dual H1s where the two halves carry distinct meaning that
# can't be collapsed to a single noun without losing information.
# Each entry should be revisited in a coordinated editorial pass;
# new entries should NOT be added casually.
_KNOWN_DISTINCT_TITLES = {
    "Capital Call / LP Communication Tracker",
    "Co-Investment Pipeline / LP Allocation Tracker",
    "Compliance Attestation / Security Posture Tracker",
    "Digital Front Door / Patient Experience Tracker",
    "Operating Partner / CEO Rolodex Tracker",
    "Partner Economics / Physician Buy-in",
    "Peer Transaction Database / Comps Library",
    "Platform Maturity / Exit Readiness",
    "Value Creation Plan (VCP) / 100-Day Plan Tracker",
}

_DATA_PUBLIC = (
    Path(__file__).resolve().parent.parent
    / "rcm_mc" / "ui" / "data_public"
)


def _ck_page_title_strings(src: str) -> list[str]:
    """Pull the first positional argument string from each
    ``ck_page_title(...)`` call in a module. Handles single-line and
    multi-line forms because that's how renderers actually write them."""
    out = []
    # Single-line form: ck_page_title("Foo Bar", ...)
    for m in re.finditer(r'ck_page_title\(\s*"([^"]+)"', src):
        out.append(m.group(1))
    # Triple-quoted form is rare here but covered for safety.
    for m in re.finditer(r"ck_page_title\(\s*'([^']+)'", src):
        out.append(m.group(1))
    return out


class TestNoSlashDualH1OnDataPublic(unittest.TestCase):
    """Audit §5 lock-in: data_public/ pages should not introduce new
    slash-dual H1s without a deliberate justification."""

    def test_no_new_slash_dual_titles_in_data_public(self):
        offenders: list[tuple[str, str]] = []
        for page in sorted(_DATA_PUBLIC.glob("*_page.py")):
            src = page.read_text(encoding="utf-8")
            for title in _ck_page_title_strings(src):
                if " / " not in title:
                    continue
                if title in _KNOWN_DISTINCT_TITLES:
                    continue
                offenders.append((page.name, title))
        self.assertFalse(
            offenders,
            "New slash-dual H1(s) introduced — collapse to a single "
            "noun or add to _KNOWN_DISTINCT_TITLES with a justification "
            "comment:\n  " + "\n  ".join(
                f"{p}: {t!r}" for p, t in offenders),
        )

    def test_known_distinct_allowlist_is_still_present(self):
        """Sanity guard: each entry in the allowlist should still
        appear in some data_public file. If a title gets renamed or
        removed, drop the allowlist entry too."""
        actual_titles: set[str] = set()
        for page in _DATA_PUBLIC.glob("*_page.py"):
            actual_titles.update(_ck_page_title_strings(page.read_text(encoding="utf-8")))
        stale = _KNOWN_DISTINCT_TITLES - actual_titles
        self.assertFalse(
            stale,
            "Allowlist entries no longer present in any data_public "
            f"renderer — remove from _KNOWN_DISTINCT_TITLES: {stale}",
        )


if __name__ == "__main__":
    unittest.main()
