# Report 0260: MR917 deploy.yml auto-trigger — verification + closure

## Scope

Closes Report 0119 / Report 0120 / MR917: "first merge from feat/ui-rework-v3 → main triggers auto-deploy". Verifies the actual state of `.github/workflows/deploy.yml` on both sides and documents the merge-time gating recipe.

Sister reports: 0119/0120 (original auto-deploy concern), 0246 (branch refresh #8 — main's `3ef3aa3` SSH-fix commit), 0259 (MERGE-CONFLICTS entry 3 prior).

## Findings

### Surprise: main is already gated to manual-only

Reading `.github/workflows/deploy.yml` on `main` (HEAD `2e8a02e`):

```yaml
on:
  # push:
  #   branches: [main]
  workflow_dispatch:
```

Lines 14-17. The `push: branches: [main]` trigger is **commented out**. Auto-deploy on merge to main is **DISABLED on main today**. Only `workflow_dispatch` (manual GitHub Actions UI button) fires the workflow.

The comment block at lines 3-12 explicitly says:

> Once secrets are set and you've verified one manual deploy succeeds, uncomment the `push: branches: [main]` block below to enable auto-deploy on every push to main.

This means **MR917's stated risk (first merge auto-deploys) was based on a stale audit assumption**. Cross-link Report-0246: main's last-known commits include CI hardening (`3ef3aa3`, `7d5afb5`, `1c845db`) which presumably gated the trigger as part of the SSH-quoting fix.

### Real risk: `feat/ui-rework-v3` re-enables auto-deploy

Reading the same file on `origin/feat/ui-rework-v3`:

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:
```

Auto-deploy **enabled**. Plus the branch uses different SSH machinery (`webfactory/ssh-agent` with explicit heredoc rather than main's `appleboy/ssh-action@v1.0.3`).

### So MR917's true shape

The risk is **not** that "main triggers auto-deploy after merge". The risk is that **the feature branch's deploy.yml — which has auto-deploy enabled — will overwrite main's intentionally-gated version** unless the merge author actively keeps the gate.

This is a **textual conflict** in the `on:` block + a **wholesale rewrite** of the SSH steps. Git will either auto-resolve to feat (taking the auto-deploy enable as a side-effect) or ask the merger to choose.

### Required secrets (from main's deploy.yml comment)

| Secret | Purpose |
|---|---|
| `AZURE_VM_HOST` | Public IP / DNS name of the Azure VM |
| `AZURE_VM_USER` | SSH user (typically `azureuser`) |
| `AZURE_VM_SSH_KEY` | Private SSH key (PEM, full contents) |

Verify with `gh secret list -R DrewThomas09/RCM`.

### Steps inside deploy (main's version)

1. SSH to `${{ secrets.AZURE_VM_HOST }}` as `${{ secrets.AZURE_VM_USER }}`.
2. `cd /opt/rcm-mc; git fetch origin main; git reset --hard origin/main`.
3. `cd RCM_MC; docker compose -f deploy/docker-compose.yml pull --quiet; docker compose -f deploy/docker-compose.yml up -d --build`.
4. Health-check loop: 12 × 5s `curl -sf http://localhost:8080/health` until pass.
5. Smoke test: `/health` + `/healthz` + migrations-applied JSON check.

### Closure justification

MR917 was conservatively flagged HIGH on the assumption that `push: branches: [main]` was active on main. It is not. The actual merge risk is documented in MERGE-CONFLICTS.md entry 4: don't let the merge silently re-enable auto-deploy until the operator has confirmed `gh secret list` shows all three secrets and a manual `workflow_dispatch` deploy succeeded.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR917** | (RETRACTED — closed) Original "first merge triggers auto-deploy" was based on stale main state. Real merge mechanics now captured in MERGE-CONFLICTS.md entry 4. | (closure) | (closed) |

## Dependencies

- **Incoming:** GitHub Actions runner (`ubuntu-latest`); Azure VM at `${{ secrets.AZURE_VM_HOST }}`.
- **Outgoing:** docker compose at `/opt/rcm-mc/RCM_MC/deploy/docker-compose.yml`; `appleboy/ssh-action@v1.0.3` (main) or `webfactory/ssh-agent` (feat-branch).

## Open questions / Unknowns

- **Q1.** Is the docker-compose path under `/opt/rcm-mc/RCM_MC/deploy/` accurate post-feat-branch's `RCM_MC/` reorganisations? The path is hardcoded at line 40 of main's deploy.yml with the comment "the deploy/ directory is INSIDE RCM_MC/, not at the repo root." If the feature branch moves it again, the deploy step breaks silently.
- **Q2.** Are the GH secrets (`AZURE_VM_*`) currently set on the repo? Cannot verify from the audit branch — needs `gh secret list` from a privileged operator.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| (operational) | Run `gh secret list -R DrewThomas09/RCM` and confirm all three AZURE_VM_* secrets exist before merging feat/ui-rework-v3. |
| (post-merge) | After a successful manual `workflow_dispatch` deploy, opt into auto-deploy by uncommenting `push: branches: [main]` in a follow-up commit (NOT in the merge commit). |

---

Report/Report-0260.md written.
