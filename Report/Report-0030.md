# Report 0030: Follow-up — `HIPAA_READINESS.md` + `PHI_SECURITY_ARCHITECTURE.md`

## Scope

Resolves **Report 0028 Q3 / MR263** by reading the two PHI-related docs end-to-end on `origin/main` at commit `f3f7e7f`:

- `RCM_MC/rcm_mc/compliance/HIPAA_READINESS.md` (142 lines)
- `RCM_MC/docs/PHI_SECURITY_ARCHITECTURE.md` (447 lines, shipped in commit `638cc4e` per Report 0029)

The question to answer: do these documents acknowledge the cosmetic-only banner gap (Report 0028 MR250) — that `RCM_MC_PHI_MODE` only changes UI HTML and does not enforce PHI handling?

Prior reports reviewed before writing: 0026-0029.

## Findings

### `compliance/HIPAA_READINESS.md` — 142 lines

Title: "HIPAA Readiness Inventory". Opening disclaimer: "This document is a **readiness inventory**, not a compliance certification."

**Engagement modes documented (line 25-31):**

- **Sandbox** — synthetic fixtures only, no PHI. Default for demos / dev.
- **Engaged** — real claims data under signed BAA.

The doc is structured around the three HIPAA Safeguard categories (`§ 164.308` admin, `§ 164.310` physical, `§ 164.312` technical).

**`phi_scanner.py` mention (line 80):**

> "Regex-based detector for the common PHI patterns (SSN, phone, DOB, MRN, NPI, email, street address). Run before:
> - Committing test fixtures
> - Exporting analyst working files out of the engagement sandbox
> - Shipping logs to off-host systems"

**The doc explicitly positions `phi_scanner.py` as a PRE-COMMIT / PRE-EXPORT tool — NOT as a runtime PHI-enforcement layer.** The recommended invocation (lines 89-99) is a `python -c "..."` one-liner integrated into pre-commit hooks.

**`RCM_MC_PHI_MODE` mention: ZERO.** The doc does NOT reference the env var anywhere. Confirmed via `grep -n "PHI_MODE\|phi_mode\|RCM_MC_PHI_MODE"` — only matches are on `phi_scanner` (the file).

**Appendix B — "What This Package Is Not" (lines 130-142):**

> "**Not a DLP product.** `phi_scanner.py` catches pattern-matchable PHI in text — it won't catch PHI embedded in images, PDFs, or proprietary binary formats."

> "**Not a WAF.** Rate-limited login + CSRF + session TLS are the baseline only; deploying to a hostile network requires a reverse proxy with its own WAF / fail2ban layer."

**The doc explicitly disclaims runtime DLP capability.** Combined with the absence of any `PHI_MODE` reference, the inventory is honest about the boundary: PHI scanning is a developer / pre-commit tool, not a runtime gate.

### `docs/PHI_SECURITY_ARCHITECTURE.md` — 447 lines

Per Report 0007 / 0001 file map, this lives at `RCM_MC/docs/PHI_SECURITY_ARCHITECTURE.md`. 447 lines.

`grep -n "PHI_MODE\|phi_scanner\|enforce\|banner"` returns **only 3 hits**:

| Line | Context |
|---|---|
| 252 | "recent UI sprint enforces this in tests)" — about a UI invariant, not PHI |
| 253 | "SQL injection: parameterized queries only (already enforced" |
| 417 | "paths to our service. We require TLS but can't enforce" |

**ZERO references to `RCM_MC_PHI_MODE`, `phi_scanner`, or the banner**. The 447-line architecture doc does not connect to either of the two implementation surfaces (the env var or the scanner module).

The doc was shipped in commit `638cc4e` ("docs: PHI security architecture + BAA plan"). Per Report 0029 MR268, this is **doc-vs-code drift**: the architecture is described in prose; the implementation is a banner without enforcement and a scanner that is unwired.

### Cross-reference findings

| Question | Answer |
|---|---|
| Does HIPAA_READINESS.md acknowledge the banner-vs-enforcement gap (MR250)? | **No.** It doesn't mention the banner at all. The doc treats `phi_scanner.py` as a pre-commit DLP tool, not a runtime gate. **The gap is unrecognized.** |
| Does PHI_SECURITY_ARCHITECTURE.md acknowledge the gap? | **No.** It doesn't reference `RCM_MC_PHI_MODE`, `phi_scanner`, or the banner. **The gap is unrecognized.** |
| Does either doc claim the banner is enforced? | **Neither doc mentions the banner.** So neither claims nor denies enforcement. The misleading claim lives in the banner HTML itself ("🛡️ Public data only — no PHI permitted on this instance"), not in the docs. |
| Is `phi_scanner.py` actually wired anywhere in production runtime? | **No.** Per Report 0028, zero production sites import / call `phi_scanner.scan*`. Only used in pre-commit context per the HIPAA doc. |
| Does the HIPAA doc honestly disclaim what's not implemented? | **Yes.** Appendix B is candid: "Not a DLP product." This is the right disclaimer — but it doesn't extend to the banner. |

### The actual contract documented

Reading both docs together, the **honest contract** is:

1. PHI mode is a **deploy-posture flag** that displays a banner so users know whether the instance has PHI in scope.
2. `phi_scanner.py` is a **developer / pre-commit / pre-export tool** to catch pattern-matchable PHI before files leave the engagement.
3. Runtime PHI enforcement is **NOT promised** in either doc.

**Report 0028 MR250 was wrong to call the banner "misleading."** The misleading claim is the banner's own text ("🛡️ Public data only — no PHI permitted") which **promises something the docs explicitly disclaim**. The HIPAA inventory is honest; the banner text overpromises.

### Refined finding

The gap is **between the banner text and the documented contract**, not between the docs and the code. The right fix is one of:

- **Soften the banner text** to match the documented contract: "🛡️ This instance is configured for public data only. PHI handling requires a separate BAA-signed deployment."
- **Implement enforcement** to match the banner's claim (Report 0028 MR250 fix).

Either fix closes the gap. The current state — strong banner promise + no enforcement + no doc claim — is the worst of three options.

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR275** | **Banner text overpromises vs docs' contract** | The banner says "🛡️ Public data only — no PHI permitted" but neither HIPAA_READINESS.md nor PHI_SECURITY_ARCHITECTURE.md claim runtime enforcement. **Banner is the misleading element.** Soften wording or implement enforcement. | **High** |
| **MR276** | **`PHI_SECURITY_ARCHITECTURE.md` (447 lines) does NOT reference its own implementation surfaces** | Zero mentions of `RCM_MC_PHI_MODE`, `phi_scanner.py`, or the banner across the architecture doc. **Architecture is described in prose with no traceability to code.** Recommend: each architectural claim should cite the implementing module. | **High** |
| **MR277** | **`HIPAA_READINESS.md` and `PHI_SECURITY_ARCHITECTURE.md` are not cross-referenced** | The two docs are independent. A reader of one cannot find the other. The HIPAA doc lives at `compliance/HIPAA_READINESS.md`; the architecture doc lives at `docs/PHI_SECURITY_ARCHITECTURE.md`. Confusing pair. | Low |
| **MR278** | **`PHI_SECURITY_ARCHITECTURE.md` deleted on `feature/workbench-corpus-polish`** (per Report 0007 docs deletion list) | The 447-line doc is gone on that branch. If that branch merges, the architectural rationale is lost. **Pre-merge: confirm the doc has been moved/replaced, not deleted outright.** | Medium |
| **MR279** | **`HIPAA_READINESS.md` survives in `compliance/`** but its sister doc lives at `docs/` | Inconsistent location. A future reader looking for the HIPAA doc in `docs/` won't find it; looking in `compliance/` won't find the architecture. | Low |

## Dependencies

- **Incoming:** any HIPAA-engagement onboarding; any auditor reviewing the platform; future feature branches that touch PHI handling.
- **Outgoing:** the HIPAA doc references `phi_scanner.py`, `audit_chain.py`, `templates/baa_template.md`. The architecture doc references TLS / SQL injection / UI invariants.

## Open questions / Unknowns

- **Q1 (this report).** Should the banner text be softened, or should enforcement be implemented? Product-decision question.
- **Q2.** What does `RCM_MC/rcm_mc/compliance/templates/baa_template.md` contain? Referenced by HIPAA_READINESS.md (line 31).
- **Q3.** What does `audit_chain.py` enforce, and is it actually wired to the request lifecycle?
- **Q4.** Was `638cc4e` (the architecture-doc commit) accompanied by a code commit that wired enforcement, but the wiring was reverted? Git log on `RCM_MC_PHI_MODE` would tell.
- **Q5.** Does `SOC2_CONTROL_MAPPING.md` (sister doc per Report 0026 directory listing) reference the gap?

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0031** | **Resume / kickoff meta-survey** (already requested as Iteration 31). | Pending. |
| **0032** | **Read `compliance/templates/baa_template.md`** | Resolves Q2. |
| **0033** | **Read `compliance/audit_chain.py`** | Resolves Q3. |
| **0034** | **Read `compliance/SOC2_CONTROL_MAPPING.md`** | Resolves Q5. |
| **0035** | **`git log -p RCM_MC/rcm_mc/ui/_chartis_kit.py` filtered for PHI commits** | Resolves Q4 (was enforcement ever attempted?). |

---

Report/Report-0030.md written. Next iteration should: read `compliance/audit_chain.py` to determine whether the audit-trail subsystem fires per-request and whether it tags entries with `RCM_MC_PHI_MODE` state — would close Report 0028 MR261 (audit-log doesn't tag PHI mode) and Report 0021 Q1 (does any module log security events).

