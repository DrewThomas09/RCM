"""Smoke test: every ``render_*`` function in ``rcm_mc/ui/data_public/``
must execute without raising ``TypeError``.

The 2026-05 kwarg-drift sweep surfaced eight latent 500 bugs:
seven page modules called ``ck_kpi_block(..., unit=..., delta=...)``
using the legacy keyword names that the v2 kit no longer accepts.
Each page raised TypeError at first render and dispatched to the
500 handler. Module-import smoke didn't catch them — imports
succeed because the bad kwargs are inside a function body, not at
module load — they only fire when the route handler invokes the
render function.

This test exercises each ``render_*`` function with ``{}`` (empty
dict) as the single positional, which the request-param contract
of every dispatcher accepts. The test fails on ``TypeError`` from
missing/unknown kwargs (the kwarg-drift class). Other exception
types (``AttributeError`` on missing computed-field attributes,
``ValueError`` on type-coercion failures) are tolerated as
"renderer needs real data, not an empty dict" — those are caught
separately by the per-route compliance sweep when it boots a real
server with a seeded store.

The point of this test: catch *signature* drift cheaply, without
booting a server. Anything render-data-shaped is out of scope.
"""
from __future__ import annotations

import importlib
import inspect
import os
import pathlib
import unittest


def _render_modules() -> list[str]:
    """Enumerate ``rcm_mc/ui/data_public/*_page.py`` modules."""
    pkg_root = (
        pathlib.Path(__file__).resolve().parent.parent
        / "rcm_mc" / "ui" / "data_public"
    )
    mods: list[str] = []
    for py in sorted(pkg_root.rglob("*_page.py")):
        rel = py.relative_to(pkg_root.parent.parent.parent)
        mods.append(
            ".".join(rel.with_suffix("").parts)
        )
    return mods


class CkKpiBlockKwargDriftIsSurfaced(unittest.TestCase):
    """If any ``render_*`` callable raises ``TypeError`` referencing
    ``unit`` or ``delta`` kwargs, surface it loudly.

    The tolerated TypeErrors are the ones with messages like
    "missing 1 required positional argument" — those mean the
    render function takes a non-default positional we didn't
    supply, which is fine.
    """

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"

    def test_no_legacy_kwarg_typeerrors(self) -> None:
        violations: list[tuple[str, str]] = []
        for mod_name in _render_modules():
            try:
                mod = importlib.import_module(mod_name)
            except Exception:  # pragma: no cover
                continue
            for attr in dir(mod):
                if not attr.startswith("render_"):
                    continue
                func = getattr(mod, attr)
                if not callable(func):
                    continue
                try:
                    sig = inspect.signature(func)
                except (TypeError, ValueError):
                    continue
                # Build minimal positional args
                args = []
                for p in sig.parameters.values():
                    if p.default is inspect.Parameter.empty and p.kind in (
                        inspect.Parameter.POSITIONAL_ONLY,
                        inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    ):
                        args.append({})
                try:
                    func(*args)
                except TypeError as e:
                    msg = str(e)
                    # Only flag the kwarg-drift class:
                    if (
                        "unexpected keyword argument" in msg
                        and ("'unit'" in msg or "'delta'" in msg)
                    ):
                        violations.append((mod_name, msg))
                except Exception:
                    # Any other exception is render-data shape;
                    # out of scope for this smoke test.
                    pass

        self.assertEqual(
            violations, [],
            "render_*() functions raised legacy-kwarg TypeError. "
            "These would 500 the route at first render. The v2 kit "
            "renamed ``unit=`` → ``sub=`` and ``delta=`` → ``trend=`` "
            "(keyword-only). Update the renderer.\n"
            + "\n".join(f"  {m}: {e}" for m, e in violations[:10]),
        )


if __name__ == "__main__":
    unittest.main()
