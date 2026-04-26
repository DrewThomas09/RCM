# Report 0181: Kickoff/Resume — 180-Report Status

## Scope

Meta-survey after 180 reports (181st report). Sister to Reports 0001 (kickoff), 0031, 0061, 0091, 0121, 0151. Window: Reports 0152-0180 (29 audit reports).

## Findings

### Headline numbers

- **Reports written**: 180 in `Report/` (per `ls`)
- **Local main**: 1,266 commits, 142 ahead of origin/main
- **Origin/main**: `3ef3aa3` — unchanged since Report 0096
- **`feat/ui-rework-v3`**: 57 ahead, last commit `80223e4` 2026-04-26 01:23
- **Net unique merge risks**: ~960 (~875+ after retractions/corrections)
- **Tables schema-walked**: 16 confirmed; 6+ unconfirmed FK-bearing tables likely (per Report 0180 MR929)

### Major windowed findings (Reports 0152-0180)

| Report | Finding | Severity |
|---|---|---|
| 0152 | pe_intelligence/ inventory: **276 modules, 3.2MB** (largest unmapped) | (HIGH-PRIORITY) |
| 0153 | __init__.py 1,455 names re-exported (4th distinct subpackage org) | MR841 medium |
| 0154 | pe_intelligence has only 10 importers (vs 1455 names — narrow tight coupling) | MR845-848 |
| 0156 | branch refresh #5: feat/ui-rework-v3 +20 commits/day | MR851 high |
| 0157 | feat/ui-rework-v3 NEW dev/ subpackage + initiative_actuals (8th unidentified table) | MR853 high |
| 0158 | test_pe_intelligence.py is 36,212 LOC + 2,973 tests in single file | MR858 high |
| 0163 | **CLOSES 19+ iter cli.py carry**; 5 public fns; 723-LOC mega-function | (closure) |
| 0167 | initiative_actuals: 6th FK; 4th NO-ACTION cascade behavior | MR889 high |
| 0173 | Pillow CVE risk (transitive — unpinned) | MR908+909 medium |
| 0176 | branch contract tests NOT in PR-CI 12-file list (only weekly sweep) | MR916 medium |
| 0178 | RCM_MC_AUTH unset = NO authentication (open server) | **MR921 high** |
| 0180 | FK-frontier was incomplete: 6 confirmed, ~10 more likely | MR929 high |

**~12 high/critical findings in 30-iteration window.**

### Closures vs accumulations

**Closures**:
- Report 0091 #1 (cli.py 19+ iter carry)
- Report 0118 MR677 (deal_overrides)
- Report 0118 MR678 (analysis_runs FK — but partial; 0167 found more)
- Report 0102 Q2 (data_source_status — done in 0107 + 0157)
- Report 0145 Q1 (profiles.yml gitignore)
- Report 0152 Q2 (pe_intelligence/__init__.py)
- Report 0157 MR853 (initiative_actuals)
- Report 0167 Q1 (more FKs — partial close in 0180)

**~9 carries closed in window.**

**Accumulations**:
- pe_intelligence/ deep-dive opened: 276 modules, 1455 names (Reports 0152-0160)
- data_public/ surveyed: 313 modules, 2 subdirs (Report 0172)
- 7+ deal-child tables likely have FKs (MR929)

### Coverage by domain (refresh)

| Domain | Latest reports |
|---|---|
| Repo structure | 0001, 0091, 0101, 0121, 0130, 0151, **0181** |
| Branches | 0006, 0036, 0066, 0096, 0119, 0120, 0126, 0149, 0156, 0179 |
| Build/CI/CD | 0026, 0033, 0041, 0056, 0086, 0101, 0116, 0120, 0143, 0146, 0176 |
| Tests | 0008, 0026, 0038, 0068, 0098, 0128, **0158** |
| Logging/errors | 0020, 0024, 0050, 0080, 0110, 0111, 0140, **0170** |
| Security | 0021, 0028, 0030, 0043, 0051, 0072, 0081, 0104, 0108, 0111, 0114, 0136, 0141, 0145, 0150, **0171, 0178** |
| Database/SQLite | 0017, 0047, 0077, 0087, 0102, 0104, 0107, 0117, 0118, 0123, 0133, 0134, 0137, 0147, 0148, **0167** |
| Configuration | many incl. **0161, 0169, 0178** |
| Server/HTTP | 0005, 0018, 0019, 0048, 0078, 0102, 0108, 0114, 0132, 0138, **0168** |
| External integrations | 0025, 0042, 0049, 0050, 0051, 0055, 0085, 0102, 0104, 0115, 0136, 0145, **0166, 0173, 0175** |
| Dependencies | many incl. **0166, 0173** |
| Documentation | 0014, 0029, 0044, 0089, 0104, 0119, 0134, 0149, **0164** |
| Cross-cuts | 0024, 0054, 0084, 0114, 0144, **0174 (provenance)** |
| Schema | many incl. **0167, 0177, 0180** |
| Compliance/PHI | 0028, 0030, 0043, 0056, 0072 |
| Auth subsystem | many incl. **0147, 0178** |
| ML | 0092, 0093, 0094, 0095, 0098, 0099, 0112, 0129 |
| Dead code / orphans | 0009-0040, 0069-0070, 0099-0105, 0129, 0130, **0159, 0160** |
| Circular imports | 0022, 0052, 0082, 0095, 0112, 0142, **0172** |
| Idempotency / Job queue | 0103, 0108, 0128, 0132 |
| CSRF | 0114 |
| Retries (cross-cut) | 0144 |
| Provenance | **0174 (NEW cross-cut)** |
| FK frontier | 0117, 0133, 0134, 0137, 0147, 0148, 0167, 0180 |

### Net risk count

| Source | Risks |
|---|---|
| Reports 0001-0090 | ~501 |
| Reports 0091-0120 | +182 |
| Reports 0121-0150 | ~+150 |
| Reports 0151-0180 | ~+135 |
| **Total claimed** | **~968** |
| Retractions + corrections | ~12 |
| **Net unique** | **~956** |

### Schema inventory progress

After Reports 0167 + 0180 expansion: **16 walked + ~7-10 likely additional FK-bearing.** Backlog grew from "~6 unidentified" (Report 0151) to "~10-15 unidentified" (Report 0180).

### Top-priority unmapped (refresh)

1. **`pe_intelligence/` 276 modules**: __init__.py + partner_review.py mapped; **270+ submodules unread**
2. **`data_public/` 313 files**: only architectural-cycle survey done (Report 0172)
3. **~17 NEVER-mentioned subpackages** from Report 0121 list
4. **6-7 CMS data-loaders** still unaudited (only `cms_hcris.py` per Report 0115)
5. **2 NEW unmapped modules**: `data/data_scrub.py`, `reports/reporting.py` (Reports 0163, 0164, 0170)
6. **`initiative_actuals + deal-child tables** schema-walks: ~7-10 remain
7. **`server.py` ~11K lines** still ~80% unread

### Project state observations

- **Origin/main frozen at `3ef3aa3` for 7+ days** (since 2026-04-25 16:40)
- **`feat/ui-rework-v3` actively advancing** — at ~20 commits/day cadence
- **Local main 142 commits ahead** of origin/main
- **3-way divergence at `f3f7e7f`** persists
- **No remediation observed** of any of the high/critical MRs in the window

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR932** | **142 unpushed audit commits** — backup risk continues | Cross-link MR925 / MR684 / MR493 lineage. | (carried) |
| **MR933** | **180 reports / ~956 net risks / ~1.5% remediation = ~14.4 risks remediated total** | Per estimate. **Audit-vs-fix gap continues to widen.** | (advisory) |

## Dependencies

- **Incoming:** all future iterations.
- **Outgoing:** Reports 0001-0180.

## Open questions / Unknowns

Carried Q1-Q5 from Report 0151.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0182** | Schema-walk a deal-child table (`deal_notes` / `deal_tags` / `deal_owners` / etc. — per Report 0180 likely-FK list). |
| **0183** | Audit `data_public/__init__.py` (closes Report 0172 Q2). |
| **0184** | Audit `cms_care_compare.py` (2nd of 7 CMS modules per Report 0102 MR558). |

---

Report/Report-0181.md written.
Next iteration should: schema-walk a deal-child table (one of `deal_notes`, `deal_tags`, `deal_owners`, etc. per Report 0180 MR929 likely-FK list).
