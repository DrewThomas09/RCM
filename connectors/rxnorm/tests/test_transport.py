import unittest

from ..transport import RawResponse, RxNavApiError, RxNavTransport
from .fakes import FakeRxNav

_RXCUI = "/rxcui.json"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return RxNavTransport(**kw)

    def test_build_url_is_deterministic_and_sorts_params(self):
        t = self._transport()
        url = t.build_url(_RXCUI, {"idtype": "NDC", "id": "00006302602"})
        self.assertEqual(
            url, "https://rxnav.nlm.nih.gov/REST/rxcui.json"
                 "?id=00006302602&idtype=NDC")

    def test_200_parses_top_level_object(self):
        fake = FakeRxNav().add_ndc("00006-3026-02", "1547220")
        t = self._transport()
        doc = t.get_json(_RXCUI, {"idtype": "NDC", "id": "00006302602"},
                         opener=fake)
        self.assertEqual(doc["idGroup"]["rxnormId"], ["1547220"])

    def test_top_level_array_is_rejected(self):
        class ArrayOpener:
            def __call__(self, url, headers, timeout):
                return RawResponse(status=200, body=b"[1, 2, 3]")
        t = self._transport()
        with self.assertRaises(RxNavApiError):
            t.get_json(_RXCUI, {}, opener=ArrayOpener())

    def test_unresolvable_id_is_200_with_an_empty_envelope(self):
        # RxNav's empty result is NOT a 404 — it is a 200 whose envelope
        # simply lacks the payload key. The connector's diggers rely on
        # this, so pin the behaviour here too.
        fake = FakeRxNav()
        t = self._transport()
        doc = t.get_json(_RXCUI, {"idtype": "NDC", "id": "99999999999"},
                         opener=fake)
        self.assertEqual(doc, {"idGroup": {}})

    def test_404_returns_empty_dict(self):
        fake = FakeRxNav()
        fake.transients[0] = (404, {})
        t = self._transport()
        self.assertEqual(t.get_json(_RXCUI, {}, opener=fake), {})

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeRxNav().add_ndc("00006302602", "1547220")
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        doc = t.get_json(_RXCUI, {"idtype": "NDC", "id": "00006302602"},
                         opener=fake, sleep=sleeps.append, now=lambda: 0.0,
                         rand=lambda: 0.0)
        self.assertEqual(doc["idGroup"]["rxnormId"], ["1547220"])
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeRxNav()
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(RxNavApiError):
            t.get_json(_RXCUI, {}, opener=fake, sleep=lambda s: None,
                       now=lambda: 0.0, rand=lambda: 0.0)

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeRxNav()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(RxNavApiError):
            t.get_json(_RXCUI, {}, opener=fake, sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400


if __name__ == "__main__":
    unittest.main()
