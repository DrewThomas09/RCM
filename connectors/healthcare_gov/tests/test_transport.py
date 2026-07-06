import unittest

from ..endpoints import CATALOG_PATH, datastore_path
from ..transport import HealthcareGovApiError, HealthcareGovTransport
from .fakes import CATALOG_ITEMS, FakeHealthcareGov, RATES_ROWS

_RATES_ID = "477ffb11-db39-44ae-9f96-40d9db2ba79f"
_RATES_PATH = datastore_path(_RATES_ID)


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return HealthcareGovTransport(**kw)

    def test_build_url_is_deterministic(self):
        t = self._transport()
        url = t.build_url(_RATES_PATH, {"offset": 500, "limit": 500,
                                        "rowIds": "true"})
        self.assertEqual(
            url,
            "https://data.healthcare.gov/api/1/datastore/query/"
            f"{_RATES_ID}/0?limit=500&offset=500&rowIds=true")

    def test_200_parses_datastore_envelope(self):
        fake = FakeHealthcareGov().add_datastore(_RATES_ID, RATES_ROWS)
        t = self._transport()
        payload = t.get_json(_RATES_PATH, {"limit": 10, "offset": 0},
                             opener=fake)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(payload["results"][0]["planid"], "21989AK0030001")

    def test_200_parses_catalog_list(self):
        # The metastore endpoint returns a bare JSON list, not a dict.
        fake = FakeHealthcareGov().add_catalog(CATALOG_ITEMS)
        t = self._transport()
        payload = t.get_json(CATALOG_PATH, opener=fake)
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["identifier"],
                         "ca253298-c4ef-4a77-9c44-0de0bbe91941")

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeHealthcareGov().add_datastore(_RATES_ID, RATES_ROWS)
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            _RATES_PATH, {"limit": 10}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(payload["count"], 2)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_429_negative_or_garbage_retry_after_still_retries(self):
        # Buggy/hostile servers send negative, non-finite, or HTTP-date
        # Retry-After values. None may reach time.sleep() unclamped —
        # sleep(-5) raises ValueError and would abort the retry loop.
        fake = FakeHealthcareGov().add_datastore(_RATES_ID, RATES_ROWS)
        fake.transients[0] = (429, {"retry-after": "-5"})
        fake.transients[1] = (429, {"retry-after": "nan"})
        fake.transients[2] = (429, {"retry-after": "Wed, 21 Oct 2026 07:28:00 GMT"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            _RATES_PATH, {"limit": 10}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.25)
        self.assertEqual(payload["count"], 2)
        self.assertEqual(len(fake.calls), 4)  # three 429s, then success
        # Negative clamps to 0.0; nan / HTTP-date fall back to the jittered
        # backoff schedule (ceilings 2s, 4s at rand()=0.25 → 0.5s, 1.0s).
        self.assertEqual(sleeps, [0.0, 0.5, 1.0])

    def test_5xx_exhausts_and_raises(self):
        fake = FakeHealthcareGov().add_datastore(_RATES_ID, RATES_ROWS)
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(HealthcareGovApiError):
            t.get_json(_RATES_PATH, {"limit": 10}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0,
                       rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # 1 try + 2 retries

    def test_transport_level_failure_retries_then_raises(self):
        fake = FakeHealthcareGov()
        for i in range(10):
            fake.transients[i] = (0, {}, b"connection refused")
        t = self._transport(max_retries=1)
        with self.assertRaises(HealthcareGovApiError):
            t.get_json(_RATES_PATH, opener=fake, sleep=lambda s: None,
                       now=lambda: 0.0, rand=lambda: 0.0)

    def test_404_returns_empty_envelope(self):
        fake = FakeHealthcareGov()
        fake.transients[0] = (404, {})
        t = self._transport()
        payload = t.get_json(_RATES_PATH, {"limit": 10}, opener=fake,
                             sleep=lambda s: None)
        self.assertEqual(payload, {"count": 0, "results": []})

    def test_hard_400_raises_without_retry_and_carries_body(self):
        # Live shape for a dataset never imported into the datastore.
        fake = FakeHealthcareGov()   # unknown id → scripted 400 body
        t = self._transport()
        with self.assertRaises(HealthcareGovApiError) as ctx:
            t.get_json(datastore_path("zip-only-dataset"), {"limit": 5},
                       opener=fake, sleep=lambda s: None)
        self.assertIn("No datastore storage found", str(ctx.exception))
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400

    def test_non_json_body_raises(self):
        fake = FakeHealthcareGov()
        fake.transients[0] = (200, {}, b"<html>maintenance</html>")
        t = self._transport()
        with self.assertRaises(HealthcareGovApiError):
            t.get_json(_RATES_PATH, opener=fake, sleep=lambda s: None)


if __name__ == "__main__":
    unittest.main()
