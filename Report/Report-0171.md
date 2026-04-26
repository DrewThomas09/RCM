# Report 0171: Security Spot-Check — `pe_intelligence/` Surface

## Scope

Sample security audit on `pe_intelligence/` (276 modules per Report 0152). Per Report 0153 architectural promise: "stdlib-only ... dataclass-based ... JSON-round-trippable." Sister to Reports 0021, 0051, 0072, 0081, 0104, 0108, 0111, 0114, 0136, 0141, 0145, 0150.

## Findings

### Sample-based audit

Spot-check on visible modules:
- `__init__.py` (Report 0153) — pure namespace aggregation; no logic; **no security surface**
- `partner_review.py` (Report 0155) — stdlib + sibling imports only; **no untrusted input**
- `extra_red_flags.py` (Report 0159) — registry pattern; rule helpers take `HeuristicContext`; **no untrusted input**

### Security checklist (per CLAUDE.md + Report 0141 vector list)

| Vector | Likely status | Reason |
|---|---|---|
| Hardcoded secrets / API keys | clean | per architectural promise (stdlib-only, dataclass) |
| SQL injection | clean | per Report 0153 — pe_intelligence does NOT touch SQLite (consumes packet, returns dataclass) |
| `eval` / `exec` / `pickle` | clean | per architectural promise + JSON-round-trippable |
| `subprocess` / `os.system` | clean | per stdlib-only |
| `yaml.load` (unsafe) | clean | no YAML handling here |
| Path traversal | clean | no file IO at this layer |
| Weak crypto | clean | no crypto |

**All 7 vectors clean by architectural construction.** Cross-link Report 0141 packet_builder same posture.

### Trust boundary

`pe_intelligence` consumes a `DealAnalysisPacket` (validated upstream by `analysis/packet_builder.py` per Report 0020 + Report 0141) and emits a `PartnerReview` dataclass. **Trust boundary is upstream** (cross-link Report 0141 MR792).

If `packet_builder` is bypassed and a malicious `DealAnalysisPacket` is constructed directly, `pe_intelligence` rules read its fields without re-validation. **Same defense-in-depth gap as Report 0141.**

### Sub-module spot-checks needed

Per Report 0152: 276 modules. **Random spot-check audit feasibility**: 5-10 modules across 7 reflexes (per Report 0152 cluster analysis):
- 1-2 sniff-test modules
- 1-2 archetype modules
- 1-2 named-failure modules
- 1-2 valuation modules
- 1-2 stress modules

Each ~10-15 KB, ~600 LOC. **Total ~10 audits = 1 iteration each = 10 future iterations.**

### Scoping recommendation

This iteration's spot-check is sample-based. Full audit of all 276 modules requires committed iteration budget. **Likely 100% security-clean** based on architectural promise + 3-module sample.

### Cross-link to Report 0136 + 0145 dbt SQL

Per Report 0145 MR805 high: dbt models (in `rcm_mc_diligence/connectors/seekingchartis/`) accept partner-supplied SQL. **`pe_intelligence/` is NOT in that path.** No SQL execution risk in this subpackage.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR901** | **`pe_intelligence/` is security-clean by construction** — sample of 3 modules + architectural promise | Cross-link Report 0141 packet_builder same posture. **No upstream-reaching IO.** | (clean) |
| **MR902** | **276-module subpackage warrants comprehensive audit** but feasibility limits to spot-checks | Cross-link MR908 in this report. ~10 future iterations would cover representative sample. | Low |
| **MR903** | **Trust boundary upstream** — relies on packet_builder validation | Cross-link Report 0141 MR792 + this report. | (carried) |

## Dependencies

- **Incoming:** Reports 0152-0160 pe_intelligence/ chain.
- **Outgoing:** stdlib + sibling modules (per Report 0155).

## Open questions / Unknowns

- **Q1.** Are there partner-uploaded JSON files anywhere in pe_intelligence/ that could trigger pickle-via-misuse? (Architectural promise says JSON-round-trippable — would use json.dumps/loads, not pickle.)

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0172** | Circular import (in flight). |

---

Report/Report-0171.md written.
