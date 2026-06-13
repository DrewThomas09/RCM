"""Declarative dataset registry for the RxNorm source.

Per the registry contract, every dataset is one declarative row —
``{dataset_id, connector, base_url, endpoint, default_params, refresh_cadence,
join_keys, target_table}`` — and adding a dataset is a registry row, not new
routing code. A uniform query layer (``query.query_dataset``) auto-exposes
anything declared here, mirroring the ``/v1/query/{dataset}`` contract.

All rows are tagged ``source="rxnorm"`` (the only rows this connector owns).
``base_url`` is the RxNav REST root; ``endpoint`` is the connector's logical
endpoint name (see :meth:`connector.RxNormConnector.fetch`), not the raw URL
path, so the connector owns URL construction.
"""
from __future__ import annotations

from typing import Any, Dict, List

SOURCE = "rxnorm"
BASE_URL = "https://rxnav.nlm.nih.gov/REST"

# refresh_cadence values follow the repo convention: monthly for the bulk
# concept universe (RxNorm ships monthly), weekly for NDC resolution (NDC
# directory churns faster), monthly for class grouping.
_ROWS: List[Dict[str, Any]] = [
    {
        "dataset_id": "rxnorm_concepts",
        "connector": "rxnorm",
        "source": SOURCE,
        "base_url": BASE_URL,
        "endpoint": "allconcepts",
        "default_params": {"tty": "IN+PIN+MIN+BN+SCD+SBD+SCDC+GPCK+BPCK"},
        "refresh_cadence": "monthly",
        "join_keys": ["rxcui"],
        "target_table": "dim_rxnorm_concept",
    },
    {
        "dataset_id": "rxnorm_ndc_crosswalk",
        "connector": "rxnorm",
        "source": SOURCE,
        "base_url": BASE_URL,
        "endpoint": "ndcs",
        "default_params": {},
        "refresh_cadence": "weekly",
        "join_keys": ["ndc_11", "rxcui"],
        "target_table": "xwalk_ndc_rxcui",
    },
    {
        "dataset_id": "rxnorm_related",
        "connector": "rxnorm",
        "source": SOURCE,
        "base_url": BASE_URL,
        "endpoint": "allrelated",
        "default_params": {},
        "refresh_cadence": "monthly",
        "join_keys": ["rxcui", "related_rxcui"],
        "target_table": "bridge_rxcui_related",
    },
    {
        "dataset_id": "rxnorm_drug_class",
        "connector": "rxnorm",
        "source": SOURCE,
        "base_url": BASE_URL,
        "endpoint": "rxclass",
        "default_params": {},
        "refresh_cadence": "monthly",
        "join_keys": ["rxcui", "class_id"],
        "target_table": "dim_drug_class",
    },
    {
        "dataset_id": "rxnorm_ndc_properties",
        "connector": "rxnorm",
        "source": SOURCE,
        "base_url": BASE_URL,
        "endpoint": "ndcproperties",
        "default_params": {},
        "refresh_cadence": "weekly",
        "join_keys": ["ndc_11"],
        "target_table": "dim_ndc_properties",
    },
]

_BY_ID = {r["dataset_id"]: r for r in _ROWS}
_BY_TABLE = {r["target_table"]: r for r in _ROWS}


def dataset_rows() -> List[Dict[str, Any]]:
    """All registry rows for this source (stable order)."""
    return [dict(r) for r in _ROWS]


def get(dataset_id: str) -> Dict[str, Any]:
    return dict(_BY_ID.get(dataset_id, {}))


def by_target_table(table: str) -> Dict[str, Any]:
    return dict(_BY_TABLE.get(table, {}))


def dataset_ids() -> List[str]:
    return [r["dataset_id"] for r in _ROWS]
