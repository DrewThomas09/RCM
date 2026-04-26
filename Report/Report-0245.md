# Report 0245: Dep Graph (Outgoing) — `ai/` subpackage

## Scope

Outgoing dependencies for `rcm_mc/ai/` (5 .py, 1353 LOC per Report 0212). Sister to Report 0244 (incoming).

## Findings

### Outgoing surface (per Reports 0212/0213)

| Source module | Outgoing |
|---|---|
| `__init__.py` (6L) | re-exports only |
| `llm_client.py` (241L) | stdlib (urllib, hashlib, json, logging, os, time, dataclasses, datetime, typing) + **Anthropic API HTTP** |
| `claude_reviewer.py` (182L) | likely → llm_client + stdlib |
| `conversation.py` (264L) | likely → llm_client + stdlib + maybe sqlite3 (chat state) |
| `document_qa.py` (355L) | likely → llm_client + stdlib (largest, possibly chunking helpers) |
| `memo_writer.py` (305L) | likely → llm_client + maybe pe_intelligence/ic_memo |

### Third-party deps

**Zero.** Per Report 0213: `urllib.request` direct, no `anthropic` SDK. Consistent with CLAUDE.md stdlib-heavy stance.

### External-network surface

**Anthropic API** (api.anthropic.com) — single network egress point in this subpackage. Cross-link Report 0150 secret coverage + Report 0136 trust-boundary class.

### Possible cross-package outgoing

- `memo_writer` → `pe_intelligence/ic_memo` (Report 0212 noted these are SEPARATE — memo_writer synthesizes, ic_memo renders). May be one-directional.
- `document_qa` → could hit `data_public/` for corpus reads. Unverified.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1012** | **Single-vendor lock to Anthropic API** | No abstraction layer for swapping provider. If Anthropic rate-limits or pricing changes, all 4 ai/ modules degrade together. | Medium |
| **MR1013** | **Possible `ai/memo_writer` → `pe_intelligence/ic_memo` cross-package call** | Cross-package coupling pe_intelligence ↔ ai. Cross-link Report 0212. | Q1 below |

## Dependencies

- **Incoming:** see Report 0244 (4 sibling consumers).
- **Outgoing:** stdlib + Anthropic API HTTP. **Possibly** pe_intelligence/ic_memo + data_public.

## Open questions / Unknowns

- **Q1.** Does memo_writer call into pe_intelligence?
- **Q2.** Does document_qa read corpora from data_public/?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0246** | Branch audit (in flight). |

---

Report/Report-0245.md written.
