"""Source-level guard: no legacy kwargs on kit primitives.

The v2 ``ck_kpi_block`` rework renamed two keyword arguments:

  * ``unit=``  →  ``sub=``    (third positional, formerly the unit
                               suffix string; now a subtitle)
  * ``delta=`` → ``trend=``   (fourth positional, formerly delta;
                               now an arbitrary trend indicator)

Pages that called ``ck_kpi_block(..., unit=..., delta=...)`` raised
``TypeError`` at render time and dispatched to the 500 handler —
silently breaking eight partner-facing routes (/provider-network,
/covenant-monitor, /qoe-analyzer, /value-creation, /underwriting-model,
/mgmt-fee-tracker, /exit-multiple, /diligence/checklist) until the
route-broadening sweep surfaced them.

This guard scans ``rcm_mc/ui/`` for any ``ck_kpi_block(...)`` call
that uses the legacy kwargs and fails the test, blocking the
regression from creeping back.
"""
from __future__ import annotations

import pathlib
import re
import unittest


_LEGACY_KWARG_RE = re.compile(
    r"ck_kpi_block\([^)]*?\b(unit|delta)\s*=", re.DOTALL,
)


class NoLegacyCkKpiBlockKwargs(unittest.TestCase):
    """Walks ``rcm_mc/ui/`` for ``ck_kpi_block(..., unit=...)``
    or ``ck_kpi_block(..., delta=...)``. Either form raises
    ``TypeError`` at runtime — the v2 signature uses ``sub`` and
    ``trend`` keyword-only.
    """

    def test_no_unit_or_delta_kwargs_in_ck_kpi_block(self) -> None:
        ui_root = (
            pathlib.Path(__file__).resolve().parent.parent
            / "rcm_mc" / "ui"
        )
        violations: list[tuple[str, int, str]] = []
        for py in ui_root.rglob("*.py"):
            try:
                src = py.read_text(encoding="utf-8")
            except OSError:
                continue
            for m in _LEGACY_KWARG_RE.finditer(src):
                line_no = src[: m.start()].count("\n") + 1
                rel = py.relative_to(ui_root.parent.parent)
                violations.append((str(rel), line_no, m.group(1)))

        self.assertEqual(
            violations, [],
            "ck_kpi_block() callers using legacy kwargs (these "
            "raise TypeError at render — see /provider-network and "
            "/covenant-monitor for the regression history). Use "
            "``sub=`` instead of ``unit=`` and ``trend=`` instead "
            "of ``delta=``.\n"
            + "\n".join(
                f"  {p}:{ln}  {kw}=" for p, ln, kw in violations[:20]
            )
            + (f"\n  ...and {len(violations) - 20} more"
               if len(violations) > 20 else ""),
        )


if __name__ == "__main__":
    unittest.main()
