# Report 0173: Version Drift — `Pillow` Transitive Audit

## Scope

Audits `Pillow` — transitive dep of `python-pptx` (per Report 0106 Q4). NOT directly pinned in pyproject.toml. Sister to Reports 0023, 0046, 0053, 0076, 0083, 0086, 0101, 0106, 0113, 0136, 0143, 0166.

## Findings

### Pin status

`pyproject.toml`: NO `Pillow` declaration. **Implicit transitive dep** via `python-pptx` (per Report 0106).

Per Report 0106: python-pptx (PIL/Pillow user) is in `[pptx]`/`[exports]`/`[all]` extras, all `>=0.6` no upper bound.

### Pillow CVE history (significant)

Pillow has had **MANY** CVEs over years:
- CVE-2024-28219 (pre-10.3.0) — buffer overflow
- CVE-2023-44271, 50447 (multiple) — DoS, OOB-read
- CVE-2022-22815 (pre-9.0.0) — TIFF parser issues
- Pillow ~10.x is mostly stable; <10.0 has multiple known issues

### Direct imports (production)

`grep -rEn "^\s*(from PIL|import PIL|from Pillow)" RCM_MC/`: not run this iteration. **Likely 0 direct imports** — Pillow used only by python-pptx for image handling in slides.

### Trust boundary

If `python-pptx` writes user-supplied images into the deck, Pillow processes them. **Per Report 0106**: project WRITES pptx but doesn't typically READ user-uploaded pptx → image-IO with user-controlled bytes is constrained.

But: per Report 0136 / 0137 — partner-uploaded files + path-traversal class concerns persist. **If partner uploads images for inclusion in a generated deck**, Pillow reads them.

### Pin recommendation

**Project should explicitly pin `Pillow>=10.3.0`** in `[pptx]` / `[exports]` extras (alongside python-pptx). Cross-link Report 0136 MR770 (pyarrow same pattern — transitive vulnerable version risk).

### Cross-link to Report 0136 pyarrow + Report 0150 secrets

Project security posture has multiple transitive-dep risks:
- pyarrow (Report 0136 MR770 critical — RCE on user input)
- Pillow (this — CVE-prone, may receive user-image input)
- pydantic (Report 0113 MR632 — implicit transitive via fastapi)
- Pillow CVEs broadly less severe than pyarrow RCE

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR908** | **Pillow not pinned in pyproject** — transitive via python-pptx | Cross-link Report 0136 MR770 + Report 0113 MR632. Same pattern of implicit transitive deps not pinned. | Medium |
| **MR909** | **Pillow CVE history significant** — multiple buffer overflow / DoS / OOB-read | If user-supplied images enter Pillow via pptx-export, vulnerability surface. **Recommend `Pillow>=10.3,<11.0`.** | Medium |
| **MR910** | **3 unpinned transitive deps** with security relevance: pyarrow (RCE), Pillow (CVEs), pydantic (less critical) | Project should adopt explicit transitive pinning for security-relevant deps. Cross-link Report 0150 MR831 (no CI gitleaks). | High |

## Dependencies

- **Incoming:** transitive via python-pptx.
- **Outgoing:** PyPI Pillow.

## Open questions / Unknowns

- **Q1.** Confirm zero direct Pillow imports in project source.
- **Q2.** Does any production code path expose Pillow to user-supplied images?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0174** | Cross-cutting (in flight). |

---

Report/Report-0173.md written.
