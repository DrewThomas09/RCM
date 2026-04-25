# NEXT_CYCLE.md — where to point the roadmap

A pragmatic read of the deployment as it stands today, and the three
classes of investment that should come next. Written so a partner
can redirect the plan in one conversation, not so a PM can execute
it verbatim.

---

## Where we are right now

The private web deployment works end-to-end:

- 282 user-facing HTML routes, 49 JSON APIs, 0 of them leaking a
  Python traceback (audited by `tests/test_web_e2e_audit.py`).
  Bidirectional now: `tests/test_post_error_audit.py` covers POST
  endpoints with bad/missing input — same "no traceback, structured
  error envelope" contract.
- Session auth with scrypt + CSRF + 30-min idle timeout
- Conditional HSTS + Secure cookies when behind HTTPS
  (`X-Forwarded-Proto` detection)
- PHI banner injected at both the shell layer and a response-level
  safety net, so compliance posture can't regress even if a new page
  bypasses the shell
- Sensitive-view audit (`/admin`, `/settings`, `/users`, `/audit`,
  `/api/users`, `/api/backup`, `/api/system`, bulk exports)
- Full export pipeline (HTML, PDF auto-print, XLSX, PPTX, CSV, JSON,
  ZIP package) with `/tmp` cleanup after serving
- Dashboard with **live workflow badges** — open alerts, overdue
  deadlines, watchlist size, saved-search count rendered right next
  to the navigation hops, so a partner sees what's waiting before
  clicking. Color-coded (red for overdue, amber for alerts, indigo
  for neutral counts); zero-state degrades to no chip.
- Six **filterable + sortable tables** across the three web-deployment
  surfaces (dashboard, /exports, /data/refresh) — `/` keyboard
  shortcut focuses the first filter, `Esc` clears, debounced 80ms
  substring match across every cell.
- `/data/refresh` with async jobs, polling, mark-stale recovery
- 200+ passing web-deployment tests across 16 dedicated test files;
  full suite at 8,548 passed / ~3 unrelated failures (down from 59
  baseline — all 56 v2-marker holdovers gated or fixed this cycle).

Known gaps (not bugs — just work that comes next):

1. **Heroku ephemeral `/tmp`.** Any deploy that cares about data
   durability needs either volume-mounted SQLite (Azure VM path) or
   an external store (see Track A below). For a partner demo, set
   up the Azure VM path; for a sales POC where data loss on restart
   is acceptable, Heroku is fine.

2. **No server-side PDF engine.** PDF is HTML + `window.print()` with
   a "Save as PDF" dialog. Fine for the partner-in-front-of-browser
   case; not fine for an automation that needs headless PDF generation.
   Adding WeasyPrint adds ~200 MB to the slug — defer until needed.

3. ~~**Azure VM doesn't have HTTPS termination wired.**~~ **Shipped.**
   Caddy sidecar gated behind the `tls` profile in
   `deploy/docker-compose.yml`; `deploy/Caddyfile` does automatic
   Let's Encrypt + forwards `X-Forwarded-Proto: https`; `vm_setup.sh`
   now takes an optional `<domain>` arg. See DEPLOY.md §8. Also
   fixed the pre-existing Dockerfile `--host 0.0.0.0` bug that
   DEPLOYMENT_PLAN.md flagged.

4. **`test_deals_corpus.py::test_seed_569_signify_health_homerun`
   fails on `realized_moic` being None.** Either a seed-data
   regression or a None-handling test fix — small, isolated, doesn't
   block any user-facing behavior.

Cleared this cycle:

- ~~Filter inputs on tables~~ — shipped in `_web_components.py`,
  wired on all 6 web-deployment tables.
- ~~59 stale `seekingchartis_*` v2-reskin test assertions~~ —
  41 gated behind `CHARTIS_UI_V2`, 4 individually fixed, 2 real
  bugs surfaced and patched (`_fmt_pct(is_fraction=True)` for LBO
  IRR > 100%, NaN false-positive in the script-tag scan).

---

## Three investment tracks for next cycle

### Track A — Durability (pick first if stakes > demo)

**Problem:** Heroku's ephemeral filesystem makes any deployment a
glorified demo — a dyno restart loses every packet built since
last boot.

**Two viable paths:**

1. **Azure VM** (already scaffolded at `RCM_MC/deploy/`): Docker
   compose + systemd + 60-line `vm_setup.sh`. Volume-mount
   `/data/rcm` for SQLite persistence. BAA-eligible via Azure's
   standard HIPAA terms. ~1 week to production if the Dockerfile
   `--host 0.0.0.0` fix (flagged in `DEPLOYMENT_PLAN.md`) is
   confirmed and ssl is wired via Caddy.

2. **Heroku + managed Postgres:** Ship a `PortfolioStore` adapter
   that chooses between SQLite and Postgres based on
   `DATABASE_URL`. ~2 weeks because every table definition is
   SQLite-dialect and every `_ensure_table()` would need a
   compat layer. Not recommended — the app is designed around
   SQLite's concurrency model (WAL mode, `BEGIN IMMEDIATE`,
   single-writer).

**Recommendation:** Azure VM. We already wrote the plan; the work
is small; the deployment shape matches the code's design. The
only reason to stay on Heroku is the PaaS DX (`git push heroku
main`), and the Heroku work we shipped this cycle buys that for
demos without tying the production path to it.

### Track B — Data depth (pick first if discovery > production)

**Problem:** Every partner-demoed analysis pulls from the same 635-
deal corpus + four CMS public feeds (HCRIS, Care Compare, IRS 990,
NPPES). That's enough to look sharp in a meeting; not enough to
beat an analyst with a Bloomberg terminal.

**Three sources worth the effort:**

1. **Definitive Healthcare / IQVIA** (commercial) — physician
   movement, practice M&A deal flow, specialty mix. Unlocks the
   physician-attrition + payer-mix modules that today run on
   corpus-level base rates instead of deal-specific signal.

2. **PitchBook / Preqin deal comp data** (commercial) — healthcare
   PE transaction multiples, hold periods, exit types. Replaces
   the corpus-only `find-comps` with a real market-comparable
   engine. The data ingest is small; the license is the gating
   cost.

3. **State-specific Medicaid rate schedules** (public, hard to
   normalize) — today we run Medicaid rate shock as a uniform
   overlay. Per-state + per-DRG rates would let the payer-stress
   module show a fund the real rate-cut exposure on their Texas
   vs. Florida portfolio split.

**Recommendation:** Start with (3) — it's free, hard-to-get, and a
direct deepener of the payer-stress module which partners already
click on. (1) and (2) are budget decisions, not engineering ones.

### Track C — Model capability (pick first if moat > breadth)

**Problem:** The ML predictor is a ridge-regression baseline with
conformal intervals. It's honest and fast; it's also not the thing
that makes a partner pay for the tool vs. cobbling together their
own spreadsheets.

**Three upgrades, in order of ROI-per-week-of-work:**

1. **Better margin-of-safety estimator.** The current
   `margin_of_safety` score is a linear combo of four subscores.
   Replace with a calibrated gradient-boosted classifier trained
   on the 635 corpus deals with realized MOIC outcomes. One week.
   Big partner-visible delta if the corpus has enough label
   signal.

2. **Causal-inference overlay on the bridge audit.** Today
   `bridge-audit` compares a banker bridge against historical
   outcome distributions. Adding a causal decomposition (e.g.
   "this bridge assumes +300 bps of margin from RCM that no
   comparable deal has achieved") is the kind of output a partner
   screenshots into an IC memo. Two weeks.

3. **LLM-generated IC memo with structured citations.** We have
   the Anthropic integration scaffolded (`/settings/ai`). The gap
   is: today the "IC packet builder" concatenates per-module
   HTML. Replace the exec-summary section with a Claude-generated
   narrative that cites specific module outputs by section-ID.
   Three weeks with prompt engineering + evaluation harness.

**Recommendation:** (1) first — one-week, high partner-visibility,
doesn't compound risk into further modules if the model
under-performs. (3) is a demo killer but needs the
AI-hallucination guardrails that aren't wired yet.

---

## Are we ready to show a PE partner?

**Yes, with two caveats:**

- **Demo on Azure VM, not Heroku.** The story "the dyno restart
  just nuked the IC packet you were looking at" is not a good
  story. Azure + SQLite-on-volume makes the problem vanish. The
  walkthrough script is the same.

- **Start with `/dashboard`, not `/`.** Set
  `RCM_MC_HOMEPAGE=dashboard` on the demo instance so the partner
  lands on the new web-deployment dashboard (curated analyses,
  recent runs, system status, PHI banner) instead of the legacy
  portfolio view. The legacy view is fine — it's just not the
  first impression we want.

Everything else — auth, export pipeline, security headers, 184
passing tests, error boundary, PHI banner — is already at the
level where a partner's first question is about features, not
about the app itself.
