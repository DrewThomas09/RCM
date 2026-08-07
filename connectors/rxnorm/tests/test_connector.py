import unittest

from ..connector import RxNormConnector
from ..endpoints import get_endpoint
from ..transport import RxNavTransport
from .fakes import FakeRxNav


def _conn(max_ids_per_step=25):
    t = RxNavTransport(min_interval_s=0.0)
    return RxNormConnector(t, max_ids_per_step=max_ids_per_step)


def _fake():
    return (FakeRxNav()
            .add_concept("1547220", "pembrolizumab 25 MG/ML",
                         ingredients=["pembrolizumab"],
                         atc=["Antineoplastic agents"])
            .add_ndc("00006-3026-02", "1547220")
            .add_name("keytruda", "1547220"))


class NdcResolveTests(unittest.TestCase):
    def test_ndc_resolves_to_rxcui_and_enriched_concept(self):
        fake = _fake()
        res = _conn().fetch(get_endpoint("ndc"),
                            {"ndcs": "00006-3026-02"}, opener=fake)
        self.assertIsNone(res.next_cursor)
        self.assertEqual(len(res.rows), 1)
        row = res.rows[0]
        self.assertEqual(row["rxcui"], "1547220")
        self.assertEqual(row["ndc_digits"], "00006302602")
        self.assertEqual(row["concept"]["name"], "pembrolizumab 25 MG/ML")
        self.assertEqual(row["concept"]["ingredients"], ["pembrolizumab"])
        self.assertEqual(row["concept"]["classes"], ["Antineoplastic agents"])
        self.assertEqual(row["concept"]["class_source"], "ATC")

    def test_hyphenation_does_not_matter(self):
        fake = _fake()
        res = _conn().fetch(get_endpoint("ndc"),
                            {"ndcs": ["00006302602"]}, opener=fake)
        self.assertEqual(res.rows[0]["rxcui"], "1547220")

    def test_unresolvable_ndc_is_recorded_not_fatal(self):
        fake = _fake()
        res = _conn().fetch(get_endpoint("ndc"),
                            {"ndcs": "00006-3026-02,99999999999"}, opener=fake)
        self.assertEqual(len(res.rows), 1)
        self.assertEqual(res.unresolved, ["99999999999"])

    def test_too_short_to_be_an_ndc_is_skipped_without_a_request(self):
        fake = _fake()
        res = _conn().fetch(get_endpoint("ndc"), {"ndcs": "123"}, opener=fake)
        self.assertEqual(res.rows, [])
        self.assertEqual(res.unresolved, ["123"])
        self.assertEqual(fake.calls, [])

    def test_roster_is_required(self):
        with self.assertRaises(ValueError):
            _conn().fetch(get_endpoint("ndc"), {}, opener=_fake())

    def test_roster_resumes_across_steps(self):
        fake = _fake()
        for i in range(5):
            fake.add_ndc(f"1111111111{i}", "1547220")
        conn = _conn(max_ids_per_step=2)
        spec = get_endpoint("ndc")
        params = {"ndcs": [f"1111111111{i}" for i in range(5)]}
        rows, cursor, steps = [], None, 0
        while True:
            res = conn.fetch(spec, params, cursor, opener=fake)
            rows.extend(res.rows)
            steps += 1
            if res.next_cursor is None:
                break
            cursor = res.next_cursor
        self.assertEqual(len(rows), 5)
        self.assertEqual(steps, 3)  # 2 + 2 + 1


class NameResolveTests(unittest.TestCase):
    def test_exact_name_match(self):
        fake = _fake()
        res = _conn().fetch(get_endpoint("name"), {"names": "KEYTRUDA"},
                            opener=fake)
        row = res.rows[0]
        self.assertEqual(row["rxcui"], "1547220")
        self.assertEqual(row["match_type"], "exact")

    def test_approximate_fallback_is_flagged(self):
        fake = _fake().add_approximate("keytrudah", "1547220")
        res = _conn().fetch(get_endpoint("name"), {"names": "KEYTRUDAH"},
                            opener=fake)
        row = res.rows[0]
        self.assertEqual(row["rxcui"], "1547220")
        self.assertEqual(row["match_type"], "approximate")

    def test_unresolvable_name_is_recorded(self):
        fake = _fake()
        res = _conn().fetch(get_endpoint("name"), {"names": "NOT A DRUG"},
                            opener=fake)
        self.assertEqual(res.rows, [])
        self.assertEqual(res.unresolved, ["NOT A DRUG"])


class ConceptResolveTests(unittest.TestCase):
    def test_rxcui_enriches_directly(self):
        fake = _fake()
        res = _conn().fetch(get_endpoint("concept"), {"rxcuis": "1547220"},
                            opener=fake)
        self.assertEqual(res.rows[0]["concept"]["tty"], "SCD")

    def test_unknown_rxcui_is_unresolved(self):
        fake = _fake()
        res = _conn().fetch(get_endpoint("concept"), {"rxcuis": "999999"},
                            opener=fake)
        self.assertEqual(res.rows, [])
        self.assertEqual(res.unresolved, ["999999"])

    def test_dailymed_fallback_when_no_atc_class(self):
        # Biologics such as immune globulin often carry no ATC class but do
        # carry a DailyMed pharmacologic class — the fallback keeps the
        # class column populated for exactly those high-cost Part B drugs.
        fake = (FakeRxNav()
                .add_concept("1657443", "immune globulin",
                             ingredients=["immune globulin"],
                             dailymed=["Immunoglobulin"]))
        res = _conn().fetch(get_endpoint("concept"), {"rxcuis": "1657443"},
                            opener=fake)
        concept = res.rows[0]["concept"]
        self.assertEqual(concept["classes"], ["Immunoglobulin"])
        self.assertEqual(concept["class_source"], "DAILYMED")


if __name__ == "__main__":
    unittest.main()
