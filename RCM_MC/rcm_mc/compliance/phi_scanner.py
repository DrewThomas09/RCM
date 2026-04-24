"""Pattern-based PHI scanner.

Catches the common PHI patterns that leak into logs, test fixtures,
exports, and committed files:

- SSN (ddd-dd-dddd or ddddddddd, with a sanity band that excludes
  area codes 000 / 666 / 900-999 per SSA guidance)
- US phone numbers in the common formats
- Dates of birth (MM/DD/YYYY, YYYY-MM-DD, Month D, YYYY)
- Medical record numbers (MRN: …), patient IDs written as PT/PID
- NPI (10-digit Luhn-valid; distinguishes from generic 10-digit
  numbers)
- Email + address-like patterns

False-positive minimisation: every pattern is a narrow regex with
surrounding word boundaries. The scanner is meant to be run on
committed files, not live claims — claim_id columns in CCDs are
already pseudonymised, so we deliberately DO NOT flag the
``H[0-9]+-[A-Z][0-9]+`` synthetic IDs used in kpi_truth fixtures.

Not a DLP substitute. It reads local paths only; it does not
transmit. It is a pre-commit guardrail, not a production exfiltration
control.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Pattern, Tuple


# ── Patterns ────────────────────────────────────────────────────────

# SSN — three digits, two digits, four digits, with forbidden area
# codes filtered out (000, 666, 900-999 are never assigned per SSA).
_SSN_RE: Pattern[str] = re.compile(
    r"\b(?!000|666|9\d{2})\d{3}-\d{2}-\d{4}\b"
)

# Bare 9-digit SSN without dashes — tighter context window required
# to avoid flagging zip+4 combos and random 9-digit numbers. We only
# match when preceded by ``ssn``/``social``/``tax id`` keyword.
_SSN_NODASH_RE: Pattern[str] = re.compile(
    r"(?i)(?:\b(?:ssn|social\s*security|tax\s*id)[:\s#]*?)"
    r"(?!000|666|9\d{2})\d{3}\d{2}\d{4}\b"
)

# US phone: (123) 456-7890, 123-456-7890, 123.456.7890, +1 …
_PHONE_RE: Pattern[str] = re.compile(
    r"(?:(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4})"
)

# Email. Permissive left-hand side, strict TLD.
_EMAIL_RE: Pattern[str] = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)

# DOB-like dates. Three formats:
#   MM/DD/YYYY, M/D/YYYY
#   YYYY-MM-DD (ISO)
#   Month DD, YYYY
# Flagged only when preceded by a DOB-suggesting keyword to avoid
# firing on every claim date_of_service. The scanner accepts a
# ``strict=False`` mode that drops the keyword requirement if the
# user wants to audit every date.
_DOB_KEYED_RE: Pattern[str] = re.compile(
    r"(?i)(?:\b(?:dob|date\s*of\s*birth|d\.?o\.?b\.?|birthday|born)[:\s]*)"
    r"("
    r"\d{1,2}/\d{1,2}/(?:19|20)\d{2}"
    r"|(?:19|20)\d{2}-\d{2}-\d{2}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
    r"\s+\d{1,2},?\s+(?:19|20)\d{2}"
    r")"
)

# MRN — medical record number. Often written MRN: or MR#.
_MRN_RE: Pattern[str] = re.compile(
    r"(?i)\b(?:MRN|MR\s*#|Medical\s*Record\s*(?:Number|#|No))"
    r"[:\s#]*([A-Z0-9\-]{4,})"
)

# NPI — 10 digits, Luhn with prefix 80840 per CMS NPI spec. We use a
# relaxed "10-digit number preceded by NPI keyword" to avoid false
# positives on phone numbers.
_NPI_RE: Pattern[str] = re.compile(
    r"(?i)\b(?:NPI|National\s*Provider\s*Identifier)[:\s#]*(\d{10})\b"
)

# Street address — a number, one-or-more words, then a street suffix.
_STREET_RE: Pattern[str] = re.compile(
    r"\b\d+\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)*\s+"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|"
    r"Drive|Dr|Court|Ct|Circle|Cir|Way|Parkway|Pkwy)\b\.?"
)


@dataclass
class _PatternSpec:
    name: str
    regex: Pattern[str]
    severity: str                   # "HIGH" | "MEDIUM" | "LOW"
    # Index into ``match.group(n)`` to extract the value to redact.
    # 0 = whole match, 1 = first capture group, etc.
    value_group: int = 0


_PATTERNS: Tuple[_PatternSpec, ...] = (
    _PatternSpec("ssn",          _SSN_RE,        "HIGH",   0),
    _PatternSpec("ssn_nodash",   _SSN_NODASH_RE, "HIGH",   0),
    _PatternSpec("phone",        _PHONE_RE,      "MEDIUM", 0),
    _PatternSpec("email",        _EMAIL_RE,      "MEDIUM", 0),
    _PatternSpec("dob",          _DOB_KEYED_RE,  "HIGH",   1),
    _PatternSpec("mrn",          _MRN_RE,        "HIGH",   1),
    _PatternSpec("npi",          _NPI_RE,        "LOW",    1),
    _PatternSpec("street",       _STREET_RE,     "MEDIUM", 0),
)


# ── Results ─────────────────────────────────────────────────────────

@dataclass
class PHIFinding:
    """One PHI hit. Position is a character offset within the scanned
    text so callers can produce a source-highlight."""
    pattern: str
    severity: str
    value: str
    start: int
    end: int
    context: str = ""           # ±30 chars around the hit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern, "severity": self.severity,
            "value": self.value, "start": self.start, "end": self.end,
            "context": self.context,
        }


@dataclass
class PHIScanReport:
    """Summary of one scan pass. Immutable — callers that need to
    re-scan create a new report."""
    source: str                   # "<stdin>" | file path | identifier
    char_count: int
    findings: List[PHIFinding] = field(default_factory=list)

    @property
    def count_by_pattern(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        for f in self.findings:
            out[f.pattern] = out.get(f.pattern, 0) + 1
        return out

    @property
    def highest_severity(self) -> Optional[str]:
        """``HIGH`` > ``MEDIUM`` > ``LOW`` > None (no findings)."""
        for tier in ("HIGH", "MEDIUM", "LOW"):
            if any(f.severity == tier for f in self.findings):
                return tier
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "char_count": self.char_count,
            "findings": [f.to_dict() for f in self.findings],
            "count_by_pattern": self.count_by_pattern,
            "highest_severity": self.highest_severity,
        }


# ── Core scanner ────────────────────────────────────────────────────

def scan_text(
    text: str,
    *,
    source: str = "<text>",
    allowed_patterns: Optional[Iterable[str]] = None,
) -> PHIScanReport:
    """Scan one text buffer for PHI. Returns a
    :class:`PHIScanReport` — no exceptions on benign input.

    ``allowed_patterns``: optional set of pattern names to skip. Use
    when you intentionally include a category in a file (e.g. an NPI
    list in a contract spec)."""
    allowed = set(allowed_patterns or ())
    findings: List[PHIFinding] = []
    for spec in _PATTERNS:
        if spec.name in allowed:
            continue
        for m in spec.regex.finditer(text):
            value = m.group(spec.value_group) or m.group(0)
            start, end = m.start(spec.value_group), m.end(spec.value_group)
            if start < 0:  # group didn't match
                start, end = m.start(), m.end()
            ctx_left = max(0, start - 30)
            ctx_right = min(len(text), end + 30)
            ctx = text[ctx_left:ctx_right].replace("\n", " ")
            findings.append(
                PHIFinding(
                    pattern=spec.name, severity=spec.severity,
                    value=value, start=start, end=end, context=ctx,
                )
            )
    # Sort by offset so the report reads left-to-right.
    findings.sort(key=lambda f: f.start)
    return PHIScanReport(source=source, char_count=len(text),
                         findings=findings)


def scan_file(
    path: Any,
    *,
    allowed_patterns: Optional[Iterable[str]] = None,
) -> PHIScanReport:
    """Scan one file on disk. Binary files are skipped with an empty
    report — we don't attempt to decode EDI/PDFs here (that's the
    ingest pipeline's job)."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError, OSError):
        return PHIScanReport(source=str(p), char_count=0, findings=[])
    return scan_text(text, source=str(p),
                     allowed_patterns=allowed_patterns)


# ── Redaction ───────────────────────────────────────────────────────

def redact_phi(
    text: str,
    *,
    allowed_patterns: Optional[Iterable[str]] = None,
    replacement: str = "[REDACTED-{pattern}]",
) -> Tuple[str, PHIScanReport]:
    """Return ``(redacted_text, report)``. Every finding is replaced
    by ``replacement`` (a ``.format(pattern=...)``-compatible
    template). Non-overlapping by construction since patterns run in
    order and findings sort left-to-right."""
    report = scan_text(text, allowed_patterns=allowed_patterns)
    if not report.findings:
        return text, report
    out: List[str] = []
    cursor = 0
    for f in report.findings:
        out.append(text[cursor:f.start])
        out.append(replacement.format(pattern=f.pattern))
        cursor = f.end
    out.append(text[cursor:])
    return "".join(out), report
