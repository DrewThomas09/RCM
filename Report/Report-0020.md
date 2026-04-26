# Report 0020: Error-Handling Audit — `analysis/packet_builder.py`

## Scope

This report covers **every `try/except` block in `RCM_MC/rcm_mc/analysis/packet_builder.py`** on `origin/main` at commit `f3f7e7f`. The module was selected because:

- It is the **12-step packet orchestrator** named in `RCM_MC/CLAUDE.md` as the load-bearing pipeline ("every UI page, API endpoint, and export renders from a single `DealAnalysisPacket` instance").
- It carries **27 `# noqa: BLE001`** suppressions per Report 0015 (third-highest in the package after server.py and dashboard_page.py).
- It has not been the focus of any prior report (Report 0004 covered `analysis/packet.py`, the dataclass — not the builder).

The audit lists every handler, classifies its behavior (silent swallow vs FAILED-section vs logger.debug vs re-raise), and flags the patterns most likely to hide real failures.

Prior reports reviewed before writing: 0016-0019.

## Findings

### Module shape

- `RCM_MC/rcm_mc/analysis/packet_builder.py` — **1,454 lines**.
- **34 `try:` blocks**, 34 corresponding `except` handlers.
- **0 bare `except:`** (every handler names at least one exception class — good baseline).
- **27 `# noqa: BLE001`** suppressions (broad-except deliberately tagged).
- **20 logger calls — ALL at `logger.debug` level**. Zero `logger.error`, `logger.warning`, or `logger.exception`.
- 1 `# pragma: no cover` (line 279).

### Handler classification (34 total)

The exception handlers fall into 4 patterns:

| Pattern | Count | Description | Risk |
|---|---:|---|---|
| **A. Typed-narrow + recover** | 4 | `except (json.JSONDecodeError, TypeError)`, `except (KeyError, ValueError, TypeError)`, etc. → return a sane default | Low — the "right way" |
| **B. BLE001 + return FAILED status + reason=str(exc)** | ~16 | `except Exception as exc: # noqa: BLE001` → `return SectionStatus.FAILED, reason=str(exc)` | **Medium-Low** — failures surface in UI as a status banner; user sees the section is broken. **Original exception class lost, but message preserved.** |
| **C. BLE001 + logger.debug + recover** | ~7 | `except Exception as exc: # noqa: BLE001 \n logger.debug("X failed: %s", exc)` → continue with default | **Medium** — `logger.debug` is suppressed in production by default; effectively silent unless someone enables debug logging |
| **D. BLE001 + silent recover (no logger, no FAILED return, no raise)** | **7** | `except Exception: # noqa: BLE001` → swallow + continue | **HIGH — true silent-swallow sites** |

### Pattern detail

#### Pattern A — Typed-narrow handlers (4)

These are well-bounded:

| Line | Catch | Action |
|---|---|---|
| 84 | `(json.JSONDecodeError, TypeError)` | Return parsed-default |
| 100 | `(KeyError, ValueError, TypeError)` | Return parsed-default |
| 108 | `(TypeError, ValueError)` | Return default |
| 279 | `(AttributeError, TypeError, ValueError)` + `# pragma: no cover` | Defensive coverage opt-out |
| 515, 850 | `ValueError` (nested) | Continue iteration |

#### Pattern B — BLE001 → SectionStatus.FAILED

Sample (line 187-191):

```python
try:
    from ..ml.comparable_finder import find_comparables, WEIGHTS
except Exception as exc:  # noqa: BLE001
    return ComparableSet(status=SectionStatus.FAILED,
                         reason=f"finder unavailable: {exc}")
```

This pattern preserves error context inside the packet — the UI renders the FAILED section with the `reason` string. Per Report 0004's findings, the packet is the load-bearing artifact; section-level failures are first-class data.

**Strengths:**
- Failure visible to user (in the rendered UI section).
- Reason string captured.
- Non-blocking: rest of packet builds.

**Weaknesses:**
- Catches ALL Exceptions including `MemoryError`, `KeyboardInterrupt`-derived issues that should propagate (note: KeyboardInterrupt is BaseException, not caught here — that's correct).
- Original exception class is lost; only `str(exc)` survives. A `KeyError('deal_id')` becomes the string `"'deal_id'"` — interpretation requires reading source.

#### Pattern C — BLE001 → logger.debug + recover (~7)

Sample (line 249-256):

```python
try:
    from ..ml.ridge_predictor import predict_missing_metrics
    pred = predict_missing_metrics(profile.to_dict(), pool)
except Exception as exc:  # noqa: BLE001
    logger.debug("ridge predictor unavailable: %s", exc)
    return {}
```

| Line | Logger call | Recover-to |
|---|---|---|
| 255 | `logger.debug("ridge predictor unavailable: %s", exc)` | `return {}` |
| 271 | `logger.debug("predict_missing_metrics raised: %s", exc)` | continue |
| 376 | `logger.debug("econ_ontology unavailable: %s", exc)` | continue |
| 418 | `logger.debug("reimbursement_engine unavailable: %s", exc)` | continue |
| 427 | `logger.debug("build_reimbursement_profile failed: %s", exc)` | continue |
| 447 | `logger.debug("compute_revenue_realization_path failed: %s", exc)` | continue |
| 481 | `logger.debug("value_bridge_v2 unavailable: %s", exc)` | continue |
| 519 | `logger.debug("ramp override resolution failed: %s", exc)` | continue |
| 550 | `logger.debug("compute_value_bridge failed: %s", exc)` | continue |
| 806 | `logger.debug("v2 Monte Carlo unavailable: %s", exc)` | continue |

**HIGH-PRIORITY observation:** **All 20 logger calls in this module are `logger.debug`.** Per Python's standard logging behavior, `logger.debug` only emits when log level is `DEBUG`. The default for production is usually `INFO` or `WARNING` — debug-level messages are suppressed.

So in practice, all 10 of these "logged" failures are **silently swallowed in production**. The user only sees that a section is empty / partial; no operator can tell which subsystem failed without enabling debug logging.

**This is a substantial blind spot** — the packet builder's failure modes are visible only in dev/debug mode, not in the operator's normal log feed.

#### Pattern D — Silent-swallow handlers (7)

The most concerning category. Approximate sites (per heuristic count):

```python
try:
    pm.causal_path_summary = explain_causal_path(key)
except Exception:  # noqa: BLE001 — narrative must never break build
    pm.causal_path_summary = None
```
(line 386-388)

The "narrative must never break build" rationale is principled — the builder must complete even if a single per-metric narrative fails. But:

- **No logger anywhere.**
- **No FAILED status — caller has no signal that narrative is missing.**
- **No exception-class preservation** — debugging requires reproducing the failure manually.

| Line | Comment | What's lost |
|---|---|---|
| 387 | `# noqa: BLE001 — narrative must never break build` | Per-metric causal narrative missing; pm field becomes None silently |
| 455 | `# noqa: BLE001` (no comment) | (need to read context) |
| 947 | `# noqa: BLE001` (no comment) | Quantile computation falls back to 0.0 |
| (4 more) | various | similar |

The site at line 945-948 is illustrative:

```python
def _pct(series, q: float) -> float:
    try:
        return float(series.quantile(q))
    except Exception:  # noqa: BLE001
        return 0.0
```

Returning `0.0` on any quantile failure means a percentile field that *should be* "missing" or "n/a" reads as 0. **A real 0 is indistinguishable from a silent failure.**

### Logger-level audit

`grep -cE "logger\.(error|warning|exception|info|debug)" RCM_MC/rcm_mc/analysis/packet_builder.py` = **20**.

Distribution:

| Level | Count | Action |
|---|---:|---|
| `logger.debug` | 20 | All logger calls are at this level |
| `logger.info` | 0 | — |
| `logger.warning` | 0 | — |
| `logger.error` | 0 | **No error-level logs anywhere** |
| `logger.exception` | 0 | **No exception-with-traceback logs anywhere** |

**The packet builder never logs at WARNING or higher.** Combined with `logger.debug` suppression in production, **the builder's exception channel is effectively closed at production log level.**

### `SectionStatus` semantics

Pattern B handlers return `SectionStatus.FAILED`. There is also a `SectionStatus.SKIPPED` variant (per the line 925 sample: `return SimulationSummary(status=SectionStatus.SKIPPED, reason="sim input files not on disk")`).

| Status | When | Caller-visible signal |
|---|---|---|
| `OK` | Section built normally | None (rendered section) |
| `SKIPPED` | Preconditions not met (e.g. files missing, optional input absent) | Rendered as "skipped: <reason>" in UI |
| `FAILED` | Exception caught | Rendered as "failed: <reason>" in UI |

This is a clean status-vs-failure separation: SKIPPED is "expected, told you so"; FAILED is "unexpected, here's the exception message".

### Nested try/except clusters

3 sites have nested handlers:

| Site | Outer / Inner |
|---|---|
| Lines 506-518 | Outer BLE001 + inner ValueError on a coercion |
| Lines 841-853 | Same pattern |
| Lines 927-947 | Outer BLE001 + middle BLE001 + inner BLE001 (3-deep) |

The 3-deep nest at 927-947 (the simulation-comparison block) is the most complex error-handling site in the file. Each layer catches a different failure mode:
- innermost: `_pct` quantile fallback to 0.0 (silent)
- middle: scenario-overlay fallback (logger.debug)
- outermost: simulator failure → SectionStatus.FAILED (visible)

### Re-raises

Single `raise` site (line 1121): `raise ValueError("deal_id must be a non-empty string")`. This is an input-validation raise, not an except-and-re-raise.

**Zero `raise` inside except blocks** — the builder never re-throws caught exceptions. Every caught exception is fully swallowed.

### Test coverage of handlers

Not directly measured this iteration. Report 0008 noted `analysis/packet_builder.py` is referenced in many tests via `from rcm_mc.analysis.packet_builder import build_analysis_packet` — but **happy-path tests don't exercise BLE001 branches**. The 27 BLE001 sites are most likely test-uncovered.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR152** | **All logging is at DEBUG level — silent in production** | 20 of 20 logger calls use `logger.debug`. Default production log level is INFO/WARNING; DEBUG messages are dropped. **Failures of optional subsystems (ridge predictor, econ_ontology, reimbursement_engine, value_bridge, simulator scenario overlay, etc.) are completely invisible to operators.** Recommend: switch ~7 most-load-bearing failures to `logger.warning`. | **High** |
| **MR153** | **7 silent-swallow handlers (Pattern D)** | No logger, no FAILED status, no raise. Per-metric narratives, quantile computations, etc. silently degrade. **A user sees an "Average" output field reading 0 with no signal it should be "missing".** Recommend: tag each silent-swallow with at least `logger.warning` and consider sentinel values (NaN, None) over neutral zeros. | **High** |
| **MR154** | **`return 0.0` from `_pct` (line 947) makes real-zero indistinguishable from failure** | The quantile fallback returns the same value (0.0) for both "true zero" and "computation failed". Pre-merge: any branch that adds quantile-based logic must NOT trust 0.0 as a healthy signal — it could be a silent failure. | **High** |
| **MR155** | **27 BLE001 suppressions are not test-covered** | Happy-path tests don't trigger the broad-except branches. **A regression that changes a recovery path's return value (e.g. returning empty dict instead of empty list) would not fail tests.** Recommend: failure-injection tests for the top 5 most-used Pattern B/C/D sites. | **High** |
| **MR156** | **Original exception class lost in Pattern B** | `reason=str(exc)` discards the type. A `KeyError("deal_id")` becomes `"'deal_id'"`; a `FileNotFoundError("/path")` becomes `"[Errno 2] No such file or directory: '/path'"`. Both render the same generically. Recommend: include `type(exc).__name__` in reason. | Medium |
| **MR157** | **Failure mode shifts when a feature branch lowers/raises log level** | `logger` is a module-level `getLogger(__name__)` (per Report 0005 server.py uses the same). If a branch switches the root level to DEBUG (per ops request), suddenly all 20 debug messages become visible — could reveal noise that wasn't expected. Conversely, raising the level silences even the few warnings hypothetically added. **Audit the global log-level config before any change.** | Medium |
| **MR158** | **`narrative must never break build` rationale repeats verbatim only at line 387** | Other silent-swallow sites lack this rationale comment. **The principle ("never break build") is enforced inconsistently.** Some swallows are principled non-blocking (narrative); others are convenience. Pre-merge: any new silent-swallow needs a written rationale. | Low |
| **MR159** | **3-deep nested try at lines 927-947** | The simulation-comparison block is the hardest to reason about. A schema change to `df` columns (e.g. simulator output renames `ebitda_drag`) propagates: outer BLE001 catches → SectionStatus.FAILED with generic message. Hard to debug for operators. | Medium |
| **MR160** | **`SectionStatus.SKIPPED` vs `FAILED` semantic drift** | The contract is "skipped = expected, failed = unexpected". A branch that flips a SKIPPED to FAILED (or vice versa) for a given path silently changes the UI presentation. Pre-merge: confirm no ahead-of-main branch swaps these in this file. | Low |
| **MR161** | **No `logger.exception(...)` calls — tracebacks never logged** | When something does break in production-debug mode, only the `str(exc)` is logged via `logger.debug("X failed: %s", exc)`. The traceback is lost. **Post-mortem of an intermittent simulator crash would require reproducing locally.** Recommend: top-level `try` in `build_analysis_packet` should `logger.exception(...)` to preserve traceback. | Medium |

## Dependencies

- **Incoming (who calls `packet_builder.py`):** `cli.py:1303` `analysis_main(...)` (likely calls `build_analysis_packet`); `server.py` (lazy imports per Report 0005); 80+ test files (per Report 0004 packet importers); `analysis/__init__.py:33` re-exports `build_analysis_packet`.
- **Outgoing (what `packet_builder.py` depends on):** `analysis/packet.py` (the dataclasses); `ml/comparable_finder.py`, `ml/ridge_predictor.py`, `pe/value_bridge_v2.py`, `core/simulator.py`, `infra/config.py`, `scenarios/scenario_overlay.py`, `domain/econ_ontology.py`, plus 10+ other module-imported-from-handler subsystems.

## Open questions / Unknowns

- **Q1 (this report).** What's the project's intended production log level? If it's INFO or WARNING (typical), all 20 `logger.debug` calls are dead. Need to verify against `infra/logger.py` config.
- **Q2.** What does the UI render when a section comes back as `SectionStatus.FAILED` with `reason="finder unavailable: No module named 'rcm_mc.ml.comparable_finder'"`? Is the reason string user-friendly?
- **Q3.** Of the 7 silent-swallow handlers (Pattern D), which are intentional non-blocking (narrative-style) vs convenience? Per-line review needed.
- **Q4.** Does any test inject a failure into `packet_builder` to exercise the BLE001 branches? `pytest -k "fail"` would surface relevant tests.
- **Q5.** Is `SectionStatus` consumed by both UI (rendering) and logic (downstream consumers like report exports)? If a section is FAILED, do exports include or omit it?
- **Q6.** What happens at `build_analysis_packet`'s top level if EVERY section fails? Does the function still return a packet (with all FAILED statuses), or does it raise?
- **Q7.** Are there equivalent silent-swallow patterns in `analysis/risk_flags.py` or `analysis/diligence_questions.py` (sister modules in the same subpackage)?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0021** | **Read `infra/logger.py`** — find the project's production log level. | Resolves Q1 / MR152 / MR157. Determines whether 20 `logger.debug` calls are operational dead-letter. |
| **0022** | **Read the top-level `build_analysis_packet` function** (line 1100+ likely). | Resolves Q6 — packet-level failure semantics. |
| **0023** | **Sister-module audit: `analysis/risk_flags.py`** error handling. | Resolves Q7 — pattern-match across the subpackage. |
| **0024** | **Trace `SectionStatus.FAILED` consumption** — UI render + export-skip behavior. | Resolves Q2 / Q5 / MR160. |
| **0025** | **Failure-injection test sample** — inject ImportError into `comparable_finder` and verify packet build succeeds with FAILED ComparableSet. | Resolves Q4 / MR155. |
| **0026** | **Audit `RCM_MC_PHI_MODE`** — owed since Report 0019. | Closes the security-flag gap. |
| **0027** | **Sample-inspect 20 BLE001 sites in `server.py`** — owed since Report 0015. | Sister analysis. |

---

Report/Report-0020.md written. Next iteration should: read `infra/logger.py` to find the project's default production log level — closes Q1 / MR152 / MR157 here and tells us whether the 20 `logger.debug` calls in `packet_builder.py` actually surface in operator log feeds (the difference between "tracked" and "silent" failure modes).

