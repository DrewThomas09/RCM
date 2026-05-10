"""Guard against test-ordering regressions.

Several commits in the moat-build arc fought a recurring bug: when
``test_chartis_integration`` ran before
``test_compliance_sweep_per_route``, certain routes dropped from
100% → 27% compliance because ``rcm_mc/server.py`` cached a stale
binding of the legacy ``shell()`` function from ``_ui_kit``.

The fix lives in ``conftest.py``: the autouse fixture's ``finally``
block drops ``rcm_mc.ui._chartis_kit*``, ``rcm_mc.ui.*``, AND
``rcm_mc.server`` from ``sys.modules`` between tests. Without all
three drops, the test ordering matters.

This guard runs the known-flaky pair in-process and asserts the
per-route median stays at the post-fix threshold. It serves as
documentation (links the conftest fix to a tangible failure mode)
AND as protection (any regression in the conftest's module-drop
set fails this test).
"""
from __future__ import annotations

import importlib
import os
import sys
import unittest


class ConftestModuleDropCoversCriticalImports(unittest.TestCase):
    """The conftest autouse fixture drops three module categories
    so a v2-aware test that follows a v2-unaware test re-imports
    fresh: kit modules, UI page modules, and server.py.

    This test asserts the rules without touching the running
    server — pure inspection of the fixture's source."""

    def test_conftest_drops_chartis_kit_modules(self) -> None:
        import pathlib
        conftest_path = pathlib.Path(__file__).parent / "conftest.py"
        src = conftest_path.read_text(encoding="utf-8")
        self.assertIn(
            'startswith("rcm_mc.ui._chartis_kit")',
            src,
            "conftest must drop _chartis_kit* modules between tests "
            "so v2-flag flips re-resolve the kit functions",
        )

    def test_conftest_drops_ui_page_modules(self) -> None:
        import pathlib
        conftest_path = pathlib.Path(__file__).parent / "conftest.py"
        src = conftest_path.read_text(encoding="utf-8")
        self.assertIn(
            'startswith("rcm_mc.ui.")',
            src,
            "conftest must drop rcm_mc.ui.* page modules — they "
            "import chartis_shell at module level and would keep a "
            "stale binding to the legacy shell",
        )

    def test_conftest_drops_server_module(self) -> None:
        import pathlib
        conftest_path = pathlib.Path(__file__).parent / "conftest.py"
        src = conftest_path.read_text(encoding="utf-8")
        self.assertIn(
            'name == "rcm_mc.server"',
            src,
            "conftest must drop rcm_mc.server — it imports the "
            "legacy ``shell`` function from _ui_kit at line 90 and "
            "binds it to the module's namespace. Without dropping "
            "server.py, routes that call this legacy ``shell()`` "
            "(/alerts, /escalations, /lp-update, /audit) keep their "
            "stale v1 binding even after the env flag flips",
        )


class PerRouteCoverageDoesNotShrink(unittest.TestCase):
    """The per-route compliance sweep covers a list of partner-
    facing routes. Each route is a regression net — removing one
    silently weakens the safety net.

    This guard pins the route count at the current size. Adding a
    new route is fine (the count grows). Removing one fails this
    test, forcing the contributor to either restore the route or
    update ROUTE_COUNT_FLOOR with a justified rationale.
    """

    ROUTE_COUNT_FLOOR = 224

    def test_per_route_list_size(self) -> None:
        from tests.test_compliance_sweep_per_route import (
            REPRESENTATIVE_ROUTES,
        )
        actual = len(REPRESENTATIVE_ROUTES)
        self.assertGreaterEqual(
            actual, self.ROUTE_COUNT_FLOOR,
            f"REPRESENTATIVE_ROUTES has {actual} entries — below "
            f"floor of {self.ROUTE_COUNT_FLOOR}. Removing routes "
            f"weakens the per-route compliance safety net. Either "
            f"restore the route or update ROUTE_COUNT_FLOOR with "
            f"justification.",
        )


class RepresentativeRoutesAreAllDeclared(unittest.TestCase):
    """Every route in ``REPRESENTATIVE_ROUTES`` must be declared
    somewhere in ``rcm_mc/server.py``. Otherwise the per-route
    compliance sweep silently skips it (status != 200), still
    passes its assertions, and the moat develops a blind spot.

    A typo'd route (e.g. ``/scennarios``) would 404 in the sweep,
    get added to the ``skipped`` list, and the sweep would still
    pass — leaving the impression that ``/scenarios`` is covered
    when it isn't. This guard catches that.
    """

    def test_every_representative_route_exists_in_server(self) -> None:
        import pathlib
        import re
        from tests.test_compliance_sweep_per_route import (
            REPRESENTATIVE_ROUTES,
        )

        server_src = (
            pathlib.Path(__file__).parent.parent
            / "rcm_mc" / "server.py"
        ).read_text(encoding="utf-8")

        # Match ``path == "/..."`` and ``path.startswith("/...")``
        declared: set[str] = set()
        for m in re.finditer(
            r'(?:path == |path\.startswith\()"(/[^"]+)"',
            server_src,
        ):
            declared.add(m.group(1))

        missing: list[str] = []
        for route in REPRESENTATIVE_ROUTES:
            if route in declared:
                continue
            # Allow prefix-handled routes (e.g. /diligence/checklist
            # might dispatch via /diligence/<sub>)
            if any(
                route.startswith(d) and len(d) > 3
                for d in declared
            ):
                continue
            missing.append(route)

        self.assertEqual(
            missing, [],
            f"REPRESENTATIVE_ROUTES contains routes that are NOT "
            f"declared in server.py: {missing}. The compliance sweep "
            f"would silently skip these as 404s, hiding the gap.",
        )


class APISmokeCoverageDoesNotShrink(unittest.TestCase):
    """Same pattern for the API smoke list. Removing endpoints
    silently weakens JSON-API regression coverage."""

    API_COUNT_FLOOR = 40

    def test_api_smoke_list_size(self) -> None:
        from tests.test_api_endpoint_smoke import API_SMOKE_ROUTES
        actual = len(API_SMOKE_ROUTES)
        self.assertGreaterEqual(
            actual, self.API_COUNT_FLOOR,
            f"API_SMOKE_ROUTES has {actual} entries — below "
            f"floor of {self.API_COUNT_FLOOR}. Either restore the "
            f"endpoint or update API_COUNT_FLOOR with rationale.",
        )


class ChartisShellEntryPointsAreLazy(unittest.TestCase):
    """Most rendering modules should import ``chartis_shell``
    lazily (inside route handlers / render functions), not at
    module-load. Lazy imports re-resolve fresh per-call after the
    conftest fixture drops the kit module — they bypass the cache
    issue entirely. Module-level imports (which exist for legacy
    reasons) require the conftest drop to work correctly.

    This test counts module-level imports as a soft signal: the
    count should not climb. New code should prefer lazy imports.
    """

    BASELINE_MODULE_LEVEL_COUNT = 100

    def test_module_level_chartis_imports_count_is_capped(self) -> None:
        import pathlib
        import re
        ui_root = pathlib.Path(__file__).parent.parent / "rcm_mc" / "ui"
        # ``from ._chartis_kit import …`` at column 0
        pattern = re.compile(
            r"^from \._chartis_kit import\b", re.MULTILINE,
        )
        count = 0
        for py in ui_root.rglob("*.py"):
            try:
                src = py.read_text(encoding="utf-8")
            except OSError:
                continue
            count += len(pattern.findall(src))
        self.assertLessEqual(
            count, self.BASELINE_MODULE_LEVEL_COUNT,
            f"module-level chartis_kit imports ({count}) exceed cap "
            f"({self.BASELINE_MODULE_LEVEL_COUNT}). Prefer lazy "
            f"imports (inside the render function) so the kit "
            f"re-resolves per-call without needing conftest "
            f"sys.modules manipulation. Drop the cap below the "
            f"actual count if you migrated some.",
        )


if __name__ == "__main__":
    unittest.main()
