# PEdesk auto-deploy (GitHub Actions → DigitalOcean Droplet)

Every push to `main` runs a fast test gate; if it passes, GitHub Actions
SSHes into the Droplet, fast-forwards the code, reinstalls the package, and
restarts `pedesk.service`. So **merge = deploy**, usually live within a
minute or two.

Workflow: [`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml).
This replaced the former Azure docker-compose deploy.

```
push to main
   └─ job: test   (pytest auth/login/guide-sidebar/guide-endpoints/csrf + server boot)
        └─ job: deploy  (needs: test)   ── SSH ──►  Droplet
             git fetch + reset --hard origin/main
             source .venv/bin/activate && pip install -e .
             sudo systemctl restart pedesk
             curl https://pedesk.app/healthz   (must be 200)
```

Deploys are **serialized** (`concurrency: pedesk-production`,
`cancel-in-progress: true`) so two merges can't restart the service at once.

## What it does NOT touch

Ollama, Tailscale, RAG, Caddy, the `pedesk.service` unit file, and
`/opt/RCM/RCM_MC/.pedesk_prod.env` are all left alone. The deploy only
pulls code, reinstalls the Python package, and restarts the app. Ollama
stays private on the Mac over Tailscale; port 11434 is never exposed.

## Required GitHub repository secrets

Set these in **Settings → Secrets and variables → Actions → Repository
secrets** (or with `gh secret set`):

| Secret | Value | Required |
|---|---|---|
| `DO_HOST` | Droplet public IPv4 — `107.170.18.237` | yes |
| `DO_USER` | SSH login user — `root` (or a sudo-capable deploy user) | yes |
| `DO_SSH_KEY` | **Private** key of a deploy keypair (full PEM, incl. header/footer) | yes |
| `DO_PORT` | SSH port — omit to default to `22` | no |

> Never commit any of these. The private key lives **only** in the GitHub
> secret; the workflow passes it to the SSH action and never echoes it.
> `.pedesk_prod.env` stays git-ignored and is never read by this workflow.

## One-time setup

### 1. Create a dedicated deploy keypair (on your laptop)

Use a separate key for CI — not your personal key — so it can be revoked
independently.

```bash
ssh-keygen -t ed25519 -C "pedesk-deploy@github-actions" -f ~/.ssh/pedesk_deploy -N ""
# creates ~/.ssh/pedesk_deploy (private) and ~/.ssh/pedesk_deploy.pub (public)
```

### 2. Authorize the public key on the Droplet

Append the **public** key to the deploy user's `authorized_keys`:

```bash
ssh root@107.170.18.237 'mkdir -p ~/.ssh && chmod 700 ~/.ssh \
  && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys' \
  < ~/.ssh/pedesk_deploy.pub
```

(If you deploy as a non-root user, that user needs **passwordless sudo for
systemctl** — e.g. a sudoers line
`deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart pedesk`. As `root`,
no sudo config is needed.)

### 3. Store the secrets in GitHub

```bash
gh secret set DO_HOST   --body "107.170.18.237"
gh secret set DO_USER   --body "root"
gh secret set DO_SSH_KEY < ~/.ssh/pedesk_deploy        # the PRIVATE key
# gh secret set DO_PORT --body "22"                    # only if not 22
```

### 4. Confirm the Droplet preconditions (already true for current prod)

- `/opt/RCM` is a git clone of `DrewThomas09/RCM` whose `origin` is the
  public `https://github.com/DrewThomas09/RCM.git` (anonymous fetch works —
  no token needed).
- `/opt/RCM/RCM_MC/.venv` exists and `pedesk.service` runs the app from it.
- `git fetch && git reset --hard origin/main` is safe — the Droplet checkout
  carries no local commits (config/secrets live in the git-ignored
  `.pedesk_prod.env`, not in tracked files).

## Verifying it works

1. Merge any PR to `main` (or run the workflow manually:
   **Actions → Deploy PEdesk → Run workflow**).
2. Watch **Actions** — `test` runs, then `deploy`.
3. The deploy step prints the deployed short SHA and confirms
   `pedesk.service` is active; the health step requires
   `https://pedesk.app/healthz` → `200`.

## Rollback

Auto-deploy always ships the latest `main`. To roll back, revert the bad
commit/PR on `main` (which re-deploys the prior state), or SSH in for an
immediate manual rollback:

```bash
ssh root@107.170.18.237
cd /opt/RCM && git reset --hard <last-good-sha>
cd RCM_MC && source .venv/bin/activate && pip install -e . && sudo systemctl restart pedesk
```

## Security notes

- The deploy key is CI-only and revocable: remove its line from the
  Droplet's `authorized_keys` and delete the `DO_SSH_KEY` secret to cut
  access.
- The workflow never prints secrets and only deploys from `refs/heads/main`
  (fork PRs can't trigger a deploy).
- No credential is persisted in `/opt/RCM/.git/config` — fetch is anonymous
  over HTTPS against the public repo.
