import unittest

from ..transport import HrsaApiError, HrsaTransport
from .fakes import FakeHrsa, hpsa_pc_csv, mua_csv

_PC_PATH = "/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv"
_MUA_PATH = "/DataDownload/DD_Files/MUA_DET.csv"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return HrsaTransport(**kw)

    def test_build_url_is_deterministic(self):
        t = self._transport()
        self.assertEqual(
            t.build_url(_PC_PATH),
            "https://data.hrsa.gov/DataDownload/DD_Files/BCD_HPSA_FCT_DET_PC.csv")

    def test_200_parses_rows_and_drops_dangling_header(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        t = self._transport()
        res = t.get_csv(_PC_PATH, opener=fake)
        self.assertEqual(len(res.rows), 3)
        self.assertFalse(res.truncated)
        # Trailing empty header cell (dangling comma) must be gone.
        self.assertNotIn("", res.fieldnames)
        self.assertEqual(len(res.fieldnames), 65)
        # Raw headers survive verbatim (snake_casing is normalize's job).
        self.assertIn("HPSA ID", res.fieldnames)
        self.assertIn("% of Population Below 100% Poverty", res.fieldnames)
        self.assertEqual(res.rows[0]["HPSA ID"], "1481234567")
        # Raw values keep live padding — stripping is normalize's job.
        self.assertEqual(res.rows[0]["PC MCTA Score"], " 6")

    def test_quoted_comma_value_survives(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        res = self._transport().get_csv(_PC_PATH, opener=fake)
        self.assertEqual(res.rows[1]["HPSA Component Name"],
                         "Hereford, city of")

    def test_bom_is_stripped_from_first_header(self):
        fake = FakeHrsa().add(_MUA_PATH, "\ufeff" + mua_csv())
        res = self._transport().get_csv(_MUA_PATH, opener=fake)
        self.assertEqual(res.fieldnames[0], "MUA/P ID")

    def test_max_rows_caps_and_flags_truncation(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        res = self._transport().get_csv(_PC_PATH, max_rows=2, opener=fake)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)
        # Exactly at the row count → not truncated.
        res2 = self._transport().get_csv(_PC_PATH, max_rows=3, opener=fake)
        self.assertEqual(len(res2.rows), 3)
        self.assertFalse(res2.truncated)

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        res = t.get_csv(_PC_PATH, opener=fake,
                        sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 3)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(HrsaApiError):
            t.get_csv(_PC_PATH, opener=fake,
                      sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # initial + 2 retries

    def test_404_raises_with_rename_pointer(self):
        fake = FakeHrsa()  # nothing registered → 404
        t = self._transport()
        with self.assertRaises(HrsaApiError) as ctx:
            t.get_csv("/DataDownload/DD_Files/GONE.csv", opener=fake,
                      sleep=lambda s: None)
        self.assertIn("data.hrsa.gov/data/download", str(ctx.exception))
        self.assertEqual(len(fake.calls), 1)  # no retry on a 404

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeHrsa()
        fake.transients[0] = (403, {})
        t = self._transport()
        with self.assertRaises(HrsaApiError):
            t.get_csv(_PC_PATH, opener=fake, sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)

    def test_empty_body_raises_clear_error(self):
        fake = FakeHrsa().add(_PC_PATH, "")
        t = self._transport()
        with self.assertRaises(HrsaApiError) as ctx:
            t.get_csv(_PC_PATH, opener=fake, sleep=lambda s: None)
        self.assertIn("empty CSV", str(ctx.exception))

    def test_header_only_file_yields_zero_rows(self):
        header_only = hpsa_pc_csv().splitlines()[0] + "\r\n"
        fake = FakeHrsa().add(_PC_PATH, header_only)
        res = self._transport().get_csv(_PC_PATH, opener=fake)
        self.assertEqual(res.rows, [])
        self.assertFalse(res.truncated)


if __name__ == "__main__":
    unittest.main()
