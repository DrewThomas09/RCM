import io
import unittest
from http.client import IncompleteRead

from ..transport import OigLeieApiError, OigLeieTransport, RawResponse
from .fakes import (FakeOig, SUPPL_2605_EXCL, UPDATED_PATH, supplement_excl_csv,
                    updated_csv)


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


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return OigLeieTransport(**kw)

    def test_build_url_is_deterministic(self):
        t = self._transport()
        self.assertEqual(
            t.build_url(UPDATED_PATH),
            "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv")
        self.assertEqual(
            t.build_url(SUPPL_2605_EXCL),
            "https://oig.hhs.gov/exclusions/downloadables/2026/2605excl.csv")

    def test_200_parses_rows_with_raw_headers_and_values(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(len(res.rows), 4)
        self.assertFalse(res.truncated)
        self.assertEqual(len(res.fieldnames), 18)
        self.assertEqual(res.fieldnames[0], "LASTNAME")
        self.assertEqual(res.fieldnames[-1], "WVRSTATE")
        # Raw values survive verbatim — sentinel cleanup is normalize's job.
        self.assertEqual(res.rows[0]["NPI"], "0000000000")
        self.assertEqual(res.rows[0]["REINDATE"], "00000000")

    def test_quoted_comma_busname_survives(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(res.rows[0]["BUSNAME"], "#1 MARKETING SERVICE, INC")

    def test_bom_is_stripped_from_first_header(self):
        fake = FakeOig().add(UPDATED_PATH, "\ufeff" + updated_csv())
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(res.fieldnames[0], "LASTNAME")

    def test_short_row_is_padded_to_header_shape(self):
        body = updated_csv().splitlines()[0] + "\r\nDOE,JANE\r\n"
        fake = FakeOig().add(UPDATED_PATH, body)
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(res.rows[0]["LASTNAME"], "DOE")
        self.assertEqual(res.rows[0]["WVRSTATE"], "")   # padded, stable shape

    def test_max_rows_caps_and_flags_truncation(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        res = self._transport().get_csv(UPDATED_PATH, max_rows=2, opener=fake)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)
        # Exactly at the row count → not truncated.
        res2 = self._transport().get_csv(UPDATED_PATH, max_rows=4, opener=fake)
        self.assertEqual(len(res2.rows), 4)
        self.assertFalse(res2.truncated)

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        res = self._transport().get_csv(
            UPDATED_PATH, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 4)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(OigLeieApiError):
            t.get_csv(UPDATED_PATH, opener=fake,
                      sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # initial + 2 retries

    def test_transport_error_status_0_retries(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        fake.transients[0] = (0, {})
        res = self._transport().get_csv(
            UPDATED_PATH, opener=fake,
            sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 4)
        self.assertEqual(len(fake.calls), 2)

    def test_404_raises_immediately_with_status_and_index_pointer(self):
        fake = FakeOig()  # nothing registered → 404
        t = self._transport()
        with self.assertRaises(OigLeieApiError) as ctx:
            t.get_csv("/exclusions/downloadables/2026/2606excl.csv",
                      opener=fake, sleep=lambda s: None)
        self.assertEqual(ctx.exception.status, 404)
        self.assertIn("exclusions_list.asp", str(ctx.exception))
        self.assertEqual(len(fake.calls), 1)  # no retry on a 404

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeOig()
        fake.transients[0] = (403, {})
        t = self._transport()
        with self.assertRaises(OigLeieApiError) as ctx:
            t.get_csv(UPDATED_PATH, opener=fake, sleep=lambda s: None)
        self.assertEqual(ctx.exception.status, 403)
        self.assertEqual(len(fake.calls), 1)

    def test_empty_body_raises_clear_error(self):
        fake = FakeOig().add(UPDATED_PATH, "")
        with self.assertRaises(OigLeieApiError) as ctx:
            self._transport().get_csv(UPDATED_PATH, opener=fake,
                                      sleep=lambda s: None)
        self.assertIn("empty CSV", str(ctx.exception))

    def test_header_only_file_yields_zero_rows(self):
        header_only = updated_csv().splitlines()[0] + "\r\n"
        fake = FakeOig().add(UPDATED_PATH, header_only)
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(res.rows, [])
        self.assertFalse(res.truncated)

    def test_supplement_file_parses_same_shape(self):
        fake = FakeOig().add(SUPPL_2605_EXCL, supplement_excl_csv())
        res = self._transport().get_csv(SUPPL_2605_EXCL, opener=fake)
        self.assertEqual(len(res.rows), 2)
        self.assertEqual(len(res.fieldnames), 18)

    # ── download-integrity regression tests ───────────────────────────
    # A connection drop mid-body used to yield a truncated CSV that was
    # treated as complete; the transport now counts bytes against
    # Content-Length and retries IncompleteRead.

    def test_content_length_shortfall_retries_then_raises(self):
        body = updated_csv().encode("utf-8")
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
        with self.assertRaises(OigLeieApiError) as ctx:
            t.get_csv(UPDATED_PATH, opener=short_opener,
                      sleep=lambda s: None, now=lambda: 0.0,
                      rand=lambda: 0.0)
        self.assertIn("truncated body", str(ctx.exception))
        self.assertIn("Content-Length", str(ctx.exception))
        self.assertEqual(len(calls), 3)  # initial + 2 retries

    def test_content_length_shortfall_recovers_on_retry(self):
        body = updated_csv().encode("utf-8")
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
            UPDATED_PATH, opener=flaky_opener,
            sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 4)
        self.assertEqual(len(calls), 2)

    def test_incomplete_read_mid_stream_is_retried(self):
        body = updated_csv().encode("utf-8")
        calls = []

        def dropping_opener(url, headers, timeout):
            calls.append(url)
            if len(calls) == 1:
                return RawResponse(status=200,
                                   stream=_DroppingStream(body, 60))
            return RawResponse(status=200, body=body)

        res = self._transport().get_csv(
            UPDATED_PATH, opener=dropping_opener,
            sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 4)
        self.assertEqual(len(calls), 2)

    def test_incomplete_read_exhausts_into_transport_error(self):
        body = updated_csv().encode("utf-8")

        def always_dropping(url, headers, timeout):
            return RawResponse(status=200, stream=_DroppingStream(body, 60))

        t = self._transport(max_retries=1)
        with self.assertRaises(OigLeieApiError) as ctx:
            t.get_csv(UPDATED_PATH, opener=always_dropping,
                      sleep=lambda s: None, now=lambda: 0.0,
                      rand=lambda: 0.0)
        self.assertIn("IncompleteRead", str(ctx.exception))

    def test_max_rows_capped_fetch_skips_content_length_check(self):
        # A capped parse stops mid-stream by design — it must not be
        # failed for not consuming the whole declared body.
        body = updated_csv().encode("utf-8")

        def opener(url, headers, timeout):
            return RawResponse(
                status=200,
                headers={"content-length": str(len(body) + 999)},
                body=body)

        res = self._transport().get_csv(UPDATED_PATH, max_rows=2,
                                        opener=opener, sleep=lambda s: None)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)

    # ── Retry-After clamp regression tests ────────────────────────────
    # time.sleep(-5) raises ValueError and used to abort the retry loop.

    def test_negative_retry_after_is_clamped_to_zero(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        fake.transients[0] = (429, {"retry-after": "-5"})
        sleeps = []
        res = self._transport().get_csv(
            UPDATED_PATH, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 4)          # retried and succeeded
        self.assertTrue(all(s >= 0 for s in sleeps))
        self.assertIn(0.0, sleeps)                  # clamped, not -5

    def test_garbage_retry_after_falls_back_to_backoff(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        fake.transients[0] = (429, {"retry-after": "soon"})
        sleeps = []
        res = self._transport(backoff_base_s=2.0).get_csv(
            UPDATED_PATH, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.5)
        self.assertEqual(len(res.rows), 4)
        self.assertTrue(all(s >= 0 for s in sleeps))
        self.assertIn(1.0, sleeps)  # backoff schedule: 2.0 * 2^0 * 0.5

    def test_oversized_retry_after_is_capped(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        fake.transients[0] = (429, {"retry-after": "9999"})
        sleeps = []
        t = self._transport(backoff_cap_s=60.0)
        res = t.get_csv(UPDATED_PATH, opener=fake,
                        sleep=sleeps.append, now=lambda: 0.0,
                        rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 4)
        self.assertIn(60.0, sleeps)
        self.assertTrue(all(s <= 60.0 for s in sleeps))


if __name__ == "__main__":
    unittest.main()
