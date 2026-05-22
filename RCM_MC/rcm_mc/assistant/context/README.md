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
