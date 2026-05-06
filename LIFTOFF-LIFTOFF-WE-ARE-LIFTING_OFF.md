# 🚀 LIFTOFF · v5 Editorial UI → pedesk.app

> The full walkthrough for taking the v5 editorial rebuild from a green PR to a verified production deploy on `https://pedesk.app`.
>
> Written 2026-05-06. Last verified: PR #24 head `cd96b96c`, CI green across Python 3.11 / 3.12 / 3.14.

---

## TL;DR

**You have one job: open https://github.com/DrewThomas09/RCM/pull/24 and click "Merge pull request".**

The push-to-main webhook fires `.github/workflows/deploy.yml` automatically. The workflow SSHes into the Azure VM, pulls, rebuilds containers, and curls `https://pedesk.app/` until it returns 200/303. Wall time: 8–12 minutes.

This document covers the rest: what happens before, during, and after that click, plus how to verify, troubleshoot, and roll back.

---

## Table of Contents

1. [Pre-flight checklist](#1-pre-flight-checklist)
2. [What's in this deploy](#2-whats-in-this-deploy)
3. [The merge — step by step](#3-the-merge--step-by-step)
4. [What the deploy workflow does](#4-what-the-deploy-workflow-does)
5. [Post-deploy verification](#5-post-deploy-verification)
6. [Partner walkthrough — first 90 seconds on pedesk.app](#6-partner-walkthrough)
7. [Rollback recipe](#7-rollback-recipe)
8. [Troubleshooting](#8-troubleshooting)
9. [Known gaps shipped with this deploy](#9-known-gaps)
10. [What to ship next](#10-what-to-ship-next)

---

## 1. Pre-flight checklist

Everything below was verified before this document was written. Re-verify if it's been more than a few hours since.

| Check | How | Expected | Status |
|---|---|---|:---:|
| PR is open + mergeable | `gh pr view 24 --json state,mergeable` | `OPEN` + `MERGEABLE` | ✅ |
| CI green on all Python versions | `gh pr view 24 --json statusCheckRollup` | 3.11, 3.12, 3.14 all `SUCCESS` | ✅ |
| Local demo healthy | `curl http://127.0.0.1:8785/login` | 200 | ✅ |
| `pedesk.app` currently reachable | `curl -I https://pedesk.app/` | 200/303 | ✅ |
| Deploy workflow on file | `cat .github/workflows/deploy.yml` | exists, triggers on push to `main` | ✅ |
| `RCM_MC_HOMEPAGE=app` set in compose | `grep RCM_MC_HOMEPAGE deploy/docker-compose.yml` | default is `app`, not `dashboard` | ✅ |
| `CHARTIS_UI_V2=1` set in compose | `grep CHARTIS_UI_V2 deploy/docker-compose.yml` | explicitly `1` | ✅ |

If any of those are red, **stop**. Open `DEPLOY_STATUS.md` and walk back through the prep steps.

---

## 2. What's in this deploy

196 commits on `design-v5` since `main`. The full PR description on #24 has the inventory; the highlights:

### Editorial chrome — every page

- **`chartis_shell()`** is now the only render path. Navy topbar (`#0b2341`), parchment body (`#f5f1ea`), teal accents (`#155752`), near-ink text (`#1a2332`). Source Serif 4 + Inter Tight + JetBrains Mono.
- **Top nav**: Home / Pipeline / Diligence / Library / Research / Portfolio. Each section has a sub-nav rail.
- **Auto-breadcrumbs** on every editorial page (Home / Section / Page).
- **Cmd+K command palette** over 69 surfaces.
- **Toast/flash system** confirms state-changing POSTs.
- **Recently-viewed deals** in the user dropdown.
- **Vim-style g+letter quick jumps** + keyboard help (`?`).
- **Width cap** raised to 1720px so pages fill modern displays.

### New editorial primitives

- `ck_page_title` — the H1 of every page (eyebrow + serif + meta).
- `ck_empty_state` — the "no data here" surface (icon + serif title + body + CTA).
- `ck_provenance_tooltip` — partner-grade hover-card explainers.
- `ck_section_intro` — opt-in tutorial intros via the user dropdown.

### Per-page rebuilds (new editorial chrome)

`/app`, `/home`, `/pipeline`, `/portfolio`, `/portfolio/heatmap`, `/portfolio/risk-scan`, `/library`, `/research`, `/notes`, `/sector-momentum`, `/irr-dispersion`, `/comparable-outcomes`, `/regulatory-calendar`, `/alerts`, `/escalations`, `/watchlist`, `/lp-update`, `/find-comps`, `/deal/<id>` (every section), `/analysis/<id>` (workbench), `/models/dcf`, `/models/lbo`, `/predictive-screener`, `/metric-glossary`, `/methodology`, **`/tools`** (new 69-surface index), QoE memo picker, **`/login`** (pre-fill + SSO removed), **editorial 404 + 500** pages, **`/diligence` index** (kills the prior 404 — 4-pillar landing).

### Diligence — 24 surfaces wired

The new `/diligence` index groups them into four pillars:

| Pillar | Surfaces |
|---|---|
| **Profile & Health** | Deal Profile · HCRIS X-Ray · Benchmarks · Physician Attrition · Provider Economics · Management |
| **Thesis & Playbook** | Thesis Pipeline · Checklist · Ingestion · Value Creation · Root Cause · Denial Predict |
| **Audit & Stress** | Risk Workbench · Counterfactual · Compare · Bankruptcy Scan · Payer Stress · Covenant Stress · Bridge Audit · Deal MC · Deal Autopsy |
| **Exit & Synthesis** | QoE Memo · IC Packet · Exit Timing · Reg Calendar · Engagements |

Editorial `ck_page_title` H1 retrofitted on 11 of 24 surfaces (benchmarks, checklist, physician-eu, physician-attrition, management, denial-prediction, deal-mc, thesis-pipeline, compare, hcris-xray, risk-workbench). The remaining 13 still ship with their hand-rolled headers — visually OK but inconsistent; staged for a follow-up sweep (see [§10](#10-what-to-ship-next)).

### Deploy spec changes

`deploy/docker-compose.yml` — flipped `RCM_MC_HOMEPAGE` default from `dashboard` to `app` and added explicit `CHARTIS_UI_V2=1`. Without these two lines, `/` on pedesk.app would still redirect authenticated partners into the legacy chrome even with the editorial code shipped.

### Bug fixes

- 7 Python 3.11 f-string-backslash syntax errors (PR was blocked on this).
- 5 stale tests updated to match new editorial copy / URL contracts.
- Span-escape bugs on 4+ pages (literal `<span class="mn">655</span>` rendering as text).
- 7 pages that 500'd at runtime due to wrong `chartis_shell(body=…)` kwarg.
- `/app` ↔ `/dashboard` infinite redirect loop in default config.
- `v3/chartis.css` was never linked → all `.cad-*` classes were unstyled.
- Deal-name slug resolution everywhere joins `deals.name`.
- IRR dispersion: span escaping, chart sizing, hurdle-line cleanup.
- Wordmark gap inside "Seeking Chartis".

---

## 3. The merge — step by step

### Step 3.1 — Open the PR

```
https://github.com/DrewThomas09/RCM/pull/24
```

Skim the description if you want; the inventory lines up with [§2 above](#2-whats-in-this-deploy).

### Step 3.2 — Click "Merge pull request"

GitHub's standard merge button. Use **"Create a merge commit"** (default) so the 196 commits land as one merge with the editorial-rebuild context preserved.

> **DO NOT** force-push to main. **DO NOT** rebase. **DO NOT** squash. The history is informative — keep it.

The instant you click, three things happen on GitHub side:
1. The merge commit lands on `main`.
2. The `Deploy to Azure VM` workflow auto-fires (you'll see it appear at https://github.com/DrewThomas09/RCM/actions within ~10 seconds).
3. The PR moves to "Merged".

### Step 3.3 — Watch the deploy run

Open the Actions tab: https://github.com/DrewThomas09/RCM/actions

You'll see a new run titled `Deploy to Azure VM`. Click into it. You'll see steps execute in order:

| # | Step | Wall time |
|---|---|---|
| 1 | Record start time | <1s |
| 2 | Start SSH agent | ~5s |
| 3 | Add VM to known_hosts | ~2s |
| 4 | Deploy via SSH | **6–10 minutes** (Docker rebuild on the VM) |
| 5 | Health check (public URL) | ~5–25s (5 retries) |
| 6 | Report duration | <1s |

The bulk of the wait is step 4 — the VM is rebuilding the Python 3.14 image and bringing the containers up. Don't refresh the actions page obsessively; it'll go green when it goes green.

If step 5 (health check) goes red, jump to [§7 — Rollback](#7-rollback-recipe).

---

## 4. What the deploy workflow does

For the curious. From `.github/workflows/deploy.yml`:

```yaml
on:
  push:
    branches: [main]   # this is the trigger — push to main, deploy fires
```

The deploy step SSHes into the VM and runs:

```bash
cd /opt/rcm-mc
sudo git fetch origin main
sudo git reset --hard origin/main
cd RCM_MC/deploy
sudo DOMAIN=pedesk.app docker compose --profile tls up -d --build
```

This:
1. **Pulls latest code** into `/opt/rcm-mc` on the VM.
2. **Resets hard** to `origin/main` — discards any local changes on the VM (none should exist).
3. **Rebuilds containers** — `--build` forces a fresh Python image with the new code; `--profile tls` brings up Caddy too so HTTPS keeps working; `-d` detaches.
4. The `rcm-mc` container picks up the new env defaults from `docker-compose.yml` — including `RCM_MC_HOMEPAGE=app` and `CHARTIS_UI_V2=1` we set in `89e235c`.
5. Caddy provisions/refreshes the Let's Encrypt cert for `pedesk.app` (cached in the persistent `caddy_data` volume — no rate-limit risk).
6. The container's `HEALTHCHECK` directive starts probing `localhost:8080/health` every 30 seconds.

The workflow then runs its own health check from GitHub-hosted runner against `https://pedesk.app/` — 5 retries with 5-second waits. Passes if any returns 200 or 303.

---

## 5. Post-deploy verification

Once the deploy run goes green, do this 6-step check before declaring victory.

### Step 5.1 — Site is alive

```bash
curl -sI https://pedesk.app/ | head -3
# Expected: HTTP/2 303 (redirect to /login or /app)
```

```bash
curl -sI https://pedesk.app/login | head -3
# Expected: HTTP/2 200
```

### Step 5.2 — Editorial chrome is rendering

```bash
curl -s https://pedesk.app/login | grep -oE 'ck-topbar|chartis-tokens|Source Serif 4' | sort -u
# Expected: ck-topbar, chartis-tokens, Source Serif 4
```

If you see `bg:#000` or `class="card"` patterns, the legacy shell is leaking — see [§8 — Troubleshooting](#8-troubleshooting).

### Step 5.3 — Log in

Open https://pedesk.app/login in a browser.

- Form should be **pre-filled** with demo creds (or your partner creds if you've configured them).
- The page should be **parchment-on-navy** with an italic-serif "Seeking *Chartis*" wordmark — **not** a dark Bloomberg-terminal look.
- **No SSO buttons** ("Continue with Google / Microsoft / SAML SSO") — those were removed because they didn't connect to anything.
- **One** PHI mention (the meta-stack tag "DATA: Public only — no PHI") — not two.

Click **Open Command Center →**.

### Step 5.4 — Land on `/app`

You should land on `https://pedesk.app/app` (NOT `/dashboard`). The Command Center shows:
- **KPI tiles** at the top (Active Deals, Universe size, etc.)
- **Deal table** with full deal names ("Cypress Crossing Health" not "ccf")
- **Pipeline funnel** with bone/teal/navy palette (no purple/orange clash)
- **Active alerts panel** with severity-coloured pills
- **Topbar wordmark** "Seeking *Chartis*" with **no gap** between the two words

If you see the legacy dark dashboard, the env vars didn't take effect — see [§8 — Troubleshooting](#8-troubleshooting).

### Step 5.5 — `/diligence` is alive (this was a 404 before)

Click **DILIGENCE** in the top nav. You should see:

- A new editorial landing page titled **"Diligence"** with "RCM PLAYBOOK" eyebrow.
- **Four pillar cards**: Profile & Health · Thesis & Playbook · Audit & Stress · Exit & Synthesis.
- Each pillar lists 5–9 surfaces with one-line blurbs.
- Hover any link — it should bump padding right and tint the arrow teal.

If `/diligence` returns 404, the routing hasn't picked up the new index page — re-verify the deploy completed cleanly.

### Step 5.6 — Smoke test 5 random surfaces

Pick a few from this list and confirm each renders with editorial chrome (parchment + navy topbar):

```
https://pedesk.app/library
https://pedesk.app/pipeline
https://pedesk.app/portfolio/heatmap
https://pedesk.app/alerts
https://pedesk.app/lp-update
https://pedesk.app/deal/ccf
https://pedesk.app/diligence/checklist
https://pedesk.app/diligence/benchmarks
https://pedesk.app/predictive-screener
https://pedesk.app/tools
```

Each should:
- Return 200
- Show the navy topbar
- Show the sub-nav rail under the topbar
- Show breadcrumbs (Home / Section / Page)
- Render in the editorial palette

### Step 5.7 — Functional checks

| Action | Expected behaviour |
|---|---|
| Press **`?`** anywhere | Keyboard shortcut help dialog opens |
| Press **`Cmd+K`** (or `Ctrl+K`) | Command palette opens with 69 surfaces |
| Click ★ on a deal page | Toast pops in bottom-right ("Pinned to watchlist") |
| Click an alert's "Acknowledge" | Toast confirms ("Alert acknowledged") |
| Click the user chip (top-right) | Dropdown shows My Dashboard, Recently viewed, Methodology, Admin, Audit, Sign out, Tutorial intros toggle |

If all 7 of these pass, the deploy is verified. ✅

---

## 6. Partner walkthrough

If you want to run a 90-second tour to confirm a fresh-eyes experience matches the design intent.

### 0:00 — Land on `/login`

- Editorial parchment background.
- Italic "Seeking *Chartis*" wordmark in the top-left.
- Pre-filled demo creds in the form.
- One subtle PHI tag in the left-side meta-stack: `DATA: Public only — no PHI`.
- No legacy SSO buttons.

### 0:05 — Click "Open Command Center →"

- Land on `/app` — the Command Center.
- KPI strip at top (Active Deals: 5 · Universe: 6,024 hospitals · etc.).
- Deal table below with **full names** ("Cypress Crossing Health", "Magnolia Grove Hospital", "Northvale Physician Partners", "Beacon Urban Health", "Sterling Heights Medical").

### 0:15 — Click DILIGENCE in the top nav

- New 4-pillar landing.
- Skim the pillars to see the structure.

### 0:25 — Click "Risk Workbench" in the Audit & Stress pillar

- Editorial H1 "Risk Workbench" with "RCM DILIGENCE" eyebrow.
- 9 panels of risk dimensions.
- Counterfactual advisor at the bottom.

### 0:45 — Press `Cmd+K`

- Palette opens with 69 surfaces.
- Type "lbo" — narrows to LBO Model.
- Press Enter — lands on `/models/lbo/...` for the focused deal.

### 1:00 — Click ★ on the deal page

- Toast pops bottom-right ("Pinned to watchlist").
- Open `/watchlist` — deal is there.

### 1:15 — Click your initials top-right

- Dropdown opens.
- Recently viewed deals shows the deal you just opened.
- Toggle "Tutorial intros: off → on" — refresh `/library` and the editorial intro card now appears at the top.

### 1:30 — Done

If all of that flowed without surprises, the v5 deploy is shipping correctly.

---

## 7. Rollback recipe

If anything goes wrong, here's the path back to the pre-merge state.

### Fastest path (5 minutes)

```bash
ssh azureuser@pedesk.app
cd /opt/rcm-mc

# Confirm where you are
sudo git log --oneline -3

# Reset to the last main commit before the v5 merge.
# As of 2026-05-06 that's cc5d541d.
sudo git reset --hard cc5d541d

# Rebuild containers from the rolled-back code
cd RCM_MC/deploy
sudo DOMAIN=pedesk.app docker compose --profile tls up -d --build
```

That gets you back to the legacy Bloomberg-dark UI. The persistent `/data/rcm` volume + Caddy data are unchanged, so sessions, deal data, and TLS certs all carry over.

### Slower-but-cleaner path (revert PR + redeploy)

```bash
# On your local machine
cd /Users/drewthomas/dev/RCM_MC
git checkout main
git pull origin main
git revert -m 1 <merge_commit_sha>
git push origin main
```

The revert push triggers `deploy.yml` automatically — same workflow, deploys the reverted state.

### What rollback doesn't undo

- `/data/rcm/rcm_mc.db` — your portfolio + alerts + notes table data is untouched. Rollback is purely code; data persists.
- Existing partner sessions — they'll need to log in again because the CSRF secret regenerates per process. Same as any deploy.
- DNS / Caddy / Let's Encrypt — untouched.

---

## 8. Troubleshooting

### "I see the dark Bloomberg theme on pedesk.app"

The editorial code shipped but `CHARTIS_UI_V2` env didn't take effect. Diagnose on the VM:

```bash
ssh azureuser@pedesk.app
docker exec rcm-mc-rcm-mc-1 env | grep -E "CHARTIS|HOMEPAGE"
```

Should print:
```
CHARTIS_UI_V2=1
RCM_MC_HOMEPAGE=app
```

If those aren't set, the compose file didn't get the env update. Force a rebuild:

```bash
cd /opt/rcm-mc/RCM_MC/deploy
sudo docker compose --profile tls down
sudo DOMAIN=pedesk.app docker compose --profile tls up -d --build --force-recreate
```

### "I see /diligence 404"

The routing didn't pick up the new index handler. Check:

```bash
docker exec rcm-mc-rcm-mc-1 grep -A2 'path == "/diligence"' /app/rcm_mc/server.py | head -8
```

Should show:
```python
if path == "/diligence" or path == "/diligence/":
    from .ui.diligence_index_page import render_diligence_index
    return self._send_html(render_diligence_index())
```

If that's missing the container ran an older image. Force rebuild as above.

### "Deploy workflow ran but the site looks unchanged"

Browsers cache aggressively. Hard-refresh: **Cmd+Shift+R** (Mac) or **Ctrl+Shift+R** (Win/Linux). If still stale, clear the site's cookies and reload — the editorial chrome's CSS lives at `/static/v3/chartis.css?v=...` and the version param invalidates older builds.

### "I see literal `<span class="mn">655</span>` text"

That bug was fixed in `e11ce2e` (kit-level SafeHtml support). If it reappears, a new page added a raw HTML kpi value without wrapping in `SafeHtml(...)`. The fix is in `_chartis_kit.py:_esc()`.

### "Health check fails on the deploy workflow"

Means the rebuild didn't bring containers up cleanly. SSH in and look at logs:

```bash
ssh azureuser@pedesk.app
cd /opt/rcm-mc/RCM_MC/deploy
docker compose --profile tls logs --tail=100 rcm-mc
```

Common causes:
- **Python import error** — usually a missing dep in `pyproject.toml`. Look for `ImportError: No module named X` in the log.
- **DB migration failure** — schema changed but migration didn't run. Check `_ensure_table` calls.
- **Port already in use** — `compose down` then `up`.

### "The PR auto-merged but the workflow didn't fire"

Check `.github/workflows/deploy.yml` is on `main`. If you somehow merged before `89e235c` (the deploy-spec fix) was pushed, the workflow on `main` would be stale. Push another commit (or amend a no-op) to re-fire.

---

## 9. Known gaps

These ship with the editorial deploy but are tracked for follow-up. None of them block partner workflows.

| # | Gap | Severity |
|---|---|---|
| 1 | 13 of 24 diligence sub-pages still have hand-rolled headers (no `ck_page_title` H1). They render fine, just visually inconsistent with the 11 already swept. | Cosmetic |
| 2 | `/dashboard` still exists as a route — anyone with a bookmarked `/dashboard` link gets the legacy chrome. Could 301 redirect or remove next pass. | Cosmetic |
| 3 | `/admin`, `/audit`, `/forgot` (password reset) still on legacy chrome. | Cosmetic |
| 4 | Mobile/tablet layout below 880px — rail collapses but tables horizontal-scroll. Desktop-first by design for now. | Out of scope |
| 5 | ~13 `<style>` tags inlined per-page (LP Update, Watchlist, Pipeline funnel) — should be promoted into `_chartis_kit.py`. | Tech debt |
| 6 | 18 of the 24 diligence pages still depend on the shared `_hero()` / `_fixture_selector()` helpers we built; only 6 use the editorial primitives directly. | Tech debt |
| 7 | Saved-searches surface only on `/pipeline` — `/library` and `/research` filter rails don't yet have a save-set affordance. | Feature |
| 8 | No first-run onboarding tour — new partners see KPIs without context. | UX |

Tracked at the end of `DEPLOY_STATUS.md` and at the bottom of the v5 needs-attention report.

---

## 10. What to ship next

In customer-impact order. Each is one focused PR.

### Week 1 (post-deploy polish)

1. **Sweep the remaining 13 diligence sub-pages** to `ck_page_title`. Pattern is identical to the 11 already done; ~1 commit per page.
2. **Editorial 404/500 polish** — confirm both surface the right "try one of these" chips.
3. **Skeleton loading states on 3 slowest packets** — partner stops thinking the app froze.

### Week 2

4. **Group the 24 diligence surfaces into 4 pillared sub-nav buckets** matching the new index.
5. **Wire the remaining 6 state-change POSTs into the toast/flash system** (tags add/remove, archive/unarchive, snapshot register, sim-input save, simulation rerun, bulk ops).
6. **Rebuild `/dashboard`** so `/` doesn't fall back to legacy in any code path.

### Week 3+

7. **First-run onboarding banner on `/app`** for sessions 1–3.
8. **Mobile/responsive treatment**.
9. **"Compare these deals" button on every deal page**.
10. **Save-search everywhere there's a filter rail**.
11. **Provenance tooltips on every numeric** (currently ~6 metrics).

---

## Appendix A — File reference

Files touched by this deploy that are worth knowing about:

| File | Why |
|---|---|
| `RCM_MC/rcm_mc/ui/_chartis_kit.py` | Core editorial design system. `chartis_shell`, `ck_page_title`, `ck_empty_state`, `_SUB_NAV`, `_CORPUS_NAV`. |
| `RCM_MC/rcm_mc/ui/diligence_index_page.py` | The new `/diligence` 4-pillar landing. |
| `RCM_MC/rcm_mc/server.py` | Route handlers; `_route_seekingchartis_home`, `_error_page` (editorial 404/500), homepage `?v3=1` short-circuit. |
| `RCM_MC/deploy/docker-compose.yml` | Production env defaults — `RCM_MC_HOMEPAGE=app` + `CHARTIS_UI_V2=1`. |
| `.github/workflows/deploy.yml` | Push-to-main deploy automation. |
| `RCM_MC/CLAUDE.md` | AI-assistant coding conventions for this repo (updated for v5). |
| `RCM_MC/rcm_mc/ui/README.md` | Editorial kit catalog + authoring conventions. |
| `README.md` (root) | Top-level repo overview. |
| `DEPLOY_STATUS.md` | Companion to this file — slimmer, more action-oriented. |

---

## Appendix B — Quick reference commands

```bash
# Pre-flight check (run from repo root)
gh pr view 24 --json state,mergeable,statusCheckRollup
curl -sI https://pedesk.app/

# After merge — watch deploy
open https://github.com/DrewThomas09/RCM/actions

# Live smoke test
curl -sI https://pedesk.app/
curl -sI https://pedesk.app/login
curl -sI https://pedesk.app/diligence

# Rollback (if needed)
ssh azureuser@pedesk.app
cd /opt/rcm-mc && sudo git reset --hard cc5d541d
cd RCM_MC/deploy && sudo DOMAIN=pedesk.app docker compose --profile tls up -d --build

# Check live env on the VM
ssh azureuser@pedesk.app
docker exec rcm-mc-rcm-mc-1 env | grep -E "CHARTIS|HOMEPAGE|PHI"

# Tail live logs
ssh azureuser@pedesk.app
cd /opt/rcm-mc/RCM_MC/deploy
docker compose --profile tls logs -f --tail=50 rcm-mc
```

---

## Appendix C — Final state at lift-off

```
Branch:           design-v5
Latest commit:    cd96b96c
Commits ahead:    196 (vs origin/main cc5d541)
PR:               #24, OPEN, MERGEABLE
CI:               3.11 ✅ · 3.12 ✅ · 3.14 ✅
Tests:            138 passed, 1 skipped (legacy-only) in 19.66s
Local demo:       http://127.0.0.1:8785/login → 200 in ~5ms
pedesk.app:       https://pedesk.app/ → 200 in ~125ms
Deploy spec:      RCM_MC_HOMEPAGE=app · CHARTIS_UI_V2=1
```

🚀 We are GO for liftoff.

---

*Last updated: 2026-05-06 by the v5 editorial deploy prep. If this document is more than a week old, re-run the pre-flight checks before merging — environments drift.*
