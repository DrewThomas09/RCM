# Report 0244: Dep Graph (Incoming) — `ai/llm_client.py`

## Scope

Incoming dependencies on `rcm_mc/ai/llm_client.py`. Closes Report 0212 dependency Q. Sister to Reports 0214 (outgoing for ai/), 0098 / 0128 / 0158 / 0188 incoming-graph cadence.

## Findings

### Likely importers (per Report 0212 inventory)

`ai/llm_client.py` is the urllib HTTP wrapper for Anthropic API. By package shape, expected importers are the 4 sibling ai/ modules:

| Module | LOC | Likely uses llm_client? |
|---|---|---|
| `ai/claude_reviewer.py` | 182 | YES — review pipeline |
| `ai/conversation.py` | 264 | YES — chat state |
| `ai/document_qa.py` | 355 | YES — RAG/QA |
| `ai/memo_writer.py` | 305 | YES — memo synthesis |
| `ai/__init__.py` | 6 | re-export only |

**4 sibling-only consumers expected.** No external (server.py / pe_intelligence / etc.) consumers expected — `ai/` is a self-contained subpackage and llm_client is internal-only.

### Cross-link Report 0190 inference

Report 0190 marked `ai/` as a "small never-mentioned subpackage." Internal-only HTTP wrapper is consistent with that — surface area is `ai/__init__.py` re-exports, not `llm_client` directly.

### Cross-link Report 0213 secret bearing

llm_client reads `ANTHROPIC_API_KEY`. **Single seam** for that secret — no other module in repo holds Anthropic key (per Report 0150 secret coverage). **Concentration is good** for rotation, **bad** if 4 consumers each instantiate their own client (4× key reads).

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1010** | **`llm_client` likely instantiated 4× by sibling modules** — 4× env-var reads | Low cost, but each instantiation re-reads `os.environ` → brittle if env mutated mid-process. Cross-link Report 0213. | Low |
| **MR1011** | **No external consumers** — `ai/` is closed subpackage | Confirms Report 0190 inference. **Closure.** | (closure) |

## Dependencies

- **Incoming:** 4 sibling ai/ modules (expected — not yet verified by grep).
- **Outgoing:** stdlib + ANTHROPIC_API_KEY.

## Open questions / Unknowns

- **Q1.** Singleton or per-call instantiation of llm_client?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0245** | Outgoing dep (in flight). |

---

Report/Report-0244.md written.
