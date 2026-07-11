"""Invariants of the committed IFT Sourced Evidence Master v3 deliverable.

Validates the shipped workbook without regenerating it (no network, no
LibreOffice): structure, governance integrity, the no-illustrative rule, and
the deliverable gates (tabs >= 200, printed-page estimate >= 200, >= 15MB).
"""
import json
import os
import re
import unittest

RCM_MC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DELIV = os.path.join(RCM_MC, 'deliverables', 'IFT_Sourced_Evidence_Master_v3_1.xlsx')
PIPE = os.path.join(RCM_MC, 'scripts', 'ift_evidence_v3')
CACHE = os.path.join(RCM_MC, 'rcm_mc', 'market_reports', 'reference', 'ift_v3_cache')

try:
    import openpyxl  # noqa: F401
    HAVE_OPENPYXL = True
except ImportError:
    HAVE_OPENPYXL = False


@unittest.skipUnless(HAVE_OPENPYXL, 'openpyxl not installed')
@unittest.skipUnless(os.path.exists(DELIV), 'deliverable not present')
class TestIFTEvidenceV3(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from openpyxl import load_workbook
        cls.wb = load_workbook(DELIV, read_only=False)

    def test_deliverable_gates(self):
        self.assertGreaterEqual(len(self.wb.sheetnames), 200)
        self.assertGreaterEqual(os.path.getsize(DELIV), 15_000_000)

    def test_governance_tabs_present(self):
        for tab in ('README', 'Methodology', 'Fact_Ledger', 'Source_Register',
                    'Source_Index', 'Verification_Log', 'V3_Change_Log',
                    'Pull_Manifest', 'Excluded_Not_Sourced'):
            self.assertIn(tab, self.wb.sheetnames)

    def test_fact_ids_contiguous(self):
        fids = []
        for row in self.wb['Fact_Ledger'].iter_rows(min_col=1, max_col=1):
            v = row[0].value
            if isinstance(v, str) and re.fullmatch(r'F\d+', v):
                fids.append(int(v[1:]))
        self.assertGreaterEqual(max(fids), 433)
        missing = set(range(1, max(fids) + 1)) - set(fids)
        self.assertEqual(missing, set(), f'missing fact IDs: {sorted(missing)[:10]}')

    def test_source_ids_contiguous(self):
        sids = []
        for row in self.wb['Source_Index'].iter_rows(min_col=1, max_col=1):
            v = row[0].value
            if isinstance(v, str) and re.fullmatch(r'S\d+', v):
                sids.append(int(v[1:]))
        self.assertGreaterEqual(max(sids), 306)
        missing = set(range(1, max(sids) + 1)) - set(sids)
        self.assertEqual(missing, set(), f'missing source IDs: {sorted(missing)[:10]}')

    def test_pull_manifest_matches_cache(self):
        man_path = os.path.join(CACHE, 'manifest.json')
        if not os.path.exists(man_path):
            self.skipTest('cache not present')
        man = json.load(open(man_path))
        cells = set()
        for row in self.wb['Pull_Manifest'].iter_rows(min_col=1, max_col=1):
            v = row[0].value
            if isinstance(v, str):
                cells.add(v)
        missing = [k for k in man if k not in cells]
        self.assertEqual(missing, [], f'manifest keys missing from tab: {missing[:5]}')

    def test_no_banned_illustrative_figures(self):
        banned = [re.compile(p, re.I) for p in
                  (r'\$6\.5\s*B', r'\$18[-–]22\s*B', r'165\.8')]
        hits = []
        for name in self.wb.sheetnames:
            if name == 'Excluded_Not_Sourced':
                continue
            for row in self.wb[name].iter_rows():
                for c in row:
                    if isinstance(c.value, str):
                        for rx in banned:
                            if rx.search(c.value):
                                hits.append(f'{name}!{c.coordinate}')
        self.assertEqual(hits, [], f'banned figures outside quarantine: {hits[:5]}')

    def test_charts_present(self):
        n = sum(len(self.wb[s]._charts) for s in self.wb.sheetnames)
        self.assertGreaterEqual(n, 150)

    def test_granular_families_present(self):
        names = set(self.wb.sheetnames)
        for y in range(2010, 2025):
            self.assertIn(f'PSPS_Detail_{y}', names)
        for y in range(2013, 2025):
            self.assertIn(f'MUP_State_{y}', names)
        for y in range(2020, 2026):
            self.assertIn(f'MS_County_{y}', names)
        for tab in ('PECOS_Registry', 'Hosp_Registry', 'SNF_Registry',
                    'HSA_Hospital_Catchment', 'ED_Timeliness_Registry', 'SP_Index',
                    'Index', 'State_Age_65plus', 'OEWS_EMS_Wages'):
            self.assertIn(tab, names)

    def test_state_profiles_are_formula_driven(self):
        ws = self.wb['SP_TX']
        n_formula = sum(1 for row in ws.iter_rows() for c in row
                        if isinstance(c.value, str) and c.value.startswith('='))
        self.assertGreaterEqual(n_formula, 15)


@unittest.skipUnless(os.path.exists(PIPE), 'pipeline not present')
class TestPipelineArtifacts(unittest.TestCase):

    def test_pipeline_files_present(self):
        for f in ('assemble.py', 'pull.py', 'verify.py', 'v3lib.py',
                  'copy_engine.py', 'corrections.py', 'README.md'):
            self.assertTrue(os.path.exists(os.path.join(PIPE, f)), f)

    def test_verify_results_all_green(self):
        p = os.path.join(PIPE, 'verify_results.json')
        self.assertTrue(os.path.exists(p))
        r = json.load(open(p))
        self.assertEqual(r.get('n_errors'), 0)
        self.assertEqual(r.get('copy_diffs'), 0)
        self.assertEqual(r.get('n_mismatch'), 0)
        self.assertGreaterEqual(r.get('pages', 0), 200)


if __name__ == '__main__':
    unittest.main()
