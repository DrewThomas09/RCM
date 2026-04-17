"""One-click diligence package generator (Prompt 35).

``generate_package(packet)`` produces a zip containing 9 documents +
a manifest. Associates click "Export → Package" and get a
download-ready IC preparation bundle in 90 seconds.
"""
from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from ..analysis.packet import DealAnalysisPacket, PACKET_SCHEMA_VERSION

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_stem(packet: DealAnalysisPacket) -> str:
    import re
    return re.sub(
        r"[^A-Za-z0-9_.-]+", "_",
        str(packet.run_id or packet.deal_id or "package"),
    )


# ── Sub-renderers ─────────────────────────────────────────────────

def _exec_summary_html(packet: DealAnalysisPacket) -> str:
    """2-page executive summary: headline number, top risks,
    top opportunities, recommendation."""
    br = packet.ebitda_bridge
    total_impact = float(br.total_ebitda_impact or 0) if br else 0
    risks = packet.risk_flags[:3]
    risk_lines = "\n".join(
        f"<li><strong>{r.severity.value if hasattr(r.severity, 'value') else r.severity}</strong>: "
        f"{r.title or ''} — {r.detail or r.explanation or ''}</li>"
        for r in risks
    ) or "<li>No critical risks flagged.</li>"
    grade = getattr(packet.completeness, "grade", "?") or "?"
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{packet.deal_name or packet.deal_id} — Executive Summary</title>"
        "<style>body{font-family:sans-serif;max-width:800px;margin:0 auto;padding:24px;}"
        "h1{color:#1f4e78;} .num{font-family:monospace;} .risk{color:#ef4444;}</style></head>"
        f"<body><h1>{packet.deal_name or packet.deal_id}</h1>"
        f"<h2>Executive Summary</h2>"
        f"<p>Total EBITDA opportunity: <span class='num'>${total_impact/1e6:,.1f}M</span></p>"
        f"<p>Completeness grade: <strong>{grade}</strong></p>"
        f"<h3>Top Risks</h3><ul>{risk_lines}</ul>"
        f"<h3>Top Opportunities</h3>"
        f"<p>See the EBITDA Bridge in the attached workbook for lever-by-lever detail.</p>"
        f"<p><em>Generated {_utcnow_iso()[:10]} · RCM-MC v{PACKET_SCHEMA_VERSION}</em></p>"
        "</body></html>"
    )


def _data_request_md(packet: DealAnalysisPacket) -> str:
    """P0/P1 diligence questions as a numbered checklist."""
    lines = [
        f"# Data Request List — {packet.deal_name or packet.deal_id}",
        "",
        f"Generated {_utcnow_iso()[:10]}",
        "",
    ]
    for i, q in enumerate(packet.diligence_questions or [], start=1):
        pri = q.priority.value if hasattr(q.priority, "value") else str(q.priority)
        lines.append(f"{i}. [{pri}] {q.question}")
        if q.context:
            lines.append(f"   *Why it matters:* {q.context}")
        lines.append(f"   **Response:**  ")
        lines.append("")
    return "\n".join(lines)


def _risk_register_csv(packet: DealAnalysisPacket) -> str:
    """Severity-sorted risk register as CSV."""
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["severity", "category", "title", "detail",
                "trigger_metric", "ebitda_at_risk"])
    for rf in sorted(
        packet.risk_flags or [],
        key=lambda r: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}.get(
            r.severity.value if hasattr(r.severity, "value") else str(r.severity), 9,
        ),
    ):
        sev = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
        w.writerow([
            sev, rf.category or "", rf.title or "",
            rf.detail or rf.explanation or "",
            rf.trigger_metric or "",
            rf.ebitda_at_risk or "",
        ])
    return buf.getvalue()


def _comparables_csv(packet: DealAnalysisPacket) -> str:
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    peers = (packet.comparables.peers if packet.comparables else [])
    if not peers:
        w.writerow(["(no comparable set)"])
        return buf.getvalue()
    w.writerow(["id", "similarity_score"] + sorted(
        set().union(*(p.fields.keys() for p in peers if p.fields)),
    ))
    for p in peers:
        row = [p.id, f"{p.similarity_score:.3f}"]
        for col in sorted(
            set().union(*(pp.fields.keys() for pp in peers if pp.fields)),
        ):
            row.append(str(p.fields.get(col) or ""))
        w.writerow(row)
    return buf.getvalue()


def _assumptions_md(packet: DealAnalysisPacket) -> str:
    """Every assumption stated in plain English."""
    lines = [
        f"# Assumptions Log — {packet.deal_name or packet.deal_id}",
        "",
    ]
    vb = packet.value_bridge_result or {}
    assumptions = vb.get("assumptions") or {}
    if assumptions:
        lines.append("## Bridge Assumptions")
        for k, v in sorted(assumptions.items()):
            lines.append(f"- **{k}**: {v}")
        lines.append("")
    overrides = packet.analyst_overrides or {}
    if overrides:
        lines.append("## Analyst Overrides")
        for k, v in sorted(overrides.items()):
            lines.append(f"- **{k}**: {v}")
        lines.append("")
    lines.append(f"*Model version: {packet.model_version}*")
    return "\n".join(lines)


# ── Public entry ──────────────────────────────────────────────────

def generate_package(
    packet: DealAnalysisPacket,
    out_dir: Path,
    *,
    inputs_hash: str = "",
) -> Path:
    """Produce a zip with 9+ documents + manifest.

    Returns the zip path. Callers serve it as a download or persist
    it to disk.
    """
    from .packet_renderer import PacketRenderer

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    renderer = PacketRenderer(out_dir=out_dir)
    stem = _safe_stem(packet)
    zip_path = out_dir / f"{stem}_diligence_package.zip"

    manifest_entries: Dict[str, str] = {}

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        # 01: Executive Summary
        exec_html = _exec_summary_html(packet)
        z.writestr("01_Executive_Summary.html", exec_html)
        manifest_entries["01_Executive_Summary.html"] = "Executive summary"

        # 02: Diligence Memo
        memo_html = renderer.render_diligence_memo_html(
            packet, inputs_hash=inputs_hash,
        )
        z.writestr("02_Diligence_Memo.html", memo_html)
        manifest_entries["02_Diligence_Memo.html"] = "Full diligence memo"

        # 03: Analysis Workbook (xlsx)
        try:
            xlsx_path = renderer.render_deal_xlsx(
                packet, inputs_hash=inputs_hash,
            )
            z.write(xlsx_path, "03_Analysis_Workbook.xlsx")
            manifest_entries["03_Analysis_Workbook.xlsx"] = "Multi-sheet workbook"
        except Exception as exc:  # noqa: BLE001
            logger.debug("xlsx in package failed: %s", exc)

        # 04: IC Presentation (pptx)
        try:
            pptx_path = renderer.render_diligence_memo_pptx(
                packet, inputs_hash=inputs_hash,
            )
            z.write(pptx_path, "04_IC_Presentation.pptx")
            manifest_entries["04_IC_Presentation.pptx"] = "8-slide deck"
        except Exception as exc:  # noqa: BLE001
            logger.debug("pptx in package failed: %s", exc)

        # 05: Data Request List
        z.writestr("05_Data_Request_List.md", _data_request_md(packet))
        manifest_entries["05_Data_Request_List.md"] = "Diligence questions checklist"

        # 06: Risk Register
        z.writestr("06_Risk_Register.csv", _risk_register_csv(packet))
        manifest_entries["06_Risk_Register.csv"] = "Severity-sorted risk table"

        # 07: Comparable Analysis
        z.writestr("07_Comparable_Analysis.csv", _comparables_csv(packet))
        manifest_entries["07_Comparable_Analysis.csv"] = "Peer hospitals"

        # 08: Provenance Audit
        prov_json = json.dumps(
            packet.provenance.to_dict() if packet.provenance else {},
            indent=2, default=str,
        )
        z.writestr("08_Provenance_Audit.json", prov_json)
        manifest_entries["08_Provenance_Audit.json"] = "Full provenance graph"

        # 09: Assumptions Log
        z.writestr("09_Assumptions_Log.md", _assumptions_md(packet))
        manifest_entries["09_Assumptions_Log.md"] = "All assumptions in plain English"

        # Manifest
        manifest = {
            "deal_id": packet.deal_id,
            "deal_name": packet.deal_name or "",
            "run_id": packet.run_id or "",
            "packet_hash": inputs_hash,
            "generated_at": _utcnow_iso(),
            "model_version": packet.model_version or PACKET_SCHEMA_VERSION,
            "files": manifest_entries,
        }
        z.writestr("manifest.json", json.dumps(manifest, indent=2))

    return zip_path
