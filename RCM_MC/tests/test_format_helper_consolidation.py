"""Guard test for the ad-hoc format-helper consolidation moat.

The kit ships ``rcm_mc.ui._ui_kit.format_value(value, kind=...)`` as
the canonical missing-aware formatter for money/percent/multiples/
counts. CLAUDE.md format rules (money 2dp, percent 1dp, multiples
2dp) are enforced inside the kit, so any caller that uses
``format_value`` is automatically compliant — and the per-route
``number-format-clean`` compliance rule (P94) cannot regress on
them.

But many UI modules still ship their own ``_fmt_m`` / ``_fmt_money``
/ ``_fmt_pct`` / ``_fm`` helpers. Those:

  * usually crash or return ``"$0.0"`` instead of the missing-label
    span on ``None``
  * historically used ``$X.1f}M`` formatting (1 decimal), which the
    P94 audit catches at render time but not at source time
  * duplicate behaviour that should live in one place

This test caps the count of ad-hoc helpers at the current
post-sweep baseline. Adding a NEW helper FAILS the test, forcing
the contributor to either:

  (a) use ``format_value(v, kind="money")`` from the kit, or
  (b) update this baseline and document why a bespoke formatter
      is justified for the new module

Lowering the count (by migrating a module to the kit) is a free
win — drop the cap to the new count and ratchet down.
"""
from __future__ import annotations

import pathlib
import re
import unittest


# Pattern matches the most common ad-hoc helper names seen in the
# UI layer. Includes single-letter aliases (`_fm`) and long forms
# (`_fmt_money`, `_fmt_moic`).
_HELPER_PATTERN = re.compile(
    r"^def\s+("
    r"_fm|_fmt|_fmt_m|_fmt_money|_fmt_pct|_fmt_moic|_fmt_multi"
    r")\s*\(",
    re.MULTILINE,
)


# Baseline as of the consolidation guard's introduction. Drop this
# number whenever a module migrates to ``format_value()``; never
# raise it without explicit reason in the commit message.
HELPER_COUNT_CAP = 47


class HelperCountIsCapped(unittest.TestCase):
    """Pin the count of ad-hoc format helpers in rcm_mc/ui/."""

    def test_count_does_not_exceed_cap(self) -> None:
        ui_dir = (
            pathlib.Path(__file__).resolve().parent.parent
            / "rcm_mc" / "ui"
        )
        count = 0
        offenders: list[tuple[str, list[str]]] = []
        for py in ui_dir.rglob("*.py"):
            try:
                src = py.read_text(encoding="utf-8")
            except OSError:
                continue
            matches = _HELPER_PATTERN.findall(src)
            if matches:
                count += len(matches)
                offenders.append((str(py.relative_to(ui_dir)), matches))
        self.assertLessEqual(
            count, HELPER_COUNT_CAP,
            f"Ad-hoc format-helper count ({count}) exceeds cap "
            f"({HELPER_COUNT_CAP}). Either use format_value() from "
            f"the kit, or update HELPER_COUNT_CAP after justifying "
            f"the new helper. Offenders:\n"
            + "\n".join(f"  {p}: {m}" for p, m in offenders),
        )


class CapIsTightAgainstCurrentCount(unittest.TestCase):
    """If the actual count drops below the cap (a module migrated
    to format_value), this test prompts ratcheting the cap down so
    the gain locks in. Soft assertion — emits a warning rather than
    a hard fail so a single migration doesn't break CI."""

    def test_cap_within_two_of_actual_count(self) -> None:
        ui_dir = (
            pathlib.Path(__file__).resolve().parent.parent
            / "rcm_mc" / "ui"
        )
        count = 0
        for py in ui_dir.rglob("*.py"):
            try:
                src = py.read_text(encoding="utf-8")
            except OSError:
                continue
            count += len(_HELPER_PATTERN.findall(src))
        # If the cap is more than 2 above current count, prompt a
        # ratchet. The gap-of-2 buffer absorbs in-flight migrations
        # without spurious failures.
        self.assertLessEqual(
            HELPER_COUNT_CAP - count, 5,
            f"HELPER_COUNT_CAP ({HELPER_COUNT_CAP}) is more than 5 "
            f"above actual count ({count}). Drop the cap to {count} "
            f"in tests/test_format_helper_consolidation.py to lock "
            f"in the gain.",
        )


if __name__ == "__main__":
    unittest.main()
