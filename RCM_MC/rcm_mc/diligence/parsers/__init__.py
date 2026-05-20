"""Parser adapter layer for healthcare EDI snapshots.

Public surface: the adapter contract + result types, the always-on
fallback adapter, and detection helpers. Library adapters (x12-python,
pyx12) register themselves when their backing package is importable.
See ``docs/healthcare-revenue-leakage-v2-plan.md`` §4 and
``docs/adr/healthcare-parser-selection.md``.
"""
from __future__ import annotations

from typing import Dict, List

from .base import (
    AdapterAvailability,
    Delimiters,
    FileDetectionResult,
    ParsedFileMetadata,
    ParsedTransactionSet,
    ParserAdapter,
    ValidationReport,
)
from .detection import detect_delimiters, detect_file
from .fallback_adapter import FallbackSegmentAdapter

__all__ = [
    "AdapterAvailability",
    "Delimiters",
    "FileDetectionResult",
    "ParsedFileMetadata",
    "ParsedTransactionSet",
    "ParserAdapter",
    "ValidationReport",
    "detect_delimiters",
    "detect_file",
    "FallbackSegmentAdapter",
    "available_adapters",
]


def available_adapters() -> List[ParserAdapter]:
    """Return instances of every adapter whose backing library is
    importable. The fallback is always present and always last so a
    primary library adapter wins ordering when one is available."""
    adapters: List[ParserAdapter] = []
    # Library adapters first (primary), guarded by import availability.
    try:
        from .x12_python_adapter import X12PythonAdapter  # noqa: F401

        adapters.append(X12PythonAdapter())
    except Exception:  # noqa: BLE001 — optional dep; fall back silently
        pass
    adapters.append(FallbackSegmentAdapter())
    return adapters


def adapter_availability() -> Dict[str, AdapterAvailability]:
    """Diagnostic: which adapters are usable in this environment."""
    out: Dict[str, AdapterAvailability] = {
        "fallback_segment": AdapterAvailability("fallback_segment", True),
    }
    try:
        import x12  # noqa: F401

        out["x12_python"] = AdapterAvailability("x12_python", True)
    except Exception as exc:  # noqa: BLE001
        out["x12_python"] = AdapterAvailability(
            "x12_python", False, f"x12-python not importable: {exc}")
    return out
