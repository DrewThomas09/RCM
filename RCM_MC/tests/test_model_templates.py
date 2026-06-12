"""Tests for the Excel model-template library and the xlsx_writer
formula/style extensions that power it.

The templates ship to partners as working models, so the guards here
are about trust: every registry slug must build a valid OOXML zip with
the declared sheets, formulas must land as live ``<f>`` elements (not
text), and formulas must remain opt-in via the F wrapper so a string
that merely *looks* like a formula can never execute (the same
injection class the CSV exporters defang).
"""
from __future__ import annotations

import io
import re
import unittest
import zipfile

from rcm_mc.exports.model_templates import (
    TEMPLATES, build_template_xlsx, get_template,
)
from rcm_mc.exports.xlsx_writer import F, Sheet, write_xlsx


def _sheet_xmls(data: bytes) -> list:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = sorted(n for n in z.namelist()
                       if n.startswith("xl/worksheets/"))
        return [z.read(n).decode("utf-8") for n in names]


class XlsxWriterFormulaTests(unittest.TestCase):
    def test_formula_cell_renders_f_element(self):
        data = write_xlsx([Sheet("S", [[(F("SUM(A2:A4)"), "money2")]])])
        xml = _sheet_xmls(data)[0]
        self.assertIn("<f>SUM(A2:A4)</f>", xml)
        self.assertNotIn("inlineStr", xml)

    def test_plain_string_starting_with_equals_stays_text(self):
        # The injection guard: "=cmd|..." pasted into a template field
        # must serialize as an inline string, never a formula.
        data = write_xlsx([Sheet("S", [["=2+2"]])])
        xml = _sheet_xmls(data)[0]
        self.assertNotIn("<f>", xml)
        self.assertIn("=2+2", xml)
        self.assertIn("inlineStr", xml)

    def test_formula_expr_is_xml_escaped(self):
        data = write_xlsx([Sheet("S", [[F('IF(A1<5,"a","b")')]])])
        xml = _sheet_xmls(data)[0]
        self.assertIn("A1&lt;5", xml)

    def test_new_styles_have_cellxfs_entries(self):
        from rcm_mc.exports.xlsx_writer import _STYLE_IDS, _STYLES_XML
        n_xfs = _STYLES_XML.count("<xf ") + _STYLES_XML.count("<xf\n")
        # cellStyleXfs has one <xf>; cellXfs must cover every style id.
        self.assertGreaterEqual(n_xfs - 1, max(_STYLE_IDS.values()) + 1)
        for style in ("mult", "label", "input", "input_money",
                      "input_pct", "input_num"):
            self.assertIn(style, _STYLE_IDS)


class TemplateRegistryTests(unittest.TestCase):
    def test_slugs_unique_and_url_safe(self):
        slugs = [t.slug for t in TEMPLATES]
        self.assertEqual(len(slugs), len(set(slugs)))
        for slug in slugs:
            self.assertRegex(slug, r"^[a-z0-9-]+$")

    def test_get_template(self):
        self.assertIsNotNone(get_template("quick-lbo"))
        self.assertIsNone(get_template("not-a-template"))

    def test_unknown_slug_builds_none(self):
        self.assertIsNone(build_template_xlsx("not-a-template"))

    def test_every_template_builds_valid_workbook(self):
        for spec in TEMPLATES:
            data = build_template_xlsx(spec.slug)
            self.assertIsInstance(data, bytes, spec.slug)
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                self.assertIsNone(z.testzip(), spec.slug)
                wb = z.read("xl/workbook.xml").decode("utf-8")
            for sheet_name in spec.sheets:
                self.assertIn(f'name="{sheet_name}"', wb, spec.slug)

    def test_every_template_has_live_formulas_and_inputs(self):
        # A template without formulas is a data dump; one without
        # blue-input cells gives the user nothing to edit.
        for spec in TEMPLATES:
            xmls = "".join(_sheet_xmls(build_template_xlsx(spec.slug)))
            self.assertIn("<f>", xmls,
                          f"{spec.slug} has no live formulas")
            input_ids = [str(i) for i in range(9, 13)]  # input* styles
            self.assertTrue(
                any(re.search(rf'\bs="{i}"', xmls) for i in input_ids),
                f"{spec.slug} has no editable input cells")

    def test_declared_sheets_match_builder_output(self):
        for spec in TEMPLATES:
            built = [s.name for s in spec.builder()]
            self.assertEqual(built, spec.sheets, spec.slug)

    def test_lbo_formula_cell_references_resolve(self):
        # The Quick LBO is the template partners will sanity-check
        # first; pin the load-bearing return formulas to their cells.
        sheet = get_template("quick-lbo").builder()[0]

        def cell(row_1based, col_0based):
            return sheet.rows[row_1based - 1][col_0based]

        self.assertEqual(cell(32, 1)[0].expr, "B31/B11")        # MOIC
        self.assertEqual(cell(33, 1)[0].expr, "(B31/B11)^(1/5)-1")  # IRR
        self.assertEqual(cell(7, 1)[0].expr, "B5*B6")           # TEV


if __name__ == "__main__":
    unittest.main()
