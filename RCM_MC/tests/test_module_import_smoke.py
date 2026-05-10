"""Smoke test: every UI module must import cleanly under both
v1-legacy and v2-editorial chartis kits.

The recent ``bear_case_page.py`` regression (commit 8601d58)
exposed a silent failure mode: the module had ``P["brand_accent"]``
at module level, which raises ``KeyError`` when the legacy chartis
kit's ``P`` dict is in scope (the legacy dict only has ``accent``).

The bug only surfaced when pytest re-collected ``test_preview_panel
_migration.py`` (which imports ``bear_case_page``) under filter
options. In normal runs, the test was already in the cache and
the import-time crash didn't fire — so the bug lurked silently
across multiple commits.

This guard imports every module under ``rcm_mc/ui/`` under both
``CHARTIS_UI_V2=1`` and ``CHARTIS_UI_V2`` unset. Any import-time
exception (KeyError, ImportError, AttributeError, etc.) fails
the test with a clear path + traceback.
"""
from __future__ import annotations

import importlib
import os
import pathlib
import sys
import unittest


def _ui_modules() -> list[str]:
    """Enumerate every importable module name under rcm_mc/ui/."""
    pkg_root = (
        pathlib.Path(__file__).resolve().parent.parent
        / "rcm_mc" / "ui"
    )
    names: list[str] = []
    for py in pkg_root.rglob("*.py"):
        rel = py.relative_to(pkg_root.parent.parent)
        # rcm_mc/ui/foo.py → rcm_mc.ui.foo
        # rcm_mc/ui/sub/foo.py → rcm_mc.ui.sub.foo
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1][:-3]
        names.append(".".join(parts))
    return sorted(names)


def _drop_ui_modules() -> None:
    """Drop cached ``rcm_mc.ui.*`` and ``rcm_mc.server`` modules
    so subsequent imports re-resolve under the current env flag."""
    for name in list(sys.modules):
        if (
            name.startswith("rcm_mc.ui.")
            or name.startswith("rcm_mc.ui._chartis_kit")
            or name == "rcm_mc.server"
        ):
            sys.modules.pop(name, None)


class EveryUIModuleImportsCleanly(unittest.TestCase):
    """Each UI module must import without raising under both
    chartis-kit modes. Catches module-level expressions that
    depend on env-conditional dict keys (the bear_case
    ``P["brand_accent"]`` regression)."""

    def _import_all(self, env_flag: str) -> list[tuple[str, str]]:
        prior = os.environ.get("CHARTIS_UI_V2")
        if env_flag is None:
            os.environ.pop("CHARTIS_UI_V2", None)
        else:
            os.environ["CHARTIS_UI_V2"] = env_flag

        _drop_ui_modules()

        failures: list[tuple[str, str]] = []
        for mod_name in _ui_modules():
            try:
                importlib.import_module(mod_name)
            except Exception as e:  # noqa: BLE001 — catch all
                failures.append((mod_name, f"{type(e).__name__}: {e}"))

        # Restore env so subsequent tests see consistent state.
        if prior is None:
            os.environ.pop("CHARTIS_UI_V2", None)
        else:
            os.environ["CHARTIS_UI_V2"] = prior
        _drop_ui_modules()

        return failures

    def test_imports_under_v2_editorial(self) -> None:
        failures = self._import_all("1")
        self.assertEqual(
            failures, [],
            f"{len(failures)} modules failed to import under v2:\n"
            + "\n".join(f"  {n}: {e}" for n, e in failures[:20]),
        )

    def test_imports_under_v1_legacy(self) -> None:
        failures = self._import_all(None)
        self.assertEqual(
            failures, [],
            f"{len(failures)} modules failed to import under v1:\n"
            + "\n".join(f"  {n}: {e}" for n, e in failures[:20]),
        )


if __name__ == "__main__":
    unittest.main()
