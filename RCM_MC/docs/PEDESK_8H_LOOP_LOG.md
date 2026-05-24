# PEdesk 8-hour autonomous build loop — log

Running log of the autonomous build loop (auto-merge + auto-deploy of
in-scope, CI-green PRs). Each deploy entry confirms: test job, deploy job,
deployed SHA == main, `pedesk.service` restart, and `/healthz` 200.

Scope guardrails (do-not-touch): auth/login/session, `.pedesk_prod.env`,
secrets, Caddy, systemd, DigitalOcean deploy config, GitHub Actions
workflow, Ollama/Tailscale, RAG backend runtime, #580/#579. No synthetic
data, no runtime CMS/map/chart APIs, no unsupported claims.

## Deploy ledger

| When (UTC) | PRs | main SHA | test | deploy | /healthz | notes |
|---|---|---|---|---|---|---|
| 2026-05-24 05:07 | #604 map · #605 pipeline · #606 analytics · #603 CC grid | `f25b1c72` | ✓ | ✓ | 200 | Queue cleared; concurrency collapsed the 4 merges into one deploy of `main`. All 4 features live. |
| 2026-05-24 05:09 | #607 Phase 0 coverage audit (docs) | `fafcf89f` | ✓ | ✓ | 200 | Audit + loop log committed. |
| 2026-05-24 05:1x | #608 Phase 1 batch 1 (CMS/data Guide context) | `6fb7945a` | ✓ | ✓ | 200 | 5 pages curated. |
| 2026-05-24 05:2x | #609 Phase 1 batch 2 (portfolio/diligence/source context) | `36eac75d` | ✓ | ✓ | 200 | 5 pages curated (73→83). |
| 2026-05-24 05:5x | #610 SNF / Nursing Home vertical | `ef9aa9c2` | ✓ | ✓ | 200 | 14,699 real CMS facilities; full screener/profile/market-intel/Guide/tests. |
| 2026-05-24 06:0x | #611 Phase 3 evidence/prediction framework (docs+RAG) | `5a263347` | ✓ | ✓ | 200 | 4 RAG-indexed framework docs (199 docs). |
| 2026-05-24 06:1x | #6xx Dialysis vertical | _pending merge_ | — | — | — | 7,557 real CMS Dialysis Facility Compare facilities; full factory. |

## Phase ledger

- **Queue clear (done):** merged the four open UI PRs (#603–#606) — Command
  Center dossier grid, Portfolio Map cartogram, Pipeline filter/sort,
  Portfolio Analytics filter/toggle/guardrails. Deployed `f25b1c72`.
- **Phase 0 (in progress):** route + Guide-context coverage audit →
  `PEDESK_GUIDE_AI_COVERAGE_AUDIT.md`. Result: 309 exact page routes; 73
  curated Guide contexts; 236 on the safe generic fallback. Every page
  answers the Guide (fallback), so the work is upgrading high-priority
  pages from fallback → curated.
- **Phase 1 (in progress):** curated Guide context for high-priority
  fallback pages. Batch 1 (CMS/data): `/market-data`, `/cms-sources`,
  `/cms-data-browser`, `/data/catalog`, `/benchmarks` upgraded
  fallback → curated (accurate sources, honest caveats, 7–8 suggested
  questions each).
  Batch 2 (portfolio/diligence/source): `/diligence`,
  `/concentration-risk` (HHI/CR3/CR5 labeled composition not market share),
  `/competitive-intel` (peer percentile = deviation not conclusion),
  `/lp-dashboard` (realized vs marked distinguished), `/admin/data-sources`
  upgraded fallback → curated. Verified `/comps`, `/deliverables`, `/proof`,
  `/about` are NOT real routes (skipped — no phantom contexts). Curated
  count: 73 → 83 of 309 page routes.
- **Phase 2 (queued):** RAG source cards (sectors + metrics).
- **Phase 3 (queued):** investable-evidence + predictive-modeling framework.
- **Phase 4 (in progress):** CMS verticals — **SNF / Nursing Home built**.
  Vendored the official **CMS Nursing Home Care Compare — Provider
  Information** file (`NH_ProviderInfo`, Apr 2026, downloaded once from
  data.cms.gov) → normalized `snf_providers.csv` + `snf_quality.csv`
  (**14,699 real facilities**, provenance columns, no synthetic data).
  Built `data/snf.py` loader (providers / quality / state summary / state
  filter / by-CCN), `ui/snf_page.py` screener + profile reusing the sector
  scaffolds (state map, market intelligence, county competition, ownership
  mix, rating distribution, peer percentiles), routes `/nursing-homes`
  + `/nursing-homes/<ccn>`, curated Guide context (10 suggested questions),
  command-palette entry, and `tests/test_snf_vertical.py`. Honesty: four CMS
  star ratings + staffing + beds + SFF shown; lower-is-better signals
  (fines/denials/turnover) deliberately kept out of the "higher = better"
  percentile table; "total fines" labeled a regulatory penalty, not revenue.
  **Dialysis vertical built** (#6xx): vendored CMS Dialysis Facility Compare
  'Listing by Facility' (DFC_FACILITY, Mar 2026) → `dialysis_providers.csv` +
  `dialysis_quality.csv` (**7,557 real facilities**). `data/dialysis.py`
  loader + `ui/dialysis_page.py` screener/profile (five-star + chain mix +
  county competition; outcome rates shown raw in the table but kept out of
  the higher=better percentile table since they're lower-is-better) + routes
  `/dialysis` + `/dialysis/<ccn>` + curated Guide context (9 Qs) + palette +
  `tests/test_dialysis_vertical.py`. **Verticals fully covered: Home Health,
  Hospice, SNF, Dialysis.** Remaining (ASC / IRF / LTCH / DMEPOS) queued —
  depth over breadth.
- **Phase 3 (done, separate from numeric order):** investable-evidence +
  predictive-modeling framework — `PEDESK_INVESTABLE_EVIDENCE_FRAMEWORK.md`,
  `PEDESK_PREDICTIVE_MODELING_ROADMAP.md`, and two `rag_sources/` cards
  (statistics + modeling boundaries). All four RAG-indexed (199 docs). The
  Guide can now explain peer percentile, z-score (n≥5 / sd=0 guards), HHI
  (composition ≠ market share), quality composites, OLS/Ridge/Lasso/Elastic-
  Net/logistic/fixed-effects/multilevel/survival, validation, uncertainty,
  bias checks, and the 8-point investable-evidence threshold — with the
  prediction≠causation and CMS≠commercial boundaries.
- **Phase 2 (partial):** RAG coverage — every curated page context + the
  framework docs are auto-indexed into the RAG corpus (page/metric/source/
  doc documents). Dedicated metric/data-source registry cards for SNF +
  the new statistics are a queued enhancement.
- **Phase 5 (queued):** re-run coverage audit + final report.
