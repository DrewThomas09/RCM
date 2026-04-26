# Report 0190: Orphan Files — 12 Never-Mentioned Subpackages Existence Survey

## Scope

Verifies existence + sizes of 12 of 17+ never-mentioned subpackages from Report 0121 backlog. Sister to Reports 0010, 0040, 0070, 0100, 0130, 0160 (orphan-file lineage).

## Findings

### Existence + size sweep (12 of 17+)

| Subpackage | .py file count | Status |
|---|---|---|
| `ai/` | 6 | exists |
| `analytics/` | 5 | exists |
| `causal/` | 4 | exists |
| `ic_memo/` | 4 | exists |
| `intelligence/` | 5 | exists |
| `irr_attribution/` | 6 | exists |
| `negotiation/` | 5 | exists |
| `portfolio_monitor/` | 4 | exists |
| `portfolio_synergy/` | 4 | exists |
| `screening/` | 4 | exists |
| `site_neutral/` | 5 | exists |
| `verticals/` | 2 | exists (smallest) |

**Total: 54 .py files across 12 subpackages.** Average 4.5 files per subpackage.

### Combined unmapped subpackages — net update

Per Report 0121 + this:
- 12 confirmed-exist subpackages (this report) — **all small** (2-6 files each)
- pe_intelligence/ (276) + data_public/ (313) — large unmapped
- engagement/ (3 files, mapped Report 0182-0185)
- ic_binder, diligence_synthesis (Report 0100) — mapped/partial

**Backlog**: 12 small subpackages (54 files total) + 2 large = **~14 subpackages remain.**

### No orphan-at-package-level

Per `find` (this iteration): all 12 directories exist with content. **None is orphan.** Per Report 0091/0181 inferred: each likely has tests + import paths.

### Filesystem cruft

Not run this iteration. Per Reports 0100, 0130, 0160 (and confirmed Report 0135): zero `.DS_Store`/`.orig`/`.bak` repo-wide.

### Implication for audit pace

12 subpackages × 1 iteration each = 12 iterations to drain THIS portion of the backlog. Plus 270 pe_intelligence submodules + 313 data_public files = far longer.

**Realistic strategy**: spot-check each small subpackage at top-level (1 iteration each) → defer interior. Manageable in 12-15 iterations.

### Sample inference (subpackage-name ↔ purpose)

| Subpackage | Likely purpose |
|---|---|
| `ai/` | Anthropic API + LLM integration (cross-link Report 0025 — partial) |
| `analytics/` | aggregate analytics (likely consumes packets) |
| `causal/` | causal-inference layer (cross-link Report 0094 econ_ontology causal DAG) |
| `ic_memo/` | IC memo rendering (different from `pe_intelligence/ic_memo.py`) |
| `intelligence/` | ambiguous — could be partner-brain related |
| `irr_attribution/` | IRR-attribution math (cross-link pe/ + scenarios/) |
| `negotiation/` | deal-negotiation tools |
| `portfolio_monitor/` | portfolio tracking (different from `portfolio/`) |
| `portfolio_synergy/` | cross-deal synergy analysis |
| `screening/` | hospital screening (cross-link Report 0102) |
| `site_neutral/` | CMS site-neutral payment policy |
| `verticals/` | hospital verticals (smallest — 2 files) |

### Cross-link Report 0093 ml/

Per Report 0093: ml/ has 41 modules with extensive README. **Each of these 12 subpackages is much smaller than ml/.** Likely tighter, more focused.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR952** | **12 small never-mentioned subpackages confirmed extant** with 54 .py files combined | Add to backlog with concrete iteration estimate. | (advisory) |
| **MR953** | **`portfolio_monitor/` vs `portfolio/` name disambiguation** | Different packages. Cross-link Report 0094 ReimbursementProfile collision. Onboarding ambiguity. | Low |
| **MR954** | **`ic_memo/` (top-level) vs `pe_intelligence/ic_memo.py` (sibling)** | Different packages, same name. Already noted in Report 0153. | (carried) |

## Dependencies

- **Incoming:** Reports 0091/0121/0151/0181 backlog lineage.
- **Outgoing:** future iterations.

## Open questions / Unknowns

- **Q1.** What's in `verticals/` (smallest at 2 files)?
- **Q2.** Does `ai/` overlap with Report 0025 Anthropic integration audit?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0191** | Config map (in flight). |
| **0192** | Spot-check `verticals/` (smallest unmapped, closes Q1). |
| **0193** | Spot-check `ai/` (closes Q2 + cross-link Report 0025). |

---

Report/Report-0190.md written.
