import unittest

from ..transport import CdcDataApiError, CdcSodaTransport
from .fakes import FakeCdcData, leading_causes_rows

_RESOURCE_PATH = "/resource/bi63-dtpu.json"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return CdcSodaTransport(**kw)

    def test_build_url_is_deterministic_and_encodes_soql(self):
        t = self._transport()
        url = t.build_url(_RESOURCE_PATH, {
            "$limit": 5, "$offset": 10, "$where": "state='CA' AND year='2023'"})
        # Sorted params; $ percent-encoded; where clause fully escaped.
        self.assertEqual(
            url,
            "https://data.cdc.gov/resource/bi63-dtpu.json"
            "?%24limit=5&%24offset=10"
            "&%24where=state%3D%27CA%27+AND+year%3D%272023%27")

    def test_app_token_header_only_when_configured(self):
        fake = FakeCdcData().add(_RESOURCE_PATH, leading_causes_rows())
        t = self._transport(app_token="SECRET")
        t.get_json(_RESOURCE_PATH, {"$limit": 1}, opener=fake)
        self.assertEqual(fake.headers_seen[0].get("X-App-Token"), "SECRET")

        fake2 = FakeCdcData().add(_RESOURCE_PATH, leading_causes_rows())
        t2 = self._transport()  # no token → header absent (bad tokens 403 live)
        t2.get_json(_RESOURCE_PATH, {"$limit": 1}, opener=fake2)
        self.assertNotIn("X-App-Token", fake2.headers_seen[0])

    def test_200_parses_json_array(self):
        fake = FakeCdcData().add(_RESOURCE_PATH, leading_causes_rows())
        t = self._transport()
        payload = t.get_json(_RESOURCE_PATH, {"$limit": 10}, opener=fake)
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["cause_name"], "Unintentional injuries")

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeCdcData().add(_RESOURCE_PATH, leading_causes_rows())
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            _RESOURCE_PATH, {"$limit": 10}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(payload), 3)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeCdcData().add(_RESOURCE_PATH, leading_causes_rows())
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(CdcDataApiError):
            t.get_json(_RESOURCE_PATH, {"$limit": 10}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # initial try + 2 retries

    def test_transport_error_status_0_retries(self):
        fake = FakeCdcData().add(_RESOURCE_PATH, leading_causes_rows())
        fake.transients[0] = (0, {})   # URLError folded to status 0
        t = self._transport()
        payload = t.get_json(_RESOURCE_PATH, {"$limit": 10}, opener=fake,
                             sleep=lambda s: None, now=lambda: 0.0,
                             rand=lambda: 0.0)
        self.assertEqual(len(payload), 3)

    def test_404_returns_empty_list(self):
        fake = FakeCdcData()  # nothing registered → 404 for any path
        t = self._transport()
        payload = t.get_json("/resource/nope-nope.json", {"$limit": 1},
                             opener=fake, sleep=lambda s: None)
        self.assertEqual(payload, [])

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeCdcData()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(CdcDataApiError):
            t.get_json(_RESOURCE_PATH, {"$limit": 1}, opener=fake,
                       sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400

    def test_non_json_body_raises_clear_error(self):
        class HtmlOpener:
            def __call__(self, url, headers, timeout):
                from ..transport import RawResponse
                return RawResponse(status=200, body=b"<html>oops</html>")
        t = self._transport()
        with self.assertRaises(CdcDataApiError) as ctx:
            t.get_json(_RESOURCE_PATH, opener=HtmlOpener())
        self.assertIn("non-JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
