"""Parser evaluation harness.

Runs every *available* parser adapter over a set of EDI fixtures and
produces a comparison report. Adapters whose backing library is not
installed are skipped (recorded as unavailable) rather than failing the
run, so the harness is meaningful in a minimal environment (fallback
only) and richer where x12-python/pyx12 are installed.

Feeds ``docs/adr/healthcare-parser-selection.md``.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from . import adapter_availability, available_adapters


@dataclass
class AdapterFixtureResult:
    adapter: str
    fixture: str
    detected_types: List[str] = field(default_factory=list)
    is_valid: bool = False
    transaction_sets: int = 0
    claims_extracted: int = 0
    parse_error: str = ""
    runtime_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return vars(self)


@dataclass
class HarnessReport:
    availability: Dict[str, Dict[str, Any]]
    results: List[AdapterFixtureResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "availability": self.availability,
            "results": [r.to_dict() for r in self.results],
        }


def run_harness(fixture_dir: Path | str) -> HarnessReport:
    fixtures = sorted(Path(fixture_dir).glob("*.edi"))
    adapters = available_adapters()
    results: List[AdapterFixtureResult] = []
    for adapter in adapters:
        for fx in fixtures:
            r = AdapterFixtureResult(adapter=adapter.name, fixture=fx.name)
            t0 = time.perf_counter()
            try:
                det = adapter.detect(fx)
                r.detected_types = list(det.detected_transaction_types)
                rep = adapter.validate(fx)
                r.is_valid = rep.is_valid
                sets = adapter.parse(fx)
                r.transaction_sets = len(sets)
                r.claims_extracted = sum(len(s.parsed_payload) for s in sets)
            except Exception as exc:  # noqa: BLE001 — harness records, never raises
                r.parse_error = f"{type(exc).__name__}: {exc}"
            r.runtime_ms = round((time.perf_counter() - t0) * 1000, 3)
            results.append(r)
    avail = {k: vars(v) for k, v in adapter_availability().items()}
    return HarnessReport(availability=avail, results=results)
