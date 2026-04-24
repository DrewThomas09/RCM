"""Data quality layer — report dataclass, HTML renderer, rules,
Tuva-output translator."""
from __future__ import annotations

from .report import (
    AnalysisCoverageRow,
    ConnectorColumnMapping,
    DQReport,
    DQSectionStatus,
    DQSeverity,
    FileInventoryEntry,
    Provenance,
    RawTableSummary,
    Section,
    TuvaDQFinding,
)
from .rules import RuleFinding, run_all_rules
from .tuva_bridge import (
    build_analysis_coverage_rows,
    build_connector_mapping_rows,
    build_raw_load_rows,
    fold_tuva_results,
)

__all__ = [
    "AnalysisCoverageRow",
    "ConnectorColumnMapping",
    "DQReport",
    "DQSectionStatus",
    "DQSeverity",
    "FileInventoryEntry",
    "Provenance",
    "RawTableSummary",
    "RuleFinding",
    "Section",
    "TuvaDQFinding",
    "build_analysis_coverage_rows",
    "build_connector_mapping_rows",
    "build_raw_load_rows",
    "fold_tuva_results",
    "run_all_rules",
]
