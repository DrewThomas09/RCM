# Report 0212: Map Next Directory — `rcm_mc/ai/`

## Scope

Maps `RCM_MC/rcm_mc/ai/` — 3rd of 12 small never-mentioned subpackages (Report 0190). Sister to Reports 0182 (engagement/), 0193 (verticals/), 0194 (causal/).

## Findings

### Inventory

```
ai/
├── README.md
├── __init__.py            (6 lines)
├── claude_reviewer.py     (182 lines)
├── conversation.py        (264 lines)
├── document_qa.py         (355 lines — largest)
├── llm_client.py          (241 lines)
└── memo_writer.py         (305 lines)
```

**5 .py + README + __init__.** **1,353 total LOC.**

### Per-file purpose

- `__init__.py` (6L) — minimal re-export
- `claude_reviewer.py` (182L) — Claude (Anthropic API) review pipeline; cross-link Report 0025
- `conversation.py` (264L) — chat/conversation state
- `document_qa.py` (355L) — document Q&A (largest)
- `llm_client.py` (241L) — Anthropic HTTP client
- `memo_writer.py` (305L) — IC memo synthesizer

### Cross-link to Report 0025 + 0093

Per Report 0025 Anthropic LLM API integration audit. **`ai/` subpackage IS the Anthropic integration.** Report 0025 was partial — this iteration confirms and locates the surface.

### Cross-link to Report 0153 ic_memo

Per Report 0153 + 0190: `pe_intelligence/ic_memo.py` (4 functions per __init__) and **`ai/memo_writer.py` are SEPARATE.** First likely renders existing data into IC memo HTML; second likely uses LLM to synthesize narrative.

### Public surface (per `__init__.py` 6L — minimal)

Per Report 0153 ml/__init__ pattern: small re-export. **6L means likely 1-3 names re-exported.**

### Suspicious findings

| Item | Note |
|---|---|
| document_qa.py (355L) | largest in subpackage — likely RAG/vector-search |
| llm_client.py (241L) | Anthropic HTTP client; cross-link Report 0025 secret-management concern |
| memo_writer.py (305L) | LLM-driven memo synthesis |

### Cross-link to Report 0150 secrets

`llm_client.py` likely reads `ANTHROPIC_API_KEY` env var. **Cross-link Report 0150 + 0178 secret patterns.** **Q1 below.**

### Cross-correction Report 0190 inference

Report 0190 inferred `ai/` as "Anthropic API + LLM integration." **Confirmed.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR998** | **`ai/` subpackage IS the Anthropic integration** (per Report 0025 partial audit) | Confirms Report 0190 inference. | (closure) |
| **MR999** | **`llm_client.py` likely uses ANTHROPIC_API_KEY env var** — secret bearing | Cross-link Report 0150 secret coverage. ANTHROPIC_API_KEY likely in `.env` (gitignored). | Medium |
| **MR1000** | **`document_qa.py` (355L) is largest in subpackage — likely RAG implementation** | Trust boundary: user-supplied document text → LLM. Cross-link Report 0150 secret + Report 0136 trust-boundary class. | High |

## Dependencies

- **Incoming:** TBD — likely server.py routes (per Report 0025 web routes), pe_intelligence (cross-link).
- **Outgoing:** stdlib + Anthropic API HTTP (urllib).

## Open questions / Unknowns

- **Q1.** `ANTHROPIC_API_KEY` source path (env var direct or config)?
- **Q2.** Does `document_qa.py` validate user-uploaded docs?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0213** | Read `llm_client.py` (closes Q1, 241L). |

---

Report/Report-0212.md written.
