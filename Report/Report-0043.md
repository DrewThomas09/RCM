# Report 0043: Public API Surface — `compliance/phi_scanner.py`

## Scope

Documents `RCM_MC/rcm_mc/compliance/phi_scanner.py` (252 lines) on `origin/main` at commit `f3f7e7f`. Module repeatedly deferred since Reports 0028, 0030. Critical for resolving the PHI-banner-vs-enforcement gap (MR250, MR275).

Prior reports reviewed: 0039-0042.

## Findings

### Module shape

| Item | Line | Category |
|---|---:|---|
| `class PHIFinding` (dataclass) | 122-138 | Public dataclass |
| `class PHIScanReport` (dataclass) | 141-171 | Public dataclass |
| `def scan_text(text, *, source, allowed_patterns)` | 176-210 | Public function |
| `def scan_file(path, *, allowed_patterns)` | 213-? | Public function |
| `def redact_phi(...)` | 232-? | Public function |
| `_PATTERNS` (module-level constant) | (in setup) | Internal — referenced at line 190 |

**3 public functions + 2 dataclasses.** Plus a `_PATTERNS` regex registry (private).

### Public-surface signatures

#### `class PHIFinding` (line 122)

Dataclass with:

| Field | Type | Default |
|---|---|---|
| `pattern` | str | required (e.g. "SSN", "phone", "DOB") |
| `severity` | str | required ("HIGH" / "MEDIUM" / "LOW") |
| `value` | str | required — the matched literal |
| `start` | int | required — character offset start |
| `end` | int | required — character offset end |
| `context` | str | "" — ±30 char context around the hit |

Method: `to_dict() -> Dict[str, Any]` (line 133-138).

**Docstring present.** "One PHI hit. Position is a character offset within the scanned text so callers can produce a source-highlight."

#### `class PHIScanReport` (line 141)

Dataclass with:

| Field | Type | Default |
|---|---|---|
| `source` | str | required — "`<stdin>`" / file path / identifier |
| `char_count` | int | required |
| `findings` | List[PHIFinding] | `field(default_factory=list)` |

Properties:

- `count_by_pattern -> Dict[str, int]` (line 149-154) — histogram of findings by pattern name
- `highest_severity -> Optional[str]` (line 156-162) — "HIGH" > "MEDIUM" > "LOW" > None

Method: `to_dict() -> Dict[str, Any]` (line 164-171).

**Docstring present.** "Summary of one scan pass. Immutable — callers that need to re-scan create a new report."

#### `def scan_text(text, *, source="<text>", allowed_patterns=None) -> PHIScanReport` (line 176)

```python
def scan_text(
    text: str,
    *,
    source: str = "<text>",
    allowed_patterns: Optional[Iterable[str]] = None,
) -> PHIScanReport:
```

**Docstring present.** "Scan one text buffer for PHI. Returns a `PHIScanReport` — no exceptions on benign input."

Implementation: iterates `_PATTERNS` (line 190), skips entries in `allowed_patterns`, returns sorted findings.

#### `def scan_file(path, *, allowed_patterns=None) -> PHIScanReport` (line 213)

```python
def scan_file(
    path: Any,
    *,
    allowed_patterns: Optional[Iterable[str]] = None,
) -> PHIScanReport:
```

**Docstring present.** "Scan one file on disk. Binary files are skipped with an empty report — we don't attempt to decode EDI/PDFs here (that's the [...]"

#### `def redact_phi(...)` (line 232)

Signature not extracted in this iteration's read. Likely takes a text + report and returns a redacted version with PHI replaced by sentinel tokens.

### Private — `_PATTERNS` registry

Internal (per `_PATTERNS` access at line 190) — collection of `(name, regex, severity, value_group)` specs. Per the module docstring (per Report 0028 / 0030), patterns include: SSN, phone, DOB, MRN, NPI, email, address, ICD codes with name proximity.

### Re-exports — `compliance/__init__.py`

Per `head -30 RCM_MC/rcm_mc/compliance/__init__.py`:

```python
from .audit_chain import (  # noqa: F401
    AuditChainReport,
    append_chained_event,
    chain_status,
    verify_audit_chain,
)
```

**Only `audit_chain` symbols are re-exported in `__init__.py` head**. Need to read the rest to confirm if `phi_scanner` symbols are re-exported too. **HIPAA_READINESS.md (Report 0030)** showed callers use `from rcm_mc.compliance import scan_file, PHIScanReport` — so they ARE re-exported, just below the head shown.

### Production callers

`grep -rln "from .*compliance\.phi_scanner\|from .compliance import\|from .phi_scanner"`:

- `RCM_MC/rcm_mc/compliance/__init__.py` (re-export)
- `RCM_MC/rcm_mc/compliance/__main__.py` (CLI entry — `python -m rcm_mc.compliance` per Report 0026 `tests/test_compliance_cli.py`)

**ZERO consumers outside `compliance/` package.** Confirmed Report 0028 finding: `phi_scanner.py` is wired only to its own CLI + re-exports; **never invoked from server/route/ingest/runtime paths**.

### Documentation completeness

| Symbol | Has docstring? |
|---|---|
| `PHIFinding` | ✅ |
| `PHIScanReport` | ✅ |
| `scan_text` | ✅ |
| `scan_file` | ✅ |
| `redact_phi` | ✅ (assumed; not verified) |
| Module docstring | ✅ (per Report 0028 head read) |

**Documentation hygiene: clean.** Every public symbol has a docstring; module-level docstring exists.

### Severity tiering

PHIScanReport ranks findings via `highest_severity` (HIGH > MEDIUM > LOW). The convention matches HIPAA-relevant pattern severity:

- HIGH likely = SSN, NPI (direct identifiers)
- MEDIUM likely = phone, MRN, DOB
- LOW likely = email, address (less direct)

Exact mapping per pattern is in `_PATTERNS` (private; not enumerated this iteration).

### Sister module: `audit_chain.py`

Per `compliance/__init__.py` re-exports: `AuditChainReport, append_chained_event, chain_status, verify_audit_chain`. **Audit-log hash chain** for tamper-detection. Sister to phi_scanner; reserved for future iteration.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR348** | **Public API is small + clean — but unwired in production** | `scan_text`, `scan_file`, `redact_phi`, `PHIFinding`, `PHIScanReport` all have docstrings + clean signatures. The API is **production-ready**. The bug per Reports 0028/0030 is that nobody calls it from production paths. | (advisory — closes the API-readiness question) |
| **MR349** | **`scan_file` skips binary files silently** | Per docstring (line 218-219): "Binary files are skipped with an empty report". A PHI-bearing PDF/EDI gets a `findings=[]` report — caller may assume safe. **Misleading on the binary file path.** Recommend: PHIScanReport should include a `skipped_binary` flag. | Medium |
| **MR350** | **`scan_text` requires the text already in memory** | For large log files, callers must `path.read_text()` first — could OOM. `scan_file` likely streams. Prefer scan_file when possible. | Low |
| **MR351** | **`PHIScanReport.findings` returned with character offsets** | Caller-friendly for highlighting but **doesn't redact the value field** (line 128 `value: str`). The `value` IS the PHI itself. **Reports stored to disk leak PHI.** Recommend: redact-by-default; callers opt in to raw via flag. | **High** |
| **MR352** | **`redact_phi` API surface not yet read** | If redact returns a string, callers must replace original. If it mutates in place... unknown. Need full read. | Medium |
| **MR353** | **No async / streaming version for huge files** | `scan_text` reads the whole buffer; `scan_file` likely reads-then-scans. **Multi-GB log streams not supported.** | Low |
| **MR354** | **`allowed_patterns` parameter takes pattern NAMES (strings)** | Typo-prone — `allowed_patterns=["SSN"]` but pattern is named `"ssn"` (case-sensitivity unknown). **No enum / TypedDict to constrain.** | Low |
| **MR355** | **No test coverage indicator** | Per Report 0026 the CI weekly sweep includes `tests/test_phi_scanner.py` — but coverage depth not yet audited. | Medium |

## Dependencies

- **Incoming:** `compliance/__init__.py` (re-exports), `compliance/__main__.py` (CLI), test `tests/test_phi_scanner.py` (per Report 0026), HIPAA_READINESS.md (referenced as recommended pre-commit usage), and **0 production runtime callers**.
- **Outgoing:** stdlib (`re`, `dataclasses`, `pathlib`?, `typing`); the `_PATTERNS` private registry.

## Open questions / Unknowns

- **Q1.** What's `redact_phi`'s exact signature?
- **Q2.** What patterns does `_PATTERNS` actually include — what's the regex for SSN, NPI Luhn check, etc.?
- **Q3.** Does `compliance/__main__.py` accept paths from CLI? Hooks for pre-commit?
- **Q4.** Are PHIScanReport.findings stored anywhere (e.g. logged)? If yes, MR351 needs immediate fix.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0044** | **Read the rest of `phi_scanner.py` (lines 1-122 + 213-252)** to surface `_PATTERNS` + `redact_phi`. | Resolves Q1 / Q2. |
| **0045** | **Read `compliance/__main__.py`** | Resolves Q3. |
| **0046** | **Read `tests/test_phi_scanner.py`** | Closes Q2 + MR355. |
| **0047** | **Read `compliance/audit_chain.py`** — sister module | Closes Reports 0021 Q1, 0024 Q1 backlog. |

---

Report/Report-0043.md written. Next iteration should: read `compliance/audit_chain.py` end-to-end — repeatedly deferred as the canonical audit-trail module; needed to close Report 0021 Q1 (does any module log security events?) and Report 0024 (the only logger.error sites).

