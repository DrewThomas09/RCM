import unittest

from ..transport import ProviderDataApiError, ProviderDataTransport
from .fakes import CATALOG_PATH, FakeProviderData, hospital_rows

_HOSPITAL_PATH = "/api/1/datastore/query/xubh-q36u/0"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return ProviderDataTransport(**kw)

    def test_build_url_is_deterministic(self):
        t = self._transport()
        url = t.build_url(_HOSPITAL_PATH, {"offset": 0, "limit": 5})
        self.assertEqual(
            url,
            "https://data.cms.gov/provider-data/api/1/datastore/query/"
            "xubh-q36u/0?limit=5&offset=0")

    def test_200_parses_datastore_envelope(self):
        fake = FakeProviderData().add("xubh-q36u", hospital_rows(2))
        t = self._transport()
        payload = t.get_json(_HOSPITAL_PATH, {"limit": 10, "offset": 0},
                             opener=fake)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["results"][0]["facility_id"], "010000")

    def test_200_parses_catalog_array(self):
        # The metastore catalog is a bare JSON array, not a dict envelope.
        fake = FakeProviderData().add_catalog([{"identifier": "abcd-1234"}])
        t = self._transport()
        payload = t.get_json(CATALOG_PATH, opener=fake)
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["identifier"], "abcd-1234")

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeProviderData().add("xubh-q36u", hospital_rows(1))
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            _HOSPITAL_PATH, {"limit": 10, "offset": 0}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(payload["results"][0]["facility_id"], "010000")
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeProviderData().add("xubh-q36u", hospital_rows(1))
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(ProviderDataApiError):
            t.get_json(_HOSPITAL_PATH, {"limit": 10, "offset": 0}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)

    def test_transport_error_status_0_retries_then_raises(self):
        fake = FakeProviderData()
        for i in range(10):
            fake.transients[i] = (0, {})
        t = self._transport(max_retries=1)
        with self.assertRaises(ProviderDataApiError):
            t.get_json(_HOSPITAL_PATH, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 2)   # initial try + one retry

    def test_404_returns_empty_results(self):
        # Unknown identifier → empty envelope, not an exception, so a
        # speculative fetch on a stale catalog id degrades gracefully.
        fake = FakeProviderData()
        t = self._transport()
        payload = t.get_json("/api/1/datastore/query/zzzz-zzzz/0",
                             {"limit": 10, "offset": 0}, opener=fake,
                             sleep=lambda s: None)
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["count"], 0)

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeProviderData()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(ProviderDataApiError):
            t.get_json(_HOSPITAL_PATH, {"limit": 9999, "offset": 0},
                       opener=fake, sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400


if __name__ == "__main__":
    unittest.main()
