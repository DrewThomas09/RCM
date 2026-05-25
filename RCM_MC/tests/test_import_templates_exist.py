"""Import templates referenced by the activation plan must exist and be
schema-only (header + a clearly-non-real placeholder row; no fabricated data)."""
import csv
import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TPL = _ROOT / "docs" / "import_templates"
_PLAN = _ROOT / "docs" / "reports" / "RED_PAGE_ACTIVATION_PLAN.md"
_PLACEHOLDER = re.compile(r"^<.*>$")


class ImportTemplatesTests(unittest.TestCase):
    def test_templates_dir_populated(self):
        files = list(_TPL.glob("*_template.csv"))
        self.assertGreaterEqual(len(files), 20, "expected the import-template set")

    def test_each_template_is_schema_only(self):
        for f in _TPL.glob("*_template.csv"):
            rows = list(csv.reader(f.open()))
            self.assertGreaterEqual(len(rows), 2, f"{f.name}: needs header + placeholder")
            header = rows[0]
            self.assertTrue(all(h.strip() for h in header), f"{f.name}: blank header field")
            # data rows must be placeholders only — never fabricated real values
            for r in rows[1:]:
                for cell in r:
                    c = cell.strip()
                    if c:
                        self.assertTrue(_PLACEHOLDER.match(c),
                                        f"{f.name}: non-placeholder value {c!r} (no fake data)")

    def test_plan_referenced_templates_exist(self):
        text = _PLAN.read_text()
        for name in re.findall(r"([a-z0-9_]+_template\.csv)", text):
            self.assertTrue((_TPL / name).exists(), f"plan references missing template {name}")


if __name__ == "__main__":
    unittest.main()
