# Report 0015: Tech-Debt Marker Sweep — `RCM_MC/rcm_mc/` (full subdirectory)

## Scope

This report covers a **tech-debt marker sweep across the entire `RCM_MC/rcm_mc/` source tree** on `origin/main` at commit `f3f7e7f`. Markers searched: standard tech-debt vocabulary (`TODO`, `FIXME`, `XXX`, `HACK`, `DEPRECATED`), neutral hints (`NOTE`, `TBD`), wider candidates (`BUG`, `KLUDGE`, `REFACTOR`, `OPTIMIZE`, `WORKAROUND`, `STUB`, etc.), and **suppression markers** (`# noqa`, `type: ignore`, `pragma: no cover`) which are de-facto tech-debt tags.

`RCM_MC/tests/`, `RCM_MC/docs/`, `RCM_MC/readME/`, `vendor/`, and `legacy/` are also surveyed for completeness but treated as adjacent territory.

Prior reports reviewed before writing: 0011-0014.

## Findings

### Marker totals across `RCM_MC/rcm_mc/`

| Marker | Files | Total occurrences | Verdict |
|---|---:|---:|---|
| **TODO** | 2 | **2** | (both are `TODO(phase-7)` — intentional deferrals) |
| **FIXME** | 0 | 0 | clean |
| **XXX** | 1 | 1 | false positive (number-format placeholder, not a marker) |
| **HACK** | 0 | 0 | clean |
| **DEPRECATED** | 0 | 0 | clean |
| **NOTE** | 3 | 3 | 2 are HTML/string literals; 1 is a code comment that is benign |
| **TBD** | 4 | 5 | all are data placeholders / UI fallbacks, not code debt |
| **BUG / KLUDGE / REFACTOR / OPTIMIZE / WORKAROUND / STUB / TEMPORARY** | 0 | 0 | clean |

**Across 60K+ LoC of production code, only 2 explicit tech-debt markers exist.** That is unusually clean.

### The 2 real explicit-marker entries

#### `RCM_MC/rcm_mc/ui/chartis/ic_packet_page.py:525`

```python
audit_section = _audit_section(b.get("audit_trail"), "audit")

# TODO(phase-7): split into per-section micro-explainers as part
# of a later documentation polish pass.
explainer = render_page_explainer(
    what=(
        "IC-ready packet combining the IC memo, analyst "
        "cheat-sheet, bear patterns, regulatory items, 100-day "
        ...
```

- **Severity: LOW** — UX polish; the page renders correctly without the split.
- **Owner cue:** `phase-7` — references a planned future phase. No commit / issue link.

#### `RCM_MC/rcm_mc/ui/chartis/_sanity.py:166`

```python
    # ── RCM operating metrics ────────────────────────────────────────
    # TODO(phase-7): subsector-aware guards. The ranges below cover the
    # widest partner-plausible envelope across ALL hospital subsectors
    # combined, because the render sites don't currently pass subsector
    # context. A future pass should take (metric, subsector) and look
    # up per-subsector bands (e.g. acute + behavioral + ASC each).
    "denial_rate": MetricRange(
        # Widened in Phase 6D from 0.30 to 0.38 to accommodate
        ...
```

- **Severity: MEDIUM** — sanity-range guards are deliberately loose; subsector-aware guards would tighten precision. Today, an unusual ASC may pass a sanity check that an acute-hospital target shouldn't, and vice versa.
- Adjacent comment ("Widened in Phase 6D from 0.30 to 0.38") suggests the sanity ranges are evolving; this TODO is the consolidation roadmap.

### False positives

- `RCM_MC/rcm_mc/ui/chartis/_sanity.py:39` → `UNIT_NUM = "num"  # rendered as X,XXX.XX (raw numbers — HHI, counts)` — the `XXX` is in a number-format placeholder, not a marker.
- `RCM_MC/rcm_mc/server.py:13254` → `"note": ('badge-amber', "NOTE")` — `NOTE` is a UI badge label string.
- `RCM_MC/rcm_mc/ui/hospital_profile.py:361` → `f'<span class="cad-section-code">NOTE</span>'` — HTML output literal.
- `RCM_MC/rcm_mc/ui/_chartis_kit_legacy.py:120` → benign code-organization comment ("everything previously under CORPUS INTEL").

### TBD entries (data placeholders, not code debt)

- `RCM_MC/rcm_mc/exports/qoe_memo.py:87` — UI default text `"Target Entity (TBD)"`.
- `RCM_MC/rcm_mc/data_public/biosimilars_opp.py:151,152` — corpus rows with TBD launch dates ("Hadlima TBD 2025", "Wyost TBD").
- `RCM_MC/rcm_mc/data_public/deal_origination.py:121` — fallback string.
- `RCM_MC/rcm_mc/data_public/sellside_process.py:143` — corpus active-process row with TBD banker.

These are corpus-data artifacts where the source itself is "TBD" — not code that needs fixing.

### Adjacent territory — vendor/

`vendor/ChartisDrewIntel/` (the DBT subproject) carries **12 explicit `TODO`** markers in `.sql` files. These are vendored third-party DBT models; not maintained by this project. Listed for completeness:

- `vendor/ChartisDrewIntel/models/core/staging/core__stg_claims_condition.sql:59`
- `vendor/ChartisDrewIntel/models/data_marts/hcc_recapture/staging/hcc_recapture__stg_coef_hier.sql:12`
- 9 more in `data_marts/hcc_recapture/`, `data_marts/cms_hcc/`, `data_marts/hcc_suspecting/`
- `vendor/ChartisDrewIntel/macros/cross_database_utils/load_seed.sql:337`

### Adjacent — `RCM_MC/tests/`, `RCM_MC/docs/`, `RCM_MC/readME/`

**Zero TODO/FIXME/XXX/HACK/DEPRECATED** in any of these trees. The codebase's test + doc surfaces have no marker debt.

### Suppression-marker survey (de-facto tech debt)

The explicit-marker count is misleadingly low because the project tracks tech debt via **lint-suppression markers** instead. Counts:

| Marker | Files | Notes |
|---|---:|---|
| `# noqa: BLE001` | many | **369 occurrences** (335 + 34 trailing-space variant) — bare-except / broad-except suppression |
| `# noqa: F401` | many | **149 occurrences** (145 + 3 + 1) — unused import suppression |
| `# noqa: ARG001` | few | 4 — unused argument suppression |
| `# noqa: S608` | 2 | SQL-injection lint suppression |
| `# noqa: PLC0415` | 1 | Import-outside-top-level suppression |
| `# noqa: F821` | 1 | Undefined-name suppression |
| `# noqa: F401, F403` | 1 | Wildcard import suppression (the `rcm_mc/lookup.py:7` shim flagged in Report 0009) |
| `# type: ignore` | 8 | mypy suppressions |
| `# pragma: no cover` | 3 | coverage-tool exclusions |

**Total: ~530 suppression markers across the production tree.** This is an order of magnitude more than explicit TODO/FIXME — the project's actual debt-tracking medium.

### BLE001 distribution (broad-except suppression)

Top BLE001 hot-spots:

| File | BLE001 count | Risk |
|---|---:|---|
| `rcm_mc/server.py` | **71** | Sample line `1450`: `except Exception:  # noqa: BLE001 — never break a request`. Comment-as-rationale pattern. **Every BLE001 silently swallows a class of errors.** |
| `rcm_mc/ui/dashboard_page.py` | 38 | Per Report 0007, this file is **deleted on `feature/workbench-corpus-polish`**. The BLE001 burden disappears with the file — but only if that branch's deletion is accepted. |
| `rcm_mc/analysis/packet_builder.py` | 27 | The 12-step orchestrator. Broad excepts here mean step failures don't propagate — packet may emerge with silent gaps. |
| `rcm_mc/ui/ic_packet_page.py` | 15 | IC packet rendering — silent failures = blank sections in IC memos |
| `rcm_mc/ui/portfolio_risk_scan_page.py` | 8 | |
| `rcm_mc/diligence/bear_case/evidence.py` | 8 | |
| `rcm_mc/ui/dashboard_v3.py` | 7 | |
| 4 more files | 5-5 each | |

The `# noqa: BLE001 — never break a request` annotation pattern (server.py:1450, 1521, 1571) is intentional resilience: the HTTP server should never crash on a downstream module bug. But it's also a legitimate concern: 71 broad-except sites in `server.py` means **the server will accept any module breakage and turn it into a silent log line**.

### `type: ignore` distribution

8 occurrences across:

| File | Line | Context |
|---|---|---|
| `server.py:9783` | `from .provenance.explain import _resolve_metric_id  # type: ignore` | Private-symbol import |
| `ui/_chartis_kit_v2.py:546` | `from . import _chartis_kit_legacy as _legacy  # type: ignore` | **Legacy fallback** — the v2 kit imports the legacy kit as a fallback. Implies a UI-kit migration in progress. |
| `ui/dashboard_page.py:2180` | `history_series = None  # type: ignore[assignment]` | None-assignment to typed var |
| `ui/_chartis_kit.py:229` | `def chartis_shell(body: str, title: str, **kwargs) -> str:  # type: ignore[misc]` | Function-signature suppression |
| `infra/cache.py:119, 120` | Adding attributes to a wrapper function | mypy-correct, legit ignore |
| `analysis/playbook.py:424` | `key=initiative_counts.get  # type: ignore[arg-type]` | Generic-typing edge case |
| `exports/packet_renderer.py:199, 200, 507` | `from pptx import Presentation  # type: ignore` (and similar) | **Optional dep imports** — pptx + docx are not in core deps |

### `pragma: no cover` distribution

3 occurrences (small):

| File | Line | Why excluded |
|---|---|---|
| `analysis/packet_builder.py:279` | `except (AttributeError, TypeError, ValueError):  # pragma: no cover` | Defensive catch, untested path |
| `analysis/packet.py:135` | `except ImportError:  # pragma: no cover` | Optional import fallback |
| `provenance/registry.py:362` | `else:  # pragma: no cover — new source?` | Future-source dispatch |

## Severity grouping

### HIGH (0)

No HIGH-severity tech-debt markers in the production tree.

### MEDIUM (2 explicit + 1 systemic)

1. `ui/chartis/_sanity.py:166` `TODO(phase-7)` — subsector-aware sanity guards. Affects metric-range correctness across hospital subsectors.
2. `ui/chartis/ic_packet_page.py:525` `TODO(phase-7)` — UX polish (per-section micro-explainers).
3. **The 369 BLE001 suppressions** are systemic medium-grade debt: every one silently swallows errors. Most have inline comment rationale ("never break a request") which is appropriate for HTTP handlers but applies more loosely in `dashboard_page.py` (38), `packet_builder.py` (27), and elsewhere.

### LOW (5 + ~10 suppressions)

- 5 TBDs (data placeholders, not code).
- 8 `type: ignore` — mostly legitimate (optional deps, attribute-on-wrapper patterns).
- 3 `pragma: no cover` — defensive-path exclusions.

### NOISE (false positives)

- 1 XXX (number-format placeholder).
- 3 NOTE (HTML/string literals + benign comment).
- 12 vendor/ TODOs (third-party DBT models — not our debt).

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR107** | **`feature/workbench-corpus-polish` deletes 38 of 165 BLE001 sites** | The deletion of `dashboard_page.py` (per Report 0007 MR46) removes 38 broad-except suppressions. **If the branch is merged, the systemic-debt count drops by ~10%**; if rejected, those 38 stay. Either way, code paths currently catching errors silently disappear — pre-merge audit needed for any callers downstream. | **High** |
| **MR108** | **`# noqa: BLE001 — never break a request` rationales are inconsistently applied** | 71 BLE001 sites in `server.py` have varying rationales (some commented "audit must never break flow", some uncommented). A branch that adds new suppressions without rationale will pass lint but ratchet the debt. **Recommend: enforce a rationale comment on every new BLE001 in CI.** | Medium |
| **MR109** | **`# type: ignore` on `from . import _chartis_kit_legacy as _legacy`** | `ui/_chartis_kit_v2.py:546` imports the legacy kit as a fallback. This implies a UI-kit migration in progress. The `feature/workbench-corpus-polish` branch renames `_chartis_kit_legacy.py → _chartis_kit_dark.py` (per Report 0007). **The fallback import path becomes broken if that rename merges without coordination.** | **High** |
| **MR110** | **The 2 `TODO(phase-7)` are uncommitted commitments** | Neither links to an issue, PR, or roadmap doc. "Phase 7" is referenced but not located. If a feature branch retires the phase-7 plan without updating these TODOs, they become permanent untruths. | Low |
| **MR111** | **5 `TBD` corpus placeholders are data debt, not code debt** | `data_public/biosimilars_opp.py:151-152` "Hadlima TBD 2025", "Wyost TBD" — corpus rows shipped with literal "TBD". A future iteration should refresh against actual launch dates. Not a merge blocker but a corpus-staleness signal. | Low |
| **MR112** | **`pragma: no cover — new source?` (provenance/registry.py:362)** | Inline comment is itself a question. Indicates the author knew the dispatch was incomplete. | Low |
| **MR113** | **`type: ignore` on optional-dep imports (`pptx`, `docx`)** | `exports/packet_renderer.py:199, 200, 507`. These bypass mypy because the modules are in optional extras (per Report 0003). If a future branch makes pptx/docx required deps, the `type: ignore` becomes stale and hides real type errors. | Low |
| **MR114** | **No HIGH-severity tech debt = signal that markers are NOT the debt-tracking medium** | The codebase has 60K+ LoC and only 2 explicit TODOs. **The actual debt-tracking medium is `# noqa: BLE001`** (369 occurrences). Future merge audits must prioritize suppression-marker review over TODO-style review. | (advisory) |

## Dependencies

- **Incoming (who consumes these markers):** `ruff`, `mypy`, `pytest --cov` honor the suppression markers. Manual code review honors the TODOs.
- **Outgoing (what these markers depend on):** `pyproject.toml:[tool.ruff.lint]` and `[tool.mypy]` config (per Report 0003) — ruff codes BLE001/F401/ARG001/S608 are part of the active rule set; suppressions are valid only because the codes are enabled.

## Open questions / Unknowns

- **Q1 (this report).** Are the 369 BLE001 sites legitimate (HTTP-resilience, audit non-blocking, optional-dep fallbacks) or are some genuinely hiding bugs? Sample a random 20 BLE001 sites and inspect the swallowed exception type.
- **Q2.** What is "phase-7"? The two TODO(phase-7) markers reference a plan not visible in `RCM_MC/docs/` (per Report 0002 file list). Is it on a feature branch? An archived doc?
- **Q3.** Has any feature branch added new `# noqa` suppressions? Pre-merge sweep would surface ratchet.
- **Q4.** The `_chartis_kit_legacy → _chartis_kit_dark` rename on `feature/workbench-corpus-polish` (Report 0007 MR54) — does the legacy fallback at `ui/_chartis_kit_v2.py:546` still work post-rename, or does it become a broken import?
- **Q5.** Is the 38-BLE001 count in `dashboard_page.py` representative of the file's design (defensive UI rendering) or of accumulated bug-shrugs?
- **Q6.** Are the 8 `type: ignore` sites all justified? Specifically `analysis/playbook.py:424` `key=initiative_counts.get  # type: ignore[arg-type]` — is there a typed alternative?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0016** | **Sample-inspect 20 random BLE001 sites in `server.py`** to verify rationale per-site. | Resolves Q1 / MR108. Determines whether systemic debt is principled or accumulated. |
| **0017** | **Locate the "phase-7" plan** — grep `phase-7`, `Phase 7`, `phase 7` across the repo. | Resolves Q2 / MR110. |
| **0018** | **Cross-branch noqa-ratchet sweep** — does any ahead-of-main branch add `# noqa` suppressions? | Resolves Q3 / MR114. |
| **0019** | **Read `feedback.py:aggregate_360_feedback`** — owed since Report 0014. | Closes MR101 (RaterRole weight desync). |
| **0020** | **Trace the `_chartis_kit_legacy` ↔ `_chartis_kit_dark` rename impact** across all branches. | Resolves Q4 / MR109 / Report 0007 MR54. |

---

Report/Report-0015.md written. Next iteration should: sample-inspect 20 random BLE001 sites in `server.py` to verify each `# noqa: BLE001` rationale per-site — closes Q1 here and tells us whether the 369 systemic suppressions are principled (HTTP resilience) or accumulated (silent bug-shrugs).

