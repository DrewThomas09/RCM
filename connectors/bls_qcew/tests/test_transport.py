import unittest

from ..transport import QcewApiError, QcewTransport
from .fakes import FakeQcew, area_48453_csv, industry_622_csv

_IND_PATH = "/cew/data/api/2025/4/industry/622.csv"
_AREA_PATH = "/cew/data/api/2025/4/area/48453.csv"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return QcewTransport(**kw)

    def test_build_url_is_deterministic(self):
        t = self._transport()
        self.assertEqual(
            t.build_url(_IND_PATH),
            "https://data.bls.gov/cew/data/api/2025/4/industry/622.csv")

    def test_200_parses_rows_with_live_quoting_mix(self):
        fake = FakeQcew().add(_IND_PATH, industry_622_csv())
        t = self._transport()
        res = t.get_csv(_IND_PATH, opener=fake)
        self.assertEqual(len(res.rows), 6)
        self.assertFalse(res.truncated)
        self.assertEqual(len(res.fieldnames), 42)
        # Headers survive verbatim (they are already snake_case).
        self.assertEqual(res.fieldnames[0], "area_fips")
        self.assertIn("oty_avg_wkly_wage_pct_chg", res.fieldnames)
        # Quoted dimension cells and bare numeric cells both land as str.
        self.assertEqual(res.rows[0]["area_fips"], "US000")
        self.assertEqual(res.rows[0]["month3_emplvl"], "5421400")
        # Raw values keep padding — stripping is normalize's job.
        self.assertEqual(res.rows[2]["avg_wkly_wage"], " 1725")
        # Empty disclosure cells stay empty strings.
        self.assertEqual(res.rows[0]["disclosure_code"], "")
        self.assertEqual(res.rows[5]["disclosure_code"], "N")

    def test_max_rows_caps_and_flags_truncation(self):
        fake = FakeQcew().add(_AREA_PATH, area_48453_csv())
        res = self._transport().get_csv(_AREA_PATH, max_rows=2, opener=fake)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)
        # Exactly at the row count → not truncated.
        res2 = self._transport().get_csv(_AREA_PATH, max_rows=6, opener=fake)
        self.assertEqual(len(res2.rows), 6)
        self.assertFalse(res2.truncated)

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeQcew().add(_IND_PATH, industry_622_csv())
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        res = t.get_csv(_IND_PATH, opener=fake,
                        sleep=sleeps.append, now=lambda: 0.0,
                        rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 6)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeQcew().add(_IND_PATH, industry_622_csv())
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(QcewApiError):
            t.get_csv(_IND_PATH, opener=fake,
                      sleep=lambda s: None, now=lambda: 0.0,
                      rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # initial + 2 retries

    def test_404_raises_actionable_window_error_without_retry(self):
        fake = FakeQcew()  # nothing registered → 404
        t = self._transport()
        with self.assertRaises(QcewApiError) as ctx:
            t.get_csv("/cew/data/api/2026/1/industry/622.csv", opener=fake,
                      sleep=lambda s: None)
        msg = str(ctx.exception)
        # The error must name the live-verified window and the BLS doc.
        self.assertIn("2014", msg)
        self.assertIn("2025", msg)
        self.assertIn("Q4", msg)
        self.assertIn("csv-data-slices", msg)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 404

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeQcew()
        fake.transients[0] = (403, {})
        t = self._transport()
        with self.assertRaises(QcewApiError):
            t.get_csv(_IND_PATH, opener=fake, sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)

    def test_transport_error_status_0_retries_then_succeeds(self):
        fake = FakeQcew().add(_IND_PATH, industry_622_csv())
        fake.transients[0] = (0, {})
        res = self._transport().get_csv(
            _IND_PATH, opener=fake, sleep=lambda s: None,
            now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 6)
        self.assertEqual(len(fake.calls), 2)

    def test_empty_body_raises_clear_error(self):
        fake = FakeQcew().add(_IND_PATH, "")
        t = self._transport()
        with self.assertRaises(QcewApiError) as ctx:
            t.get_csv(_IND_PATH, opener=fake, sleep=lambda s: None)
        self.assertIn("empty CSV", str(ctx.exception))

    def test_header_only_file_yields_zero_rows(self):
        header_only = industry_622_csv().splitlines()[0] + "\n"
        fake = FakeQcew().add(_IND_PATH, header_only)
        res = self._transport().get_csv(_IND_PATH, opener=fake)
        self.assertEqual(res.rows, [])
        self.assertFalse(res.truncated)

    def test_bom_is_stripped_from_first_header(self):
        fake = FakeQcew().add(_IND_PATH, "\ufeff" + industry_622_csv())
        res = self._transport().get_csv(_IND_PATH, opener=fake)
        self.assertEqual(res.fieldnames[0], "area_fips")


if __name__ == "__main__":
    unittest.main()
