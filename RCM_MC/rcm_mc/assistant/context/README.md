# PEdesk Guide — page-context foundation

A **read-only, structured context layer** describing every PEdesk
page/route. It is the foundation a future *PEdesk Guide* assistant will
use to **explain** pages — never to act.

> **Language note.** The original spec was written for a TypeScript/Node
> project (`src/assistant/context/*.ts`, `npm`, `tsx`). PEdesk is a pure
> **Python** stdlib codebase (no Node toolchain), so — per the spec's
> "adapt paths to match the codebase" — this is implemented in Python
> under `rcm_mc/assistant/context/`. TS interfaces → dataclasses; TS
> string-union types → `Enum`s; the `npm run validate:page-context`
> script → a runnable Python module (below).

## What this is NOT (scope guardrails)

This task builds **only** the context layer. It deliberately does **not**
include — and the future assistant must remain — without:

- an AI sidebar / chat UI
- Ollama or any LLM integration
- RAG / embeddings
- autonomous actions or task creation
- database memory
- any ability to modify data, run models, change assumptions, or make
  investment recommendations

The Guide is **explanatory only**: what a page does, where data comes
from, what metrics mean, why they matter in healthcare-PE diligence,
what caveats apply, and what related page to look at next.

## Files

| File | Role |
|------|------|
| `types.py` | Enums (`PageContextCategory`, `SourceConfidence`, `DataConfidence`) + dataclasses (`PageContext`, `ToolRouteDefinition`, `PageContextLookupResult`). |
| `discovered_tool_routes.py` | **Auto-generated** route manifest (the source of truth). |
| `_generate_discovered.py` | Regenerates the manifest from the palette. |
| `generated_page_context_stubs.py` | One placeholder context per discovered route (nothing is ever missing). |
| `manual_page_contexts.py` | Hand-written, conservative contexts for core pages (override stubs). |
| `page_context_registry.py` | Merged registry (manual overrides stubs) + helper lists. |
| `get_page_context.py` | `get_page_context(route)` — normalize, alias, dynamic routes, fallback. |
| `validate_page_context_coverage.py` | Coverage + integrity validator (exits non-zero on hard failure). |

## Route source of truth

`_DEFAULT_PALETTE_MODULES` in `rcm_mc/ui/_chartis_kit.py` — the Cmd+K /
Tools palette, whose comment-group headers map 1:1 to the seven PEdesk
tool groups (Home & Operations, Pipeline & Sourcing, Diligence
Workspace, Library & Reference, Research & Backtesting, Portfolio & LP,
Admin & System). Routes are query-string-normalized and de-duplicated.

## Commands

```bash
# Validate coverage (the equivalent of "validate:page-context")
.venv/bin/python -m rcm_mc.assistant.context.validate_page_context_coverage

# Regenerate the discovered-route manifest from the palette
.venv/bin/python -m rcm_mc.assistant.context._generate_discovered

# Tests
.venv/bin/python -m pytest tests/test_pedesk_guide_page_context.py
```

## Conservative-explanation principle

Where a page's exact formula, model mechanics, or data lineage is not
established from source, the context field literally says
**"Needs source documentation."** and `notes_for_assistant` instructs
the assistant not to invent specifics. Placeholder pages
(`source_confidence = needs_validation`) are allowed; missing pages are
not. Live-vs-illustrative honesty is carried by `data_confidence`.

---

## Task 2 — Metric Registry & Data Source Registry

Two more read-only registries + lookup helpers + a quality validator,
so the future Guide can also explain **metrics** and **data sources**.

| File | Role |
|------|------|
| `metric_registry.py` | `METRIC_REGISTRY` — 54 `MetricContext` entries (definition, formula + `formula_confidence`, why-it-matters, interpretation, common misread, caveats, source/data confidence). |
| `get_metric_context.py` | `get_metric_context(id_or_label)` — case-insensitive, alias-aware, clean fallback. |
| `data_source_registry.py` | `DATA_SOURCE_REGISTRY` — 32 `DataSourceContext` entries (description, `source_type`, cadence/lag, used-for, strengths, limitations, `ic_ready`). |
| `get_data_source_context.py` | `get_data_source_context(id_or_label)` — alias-aware, clean fallback. |
| `validate_guide_context_quality.py` | Quality validator (fails on invalid metric/source refs, duplicate ids, ambiguous aliases). |

New types in `types.py`: `FormulaConfidence`, `DataSourceType`,
`MetricContext`, `DataSourceContext`, and their lookup-result dataclasses.
`PageContext` gained optional `metric_ids` / `data_source_ids` links
(default empty — backward compatible).

**Conservative formulas.** Standard textbook formulas (EV/EBITDA, EBITDA
margin, leverage, days in A/R, …) are stated with
`formula_confidence = inferred`. Proprietary / model-derived metrics
keep `formula = "Needs source documentation."` + `needs_validation`.
No model-specific formula is invented.

```bash
.venv/bin/python -m rcm_mc.assistant.context.validate_guide_context_quality
.venv/bin/python -m pytest tests/test_pedesk_guide_metric_data_context.py
```

Connected high-priority pages (metric_ids / data_source_ids): hcris-xray,
bridge-audit, payer-stress, denial-prediction, physician-eu,
portfolio/monitor, data, methodology.

---

## Task 3 — Guide Context Packet layer

A single read-only builder that assembles **all** structured context the
future Guide needs to explain the current page — page context, the metric
and data-source contexts it links to, deterministic suggested questions,
the read-only behavioral policy, known limitations, and an honest quality
grade. It reads the registries only; it modifies nothing, runs no model,
performs no RAG, persists no memory, and makes no recommendation.

| File | Role |
|------|------|
| `guide_prompt_policy.py` | The behavioral contract — `GUIDE_PROMPT_POLICY` + `GUIDE_IDENTITY` / `ALLOWED_BEHAVIOR` / `DISALLOWED_BEHAVIOR` / `DEFAULT_UNCERTAINTY_MESSAGE` + `policy_as_dict()`. Importable by the future assistant endpoint. |
| `suggested_questions.py` | `get_suggested_questions_for_page(page_context)` — 5 defaults plus category/data-source-specific questions; deterministic, no AI, capped at 8. |
| `guide_context_packet.py` | `GuideContextPacket` dataclass, `build_guide_context_packet(route)`, `summarize_context_packet(packet)` (debug-only). |

`context_quality` ∈ {`strong`, `partial`, `placeholder`, `missing`} —
graded from `source_confidence`, linked metric/source contexts, and how
many core fields still say "Needs source documentation." Anything that
can't be resolved goes to `missing_context_notes` — never invented.

```bash
.venv/bin/python -m pytest tests/test_pedesk_guide_context_packet.py
```

```python
from rcm_mc.assistant.context import build_guide_context_packet, summarize_context_packet
print(summarize_context_packet(build_guide_context_packet("/diligence/hcris-xray")))
```

### Read-only debug endpoint

`GET /api/guide/context?route=<route>` returns the JSON-safe packet
(`packet_to_dict`). Missing `route` → 400; unknown route → 200 with
`context_quality="missing"`. It is a pure builder call — no model /
Ollama / RAG / DB writes. Optional HTML inspector at
`GET /guide/context-debug?route=<route>`.

```bash
curl 'http://127.0.0.1:8080/api/guide/context?route=/diligence/hcris-xray'
```

### Local-Ollama answer endpoint (read-only)

`POST /api/guide/ask` `{"route","question","model"?}` builds the packet
and asks a **local** model (`rcm_mc/assistant/ollama_client.py` +
`guide_prompt_builder.py`) to explain the page using **only** that
context — no RAG, no uploads, no mutation, no actions. Disabled by
default; enable per env: `PEDESK_GUIDE_OLLAMA_ENABLED=true`,
`PEDESK_GUIDE_OLLAMA_BASE_URL`, `PEDESK_GUIDE_OLLAMA_MODEL` (default
`gemma4:e4b`), `PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS`. Clean 400 (bad
request) / 503 (Ollama unavailable). Health: `GET /api/guide/ollama-health`.

```bash
PEDESK_GUIDE_OLLAMA_ENABLED=true rcm-mc serve --db p.db --port 8080
curl -X POST localhost:8080/api/guide/ask -H 'Content-Type: application/json' \
  -d '{"route":"/diligence/hcris-xray","question":"Where does this data come from?"}'
```

### Guide sidebar (read-only)

A closed-by-default right-side "Guide" panel ships on every chrome page
(injected by `chartis_shell`). It renders the deterministic page guide
from `/api/guide/context` and, when local Ollama is enabled, answers
read-only questions via `/api/guide/ask`. No RAG / uploads / memory /
actions / exports / mutation. Long answers wrap safely; in-flight answers
are dropped on close or route change; duplicate submits are blocked.

## Operating local Ollama (PEdesk Guide Q&A)

The Q&A is **disabled by default**. To enable it locally:

```bash
# 1. Install Ollama (https://ollama.com), then pull the models:
ollama pull gemma4:e4b          # the Guide answer model
ollama pull nomic-embed-text    # reserved for future use (not used by v1)

# 2. Confirm the models and that the server is up:
ollama list
curl -s http://localhost:11434/api/tags   # should return JSON

# 3. Start PEdesk with the Guide enabled:
PEDESK_GUIDE_OLLAMA_ENABLED=true \
PEDESK_GUIDE_OLLAMA_MODEL=gemma4:e4b \
PEDESK_GUIDE_OLLAMA_BASE_URL=http://localhost:11434 \
  rcm-mc serve --db p.db --port 8080
```

**Environment variables**

| Var | Default | Meaning |
|-----|---------|---------|
| `PEDESK_GUIDE_OLLAMA_ENABLED` | `false` | Master switch. Off → Q&A disabled (page guide still works). |
| `PEDESK_GUIDE_OLLAMA_BASE_URL` | `http://localhost:11434` | Local Ollama HTTP API base. |
| `PEDESK_GUIDE_OLLAMA_MODEL` | `gemma4:e4b` | Default chat model. |
| `PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS` | `30` | Per-request timeout. |

**Expected latency.** On a typical laptop, a `gemma4:e4b` answer takes
**~20 seconds**. The sidebar shows "PEdesk Guide is answering from the
page context…", and after 10s adds "Local model responses can take a
little while on this machine." The send button stays disabled while a
request is pending — this is expected, not a hang.

**Disabled behavior.** With `PEDESK_GUIDE_OLLAMA_ENABLED` unset/false the
deterministic page guide (overview, metrics, data sources, limitations,
suggested questions) renders normally; the ask box is disabled with copy
explaining how to enable it, and `POST /api/guide/ask` returns a clean
503.

**Troubleshooting 503 / "local model is unavailable"**

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `/api/guide/ollama-health` → `enabled:false` | env not set | start with `PEDESK_GUIDE_OLLAMA_ENABLED=true` |
| `enabled:true, reachable:false` | Ollama not running / wrong URL | `ollama serve`; check `PEDESK_GUIDE_OLLAMA_BASE_URL` |
| 503 on ask, health reachable | model not pulled | `ollama pull gemma4:e4b` (verify with `ollama list`) |
| answer never returns | request slower than timeout | raise `PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS` |

The Guide is **read-only** in every mode: it explains pages, metrics,
data sources, model intent, and limitations, and refuses to change
assumptions, run models, create tasks, export files, or make investment
recommendations.

### One-command local dev

```bash
./scripts/run_with_guide_ollama.sh            # serve with Guide Q&A enabled
PEDESK_GUIDE_RAG_ENABLED=true ./scripts/run_with_guide_ollama.sh   # + RAG
```

## Full local AI mode (one command)

The integrated path — Ollama Q&A **and** local RAG — in five steps:

```bash
# 1. Pull the models (one-time)
ollama pull gemma4:e4b
ollama pull nomic-embed-text

# 2. Build the local Guide RAG index
PEDESK_GUIDE_RAG_ENABLED=true ./scripts/build_guide_rag_index.sh

# 3. Check it
PEDESK_GUIDE_RAG_ENABLED=true ./scripts/check_guide_rag.sh

# 4. Run PEdesk in full AI mode (enables Ollama + RAG, runs a preflight)
PEDESK_GUIDE_RAG_ENABLED=true ./scripts/run_with_guide_ai.sh

# 5. Confirm readiness
curl localhost:8080/api/guide/ollama-health   # expect "ai_ready": true
```

Preflight any time without starting the server:
`python -m rcm_mc.assistant.rag.preflight_guide_ai` (PASS/WARN/FAIL with
exact fix commands).

**What "ready" means.** The sidebar's Ask box is active only when
`ai_ready` is true: Ollama enabled + reachable, the chat model installed,
RAG enabled, and a populated index (with the embed model installed). When
it isn't ready the sidebar shows *Ask PEdesk Guide is not fully
configured*, names the specific reason, and tucks the setup commands into
a **Setup details** disclosure — and the deterministic page guide still
renders. Notes: the normal Guide works without AI; Q&A requires local AI
mode; RAG requires a built index; **no user uploads are indexed yet**.

## Local RAG (PEdesk Guide knowledge base)

`rcm_mc/assistant/rag/` adds a **local, read-only** retrieval layer so the
Guide can answer from the whole in-repo knowledge base — page contexts,
metric/data-source registries, the read-only policy, and curated
methodology docs — not just the current route packet. Local embeddings
(Ollama `nomic-embed-text`), a local SQLite vector store, brute-force
cosine search. No cloud calls, no user uploads, no conversation memory.
**Disabled by default.**

```bash
# 1. Pull the models (one-time):
ollama pull gemma4:e4b
ollama pull nomic-embed-text

# 2. Build the local index (Ollama must be running):
PEDESK_GUIDE_RAG_ENABLED=true \
  .venv/bin/python -m rcm_mc.assistant.rag.index_builder

# 3. Validate it:
.venv/bin/python -m rcm_mc.assistant.rag.validate_rag_index

# 4. Serve with Ollama + RAG enabled:
PEDESK_GUIDE_OLLAMA_ENABLED=true PEDESK_GUIDE_RAG_ENABLED=true \
  rcm-mc serve --db p.db --port 8080
```

**Operator scripts** (local):
- `./scripts/build_guide_rag_index.sh` — build/refresh the index (idempotent).
- `./scripts/check_guide_rag.sh` — validate it (counts, model consistency, test searches).
- `GET /api/guide/ollama-health` reports `rag_enabled`, `rag_index_exists`, `rag_chunk_count`, and a `suggested_fix` (incl. "build the index" / "ollama pull …") for whatever is blocking.

| Var | Default | Meaning |
|-----|---------|---------|
| `PEDESK_GUIDE_RAG_ENABLED` | `false` | Master switch for retrieval in `/api/guide/ask` + `/api/guide/rag/search`. |
| `PEDESK_GUIDE_RAG_EMBED_MODEL` | `nomic-embed-text` | Local embedding model. |
| `PEDESK_GUIDE_RAG_INDEX_PATH` | `.pedesk_guide_rag.sqlite3` | Local index file. |
| `PEDESK_GUIDE_RAG_TOP_K` | `5` | Chunks retrieved per query. |

**Endpoints**
- `GET /api/guide/rag/search?q=…&route=…` — read-only retrieval (no LLM).
  Returns a clean disabled payload when RAG is off, a 503 when the local
  embedding model is unreachable.
- `POST /api/guide/ask` — when RAG is enabled it adds retrieved snippets to
  the prompt as *supporting* context (the route packet stays primary) and
  returns `rag_enabled`, `rag_results_count`, `rag_sources_used`. When RAG
  is disabled the behavior is exactly the v1 (packet-only) answer. RAG
  failures fall back to packet-only — they never break the answer.

```bash
curl 'http://127.0.0.1:8080/api/guide/rag/search?q=What%20does%20denial%20rate%20mean'
```

Scope guardrail: RAG indexes only safe internal context — never secrets,
credentials, audit logs, sessions, runtime data, or **user uploads**
(document ingestion is a deliberate later phase).

### Answer-quality evaluation (read-only quality gate)

`rcm_mc/assistant/eval/guide_eval.py` runs a fixed set of representative
questions across key routes in **packet-only** vs **RAG** mode through the
real ask pipeline, scores each answer with read-only / honesty heuristics
(no action-claims, no investment recommendations, admits-missing-context,
mentions source/caveat, latency), and writes a JSONL + markdown report to
the local (gitignored) `.pedesk_guide_eval/` folder. Needs a running
Ollama; not a CI test (the analyzers themselves are unit-tested in
`tests/test_guide_eval.py`).

```bash
# full matrix (9 routes x 10 questions x 2 modes)
PEDESK_GUIDE_OLLAMA_ENABLED=true PEDESK_GUIDE_RAG_ENABLED=true \
  .venv/bin/python -m rcm_mc.assistant.eval.guide_eval

# quick subset
PEDESK_GUIDE_OLLAMA_ENABLED=true PEDESK_GUIDE_RAG_ENABLED=true \
  .venv/bin/python -m rcm_mc.assistant.eval.guide_eval \
  --routes /diligence/hcris-xray --limit 4
```

The run prints a PASS/FAIL **gate**: zero action/mutation claims, zero
final investment recommendations, `read_only` true everywhere.
