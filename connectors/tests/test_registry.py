"""The aggregated estate registry: counts, ownership, uniform rows."""
import unittest

from .. import registry as estate
from .._spi import CONNECTOR_NAMES


class EstateRegistryTests(unittest.TestCase):
    def test_all_rows_is_the_sum_of_every_connector(self):
        rows = estate.all_registry_rows()
        adapters = estate.adapters()
        expected = sum(len(adapters[n].dataset_ids()) for n in CONNECTOR_NAMES)
        self.assertEqual(len(rows), expected)
        # Every connector is represented.
        self.assertEqual({r["connector"] for r in rows}, set(CONNECTOR_NAMES))

    def test_rows_carry_the_uniform_registry_fields(self):
        required = {"dataset_id", "connector", "base_url", "endpoint",
                    "default_params", "refresh_cadence", "join_keys",
                    "target_table", "source", "source_filter", "date_field"}
        for r in estate.all_registry_rows():
            self.assertTrue(required.issubset(r), f"missing fields on {r}")
            # The tag columns are self-consistent.
            self.assertEqual(r["connector"], r["source"])

    def test_dataset_ids_are_globally_unique(self):
        ids = [r["dataset_id"] for r in estate.all_registry_rows()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_dataset_owner_resolves_and_unknown_is_none(self):
        self.assertEqual(estate.dataset_owner("openfda_drug_ndc"), "openfda")
        self.assertEqual(estate.dataset_owner("icd10_cm"), "icd10")
        self.assertEqual(estate.dataset_owner("npi_provider"), "npi_registry")
        self.assertIsNone(estate.dataset_owner("does_not_exist"))

    def test_connectors_summary_and_catalog_shape(self):
        summary = estate.connectors_summary()
        self.assertEqual([s["connector"] for s in summary], list(CONNECTOR_NAMES))
        for s in summary:
            self.assertEqual(s["n_datasets"], len(s["dataset_ids"]))
            self.assertTrue(s["base_urls"])
        cat = estate.catalog()
        self.assertEqual(cat["n_connectors"], len(CONNECTOR_NAMES))
        self.assertEqual(cat["n_datasets"], len(estate.all_registry_rows()))


if __name__ == "__main__":
    unittest.main()
