# Deploy Status — v5 Editorial UI to `pedesk.app`

**Status: PR open, awaiting your merge.**

PR: https://github.com/DrewThomas09/RCM/pull/24

---

## What you need to do

### 1. Review the PR (5 min)

Open https://github.com/DrewThomas09/RCM/pull/24 and skim the description. Highlights:

- 196 commits since `main` — the entire v5 editorial UI rebuild
- 29/29 local routes smoke-tested green
- Deploy spec (`docker-compose.yml`) updated so `/` lands authenticated partners on the editorial `/app`, not the legacy `/dashboard`
- No new runtime dependencies; same Docker / Caddy / Azure VM topology

### 2. Hit "Merge" (1 click)

The moment you click **Merge pull request** on GitHub:

1. Commit lands on `main`
2. `.github/workflows/deploy.yml` fires automatically
3. Workflow SSHes into the Azure VM (`pedesk.app`)
4. Pulls latest, rebuilds containers, brings them up with `DOMAIN=pedesk.app docker compose --profile tls up -d --build`
5. Health check curls `https://pedesk.app/` 5× until 200/303

You can watch the deploy at https://github.com/DrewThomas09/RCM/actions.

**Estimated wall time: 8–12 minutes** (most of it is the Docker rebuild on the VM).

### 3. Verify the live site (2 min)

Once the workflow turns green:

```bash
# Quick checks
curl -sIk https://pedesk.app/ | head -3
curl -sIk https://pedesk.app/login | head -3
```

Then in a browser:

1. Open https://pedesk.app/login
2. Confirm the chrome is editorial (parchment background, navy topbar, italic-serif "Seeking *Chartis*" wordmark — **not** the dark Bloomberg shell)
3. Log in with your partner credentials (or demo / DemoPass!1 if seeded)
4. You should land on `/app` — Command Center with KPIs + deal table + alerts
5. Click DILIGENCE in the topbar — confirm the new 4-pillar landing page renders (this was a 404 before this deploy)
6. Cmd+K opens the command palette
7. Click ★ on any deal page — toast should pop in the bottom-right

If any of those fail, see Rollback below.

---

## What's changing on `pedesk.app` after merge

| Before (legacy) | After (v5 editorial) |
|---|---|
| Dark Bloomberg shell — black background, amber accents | Parchment + navy + teal editorial palette |
| `/` → `/dashboard` (legacy table view) | `/` → `/app` (editorial Command Center) |
| `/diligence` returned 404 | `/diligence` is a 4-pillar landing page over 24 surfaces |
| 5-section top-nav | 6-section top-nav (added Diligence) |
| No command palette | Cmd+K over 69 surfaces |
| Bare "no items" empty states | `ck_empty_state` cards with icons + CTAs |
| Plain HTML 404 | Editorial 404 with 4 nav-back chips |
| State-changing POSTs were silent | Toast/flash confirmations |
| SSO buttons on login (Google / Microsoft / SAML) that didn't connect | Removed |
| Demo credentials shown on login as a panel | Pre-filled in the form fields |
| Topbar wordmark had a visible gap inside "Seeking Chartis" | Fixed |

---

## Rollback (if the deploy goes red)

The deploy workflow has a built-in health check that fails the run if `https://pedesk.app/` doesn't return 200/303 within ~30 seconds of the rebuild. If that fails OR if you visit the live site and something looks broken:

```bash
ssh azureuser@pedesk.app
cd /opt/rcm-mc
sudo git log -3 --oneline                    # confirm latest commit
sudo git reset --hard cc5d541d               # last green main before this merge
cd RCM_MC/deploy
sudo DOMAIN=pedesk.app docker compose --profile tls up -d --build
```

That gets you back to the pre-merge state in ~3 minutes. Then file an issue / report what broke and I'll patch.

---

## Known cosmetic gaps (not deploy-blocking)

These ship with the editorial deploy but are tracked for follow-up:

| # | Gap | Severity |
|---|---|---|
| 1 | 13 of 24 diligence sub-pages still have hand-rolled headers (no `ck_page_title` H1). They render fine, just visually inconsistent with the 11 already swept. | Cosmetic |
| 2 | `/dashboard` still exists alongside `/app` — anyone with a bookmarked `/dashboard` link gets the legacy chrome. Suggest a 301 redirect or removal next pass. | Cosmetic |
| 3 | `/admin`, `/audit`, `/forgot` (password reset) still on legacy chrome. | Cosmetic |
| 4 | Mobile / tablet layout below 880px collapses but tables horizontal-scroll. Desktop-first. | Out of scope for this deploy |
| 5 | ~13 `<style>` tags inlined per-page (LP Update, Watchlist, Pipeline funnel, etc.) — should be promoted into `_chartis_kit.py`. | Tech debt |

None of these block the deploy or break partner workflows.

---

## After it's live

Recommended next slices, in order of customer impact:

1. **Sweep remaining 13 diligence sub-pages** to `ck_page_title` so the section reads identically across all 24 surfaces. ~1 commit per surface, 1 hour total.
2. **Wire the remaining 6 state-change POSTs** (tags add/remove, archive/unarchive, snapshot register, sim-input save, rerun, bulk ops) into the toast/flash system.
3. **Rebuild `/dashboard`** with editorial chrome OR redirect it to `/app` outright.
4. **Mobile / responsive treatment.** Bigger lift; needs a scoping conversation.
5. **Onboarding tour for sessions 1–3** — first-time partners need a 30-second guided intro.

---

## Files that document the work

- Root README: [`README.md`](README.md)
- Package README: [`RCM_MC/README.md`](RCM_MC/README.md)
- UI module README: [`RCM_MC/rcm_mc/ui/README.md`](RCM_MC/rcm_mc/ui/README.md)
- Coding conventions for AI assistants: [`RCM_MC/CLAUDE.md`](RCM_MC/CLAUDE.md)
- Azure deploy guide: [`AZURE_DEPLOY.md`](AZURE_DEPLOY.md)
- Deployment plan (full assessment): [`DEPLOYMENT_PLAN.md`](DEPLOYMENT_PLAN.md)

---

## TL;DR

**Your one job: open https://github.com/DrewThomas09/RCM/pull/24 and click Merge.**

Everything else — git pull, Docker rebuild, Caddy TLS, health check — runs automatically on the Azure VM. After ~10 minutes, https://pedesk.app/ is live with the v5 editorial UI.
