import unittest

from ..transport import NlmApiError, NlmTransport
from .fakes import FakeNlm

_HCPCS = "/hcpcs/v3/search"


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return NlmTransport(**kw)

    def test_build_url_is_deterministic_and_sorts_params(self):
        t = self._transport()
        url = t.build_url(_HCPCS, {"terms": "", "df": "code,display", "offset": 0})
        self.assertEqual(
            url,
            "https://clinicaltables.nlm.nih.gov/api/hcpcs/v3/search"
            "?df=code%2Cdisplay&offset=0&terms=")

    def test_build_url_injects_key_when_present(self):
        t = self._transport(api_key="SECRET")
        url = t.build_url(_HCPCS, {"terms": "cpap"})
        self.assertIn("api_key=SECRET", url)

    def test_200_parses_top_level_array(self):
        fake = FakeNlm().add(_HCPCS, [{"code": "J9271", "display": "Pembrolizumab inj"}])
        t = self._transport()
        arr = t.get_json(_HCPCS, {"terms": "", "df": "code,display", "maxList": 5},
                         opener=fake)
        # A top-level LIST is accepted (unlike openFDA which requires a dict).
        self.assertIsInstance(arr, list)
        self.assertEqual(arr[0], 1)              # total
        self.assertEqual(arr[1], ["J9271"])      # code list
        self.assertEqual(arr[3][0][0], "J9271")  # display row

    def test_top_level_dict_is_rejected(self):
        class DictOpener:
            def __call__(self, url, headers, timeout):
                from ..transport import RawResponse
                return RawResponse(status=200, body=b'{"not": "an array"}')
        t = self._transport()
        with self.assertRaises(NlmApiError):
            t.get_json(_HCPCS, {"terms": ""}, opener=DictOpener())

    def test_404_returns_empty_array_shape(self):
        fake = FakeNlm()
        fake.transients[0] = (404, {})
        t = self._transport()
        arr = t.get_json(_HCPCS, {"terms": ""}, opener=fake)
        self.assertEqual(arr, [0, [], None, []])

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeNlm().add(_HCPCS, [{"code": "J9271", "display": "x"}])
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        arr = t.get_json(
            _HCPCS, {"terms": "", "df": "code,display", "maxList": 5}, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(arr[1], ["J9271"])
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeNlm().add(_HCPCS, [{"code": "A0428", "display": "a"}])
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(NlmApiError):
            t.get_json(_HCPCS, {"terms": ""}, opener=fake,
                       sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeNlm()
        fake.transients[0] = (400, {})
        t = self._transport()
        with self.assertRaises(NlmApiError):
            t.get_json(_HCPCS, {"terms": ""}, opener=fake, sleep=lambda s: None)
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400


if __name__ == "__main__":
    unittest.main()
