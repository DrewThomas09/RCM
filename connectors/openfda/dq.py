"""Data-quality checks for the openFDA slice.

Three families, matching the definition of done:

  1. **Row-count reconciliation** — ingested rows for an endpoint vs the
     live ``count=``/``meta.results.total`` for the same search. A large
     shortfall means a window was skipped or truncated (the connector
     logs truncation, so DQ surfaces it as a fail with the gap).
  2. **Null-key checks** — every canonical table's native id is
     non-null/non-empty (idempotent upsert depends on it).
  3. **NDC→RxCUI coverage** — percent of distinct drug NDCs resolved to
     an RxCUI, reported (not failed) because RxNorm may be deferred.

Each check returns a :class:`DqResult`; :func:`run_all` aggregates them.
The reconciliation check takes an injectable opener so it is testable
without a live endpoint.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .connector import OpenFdaConnector
from .endpoints import ENDPOINTS, EndpointSpec
from .tables import CANONICAL_TABLES, TABLES, OpenFdaStore
from .transport import Opener


@dataclass
class DqResult:
    name: str
    passed: bool
    severity: str            # "error" | "warn" | "info"
    detail: str
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DqReport:
    results: List[DqResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.passed for r in self.results if r.severity == "error")

    def add(self, r: DqResult) -> None:
        self.results.append(r)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "checks": [r.__dict__ for r in self.results],
            "summary": {
                "error_fails": sum(1 for r in self.results
                                   if not r.passed and r.severity == "error"),
                "warn_fails": sum(1 for r in self.results
                                  if not r.passed and r.severity == "warn"),
                "total": len(self.results),
            },
        }

    def to_markdown(self) -> str:
        """Render the report as a DQ_REPORT.md artifact (filesystem-as-memory).

        A human-readable companion to ``as_dict()`` so a partner can read
        the last DQ outcome straight from the working dir without re-running.
        """
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        s = self.as_dict()["summary"]
        lines = [
            "# openFDA connector — DQ report",
            "",
            f"_Generated {now} (UTC)._",
            "",
            f"**Overall: {'PASS' if self.ok else 'FAIL'}** "
            f"({s['error_fails']} error-fails, {s['warn_fails']} warn-fails, "
            f"{s['total']} checks)",
            "",
            "| Check | Severity | Result | Detail |",
            "|---|---|---|---|",
        ]
        for r in self.results:
            detail = r.detail.replace("|", "\\|")
            lines.append(
                f"| {r.name} | {r.severity} | {'pass' if r.passed else 'FAIL'} "
                f"| {detail} |")
        return "\n".join(lines) + "\n"


# ── individual checks ──────────────────────────────────────────────────
def null_key_check(store: OpenFdaStore) -> List[DqResult]:
    out: List[DqResult] = []
    for table in CANONICAL_TABLES:
        pk = TABLES[table].pk
        n = store.count(table, f"{pk} IS NULL OR {pk} = ''")
        out.append(DqResult(
            name=f"null_key:{table}",
            passed=(n == 0),
            severity="error",
            detail=f"{n} rows with null/empty {pk}",
            metrics={"null_keys": n, "pk": pk},
        ))
    return out


def ndc_rxcui_coverage(store: OpenFdaStore) -> DqResult:
    total = store.count("dim_drug_product", "ndc IS NOT NULL AND ndc <> ''")
    resolved = store.count(
        "dim_drug_product", "rxcui IS NOT NULL AND rxcui <> ''")
    pct = round(100.0 * resolved / total, 2) if total else 0.0
    # Reported, not failed: RxNorm resolution may legitimately be deferred.
    return DqResult(
        name="ndc_rxcui_coverage",
        passed=True,
        severity="info",
        detail=f"{resolved}/{total} NDCs resolved to RxCUI ({pct}%)",
        metrics={"total_ndc": total, "resolved": resolved, "coverage_pct": pct},
    )


def reconcile_counts(
    connector: OpenFdaConnector,
    store: OpenFdaStore,
    spec: EndpointSpec,
    *,
    search: str = "",
    tolerance_pct: float = 5.0,
    opener: Optional[Opener] = None,
) -> DqResult:
    """Compare ingested rows for an endpoint to its live total.

    ``search`` should match the slice that was ingested (e.g. a date
    window for an incremental). Default compares the whole endpoint.
    """
    live_total = connector.total_count(spec, search=search, opener=opener)
    ingested = store.count(spec.target_table, "source_endpoint = ?", (spec.key,))
    if live_total <= 0:
        passed = ingested == 0
        gap_pct = 0.0
    else:
        gap_pct = round(100.0 * abs(live_total - ingested) / live_total, 2)
        passed = gap_pct <= tolerance_pct
    return DqResult(
        name=f"reconcile:{spec.key}",
        passed=passed,
        severity="error",
        detail=(f"ingested {ingested} vs live {live_total} "
                f"(gap {gap_pct}%, tol {tolerance_pct}%)"),
        metrics={"ingested": ingested, "live_total": live_total,
                 "gap_pct": gap_pct, "tolerance_pct": tolerance_pct},
    )


def run_all(
    store: OpenFdaStore,
    *,
    connector: Optional[OpenFdaConnector] = None,
    reconcile: bool = False,
    opener: Optional[Opener] = None,
) -> DqReport:
    """Run the full DQ suite. ``reconcile=True`` adds the live-count
    reconciliation (needs a connector + reachable endpoint)."""
    report = DqReport()
    for r in null_key_check(store):
        report.add(r)
    report.add(ndc_rxcui_coverage(store))
    if reconcile and connector is not None:
        for spec in ENDPOINTS.values():
            try:
                report.add(reconcile_counts(connector, store, spec, opener=opener))
            except Exception as exc:  # a flaky endpoint must not abort DQ
                report.add(DqResult(
                    name=f"reconcile:{spec.key}", passed=False, severity="warn",
                    detail=f"reconcile error: {exc}", metrics={}))
    return report
