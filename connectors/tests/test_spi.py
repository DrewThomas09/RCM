"""The service-provider interface: adapter loading + the generic binder."""
import unittest

from .._spi import (
    CONNECTOR_NAMES, invoke_handler, load_all, match_template,
)


class AdapterLoadTests(unittest.TestCase):
    def test_every_connector_loads_a_store_class_and_query_engine(self):
        adapters = load_all()
        self.assertEqual(set(adapters), set(CONNECTOR_NAMES))
        for name, a in adapters.items():
            self.assertTrue(a.store_cls.__name__.endswith("Store"))
            self.assertTrue(callable(a.query_mod.query))
            self.assertTrue(callable(a.query_mod.aggregate))
            self.assertTrue(issubclass(a.QueryError, Exception))
            self.assertTrue(a.dataset_ids())
            self.assertTrue(a.base_urls())


class MatchTemplateTests(unittest.TestCase):
    def test_matches_and_extracts_params_in_order(self):
        self.assertEqual(
            match_template("/v1/lookup/code/{code}",
                           ["v1", "lookup", "code", "E11.65"]),
            {"code": "E11.65"})

    def test_literal_mismatch_returns_none(self):
        self.assertIsNone(
            match_template("/v1/lookup/code/{code}",
                           ["v1", "lookup", "drug", "0002-1200"]))

    def test_length_mismatch_returns_none(self):
        self.assertIsNone(
            match_template("/v1/lookup/code/{code}", ["v1", "lookup", "code"]))


class InvokeHandlerTests(unittest.TestCase):
    def test_single_path_param_positional(self):
        got = invoke_handler(lambda code: {"code": code},
                             {"code": "E11.65"}, {})
        self.assertEqual(got, {"code": "E11.65"})

    def test_extra_params_pulled_from_query_string(self):
        # Mirrors ICD-10 search: (code_type, q="", limit=50).
        got = invoke_handler(
            lambda code_type, q="", limit=50: (code_type, q, limit),
            {"code_type": "cm"}, {"q": ["diabetes"], "limit": ["5"]})
        self.assertEqual(got, ("cm", "diabetes", "5"))

    def test_code_type_alias_maps_from_type_query_key(self):
        # Handler param is code_type; it is exposed as ?type=.
        got = invoke_handler(
            lambda code, code_type="cm": (code, code_type),
            {"code": "E11.65"}, {"type": ["pcs"]})
        self.assertEqual(got, ("E11.65", "pcs"))

    def test_defaults_used_when_query_absent(self):
        got = invoke_handler(
            lambda code, code_type="cm": (code, code_type),
            {"code": "E11.65"}, {})
        self.assertEqual(got, ("E11.65", "cm"))


if __name__ == "__main__":
    unittest.main()
