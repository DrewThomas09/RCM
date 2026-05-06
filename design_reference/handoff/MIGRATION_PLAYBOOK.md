# Migration Playbook — page-by-page, in priority order

This is the walk-order for reskinning the 79 platform surfaces. Each wave lands independently; ship after each wave so you get review feedback early.

---

## Wave 0 — Shell landing (1 PR, ~30 min)

- [ ] Copy `CHARTIS_KIT_REWORK.py` → `rcm_mc/ui/_chartis_kit.py`.
- [ ] Move old file to `_chartis_kit_legacy.py` first (the new one auto-falls-back when `CHARTIS_UI_V2=0`).
- [ ] Copy `chartis_tokens.css` → `rcm_mc/ui/static/chartis_tokens.css`.
- [ ] Confirm `rcm_mc/server.py`'s static handler serves `/static/*` (most HTTP servers do; if not, add 3 lines).
- [ ] Run `python seekingchartis.py`; confirm `/home` renders with new chrome.
- [ ] Run `python handoff/verify_rework.py` — should pass kit-signatures + tokens-file checks.

**Ship.** Don't touch any pages yet. Let the team eyeball the shell.

---

## Wave 1 — The ten gates (1 PR per page, ~4 hrs total)

The ten routes in `ACCEPTANCE_CHECKLIST.md`. These are highest-traffic and most seen; they define "what good looks like" for the rest.

Order:
1. `home_page.py` (or `chartis/home_page.py`)
2. `pipeline_page.py`
3. `analysis_workbench.py`
4. `ic_memo_page.py`
5. `ebitda_bridge_page.py`
6. `portfolio_analytics_page.py`
7. `chartis/payer_intelligence_page.py`
8. `chartis/pe_intelligence_hub_page.py`
9. `chartis/corpus_backtest_page.py`
10. `deal_dashboard` (wherever `/deal/<id>` resolves)

For each: open in `SeekingChartis Rework.html` → open the same page in the live app → swap hardcoded hex → run `verify_rework.py` → tick `ACCEPTANCE_CHECKLIST.md`.

---

## Wave 2 — Per-deal surfaces (7 routes, ~2 hrs)

All under `/deal/<id>/*`:
- `chartis/partner_review_page.py`
- `chartis/red_flags_page.py`
- `chartis/ic_packet_page.py`
- `chartis/investability_page.py`
- `chartis/archetype_page.py`
- `chartis/market_structure_page.py`
- `chartis/white_space_page.py`
- `chartis/stress_page.py`

These share a layout family — fix one, copy-paste the fix to the rest.

---

## Wave 3 — Dashboards & analytics (11 routes)

- `dashboard_v2.py`, `home_v2.py`
- `portfolio_heatmap.py`, `portfolio_monitor_page.py`, `chartis/portfolio_analytics_page.py`
- `market_data_page.py`, `competitive_intel_page.py`
- `model_validation_page.py`, `bayesian_page.py`
- `value_tracking_page.py`, `waterfall_page.py`

All `kind: dashboard` — follow `PATCH_GUIDES/README.md` dashboard recipe.

---

## Wave 4 — Workbenches & models (8 routes)

- `scenario_modeler_page.py`, `ebitda_bridge_page.py`
- `models_page.py`, `pe_returns_page.py`, `pe_tools_page.py`
- `advanced_tools_page.py`, `ml_insights_page.py`
- `quant_lab_page.py`

All `kind: workbench` — tab bar + panel-per-tab.

---

## Wave 5 — Intake & onboarding (5 routes)

- `onboarding_wizard.py`, `quick_import.py`
- `data_room_page.py`, `thesis_card.py`
- `deal_screening_page.py`

`kind: wizard` or `kind: intake` — see patch guide.

---

## Wave 6 — Long-form & memos (4 routes)

- `memo_page.py`, `ic_memo_page.py`
- `sponsor_track_record_page.py`
- `methodology_page.py`

`kind: long-form` — **critically**, test print-to-PDF on each. Andrew's partners save these as PDFs and email them.

---

## Wave 7 — Reference, research, hubs (rest)

- `analysis_landing.py`, `diligence_page.py`, `analytics_pages.py`
- `conference_page.py`, `news_page.py`, `verticals_page.py`
- `hospital_profile.py`, `hospital_history.py`, `hospital_stats_page.py`
- `predictive_screener.py`, `rcm_benchmarks_page.py`
- `provenance.py`, `deal_timeline.py`, `deal_quick_view.py`
- Anything left in `MODULE_ROUTE_MAP.md`.

Mostly `kind: hub` or `kind: dashboard`. Mechanical at this point.

---

## Wave 8 — Cleanup (1 PR)

- [ ] Delete `_chartis_kit_legacy.py`.
- [ ] Remove the `CHARTIS_UI_V2` env flag from `_chartis_kit.py`.
- [ ] Delete any `if UI_V2_ENABLED:` branches that grew during migration.
- [ ] Update `README.md` screenshots to the new aesthetic.
- [ ] Archive the old screenshots to `docs/archive/ui-v1/`.

---

## Time budget

| Wave | Scope | Est. time |
|---|---|---|
| 0 | Shell | 30 min |
| 1 | Ten gates | 4 hrs |
| 2 | Per-deal (8 pages) | 2 hrs |
| 3 | Dashboards (11) | 3 hrs |
| 4 | Workbenches (8) | 3 hrs |
| 5 | Intake (5) | 1.5 hrs |
| 6 | Long-form (4) | 2 hrs |
| 7 | Rest (~40) | 6 hrs |
| 8 | Cleanup | 1 hr |
| **Total** | **79 surfaces** | **~23 hrs** |

Realistic elapsed: 3–4 working days for one engineer, or a weekend for Claude Code running autonomously with supervision.
