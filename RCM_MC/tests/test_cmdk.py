"""tests for the cmd-K command palette.

PROMPTS.md Phase 4 / Prompt 46. Every page must ship a working cmd-K
palette out of the box — no per-page wiring. The default route
catalog covers the platform's main partner-facing surfaces; pages
can supply a richer module list (deals, glossary, audit events) by
passing ``palette_modules`` to chartis_shell.
"""
from __future__ import annotations

import os
import sys
import unittest


class PaletteShipsByDefault(unittest.TestCase):

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>x</p>", "T")

    def test_palette_div_present(self) -> None:
        self.assertIn('id="ck-palette"', self.html)

    def test_palette_input_present(self) -> None:
        self.assertIn("Jump to… (⌘K)", self.html)

    def test_default_routes_in_palette(self) -> None:
        # Spot-check a handful of canonical entries.
        for needle in (
            'data-route="/home"',
            'data-route="/library"',
            'data-route="/diligence/risk-workbench"',
            'data-route="/lp-update"',
        ):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.html)


class PaletteOptOut(unittest.TestCase):

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)

    def test_include_palette_false_drops_palette(self) -> None:
        from rcm_mc.ui._chartis_kit_v2 import chartis_shell
        html = chartis_shell("<p>x</p>", "T", include_palette=False)
        self.assertNotIn('id="ck-palette"', html)


class PaletteAcceptsCustomModules(unittest.TestCase):

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)

    def test_custom_modules_override_default(self) -> None:
        from rcm_mc.ui._chartis_kit_v2 import chartis_shell

        html = chartis_shell(
            "<p>x</p>", "T",
            palette_modules=[
                {"id": "aurora", "title": "Project Aurora",
                 "route": "/deal/aurora"},
            ],
        )
        # Custom entry present.
        self.assertIn("Project Aurora", html)
        self.assertIn('data-route="/deal/aurora"', html)
        # Default route catalog NOT mixed in (caller-supplied overrides).
        self.assertNotIn('data-route="/library"', html)


class PaletteJSWired(unittest.TestCase):

    def setUp(self) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>x</p>", "T")

    def test_cmd_k_keybinding_present(self) -> None:
        # The palette JS binds on cmd+k / ctrl+k; pin both branches.
        self.assertIn("metaKey", self.html)
        self.assertIn("ctrlKey", self.html)
        self.assertIn("'k'", self.html)


if __name__ == "__main__":
    unittest.main()
