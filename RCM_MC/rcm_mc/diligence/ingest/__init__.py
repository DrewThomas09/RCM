"""Phase 1 — Ingestion & Normalization.

Public surface:

    from rcm_mc.diligence.ingest import (
        CanonicalClaim,
        CanonicalClaimsDataset,
        TransformationLog,
        ingest_dataset,
    )

``ingest_dataset(path)`` is the entry point every other module calls.
Everything else in this module is implementation detail.
"""
from __future__ import annotations

from .ccd import (
    CCD_SCHEMA_VERSION,
    CanonicalClaim,
    CanonicalClaimsDataset,
    ClaimStatus,
    PayerClass,
    SourceFormat,
    Transformation,
    TransformationLog,
)
from .ingester import ingest_dataset
from .normalize import parse_date, resolve_payer, validate_cpt, validate_icd
from .tuva_bridge import (
    TUVA_ELIGIBILITY_COLUMNS,
    TUVA_MEDICAL_CLAIM_COLUMNS,
    TUVA_PHARMACY_CLAIM_COLUMNS,
    ccd_to_tuva_input_layer_arrow,
    vendored_tuva_path,
    write_tuva_input_layer_duckdb,
)

__all__ = [
    "CCD_SCHEMA_VERSION",
    "CanonicalClaim",
    "CanonicalClaimsDataset",
    "ClaimStatus",
    "PayerClass",
    "SourceFormat",
    "TUVA_ELIGIBILITY_COLUMNS",
    "TUVA_MEDICAL_CLAIM_COLUMNS",
    "TUVA_PHARMACY_CLAIM_COLUMNS",
    "Transformation",
    "TransformationLog",
    "ccd_to_tuva_input_layer_arrow",
    "ingest_dataset",
    "parse_date",
    "resolve_payer",
    "validate_cpt",
    "validate_icd",
    "vendored_tuva_path",
    "write_tuva_input_layer_duckdb",
]
