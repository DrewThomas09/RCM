"""DQReport — the diligence-layer analog of DealAnalysisPacket.

Every signal the ingestion layer wants to tell a partner flows through
this object: what files we saw, what landed in raw, how the Tuva
input-layer mapping went, what Tuva's built-in DQ tests said, which
downstream diligence analyses we can compute vs cannot, and the full
provenance stamp.

Same invariants as ``rcm_mc.analysis.packet.DealAnalysisPacket``:

- Every section has a status enum; a section being ``FAIL`` doesn't
  void the whole report — partners still want to see which *other*
  sections are fine.
- JSON round-trip. The on-disk artefact is the truth; the HTML is a
  rendering, not a source.
- Content hash is a function of inputs + connector version + tuva
  version. Running twice against the same fixture must produce byte-
  identical JSON modulo the excluded ``wall_time`` fields — call
  :meth:`content_hash` to get the stable hash.
"""
from __future__ import annotations

import hashlib
import html
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple


# ── Enums (mirror rcm_mc.analysis.packet.SectionStatus) ──────────────

class DQSectionStatus(str, Enum):
    OK = "OK"
    WARN = "WARN"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"


class DQSeverity(str, Enum):
    """Per-finding severity. Critical is reserved for "analysis
    coverage is degraded to the point of non-use" — stronger than a
    dbt ``error`` on a single column because it's a rollup assertion
    about the downstream portfolio of analyses."""
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# ── Section dataclasses ──────────────────────────────────────────────

@dataclass
class FileInventoryEntry:
    path: str
    size_bytes: int
    format: str
    row_count: int
    columns_detected: List[str]
    columns_dropped: List[str]
    encoding: str
    status: str
    note: str = ""


@dataclass
class RawTableSummary:
    table: str
    schema: str
    row_count: int
    load_duration_seconds: float
    column_null_rates: Dict[str, float] = field(default_factory=dict)


@dataclass
class ConnectorColumnMapping:
    """One row per Tuva input-layer column."""
    tuva_table: str           # medical_claim | pharmacy_claim | eligibility
    tuva_column: str
    source_field: str         # "" if synthesised (cast null as …)
    transformation: str       # terse SQL-like description
    null_rate: float = 0.0
    rows_dropped: int = 0
    rationale: str = ""       # pulled from the SQL -- RATIONALE: comment


@dataclass
class TuvaDQFinding:
    """Full passthrough of one Tuva built-in DQ test."""
    test_name: str
    unique_id: str
    status: str
    severity: str
    failures: int
    tags: List[str] = field(default_factory=list)
    sample_failing_rows: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AnalysisCoverageRow:
    """Per diligence analysis, whether inputs are sufficient."""
    analysis: str             # e.g. "cohort_liquidation"
    computable: bool
    required_fields: List[str]
    missing_fields: List[str]
    note: str = ""


@dataclass
class Provenance:
    """Deterministic inputs-hash + metadata. Same shape as the
    provenance field on DealAnalysisPacket — by intent; partners
    will see both surfaces and expect them to rhyme."""
    connector: str = "seekingchartis"
    connector_version: str = ""
    tuva_version: str = ""
    dbt_version: str = ""
    adapter_backend: str = ""
    input_file_hashes: Dict[str, str] = field(default_factory=dict)
    run_id: str = ""
    wall_time_utc: str = ""   # excluded from content_hash by design


# ── Section wrapper ──────────────────────────────────────────────────

@dataclass
class Section:
    status: DQSectionStatus = DQSectionStatus.OK
    severity: DQSeverity = DQSeverity.INFO
    message: str = ""
    rows: List[Any] = field(default_factory=list)


# ── DQReport ─────────────────────────────────────────────────────────

@dataclass
class DQReport:
    """The canonical ingestion result object.

    Partners read this to decide whether a seller's data can feed the
    downstream Phase 0.B analyses. Nothing in the diligence layer
    renders independently of it — same rule as DealAnalysisPacket.
    """
    source_inventory: Section = field(default_factory=Section)
    raw_load_summary: Section = field(default_factory=Section)
    connector_mapping: Section = field(default_factory=Section)
    tuva_dq_results: Section = field(default_factory=Section)
    analysis_coverage: Section = field(default_factory=Section)
    provenance: Provenance = field(default_factory=Provenance)

    # Top-level aggregate the HTML renderer uses for the header
    overall_status: DQSectionStatus = DQSectionStatus.OK
    overall_message: str = ""

    # ------- serialisation -------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return _json_safe(asdict(self))

    def to_json(self, *, indent: int = 2, sort_keys: bool = True) -> str:
        return json.dumps(
            self.to_dict(), indent=indent, sort_keys=sort_keys,
            default=_json_default,
        )

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "DQReport":
        def _section(key: str) -> Section:
            s = d.get(key) or {}
            return Section(
                status=DQSectionStatus(s.get("status", "OK")),
                severity=DQSeverity(s.get("severity", "INFO")),
                message=s.get("message", ""),
                rows=list(s.get("rows", []) or []),
            )

        prov_d = d.get("provenance") or {}
        prov = Provenance(
            connector=prov_d.get("connector", "seekingchartis"),
            connector_version=prov_d.get("connector_version", ""),
            tuva_version=prov_d.get("tuva_version", ""),
            dbt_version=prov_d.get("dbt_version", ""),
            adapter_backend=prov_d.get("adapter_backend", ""),
            input_file_hashes=dict(prov_d.get("input_file_hashes") or {}),
            run_id=prov_d.get("run_id", ""),
            wall_time_utc=prov_d.get("wall_time_utc", ""),
        )
        return cls(
            source_inventory=_section("source_inventory"),
            raw_load_summary=_section("raw_load_summary"),
            connector_mapping=_section("connector_mapping"),
            tuva_dq_results=_section("tuva_dq_results"),
            analysis_coverage=_section("analysis_coverage"),
            provenance=prov,
            overall_status=DQSectionStatus(d.get("overall_status", "OK")),
            overall_message=d.get("overall_message", ""),
        )

    @classmethod
    def from_json(cls, s: str) -> "DQReport":
        return cls.from_dict(json.loads(s))

    # ------- hash + rendering ----------------------------------------

    def content_hash(self) -> str:
        """Deterministic SHA256 over canonical JSON, excluding
        wall-time-ish fields. Same invariant as
        ``rcm_mc.analysis.packet.hash_inputs``.
        """
        d = self.to_dict()
        # Strip fields that vary between identical-input runs:
        #   - wall_time_utc (clock)
        #   - any fields we've tagged with the "__volatile__" key
        prov = d.get("provenance") or {}
        prov.pop("wall_time_utc", None)
        prov.pop("run_id", None)  # run_id is time-prefixed by default
        d["provenance"] = prov
        # Also strip per-model dbt invocation times / paths that the
        # tuva passthrough might carry.
        for section_key in ("tuva_dq_results",):
            rows = (d.get(section_key) or {}).get("rows") or []
            for r in rows:
                r.pop("duration_seconds", None)
                r.pop("execution_time", None)
        payload = json.dumps(d, sort_keys=True, default=_json_default)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def render_html(self) -> str:
        """Single-file HTML, dark theme, no JS. Matches the chartis
        palette (``_chartis_kit``) so it doesn't look like a transplant
        when opened next to the main app.
        """
        return _render_dq_html(self)

    def write(self, output_dir: Path | str) -> Tuple[Path, Path]:
        """Write ``dq_report.json`` + ``dq_report.html`` to
        ``output_dir``. Returns the two file paths."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        jp = out / "dq_report.json"
        hp = out / "dq_report.html"
        jp.write_text(self.to_json(), encoding="utf-8")
        hp.write_text(self.render_html(), encoding="utf-8")
        return jp, hp

    # ------- aggregation helpers -------------------------------------

    def recompute_overall(self) -> None:
        """Roll up section statuses into ``overall_status``.

        Precedence: FAIL > WARN > SKIPPED > OK. CRITICAL severity in
        any section promotes the overall to FAIL even if the section
        status itself is WARN — this is how ``mess_scenario_5`` surfaces
        its analysis-coverage-degraded signal.
        """
        sections = [
            self.source_inventory, self.raw_load_summary,
            self.connector_mapping, self.tuva_dq_results,
            self.analysis_coverage,
        ]
        any_fail = any(s.status == DQSectionStatus.FAIL for s in sections)
        any_warn = any(s.status == DQSectionStatus.WARN for s in sections)
        any_crit = any(s.severity == DQSeverity.CRITICAL for s in sections)
        if any_fail or any_crit:
            self.overall_status = DQSectionStatus.FAIL
        elif any_warn:
            self.overall_status = DQSectionStatus.WARN
        else:
            self.overall_status = DQSectionStatus.OK
        if not self.overall_message:
            self.overall_message = _default_overall_message(self.overall_status)


# ── JSON helpers ─────────────────────────────────────────────────────

def _json_safe(v: Any) -> Any:
    """Same contract as :func:`rcm_mc.analysis.packet._json_safe` — we
    keep this copy local so the diligence layer doesn't import from
    the core package. Minor scope: we only handle primitives, enums,
    dates, dicts, lists, dataclasses."""
    if v is None or isinstance(v, (bool, int, str)):
        return v
    if isinstance(v, float):
        if v != v or v in (float("inf"), float("-inf")):
            return None
        return v
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, dict):
        return {str(k): _json_safe(val) for k, val in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_json_safe(x) for x in v]
    if is_dataclass(v):
        return _json_safe(asdict(v))
    return str(v)


def _json_default(o: Any) -> Any:
    if isinstance(o, Enum):
        return o.value
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    if is_dataclass(o):
        return asdict(o)
    raise TypeError(f"not JSON-serialisable: {type(o).__name__}")


def _default_overall_message(status: DQSectionStatus) -> str:
    return {
        DQSectionStatus.OK: "Ingestion complete. No blocking data quality issues.",
        DQSectionStatus.WARN: "Ingestion complete with warnings. Review DQ report before running downstream analyses.",
        DQSectionStatus.FAIL: "Ingestion completed with FAIL-severity findings. Downstream analyses may be invalid.",
        DQSectionStatus.SKIPPED: "Ingestion skipped (dry-run or no input).",
    }[status]


# ── HTML renderer ────────────────────────────────────────────────────

# Palette mirrors rcm_mc/ui/_chartis_kit.py::P so a partner opening the
# dq_report.html next to the Corpus Intelligence workbench sees a
# coherent surface. Kept inline here (not imported) to preserve the
# zero-coupling rule with the core package.
_P = {
    "bg": "#0a0e17", "panel": "#111827", "panel_alt": "#0f172a",
    "border": "#1e293b", "border_dim": "#0f1a2e",
    "text": "#e2e8f0", "text_dim": "#94a3b8", "text_faint": "#64748b",
    "accent": "#3b82f6",
    "positive": "#10b981", "negative": "#ef4444",
    "warning": "#f59e0b", "critical": "#dc2626",
}
_MONO = "'JetBrains Mono', 'SF Mono', 'Fira Code', 'Consolas', monospace"
_SANS = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"


def _render_dq_html(report: DQReport) -> str:
    d = report.to_dict()
    parts: List[str] = []
    parts.append(_HTML_HEAD)
    parts.append(_header_html(report))
    parts.append(_section_html(
        "Source Inventory",
        "One row per raw file: what loaded, what was dropped.",
        report.source_inventory,
        _render_inventory_table,
    ))
    parts.append(_section_html(
        "Raw Load Summary",
        "Tables landed in the raw_data schema.",
        report.raw_load_summary,
        _render_raw_load_table,
    ))
    parts.append(_section_html(
        "Connector Mapping",
        "Tuva Input Layer column mapping, transformation, and null rate.",
        report.connector_mapping,
        _render_mapping_table,
    ))
    parts.append(_section_html(
        "Tuva DQ Results",
        "Pass-through of Tuva's built-in DQ tests.",
        report.tuva_dq_results,
        _render_tuva_dq_table,
    ))
    parts.append(_section_html(
        "Analysis Coverage",
        "Which downstream diligence analyses can be computed with the ingested data.",
        report.analysis_coverage,
        _render_coverage_table,
    ))
    parts.append(_provenance_footer(report.provenance))
    parts.append("</div></body></html>")
    return "\n".join(parts)


_CSS_TEMPLATE = """
html,body{background:%(bg)s;color:%(text)s;font-family:%(sans)s;margin:0;padding:0;}
*{box-sizing:border-box;}
.wrap{max-width:1180px;margin:0 auto;padding:24px;}
h1{font-size:18px;letter-spacing:.5px;margin:0 0 6px 0;color:%(text)s;font-weight:600;}
h2{font-size:13px;letter-spacing:.75px;text-transform:uppercase;color:%(text_dim)s;margin:28px 0 6px 0;font-weight:600;}
.sub{color:%(text_faint)s;font-size:11px;margin-bottom:8px;}
.panel{background:%(panel)s;border:1px solid %(border)s;border-radius:4px;padding:14px 16px;margin-bottom:4px;}
.num,.mono{font-family:%(mono)s;font-variant-numeric:tabular-nums;}
table{border-collapse:collapse;width:100%%;font-size:11px;}
th{text-align:left;color:%(text_dim)s;border-bottom:1px solid %(border)s;padding:6px 8px;font-weight:600;letter-spacing:.3px;text-transform:uppercase;font-size:10px;}
td{padding:6px 8px;border-bottom:1px solid %(border_dim)s;vertical-align:top;}
tr:nth-child(even) td{background:%(panel_alt)s;}
.badge{display:inline-block;padding:2px 8px;border-radius:3px;font-size:10px;font-family:%(mono)s;letter-spacing:.5px;font-weight:600;}
.badge-ok{background:rgba(16,185,129,.12);color:%(positive)s;}
.badge-warn{background:rgba(245,158,11,.12);color:%(warning)s;}
.badge-fail{background:rgba(239,68,68,.12);color:%(negative)s;}
.badge-critical{background:rgba(220,38,38,.18);color:%(critical)s;}
.badge-skipped{background:rgba(100,116,139,.12);color:%(text_faint)s;}
.footer{margin-top:32px;padding-top:16px;border-top:1px solid %(border)s;color:%(text_faint)s;font-size:10px;font-family:%(mono)s;}
"""

_CSS = _CSS_TEMPLATE % {**_P, "sans": _SANS, "mono": _MONO}

_HTML_HEAD = (
    "<!doctype html><html lang=\"en\"><head>"
    "<meta charset=\"utf-8\">"
    "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
    "<title>SeekingChartis — Diligence Data Quality Report</title>"
    "<style>" + _CSS + "</style>"
    "</head><body><div class=\"wrap\">"
)


def _header_html(report: DQReport) -> str:
    d = report.to_dict()
    run_id = html.escape(report.provenance.run_id or "")
    overall = _status_badge(report.overall_status.value)
    msg = html.escape(report.overall_message or "")
    return (
        f"<h1>SeekingChartis — Diligence DQ Report {overall}</h1>"
        f"<div class=\"sub mono\">run_id: {run_id}</div>"
        f"<div class=\"panel\"><div style=\"color:{_P['text_dim']};font-size:12px;\">{msg}</div></div>"
    )


def _section_html(
    title: str,
    subtitle: str,
    section: Section,
    render_rows: Any,
) -> str:
    badge = _status_badge(section.status.value)
    sev = _severity_badge(section.severity.value)
    msg = html.escape(section.message or "")
    body = render_rows(section.rows) if section.rows else (
        "<div class=\"sub\" style=\"padding:8px 0;\">no rows</div>"
    )
    return (
        f"<h2>{html.escape(title)} {badge} {sev}</h2>"
        f"<div class=\"sub\">{html.escape(subtitle)}</div>"
        f"<div class=\"panel\">"
        f"{('<div class=\"sub\" style=\"margin-bottom:8px;\">'+msg+'</div>') if msg else ''}"
        f"{body}"
        f"</div>"
    )


def _status_badge(value: str) -> str:
    cls = {
        "OK": "badge-ok", "WARN": "badge-warn",
        "FAIL": "badge-fail", "SKIPPED": "badge-skipped",
    }.get(value, "badge-skipped")
    return f"<span class=\"badge {cls}\">{html.escape(value)}</span>"


def _severity_badge(value: str) -> str:
    if value == "INFO":
        return ""
    cls = {
        "WARN": "badge-warn", "ERROR": "badge-fail", "CRITICAL": "badge-critical",
    }.get(value, "badge-skipped")
    return f"<span class=\"badge {cls}\">{html.escape(value)}</span>"


def _render_inventory_table(rows: List[Dict[str, Any]]) -> str:
    hdr = "<tr><th>Path</th><th>Format</th><th>Bytes</th><th class=\"num\">Rows</th>" \
          "<th>Encoding</th><th>Status</th><th>Note</th></tr>"
    body = []
    for r in rows:
        body.append(
            "<tr>"
            f"<td class=\"mono\">{html.escape(str(r.get('path','')))}</td>"
            f"<td class=\"mono\">{html.escape(str(r.get('format','')))}</td>"
            f"<td class=\"num\">{_fmt_int(r.get('size_bytes'))}</td>"
            f"<td class=\"num\">{_fmt_int(r.get('row_count'))}</td>"
            f"<td class=\"mono\">{html.escape(str(r.get('encoding','')))}</td>"
            f"<td>{_status_badge(str(r.get('status','OK')))}</td>"
            f"<td>{html.escape(str(r.get('note','')))}</td>"
            "</tr>"
        )
    return f"<table>{hdr}{''.join(body)}</table>"


def _render_raw_load_table(rows: List[Dict[str, Any]]) -> str:
    hdr = "<tr><th>Table</th><th class=\"num\">Rows</th><th class=\"num\">Cols</th>" \
          "<th class=\"num\">Max NULL %</th><th class=\"num\">Load s</th></tr>"
    body = []
    for r in rows:
        nrates = r.get("column_null_rates") or {}
        max_null = max(nrates.values()) if nrates else 0.0
        body.append(
            "<tr>"
            f"<td class=\"mono\">{html.escape(str(r.get('schema','raw_data')))}."
            f"{html.escape(str(r.get('table','')))}</td>"
            f"<td class=\"num\">{_fmt_int(r.get('row_count'))}</td>"
            f"<td class=\"num\">{len(nrates)}</td>"
            f"<td class=\"num\">{max_null*100:.1f}%</td>"
            f"<td class=\"num\">{float(r.get('load_duration_seconds',0) or 0):.2f}</td>"
            "</tr>"
        )
    return f"<table>{hdr}{''.join(body)}</table>"


def _render_mapping_table(rows: List[Dict[str, Any]]) -> str:
    hdr = "<tr><th>Tuva Table</th><th>Tuva Column</th><th>Source Field</th>" \
          "<th>Transformation</th><th class=\"num\">NULL %</th><th>Rationale</th></tr>"
    body = []
    for r in rows:
        body.append(
            "<tr>"
            f"<td class=\"mono\">{html.escape(str(r.get('tuva_table','')))}</td>"
            f"<td class=\"mono\">{html.escape(str(r.get('tuva_column','')))}</td>"
            f"<td class=\"mono\">{html.escape(str(r.get('source_field','')))}</td>"
            f"<td class=\"mono\">{html.escape(str(r.get('transformation','')))}</td>"
            f"<td class=\"num\">{float(r.get('null_rate',0) or 0)*100:.1f}%</td>"
            f"<td>{html.escape(str(r.get('rationale','')))}</td>"
            "</tr>"
        )
    return f"<table>{hdr}{''.join(body)}</table>"


def _render_tuva_dq_table(rows: List[Dict[str, Any]]) -> str:
    hdr = "<tr><th>Test</th><th>Severity</th><th>Status</th>" \
          "<th class=\"num\">Failing Rows</th><th>Tags</th></tr>"
    body = []
    for r in rows:
        body.append(
            "<tr>"
            f"<td class=\"mono\" style=\"max-width:400px;overflow:hidden;text-overflow:ellipsis;\">"
            f"{html.escape(str(r.get('test_name','')))}</td>"
            f"<td>{_severity_badge(str(r.get('severity','INFO')).upper())}</td>"
            f"<td>{_status_badge(_map_dbt_status(str(r.get('status',''))))}</td>"
            f"<td class=\"num\">{_fmt_int(r.get('failures'))}</td>"
            f"<td class=\"mono\" style=\"font-size:10px;color:{_P['text_dim']};\">"
            f"{html.escape(', '.join((r.get('tags') or [])[:4]))}</td>"
            "</tr>"
        )
    return f"<table>{hdr}{''.join(body)}</table>"


def _render_coverage_table(rows: List[Dict[str, Any]]) -> str:
    hdr = "<tr><th>Analysis</th><th>Computable</th><th>Missing Fields</th><th>Note</th></tr>"
    body = []
    for r in rows:
        comp = "OK" if r.get("computable") else "FAIL"
        missing = ", ".join(r.get("missing_fields") or []) or "—"
        body.append(
            "<tr>"
            f"<td class=\"mono\">{html.escape(str(r.get('analysis','')))}</td>"
            f"<td>{_status_badge(comp)}</td>"
            f"<td class=\"mono\" style=\"font-size:10px;color:{_P['text_dim']};\">"
            f"{html.escape(missing)}</td>"
            f"<td style=\"font-size:11px;\">{html.escape(str(r.get('note','')))}</td>"
            "</tr>"
        )
    return f"<table>{hdr}{''.join(body)}</table>"


def _provenance_footer(prov: Provenance) -> str:
    return (
        "<div class=\"footer\">"
        f"connector={html.escape(prov.connector)} "
        f"connector_version={html.escape(prov.connector_version)} "
        f"tuva_version={html.escape(prov.tuva_version)} "
        f"dbt_version={html.escape(prov.dbt_version)} "
        f"backend={html.escape(prov.adapter_backend)} "
        f"run_id={html.escape(prov.run_id)} "
        f"input_files={len(prov.input_file_hashes)} "
        f"wall_time_utc={html.escape(prov.wall_time_utc)}"
        "</div>"
    )


def _map_dbt_status(s: str) -> str:
    return {"pass": "OK", "fail": "FAIL", "warn": "WARN",
            "error": "FAIL", "skipped": "SKIPPED"}.get(s.lower(), s.upper() or "OK")


def _fmt_int(v: Any) -> str:
    try:
        return f"{int(v):,}"
    except (TypeError, ValueError):
        return "—"
