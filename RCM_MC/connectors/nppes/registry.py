"""Declarative dataset registry for the NPPES source.

Architecture contract: *every dataset is one declarative row*. Adding a
dataset is a registry row, not new routing code. The ``/v1/query/{dataset}``
surface auto-exposes anything that appears here, and the query engine in
``api.py`` resolves ``target_table`` + ``join_keys`` from these rows.

Each row::

    {dataset_id, connector, base_url, endpoint, default_params,
     refresh_cadence, join_keys, target_table, source}

``source`` is fixed to ``"nppes"`` so the host registry can filter/merge
this slice without colliding with other connectors' rows. Nothing here
performs I/O at import time.
"""
from __future__ import annotations

from typing import Dict, List

SOURCE = "nppes"

# Canonical crosswalk keys this connector OWNS (NPI, NUCC taxonomy). The
# others (FIPS, CPT/HCPCS, MS-DRG, NDC↔RxCUI) are owned elsewhere and must
# not be rewritten here — they appear only as nullable, wireable columns.
OWNED_KEYS = ("npi", "nucc_taxonomy")

# Bulk dissemination + NUCC code set + the live API, as declarative rows.
NPPES_DATASETS: List[Dict] = [
    {
        "dataset_id": "nppes_monthly_full",
        "connector": "nppes",
        "base_url": "https://download.cms.gov/nppes/",
        "endpoint": "NPPES_Data_Dissemination_{month}_{year}.zip",
        "default_params": {"kind": "monthly_full"},
        "refresh_cadence": "monthly",
        "join_keys": ["npi"],
        "target_table": "dim_provider",
        "source": SOURCE,
    },
    {
        "dataset_id": "nppes_weekly_incremental",
        "connector": "nppes",
        "base_url": "https://download.cms.gov/nppes/",
        "endpoint": "NPPES_Data_Dissemination_{month}_{day}_{year}_Weekly.zip",
        "default_params": {"kind": "weekly_incremental"},
        "refresh_cadence": "weekly",
        "join_keys": ["npi"],
        "target_table": "dim_provider",
        "source": SOURCE,
    },
    {
        "dataset_id": "nppes_othername",
        "connector": "nppes",
        "base_url": "https://download.cms.gov/nppes/",
        "endpoint": "othername_pfile.csv",
        "default_params": {"kind": "othername"},
        "refresh_cadence": "monthly",
        "join_keys": ["npi"],
        "target_table": "nppes_other_name",
        "source": SOURCE,
    },
    {
        "dataset_id": "nppes_practice_location",
        "connector": "nppes",
        "base_url": "https://download.cms.gov/nppes/",
        "endpoint": "pl_pfile.csv",
        "default_params": {"kind": "practice_location"},
        "refresh_cadence": "monthly",
        "join_keys": ["npi"],
        "target_table": "dim_provider_address",
        "source": SOURCE,
    },
    {
        "dataset_id": "nppes_endpoint",
        "connector": "nppes",
        "base_url": "https://download.cms.gov/nppes/",
        "endpoint": "endpoint_pfile.csv",
        "default_params": {"kind": "endpoint"},
        "refresh_cadence": "monthly",
        "join_keys": ["npi"],
        "target_table": "dim_provider_endpoint",
        "source": SOURCE,
    },
    {
        "dataset_id": "nucc_taxonomy",
        "connector": "nppes",
        "base_url": "https://www.nucc.org/",
        "endpoint": "images/stories/CSV/nucc_taxonomy_{version}.csv",
        "default_params": {"kind": "nucc_taxonomy"},
        "refresh_cadence": "biannual",
        "join_keys": ["taxonomy_code"],
        "target_table": "dim_taxonomy",
        "source": SOURCE,
    },
    {
        "dataset_id": "npi_registry_api",
        "connector": "nppes",
        "base_url": "https://npiregistry.cms.hhs.gov/api/",
        "endpoint": "?version=2.1",
        # Live lookup / incremental verification only. The API caps at 200
        # rows/request and blocks paging past ~1,200 for one query, so it is
        # NOT a backfill path — that is what nppes_monthly_full is for.
        "default_params": {"kind": "api_lookup", "limit": 200},
        "refresh_cadence": "on_demand",
        "join_keys": ["npi"],
        "target_table": "dim_provider",
        "source": SOURCE,
    },
    {
        # Derived, query-exposed dimensions/bridges (no remote endpoint).
        "dataset_id": "nppes_provider_taxonomy",
        "connector": "nppes",
        "base_url": "",
        "endpoint": "",
        "default_params": {"kind": "derived"},
        "refresh_cadence": "derived",
        "join_keys": ["npi", "taxonomy_code"],
        "target_table": "bridge_provider_taxonomy",
        "source": SOURCE,
    },
    {
        "dataset_id": "nppes_provider_affiliation",
        "connector": "nppes",
        "base_url": "",
        "endpoint": "",
        "default_params": {"kind": "derived"},
        "refresh_cadence": "derived",
        "join_keys": ["individual_npi", "organization_npi"],
        "target_table": "bridge_provider_affiliation",
        "source": SOURCE,
    },
    {
        "dataset_id": "nppes_provider_address",
        "connector": "nppes",
        "base_url": "",
        "endpoint": "",
        "default_params": {"kind": "derived"},
        "refresh_cadence": "derived",
        "join_keys": ["npi"],
        "target_table": "dim_provider_address",
        "source": SOURCE,
    },
]


def registry_rows() -> List[Dict]:
    """Return a deep-ish copy of the registry rows (callers may mutate
    default_params safely)."""
    out = []
    for row in NPPES_DATASETS:
        r = dict(row)
        r["default_params"] = dict(row["default_params"])
        r["join_keys"] = list(row["join_keys"])
        out.append(r)
    return out


def dataset_by_id(dataset_id: str) -> Dict:
    for row in NPPES_DATASETS:
        if row["dataset_id"] == dataset_id:
            return dict(row)
    raise KeyError(f"unknown nppes dataset_id: {dataset_id!r}")


# Map dataset_id -> target_table for the query engine.
def query_exposed_tables() -> Dict[str, str]:
    return {r["dataset_id"]: r["target_table"] for r in NPPES_DATASETS}
