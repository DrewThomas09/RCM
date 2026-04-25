# feature/deals-corpus — Seeking Chartis PE-Grade Analytical Suite

Final summary of work on the `feature/deals-corpus` branch.

## Headline numbers

| | |
|---|---|
| Commits vs `main` | **264** |
| Files added | **518** |
| Lines added | **170,580** |
| Backend modules (`rcm_mc/data_public/`) | **316** |
| UI pages (`rcm_mc/ui/data_public/`) | **173** |
| New HTTP routes in `server.py` | **153** |
| Corpus deals loaded across modules | **1,705** |

## What this branch is

A ground-up PE-grade institutional analytical suite layered on top of the Monte Carlo / pe-math core of RCM-MC. Every module follows the same pattern:

1. **Backend** in `rcm_mc/data_public/<module>.py` — stdlib-only, pandas/numpy acceptable, `@dataclass` wrappers, a single `compute_<module>()` public entry point.
2. **UI page** in `rcm_mc/ui/data_public/<module>_page.py` — server-rendered HTML via `_chartis_kit`, dense 6px/10px padding, JetBrains Mono tabular-nums, row striping `#0f172a`.
3. **Route hook** appended to `rcm_mc/server.py` (the only existing file touched, and only via additive blocks).
4. **Nav link** added to both `rcm_mc/ui/_chartis_kit.py::_CORPUS_NAV` and `rcm_mc/ui/brand.py::NAV_ITEMS`.
5. **Smoke-tested** via `python3 -c "... render_<module>({})"` before commit.
6. **Committed & pushed** — each module on its own `auto: <name>` commit.

Nothing renders via the legacy light-theme `_ui_kit.py`; every page uses the dark institutional `_chartis_kit.py` shell (palette: `#0a0e17` bg / `#111827` panel / `#1e293b` border / `#e2e8f0` text / `#3b82f6` accent).

## Architecture constraints honored

- **Never touched `main`** — all work on `feature/deals-corpus`.
- **Never modified existing files** except `server.py` (route hooks only), `_chartis_kit.py` (nav entries only), and `brand.py` (nav entries only).
- **Only created new files** under `rcm_mc/data_public/`, `rcm_mc/ui/data_public/`, `rcm_mc/static/`, plus test files.
- **Zero new runtime dependencies** — Python 3.14 stdlib + existing pandas/numpy.
- **No matplotlib PNGs** — inline SVG only, theme-matched.
- **No rounded corners beyond 4px, no gradients, no glows, no bright decorative color, no emoji icons, no light backgrounds.**

## Corpus foundation

- `rcm_mc/data_public/deals_corpus.py` loads 1,705 PE healthcare deal records across ~120 `extended_seed_N.py` files (seeds 2–121).
- Seeds span urology, dental DSO, home health, infusion, ortho rehab, fertility, dialysis, cardiology, telehealth, RCM, pharma services, lab/path, GI/endoscopy, MSK, podiatry, derma aesthetic, ABA, FQHC, radiology, specialty pharmacy, urology men's health, eye care, sleep medicine, SNF/LTC, PACE, and more.
- Every analytical module pulls live from the corpus via `_load_corpus()` and exposes `corpus_deal_count` so the user always sees the evidence base.

## Modules shipped (by category)

### Portfolio monitoring & operations
`/bolton-analyzer` · `/capital-efficiency` · `/capital-pacing` · `/capital-schedule` · `/capex-budget` · `/cash-position` (via `/treasury`) · `/cin-analyzer` · `/concentration-risk` · `/corpus-coverage` · `/corpus-dashboard` · `/covenant-headroom` · `/covenant-monitor` · `/debt-service` · `/denovo-expansion` · `/dividend-recap` · `/drug-shortage` · `/escrow-earnout` · `/fund-attribution` · `/gpo-supply` · `/growth-runway` · `/hospital-anchor` · `/insurance-tracker` · `/key-person` · `/locum-tracker` · `/module-index` · `/operating-partners` · `/partner-economics` · `/payer-concentration` · `/payer-contracts` · `/pmi-integration` · `/pmi-playbook` · `/portfolio-sim` · `/redflag-scanner` · `/reinvestment` · `/reit-analyzer` · `/rollup-economics` · `/transition-services` · `/treasury` · `/vcp-tracker` · `/workforce-retention` · `/working-capital` · `/zbb-tracker`

### Deal & IC workflow
`/acq-timing` · `/cap-structure` · `/competitive-intel` · `/continuation-vehicle` · `/deal-flow-heatmap` · `/deal-origination` · `/deal-pipeline` · `/deal-postmortem` · `/deal-risk-scores` · `/deal-sourcing` · `/diligence-checklist` · `/diligence-vendors` · `/entry-multiple` · `/exit-multiple` · `/exit-readiness` · `/find-comps` · `/hold-analysis` · `/hold-optimizer` · `/ic-memo-gen` · `/corpus-ic-memo` · `/lbo-stress` · `/peer-transactions` · `/peer-valuation` · `/qoe-analyzer` · `/return-attribution` · `/scenario-mc` · `/secondaries-tracker` · `/sellside-process` · `/underwriting-model` · `/vdr-tracker` · `/vintage-cohorts`

### Capital markets & financing
`/capital-call` · `/coinvest-pipeline` · `/debt-financing` · `/direct-lending` · `/dpi-tracker` · `/earnout` · `/fundraising` · `/gp-benchmarking` · `/irr-dispersion` · `/lp-dashboard` · `/lp-reporting` · `/mgmt-fee-tracker` · `/multiple-decomp` · `/nav-loan-tracker` · `/refi-optimizer` · `/rw-insurance` · `/tax-credits` · `/tax-structure` · `/tax-structure-analyzer`

### Clinical & sector analytics
`/aco-economics` · `/antitrust-screener` · `/biosimilars` · `/clinical-ai` · `/clinical-outcomes` · `/cms-apm` · `/cms-data-browser` · `/cyber-risk` · `/direct-employer` · `/drug-pricing-340b` · `/fraud-detection` · `/hcit-platform` · `/ma-contracts` · `/ma-star` · `/phys-comp-plan` · `/physician-labor` · `/physician-productivity` · `/platform-maturity` · `/provider-network` · `/provider-retention` · `/quality-scorecard` · `/rcm-red-flags` · `/regulatory-risk` · `/risk-adjustment` · `/specialty-benchmarks` · `/telehealth-econ` · `/tracker-340b` · `/trial-site-econ` · `/unit-economics`

### Market & macro
`/ai-operating-model` · `/backtester` · `/base-rates` · `/board-governance` · `/cost-structure` · `/compliance-attestation` · `/demand-forecast` · `/digital-front-door` · `/esg-dashboard` · `/esg-impact` · `/geo-market` · `/health-equity` · `/litigation` · `/medicaid-unwinding` · `/medical-realestate` · `/mgmt-comp` · `/msa-concentration` · `/nsa-tracker` · `/patient-experience` · `/payer-rate-trends` · `/payer-shift` · `/payer-stress` · `/real-estate` · `/ref-pricing` · `/revenue-leakage` · `/sector-correlation` · `/sector-momentum` · `/sponsor-heatmap` · `/supply-chain` · `/tech-stack` · `/value-creation` · `/value-creation-plan` · `/workforce-planning`

Plus `/admin/data-sources` for scraper / source registry.

## Design system (strict)

| Token | Value |
|---|---|
| bg | `#0a0e17` |
| panel | `#111827` |
| panel_alt | `#0f172a` |
| border | `#1e293b` |
| text | `#e2e8f0` |
| text_dim | `#94a3b8` |
| accent (links only) | `#3b82f6` |
| positive | `#10b981` |
| negative | `#ef4444` |
| warning | `#f59e0b` |

Every number uses JetBrains Mono + `font-variant-numeric: tabular-nums`. Tables use 6px/10px padding, sticky headers, right-aligned numerics, row striping at `panel_alt`. Every page closes with a short "thesis" callout in an `accent`-bordered panel.

## How to use this branch

```bash
# Pull branch
git fetch origin feature/deals-corpus
git checkout feature/deals-corpus

# Smoke test any module
.venv/bin/python3 -c "
import sys; sys.path.insert(0, 'RCM_MC')
from rcm_mc.data_public.<module> import compute_<module>
print(compute_<module>())
"

# Start the server and browse
.venv/bin/python3 -m rcm_mc.cli serve --port 8080
# Then open http://localhost:8080/<route>
```

All 153 routes are linked from the left-rail nav in both the Chartis shell and the legacy brand layout.

## Review & merge plan

1. **Read the diff** — `git diff main..feature/deals-corpus --stat` for the file list.
2. **Spot-check 5 pages** — e.g. `/dpi-tracker`, `/nav-loan-tracker`, `/cms-apm`, `/pmi-integration`, `/treasury` — each shows 5–7 dense tables + KPI strip + thesis callout and renders from 1,705 corpus deals.
3. **Touchpoints into existing code** are limited to: `server.py` (153 route blocks), `_chartis_kit.py` (nav entries), `brand.py` (nav entries). All other work is purely additive.
4. **No conflicts with `main`** expected — existing file modifications are append-only blocks.

## Finalized
Branch is feature-complete at commit `8fe461d` (Vintage Cohort Performance Tracker). 264 commits, all pushed to `origin/feature/deals-corpus`.
