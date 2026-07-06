import unittest

from ..transport import CmsOpenDataApiError, CmsOpenDataTransport
from .fakes import CAT_PHYS_UUID, FakeCmsOpenData, phys_rows

_DATA_PATH = f"/data-api/v1/dataset/{CAT_PHYS_UUID}/data"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return CmsOpenDataTransport(**kw)

    def test_build_url_is_deterministic_and_encodes_filters(self):
        t = self._transport()
        url = t.build_url(_DATA_PATH, {"size": 2, "offset": 4,
                                       "filter[HCPCS_Cd]": "J9271"})
        self.assertEqual(
            url,
            f"https://data.cms.gov{_DATA_PATH}"
            "?filter%5BHCPCS_Cd%5D=J9271&offset=4&size=2")

    def test_200_parses_bare_array(self):
        fake = FakeCmsOpenData().add_dataset(CAT_PHYS_UUID, phys_rows(2))
        t = self._transport()
        payload = t.get_json(_DATA_PATH, {"size": 10}, opener=fake)
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["Rndrng_NPI"], "1003000126")

    def test_200_parses_catalog_dict(self):
        fake = FakeCmsOpenData()
        t = self._transport()
        payload = t.get_json("/data.json", opener=fake)
        self.assertIsInstance(payload, dict)
        self.assertEqual(len(payload["dataset"]), 3)

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeCmsOpenData().add_dataset(CAT_PHYS_UUID, phys_rows(1))
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(_DATA_PATH, {"size": 10}, opener=fake,
                             sleep=sleeps.append, now=lambda: 0.0,
                             rand=lambda: 0.0)
        self.assertEqual(payload[0]["Rndrng_NPI"], "1003000126")
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_429_negative_or_garbage_retry_after_still_retries(self):
        # Buggy/hostile servers send negative, non-finite, or HTTP-date
        # Retry-After values. None may reach time.sleep() unclamped —
        # sleep(-5) raises ValueError and would abort the retry loop.
        fake = FakeCmsOpenData().add_dataset(CAT_PHYS_UUID, phys_rows(1))
        fake.transients[0] = (429, {"retry-after": "-5"})
        fake.transients[1] = (429, {"retry-after": "nan"})
        fake.transients[2] = (429, {"retry-after": "Wed, 21 Oct 2026 07:28:00 GMT"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(_DATA_PATH, {"size": 10}, opener=fake,
                             sleep=sleeps.append, now=lambda: 0.0,
                             rand=lambda: 0.25)
        self.assertEqual(payload[0]["Rndrng_NPI"], "1003000126")
        self.assertEqual(len(fake.calls), 4)  # three 429s, then success
        # Negative clamps to 0.0; nan / HTTP-date fall back to the jittered
        # backoff schedule (ceilings 2s, 4s at rand()=0.25 → 0.5s, 1.0s).
        self.assertEqual(sleeps, [0.0, 0.5, 1.0])

    def test_5xx_exhausts_and_raises(self):
        fake = FakeCmsOpenData().add_dataset(CAT_PHYS_UUID, phys_rows(1))
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(CmsOpenDataApiError):
            t.get_json(_DATA_PATH, {"size": 10}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # initial try + 2 retries

    def test_transport_error_status_0_is_retried(self):
        fake = FakeCmsOpenData().add_dataset(CAT_PHYS_UUID, phys_rows(1))
        fake.transients[0] = (0, {})          # URLError folded to status 0
        t = self._transport()
        payload = t.get_json(_DATA_PATH, {"size": 10}, opener=fake,
                             sleep=lambda s: None, now=lambda: 0.0,
                             rand=lambda: 0.0)
        self.assertEqual(len(payload), 1)

    def test_404_returns_empty_list(self):
        # A rotated dataset version UUID 404s — that is "no rows", not a
        # failure, so a stale pin degrades instead of crashing ingest.
        fake = FakeCmsOpenData()   # no datasets registered at all
        t = self._transport()
        payload = t.get_json(_DATA_PATH, {"size": 10}, opener=fake,
                             sleep=lambda s: None)
        self.assertEqual(payload, [])
        self.assertEqual(len(fake.calls), 1)   # no retry on a 404

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeCmsOpenData()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(CmsOpenDataApiError):
            t.get_json(_DATA_PATH, {"size": 10}, opener=fake, sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400

    def test_non_json_body_raises_clear_error(self):
        def opener(url, headers, timeout):
            from ..transport import RawResponse
            return RawResponse(status=200, body=b"<html>maintenance</html>")
        t = self._transport()
        with self.assertRaises(CmsOpenDataApiError) as ctx:
            t.get_json(_DATA_PATH, opener=opener, sleep=lambda s: None)
        self.assertIn("non-JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
