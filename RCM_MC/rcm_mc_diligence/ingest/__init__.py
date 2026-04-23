"""Ingestion layer — file loader, warehouse adapter, dbt connector, pipeline.

Kept intentionally minimal at the subpackage level: ``pipeline`` is
imported via the module path so its transitive dependency on
``..dq.rules`` doesn't cause a circular import when ``..dq`` is
loading.
"""
from __future__ import annotations

from .connector import (
    CONNECTOR_ROOT,
    CONNECTOR_VERSION,
    DbtRunResult,
    DbtTestResult,
    run_connector,
)
from .file_loader import (
    RAW_SCHEMA,
    FileLoadSummary,
    LoaderResult,
    load_directory,
)
from .warehouse import (
    DuckDBAdapter,
    LoadResult,
    PostgresAdapter,
    SnowflakeAdapter,
    TableRef,
    WarehouseAdapter,
    warehouse_from_name,
)

__all__ = [
    "CONNECTOR_ROOT",
    "CONNECTOR_VERSION",
    "DbtRunResult",
    "DbtTestResult",
    "DuckDBAdapter",
    "FileLoadSummary",
    "LoadResult",
    "LoaderResult",
    "PostgresAdapter",
    "RAW_SCHEMA",
    "SnowflakeAdapter",
    "TableRef",
    "WarehouseAdapter",
    "load_directory",
    "run_connector",
    "warehouse_from_name",
]
