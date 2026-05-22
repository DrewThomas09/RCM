# PEdesk Guide page-context — PROGRESS

**Date:** 2026-05-22

## Language adaptation
Spec was TypeScript/Node; PEdesk is pure Python (no Node toolchain).
Implemented in Python under `rcm_mc/assistant/context/` per the spec's
"adapt paths to match the codebase" instruction. TS interfaces →
dataclasses; string-union types → `Enum`s; `npm`/`tsx` validator → a
runnable Python module + a pytest.

## Route source(s) discovered
- **`rcm_mc/ui/_chartis_kit.py :: _DEFAULT_PALETTE_MODULES`** — the
  Cmd+K / Tools palette and the authoritative route manifest. Its
  comment-group headers map 1:1 to the seven PEdesk tool groups.
- Considered but not merged as separate manifests: `/module-index`
  (the ~150 `data_public` analytic modules — a secondary catalog) and
  the per-deal dynamic routes (handled by the dynamic matcher, not the
  static manifest). The palette is the single normalized source.

## Counts
- Total discovered routes: **72**
- Registry entries: **72** (one per discovered route; zero missing)
- Documented contexts: **42**
- Placeholder contexts: **30**
- Duplicate routes: **0**
- Routes that could not be categorized: **0** (all map to one of the 7 groups)
- Dynamic route contexts (not in the static manifest): Deal Dashboard,
  Partner Review, Deal IC Packet, Deal Red Flags, Analysis Workbench,
  Engagement Portal.

## Commands run + results
- `python -m rcm_mc.assistant.context.validate_page_context_coverage`
  → **PASS, exit 0** (0 missing, 0 invalid categories/confidence, 0
  duplicates, 0 missing titles/normalizedRoutes).
- `python -m pytest tests/test_pedesk_guide_page_context.py` → **9 passed**.
- Acceptance lookups verified: `?demo=steward` normalizes to
  `/diligence/risk-workbench`; `/deal/<id>`, `/deal/<id>/partner-review`,
  `/deal/<id>/ic-packet`, `/deal/<id>/red-flags`, `/analysis/<id>`,
  `/portal/<id>` resolve to generic contexts; trailing slash + hash
  normalize; unknown routes return the clean fallback.

## Placeholder routes (need source upgrade — next batches)
30 placeholders, e.g.: /source, /pe-intelligence, /deal-screening,
/conferences, /diligence/{thesis-pipeline, checklist, ingest,
benchmarks, root-cause, value, counterfactual, qoe-memo,
denial-prediction, physician-attrition, physician-eu, management,
exit-timing, covenant-stress, bridge-audit}, /engagements,
/deals-library, /market-intel, /research, /notes, /hold-analysis,
/corpus-backtest, /portfolio/{map, monitor}, /portfolio-analytics,
/market-data/state/CA.

## Remaining caveats
- Manual contexts deliberately describe *intent* and *interpretation*,
  not exact formulas. Anything not established from source is marked
  "Needs source documentation." — no invented math/lineage.
- `data_confidence` flags live-vs-illustrative honestly, but several
  manual entries use `mixed`/`unknown` pending source confirmation.
- The `/module-index` long-tail (~150 analytic modules) is intentionally
  out of scope for this manifest; fold in later if the Guide should
  cover them too.

## Next recommended batch to upgrade (highest value first)
1. Diligence Workspace placeholders: /diligence/{value, qoe-memo,
   counterfactual, exit-timing, covenant-stress, bridge-audit,
   denial-prediction} — core IC-path tools.
2. Pipeline: /source, /pe-intelligence, /deal-screening.
3. Research: /hold-analysis, /corpus-backtest, /market-intel.
4. Portfolio: /portfolio/map, /portfolio/monitor, /portfolio-analytics.

---

# Task 2 — Metric & Data Source Registries (2026-05-22)

- **Metrics created:** 54 (`METRIC_REGISTRY`) — financial/PE, revenue
  cycle, provider, hospital/HCRIS, risk/model (+ `ebitda_bridge`).
- **Data sources created:** 32 (`DATA_SOURCE_REGISTRY`) — public/external,
  uploaded/target, internal/system, special (+ `benchmark_prior`, added
  so the payer-stress page reference resolves).
- **Pages connected to metric/source ids:** 8 (hcris-xray, bridge-audit,
  payer-stress, denial-prediction, physician-eu, portfolio/monitor, data,
  methodology). `PageContext` gained optional `metric_ids` /
  `data_source_ids` (default empty — existing entries unaffected).
- **Lookups:** `get_metric_context`, `get_data_source_context` —
  case-insensitive, alias-aware, clean fallback.

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0): 0 invalid metric/
  source refs, 0 duplicate ids, 0 ambiguous aliases. (33 metrics
  `needs_validation` and placeholder pages are allowed, not failures.)
- `py_compile` on the package → clean.
- `pytest tests/test_pedesk_guide_metric_data_context.py
  tests/test_pedesk_guide_page_context.py` → 20 passed.

## Caveats
- Most metric formulas are `needs_validation` or `inferred` by design —
  no model-specific formula is invented; standard textbook ratios are
  marked `inferred`.
- Removed the ambiguous bare alias "leakage" (claimed by both
  collections_leakage and referral_leakage) so it cleanly falls back.
- Many `data_confidence` values are `mixed`/`unknown` pending source
  confirmation. The `/module-index` ~150-module long-tail remains out of
  scope for the page manifest.

## Next recommended batch
- Upgrade more diligence placeholders to documented contexts and attach
  metric/source ids (qoe-memo, covenant-stress, exit-timing, value).
- Confirm exact formulas from code/methodology to promote key metrics
  from `inferred`/`needs_validation` → `documented`.

---

# Task 3 — Guide Context Packet layer (2026-05-22)

Single read-only builder that assembles all structured context the
future Guide needs to explain a page. No AI / Ollama / RAG / chat /
actions / DB memory / visual redesign / workbench port — text + lookups.

| File | Role |
|------|------|
| `guide_prompt_policy.py` | `GUIDE_PROMPT_POLICY` (frozen) + `GUIDE_IDENTITY`, `ALLOWED_BEHAVIOR`, `DISALLOWED_BEHAVIOR` (10), `DEFAULT_UNCERTAINTY_MESSAGE`, `policy_as_dict()`. The behavioral contract; carries no behavior. |
| `suggested_questions.py` | `get_suggested_questions_for_page(page_context)` — 5 defaults + category/data-source additions, deterministic, capped at 8. |
| `guide_context_packet.py` | `GuideContextPacket` dataclass + `build_guide_context_packet(route)` + `summarize_context_packet(packet)`. |

**Builder flow:** `get_page_context` → resolve metric contexts (explicit
`metric_ids`, else conservative match from `key_metrics` labels) → resolve
data-source contexts (same) → suggested questions → embed policy →
compute `context_quality` → record `missing_context_notes`. Never invents
formulas/lineage; unresolved items are recorded, not fabricated.

**`context_quality` precedence:** `missing` (no page ctx) → `placeholder`
(`source_confidence == needs_validation`) → `strong` (documented /
inferred_from_page **and** ≥1 linked metric/source) → `placeholder`
(≥3 core fields say "Needs source documentation.") → `partial`.

## Quality distribution (all 72 registry routes)
- **strong: 8** (the 8 metric/source-linked pages from Task 2)
- **partial: 2**
- **placeholder: 62**
- **missing: 0** (every registry route resolves; only off-manifest
  routes like `/unknown-route` grade `missing`)

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0).
- `py_compile` on the package → clean.
- `pytest tests/test_pedesk_guide_context_packet.py` → 10 passed.
- `pytest tests/test_pedesk_guide_page_context.py
  tests/test_pedesk_guide_metric_data_context.py` → 20 passed (unchanged).

## Caveats
- Packet quality is honest, not flattering: 62/72 routes grade
  `placeholder` because their underlying page contexts are still
  placeholders (Task 1/2 backlog). Promoting them is a context-authoring
  task, not a packet-layer change.
- Conservative metric/source matching only resolves *registered* aliases;
  a page whose `key_metrics` are free-text prose won't auto-link (recorded
  in `missing_context_notes`). Explicit `metric_ids`/`data_source_ids`
  remain the reliable path.
- No endpoint is wired: this is infrastructure the future Guide endpoint
  imports. Building that endpoint (and any UI) is explicitly out of scope.
