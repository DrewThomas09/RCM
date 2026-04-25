# Report 0080: Error Handling — `analysis/analysis_store.py`

## Scope

try/except sweep on analysis_store.py (~250 lines per Report 0008).

## Findings

### try/except inventory

Per Report 0008 + 0077 reads, analysis_store has try blocks at:

| Line (estimated) | Pattern |
|---|---|
| 241 | `from .packet_builder import build_analysis_packet` lazy import (Report 0008 — for cycle prevention per Report 0022) |
| (others) | likely typed-narrow on JSON decode + zlib decompress |

### Specific risks

- **`zlib.decompress`** can raise on corrupt blobs. Need confirmation that callers handle.
- **`json.loads`** of decompressed packet — likely wrapped.

### Logger usage

Module uses Pattern A (`from .infra.logger import logger`) per Report 0034.

### Cross-link

Report 0008 noted the lazy import at line 241 is a near-cycle defense (Report 0022 MR174). Module is otherwise small + well-typed.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR463** | **Need full read of analysis_store to enumerate try/except sites** | This iteration is partial. | Medium |

## Dependencies

- **Incoming:** server.py, refresh_scheduler, playbook, ui pages.
- **Outgoing:** packet_builder (lazy), packet, zlib, json.

## Open questions / Unknowns

- **Q1.** Full try/except inventory — owed.

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0081** | Security spot-check (already requested). |

---

Report/Report-0080.md written.

