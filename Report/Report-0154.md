# Report 0154: Incoming Dep Graph — `rcm_mc/pe_intelligence/`

## Scope

Maps every importer of `rcm_mc/pe_intelligence/` (276 modules per Report 0152, 1,455 public names per Report 0153). Sister to Reports 0094 (domain incoming, 5 production), 0124 (PortfolioStore incoming, 237).

## Findings

### Importer count — surprisingly small for a 276-module subpackage

`grep -rln "from.*pe_intelligence\|from \.\.pe_intelligence\|import pe_intelligence\b"`:

**10 total importers** (8 production + 2 tests).

### Production importers (8)

| File | Path |
|---|---|
| `server.py` | `RCM_MC/rcm_mc/server.py` |
| `ui/chartis/archetype_page.py` | likely UI route renderer |
| `ui/chartis/home_page.py` | likely main hub |
| `data_public/rcm_benchmarks.py` | benchmarks consumer |
| `data_public/__init__.py` | re-export |
| `data_public/corpus_report.py` | corpus report renderer |
| `data_public/corpus_cli.py` | CLI |
| `data_public/ic_memo_synthesizer.py` | memo synthesis |

### Test importers (2)

- `tests/test_pe_intelligence.py` — direct module tests
- `tests/test_deals_corpus.py` — corpus tests using pe_intelligence

### Coupling-shape observation

| Subpackage | Public names | Importers | Avg names-per-importer |
|---|---|---|---|
| `domain/econ_ontology` (Report 0094) | 14 | 5 | 2.8 |
| `PortfolioStore` (Report 0124) | mostly `connect`/`init_db` | 237 | tight on 2-3 methods |
| `mc/` (Report 0112) | ~12 | varies | varies |
| **`pe_intelligence/` (this)** | **1,455** | **10** | **~145** |

**1,455 public names but only 10 importers** = importers use ~145 names each on average. **High-density, narrow-fanout coupling.**

Per Report 0153 cross-link: this is consistent with the 7-reflex orchestrator design — each importer (probably `server.py`) pulls in the full surface to render various views.

### Subpackage as "service-layer aggregator"

Per the importer list:
- `server.py` × 1 — likely renders a `/partner-review/<deal_id>` route
- `ui/chartis/` × 2 — UI pages embed pe_intelligence outputs
- `data_public/` × 4 — corpus-level analyses use pe_intelligence's reflexes

**Dominant pattern**: each importer wants the **full reflex surface** (sniff test + heuristics + named-failure + dot-connect + recurring/one-time + regulatory + partner voice).

### `data_public/__init__.py` re-export

Per Report 0094 + 0093 + 0100 namespace patterns: `data_public/` re-exports pe_intelligence symbols. **Cross-link Report 0093 ml/__init__ pattern** — projects use `__init__` re-exports to widen access.

### NEW finding: data_public/ is heavy importer

Per Report 0091/0121 backlog: `data_public/` is 313 files, never deeply mapped. Per this report: **4 of 8 production importers of pe_intelligence are in data_public/**. **Tight coupling between two unmapped giants.**

### Cross-link to Report 0153 architectural promise

Per Report 0153: `pe_intelligence` is a downstream consumer of `DealAnalysisPacket` ("called from OUTSIDE packet_builder").

**This report confirms via importer paths**: `analysis/packet_builder.py` is NOT in the importer list — no upstream-from-builder dependency. **Architectural invariant intact.**

### Cross-link to Report 0124 PortfolioStore (different scale)

PortfolioStore: 237 importers (Report 0124) — every layer.
pe_intelligence: 10 importers — tight to render layer.

**Inversely-proportional relationship** to the audit-significance: PortfolioStore is critical (every layer), pe_intelligence is concentrated (renderer-only).

### Importer audit relevance

| Importer | Audited? |
|---|---|
| `server.py` | partial (Reports 0005, 0018, 0102, 0108, 0114, 0124) |
| `tests/test_pe_intelligence.py` | UNREPORTED |
| `tests/test_deals_corpus.py` | UNREPORTED |
| `ui/chartis/archetype_page.py` | UNREPORTED |
| `ui/chartis/home_page.py` | UNREPORTED |
| `data_public/rcm_benchmarks.py` | UNREPORTED |
| `data_public/__init__.py` | UNREPORTED |
| `data_public/corpus_report.py` | UNREPORTED |
| `data_public/corpus_cli.py` | UNREPORTED |
| `data_public/ic_memo_synthesizer.py` | UNREPORTED |

**8 of 10 importers never reported.** Cross-link Reports 0091/0121 ui/ + data_public/ unmapped backlog.

### `>5 callers` heuristic vs reality

Per Report 0094 + 0124 heuristic: ">5 callers = tight coupling." pe_intelligence at **10 importers ≈ borderline tight.** Less than `domain/econ_ontology` (5) on the multi-package fanout but per-importer surface is denser.

**Tight-but-narrow coupling.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR845** | **`pe_intelligence/` has 1,455 public names but only 10 importers** | If a public name is renamed/removed in `__init__.py:__all__`, only 10 places need to update — manageable. But: any of the 10 importers could be doing a `from pe_intelligence import *` (1,455 names dumped) — high blast radius. | Medium |
| **MR846** | **4 of 8 production importers are in `data_public/`** | Tight coupling between two unmapped giants. Refactor to either is constrained by the other. | **High** |
| **MR847** | **8 of 10 importer files never reported** | Cross-link Reports 0091/0121 ui/ + data_public/ backlog. UI rendering surface is largely uncharted. | High |
| **MR848** | **Tests for pe_intelligence (`test_pe_intelligence.py`)** never analyzed | Per Report 0091: ~280 untouched test files. This is one of them. | Medium |

## Dependencies

- **Incoming:** 10 files (8 production + 2 tests) across `server.py`, `ui/chartis/`, `data_public/`, tests.
- **Outgoing:** TBD — per Report 0153 zero external imports at the `__init__` level; sub-modules are stdlib + numpy per README.

## Open questions / Unknowns

- **Q1.** Do any importers use `from rcm_mc.pe_intelligence import *` (full 1,455-name pollution)?
- **Q2.** Does `data_public/__init__.py` further re-export pe_intelligence symbols at a 3rd level?
- **Q3.** What does `data_public/ic_memo_synthesizer.py` do — different from `pe_intelligence/ic_memo.py` (Report 0153 referenced)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0155** | Outgoing dep graph (in flight) — likely `pe_intelligence/__init__.py` outgoing or pick a fresh module. |
| **0156** | Map `data_public/__init__.py` to close Q2. |
| **0157** | Read `pe_intelligence/partner_review.py` (carry from Report 0153). |

---

Report/Report-0154.md written.
