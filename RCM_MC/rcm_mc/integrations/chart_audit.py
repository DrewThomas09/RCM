"""Chart audit vendor socket.

A chart audit samples a set of billed encounters, has a certified
coder re-code the documentation, and reports:

- **Under-coding** — provider billed a 99213 for a visit that
  documentation supports at 99214; the delta is lost revenue.
- **Over-coding** — provider billed 99215 for a visit that only
  supports 99213; the delta is compliance exposure (RAC / OIG).
- **No-change** — billed code is supported.

Vendor landscape (for context, no adapter imports here):

- Navigant, MedReview, Trust HCS (independent coding audit firms)
- nThrive, R1 RCM (bundled with broader RCM outsourcing)

This module defines the data contract and two adapters. The analyst's
default path is the :class:`ManualChartAuditAdapter`, which loads a
JSON file the analyst produced (or received from a vendor) and turns
it into the same :class:`ChartAuditReport` the rest of the platform
consumes. When a vendor HTTP integration ships, it will be a third
adapter that conforms to :class:`ChartAuditAdapter`.

Report shape is designed so the KPI engine can consume it directly —
the audit produces a ``net_reimbursement_delta_usd`` the EBITDA
bridge can treat as a coding-initiative lever.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import (
    Any, Dict, Iterable, List, Optional, Protocol, runtime_checkable,
)


# ── Data contract ──────────────────────────────────────────────────

@dataclass
class ChartAuditFinding:
    """One chart. Always names the claim being audited; the audited
    code / documented code delta is what drives the revenue number."""
    claim_id: str
    patient_id: Optional[str] = None
    service_date: Optional[str] = None        # ISO
    billed_code: str = ""                      # CPT originally billed
    audited_code: str = ""                     # CPT the auditor assigns
    billed_amount_usd: float = 0.0
    audited_amount_usd: float = 0.0
    direction: str = "NO_CHANGE"  # UNDERCODED | OVERCODED | NO_CHANGE
    reason: str = ""                           # auditor's note
    severity: str = "LOW"                      # LOW | MEDIUM | HIGH

    @property
    def delta_usd(self) -> float:
        """Signed delta from the deal's perspective. Positive on
        undercoding (upside), negative on overcoding (risk)."""
        return float(self.audited_amount_usd) - float(self.billed_amount_usd)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "patient_id": self.patient_id,
            "service_date": self.service_date,
            "billed_code": self.billed_code,
            "audited_code": self.audited_code,
            "billed_amount_usd": self.billed_amount_usd,
            "audited_amount_usd": self.audited_amount_usd,
            "direction": self.direction,
            "reason": self.reason,
            "severity": self.severity,
            "delta_usd": self.delta_usd,
        }


@dataclass
class ChartAuditJob:
    """What we asked the vendor to do."""
    job_id: str
    deal_id: Optional[str] = None
    engagement_id: Optional[str] = None
    sample_size: int = 0
    requested_at: str = ""                     # ISO
    vendor: str = "manual"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id, "deal_id": self.deal_id,
            "engagement_id": self.engagement_id,
            "sample_size": self.sample_size,
            "requested_at": self.requested_at,
            "vendor": self.vendor, "notes": self.notes,
        }


@dataclass
class ChartAuditReport:
    """Top-level container. Stored on disk as JSON; consumed by the
    KPI engine and the EBITDA bridge (coding-accuracy lever)."""
    job: ChartAuditJob
    findings: List[ChartAuditFinding] = field(default_factory=list)
    completed_at: Optional[str] = None
    status: str = "COMPLETED"                  # COMPLETED | IN_PROGRESS | FAILED

    @property
    def undercoded_findings(self) -> List[ChartAuditFinding]:
        return [f for f in self.findings if f.direction == "UNDERCODED"]

    @property
    def overcoded_findings(self) -> List[ChartAuditFinding]:
        return [f for f in self.findings if f.direction == "OVERCODED"]

    @property
    def no_change_findings(self) -> List[ChartAuditFinding]:
        return [f for f in self.findings if f.direction == "NO_CHANGE"]

    @property
    def net_reimbursement_delta_usd(self) -> float:
        """Signed total — the bridge-lever input. Positive means the
        audit found net under-coding (revenue upside); negative means
        net over-coding (compliance exposure)."""
        return float(sum(f.delta_usd for f in self.findings))

    @property
    def under_rate(self) -> float:
        """Fraction of audited charts that were under-coded."""
        if not self.findings:
            return 0.0
        return len(self.undercoded_findings) / len(self.findings)

    @property
    def over_rate(self) -> float:
        if not self.findings:
            return 0.0
        return len(self.overcoded_findings) / len(self.findings)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job": self.job.to_dict(),
            "completed_at": self.completed_at,
            "status": self.status,
            "findings": [f.to_dict() for f in self.findings],
            "net_reimbursement_delta_usd": self.net_reimbursement_delta_usd,
            "under_rate": self.under_rate,
            "over_rate": self.over_rate,
        }


# ── Adapter protocol ───────────────────────────────────────────────

@runtime_checkable
class ChartAuditAdapter(Protocol):
    """Every chart-audit backend must implement this protocol."""

    def submit(self, job: ChartAuditJob) -> str:
        """Submit a new audit job; return a vendor-scoped reference."""
        ...

    def poll(self, job_id: str) -> ChartAuditReport:
        """Return the current state of the job. Status may be
        IN_PROGRESS, COMPLETED, or FAILED."""
        ...


# ── Manual adapter (always offline) ────────────────────────────────

class ManualChartAuditAdapter:
    """Local-JSON adapter. The analyst (or an offline vendor) places
    a ``{job_id}.json`` file in ``root_dir``; this adapter reads and
    returns it.

    JSON shape matches :class:`ChartAuditReport.to_dict`. The adapter
    does NOT write unless :meth:`submit` is called — it is a
    read-mostly surface for an analyst workflow where the audit was
    produced by a third party."""

    def __init__(self, root_dir: Any):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        # Reject any character outside [A-Za-z0-9-_] up-front so path
        # traversal ("../"), absolute paths, and null bytes cannot
        # sneak through. Dots are disallowed to keep job_id tokens
        # flat; the ``.json`` suffix is added here, not in the input.
        if not job_id or any(
            not (c.isalnum() or c in "-_") for c in job_id
        ):
            raise ValueError(f"invalid job_id: {job_id!r}")
        return self.root_dir / f"{job_id}.json"

    def submit(self, job: ChartAuditJob) -> str:
        """Write a placeholder report (status=IN_PROGRESS) so the
        analyst can later drop in the findings and call :meth:`poll`."""
        stamp = datetime.now(timezone.utc).isoformat()
        if not job.requested_at:
            job.requested_at = stamp
        placeholder = ChartAuditReport(
            job=job, findings=[], completed_at=None,
            status="IN_PROGRESS",
        )
        self._path(job.job_id).write_text(
            json.dumps(placeholder.to_dict(), indent=2),
            encoding="utf-8",
        )
        return job.job_id

    def poll(self, job_id: str) -> ChartAuditReport:
        p = self._path(job_id)
        if not p.exists():
            raise FileNotFoundError(
                f"no manual chart-audit report at {p}. Submit the job "
                f"first, or drop the vendor JSON into that path."
            )
        return _report_from_dict(
            json.loads(p.read_text(encoding="utf-8"))
        )


# ── Stub vendor adapter (documents shape, refuses to fake) ─────────

class StubVendorChartAuditAdapter:
    """Shape-documenting stub. Methods raise ``NotImplementedError``
    with the exact HTTP call an implementer should make. This adapter
    exists so a reviewer can see the wire contract without grepping
    vendor documentation.

    Replace this class with a real client when a vendor is picked.
    Do NOT silently return fabricated numbers from a stub — partner
    trust collapses when "audit" data turns out to be placeholder."""

    ENDPOINT_BASE = "https://api.example-chart-audit-vendor.com/v1"

    def __init__(self, api_key: str, deal_id: Optional[str] = None):
        if not api_key:
            raise ValueError("api_key required for vendor integration")
        self.api_key = api_key
        self.deal_id = deal_id

    def submit(self, job: ChartAuditJob) -> str:
        raise NotImplementedError(
            "Stub vendor adapter: implement POST "
            f"{self.ENDPOINT_BASE}/audits with "
            "{sample_size, deal_id, engagement_id} and return the "
            "vendor-assigned job_id."
        )

    def poll(self, job_id: str) -> ChartAuditReport:
        raise NotImplementedError(
            f"Stub vendor adapter: implement GET "
            f"{self.ENDPOINT_BASE}/audits/{{job_id}} and parse the "
            f"response into ChartAuditReport."
        )


# ── Helpers ────────────────────────────────────────────────────────

def _report_from_dict(d: Dict[str, Any]) -> ChartAuditReport:
    job_d = d.get("job") or {}
    job = ChartAuditJob(
        job_id=str(job_d.get("job_id", "")),
        deal_id=job_d.get("deal_id"),
        engagement_id=job_d.get("engagement_id"),
        sample_size=int(job_d.get("sample_size", 0) or 0),
        requested_at=str(job_d.get("requested_at", "")),
        vendor=str(job_d.get("vendor", "manual")),
        notes=str(job_d.get("notes", "")),
    )
    findings: List[ChartAuditFinding] = []
    for f in d.get("findings") or ():
        findings.append(ChartAuditFinding(
            claim_id=str(f.get("claim_id", "")),
            patient_id=f.get("patient_id"),
            service_date=f.get("service_date"),
            billed_code=str(f.get("billed_code", "")),
            audited_code=str(f.get("audited_code", "")),
            billed_amount_usd=float(f.get("billed_amount_usd", 0.0) or 0.0),
            audited_amount_usd=float(f.get("audited_amount_usd", 0.0) or 0.0),
            direction=str(f.get("direction", "NO_CHANGE")),
            reason=str(f.get("reason", "")),
            severity=str(f.get("severity", "LOW")),
        ))
    return ChartAuditReport(
        job=job, findings=findings,
        completed_at=d.get("completed_at"),
        status=str(d.get("status", "COMPLETED")),
    )
