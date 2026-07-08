"""Tests for the IFT Clinical Acute-Transfer Demand Engine.

These make the taxonomy self-verifying: every registry ICD-10-CM code is
validated against the vendored billability seed (so code drift fails the
build), every national volume carries a real honesty label, the destination
supply matches the provider CSVs, and the growth ranking is the aging-cohort
mechanic the thesis rests on.
"""
import unittest
from pathlib import Path

from rcm_mc.market_reports import ift_clinical_demand as m


class TestIFTClinicalRegistry(unittest.TestCase):
    def test_registry_size_in_range(self):
        conds = m.all_conditions()
        self.assertGreaterEqual(len(conds), 25)
        self.assertLessEqual(len(conds), 35)

    def test_all_families_and_transfer_types_present(self):
        conds = m.all_conditions()
        families = {c.family for c in conds}
        self.assertEqual(
            families,
            {m.FAMILY_ESCALATION, m.FAMILY_STEPDOWN, m.FAMILY_LOADBALANCE},
        )
        transfers = {c.transfer_type for c in conds}
        self.assertTrue(transfers <= {m.TRANSFER_UP, m.TRANSFER_DOWN, m.TRANSFER_LATERAL})
        # all three directions actually used
        self.assertEqual(transfers, {m.TRANSFER_UP, m.TRANSFER_DOWN, m.TRANSFER_LATERAL})

    def test_all_four_postacute_settings_represented(self):
        settings = {c.destination_setting for c in m.all_conditions()}
        for tier in ("LTACH", "IRF", "SNF"):
            self.assertIn(tier, settings, f"{tier} destination missing")
        self.assertIn("Hospice", settings)

    def test_every_condition_well_formed(self):
        for c in m.all_conditions():
            self.assertTrue(c.name)
            self.assertTrue(c.presenting)
            self.assertTrue(c.ms_drg, f"{c.name} has no MS-DRG")
            self.assertTrue(c.destination_capability, f"{c.name} has no destination_capability")
            self.assertTrue(c.destination_setting, f"{c.name} has no destination_setting")
            self.assertIn(c.acuity, ("critical", "emergent", "urgent", "stable"))

    def test_escalation_and_stepdown_have_codes(self):
        # Only the capacity-driven load-balancing/direct-admit legs are allowed
        # to be code-agnostic (routed by census / UB-04 point-of-origin).
        for c in m.all_conditions():
            if c.family in (m.FAMILY_ESCALATION, m.FAMILY_STEPDOWN):
                self.assertTrue(c.icd10, f"{c.name} should carry ICD-10 codes")


class TestCodeValidation(unittest.TestCase):
    def test_no_icd10_misses(self):
        # The seed loads offline; if it is empty the environment is broken, not
        # the taxonomy — skip rather than false-fail.
        if not m._valid_icd10():
            self.skipTest("ICD-10 billability seed unavailable offline")
        report = m.validate_codes()
        misses = {name: r["icd10_miss"] for name, r in report.items() if r["icd10_miss"]}
        self.assertEqual(misses, {}, f"non-billable ICD-10 codes drifted in: {misses}")

    def test_pcs_is_reference_only(self):
        # PCS codes are surfaced separately and never asserted billable.
        report = m.validate_codes()
        mi = report["Acute MI / chest pain"]
        self.assertIn("pcs_reference", mi)
        self.assertTrue(len(mi["pcs_reference"]) >= 1)


class TestGrowth(unittest.TestCase):
    def test_growth_ranked_monotonic(self):
        ranked = m.growth_ranked()
        cagrs = [c.growth.cagr for c in ranked]
        self.assertEqual(cagrs, sorted(cagrs, reverse=True))

    def test_aging_cohort_outgrows_pediatric(self):
        by_name = {c.name: c for c in m.all_conditions()}
        hipfx = by_name["Hip fracture (acute ortho-trauma)"].growth.cagr
        neonatal = by_name["Neonatal deterioration"].growth.cagr
        sepsis = by_name["Severe sepsis / septic shock"].growth.cagr
        self.assertGreater(hipfx, neonatal)
        self.assertGreater(hipfx, sepsis)  # 85+ skew beats 65-84 skew
        self.assertGreater(neonatal, -0.001)

    def test_compute_condition_cagr_formula(self):
        # A pure-85+ skew should return ~the 85+ band CAGR (4.5%).
        if not m._pop_growth():
            self.skipTest("demand_forecast model unavailable")
        cagr = m.compute_condition_cagr((("85+", 1.0),))
        self.assertAlmostEqual(cagr, 0.045, places=3)

    def test_growth_labels_illustrative(self):
        for c in m.all_conditions():
            self.assertTrue(c.growth.basis.startswith(m.LABEL_ILLUSTRATIVE))


class TestVolumeHonesty(unittest.TestCase):
    def test_every_volume_labeled(self):
        for c in m.all_conditions():
            label = c.national_volume.source_label
            self.assertTrue(
                any(label.startswith(tag) for tag in m._HONESTY_TAGS),
                f"{c.name} volume label '{label}' lacks an honesty tag",
            )
            self.assertTrue(c.national_volume.measure, f"{c.name} volume has no measure")

    def test_gov_backed_volumes_exist(self):
        gov = [c for c in m.all_conditions()
               if c.national_volume.source_label.startswith(m.LABEL_GOV)
               and c.national_volume.value > 0]
        # The bulk of the acute book is anchored to published GOV counts.
        self.assertGreaterEqual(len(gov), 12)


class TestDestinationSupply(unittest.TestCase):
    def test_national_floors(self):
        # Floors, not exact counts — CSVs may refresh.
        self.assertGreaterEqual(m.destination_supply("SNF")["national"], 12000)
        self.assertGreaterEqual(m.destination_supply("IRF")["national"], 1000)
        self.assertGreaterEqual(m.destination_supply("LTACH")["national"], 250)
        self.assertGreaterEqual(m.destination_supply("HHA")["national"], 10000)
        self.assertGreaterEqual(m.destination_supply("Hospice")["national"], 5000)

    def test_supply_is_sourced(self):
        for k in ("SNF", "IRF", "LTACH", "HHA", "Hospice"):
            self.assertTrue(m.destination_supply(k)["source_label"].startswith(m.LABEL_SOURCED))

    def test_per_state_subset_of_national(self):
        d = m.destination_supply("SNF", state="TX")
        self.assertLessEqual(d["state_count"], d["national"])
        self.assertGreater(d["state_count"], 0)
        # sum of per_state equals national
        self.assertEqual(sum(d["per_state"].values()), d["national"])

    def test_hub_setting_not_fabricated(self):
        d = m.destination_supply("Comprehensive Stroke Center")
        self.assertIsNone(d["national"])
        self.assertIn("authored", d["source_label"])

    def test_no_arg_returns_national_rollup(self):
        # destination_supply() with no setting must return the whole-supply
        # snapshot (not None, not a crash): national = sum of every SOURCED file.
        d = m.destination_supply()
        self.assertIsNotNone(d)
        self.assertIsNone(d["setting"])
        self.assertTrue(d["source_label"].startswith(m.LABEL_SOURCED))
        self.assertEqual(set(d["by_setting"]), set(m._SETTING_CSV))
        self.assertEqual(d["national"], sum(d["by_setting"].values()))
        self.assertEqual(
            d["national"],
            sum(m.destination_supply(k)["national"] for k in m._SETTING_CSV),
        )
        self.assertEqual(sum(d["per_state"].values()), d["national"])

    def test_no_arg_with_state(self):
        d = m.destination_supply(state="TX")
        self.assertEqual(d["state"], "TX")
        self.assertGreater(d["state_count"], 0)
        self.assertLessEqual(d["state_count"], d["national"])


class TestMissionMixAndSummary(unittest.TestCase):
    def test_mission_mix_skews_high_acuity(self):
        mm = m.mission_mix()
        # The escalation book skews toward the high-acuity CCT/SCT + specialty
        # tiers — the headline IFT-thesis output.
        self.assertGreater(mm["high_acuity_share"], mm["mid_acuity_share"])
        self.assertGreater(mm["high_acuity_share"], 0.4)
        self.assertAlmostEqual(
            mm["high_acuity_share"] + mm["mid_acuity_share"] + mm["low_acuity_share"],
            1.0, places=2,
        )

    def test_registry_summary_shape(self):
        rs = m.registry_summary()
        self.assertEqual(rs["n_conditions"], len(m.all_conditions()))
        self.assertEqual(sum(rs["n_by_family"].values()), rs["n_conditions"])
        self.assertEqual(sum(rs["n_by_transfer_type"].values()), rs["n_conditions"])
        self.assertEqual(len(rs["fastest_growth"]), 6)

    def test_transfer_matrix_covers_all(self):
        rows = m.transfer_matrix()
        self.assertEqual(len(rows), len(m.all_conditions()))
        for r in rows:
            self.assertIn("destination_setting", r)
            self.assertIn("cagr", r)

    def test_get_condition(self):
        self.assertIsNotNone(m.get_condition("Ischemic stroke"))
        self.assertIsNone(m.get_condition("nonexistent condition"))


class TestOfflineDiscipline(unittest.TestCase):
    def test_module_does_not_import_hcup_loader(self):
        # Volumes are GOV literals; the NIS loader is store-backed with no
        # vendored rows, so importing it would be a runtime foot-gun. Check the
        # actual import graph (AST), not prose — the docstring names the loader
        # deliberately to explain why it is *not* used.
        import ast
        src = Path(m.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imported.append(node.module or "")
                imported += [f"{node.module}.{a.name}" for a in node.names]
        self.assertFalse(
            any("ahrq_hcup" in name for name in imported),
            f"module must not import the HCUP loader; imports={imported}",
        )


class TestIFTClinicalPage(unittest.TestCase):
    """render_ift_clinical() — the editorial page must be FULL, LEAK-FREE, and
    TAG-BALANCED, and must list every acute scenario, its validated codes, and
    a basis chip on every figure. The page reads the same module the tests
    above pin, so a registry change flows straight into the render.
    """

    @classmethod
    def setUpClass(cls):
        from rcm_mc.ui.ift_clinical_page import render_ift_clinical
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = render_ift_clinical()
        # Bare-shell baseline — the shared shell's JS/CSS templates carry a
        # fixed set of unclosed <table>/<tr>/… tokens and a harmless "NaN".
        # Comparing against it isolates OUR content's contribution.
        cls.base = chartis_shell("<p>x</p>", "t")

    @staticmethod
    def _imbalance(html, tag):
        import re
        return len(re.findall(rf"<{tag}[ >]", html)) - html.count(f"</{tag}>")

    def test_full_document(self):
        self.assertGreater(len(self.html), 20000)
        self.assertIn("<main", self.html)
        self.assertIn("</body>", self.html)
        self.assertIn("Interfacility Transport", self.html)

    def test_lists_every_scenario(self):
        import html as _html
        for c in m.all_conditions():
            self.assertIn(_html.escape(c.name), self.html,
                          f"scenario missing from page: {c.name}")

    def test_lists_representative_codes(self):
        for code in ("I21.9", "A41.9", "I63.9", "S72.001A", "J96.00",
                     "R65.21"):
            self.assertIn(code, self.html, f"code missing from page: {code}")

    def test_basis_chips_on_every_family(self):
        for tag in ("GOV", "SOURCED", "ILLUSTRATIVE", "ACADEMIC"):
            self.assertIn(f">{tag}</span>", self.html,
                          f"missing basis chip: {tag}")

    def test_all_sections_present(self):
        for marker in ("The acute-transfer matrix",
                       "Per-condition clinical demand",
                       "Ranked by projected volume growth",
                       "Transport-acuity split of the escalation book",
                       "Real post-acute destination counts",
                       "volume driver"):
            self.assertIn(marker, self.html, f"section missing: {marker}")

    def test_growth_takeaway_and_real_supply_counts(self):
        self.assertIn("structural", self.html)
        self.assertIn("tailwind", self.html)
        self.assertIn("14,699", self.html)   # SNF supply (SOURCED)
        self.assertIn("1,221", self.html)    # IRF supply (SOURCED)

    def test_content_is_leak_free(self):
        for bad in (">None<", ">nan<", "None</td>", ">nan</td>", ">{",
                    "var(--sc-border,#d8cf"):
            self.assertNotIn(bad, self.html, f"content leak: {bad!r}")

    def test_tag_balance_matches_shell_baseline(self):
        # Our content opens and closes every tag it uses — its per-tag
        # imbalance equals the bare shell's (zero net contribution).
        for tag in ("table", "thead", "tbody", "tr", "td", "th", "section",
                    "code", "div", "header", "p"):
            self.assertEqual(self._imbalance(self.html, tag),
                             self._imbalance(self.base, tag),
                             f"content adds tag imbalance for <{tag}>")

    def test_render_accepts_query_variants(self):
        from rcm_mc.ui.ift_clinical_page import render_ift_clinical
        for qs in (None, {}, {"state": ["TX"]}):
            html = render_ift_clinical(qs)
            self.assertIn("Interfacility Transport", html)


if __name__ == "__main__":
    unittest.main()
