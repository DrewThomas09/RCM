# ADR: Healthcare EDI (835/837) Parser Selection

- Status: Accepted (initial) — revisit when real VDR corpora are available.
- Date: 2026-05-20
- Context: Healthcare Revenue Leakage Diligence Module V2
  (`docs/healthcare-revenue-leakage-v2-plan.md` §4).

## Decision

- **Primary parser: `x12-python` (MIT)**, wrapped by
  `rcm_mc/diligence/parsers/x12_python_adapter.py:X12PythonAdapter`.
  Installed via the optional `[edi]` extra so **core `rcm_mc` gains no
  new hard dependency** (CLAUDE.md "no new runtime deps" rule).
- **Fallback parser: `FallbackSegmentAdapter`**, wrapping the existing
  hand-rolled `rcm_mc/diligence/ingest/readers.read_edi`. Always
  available (stdlib only). It is the **fallback, never the primary**
  (acceptance criterion #19): `available_adapters()` returns the
  library adapter first and the fallback last.

Both emit the same library-independent `ParsedTransactionSet`, so the
CCD builder and downstream analytics are parser-blind.

## Evaluation (parser evaluation harness)

`rcm_mc/diligence/parsers/harness.py:run_harness` ran both adapters over
`tests/fixtures/edi/`. Findings:

| Capability | x12-python | FallbackSegmentAdapter |
|---|---|---|
| ISA delimiter recovery | ✅ `Delimiters.from_isa` | ⚠️ assumes `~ * :` (detection.py recovers them separately) |
| Envelope metadata (sender/receiver/control #) | ✅ | ❌ |
| 835 CLP claim payments | ✅ | ✅ |
| **835 CAS adjustments (group/reason/amount)** | ✅ | ❌ (dropped) |
| 835 patient member id (NM1*QC) | ✅ | ✅ |
| 837 CLM + SV1 + DTP + HI | ✅ | ✅ |
| **837 subscriber member id (NM1*IL)** | ✅ | ❌ (only NM1*QC) |
| Strict ISA fixed-width validation | ✅ (raises on bad ISA) | ⚠️ lenient |
| Pydantic models / typed hierarchy | ✅ | ❌ |
| New dependency | yes (pydantic) | none |
| License | MIT | n/a (in-repo) |

**Why x12-python primary:** it recovers the CAS adjustment detail and
NM1*IL subscriber id that the fallback drops — both load-bearing for
denial categorization and PHI tokenization — plus full envelope
metadata, with clean MIT licensing.

**Why keep the fallback:** zero-dependency guarantee; the module must
still ingest EDI when `[edi]` is not installed. It is also a useful
differential-parse check.

## Gaps / remaining custom normalization

- x12-python strips the segment tag, so NM1 element indices shift by one
  vs. the legacy `split("*")` convention — handled by a qualifier *scan*
  (`_member_id`) rather than fixed indices, for robustness across
  835/837 NM1 layouts.
- x12-python's strict fixed-width ISA rejects non-compliant hand exports;
  real VDR remits are compliant, but messy/synthetic files may need the
  lenient fallback. Detection (`detection.detect_file`) stays lenient and
  parser-agnostic so routing never depends on strict ISA.
- BPR payment-total reconciliation, PLB provider-level adjustments, and
  837I-specific loops are not yet mapped — tracked in the plan's build
  order (reconciliation + analytics steps).

## Candidates considered, not adopted

- **pyx12** — HIPAA validation/conversion; heavier, dated packaging.
  Revisit if we need formal 5010 compliance validation reports.
- **node-x12** — repo is Python; out of scope.
- **BerryWorks EDIReader** — **GPL** Community Edition; **reference /
  benchmark only**, never embedded.

## Revisit triggers

- A real VDR corpus exposing 837I institutional / PLB / multi-CAS edge
  cases the synthetic fixtures don't cover.
- x12-python proving brittle on messy real exports → promote a hardened
  fallback or evaluate pyx12 for the validation path.
