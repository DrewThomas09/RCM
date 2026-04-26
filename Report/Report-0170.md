# Report 0170: Error Handling — `reports/reporting.py`

## Scope

`RCM_MC/rcm_mc/reports/reporting.py` (561 lines, 13 public fns per Report 0163/0164). Sister to Reports 0020, 0050, 0080, 0099, 0104, 0110, 0111, 0123, 0131, 0140, 0141.

## Findings

### Try/except inventory — 4 try blocks

| Line | Pattern | Note |
|---|---|---|
| 265 | `try: from scipy.stats import gaussian_kde / except ImportError: gaussian_kde = None` | **scipy soft-dep** (cross-link Report 0113) |
| 285 | `try: kde = gaussian_kde(x, bw_method=0.12) / except Exception:` | **broad** — falls back to histogram |
| 302 | `try: from scipy.stats import norm` | scipy soft-dep |
| 489 | `try: ... / except (KeyError, ZeroDivisionError):` | narrow |

**4 try blocks. 0 bare `except`. 2 broad-Exception.** Cross-link Report 0140 packet_builder's 27-broad-except.

### Patterns

**Tier 1 — scipy ImportError fallback** (lines 265-268, 302):
```python
try:
    from scipy.stats import gaussian_kde
except ImportError:
    gaussian_kde = None
```

**Graceful degradation when scipy not installed.** Per Report 0113 cross-correction: scipy IS used (in 3 sites including this file). Per Report 0129 MR734: scipy missing causes silent degradation in `core/distributions.py`.

This module ALSO degrades silently — falls back to histogram (line 297) if KDE fails.

**Tier 2 — KDE-computation broad-except** (line 285-294):
```python
try:
    kde = gaussian_kde(x, bw_method=0.12)
    ...
except Exception:
    n, _, _ = ax.hist(x, bins=...)
```

**Falls through to histogram** if KDE fails. **No `noqa: BLE001`** — minor lint divergence from Report 0140 packet_builder discipline. **No logger.warning** — silent fallback. Cross-link Report 0144 silent-failure pattern.

**Tier 3 — narrow except (line 489)**:
```python
except (KeyError, ZeroDivisionError):
```

**Defensive narrow catch.** Good discipline.

### Comparison to Report 0140 packet_builder

| Module | try blocks | broad-except | bare | with logger | with noqa |
|---|---|---|---|---|---|
| `analysis/packet_builder.py` (Report 0140) | 34 | 27 | 0 | most | most |
| `infra/notifications.py` (Report 0050) | TBD | several | 0 | partial | partial |
| **`reports/reporting.py` (this)** | **4** | **2** | **0** | **0** | **0** |

**Lower volume but ALSO lower logging discipline.** None of the 4 try blocks logs the caught exception.

### Silent-failure cross-link to Report 0144 / 0131

Per Reports 0050, 0099, 0104, 0123, 0131, 0140 silent-failure pattern: `reports/reporting.py:285+292` adds another instance. **7th confirmed silent-failure site.**

### Where errors hide (cross-link Report 0131 MR744)

If the input `df` has all-NaN data, the KDE call may fail silently and the chart shows histogram instead. **No log emitted.** Operators see the "fallback" chart and don't know KDE failed.

**MR898 below.**

### Documentation per Report 0164 cross-link

The 4 try blocks document scipy soft-dep but DON'T document why broad-except is used at line 285. **Pattern**: utility/plot modules under-document broad-except discipline vs analysis modules.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR898** | **`reports/reporting.py:285+292+302+311` broad-except blocks have NO logger.warning** | 7th silent-failure site project-wide. **Should `logger.debug("KDE fallback: %s", exc)`** at minimum. | Medium |
| **MR899** | **No `noqa: BLE001` on broad-except** at line 285 + 302 | Pre-commit ruff would flag (per Report 0146 `ruff` hook). Either pre-commit not run on this file, or hook misconfigured. | Low |
| **MR900** | **scipy ImportError fallback is correct discipline** | Cross-link Report 0113 + 0129. Module degrades when scipy missing. | (clean) |

## Dependencies

- **Incoming:** cli.py (Report 0163), per Report 0140 packet_builder downstream.
- **Outgoing:** numpy, pandas, matplotlib + scipy (soft).

## Open questions / Unknowns

- **Q1.** Does pre-commit ruff actually skip this file or is BLE001 not flagged?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0171** | Security spot-check (in flight). |

---

Report/Report-0170.md written.
