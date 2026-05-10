"""Adoption tracker for the kit primitives.

The compliance moat depends on contributors using the kit
(``kpi_strip``, ``format_value``, ``PALETTE``, etc.) instead of
hand-rolling the equivalent. Source guards block the wrong path
(e.g. ``CadKpiGridFullyEliminated`` blocks new ``cad-kpi-grid``
markup); this test does the converse — pins the *minimum* count
of kit-primitive call sites so the migration trajectory can't
silently reverse.

Each primitive has a ``MIN_*`` floor below which the test fails.
The floor is the count at the time of the moat-build session that
landed the primitive's broad adoption. Future contributors can:

  * Raise the floor when they migrate more code (locks in the gain)
  * Lower the floor with explicit justification when a primitive
    is intentionally retired (rare — the kit is additive)

Floors below current count are loud regressions; floors equal to
current count let the codebase float upward.
"""
from __future__ import annotations

import pathlib
import re
import unittest


# (label, regex, floor)
PRIMITIVES: list[tuple[str, re.Pattern, int]] = [
    # KPI tile primitive — replaced ~41 cad-kpi-grid blocks during
    # the Phase-3 sweep. 70 call sites.
    ("kpi_strip(",     re.compile(r"\bkpi_strip\("),     70),

    # Money / percent / multiple formatter — canonical for all
    # 2dp-money / 1dp-percent rendering. 110 call sites after the
    # _fm-wrapper pilot inlines.
    ("format_value(",  re.compile(r"\bformat_value\("),  110),

    # Brand palette dict — 1028 references across f-strings, dicts,
    # and module-level color tokens after the brand-hex moat closed.
    ("PALETTE[",       re.compile(r"\bPALETTE\["),       1028),

    # The shared rendering shell. 409 call sites.
    ("chartis_shell(", re.compile(r"\bchartis_shell\("), 409),

    # Empty-state primitive — 14 call sites currently. Low number
    # but new pages should adopt it; the floor catches retirement.
    ("empty_state(",   re.compile(r"\bempty_state\("),   14),

    # Data-table primitive — 7 call sites.
    ("data_table(",    re.compile(r"\bdata_table\("),    7),

    # CSS var-with-fallback pattern from the brand-hex sweep.
    # 504 occurrences across static CSS strings.
    ("var(--theme",    re.compile(r"var\(--theme-[\w-]+,"), 504),
]


def _count(pat: re.Pattern) -> int:
    pkg_root = (
        pathlib.Path(__file__).resolve().parent.parent / "rcm_mc"
    )
    n = 0
    for py in pkg_root.rglob("*.py"):
        try:
            n += len(pat.findall(py.read_text(encoding="utf-8")))
        except OSError:
            continue
    return n


class KitPrimitiveAdoptionFloors(unittest.TestCase):
    """Each primitive's call-site count must stay above its floor."""

    def test_kpi_strip_adoption_floor(self) -> None:
        self._assert_floor(0)

    def test_format_value_adoption_floor(self) -> None:
        self._assert_floor(1)

    def test_palette_adoption_floor(self) -> None:
        self._assert_floor(2)

    def test_chartis_shell_adoption_floor(self) -> None:
        self._assert_floor(3)

    def test_empty_state_adoption_floor(self) -> None:
        self._assert_floor(4)

    def test_data_table_adoption_floor(self) -> None:
        self._assert_floor(5)

    def test_var_theme_adoption_floor(self) -> None:
        self._assert_floor(6)

    def _assert_floor(self, idx: int) -> None:
        label, pat, floor = PRIMITIVES[idx]
        actual = _count(pat)
        self.assertGreaterEqual(
            actual, floor,
            f"{label} adoption count ({actual}) dropped below "
            f"floor ({floor}). The kit primitive is being "
            f"retired without justification — either migrate "
            f"the call sites back, or update the floor in "
            f"tests/test_kit_primitive_adoption.py with a "
            f"commit-message rationale.",
        )


class CapsAreTightAgainstActualCounts(unittest.TestCase):
    """Soft signal — when the actual count drifts well above the
    floor, prompt ratcheting upward to lock in the gain. A 50-
    count buffer absorbs in-flight migrations without spurious
    failures."""

    def test_floors_within_buffer_of_actual(self) -> None:
        gaps: list[str] = []
        for label, pat, floor in PRIMITIVES:
            actual = _count(pat)
            gap = actual - floor
            if gap > 50:
                gaps.append(
                    f"  {label}: floor={floor}  actual={actual}  "
                    f"gap=+{gap} → bump floor to {actual}"
                )
        if gaps:
            self.fail(
                f"{len(gaps)} primitive floors are >50 below actual; "
                f"ratchet up to lock in the gain:\n"
                + "\n".join(gaps)
            )


if __name__ == "__main__":
    unittest.main()
