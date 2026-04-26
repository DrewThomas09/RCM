# Report 0120: Follow-up — 4 commits between `f3f7e7f` and `3ef3aa3` + Branch Divergence Discovery

## Scope

Resolves Report 0089 Q5 + Report 0119 Q1 — enumerate commits between `f3f7e7f` (former local main HEAD) and `3ef3aa3` (current origin/main HEAD). **Discovers branch divergence** with cross-correction implications for Report 0116.

## Findings

### The 4 commits

`git log f3f7e7f..3ef3aa3 --oneline`:

| # | Hash | Time (UTC-5) | Subject |
|---|---|---|---|
| 1 | `2e17a98` | 2026-04-25 16:19 | ci: enable auto-deploy to pedesk.app on push to main |
| 2 | `1c845db` | 2026-04-25 16:29 | trigger: test deploy after gh secret set |
| 3 | `7d5afb5` | 2026-04-25 16:34 | ci: switch to webfactory/ssh-agent for Ed25519 compatibility |
| 4 | `3ef3aa3` | 2026-04-25 16:40 | ci: fix SSH quoting — use env vars + heredoc for secret expansion |

**21-minute CI debug session** between 16:19 and 16:40 on 2026-04-25.

### Pattern: classic deploy-debugging cycle

1. **2e17a98** (`+76 / -54` to deploy.yml): enable auto-deploy
2. **1c845db** (empty trigger commit): test the new deploy
3. **7d5afb5** (`+12 / -8`): SSH key incompatible (Ed25519) — switch action
4. **3ef3aa3** (`+14 / -12`): SSH quoting still broken — heredoc fix

### Co-author

All 4 commits: `Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>`. Confirms an autonomous-loop or pair-with-Claude session, NOT manual ops.

### Files touched

**ALL 4 commits touch only `.github/workflows/deploy.yml`** (plus `1c845db` is empty). Single-file edits — disciplined.

### NEW MAJOR FINDING — branch divergence

`git merge-base origin/main main`:

```
f3f7e7f3424b7ee80f775f0656f9df96f38ea2c2  (chore(repo): deep cleanup)
```

**`f3f7e7f` is the common ancestor.** From there:
- `origin/main` advanced **4 commits** (the deploy-debug session above)
- `main` (local) advanced **115 commits** (the audit chain)

**These two paths share NO commits past the ancestor.** Local main and origin main have **diverged** — neither is a fast-forward of the other.

### CRITICAL CROSS-CORRECTION TO REPORT 0116

Report 0116 audited `.github/workflows/deploy.yml` **on local main** and concluded:

> "**Trigger**: `workflow_dispatch` ONLY. Lines 15-16 have the auto-trigger commented out: ..."
> 
> "MR660 low: deploy.yml auto-trigger commented out — manual-only until verified, but no TODO reminder."

**REALITY (per `git show origin/main:.github/workflows/deploy.yml`):**

```yaml
name: Deploy to Azure VM

on:
  push:
    branches: [main]
  workflow_dispatch:
```

**On origin/main, auto-deploy IS enabled.** `push: branches: [main]` is uncommented.

**Report 0116 audited the STALE local-main version of deploy.yml.** Production deploy on `pedesk.app` (per commit message of `2e17a98`) is **already auto-firing on every push to origin/main.**

**MR660 (Report 0116) is RETRACTED.** Auto-deploy is live.

### Origin deploy.yml shape (per the 4 commits)

| Aspect | Origin/main shape |
|---|---|
| Trigger | `push: branches: [main]` + `workflow_dispatch` |
| SSH agent | `webfactory/ssh-agent@v0.9.0` (vs Report 0116's `appleboy/ssh-action`) |
| Secret name | `secrets.SSH_KEY` (vs Report 0116's `AZURE_VM_SSH_KEY`) |
| Domain | `pedesk.app` per commit message |
| Steps | record-start-time → ssh-agent → known_hosts → ... |

**The audited local-main deploy.yml is structurally OLDER than origin** — different SSH action, different secret names, different steps.

### Implication for branch state

Per Report 0119: 115 unpushed audit commits on local main. **A `git push origin main` will FAIL** as a non-fast-forward — the 4 origin-only commits would need to be merged or rebased first.

Three options:
- **Merge origin/main into main**: brings in the 4 CI commits; preserves audit history; creates a merge commit.
- **Rebase main onto origin/main**: replays 115 audit commits on top of origin's 4 CI commits; linear history.
- **Push to a separate branch** (e.g. `audit/reports`): leaves origin/main untouched; safer.

Per Report 0089 + 0091 architectural concern: never decided which.

### Cross-link to Report 0096 branch survey

Per Report 0096: `feat/ui-rework-v3` was 24-ahead of origin/main. That count is **based on origin/main's commit count**, not the now-divergent local main. Cross-check unaffected.

### Implications for the audit's correctness

This iteration is the **second time a Report has audited stale local-only state** (first was Report 0089 declaring origin frozen, retracted by Report 0096). **Pattern**: audit reports must `git fetch origin` before claiming origin state, AND distinguish between "what the local working tree shows" vs "what origin/main shows."

For files like `.github/workflows/deploy.yml` that have been modified ONLY on origin (not local), reading the local copy gives a STALE picture.

### Cross-link to MR-counter

Per Report 0119: ~683 risks claimed. This report retracts MR660 → 682 net.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR660-RETRACTED** | **Report 0116 MR660 (deploy.yml auto-trigger commented out) is wrong** for origin | Local main file is stale; origin/main has auto-deploy enabled. | (correction) |
| **MR687** | **Branch divergence: local main and origin/main share only ancestor `f3f7e7f`** | A `git push origin main` would be rejected as non-fast-forward. Decision required: merge vs rebase vs separate-branch. | **High** |
| **MR688** | **Production deploy is auto-firing on origin/main pushes** — but local main has not been pushed in ~5 days | The 4 deploy.yml CI commits worked because they pushed to origin successfully. The 115 audit commits don't trigger deploy because they're never pushed. **Implicit dependency**: if audit chain were force-pushed, it would WIPE the 4 deploy.yml CI commits and break production deploy. | **Critical** |
| **MR689** | **Audit reports may be reading stale files for files modified only on origin** | This iteration found one (deploy.yml). There may be more. Audit must `git fetch origin && git diff main..origin/main` to enumerate the full set of stale-on-local files. | **High** |
| **MR690** | **Origin uses `webfactory/ssh-agent` action** (per `7d5afb5`); Report 0116 audited `appleboy/ssh-action@v1.0.3` (the local-stale version) | Cross-link Report 0116 MR665 — supply-chain risk audit was performed on the wrong action. Re-audit needed. | Medium |
| **MR691** | **`pedesk.app` domain mentioned in commit `2e17a98`** | Cross-link Report 0042 (DOMAIN env var). The deploy target is `pedesk.app`. New surface to audit. | Low |

## Dependencies

- **Incoming:** Reports 0089, 0096, 0116, 0119 all referenced origin state.
- **Outgoing:** future iterations must re-fetch origin and diff main..origin/main before any file-content claims.

## Open questions / Unknowns

- **Q1.** Are there OTHER files modified on origin/main but stale on local? `git diff main..origin/main --name-only` — not fully enumerated.
- **Q2.** Has any deploy run actually succeeded since `3ef3aa3`? Check GitHub Actions run history (out-of-band).
- **Q3.** Is `pedesk.app` documented in CLAUDE.md or AZURE_DEPLOY.md?
- **Q4.** Should the audit chain be merged, rebased, or pushed to a separate branch?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0121** | `git diff main..origin/main --stat` — enumerate ALL stale-on-local files (closes Q1, MR689). |
| **0122** | Schema-walk `deal_overrides` (Report 0118 MR677 backlog). |
| **0123** | Re-audit deploy.yml using origin/main copy (closes MR690). |
| **0124** | Read `infra/data_retention.py` (Report 0117 MR672 carried). |

---

Report/Report-0120.md written.
Next iteration should: `git diff main..origin/main --stat` to enumerate all files stale on local main — closes Q1 + MR689 high.
