"""VDR / Diligence Request List Tracker.

Virtual data room and diligence request tracker for an active deal:
workstream, request status, document completeness, follow-up queue,
critical-path items, and Q&A log.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class DDRequest:
    request_id: str
    workstream: str
    category: str
    request: str
    status: str
    priority: str
    requested_date: str
    response_date: str
    days_outstanding: int
    completeness_pct: float


@dataclass
class WorkstreamSummary:
    workstream: str
    total_requests: int
    complete: int
    in_progress: int
    outstanding: int
    overdue: int
    completeness_pct: float


@dataclass
class QAItem:
    qa_id: str
    topic: str
    seller_response_quality: str
    answered_within_days: int
    follow_up_required: bool
    materiality: str


@dataclass
class DocumentSection:
    section: str
    documents_uploaded: int
    total_expected: int
    completeness_pct: float
    last_updated: str
    seller_notes: str


@dataclass
class CriticalPath:
    item: str
    owner: str
    dependency: str
    needed_by: str
    current_status: str
    risk_to_close: str


@dataclass
class MaterialityFlag:
    finding: str
    workstream: str
    materiality: str
    spa_impact: str
    disposition: str


@dataclass
class VDRResult:
    deal_name: str
    days_since_vdr_open: int
    total_requests: int
    completion_pct: float
    overdue_count: int
    material_findings_count: int
    requests: List[DDRequest]
    workstreams: List[WorkstreamSummary]
    qa_log: List[QAItem]
    documents: List[DocumentSection]
    critical_path: List[CriticalPath]
    materiality: List[MaterialityFlag]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_requests() -> List[DDRequest]:
    return [
        DDRequest("DR-001", "Financial", "QoE", "3-year audited financial statements",
                  "complete", "critical", "2026-02-15", "2026-02-18", 0, 1.0),
        DDRequest("DR-002", "Financial", "QoE", "TTM detailed P&L by segment",
                  "complete", "critical", "2026-02-15", "2026-02-20", 0, 1.0),
        DDRequest("DR-003", "Financial", "Working Capital", "Working capital bridge + 3-year history",
                  "complete", "critical", "2026-02-15", "2026-02-22", 0, 1.0),
        DDRequest("DR-004", "Commercial", "Revenue", "Top 20 payer contracts (redacted)",
                  "complete", "critical", "2026-02-20", "2026-03-05", 0, 1.0),
        DDRequest("DR-005", "Commercial", "Revenue", "Provider productivity data (last 3 years)",
                  "complete", "critical", "2026-02-20", "2026-03-08", 0, 1.0),
        DDRequest("DR-006", "Commercial", "Market", "Competitive landscape analysis",
                  "complete", "standard", "2026-02-22", "2026-03-10", 0, 1.0),
        DDRequest("DR-007", "Tax", "Federal", "Federal tax returns (5 years)",
                  "complete", "critical", "2026-02-25", "2026-03-12", 0, 1.0),
        DDRequest("DR-008", "Tax", "State", "State tax returns by state (5 years)",
                  "in progress", "high", "2026-02-25", "2026-04-15", 21, 0.72),
        DDRequest("DR-009", "Legal", "Contracts", "Material contracts (>$1M annual)",
                  "complete", "critical", "2026-03-01", "2026-03-22", 0, 1.0),
        DDRequest("DR-010", "Legal", "Litigation", "Pending litigation schedule + complaint copies",
                  "in progress", "critical", "2026-03-01", "2026-04-18", 14, 0.85),
        DDRequest("DR-011", "Legal", "Compliance", "Healthcare regulatory compliance audit reports",
                  "in progress", "high", "2026-03-05", "2026-04-15", 15, 0.88),
        DDRequest("DR-012", "Regulatory", "Healthcare", "OIG / DOJ / CMS open inquiries or complaints",
                  "complete", "critical", "2026-03-05", "2026-03-18", 0, 1.0),
        DDRequest("DR-013", "Regulatory", "State", "State Medicaid audit history (3 years)",
                  "complete", "high", "2026-03-05", "2026-03-22", 0, 1.0),
        DDRequest("DR-014", "IT / Cyber", "Infrastructure", "IT/EHR architecture diagram + inventory",
                  "in progress", "high", "2026-03-10", "2026-04-15", 12, 0.82),
        DDRequest("DR-015", "IT / Cyber", "Security", "SOC 2 Type II report / HITRUST certification",
                  "complete", "critical", "2026-03-10", "2026-03-25", 0, 1.0),
        DDRequest("DR-016", "IT / Cyber", "Security", "Incident/breach history (5 years)",
                  "overdue", "critical", "2026-03-10", "", 30, 0.0),
        DDRequest("DR-017", "HR", "Employment", "Employment agreements (top 50 employees)",
                  "in progress", "high", "2026-03-15", "2026-04-15", 10, 0.78),
        DDRequest("DR-018", "HR", "Benefits", "Employee benefits plan documents",
                  "complete", "standard", "2026-03-15", "2026-03-28", 0, 1.0),
        DDRequest("DR-019", "Clinical", "Quality", "Clinical quality metrics (HEDIS, Stars)",
                  "complete", "high", "2026-03-18", "2026-04-02", 0, 1.0),
        DDRequest("DR-020", "Clinical", "Safety", "Patient safety / adverse event history",
                  "in progress", "critical", "2026-03-18", "2026-04-15", 12, 0.88),
        DDRequest("DR-021", "Insurance", "Coverage", "Insurance policies (malpractice, GL, D&O, cyber)",
                  "complete", "high", "2026-03-20", "2026-04-05", 0, 1.0),
        DDRequest("DR-022", "Insurance", "Claims", "Malpractice claims history (5 years)",
                  "complete", "critical", "2026-03-20", "2026-04-02", 0, 1.0),
        DDRequest("DR-023", "Environmental", "Real Estate", "Phase I environmental studies",
                  "overdue", "medium", "2026-03-22", "", 26, 0.0),
        DDRequest("DR-024", "Environmental", "Real Estate", "Lease schedules + original docs",
                  "in progress", "high", "2026-03-22", "2026-04-15", 8, 0.92),
        DDRequest("DR-025", "Deal", "Structure", "Proposed deal structure + capitalization",
                  "complete", "critical", "2026-03-25", "2026-04-02", 0, 1.0),
    ]


def _build_workstreams(requests: List[DDRequest]) -> List[WorkstreamSummary]:
    buckets: dict = {}
    for r in requests:
        buckets.setdefault(r.workstream, []).append(r)
    rows = []
    for ws, rs in buckets.items():
        total = len(rs)
        complete = sum(1 for r in rs if r.status == "complete")
        in_prog = sum(1 for r in rs if r.status == "in progress")
        outst = sum(1 for r in rs if r.status != "complete")
        overdue = sum(1 for r in rs if r.status == "overdue")
        comp_pct = sum(r.completeness_pct for r in rs) / total if total else 0
        rows.append(WorkstreamSummary(
            workstream=ws, total_requests=total, complete=complete,
            in_progress=in_prog, outstanding=outst, overdue=overdue,
            completeness_pct=round(comp_pct, 4),
        ))
    return sorted(rows, key=lambda w: w.total_requests, reverse=True)


def _build_qa() -> List[QAItem]:
    return [
        QAItem("QA-001", "BCBS renewal dynamics", "thorough", 2, False, "material"),
        QAItem("QA-002", "Locum MD agreements", "partial", 5, True, "material"),
        QAItem("QA-003", "EHR migration timing", "partial", 4, True, "medium"),
        QAItem("QA-004", "Q3 2025 revenue shortfall explanation", "thorough", 1, False, "high"),
        QAItem("QA-005", "Out-of-network billing exposure", "partial", 3, True, "high"),
        QAItem("QA-006", "Key MD retention agreement status", "thorough", 1, False, "critical"),
        QAItem("QA-007", "OIG inquiry 2024 — background details", "partial", 4, True, "medium"),
        QAItem("QA-008", "Management adjustments in QoE", "thorough", 2, False, "material"),
        QAItem("QA-009", "DOL investigation — any open matters?", "deflected", 6, True, "medium"),
        QAItem("QA-010", "Real estate ownership structure", "thorough", 1, False, "medium"),
        QAItem("QA-011", "340B program status", "partial", 3, True, "high"),
        QAItem("QA-012", "Cyber incident Feb 2024 details", "partial", 4, True, "critical"),
    ]


def _build_documents() -> List[DocumentSection]:
    return [
        DocumentSection("1.0 Corporate / Organizational", 85, 92, 0.924, "2026-04-12", "org chart + entity map complete"),
        DocumentSection("2.0 Financial", 145, 155, 0.935, "2026-04-14", "QoE 3-year + TTM uploaded"),
        DocumentSection("3.0 Commercial / Revenue", 118, 125, 0.944, "2026-04-10", "payer contracts + pricing schedules"),
        DocumentSection("4.0 Operations / Clinical", 92, 108, 0.852, "2026-04-12", "clinical protocols + QA metrics"),
        DocumentSection("5.0 Legal / Regulatory", 145, 168, 0.863, "2026-04-14", "contracts + litigation schedules"),
        DocumentSection("6.0 Tax", 52, 65, 0.800, "2026-04-15", "federal + state pending"),
        DocumentSection("7.0 IT / Cyber", 68, 88, 0.773, "2026-04-14", "SOC 2 + incident history pending"),
        DocumentSection("8.0 HR / People", 78, 92, 0.848, "2026-04-12", "employment + benefits"),
        DocumentSection("9.0 Real Estate / Facilities", 42, 52, 0.808, "2026-04-14", "lease schedules + environmental"),
        DocumentSection("10.0 Insurance", 35, 42, 0.833, "2026-04-12", "policies + claims history"),
        DocumentSection("11.0 Management Presentations", 28, 35, 0.800, "2026-04-08", "ops review + growth plan"),
        DocumentSection("12.0 Deal Structure / SPA", 22, 30, 0.733, "2026-04-15", "structure memo + cap table"),
    ]


def _build_critical_path() -> List[CriticalPath]:
    return [
        CriticalPath("Cyber incident history (DR-016)", "CIO (seller)", "None (independent)",
                     "2026-04-25", "overdue", "high - blocks cyber DD completion"),
        CriticalPath("Phase I environmental (DR-023)", "Facilities (seller)", "None",
                     "2026-04-22", "overdue", "medium - standard findings expected"),
        CriticalPath("State tax returns (DR-008)", "Tax advisor (seller)", "DR-007 done",
                     "2026-04-22", "in progress", "medium - 72% complete"),
        CriticalPath("Litigation detail (DR-010)", "General Counsel (seller)", "None",
                     "2026-04-25", "in progress", "high - complaint copies still outstanding"),
        CriticalPath("IT architecture (DR-014)", "CIO (seller)", "None",
                     "2026-04-25", "in progress", "medium - EHR diagram outstanding"),
        CriticalPath("Key MD employment (DR-017)", "HR + Legal (seller)", "DR-001",
                     "2026-04-28", "in progress", "high - top-tier MDs still negotiating rollover"),
        CriticalPath("Compliance audit (DR-011)", "Compliance Officer", "None",
                     "2026-04-28", "in progress", "medium - most years complete"),
        CriticalPath("Management presentation (4/25)", "CEO + CFO (seller)", "All DR items ideally",
                     "2026-04-25", "scheduled", "low - key date locked"),
        CriticalPath("SPA first draft", "Buyer Counsel", "DR-025 + structure agreed",
                     "2026-04-30", "in progress", "critical - drives close timeline"),
        CriticalPath("Confirmatory QoE", "QoE Advisor", "Final close-out data",
                     "2026-05-15", "pre-final", "medium - final 2-4 week window"),
    ]


def _build_materiality() -> List[MaterialityFlag]:
    return [
        MaterialityFlag("BCBS payer concentration 22% — renewal 2027",
                        "Commercial", "material", "Price protection + 2nd payer development clause", "disclosed, mitigated"),
        MaterialityFlag("Locum MD classification: 6 workers may warrant W-2",
                        "HR / Legal", "material", "Pre-close conversion + indemnification", "in remediation"),
        MaterialityFlag("Cyber incident Feb 2024 — insufficient disclosure detail",
                        "IT/Cyber", "critical", "Further DD required; R&W insurance exclusion possible", "open"),
        MaterialityFlag("OIG 2024 inquiry — closed with no action",
                        "Regulatory", "medium", "Disclosed in SPA", "resolved"),
        MaterialityFlag("EHR end-of-life requires 2027 migration (+$2.5M)",
                        "IT", "material", "Budget reserve + seller contribution", "disclosed"),
        MaterialityFlag("3 pending malpractice — all insured",
                        "Legal", "low", "Standard; within insurance limits", "resolved"),
        MaterialityFlag("Q3 2025 revenue variance — one-time concessions",
                        "Financial", "medium", "QoE normalization accepted", "resolved"),
        MaterialityFlag("Key MD rollover — 2 of 4 top MDs not yet committed",
                        "HR", "critical", "Close condition; 24-month minimum hold", "in negotiation"),
        MaterialityFlag("Pharmacy 340B program status unclear",
                        "Regulatory", "high", "Need formal HRSA letter", "open"),
        MaterialityFlag("Stark Law safe harbor compliance review",
                        "Legal", "medium", "Stark opinion from top-4 firm", "in progress"),
    ]


def compute_vdr_tracker() -> VDRResult:
    corpus = _load_corpus()

    requests = _build_requests()
    workstreams = _build_workstreams(requests)
    qa = _build_qa()
    documents = _build_documents()
    critical = _build_critical_path()
    materiality = _build_materiality()

    total = len(requests)
    comp_pct = sum(r.completeness_pct for r in requests) / total if total else 0
    overdue = sum(1 for r in requests if r.status == "overdue")
    material_count = sum(1 for m in materiality if m.materiality in ("critical", "material"))

    return VDRResult(
        deal_name="Project Azalea — GI Network SE",
        days_since_vdr_open=62,
        total_requests=total,
        completion_pct=round(comp_pct, 4),
        overdue_count=overdue,
        material_findings_count=material_count,
        requests=requests,
        workstreams=workstreams,
        qa_log=qa,
        documents=documents,
        critical_path=critical,
        materiality=materiality,
        corpus_deal_count=len(corpus),
    )
