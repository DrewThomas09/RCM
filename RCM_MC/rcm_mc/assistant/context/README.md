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
