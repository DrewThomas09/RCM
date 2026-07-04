import unittest

from ..transport import CmsCoverageApiError, CmsCoverageTransport
from .fakes import FakeCmsCoverage

_NCD_PATH = "/v1/reports/national-coverage-ncd"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return CmsCoverageTransport(**kw)

    def test_build_url_is_deterministic_and_injects_key(self):
        t = self._transport(api_key="SECRET")
        url = t.build_url(_NCD_PATH, {"limit": 5, "page_token": "abc"})
        self.assertIn("api_key=SECRET", url)
        self.assertEqual(
            url,
            "https://api.coverage.cms.gov/v1/reports/national-coverage-ncd"
            "?api_key=SECRET&limit=5&page_token=abc")

    def test_200_parses_result_items(self):
        fake = FakeCmsCoverage().add(_NCD_PATH, [{"document_id": 169}])
        t = self._transport()
        payload = t.get_json(_NCD_PATH, {"limit": 10}, opener=fake)
        self.assertEqual(payload["result"]["items"][0]["document_id"], 169)

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeCmsCoverage().add(_NCD_PATH, [{"document_id": 1}])
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            _NCD_PATH, {"limit": 10}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(payload["result"]["items"][0]["document_id"], 1)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeCmsCoverage().add(_NCD_PATH, [{"document_id": 1}])
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(CmsCoverageApiError):
            t.get_json(_NCD_PATH, {"limit": 10}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)

    def test_404_returns_empty_result(self):
        fake = FakeCmsCoverage()
        fake.transients[0] = (404, {})
        t = self._transport()
        payload = t.get_json(_NCD_PATH, {"limit": 10}, opener=fake,
                             sleep=lambda s: None)
        self.assertEqual(payload["result"]["items"], [])
        self.assertEqual(payload["result"]["total"], 0)

    def test_empty_items_handled(self):
        # An endpoint with no records returns a well-formed empty envelope.
        fake = FakeCmsCoverage().add(_NCD_PATH, [])
        t = self._transport()
        payload = t.get_json(_NCD_PATH, {"limit": 10}, opener=fake)
        self.assertEqual(payload["result"]["items"], [])
        self.assertIsNone(payload["result"]["next_page_token"])

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeCmsCoverage()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(CmsCoverageApiError):
            t.get_json(_NCD_PATH, {"limit": 10}, opener=fake, sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400


if __name__ == "__main__":
    unittest.main()
