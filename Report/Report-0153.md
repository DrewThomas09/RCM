# Report 0153: Map Next Key File — `pe_intelligence/__init__.py`

## Scope

Reads `RCM_MC/rcm_mc/pe_intelligence/__init__.py` (3,490 lines, 87,597 bytes) — the **anomalously large `__init__.py`** flagged by Report 0152 MR836. Closes Report 0152 Q2.

## Findings

### Structure

| Range | Content | Lines |
|---|---|---|
| 1-24 | Module docstring | 24 |
| 26-2032 | 275 `from .X import (...)` re-export blocks | ~2,007 |
| 2034+ | `__all__ = [...]` list with **1,455 names** | ~1,455 |
| | **Total** | **~3,490** |

**The file is PURE namespace aggregation.** No logic. Cross-correction to Report 0152 MR836 high — the size is **density of public surface**, not "substantive logic in `__init__`."

### Public-surface fanout

- **275 re-export source modules** (1 `from .` per sibling module)
- **1,455 public names re-exported** (per `__all__` count)
- **~5.3 names per module** average

Compare to other audited subpackages:

| Subpackage | __init__.py lines | Re-exports | Source modules |
|---|---|---|---|
| `domain/` (Report 0094) | 58 | 14 | 2 |
| `ml/` (Report 0093) | 30 | 10 | 41 |
| `rcm_mc_diligence/` (Report 0122) | 46 | 8 | 18 |
| `mc/` (Report 0112) | 38 | ~12 | 7 |
| `vbc_contracts/` (Report 0100) | 76 | 15 | 6 |
| **`pe_intelligence/` (this)** | **3,490** | **1,455** | **275** |

**pe_intelligence has 100× the public-surface count of the next-largest re-exporter (`vbc_contracts` 15 names).**

### Module docstring (lines 1-24) — 3 finding categories

Per docstring:
1. **Reasonableness bands** — sanity-check IRRs, EBITDA margins, lever realizability vs size/payer-mix peer ranges. Module: `reasonableness.py` (33,803 bytes per Report 0152).
2. **Heuristics** — codified PE rules of thumb. Module: `heuristics.py` (37,799 bytes). Mirrored in `docs/PE_HEURISTICS.md` as a living doc.
3. **Narrative commentary** — IC memo voice. Module: `narrative.py` (19,246 bytes).

### Sample re-exports (lines 27-80)

Per the visible portion:
- `reasonableness`: `Band`, `BandCheck`, `check_ebitda_margin`, `check_irr`, `check_lever_realizability`, `check_multiple_ceiling`, `run_reasonableness_checks` (7 names)
- `heuristics`: `Heuristic`, `HeuristicContext`, `HeuristicHit`, `all_heuristics`, `run_heuristics` (5 names)
- `narrative`: `NarrativeBlock`, `compose_narrative` (2 names)
- `partner_review`: `PartnerReview`, `partner_review`, `partner_review_from_context` (3 names)
- `red_flags`: `RED_FLAG_FIELDS`, `run_all_rules`, `run_red_flags` (3 names)
- `valuation_checks`: `ValuationInputs`, `check_equity_concentration`, `check_ev_walk`, `check_interest_coverage`, `check_terminal_growth`, `check_terminal_value_share`, `check_wacc`, `run_valuation_checks` (8 names)
- `ic_memo`: `render_all as render_ic_memo_all`, `render_html as render_ic_memo_html`, `render_markdown as render_ic_memo_markdown`, `render_text as render_ic_memo_text` (4 aliased renames)
- `bear_book`: `BEAR_PATTERNS`, `BearPatternHit`, `scan_bear_book` (3 names)
- `exit_readiness`: `ExitReadinessInputs`, `ExitReadinessReport`, ... (continues)

**Pattern: every submodule contributes 2-8 public names.** Consistent.

### CLOSURE — Report 0152 MR836 high (downgraded)

**MR836 was high (anomalous logic in __init__).** Reality: it's just thoroughness — 275 modules × 5 names each = 1,455 public names. **MR836 downgraded to Medium** — concern is now "extreme public-surface size" not "logic in __init__."

### Architectural promise (lines 20-23)

> "The entry point is `partner_review.partner_review`. It is called from OUTSIDE `packet_builder` — the packet stays pure; judgment is applied downstream. This preserves the 'one packet, rendered by many consumers' invariant."

**Confirms Phase-4 invariant** (per CLAUDE.md): `DealAnalysisPacket` is the central state; `pe_intelligence` is a downstream consumer that does NOT modify it.

### `partner_review` is the canonical entry

`from .partner_review import PartnerReview, partner_review, partner_review_from_context` (line 47-51). 3 entry points: `partner_review(packet)` for default; `partner_review_from_context(...)` for advanced; `PartnerReview` dataclass for the result.

### Imports — 275 internal, 0 external

`grep -c "^from \."` = 275. All sibling imports. **Zero external imports** — even stdlib not directly imported (sub-modules do their own).

### Cross-link to Report 0142 finance/

Report 0142 noted finance/ is structurally cleanest (7 modules, 0 cycles, leaf-only). pe_intelligence has the OPPOSITE shape: 275 modules with extreme namespace fanout. **Two ends of the discipline spectrum coexist.**

### Cross-link to Report 0093 ml/ pattern

Per Report 0093: ml/ has 41 modules; only 4 publicly re-exported (10 names total). 37 modules accessed only by direct path imports.

**pe_intelligence is the inverse**: 275 modules, ALL publicly re-exported. Cross-link Report 0093 MR502 + Report 0100 MR546 ("3 distinct subpackage organizations coexist") — pe_intelligence is yet another distinct style. **MR546 escalates to: 4 distinct organizations.**

### `__all__` size implication

Anyone running `from rcm_mc.pe_intelligence import *` imports 1,455 names into their namespace. **Heavy import-time cost** + namespace pollution.

### Ic_memo aliased re-exports (line 67-72)

`render_all as render_ic_memo_all` etc. — aliasing prevents collisions at the public surface (e.g., a `render_html` that conflicts with another module's `render_html`). **Discipline.**

### Doc-density vs ml/

Per Report 0152: pe_intelligence README is 20 KB / ~132K LOC = 0.15 chars/LOC.
Per Report 0093: ml/ README is 29 KB / 13,423 LOC = 2.16 chars/LOC.

**pe_intelligence is 14× less documented per LOC.** Cross-link Report 0152 MR840 medium.

But: per docstring lines 10-12 ("Each module is self-contained, stdlib-only, dataclass-based, JSON-round-trippable, and pairs a partner-voice `partner_note`"), per-module docstrings likely carry the doc burden.

### Verification — partner_review.py is the orchestrator (cross-link)

Per Report 0152: `partner_review.py` is 38,711 bytes (~1,500 LOC). The 2nd-largest .py file after `__init__.py`. Per __init__ line 47-51: 3 public entries.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR836-DOWNGRADE** | **Report 0152 MR836 was high (anomalous logic in __init__); REALITY is pure namespace aggregation** — 275 imports + 1,455 `__all__` entries | **Downgrade to Medium.** Not abnormal logic; just extreme public-surface density. | (downgrade) |
| **MR841** | **1,455 public names in `pe_intelligence` namespace** | `from rcm_mc.pe_intelligence import *` brings everything. Heavy import-time + namespace pollution. Should narrow `__all__` to a curated stable surface. | **Medium** |
| **MR842** | **`__init__.py` size makes maintenance fragile** | Adding/removing a submodule requires updating two places (the `from .X import (...)` block AND the `__all__` list). Easy to forget one half. | Medium |
| **MR843** | **4 distinct subpackage-organization patterns coexist** (per Report 0100 MR546 + this) — escalates from 3 | `domain/` thin re-export; `ml/` direct-path-imports; `vbc_contracts/` __init__-only; **`pe_intelligence/` 1,455-name flat re-export**. No project convention enforced. | (escalation) |
| **MR844** | **`pe_intelligence/__init__.py` 3,490 lines makes diff-review impractical** | Any feature-branch adding modules touches this file. PR review of a 3,490-line file with 1,455-entry `__all__` list is impractical. | Medium |

## Dependencies

- **Incoming:** TBD — likely server.py + analysis/packet_builder.py or as the LATTER's downstream renderer per Phase-4 invariant.
- **Outgoing:** 275 sibling submodules. Zero external (stdlib delegated to children).

## Open questions / Unknowns

- **Q1.** Per-module docstring density — is the README's "self-contained ... dataclass-based" claim borne out at module level?
- **Q2.** Do all 1,455 names in `__all__` correspond to actual exports, or are some stale (deleted from submodule but still listed)?
- **Q3.** What does `partner_review(packet)` actually invoke — selectively or all 275?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0154** | Read `pe_intelligence/partner_review.py` head to understand orchestrator (~1500 LOC, closes Q3). |
| **0155** | Read `cli.py` head (1,252 lines, 19+ iter carry from Report 0003). |
| **0156** | Random spot-check 3-5 pe_intelligence/ submodules for docstring density (closes Q1). |

---

Report/Report-0153.md written.
Next iteration should: read `pe_intelligence/partner_review.py` head — the canonical orchestrator (38,711 bytes, ~1,500 LOC).
