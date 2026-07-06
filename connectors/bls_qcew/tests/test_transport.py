import io
import unittest
from http.client import IncompleteRead

from ..transport import QcewApiError, QcewTransport, RawResponse
from .fakes import FakeQcew, area_48453_csv, industry_622_csv


class _DroppingStream:
    """A body stream that delivers a prefix then raises IncompleteRead,
    like http.client does when a chunked connection drops mid-body."""

    def __init__(self, data: bytes, drop_after: int) -> None:
        self._buf = io.BytesIO(data[:drop_after])

    def read(self, n: int = -1) -> bytes:
        chunk = self._buf.read(n)
        if chunk:
            return chunk
        raise IncompleteRead(b"", None)

    def close(self) -> None:
        pass

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

    # \u2500\u2500 download-integrity regression tests \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    # A connection drop mid-body used to yield a truncated CSV that was
    # treated as complete; the transport now counts bytes against
    # Content-Length and retries IncompleteRead.

    def test_content_length_shortfall_retries_then_raises(self):
        body = industry_622_csv().encode("utf-8")
        calls = []

        def short_opener(url, headers, timeout):
            calls.append(url)
            # Deliver a truncated body while declaring the full length,
            # exactly what a mid-body connection drop looks like to
            # urllib (http.client returns the short read, no error).
            return RawResponse(
                status=200,
                headers={"content-length": str(len(body) + 57)},
                body=body[: len(body) // 2])

        t = self._transport(max_retries=2)
        with self.assertRaises(QcewApiError) as ctx:
            t.get_csv(_IND_PATH, opener=short_opener,
                      sleep=lambda s: None, now=lambda: 0.0,
                      rand=lambda: 0.0)
        self.assertIn("truncated body", str(ctx.exception))
        self.assertIn("Content-Length", str(ctx.exception))
        self.assertEqual(len(calls), 3)  # initial + 2 retries

    def test_content_length_shortfall_recovers_on_retry(self):
        body = industry_622_csv().encode("utf-8")
        calls = []

        def flaky_opener(url, headers, timeout):
            calls.append(url)
            if len(calls) == 1:
                return RawResponse(
                    status=200,
                    headers={"content-length": str(len(body))},
                    body=body[:40])
            return RawResponse(
                status=200,
                headers={"content-length": str(len(body))},
                body=body)

        res = self._transport().get_csv(
            _IND_PATH, opener=flaky_opener,
            sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 6)
        self.assertEqual(len(calls), 2)

    def test_incomplete_read_mid_stream_is_retried(self):
        body = industry_622_csv().encode("utf-8")
        calls = []

        def dropping_opener(url, headers, timeout):
            calls.append(url)
            if len(calls) == 1:
                return RawResponse(status=200,
                                   stream=_DroppingStream(body, 60))
            return RawResponse(status=200, body=body)

        res = self._transport().get_csv(
            _IND_PATH, opener=dropping_opener,
            sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 6)
        self.assertEqual(len(calls), 2)

    def test_incomplete_read_exhausts_into_transport_error(self):
        body = industry_622_csv().encode("utf-8")

        def always_dropping(url, headers, timeout):
            return RawResponse(status=200, stream=_DroppingStream(body, 60))

        t = self._transport(max_retries=1)
        with self.assertRaises(QcewApiError) as ctx:
            t.get_csv(_IND_PATH, opener=always_dropping,
                      sleep=lambda s: None, now=lambda: 0.0,
                      rand=lambda: 0.0)
        self.assertIn("IncompleteRead", str(ctx.exception))

    def test_max_rows_capped_fetch_skips_content_length_check(self):
        # A capped parse stops mid-stream by design \u2014 it must not be
        # failed for not consuming the whole declared body.
        body = industry_622_csv().encode("utf-8")

        def opener(url, headers, timeout):
            return RawResponse(
                status=200,
                headers={"content-length": str(len(body) + 999)},
                body=body)

        res = self._transport().get_csv(_IND_PATH, max_rows=2,
                                        opener=opener, sleep=lambda s: None)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)

    # \u2500\u2500 Retry-After clamp regression tests \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    # time.sleep(-5) raises ValueError and used to abort the retry loop.

    def test_negative_retry_after_is_clamped_to_zero(self):
        fake = FakeQcew().add(_IND_PATH, industry_622_csv())
        fake.transients[0] = (429, {"retry-after": "-5"})
        sleeps = []
        res = self._transport().get_csv(
            _IND_PATH, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 6)          # retried and succeeded
        self.assertTrue(all(s >= 0 for s in sleeps))
        self.assertIn(0.0, sleeps)                  # clamped, not -5

    def test_garbage_retry_after_falls_back_to_backoff(self):
        fake = FakeQcew().add(_IND_PATH, industry_622_csv())
        fake.transients[0] = (429, {"retry-after": "soon"})
        sleeps = []
        res = self._transport(backoff_base_s=2.0).get_csv(
            _IND_PATH, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.5)
        self.assertEqual(len(res.rows), 6)
        self.assertTrue(all(s >= 0 for s in sleeps))
        self.assertIn(1.0, sleeps)  # backoff schedule: 2.0 * 2^0 * 0.5

    def test_oversized_retry_after_is_capped(self):
        fake = FakeQcew().add(_IND_PATH, industry_622_csv())
        fake.transients[0] = (429, {"retry-after": "9999"})
        sleeps = []
        t = self._transport(backoff_cap_s=60.0)
        res = t.get_csv(_IND_PATH, opener=fake,
                        sleep=sleeps.append, now=lambda: 0.0,
                        rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 6)
        self.assertIn(60.0, sleeps)
        self.assertTrue(all(s <= 60.0 for s in sleeps))


if __name__ == "__main__":
    unittest.main()
