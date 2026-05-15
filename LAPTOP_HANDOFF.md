# PE Desk — Laptop Handoff

Self-contained guide to get the pedesk.app codebase running on your laptop in Cursor, with all current state and pending work tracked.

**Date written:** 2026-05-15
**Production URL:** https://pedesk.app
**Repo:** https://github.com/DrewThomas09/RCM

---

## 1 · Clone the repo (5 minutes)

```bash
cd ~/dev                  # or wherever you keep code
mkdir -p RCM_MC
cd RCM_MC
git clone https://github.com/DrewThomas09/RCM.git .
```

> **Note:** The repo has a doubled-dir structure — once cloned, the actual code lives at `~/dev/RCM_MC/RCM_MC/` (one level deeper). This is intentional, don't "fix" it. Most commands run from `~/dev/RCM_MC/RCM_MC/`.

If git asks for credentials, you'll need a GitHub Personal Access Token (PAT) with `repo` scope, or set up SSH:
```bash
ssh-keygen -t ed25519 -C "your@email.com"
cat ~/.ssh/id_ed25519.pub   # copy this, paste into GitHub → Settings → SSH keys
# then change remote:
cd ~/dev/RCM_MC
git remote set-url origin git@github.com:DrewThomas09/RCM.git
```

---

## 2 · Open in Cursor

```bash
open -a Cursor ~/dev/RCM_MC
```

Or: open Cursor → File → Open Folder → select `~/dev/RCM_MC`.

Cursor will index the repo (~1 min on first open). The most important paths to remember:
- `RCM_MC/rcm_mc/server.py` — main HTTP handler
- `RCM_MC/rcm_mc/ui/` — every page renderer
- `RCM_MC/rcm_mc/ui/_chartis_kit.py` — design system primitives (`ck_page_title`, `ck_panel`, etc.)
- `RCM_MC/CLAUDE.md` — coding conventions (READ THIS FIRST)

---

## 3 · Python environment

Python 3.10+ required. Tested on 3.14. The project uses **stdlib-heavy** code — only 3 runtime deps beyond stdlib.

```bash
cd ~/dev/RCM_MC/RCM_MC

# Make virtual env
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode + dev deps
pip install -e ".[dev]"
```

If `pip install` fails because pyproject.toml has `name = "seekingchartis"` (legacy package name): that's expected, install still works.

---

## 4 · Run locally

```bash
cd ~/dev/RCM_MC/RCM_MC
source .venv/bin/activate
python demo.py
```

`demo.py` seeds a local SQLite DB and starts the server. It will print a URL like `http://localhost:8080` and auto-open your browser.

Open mode: zero users in DB = no auth required for `/`. Once you create a user via `/users`, you'll need to log in. That mirrors prod behavior exactly.

To create an admin user from the CLI (skip the UI):
```bash
python -m rcm_mc.portfolio_cmd --db demo_portfolio.db users create \
  --username yourname --password "Strong!1" --role admin
```

---

## 5 · Production state on 2026-05-15

### What's live on pedesk.app

All of these merged today (PRs #41–#68):
- ✅ **Rebrand:** Seeking Chartis → PE Desk (everywhere)
- ✅ **Marketing page:** new Claude Design port at `/` (anonymous)
- ✅ **Module directory:** new card layout at `/module-index`
- ✅ **Quick-access cards** on `/app` (top of dashboard)
- ✅ **Morning-brief panel grid** on `/app`
- ✅ **Paired-block layout** on 14 surfaces: `/hold-analysis`, `/backtest`, `/sector-momentum`, `/irr-dispersion`, `/sponsor-heatmap`, `/payer-concentration`, `/covenant-headroom`, `/lbo-stress`, `/exit-multiple`, `/capital-pacing`, `/backtester`, `/reit-analyzer`, `/denovo-expansion`, `/locum-tracker`
- ✅ **Refined editorial palette** (warmer neutrals, deeper teal)
- ✅ **Day-one weekday eyebrow** (no more "MONDAY MORNING" on a Wednesday)
- ✅ **Login no-prefill** (security improvement)
- ✅ **Auth bypass on `/`** (marketing page now reachable anonymously)
- ✅ **Deploy health check fixed** (hits `/healthz` not `/`)
- ✅ **Quick-access content gutter** fixed (PR #67)
- ✅ **Deal Profile durable title** (PR #68 — non-dismissible ck_page_title pattern)

### Production credentials

- **Admin user:** `andrewt@chartis.com` / `Demo1234`
- **Demo user:** `demo` / `DemoPass!1`

You can manage all users at https://pedesk.app/users once signed in.

---

## 6 · Open PRs awaiting merge (as of 2026-05-15)

| PR | Branch | Page | Status |
|---|---|---|---|
| #69 | `fix/checklist-action-column` | `/diligence/checklist` phases — action column wrap fix | Open |
| #70 | `fix/thesis-pipeline-page-title` | `/diligence/thesis-pipeline` durable title + explainer | Open |
| #71 | `ux/logo-pure-wordmark` | Topbar logo — pure typographic wordmark (drops circle/arc mark) | Open |

To merge from laptop: visit each URL in GitHub, click "Merge pull request." Each auto-deploys to pedesk.app in ~2 min after merge (serialized by concurrency lock).

The 5 older PRs in the open list (#25, #19, #18, #17, #6) are stale long-running branches — leave them alone or close them, they're not part of the active work.

---

## 7 · Pending UI punch list (priority order, 22 items)

Walkthrough on 2026-05-15 surfaced these — work **one fix per PR**, never batch.

### Tier 0 — real bug (do first)
1. `/ebitda-bridge` — span error in confidence section (rendering bug)

### Tier 2 — page titles + clarity (in walkthrough order)
2. `/portfolio/heatmap` — no durable title, unclear purpose
3. `/portfolio/map` — no title, white dots unclear
4. `/portfolio/risk-scan` — no title, fonts/colors don't match rest
5. `/portfolio/analytics` — shows corpus not portfolio (semantic confusion), weird box
6. `/sponsor-track-record` — weird description box, no good title, huge numbers
7. `/payer-intelligence` — small box, no title
8. `/pipeline` — no title above funnel
9. `/hospital-screener` — no title, just one box
10. `/predictive-scanner` — no title, no clear purpose
11. `/pe-intelligence` — no title, fonts/boxes inconsistent
12. `/deal-screening` — no title
13. `/comparable-finding` — instructions box off-centered
14. `/conference` — no title
15. `/benchmarks` — no title, "pick a fixture" looks like raw text
16. `/hcris-xray` — no title
17. `/counterfactual` — title is a question (weird), button should be navy
18. `/compare` — no title, "pick two fixture" UX unclear
19. `/bankruptcy-survivor` — title on right (weird placement), needs description
20. `/predictive-denial-model` — should match QOE memo style, button color wrong
21. `/deal-autopsy` — no title, library comparison broken, weird spacing
22. `/physician-attrition` — buttons too close together (spacing)

### Reference pages (gold standard — do NOT touch)
- `/qoe-memo` — user called "great"
- `/provider-economics` — user called "good"
- `/ingest` — user called "okay"
- `/lp-update` — user called "good"

### Established fix patterns

- **Pattern A — page title:** replace dismissible `ck_section_intro` (or shell `editorial_intro=`) with `ck_page_title(..., eyebrow=...)` + non-dismissible italic explainer `<p>`. Reference: PR #68 ([deal-profile](https://github.com/DrewThomas09/RCM/pull/68)), PR #70 ([thesis-pipeline](https://github.com/DrewThomas09/RCM/pull/70)).
- **Pattern B — layout/spacing:** widen grid columns, add `white-space: nowrap`, fix CSS. Reference: PR #67 (quick-access gutter), PR #69 (checklist action column).
- **Pattern C — style mismatch:** swap to ck_* primitives + editorial tokens. Reference page: `/qoe-memo`.
- **Pattern D — semantic naming:** if a page named "portfolio" shows corpus, rename or re-scope data. URL stays.
- **Pattern E — real bug:** find root cause, fix narrowly.

---

## 8 · Dev workflow on laptop

Same as you've been doing — small PRs, never batch, one page per PR.

```bash
# Fresh branch off main
git checkout main
git pull origin main
git checkout -b fix/some-page-title

# Edit files in Cursor
# ...

# Smoke-test render before committing
cd ~/dev/RCM_MC/RCM_MC
python -c "from rcm_mc.ui.your_page import render_your_page; print(len(render_your_page()))"

# Run any relevant tests
python -m pytest tests/test_your_page.py -v

# Commit
git add <files>
git commit -m "fix(your-page): short description"

# Push and PR
git push -u origin fix/some-page-title
gh pr create --base main --title "..." --body "..."

# Merge PR via GitHub web UI → auto-deploys to pedesk.app
```

Test budget: project has 2,878 tests. Local quick-check pattern (skip the slow integration run):
```bash
python -m pytest -q --ignore=tests/test_integration_e2e.py
```

---

## 9 · Critical guardrails (from CLAUDE.md)

- **No new runtime dependencies** — stdlib + pandas + numpy + matplotlib is the limit
- **Parameterised SQL only** — never f-string into SQL
- **`html.escape()` every user input** before rendering
- **Every page uses `chartis_shell`** from `_chartis_kit.py` — never bespoke HTML pages
- **Open every editorial page with `ck_page_title(title, eyebrow=, meta=)`** — this is the H1 of every page
- **Number formatting:** $ → 2 decimals; % → 1 decimal; multiples → 2 decimals + `x`; dates → ISO
- **State-changing POSTs flash a toast** via `_with_flash(message, tone)` helper

---

## 10 · Things NOT to worry about

- **Production deployment** — auto-deploys from `origin/main` to pedesk.app (no manual action needed)
- **Deploy concurrency** — locked by `concurrency: deploy-pedesk` in `.github/workflows/deploy.yml` — multiple merges serialize automatically
- **Server SSH access** — only needed for one-off ops you'll almost never do
- **Database backups** — DB on the VM, `/api/backup` exists for snapshots, fine to ignore for now

---

## 11 · If something breaks

- **Local server won't start:** check Python version (`python3 --version`), make sure venv is activated
- **Tests failing:** project has ~314 pre-existing baseline failures — only worry about tests in files YOU changed
- **Deploy failed:** check https://github.com/DrewThomas09/RCM/actions — usually the health check at the end, not the rebuild. Production is probably already up.
- **`/` shows 401 anonymously:** somehow the auth-bypass list got reverted, see PR #66 for the fix

---

## 12 · Next steps after laptop is set up

Continue the UI punch list. Per the priority order in section 7, the next fix is:
- **`/ebitda-bridge` span error** (Tier 0 bug)

Or, if you'd rather work in walkthrough order:
- **`/portfolio/heatmap` page title** (next on your visual walkthrough)

Whichever you pick, ship as a single PR per page.

---

## Quick reference

| Thing | Command/URL |
|---|---|
| Clone | `git clone https://github.com/DrewThomas09/RCM.git` |
| Open in Cursor | `open -a Cursor ~/dev/RCM_MC` |
| Run locally | `cd ~/dev/RCM_MC/RCM_MC && python demo.py` |
| Tests | `python -m pytest -q --ignore=tests/test_integration_e2e.py` |
| Production | https://pedesk.app |
| Admin login | `andrewt@chartis.com` / `Demo1234` |
| Open PRs | https://github.com/DrewThomas09/RCM/pulls |
| Conventions | `RCM_MC/CLAUDE.md` |
| Design kit | `RCM_MC/rcm_mc/ui/_chartis_kit.py` |
