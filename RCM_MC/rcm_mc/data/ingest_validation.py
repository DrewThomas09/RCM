"""Back-of-pipe validation for public-data ingestion.

The *front* of the pipe (``release_watermark``) decides whether to load;
this is the *back* — the checks a loader runs after producing rows but
before trusting them, per ``SECOND_AGENT_BUILD_PROMPT.md`` Appendix A.
Four families, all stdlib, all pure (no DB, no network) so they are
trivially testable without downloads:

1. **Suppression-awareness.** CMS suppresses small cells (≤10 or ≤11
   depending on the file): the published value is a sentinel like ``*``
   or blank, which means "1–10 / unknown", NOT zero. The repo's loaders
   already map these to ``None`` (see ``cms_monthly_enrollment._to_int``).
   The validator's job is to catch the *regression* where a suppressed
   sentinel silently became ``0`` — a blank that reads as zero corrupts
   every downstream rate.

2. **Staging-to-target reconciliation.** The count we loaded must match
   the count the source manifest promised, within tolerance. A loader is
   not "done" until this passes — a silent partial load is worse than a
   loud failure.

3. **Sign convention.** HCRIS carries negative amounts with a sign
   convention; a column that should never be negative (e.g. bed count)
   going negative means a parse or column-mapping error.

4. **Format-drift detection.** The 2552-96 → 2552-10 form change moves
   worksheet/line/column codes. An observed ``(WKSHT_CD, LINE_NUM,
   CLMN_NUM)`` key absent from the maintained crosswalk must fail loudly
   rather than silently map to the wrong variable.

Callers either inspect the returned :class:`ValidationReport` or call
``raise_for_issues()`` to fail the load.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# Canonical suppression sentinels — the union of what the existing CMS
# loaders recognize (cms_monthly_enrollment._to_int, cms_ma_enrollment).
# A raw cell equal (case-insensitively, trimmed) to one of these means
# "suppressed / 1–10 / unknown" and must NOT be stored as 0.
SUPPRESSION_SENTINELS: Set[str] = {
    "*", ".", "", "(x)", "x", "n/a", "na", "suppressed", "redacted", "--",
}


class IngestValidationError(ValueError):
    """Raised by ``ValidationReport.raise_for_issues`` when a load fails
    validation. Carries the report for the caller's logs."""

    def __init__(self, report: "ValidationReport"):
        self.report = report
        super().__init__(report.summary())


@dataclass
class ValidationReport:
    source: str
    issues: List[str] = field(default_factory=list)
    checks_run: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.issues

    def add(self, issue: str) -> None:
        self.issues.append(issue)

    def ran(self, check: str) -> None:
        self.checks_run.append(check)

    def summary(self) -> str:
        if self.ok:
            return f"{self.source}: OK ({len(self.checks_run)} checks)"
        return f"{self.source}: {len(self.issues)} issue(s): " + "; ".join(
            self.issues
        )

    def raise_for_issues(self) -> "ValidationReport":
        if not self.ok:
            raise IngestValidationError(self)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "ok": self.ok,
            "issues": list(self.issues),
            "checks_run": list(self.checks_run),
        }


def is_suppressed(raw: Any) -> bool:
    """True if a raw cell value is a CMS suppression sentinel.

    ``None`` counts as suppressed (already-parsed missing). Numbers are
    never suppressed. String comparison is trimmed + case-insensitive.
    """
    if raw is None:
        return True
    if isinstance(raw, (int, float)):
        return False
    return str(raw).strip().lower() in SUPPRESSION_SENTINELS


# ── 1. Suppression-awareness ──────────────────────────────────────────

def validate_suppression(
    report: ValidationReport,
    records: Iterable[Dict[str, Any]],
    *,
    raw_field: str,
    parsed_field: str,
) -> ValidationReport:
    """Catch suppressed sentinels that were coerced to ``0``.

    For each record, if ``raw_field`` is a suppression sentinel then
    ``parsed_field`` must be ``None`` — never ``0`` (which would read as
    a real zero downstream). Records where the raw value is a real number
    are ignored.
    """
    report.ran("suppression")
    bad = 0
    for rec in records:
        if raw_field not in rec:
            continue
        if is_suppressed(rec.get(raw_field)) and rec.get(parsed_field) == 0:
            bad += 1
    if bad:
        report.add(
            f"suppression: {bad} record(s) have a suppressed {raw_field!r} "
            f"stored as 0 in {parsed_field!r} (blank is not zero)"
        )
    return report


# ── 2. Staging-to-target reconciliation ───────────────────────────────

def reconcile_counts(
    report: ValidationReport,
    *,
    loaded: int,
    expected: int,
    tolerance: float = 0.0,
) -> ValidationReport:
    """Loaded row count must match the source manifest within tolerance.

    ``tolerance`` is a fraction (0.0 = exact). A loader is not "done"
    until this passes; a silent partial load is the failure mode this
    guards against.
    """
    report.ran("reconciliation")
    if expected < 0:
        report.add(f"reconciliation: expected count {expected} is negative")
        return report
    allowed = expected * float(tolerance)
    if abs(loaded - expected) > allowed:
        report.add(
            f"reconciliation: loaded {loaded} rows but manifest expected "
            f"{expected} (tolerance {tolerance:.1%})"
        )
    return report


# ── 3. Sign convention ────────────────────────────────────────────────

def check_non_negative(
    report: ValidationReport,
    records: Iterable[Dict[str, Any]],
    *,
    fields: Iterable[str],
) -> ValidationReport:
    """Flag any of ``fields`` carrying a negative value.

    Use for columns that are structurally non-negative (bed counts, day
    counts). ``None`` is skipped (that's suppression's job). A negative
    here means a parse or column-mapping error, not a real datum.
    """
    field_list = list(fields)
    report.ran("sign")
    hits: Dict[str, int] = {}
    for rec in records:
        for f in field_list:
            v = rec.get(f)
            if isinstance(v, (int, float)) and v < 0:
                hits[f] = hits.get(f, 0) + 1
    for f, n in hits.items():
        report.add(f"sign: {n} negative value(s) in non-negative field {f!r}")
    return report


# ── 4. Format-drift detection ─────────────────────────────────────────

def detect_unknown_keys(
    report: ValidationReport,
    observed_keys: Iterable[Tuple[str, ...]],
    known_keys: Set[Tuple[str, ...]],
    *,
    sample: int = 5,
) -> ValidationReport:
    """Fail loudly on worksheet/line/column keys not in the crosswalk.

    ``observed_keys`` are the ``(WKSHT_CD, LINE_NUM, CLMN_NUM)`` tuples
    seen in a filing; ``known_keys`` is the maintained crosswalk's key
    set (covering both 2552-96 and 2552-10). Any observed key not in the
    crosswalk signals a form change — surface it rather than silently
    mapping to the wrong variable. Reports up to ``sample`` examples so
    the operator can extend the crosswalk.
    """
    report.ran("format_drift")
    unknown = sorted({tuple(k) for k in observed_keys} - set(known_keys))
    if unknown:
        shown = ", ".join(repr(k) for k in unknown[:sample])
        more = "" if len(unknown) <= sample else f" (+{len(unknown) - sample} more)"
        report.add(
            f"format_drift: {len(unknown)} unrecognized worksheet key(s) "
            f"not in crosswalk: {shown}{more}"
        )
    return report
