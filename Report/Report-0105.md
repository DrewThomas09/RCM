# Report 0105: Tech-Debt Marker Sweep — Whole `rcm_mc/` Refresh

## Scope

Refreshes Report 0015 (whole-repo tech-debt sweep). Adds word-boundary regex (per memory: short-token substring matching false-positives — closes Report 0015 over-count). Sister to Reports 0045 (pe/), 0075 (auth/).

## Findings

### Strict marker count (word-boundary regex)

Command: `grep -rEn '\b(TODO|FIXME|HACK|DEPRECATED)\b' rcm_mc/`

**Result: 2 markers across the entire 50K+-line codebase.**

| File:Line | Marker | Context |
|---|---|---|
| `ui/chartis/ic_packet_page.py:525` | `TODO(phase-7)` | "split into per-section micro-explainers as part [of phase-7]" |
| `ui/chartis/_sanity.py:166` | `TODO(phase-7)` | "subsector-aware guards. The ranges below cover the [generic case]" |

**Both are TODO(phase-7) — labeled with project phase tag (current is phase-4 per CLAUDE.md, so deferred 3 phases out).** Neither is FIXME, HACK, XXX, or DEPRECATED.

### Cross-correction to Report 0015

Report 0015 likely matched on substring `XXX` and counted false-positives in CPT-code labels (e.g. `SURGERY_2XXXX`, `SURGERY_3XXXX` in `diligence/denial_prediction/analyzer.py`). Per memory `feedback_keyword_matching.md`: "short-token substring match silently false-positives." Confirmed here — `\bXXX\b` returns 0 matches but `XXX` substring returns 9 in this one file alone.

**MR502-update (Report 0015 cross-correction): true marker count is 2, not whatever Report 0015 said.**

### NotImplementedError-style stubs (intentional)

`grep "raise NotImplementedError"` returns 8+ matches in 3 files:

| File | Line(s) | Pattern |
|---|---|---|
| `integrations/contract_digitization.py` | 240, 247 | Vendor-API stub raising `NotImplementedError(<endpoint hint>)` |
| `integrations/chart_audit.py` | 244, 252 | Same pattern |
| `market_intel/adapters.py` | 84, 94, 104, 124, 133 | 4 vendor stubs (SeekingAlpha, PitchBook, Bloomberg) |

`market_intel/adapters.py:12-15` documents the pattern explicitly:

> "Stubs are opinionated: they raise NotImplementedError with a clear message so a partner who thinks they're getting live data never silently gets stale or fake values. Replace the stub class with a real HTTP client when a subscription is in place."

**These are intentional unimplemented-vendor contracts, not tech debt.** Counted separately. **Strong discipline.**

### `noqa` density (linter-suppression markers)

Total `noqa` directives: ~556 across whole codebase.

| Top file | noqa count |
|---|---|
| `server.py` | 178 |
| `ui/dashboard_page.py` | 38 |
| `analysis/packet_builder.py` | 29 |
| `ui/ic_packet_page.py` | 15 |
| `ui/portfolio_risk_scan_page.py` | 8 |
| `diligence/bear_case/evidence.py` | 8 |
| `ui/dashboard_v3.py` | 7 |
| ... | ... |

`noqa` clusters in:
1. **server.py (178)** — large file, lazy imports + `BLE001` broad-except patterns dominate (per Reports 0018, 0020).
2. **ui/dashboard_page.py (38)** — likely `E501` (long lines) given HTML-string concatenation per CLAUDE.md UI conventions.
3. **analysis/packet_builder.py (29)** — Report 0020 noted broad-except discipline.

**`noqa` IS a form of tech debt** — every directive marks a deliberate convention violation. But:
- Most likely `E501` (line-length) suppressions per pyproject `ignore = ["E501"]` global. **Wait — if E501 is globally ignored, why per-line noqa?** Q1 below.
- Or `BLE001` (broad-except) and `RUF012` (mutable-default).

### Cross-correction to Report 0099 MR543 + Report 0101 MR553

If pyproject globally ignores E501 (line 118), then per-line `# noqa: E501` is **redundant**. Per file scan: the `noqa`s are likely `BLE001`, `F401` (in re-export __init__.py), `B005`, etc., not E501.

**Implication:** ruff IS running and IS catching things. The 5 unused imports in `domain/custom_metrics.py` (Report 0099) escaping detection is therefore a separate puzzle:
- Either `domain/` is excluded from pre-commit hook coverage, OR
- Pre-commit hooks aren't installed, OR
- Local commits bypass hooks (e.g. `--no-verify`).

Cross-link Report 0056 pre-commit config + Report 0101 MR553. The **real reason** still TBD.

### Closure of Report 0101 MR551 (rcm-lookup entry-point mystery)

`rcm_mc/lookup.py` (17 lines) is a **back-compat shim**:

```python
"""Back-compat shim for `python -m rcm_mc.lookup`.
The real module now lives at ``rcm_mc.data.lookup``."""
from .data.lookup import *  # noqa: F401, F403
from .data import lookup as _impl

def main() -> int:
    return _impl.main()
```

`rcm-lookup` entry-point works — it shims to `rcm_mc.data.lookup.main`. **MR551 closure for `rcm-lookup`.** `rcm-intake` still pending — `rcm_mc/intake.py` doesn't exist; would need to verify same shim pattern or it's a broken binary.

### Tech-debt by subdirectory (refresh)

| Subdir | Strict markers | NotImplementedError | noqa | Verdict |
|---|---|---|---|---|
| `auth/` | 0 (Report 0075) | 0 | minimal | cleanest |
| `domain/` | 0 | 0 | minimal | clean |
| `infra/` | 0 (this report) | 0 | low | clean |
| `data/` | 0 | 0 | low | clean |
| `ml/` | 0 | 0 | low | clean |
| `pe/` | 0 (Report 0045) | 0 | low | clean |
| `analysis/` | 0 | 0 | 29 | broad-except heavy |
| `integrations/` | 0 | 4 | low | intentional stubs |
| `market_intel/` | 0 | 5 | low | intentional stubs |
| `ui/chartis/` | 2 | 0 | varies | only marker home |
| `server.py` | 0 | 0 | 178 | lazy-import + broad-except dominant |

**Project-wide marker discipline is exceptional.** The 2 markers in `ui/chartis/` are explicit phase-7 deferrals.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR585** | **Project has only 2 strict tech-debt markers in 50K+ lines — exceptional discipline OR markers being silently filed elsewhere** | If markers are tracked in a separate system (Linear / Jira) but not in source, the source becomes deceptively clean while real debt accumulates externally. | Low |
| **MR586** | **`server.py` has 178 noqa directives** — by far the highest concentration | Each is a deliberate violation. A future refactor that "cleans up noqas" could regress lazy-imports / broad-excepts that exist for reasons (Report 0020). | Medium |
| **MR587** | **`integrations/` and `market_intel/` have 4-5 NotImplementedError each** — intentional stubs per docstring | If a partner calls these without a vendor subscription, raises. Acceptable per intent, but a "feature complete" claim about market_intel must caveat the 5 stubbed adapters. | Low |
| **MR588** | **`rcm_mc/intake.py` does not exist on main** but is declared in `pyproject.toml:70` as `rcm-intake = "rcm_mc.intake:main"` | Per `find` (this iteration): no `intake.py` at top-level — only `data/intake.py`. The `rcm-intake` console script will FAIL on first invocation with `ModuleNotFoundError: No module named 'rcm_mc.intake'`. **BROKEN ENTRY-POINT.** | **CRITICAL** |
| **MR589** | **`# noqa: F401, F403` in `lookup.py` shim line 7 is overuse** — F403 (star-import) is the actual issue; F401 (unused) doesn't apply for re-exports | Linter suppression carrying along an unrelated code | Low |
| **MR590** | **TODO(phase-7) is not enforced** — no CI check fails when phase-4 ships with phase-7 markers | Markers can drift to phase-12, phase-99, never. Cross-link Report 0072 retention-policy critique. | Low |

## Dependencies

- **Incoming:** Reports 0015, 0045, 0075 baseline.
- **Outgoing:** future iterations can rely on this report's "marker count = 2" finding rather than re-sweeping.

## Open questions / Unknowns

- **Q1.** What `noqa` codes dominate in server.py's 178 hits? (`BLE001` / `B005` / `F401` / `F841` etc.)
- **Q2.** Why does pre-commit (Report 0056) not catch the 5 unused imports in `domain/custom_metrics.py` (Report 0099)? Is the hook installed, or bypassed via `--no-verify`?
- **Q3.** Is the `rcm_mc/intake.py` entry-point really broken, or is there a redirect via `setup.cfg` / `entry_points.py` that bypasses pyproject.toml?
- **Q4.** What is the canonical TODO/FIXME tracking system if the source has only 2 markers? (Linear/Jira/GitHub Issues per Report 0061 reference?)

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0106** | Verify MR588 by attempting `rcm-intake` invocation OR reading shim — if no shim, file a bug ticket. |
| **0107** | Schema-walk `data_source_status` (carried from Report 0102 Q2). |
| **0108** | Map `rcm_mc_diligence/` separate package (carried from Report 0101). |

---

Report/Report-0105.md written.
Next iteration should: verify MR588 — does `rcm_mc/intake.py` exist as a shim, or is `rcm-intake` truly broken?
