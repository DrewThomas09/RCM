"""Every DATA REQUIRED surface must render the honest data-needed panel.

Product-readiness guard: a route classified `data_required` in the surface
taxonomy must have a page that calls `data_required_panel(...)` — i.e. it
shows what to upload instead of presenting fabricated values as real. If a
route is added to `_DATA_REQUIRED` without wiring the panel (or a panel is
removed), this fails.

Resolution is source-based: for each DATA REQUIRED route, find the page
file(s) that reference the route and assert at least one calls the panel.
"""
import glob
import unittest
from pathlib import Path

from rcm_mc.diligence.surface_status import _DATA_REQUIRED

_UI = Path(__file__).resolve().parents[1] / "rcm_mc" / "ui"
_PAGE_FILES = glob.glob(str(_UI / "**" / "*page*.py"), recursive=True)


def _files_for_route(route: str) -> list:
    """Page files that reference this route (via active_nav / path match)."""
    needle = f'"{route}"'
    out = []
    for f in _PAGE_FILES:
        txt = Path(f).read_text(errors="ignore")
        if needle in txt or f"'{route}'" in txt or f"active_nav=\"{route}\"" in txt:
            out.append(f)
    return out


class DataRequiredPanelTests(unittest.TestCase):
    def test_every_data_required_route_renders_the_panel(self):
        missing = []
        for route in sorted(_DATA_REQUIRED):
            files = _files_for_route(route)
            if not files:
                missing.append(f"{route}: no page file references it")
                continue
            if not any("data_required_panel(" in Path(f).read_text(errors="ignore")
                       for f in files):
                missing.append(f"{route}: page has no data_required_panel() call")
        self.assertEqual(missing, [], "DATA REQUIRED pages missing the data-needed panel:\n"
                         + "\n".join(missing))

    def test_panel_helper_is_honest(self):
        # the shared helper must not fabricate values — it renders a needed-field
        # table + template reference, labelled DATA REQUIRED.
        src = (_UI / "data_public" / "_benchmark_panels.py").read_text()
        self.assertIn("def data_required_panel", src)
        self.assertIn("Data needed to activate this analysis", src)
        self.assertIn("no values are fabricated", src)


if __name__ == "__main__":
    unittest.main()
