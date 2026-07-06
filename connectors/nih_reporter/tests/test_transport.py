import json
import unittest

from ..transport import NihReporterApiError, NihReporterTransport
from .fakes import FakeNihReporter, PROJECTS_PATH, project_record


class TransportTests(unittest.TestCase):
    def _transport(self, **kw):
        kw.setdefault("min_interval_s", 0.0)
        return NihReporterTransport(**kw)

    def test_build_url_is_deterministic(self):
        t = self._transport()
        self.assertEqual(t.build_url(PROJECTS_PATH),
                         "https://api.reporter.nih.gov/v2/projects/search")

    def test_200_posts_json_body_and_parses_results(self):
        fake = FakeNihReporter().add(PROJECTS_PATH, [project_record()])
        t = self._transport()
        payload = t.post_json(
            PROJECTS_PATH,
            {"criteria": {"fiscal_years": [2025]}, "offset": 0, "limit": 10},
            opener=fake)
        self.assertEqual(payload["results"][0]["appl_id"], 11184227)
        self.assertEqual(payload["meta"]["total"], 1)
        # The opener received the encoded criteria, not query params.
        url, body = fake.calls[0]
        self.assertNotIn("?", url)
        self.assertEqual(body["criteria"], {"fiscal_years": [2025]})

    def test_429_honours_retry_after_then_succeeds(self):
        fake = FakeNihReporter().add(PROJECTS_PATH, [project_record()])
        fake.transients[0] = (429, {"retry-after": "2"})
        sleeps = []
        t = self._transport()
        payload = t.post_json(
            PROJECTS_PATH, {"criteria": {}, "offset": 0, "limit": 10},
            opener=fake,
            sleep=sleeps.append, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(payload["results"][0]["appl_id"], 11184227)
        self.assertIn(2.0, sleeps)  # Retry-After respected

    def test_5xx_exhausts_and_raises(self):
        fake = FakeNihReporter().add(PROJECTS_PATH, [project_record()])
        for i in range(10):
            fake.transients[i] = (503, {})
        t = self._transport(max_retries=2)
        with self.assertRaises(NihReporterApiError):
            t.post_json(PROJECTS_PATH, {"criteria": {}}, opener=fake,
                        sleep=lambda s: None, now=lambda: 0.0, rand=lambda: 0.0)
        self.assertEqual(len(fake.calls), 3)  # initial try + 2 retries

    def test_404_returns_empty_results(self):
        fake = FakeNihReporter()
        fake.transients[0] = (404, {})
        t = self._transport()
        payload = t.post_json(PROJECTS_PATH, {"criteria": {}}, opener=fake,
                              sleep=lambda s: None)
        self.assertEqual(payload["results"], [])
        self.assertEqual(payload["meta"]["total"], 0)

    def test_limit_validation_400_raises_without_retry(self):
        # Live shape: 400 + JSON array of message strings, no retry.
        fake = FakeNihReporter().add(PROJECTS_PATH, [project_record()])
        t = self._transport()
        with self.assertRaises(NihReporterApiError) as ctx:
            t.post_json(PROJECTS_PATH,
                        {"criteria": {}, "offset": 0, "limit": 501},
                        opener=fake, sleep=lambda s: None)
        self.assertIn("limit value greater than 500", str(ctx.exception))
        self.assertEqual(len(fake.calls), 1)  # no retry on a 400

    def test_offset_cap_400_raises_without_retry(self):
        fake = FakeNihReporter().add(PROJECTS_PATH, [project_record()])
        t = self._transport()
        with self.assertRaises(NihReporterApiError) as ctx:
            t.post_json(PROJECTS_PATH,
                        {"criteria": {}, "offset": 15000, "limit": 1},
                        opener=fake, sleep=lambda s: None)
        self.assertIn("offset value greater than 14,999", str(ctx.exception))
        self.assertEqual(len(fake.calls), 1)

    def test_non_json_body_raises_clear_error(self):
        def opener(url, data, headers, timeout):
            from ..transport import RawResponse
            return RawResponse(status=200, body=b"<html>not json</html>")
        t = self._transport()
        with self.assertRaises(NihReporterApiError) as ctx:
            t.post_json(PROJECTS_PATH, {"criteria": {}}, opener=opener,
                        sleep=lambda s: None)
        self.assertIn("non-JSON", str(ctx.exception))

    def test_headers_carry_content_type_and_user_agent(self):
        seen = {}

        def opener(url, data, headers, timeout):
            from ..transport import RawResponse
            seen.update(headers)
            return RawResponse(status=200, body=json.dumps(
                {"meta": {"total": 0}, "results": []}).encode())

        t = self._transport()
        t.post_json(PROJECTS_PATH, {"criteria": {}}, opener=opener,
                    sleep=lambda s: None)
        self.assertEqual(seen["Content-Type"], "application/json")
        self.assertIn("nih_reporter", seen["User-Agent"])


if __name__ == "__main__":
    unittest.main()
