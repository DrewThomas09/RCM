import unittest

from ..transport import OigLeieApiError, OigLeieTransport
from .fakes import (FakeOig, SUPPL_2605_EXCL, UPDATED_PATH, supplement_excl_csv,
                    updated_csv)


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return OigLeieTransport(**kw)

    def test_build_url_is_deterministic(self):
        t = self._transport()
        self.assertEqual(
            t.build_url(UPDATED_PATH),
            "https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv")
        self.assertEqual(
            t.build_url(SUPPL_2605_EXCL),
            "https://oig.hhs.gov/exclusions/downloadables/2026/2605excl.csv")

    def test_200_parses_rows_with_raw_headers_and_values(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(len(res.rows), 4)
        self.assertFalse(res.truncated)
        self.assertEqual(len(res.fieldnames), 18)
        self.assertEqual(res.fieldnames[0], "LASTNAME")
        self.assertEqual(res.fieldnames[-1], "WVRSTATE")
        # Raw values survive verbatim — sentinel cleanup is normalize's job.
        self.assertEqual(res.rows[0]["NPI"], "0000000000")
        self.assertEqual(res.rows[0]["REINDATE"], "00000000")

    def test_quoted_comma_busname_survives(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(res.rows[0]["BUSNAME"], "#1 MARKETING SERVICE, INC")

    def test_bom_is_stripped_from_first_header(self):
        fake = FakeOig().add(UPDATED_PATH, "\ufeff" + updated_csv())
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(res.fieldnames[0], "LASTNAME")

    def test_short_row_is_padded_to_header_shape(self):
        body = updated_csv().splitlines()[0] + "\r\nDOE,JANE\r\n"
        fake = FakeOig().add(UPDATED_PATH, body)
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(res.rows[0]["LASTNAME"], "DOE")
        self.assertEqual(res.rows[0]["WVRSTATE"], "")   # padded, stable shape

    def test_max_rows_caps_and_flags_truncation(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        res = self._transport().get_csv(UPDATED_PATH, max_rows=2, opener=fake)
        self.assertEqual(len(res.rows), 2)
        self.assertTrue(res.truncated)
        # Exactly at the row count → not truncated.
        res2 = self._transport().get_csv(UPDATED_PATH, max_rows=4, opener=fake)
        self.assertEqual(len(res2.rows), 4)
        self.assertFalse(res2.truncated)

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        res = self._transport().get_csv(
            UPDATED_PATH, opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 4)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(OigLeieApiError):
            t.get_csv(UPDATED_PATH, opener=fake,
                      sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # initial + 2 retries

    def test_transport_error_status_0_retries(self):
        fake = FakeOig().add(UPDATED_PATH, updated_csv())
        fake.transients[0] = (0, {})
        res = self._transport().get_csv(
            UPDATED_PATH, opener=fake,
            sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(res.rows), 4)
        self.assertEqual(len(fake.calls), 2)

    def test_404_raises_immediately_with_status_and_index_pointer(self):
        fake = FakeOig()  # nothing registered → 404
        t = self._transport()
        with self.assertRaises(OigLeieApiError) as ctx:
            t.get_csv("/exclusions/downloadables/2026/2606excl.csv",
                      opener=fake, sleep=lambda s: None)
        self.assertEqual(ctx.exception.status, 404)
        self.assertIn("exclusions_list.asp", str(ctx.exception))
        self.assertEqual(len(fake.calls), 1)  # no retry on a 404

    def test_hard_4xx_raises_without_retry(self):
        fake = FakeOig()
        fake.transients[0] = (403, {})
        t = self._transport()
        with self.assertRaises(OigLeieApiError) as ctx:
            t.get_csv(UPDATED_PATH, opener=fake, sleep=lambda s: None)
        self.assertEqual(ctx.exception.status, 403)
        self.assertEqual(len(fake.calls), 1)

    def test_empty_body_raises_clear_error(self):
        fake = FakeOig().add(UPDATED_PATH, "")
        with self.assertRaises(OigLeieApiError) as ctx:
            self._transport().get_csv(UPDATED_PATH, opener=fake,
                                      sleep=lambda s: None)
        self.assertIn("empty CSV", str(ctx.exception))

    def test_header_only_file_yields_zero_rows(self):
        header_only = updated_csv().splitlines()[0] + "\r\n"
        fake = FakeOig().add(UPDATED_PATH, header_only)
        res = self._transport().get_csv(UPDATED_PATH, opener=fake)
        self.assertEqual(res.rows, [])
        self.assertFalse(res.truncated)

    def test_supplement_file_parses_same_shape(self):
        fake = FakeOig().add(SUPPL_2605_EXCL, supplement_excl_csv())
        res = self._transport().get_csv(SUPPL_2605_EXCL, opener=fake)
        self.assertEqual(len(res.rows), 2)
        self.assertEqual(len(res.fieldnames), 18)


if __name__ == "__main__":
    unittest.main()
