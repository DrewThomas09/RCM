"""Contract digitization vendor socket.

Takes a payer contract (PDF, DOCX, scanned image) and returns a
structured :class:`ContractSchedule` the re-pricer consumes. The
expensive part — OCR on scanned contracts, hierarchy detection on
bundled amendments, table extraction from rate schedules — is the
vendor's job. This module defines the contract + two adapters.

Vendor landscape (for context):

- HealthGorilla, ScribeRx (healthcare-specific contract OCR)
- Fusion5, SoftwareAG (general-purpose contract AI)
- Internal analyst workflow → manual JSON

Both the chart-audit and contract-digitization sockets share the
same philosophy: ``ManualAdapter`` is the default, always works, and
the ``StubVendorAdapter`` documents the wire shape for a future
HTTP-client implementation rather than silently faking output.

Output :class:`ContractSchedule` is the same class the re-pricer
module already exports, so the downstream consumer doesn't change
when a vendor integration replaces the manual workflow.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any, Dict, List, Optional, Protocol, runtime_checkable,
)

from ..diligence.benchmarks.contract_repricer import (
    ContractRate, ContractSchedule,
)


# ── Data contract ──────────────────────────────────────────────────

@dataclass
class ContractDigitizationJob:
    """One contract digitization request."""
    job_id: str
    source_filename: str
    deal_id: Optional[str] = None
    engagement_id: Optional[str] = None
    payer_name: Optional[str] = None          # often on the cover page
    effective_date: Optional[str] = None      # ISO; if known
    requested_at: str = ""
    vendor: str = "manual"
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_filename": self.source_filename,
            "deal_id": self.deal_id,
            "engagement_id": self.engagement_id,
            "payer_name": self.payer_name,
            "effective_date": self.effective_date,
            "requested_at": self.requested_at,
            "vendor": self.vendor,
            "notes": self.notes,
        }


@dataclass
class ContractExtraction:
    """Structured fields the vendor (or analyst) extracts. Maps to
    the re-pricer's :class:`ContractSchedule` via :meth:`to_schedule`.

    ``rate_rows`` is a list of dicts — one per (payer_class, CPT)
    rule — with keys matching :class:`ContractRate` field names.
    Schedule-level bookkeeping (payer_name, effective_date,
    termination_date) is kept here for display / audit purposes and
    does NOT flow through to :class:`ContractSchedule`, which is a
    behavioural (pricing) object. Withholds, stop-loss, carve-outs
    live on individual rows because the re-pricer models them per-
    rate."""
    payer_name: str
    effective_date: Optional[str] = None       # ISO
    termination_date: Optional[str] = None     # ISO
    # Rate schedule rows. Each row accepts ContractRate fields:
    #   payer_class, cpt_code,
    #   allowed_amount_usd OR allowed_pct_of_charge,
    #   is_carve_out, withhold_pct,
    #   stop_loss_threshold_usd, stop_loss_rate_pct_of_charge, note.
    rate_rows: List[Dict[str, Any]] = field(default_factory=list)
    default_carve_out_rate_pct: float = 0.50

    def to_schedule(self) -> ContractSchedule:
        """Map the extraction to the canonical re-pricer schedule.
        Skips rows without a ``cpt_code`` and without a numeric rate
        (and not marked as carve_out). Silently drops unparseable
        rows rather than raising — the extraction quality is a
        vendor-level concern surfaced on the report."""
        rates: List[ContractRate] = []
        for row in self.rate_rows:
            cpt = str(row.get("cpt_code") or "").strip()
            payer_class = str(row.get("payer_class") or "").strip()
            if not cpt or not payer_class:
                continue
            is_carve = bool(row.get("is_carve_out", False))
            allowed = row.get("allowed_amount_usd")
            pct = row.get("allowed_pct_of_charge")
            if not is_carve and allowed is None and pct is None:
                continue  # unparseable row; don't raise
            try:
                rates.append(ContractRate(
                    payer_class=payer_class,
                    cpt_code=cpt,
                    allowed_amount_usd=(
                        float(allowed) if allowed is not None else None
                    ),
                    allowed_pct_of_charge=(
                        float(pct) if pct is not None else None
                    ),
                    is_carve_out=is_carve,
                    withhold_pct=float(row.get("withhold_pct", 0.0) or 0.0),
                    stop_loss_threshold_usd=(
                        float(row["stop_loss_threshold_usd"])
                        if row.get("stop_loss_threshold_usd") is not None
                        else None
                    ),
                    stop_loss_rate_pct_of_charge=(
                        float(row["stop_loss_rate_pct_of_charge"])
                        if row.get("stop_loss_rate_pct_of_charge") is not None
                        else None
                    ),
                    note=str(row.get("note") or ""),
                ))
            except (ValueError, TypeError):
                continue
        return ContractSchedule(
            rates=rates,
            default_carve_out_rate_pct=self.default_carve_out_rate_pct,
            name=self.payer_name or "schedule",
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "payer_name": self.payer_name,
            "effective_date": self.effective_date,
            "termination_date": self.termination_date,
            "rate_rows": list(self.rate_rows),
            "default_carve_out_rate_pct": self.default_carve_out_rate_pct,
        }


@dataclass
class ContractDigitizationReport:
    """Vendor/analyst-produced output for a single contract."""
    job: ContractDigitizationJob
    extraction: Optional[ContractExtraction] = None
    completed_at: Optional[str] = None
    status: str = "COMPLETED"                  # COMPLETED | IN_PROGRESS | FAILED
    confidence_score: Optional[float] = None   # 0..1 vendor-self-score
    unparseable_sections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job": self.job.to_dict(),
            "extraction": (self.extraction.to_dict()
                           if self.extraction is not None else None),
            "completed_at": self.completed_at,
            "status": self.status,
            "confidence_score": self.confidence_score,
            "unparseable_sections": list(self.unparseable_sections),
        }


# ── Adapter protocol ───────────────────────────────────────────────

@runtime_checkable
class ContractDigitizationAdapter(Protocol):
    def submit(self, job: ContractDigitizationJob) -> str: ...

    def poll(self, job_id: str) -> ContractDigitizationReport: ...


# ── Manual adapter ─────────────────────────────────────────────────

class ManualContractDigitizationAdapter:
    """Local-JSON adapter. The analyst reads the contract, fills in
    the rate schedule, and drops the JSON in ``root_dir``. Mirrors
    :class:`ManualChartAuditAdapter`."""

    def __init__(self, root_dir: Any):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_id: str) -> Path:
        if not job_id or any(
            not (c.isalnum() or c in "-_") for c in job_id
        ):
            raise ValueError(f"invalid job_id: {job_id!r}")
        return self.root_dir / f"{job_id}.json"

    def submit(self, job: ContractDigitizationJob) -> str:
        if not job.requested_at:
            job.requested_at = datetime.now(timezone.utc).isoformat()
        placeholder = ContractDigitizationReport(
            job=job, extraction=None, completed_at=None,
            status="IN_PROGRESS",
        )
        self._path(job.job_id).write_text(
            json.dumps(placeholder.to_dict(), indent=2),
            encoding="utf-8",
        )
        return job.job_id

    def poll(self, job_id: str) -> ContractDigitizationReport:
        p = self._path(job_id)
        if not p.exists():
            raise FileNotFoundError(
                f"no manual contract-digitization report at {p}."
            )
        return _report_from_dict(
            json.loads(p.read_text(encoding="utf-8"))
        )


# ── Stub vendor adapter ────────────────────────────────────────────

class StubVendorContractDigitizationAdapter:
    """Shape-documenting stub. Raises on remote-fetch; exists so a
    reviewer can see what a vendor integration would look like
    without having to read the vendor's docs."""

    ENDPOINT_BASE = "https://api.example-contract-vendor.com/v1"

    def __init__(self, api_key: str, deal_id: Optional[str] = None):
        if not api_key:
            raise ValueError("api_key required for vendor integration")
        self.api_key = api_key
        self.deal_id = deal_id

    def submit(self, job: ContractDigitizationJob) -> str:
        raise NotImplementedError(
            "Stub vendor adapter: implement POST "
            f"{self.ENDPOINT_BASE}/contracts with the source document "
            "(multipart) and return the vendor-assigned job_id."
        )

    def poll(self, job_id: str) -> ContractDigitizationReport:
        raise NotImplementedError(
            f"Stub vendor adapter: implement GET "
            f"{self.ENDPOINT_BASE}/contracts/{{job_id}} and map the "
            f"response into ContractDigitizationReport."
        )


# ── Helpers ────────────────────────────────────────────────────────

def _report_from_dict(d: Dict[str, Any]) -> ContractDigitizationReport:
    job_d = d.get("job") or {}
    job = ContractDigitizationJob(
        job_id=str(job_d.get("job_id", "")),
        source_filename=str(job_d.get("source_filename", "")),
        deal_id=job_d.get("deal_id"),
        engagement_id=job_d.get("engagement_id"),
        payer_name=job_d.get("payer_name"),
        effective_date=job_d.get("effective_date"),
        requested_at=str(job_d.get("requested_at", "")),
        vendor=str(job_d.get("vendor", "manual")),
        notes=str(job_d.get("notes", "")),
    )
    ext_d = d.get("extraction")
    extraction: Optional[ContractExtraction] = None
    if ext_d:
        extraction = ContractExtraction(
            payer_name=str(ext_d.get("payer_name", "")),
            effective_date=ext_d.get("effective_date"),
            termination_date=ext_d.get("termination_date"),
            rate_rows=list(ext_d.get("rate_rows") or ()),
            default_carve_out_rate_pct=float(
                ext_d.get("default_carve_out_rate_pct", 0.50) or 0.50
            ),
        )
    return ContractDigitizationReport(
        job=job, extraction=extraction,
        completed_at=d.get("completed_at"),
        status=str(d.get("status", "COMPLETED")),
        confidence_score=d.get("confidence_score"),
        unparseable_sections=list(d.get("unparseable_sections") or ()),
    )
