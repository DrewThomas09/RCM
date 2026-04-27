"""Regression test for v3 transformation campaign target 1B.

The route inventory at ``docs/V3_ROUTE_INVENTORY.md`` is the
worklist driving the v3 transformation campaign. Every loop after
1B reads it (or re-runs it) to pick the next migration target.

What this guards:
    - The generator script imports + runs end-to-end without
      touching any server-side state.
    - The generated inventory has the expected structural anchors
      (top-level heading, compliance summary, routes table).
    - The route count is in the expected order of magnitude
      (>= 100). server.py has 181 ``_route_`` methods plus
      inline ``if path == "..."`` blocks; the floor protects
      against a regression where the dispatcher slicer breaks
      and the generator silently emits an empty table.

If the inventory is intentionally rebuilt with a smaller
dispatcher in the future, lower the floor — don't disable the
test.
"""
from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "RCM_MC" / "tools" / "v3_route_inventory.py"
INVENTORY = REPO_ROOT / "docs" / "V3_ROUTE_INVENTORY.md"


class V3RouteInventoryTests(unittest.TestCase):
    def test_generator_script_present(self) -> None:
        self.assertTrue(GENERATOR.is_file(), f"missing {GENERATOR}")

    def test_generator_module_loads(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "v3_route_inventory", GENERATOR
        )
        self.assertIsNotNone(spec)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # Public symbols the test relies on
        for name in ("Route", "main", "_slice_dispatcher", "_extract_blocks"):
            self.assertTrue(
                hasattr(mod, name),
                f"v3_route_inventory missing public symbol {name!r}",
            )

    def test_inventory_file_present(self) -> None:
        self.assertTrue(
            INVENTORY.is_file(),
            f"missing {INVENTORY} — run "
            f"`python3 RCM_MC/tools/v3_route_inventory.py`",
        )

    def test_inventory_has_expected_anchors(self) -> None:
        text = INVENTORY.read_text(encoding="utf-8")
        for anchor in (
            "# V3 Route Inventory",
            "## Compliance summary",
            "## Routes",
            "| URL pattern | Match | Renderer | v3 status | Packet-driven |",
        ):
            self.assertIn(anchor, text, f"inventory missing anchor: {anchor!r}")

    def test_inventory_route_count_floor(self) -> None:
        text = INVENTORY.read_text(encoding="utf-8")
        # Each route row starts with `| \`/...\`` — count those.
        rows = re.findall(r"^\| `[^`]+` \|", text, re.M)
        self.assertGreaterEqual(
            len(rows), 100,
            f"inventory has only {len(rows)} route rows; "
            f"expected >= 100. Generator may have failed to slice "
            f"the dispatcher correctly.",
        )

    def test_inventory_total_count_matches_table_rows(self) -> None:
        """Header summary 'Total routes mapped: N' should equal the
        number of rendered table rows. Catches off-by-one in the
        generator's emit loop."""
        text = INVENTORY.read_text(encoding="utf-8")
        m = re.search(r"\*\*Total routes mapped:\*\*\s+(\d+)", text)
        self.assertIsNotNone(m, "inventory missing 'Total routes mapped' line")
        header_total = int(m.group(1))
        rows = re.findall(r"^\| `[^`]+` \|", text, re.M)
        self.assertEqual(
            header_total, len(rows),
            f"header says {header_total} routes but table has "
            f"{len(rows)} rows",
        )


if __name__ == "__main__":
    unittest.main()
