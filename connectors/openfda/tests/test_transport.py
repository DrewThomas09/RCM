import unittest

from ..transport import OpenFdaTransport, OpenFdaApiError, RawResponse
from .fakes import FakeFda


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return OpenFdaTransport(**kw)

    def test_build_url_is_deterministic_and_injects_key(self):
        t = self._transport(api_key="SECRET")
        url = t.build_url("/drug/ndc.json", {"limit": 5, "skip": 0})
        # sorted params + api_key merged
        self.assertIn("api_key=SECRET", url)
        self.assertEqual(
            url, "https://api.fda.gov/drug/ndc.json?api_key=SECRET&limit=5&skip=0")

    def test_404_not_found_returns_empty_results(self):
        fake = FakeFda()  # no records → 404
        t = self._transport()
        payload = t.get_json("/drug/ndc.json", {"limit": 1}, opener=fake)
        self.assertEqual(payload["results"], [])

    def test_200_parses_results(self):
        fake = FakeFda().add("/drug/ndc.json", [{"product_ndc": "0002-1200"}])
        t = self._transport()
        payload = t.get_json("/drug/ndc.json", {"limit": 1}, opener=fake)
        self.assertEqual(payload["results"][0]["product_ndc"], "0002-1200")

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeFda().add("/drug/ndc.json", [{"product_ndc": "x"}])
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            "/drug/ndc.json", {"limit": 1}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(payload["results"][0]["product_ndc"], "x")
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeFda().add("/drug/ndc.json", [{"a": 1}])
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(OpenFdaApiError):
            t.get_json("/drug/ndc.json", {"limit": 1}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeFda()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(OpenFdaApiError):
            t.get_json("/drug/ndc.json", {"limit": 1}, opener=fake,
                       sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400


if __name__ == "__main__":
    unittest.main()
