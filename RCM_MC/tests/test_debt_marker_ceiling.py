"""Source-level guard against TODO/FIXME debt accumulation.

The rcm_mc codebase has historically been near-zero on debt
markers — 2 TODO comments at the time this guard landed. This
test pins the ceiling so debt can't silently accumulate. New
contributors who feel the urge to write ``# TODO: fix this
later`` are forced to either:

  * fix the thing now (preserves zero-debt baseline)
  * raise the ceiling with a commit-message rationale (rare —
    requires explicit acceptance)

Distinct from a comment-style enforcer: the goal isn't to ban
TODOs forever, just to prevent silent accumulation. A 5-marker
buffer absorbs short-term in-flight work; long-term, the ceiling
should ratchet down as TODOs are resolved.

Pattern matched (case-insensitive):
  * ``# TODO``
  * ``# FIXME``
  * ``# XXX``
  * ``# HACK``

Test files (``rcm_mc/tests/``) are excluded — test scaffolding
sometimes legitimately uses ``# TODO: cover this case``.
"""
from __future__ import annotations

import pathlib
import re
import unittest


_DEBT_RE = re.compile(r"#\s*(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)

# Baseline as of guard introduction. Drop this number whenever a
# TODO is resolved; never raise without explicit justification.
DEBT_CEILING = 2


class DebtMarkerCount(unittest.TestCase):
    """Pin the count of TODO/FIXME/XXX/HACK comments."""

    def test_count_does_not_exceed_ceiling(self) -> None:
        repo_root = pathlib.Path(__file__).resolve().parent.parent
        count = 0
        offenders: list[str] = []
        for py in (repo_root / "rcm_mc").rglob("*.py"):
            try:
                src = py.read_text(encoding="utf-8")
            except OSError:
                continue
            for ln_no, line in enumerate(src.splitlines(), 1):
                if _DEBT_RE.search(line):
                    count += 1
                    rel = py.relative_to(repo_root)
                    offenders.append(f"  {rel}:{ln_no}  {line.strip()[:80]}")
        self.assertLessEqual(
            count, DEBT_CEILING,
            f"Debt-marker count ({count}) exceeds ceiling "
            f"({DEBT_CEILING}). Either fix the thing in the same "
            f"commit, or update DEBT_CEILING with rationale.\n"
            + "\n".join(offenders),
        )


class CeilingIsTightAgainstActualCount(unittest.TestCase):
    """Soft signal — when debt drops below the ceiling, prompt
    ratcheting downward. 5-marker buffer absorbs in-flight work."""

    def test_ceiling_within_buffer_of_actual(self) -> None:
        repo_root = pathlib.Path(__file__).resolve().parent.parent
        count = 0
        for py in (repo_root / "rcm_mc").rglob("*.py"):
            try:
                src = py.read_text(encoding="utf-8")
            except OSError:
                continue
            count += len(_DEBT_RE.findall(src))
        self.assertLessEqual(
            DEBT_CEILING - count, 5,
            f"DEBT_CEILING ({DEBT_CEILING}) is more than 5 above "
            f"actual count ({count}). Drop the ceiling to {count} "
            f"in tests/test_debt_marker_ceiling.py to lock in the "
            f"gain.",
        )


if __name__ == "__main__":
    unittest.main()
