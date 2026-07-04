import unittest

from ..transport import NppesApiError, NppesTransport
from .fakes import INDIVIDUAL, FakeNppes, make_records


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return NppesTransport(**kw)

    def test_build_url_is_deterministic_and_injects_version(self):
        t = self._transport()
        url = t.build_url("/", {"state": "MD", "limit": 200, "skip": 0})
        self.assertIn("version=2.1", url)
        self.assertEqual(
            url,
            "https://npiregistry.cms.hhs.gov/api/?limit=200&skip=0&state=MD&version=2.1")

    def test_200_parses_results(self):
        fake = FakeNppes(make_records(INDIVIDUAL, 1))
        t = self._transport()
        payload = t.get_json("/", {"limit": 1, "skip": 0}, opener=fake)
        self.assertEqual(payload["result_count"], 1)
        self.assertEqual(payload["results"][0]["enumeration_type"], "NPI-1")

    def test_empty_match_returns_zero_count(self):
        fake = FakeNppes([])  # no records
        t = self._transport()
        payload = t.get_json("/", {"limit": 1, "state": "ZZ"}, opener=fake)
        self.assertEqual(payload["results"], [])

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeNppes(make_records(INDIVIDUAL, 1))
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            "/", {"limit": 1}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(payload["result_count"], 1)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeNppes(make_records(INDIVIDUAL, 1))
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(NppesApiError):
            t.get_json("/", {"limit": 1}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeNppes([])
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(NppesApiError):
            t.get_json("/", {"limit": 1}, opener=fake, sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400


if __name__ == "__main__":
    unittest.main()
