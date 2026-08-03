# Report 0276: `pe_intelligence/` Package Inventory — the last never-mapped subpackage

## Scope

The TRIAGE backlog has carried "`pe_intelligence/` 270+ submodules — never mapped" as an inventory item since Report 0190. This is that map. Discovery output, not a bug hunt: structure, purity, consumers, coverage, and one measured performance finding.

## Shape

| Metric | Value |
|---|---|
| Python modules | **277** |
| Total LOC | **82,811** |
| Subpackages | **0 — completely flat** |
| `__init__.py` | 3,494 LOC, 277 imports, `__all__` of **1,457 names** |
| Largest non-init module | `_catalog.py` (2,232 LOC — the analytic-tool registry) |
| Next largest | partner_review 1,037 · heuristics 902 · reasonableness 800 · deal_to_historical_failure_matcher 648 |

At 277 modules in one directory it is by a wide margin the largest subpackage in `rcm_mc/`, and the only large one with no internal grouping.

Thematic clusters by filename: exit (12), partner (10), diligence (9), archetype (8), thesis (7), risk (6), physician (5), payer (5), failure (4), red_flag (3), market/covenant/valuation (2 each).

## Purity — the notable architectural finding

**The package has zero side effects.** Verified by import-statement scan across all 277 modules:

- **0** imports of `sqlite3`, `urllib`, `requests`, `socket`, or `subprocess`
- **0** SQL statements (`INSERT`/`UPDATE`/`DELETE`/`CREATE TABLE`)
- **0** LLM references (`llm_client`, `LLMClient`, `anthropic`) — consistent with the CLAUDE.md rule confining LLM use to `ai/` + `assistant/`
- **0** third-party runtime deps — no numpy, pandas, scipy, matplotlib, or sklearn. **Stdlib only**, across 82k LOC.

*Correction during this audit:* an initial keyword grep suggested 4 modules touched sqlite3/open/urllib. On inspection every match was a false positive — function names (`critical_open(`, `_deal_killers_open(`, `_check_largest_open(`) and prose inside strings ("supplemental-info requests."). The definitive import-statement scan returns zero. Purity confirmed.

This means the whole package is a pure-computation layer: no trust boundary, no DB coupling, trivially testable, and safely importable from any layer. It is the cleanest large surface in the codebase from a security standpoint — which is why the session's security sweeps never surfaced anything here.

## Consumers and coverage

- **24 external consumers**, overwhelmingly `ui/chartis/` pages (pe_intelligence_hub, investability, archetype, stress, red_flags, ic_packet, partner_review, white_space, market_structure, home) plus `ui/pe_reference_page.py` and two `server.py` call sites.
- **13 test files** reference the package — a thin ratio against 277 modules, though the purity means each module is individually easy to test.
- Every consumer import is **function-scope (lazy)**, not module-level — verified in server.py and the chartis pages.

## Measured finding — eager-import cost (new, LOW)

```
import rcm_mc.pe_intelligence  →  936 ms, pulls all 276 submodules, exports 1,457 names
```

Because `__init__.py` eagerly imports all 277 modules, importing **any single** submodule (e.g. `from .pe_intelligence import partner_review`) pays the full ~936 ms and loads 82k LOC.

**Severity is LOW, not startup-critical:** all consumer imports are lazy, so the server does not pay this at boot — it is a one-time ~1 s first-hit latency on the first pe_intelligence-backed page load per process, then cached in `sys.modules`.

**Fix path (not attempted here):** a PEP 562 module-level `__getattr__` in `__init__.py` mapping each of the 1,457 exported names to its owning module, loaded on first attribute access. That is a mechanical but large change to a 3,494-line facade with real potential to break `from pe_intelligence import X` patterns subtly. It wants the package owner's sign-off and a dedicated PR, not a blind loop iteration — filed as **MR1072 (LOW)**.

## Verdict

No defects found. The package is architecturally clean (pure, stdlib-only, LLM-free) with two structural observations: a flat 277-module layout with no subpackage grouping, and the eager-import facade above. Both are maintainability items for the owner, not bugs.

## Suggested follow-ups

| Item | Note |
|---|---|
| MR1072 (LOW) | Lazy `__getattr__` facade to drop the 936 ms first-import cost — needs owner sign-off. |
| (optional) | Group the 277 flat modules into thematic subpackages (exit/, partner/, diligence/, archetype/…) — large mechanical refactor, purely maintainability. |

---

Report/Report-0276.md written.
