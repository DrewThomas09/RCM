import unittest

from ..transport import HealthdataGovApiError, HealthdataSodaTransport
from .fakes import FakeHealthdataGov, hhs_ids_rows

_RESOURCE_PATH = "/resource/vz64-k9wr.json"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return HealthdataSodaTransport(**kw)

    def test_build_url_is_deterministic_and_encodes_soql(self):
        t = self._transport()
        url = t.build_url(_RESOURCE_PATH, {
            "$limit": 5, "$offset": 10, "$where": "state='CA' AND ccn='010039'"})
        # Sorted params; $ percent-encoded; where clause fully escaped.
        self.assertEqual(
            url,
            "https://healthdata.gov/resource/vz64-k9wr.json"
            "?%24limit=5&%24offset=10"
            "&%24where=state%3D%27CA%27+AND+ccn%3D%27010039%27")

    def test_app_token_header_only_when_configured(self):
        fake = FakeHealthdataGov().add(_RESOURCE_PATH, hhs_ids_rows())
        t = self._transport(app_token="SECRET")
        t.get_json(_RESOURCE_PATH, {"$limit": 1}, opener=fake)
        self.assertEqual(fake.headers_seen[0].get("X-App-Token"), "SECRET")

        fake2 = FakeHealthdataGov().add(_RESOURCE_PATH, hhs_ids_rows())
        t2 = self._transport()  # no token → header absent (bad tokens 403 live)
        t2.get_json(_RESOURCE_PATH, {"$limit": 1}, opener=fake2)
        self.assertNotIn("X-App-Token", fake2.headers_seen[0])

    def test_200_parses_json_array(self):
        fake = FakeHealthdataGov().add(_RESOURCE_PATH, hhs_ids_rows())
        t = self._transport()
        payload = t.get_json(_RESOURCE_PATH, {"$limit": 10}, opener=fake)
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["hhs_id"], "C010039-C")

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeHealthdataGov().add(_RESOURCE_PATH, hhs_ids_rows())
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            _RESOURCE_PATH, {"$limit": 10}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(payload), 3)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_429_negative_or_garbage_retry_after_still_retries(self):
        # Buggy/hostile servers send negative, non-finite, or HTTP-date
        # Retry-After values. None may reach time.sleep() unclamped —
        # sleep(-5) raises ValueError and would abort the retry loop.
        fake = FakeHealthdataGov().add(_RESOURCE_PATH, hhs_ids_rows())
        fake.transients[0] = (429, {"retry-after": "-5"})
        fake.transients[1] = (429, {"retry-after": "nan"})
        fake.transients[2] = (429, {"retry-after": "Wed, 21 Oct 2026 07:28:00 GMT"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            _RESOURCE_PATH, {"$limit": 10}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.25)
        self.assertEqual(len(payload), 3)
        self.assertEqual(len(fake.calls), 4)  # three 429s, then success
        # Negative clamps to 0.0; nan / HTTP-date fall back to the jittered
        # backoff schedule (ceilings 2s, 4s at rand()=0.25 → 0.5s, 1.0s).
        self.assertEqual(sleeps, [0.0, 0.5, 1.0])

    def test_5xx_exhausts_and_raises(self):
        fake = FakeHealthdataGov().add(_RESOURCE_PATH, hhs_ids_rows())
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(HealthdataGovApiError):
            t.get_json(_RESOURCE_PATH, {"$limit": 10}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # initial try + 2 retries

    def test_transport_error_status_0_retries(self):
        fake = FakeHealthdataGov().add(_RESOURCE_PATH, hhs_ids_rows())
        fake.transients[0] = (0, {})   # URLError folded to status 0
        t = self._transport()
        payload = t.get_json(_RESOURCE_PATH, {"$limit": 10}, opener=fake,
                             sleep=lambda s: None, now=lambda: 0.0,
                             rand=lambda: 0.0)
        self.assertEqual(len(payload), 3)

    def test_404_returns_empty_list(self):
        fake = FakeHealthdataGov()  # nothing registered → 404 for any path
        t = self._transport()
        payload = t.get_json("/resource/nope-nope.json", {"$limit": 1},
                             opener=fake, sleep=lambda s: None)
        self.assertEqual(payload, [])

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeHealthdataGov()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(HealthdataGovApiError):
            t.get_json(_RESOURCE_PATH, {"$limit": 1}, opener=fake,
                       sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400

    def test_non_json_body_raises_clear_error(self):
        class HtmlOpener:
            def __call__(self, url, headers, timeout):
                from ..transport import RawResponse
                return RawResponse(status=200, body=b"<html>oops</html>")
        t = self._transport()
        with self.assertRaises(HealthdataGovApiError) as ctx:
            t.get_json(_RESOURCE_PATH, opener=HtmlOpener())
        self.assertIn("non-JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
