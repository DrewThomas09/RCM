import unittest

from ..transport import MedicaidDataApiError, MedicaidDataTransport
from .fakes import NADAC_2026_ID, FakeMedicaidData, catalog_item, nadac_row

_NADAC_PATH = f"/api/1/datastore/query/{NADAC_2026_ID}/0"
_CATALOG_PATH = "/api/1/metastore/schemas/dataset/items"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return MedicaidDataTransport(**kw)

    def test_build_url_is_deterministic(self):
        t = self._transport()
        url = t.build_url(_NADAC_PATH, {"offset": 500, "limit": 500})
        self.assertEqual(
            url,
            f"https://data.medicaid.gov{_NADAC_PATH}?limit=500&offset=500")

    def test_200_parses_datastore_envelope(self):
        fake = FakeMedicaidData().add_datastore(NADAC_2026_ID, [nadac_row()])
        t = self._transport()
        payload = t.get_json(_NADAC_PATH, {"limit": 10, "offset": 0},
                             opener=fake)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["ndc"], "24385005452")

    def test_200_parses_catalog_array(self):
        # The metastore returns a bare JSON array — the transport must not
        # reject list payloads (a DKAN quirk the object-only estates lack).
        fake = FakeMedicaidData().add_catalog([catalog_item()])
        t = self._transport()
        payload = t.get_json(_CATALOG_PATH, opener=fake)
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["identifier"], NADAC_2026_ID)

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeMedicaidData().add_datastore(NADAC_2026_ID, [nadac_row()])
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.get_json(
            _NADAC_PATH, {"limit": 10}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(payload["results"][0]["ndc"], "24385005452")
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeMedicaidData().add_datastore(NADAC_2026_ID, [nadac_row()])
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(MedicaidDataApiError):
            t.get_json(_NADAC_PATH, {"limit": 10}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)

    def test_transport_error_status_0_retries_then_raises(self):
        fake = FakeMedicaidData()
        for i in range(10):
            fake.transients[i] = (0, {})
        t = self._transport(max_retries=1)
        with self.assertRaises(MedicaidDataApiError):
            t.get_json(_NADAC_PATH, opener=fake, sleep=lambda s: None,
                       now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 2)  # initial + 1 retry

    def test_404_returns_empty_envelope(self):
        # Unknown dataset UUID — live returns 404; the transport folds it
        # into an empty result so catalog-wide probes don't explode.
        fake = FakeMedicaidData()
        t = self._transport()
        payload = t.get_json("/api/1/datastore/query/unknown-uuid/0",
                             {"limit": 10}, opener=fake, sleep=lambda s: None)
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["count"], 0)

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeMedicaidData()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(MedicaidDataApiError):
            t.get_json(_NADAC_PATH, {"limit": 10}, opener=fake,
                       sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400

    def test_non_json_body_raises_clear_error(self):
        class HtmlOpener:
            def __call__(self, url, headers, timeout):
                from ..transport import RawResponse
                return RawResponse(status=200, body=b"<html>oops</html>")
        t = self._transport()
        with self.assertRaises(MedicaidDataApiError) as ctx:
            t.get_json(_NADAC_PATH, opener=HtmlOpener())
        self.assertIn("non-JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
