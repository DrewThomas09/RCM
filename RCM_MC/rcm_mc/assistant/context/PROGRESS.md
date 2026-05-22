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
