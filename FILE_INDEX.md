# File Index

A navigable directory to every significant file in the repo. Use this to find what file owns a behaviour before diving in. Every major directory has its own README with per-file detail — this is the **map of those maps**.

**See also**:
- [FILE_MAP.md](FILE_MAP.md) — per-file catalogue, 1,659 files across 29 chunk summaries with one-line descriptions
- [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) — 8 GitHub-rendered Mermaid diagrams covering package dependencies, packet-centric data flow, 4 canonical cascades, ingestion paths, predictor ladder, band ladder, 3 UI surfaces, 19-step Thesis Pipeline
- [README.md](README.md) — plain-English product overview
- [WALKTHROUGH.md](WALKTHROUGH.md) — full case study

---

## Top-level files (repo root)

| File | What it is |
|------|-----------|
| [README.md](README.md) | 9th-grade plain-English front page — start here |
| [WALKTHROUGH.md](WALKTHROUGH.md) | 13-step case study walking a PE VP through a real deal |
| [COMPUTER_24HOUR_UPDATE_NUMBER_1.md](COMPUTER_24HOUR_UPDATE_NUMBER_1.md) | Snapshot of a 24-hour build cycle |
| [SESSION_SUMMARY.md](SESSION_SUMMARY.md) | Multi-session build log |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to add features or fix bugs |
| [LICENSE](LICENSE) | License |
| **FILE_INDEX.md** | *(this file)* |

---

## RCM_MC/ — the main package

| Path | What it is |
|------|-----------|
| [RCM_MC/README.md](RCM_MC/README.md) | Package-level developer README |
| [RCM_MC/CLAUDE.md](RCM_MC/CLAUDE.md) | AI-assistant conventions (coding style, UI rules, number formatting) |
| [RCM_MC/CHANGELOG.md](RCM_MC/CHANGELOG.md) | Release history |
| [RCM_MC/DEMO.md](RCM_MC/DEMO.md) | One-command demo instructions |
| [RCM_MC/pyproject.toml](RCM_MC/pyproject.toml) | Package build config — pins Python 3.14, lists the 4 runtime deps |
| [RCM_MC/demo.py](RCM_MC/demo.py) | One-click demo: seeds DB, starts server, opens browser |
| [RCM_MC/seekingchartis.py](RCM_MC/seekingchartis.py) | SeekingChartis front-door CLI + server |
| [RCM_MC/run_all.sh](RCM_MC/run_all.sh), [run_everything.sh](RCM_MC/run_everything.sh) | Full-stack run scripts |

### Top-level docs inside the package

| Path | What it is |
|------|-----------|
| [RCM_MC/docs/README.md](RCM_MC/docs/README.md) | Index of canonical specs + domain deep-dives |
| [RCM_MC/docs/ANALYSIS_PACKET.md](RCM_MC/docs/ANALYSIS_PACKET.md) | `DealAnalysisPacket` dataclass spec |
| [RCM_MC/docs/ARCHITECTURE.md](RCM_MC/docs/ARCHITECTURE.md) | Layer diagram + dependency rules |
| [RCM_MC/docs/BENCHMARK_SOURCES.md](RCM_MC/docs/BENCHMARK_SOURCES.md) | CMS HCRIS, Care Compare, IRS 990, SEC EDGAR field map |
| [RCM_MC/docs/METRIC_PROVENANCE.md](RCM_MC/docs/METRIC_PROVENANCE.md) | How each metric traces back to its source |
| [RCM_MC/docs/MODEL_IMPROVEMENT.md](RCM_MC/docs/MODEL_IMPROVEMENT.md) | Known limitations + Tier 1-3 roadmap |
| [RCM_MC/docs/PE_HEURISTICS.md](RCM_MC/docs/PE_HEURISTICS.md) | 275+ partner rules, failure patterns, thesis-trap detectors |
| [RCM_MC/readME/README.md](RCM_MC/readME/README.md) | Numbered user-facing walkthrough index |

---

## rcm_mc/ — Python source (29 sub-packages)

Each sub-package has its own README with per-file documentation. Click the README to drill in.

### Diligence modules — the 7 new cycle-shipped surfaces

| Module | README | One-line |
|--------|--------|----------|
| HCRIS Peer X-Ray | [RCM_MC/rcm_mc/diligence/hcris_xray/README.md](RCM_MC/rcm_mc/diligence/hcris_xray/README.md) | 17,701-hospital Medicare cost-report benchmark in 25ms |
| Regulatory Calendar | [RCM_MC/rcm_mc/diligence/regulatory_calendar/README.md](RCM_MC/rcm_mc/diligence/regulatory_calendar/README.md) | When government rules kill thesis drivers |
| Covenant Stress Lab | [RCM_MC/rcm_mc/diligence/covenant_lab/README.md](RCM_MC/rcm_mc/diligence/covenant_lab/README.md) | Per-quarter breach probability × 4 covenants |
| Bridge Auto-Auditor | [RCM_MC/rcm_mc/diligence/bridge_audit/README.md](RCM_MC/rcm_mc/diligence/bridge_audit/README.md) | Paste banker's synergy bridge → risk-adjusted rebuild |
| Bear Case Auto-Generator | [RCM_MC/rcm_mc/diligence/bear_case/README.md](RCM_MC/rcm_mc/diligence/bear_case/README.md) | 3-5 hours of bear-case drafting in 100ms |
| Payer Mix Stress | [RCM_MC/rcm_mc/diligence/payer_stress/README.md](RCM_MC/rcm_mc/diligence/payer_stress/README.md) | Concentration-amplified rate-shock MC over 19 payers |
| Thesis Pipeline | [RCM_MC/rcm_mc/diligence/thesis_pipeline/README.md](RCM_MC/rcm_mc/diligence/thesis_pipeline/README.md) | One-click 19-step diligence orchestrator (~170ms) |

### Diligence modules — the legacy surfaces (29 total)

Navigate inside [RCM_MC/rcm_mc/diligence/](RCM_MC/rcm_mc/diligence/) — benchmarks, checklist, counterfactual, cyber, deal_autopsy, deal_mc, denial_prediction, exit_timing, integrity, labor, ma_dynamics, management_scorecard, patient_pay, physician_attrition, physician_comp, physician_eu, quality, real_estate, referral, regulatory, reputational, root_cause, screening, synergy, value, working_capital.

### PE Intelligence brain (169 modules)

| Path | What it is |
|------|-----------|
| [RCM_MC/rcm_mc/pe_intelligence/README.md](RCM_MC/rcm_mc/pe_intelligence/README.md) | Index of all 169 partner-brain modules — IC synthesizer, VCP, autopsy libraries, 9 deal-smell detectors, etc. |

### Core analytics + simulation

| Sub-package | README | One-line |
|-------------|--------|----------|
| Core simulator | [RCM_MC/rcm_mc/core/](RCM_MC/rcm_mc/core/) | Monte Carlo kernel, distributions, RNG, calibration |
| PE math | [RCM_MC/rcm_mc/pe/](RCM_MC/rcm_mc/pe/) | Value-creation bridge, MOIC/IRR, hold tracking |
| RCM math | [RCM_MC/rcm_mc/rcm/](RCM_MC/rcm_mc/rcm/) | Claim distribution, initiatives, per-lever math |
| Analysis | [RCM_MC/rcm_mc/analysis/](RCM_MC/rcm_mc/analysis/) | Packet builder + completeness + stress + compare_runs |
| ML | [RCM_MC/rcm_mc/ml/](RCM_MC/rcm_mc/ml/) | Ridge predictor + conformal prediction (stdlib-only) |
| MC | [RCM_MC/rcm_mc/mc/](RCM_MC/rcm_mc/mc/) | EBITDA Monte Carlo (two-source) |
| Scenarios | [RCM_MC/rcm_mc/scenarios/](RCM_MC/rcm_mc/scenarios/) | Scenario builder + shocks + overlay |

### Portfolio + deal ops

| Sub-package | README | One-line |
|-------------|--------|----------|
| Deals | [RCM_MC/rcm_mc/deals/](RCM_MC/rcm_mc/deals/) | Deal CRUD + notes + tags + owners + deadlines + health score |
| Portfolio | [RCM_MC/rcm_mc/portfolio/](RCM_MC/rcm_mc/portfolio/) | Store (SQLite) + dashboard + snapshots |
| Alerts | [RCM_MC/rcm_mc/alerts/](RCM_MC/rcm_mc/alerts/) | Fire/ack/snooze/escalate lifecycle |
| Auth | [RCM_MC/rcm_mc/auth/](RCM_MC/rcm_mc/auth/) | scrypt + session cookies + audit log |

### Data + ingest

| Sub-package | README | One-line |
|-------------|--------|----------|
| Data | [RCM_MC/rcm_mc/data/](RCM_MC/rcm_mc/data/) | HCRIS loader, IRS 990, sources, ingest, intake, scrub |
| Data demo | [RCM_MC/rcm_mc/data_demo/](RCM_MC/rcm_mc/data_demo/) | Synthetic CCD fixtures |

### UI + reports + exports

| Sub-package | README | One-line |
|-------------|--------|----------|
| UI | [RCM_MC/rcm_mc/ui/](RCM_MC/rcm_mc/ui/) | `_ui_kit.py::shell()`, page renderers, Chartis-themed HTML |
| Reports | [RCM_MC/rcm_mc/reports/](RCM_MC/rcm_mc/reports/) | Full report, HTML report, narrative, exit memo, PPTX, LP update |
| Exports | [RCM_MC/rcm_mc/exports/](RCM_MC/rcm_mc/exports/) | Packet renderer, CSV defanged for Excel injection |

### Infrastructure

| Sub-package | README | One-line |
|-------------|--------|----------|
| Infra | [RCM_MC/rcm_mc/infra/](RCM_MC/rcm_mc/infra/) | Config, logger, trace, job queue, run history, provenance |
| Provenance | [RCM_MC/rcm_mc/provenance/](RCM_MC/rcm_mc/provenance/) | Per-metric source graph + explain-why |
| Integrations | [RCM_MC/rcm_mc/integrations/](RCM_MC/rcm_mc/integrations/) | External data adapters |
| Verticals | [RCM_MC/rcm_mc/verticals/](RCM_MC/rcm_mc/verticals/) | Healthcare sub-vertical adapters |

### Entry points (top-level modules)

| File | What it is |
|------|-----------|
| [RCM_MC/rcm_mc/server.py](RCM_MC/rcm_mc/server.py) | HTTP app (auth, CSRF, rate-limit, audit) — `rcm-mc serve` |
| [RCM_MC/rcm_mc/cli.py](RCM_MC/rcm_mc/cli.py) | Top-level CLI — `rcm-mc ...` |
| [RCM_MC/rcm_mc/pe_cli.py](RCM_MC/rcm_mc/pe_cli.py) | PE-math subcommands — `rcm-mc pe ...` |
| [RCM_MC/rcm_mc/portfolio_cmd.py](RCM_MC/rcm_mc/portfolio_cmd.py) | Portfolio subcommands — `rcm-mc portfolio ...` |
| [RCM_MC/rcm_mc/api.py](RCM_MC/rcm_mc/api.py) | Top-level programmatic API (Python library entry) |
| [RCM_MC/rcm_mc/__main__.py](RCM_MC/rcm_mc/__main__.py) | `python -m rcm_mc` entry |
| [RCM_MC/rcm_mc/lookup.py](RCM_MC/rcm_mc/lookup.py) | Catalog lookup helpers |

---

## Tests

```
RCM_MC/tests/
```

| Pattern | What it is |
|---------|-----------|
| `test_<feature>.py` | One file per feature (2,971 tests total) |
| `test_bug_fixes_b<N>.py` | Regression assertions for filed bugs |
| `test_integration_e2e.py` | End-to-end against a real HTTP server on a free port |

Run: `.venv/bin/python -m pytest -q --ignore=tests/test_integration_e2e.py`

---

## If you want to change something specific

| To change… | Open… |
|-----------|-------|
| The dark-mode palette | [RCM_MC/rcm_mc/ui/_ui_kit.py](RCM_MC/rcm_mc/ui/_ui_kit.py) |
| Number formatting (decimals, currency) | [RCM_MC/CLAUDE.md](RCM_MC/CLAUDE.md) — canonical rules |
| A regulatory event | [regulatory_calendar/calendar.py](RCM_MC/rcm_mc/diligence/regulatory_calendar/calendar.py) — bottom of file |
| A lever prior | [bridge_audit/lever_library.py](RCM_MC/rcm_mc/diligence/bridge_audit/lever_library.py) — bottom of file |
| A payer prior | [payer_stress/payer_library.py](RCM_MC/rcm_mc/diligence/payer_stress/payer_library.py) — bottom of file |
| Covenant definitions | [covenant_lab/covenants.py](RCM_MC/rcm_mc/diligence/covenant_lab/covenants.py) — `DEFAULT_COVENANTS` |
| HCRIS metric list | [hcris_xray/metrics.py](RCM_MC/rcm_mc/diligence/hcris_xray/metrics.py) — `METRIC_SPECS` |
| A pipeline step | [thesis_pipeline/orchestrator.py](RCM_MC/rcm_mc/diligence/thesis_pipeline/orchestrator.py) — `run_thesis_pipeline` |
| A bear-case extractor | [bear_case/evidence.py](RCM_MC/rcm_mc/diligence/bear_case/evidence.py) |
| Deal SQLite schema | [RCM_MC/rcm_mc/portfolio/store.py](RCM_MC/rcm_mc/portfolio/store.py) |
| An HTTP route | [RCM_MC/rcm_mc/server.py](RCM_MC/rcm_mc/server.py) |
| The CLI | [RCM_MC/rcm_mc/cli.py](RCM_MC/rcm_mc/cli.py) |

---

## Trust + auditability

Every dataclass in the diligence modules has a `citation_key` or `source_module` field. Every metric in the analysis packet has a provenance chain ([docs/METRIC_PROVENANCE.md](RCM_MC/docs/METRIC_PROVENANCE.md)). If a number looks wrong, the flow is:

1. Click the number in the UI → opens the source module page
2. Check the source module's README for methodology
3. Check the tests for the module (`tests/test_<module>.py`) to see what's asserted
4. Run `rcm-mc analysis <deal_id> --explain <metric>` to trace back to raw inputs
