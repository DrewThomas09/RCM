"""Healthcare Revenue Leakage V2 — VDR ZIP ingestion tests."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from rcm_mc.diligence.ingestion import extract_zip
from rcm_mc.diligence.snapshot import run_snapshot_from_zip

_FIX = Path(__file__).parent / "fixtures" / "edi"


def _make_zip(dirpath: Path) -> Path:
    zp = dirpath / "vdr_package.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.write(_FIX / "clean_837p.edi", "claims/clean_837p.edi")
        zf.write(_FIX / "clean_835.edi", "remits/clean_835.edi")
        zf.writestr("README.pdf", b"%PDF- not supported")
        zf.writestr("../evil.edi", b"ISA*malicious")   # path traversal
    return zp


class TestExtractZip(unittest.TestCase):
    def test_extracts_supported_skips_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            zp = _make_zip(tmp)
            res = extract_zip(zp, tmp / "out")
            names = sorted(p.name for p in res.extracted_files)
            self.assertEqual(names, ["clean_835.edi", "clean_837p.edi"])
            self.assertTrue(any("README.pdf" in s for s in res.skipped))

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            zp = _make_zip(tmp)
            res = extract_zip(zp, tmp / "out")
            self.assertTrue(any("evil.edi" in s and "unsafe" in s
                                for s in res.skipped))
            # Nothing escaped the destination dir.
            for p in res.extracted_files:
                self.assertTrue(str(p.resolve()).startswith(str((tmp / "out").resolve())))

    def test_bad_zip_records_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bad = tmp / "notazip.zip"
            bad.write_bytes(b"not a zip at all")
            res = extract_zip(bad, tmp / "out")
            self.assertEqual(res.extracted_files, [])
            self.assertTrue(res.warnings)


class TestRunFromZip(unittest.TestCase):
    def test_full_pipeline_from_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            zp = _make_zip(Path(tmp))
            res = run_snapshot_from_zip(zp, deal_name="Project Atlas", salt="s")
        self.assertEqual(len(res.ccd.claims), 2)
        self.assertEqual(res.match.counts()["high"], 2)
        self.assertIn("## 1. Executive summary", res.memo_markdown)

    def test_empty_zip_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            zp = Path(tmp) / "empty.zip"
            with zipfile.ZipFile(zp, "w") as zf:
                zf.writestr("notes.pdf", b"%PDF-")
            with self.assertRaises(ValueError):
                run_snapshot_from_zip(zp)


if __name__ == "__main__":
    unittest.main()
