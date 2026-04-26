# Report 0140: Error Handling — `analysis/packet_builder.py`

## Scope

`RCM_MC/rcm_mc/analysis/packet_builder.py` (1,454 lines) — partial in Report 0020 (initial pass); this iteration counts every try/except and characterizes the pattern. Sister to Reports 0050, 0080, 0099, 0104, 0123, 0131 (silent-failure pattern accumulation).

## Findings

### Try/except inventory — 34 try blocks

| Aspect | Count | Note |
|---|---|---|
| Total `try:` blocks | 34 | per `grep -c` |
| `except Exception` (broad) | 27 (out of 34, ~80%) | per Report 0105 BLE001 dominance pattern |
| Bare `except:` (no class) | **0** | clean — no naked excepts |
| `except (...)` narrow tuples | 7 | (json.JSONDecodeError, TypeError), (KeyError, ValueError, TypeError), (TypeError, ValueError), (AttributeError, TypeError, ValueError), etc. |

**0 bare excepts.** **80% broad-Exception (27 of 34).** Cross-link Report 0105: 369 `noqa: BLE001` project-wide; packet_builder accounts for ~27 of them.

### Sample broad-except sites (with comments)

| Line | Pattern | Comment |
|---|---|---|
| 187 | `except Exception as exc:  # noqa: BLE001` | (no inline reason) |
| 195 | `except Exception as exc:  # noqa: BLE001` | (no inline reason) |
| 254 | `except Exception as exc:  # noqa: BLE001` | (no inline reason) |
| 270 | `except Exception as exc:  # noqa: BLE001` | (no inline reason) |
| 375 | `except Exception as exc:  # noqa: BLE001` | (no inline reason) |
| 387 | `except Exception:  # noqa: BLE001 — narrative must never break build` | **REASON DOCUMENTED** |
| 279 | `except (...):  # pragma: no cover` | unreachable / coverage-excluded |

**Only 1 of the sampled broad-except blocks has an INLINE REASON COMMENT (line 387: "narrative must never break build").** The other 26 are bare `# noqa: BLE001` without per-call-site justification.

### Narrow-except blocks (7 — the discipline)

| Line | Caught classes |
|---|---|
| 84 | `(json.JSONDecodeError, TypeError)` |
| 100 | `(KeyError, ValueError, TypeError)` |
| 108 | `(TypeError, ValueError)` |
| 279 | `(AttributeError, TypeError, ValueError)` (with `# pragma: no cover`) |

These are **defensive parsing** (json/type coercion) — the right discipline. Cross-link Report 0099 dead-branch pattern (custom_metrics had similar).

### Pattern: 12-step packet builder + lots of optional substeps

Per CLAUDE.md: `analysis/packet_builder.py` is the 12-step orchestrator. Each substep wrapped in try/except so a failing predictor / risk-flag / question-generator doesn't crash the whole packet build.

**Comment at line 387** ("narrative must never break build") confirms the design intent: **packet build is best-effort; partial failures are tolerated.**

### Cross-link to Report 0020

Report 0020 was the initial error-handling audit on packet_builder (partial). It noted broad-except discipline. This report extends:
- **Counts**: 34 try, 27 broad, 0 bare, 7 narrow.
- **Comments**: only 1 of 27 broad-except blocks has a per-site reason. The rest rely on the documented pattern (CLAUDE.md + Report 0020).

### Project-wide silent-failure cross-link (cumulative pattern)

| Report | Module | Pattern |
|---|---|---|
| 0050 | `infra/notifications.py` | except + pass |
| 0099 | `domain/custom_metrics.py` | dead `except ValueError` |
| 0104 | `infra/webhooks.py` | `_do_deliver` swallows audit-write failure (MR578) |
| 0123 | `infra/consistency_check.py` | `logger.debug` swallow |
| 0131 | `reports/html_report.py` | `except Exception: playbook = {}` swallows YAML parse error |
| **0140 (this)** | **`analysis/packet_builder.py`** | **27 broad-except, almost all noqa-only without per-site reason** |

**6 documented instances. Pattern is project-wide.** `packet_builder` is the **densest** site.

### Logging quality

Per Report 0020 + this report: most broad-except blocks have `logger.warning(...)` or `logger.exception(...)` calls. Cross-link Report 0024 logging cross-cut: packet_builder is a Pattern A logger user.

### Cross-link to Report 0103 MR571

`infra/job_queue.py` was flagged for "no logger.error on job failure" (MR571 medium). `packet_builder.py` does NOT have that issue — most broad-excepts log. **Inconsistency**: jobs swallow silently, packet builds log. Cross-link MR571.

### Cross-link to MR582 (webhook attempts always 1)

Webhooks logged but with bug. Packet_builder logs without that bug. **Pattern**: log-but-document discipline is good when applied; bugs creep in when discipline is lax.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR788** | **27 of 34 try blocks (80%) use `except Exception` with `noqa: BLE001` but NO per-site reason comment** | Per CLAUDE.md broad-except discipline is documented at module level, but per-site rationale is absent. A future refactor that "tightens" the catches has no documented reason to preserve them. **Best-practice: each `noqa: BLE001` should have a `# reason: ...` comment.** | Medium |
| **MR789** | **Only 1 of 27 broad-except blocks has documented intent inline** (line 387 "narrative must never break build") | The exception that proves the rule. Rest are docstring-pattern only. | Low |
| **MR790** | **0 bare excepts — clean discipline** | Cross-link CLAUDE.md "Don't write `except:`". Compliant. | (clean) |

## Dependencies

- **Incoming:** server.py (per Report 0102 hop), CLI.
- **Outgoing:** many — packet_builder is the 12-step orchestrator.

## Open questions / Unknowns

- **Q1.** Of the 27 broad-except blocks, are any currently producing log noise from a real bug (vs. tolerating known-non-fatal paths)?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0141** | Security spot-check (in flight). |
| **0142** | Circular import (in flight). |

---

Report/Report-0140.md written.
