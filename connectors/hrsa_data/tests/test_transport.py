import io
import unittest
from http.client import IncompleteRead

from ..transport import HrsaApiError, HrsaTransport, RawResponse
from .fakes import FakeHrsa, hpsa_pc_csv, mua_csv


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

    # ── download-integrity regression tests ───────────────────────────
    # A connection drop mid-body used to yield a truncated CSV that was
    # treated as complete; the transport now counts bytes against
    # Content-Length and retries IncompleteRead.

    def test_content_length_shortfall_retries_then_raises(self):
        body = hpsa_pc_csv().encode("utf-8")
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
        with self.assertRaises(HrsaApiError) as ctx:
            t.get_csv(_PC_PATH, opener=short_opener,
                      sleep=lambda s: None, now=lambda: 0.0,
                      rand=lambda: 0.0)
        self.assertIn("truncated body", str(ctx.exception))
        self.assertIn("Content-Length", str(ctx.exception))
        self.assertEqual(len(calls), 3)  # initial + 2 retries

    def test_content_length_shortfall_recovers_on_retry(self):
        body = hpsa_pc_csv().encode("utf-8")
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
            _PC_PATH, opener=flaky_opener,
            sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 3)
        self.assertEqual(len(calls), 2)

    def test_incomplete_read_mid_stream_is_retried(self):
        body = hpsa_pc_csv().encode("utf-8")
        calls = []

        def dropping_opener(url, headers, timeout):
            calls.append(url)
            if len(calls) == 1:
                return RawResponse(status=200,
                                   stream=_DroppingStream(body, 60))
            return RawResponse(status=200, body=body)

        res = self._transport().get_csv(
            _PC_PATH, opener=dropping_opener,
            sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 3)
        self.assertEqual(len(calls), 2)

    def test_incomplete_read_exhausts_into_transport_error(self):
        body = hpsa_pc_csv().encode("utf-8")

        def always_dropping(url, headers, timeout):
            return RawResponse(status=200, stream=_DroppingStream(body, 60))

        t = self._transport(max_retries=1)
        with self.assertRaises(HrsaApiError) as ctx:
            t.get_csv(_PC_PATH, opener=always_dropping,
                      sleep=lambda s: None, now=lambda: 0.0,
                      rand=lambda: 0.0)
        self.assertIn("IncompleteRead", str(ctx.exception))

    def test_max_rows_capped_fetch_skips_content_length_check(self):
        # A capped parse stops mid-stream by design — it must not be
        # failed for not consuming the whole declared body.
        body = hpsa_pc_csv().encode("utf-8")

        def opener(url, headers, timeout):
            return RawResponse(
                status=200,
                headers={"content-length": str(len(body) + 999)},
                body=body)

        res = self._transport().get_csv(_PC_PATH, max_rows=2,
                                        opener=opener, sleep=lambda s: None)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)

    # ── Retry-After clamp regression tests ────────────────────────────
    # time.sleep(-5) raises ValueError and used to abort the retry loop.

    def test_negative_retry_after_is_clamped_to_zero(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        fake.transients[0] = (429, {"retry-after": "-5"})
        sleeps = []
        res = self._transport().get_csv(
            _PC_PATH, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 3)          # retried and succeeded
        self.assertTrue(all(s >= 0 for s in sleeps))
        self.assertIn(0.0, sleeps)                  # clamped, not -5

    def test_garbage_retry_after_falls_back_to_backoff(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        fake.transients[0] = (429, {"retry-after": "soon"})
        sleeps = []
        res = self._transport(backoff_base_s=2.0).get_csv(
            _PC_PATH, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.5)
        self.assertEqual(len(res.rows), 3)
        self.assertTrue(all(s >= 0 for s in sleeps))
        self.assertIn(1.0, sleeps)  # backoff schedule: 2.0 * 2^0 * 0.5

    def test_oversized_retry_after_is_capped(self):
        fake = FakeHrsa().add(_PC_PATH, hpsa_pc_csv())
        fake.transients[0] = (429, {"retry-after": "9999"})
        sleeps = []
        t = self._transport(backoff_cap_s=60.0)
        res = t.get_csv(_PC_PATH, opener=fake,
                        sleep=sleeps.append, now=lambda: 0.0,
                        rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 3)
        self.assertIn(60.0, sleeps)
        self.assertTrue(all(s <= 60.0 for s in sleeps))


if __name__ == "__main__":
    unittest.main()
