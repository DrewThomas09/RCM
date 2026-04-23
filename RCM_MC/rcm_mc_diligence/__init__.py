"""rcm_mc_diligence — Tuva-wrapped diligence ingestion foundation.

Phase 0.A substrate for the SeekingChartis diligence layer. This package
is strictly additive to ``rcm_mc``: it imports nothing from it and vice
versa. Shared state (config, DB files, CLI entry points) is deliberately
separate.

Public surface:

- :class:`DQReport` — the canonical result object every ingestion run
  produces. Same role in this layer that ``DealAnalysisPacket`` plays in
  the core package.
- :func:`run_ingest` — top-level pipeline entry point. Takes a fixture
  name or a directory path, a warehouse adapter, and an output dir;
  returns a populated :class:`DQReport` and writes artifacts.
- :class:`WarehouseAdapter` + :class:`DuckDBAdapter` — the only way to
  touch a database. Snowflake/Postgres are scaffolded stubs for Phase
  0.B.

See ``rcm_mc_diligence/SESSION_LOG.md`` for what shipped and
``rcm_mc_diligence/PHASE_0B_NOTES.md`` for the punch list of deferred
work.
"""
from __future__ import annotations

from .dq.report import DQReport, DQSectionStatus, DQSeverity
from .ingest.pipeline import run_ingest
from .ingest.warehouse import (
    DuckDBAdapter,
    PostgresAdapter,
    SnowflakeAdapter,
    WarehouseAdapter,
)

__all__ = [
    "DQReport",
    "DQSectionStatus",
    "DQSeverity",
    "DuckDBAdapter",
    "PostgresAdapter",
    "SnowflakeAdapter",
    "WarehouseAdapter",
    "run_ingest",
]

__version__ = "0.1.0"
