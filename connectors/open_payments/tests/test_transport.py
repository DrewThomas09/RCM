import unittest

from ..transport import OpenPaymentsApiError, OpenPaymentsTransport
from .fakes import CATALOG_PATH, GENERAL_UUID, FakeOpenPayments, general_payment_row

_GENERAL_PATH = f"/api/1/datastore/query/{GENERAL_UUID}/0"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return OpenPaymentsTransport(**kw)

    def test_build_url_is_deterministic(self):
        t = self._transport()
        url = t.build_url(_GENERAL_PATH, {
            "offset": 0, "limit": 5,
            "conditions[0][property]": "recipient_state",
            "conditions[0][value]": "VT",
            "conditions[0][operator]": "=",
        })
        self.assertEqual(
            url,
            f"https://openpaymentsdata.cms.gov{_GENERAL_PATH}"
            "?conditions%5B0%5D%5Boperator%5D=%3D"
            "&conditions%5B0%5D%5Bproperty%5D=recipient_state"
            "&conditions%5B0%5D%5Bvalue%5D=VT"
            "&limit=5&offset=0")

    def test_200_parses_datastore_envelope(self):
        fake = FakeOpenPayments().add(GENERAL_UUID,
                                      [general_payment_row("1092248200")])
        payload = self._transport().get_json(_GENERAL_PATH, {"limit": 10},
                                             opener=fake)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["results"][0]["record_id"], "1092248200")

    def test_200_parses_top_level_list_catalog(self):
        # The metastore catalog is a JSON list, not a dict envelope.
        fake = FakeOpenPayments()
        payload = self._transport().get_json(CATALOG_PATH, opener=fake)
        self.assertIsInstance(payload, list)
        self.assertEqual(payload[0]["identifier"], GENERAL_UUID)

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeOpenPayments().add(GENERAL_UUID,
                                      [general_payment_row("1")])
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        payload = self._transport().get_json(
            _GENERAL_PATH, {"limit": 10}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(payload["results"][0]["record_id"], "1")
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeOpenPayments().add(GENERAL_UUID, [general_payment_row("1")])
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(OpenPaymentsApiError):
            t.get_json(_GENERAL_PATH, {"limit": 10}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # initial + 2 retries

    def test_404_returns_empty_envelope(self):
        # Unknown dataset UUID → empty results, not an exception.
        fake = FakeOpenPayments()
        payload = self._transport().get_json(
            "/api/1/datastore/query/00000000-0000-0000-0000-000000000000/0",
            {"limit": 10}, opener=fake, sleep=lambda s: None)
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["count"], 0)

    def test_hard_400_raises_without_retry_and_carries_message(self):
        # The live engine 400s on limit > 500; the message must surface.
        fake = FakeOpenPayments().add(GENERAL_UUID, [general_payment_row("1")])
        t = self._transport()
        with self.assertRaises(OpenPaymentsApiError) as ctx:
            t.get_json(_GENERAL_PATH, {"limit": 600}, opener=fake,
                       sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)      # no retry on a 400
        self.assertIn("less than or equal 500", str(ctx.exception))

    def test_non_json_body_raises(self):
        fake = FakeOpenPayments()
        fake.transients[0] = (200, {}, b"<html>maintenance</html>")
        with self.assertRaises(OpenPaymentsApiError):
            self._transport().get_json(_GENERAL_PATH, opener=fake,
                                       sleep=lambda s: None)


if __name__ == "__main__":
    unittest.main()
