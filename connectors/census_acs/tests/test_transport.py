import unittest

from ..transport import CensusAcsApiError, CensusAcsTransport
from .fakes import MISSING_KEY_HTML, FakeCensusApi

_DETAIL_PATH = "/2023/acs/acs5"
_PARAMS = {"get": "NAME,B01001_001E", "for": "county:*", "in": "state:48"}


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return CensusAcsTransport(**kw)

    def test_build_url_is_deterministic_and_injects_key(self):
        t = self._transport(api_key="SECRET")
        url = t.build_url(_DETAIL_PATH, dict(_PARAMS))
        self.assertEqual(
            url,
            "https://api.census.gov/data/2023/acs/acs5"
            "?for=county%3A%2A&get=NAME%2CB01001_001E&in=state%3A48&key=SECRET")

    def test_build_url_encodes_cbsa_geography(self):
        t = self._transport()
        url = t.build_url(_DETAIL_PATH, {
            "for": "metropolitan statistical area/"
                   "micropolitan statistical area:*"})
        self.assertIn(
            "for=metropolitan+statistical+area%2F"
            "micropolitan+statistical+area%3A%2A", url)
        self.assertNotIn("key=", url)  # no key configured → none injected

    def test_200_parses_array_of_arrays(self):
        fake = FakeCensusApi.with_defaults()
        t = self._transport()
        rows = t.get_rows(_DETAIL_PATH, dict(_PARAMS), opener=fake)
        self.assertEqual(rows[0][0], "NAME")           # header row first
        self.assertEqual(rows[1][0], "Harris County, Texas")
        self.assertEqual(len(rows), 4)                 # header + 3 counties

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeCensusApi.with_defaults()
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        rows = t.get_rows(
            _DETAIL_PATH, dict(_PARAMS), opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(rows[1][0], "Harris County, Texas")
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeCensusApi.with_defaults()
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(CensusAcsApiError):
            t.get_rows(_DETAIL_PATH, dict(_PARAMS), opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)

    def test_missing_key_html_raises_actionable_error(self):
        # urllib follows the API's 302 to the HTML page → a 200 non-JSON
        # body. The transport must name the env var, not choke on parse.
        fake = FakeCensusApi()
        fake.transients[0] = (200, {}, MISSING_KEY_HTML)
        t = self._transport()
        with self.assertRaises(CensusAcsApiError) as ctx:
            t.get_rows(_DETAIL_PATH, dict(_PARAMS), opener=fake,
                       sleep=lambda s: None)
        self.assertIn("CENSUS_API_KEY", str(ctx.exception))
        self.assertIn("key_signup", str(ctx.exception))
        self.assertEqual(len(fake.calls), 1)  # unrecoverable → no retry

    def test_unfollowed_302_raises_same_key_error(self):
        fake = FakeCensusApi()
        fake.transients[0] = (302, {"location": "/data/missing_key.html"}, b"")
        t = self._transport()
        with self.assertRaises(CensusAcsApiError) as ctx:
            t.get_rows(_DETAIL_PATH, dict(_PARAMS), opener=fake,
                       sleep=lambda s: None)
        self.assertIn("CENSUS_API_KEY", str(ctx.exception))

    def test_204_no_content_returns_empty(self):
        fake = FakeCensusApi()
        fake.transients[0] = (204, {}, b"")
        t = self._transport()
        rows = t.get_rows(_DETAIL_PATH, dict(_PARAMS), opener=fake,
                          sleep=lambda s: None)
        self.assertEqual(rows, [])

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeCensusApi()
        fake.transients[0] = (400, {}, b"error: unknown variable 'B9_FAKE'")
        t = self._transport()
        with self.assertRaises(CensusAcsApiError) as ctx:
            t.get_rows(_DETAIL_PATH, dict(_PARAMS), opener=fake,
                       sleep=lambda s: None)
        self.assertIn("unknown variable", str(ctx.exception))
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400

    def test_unknown_vintage_404_raises_clearly(self):
        fake = FakeCensusApi.with_defaults()   # only 2023 loaded
        t = self._transport()
        with self.assertRaises(CensusAcsApiError) as ctx:
            t.get_rows("/1999/acs/acs5", dict(_PARAMS), opener=fake,
                       sleep=lambda s: None)
        self.assertIn("HTTP 404", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
