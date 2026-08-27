import unittest

from ..transport import QppApiError, QppTransport, RawResponse
from .fakes import FakeQpp

_BENCH = "/submissions/public/benchmarks"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return QppTransport(**kw)

    def test_build_url_is_deterministic_and_sorts_params(self):
        t = self._transport()
        url = t.build_url(_BENCH, {"year": "2025"})
        self.assertEqual(
            url, "https://qpp.cms.gov/api/submissions/public/benchmarks"
                 "?year=2025")

    def test_200_parses_top_level_object(self):
        fake = FakeQpp().add_benchmarks("2025", [{"measureId": "001"}])
        t = self._transport()
        doc = t.get_json(_BENCH, {"year": "2025"}, opener=fake)
        self.assertIsInstance(doc, dict)
        self.assertEqual(doc["data"]["benchmarks"][0]["measureId"], "001")

    def test_top_level_array_is_rejected(self):
        class ArrayOpener:
            def __call__(self, url, headers, timeout):
                return RawResponse(status=200, body=b'[1, 2, 3]')
        t = self._transport()
        with self.assertRaises(QppApiError):
            t.get_json(_BENCH, {"year": "2025"}, opener=ArrayOpener())

    def test_404_returns_empty_dict(self):
        fake = FakeQpp()  # no clinicians registered → 404
        t = self._transport()
        doc = t.get_json("/eligibility/npis/1234567893", {"year": "2025"},
                         opener=fake)
        self.assertEqual(doc, {})

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeQpp().add_benchmarks("2025", [{"measureId": "001"}])
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        doc = t.get_json(_BENCH, {"year": "2025"}, opener=fake,
                         sleep=sleeps.append, now=lambda: 0.0,
                         rand=lambda: 0.0)
        self.assertEqual(doc["data"]["benchmarks"][0]["measureId"], "001")
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeQpp().add_benchmarks("2025", [])
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(QppApiError):
            t.get_json(_BENCH, {"year": "2025"}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0,
                       rand=lambda: 0.0)

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeQpp()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(QppApiError):
            t.get_json(_BENCH, {"year": "bad"}, opener=fake,
                       sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400


if __name__ == "__main__":
    unittest.main()
