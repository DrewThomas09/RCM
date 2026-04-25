# UI Rework — Plan + Safety Rails

**Branch:** `feat/ui-rework-v3`
**Designer:** working with Claude Design
**Created:** 2026-04-25

---

## What this branch is for

A full UI / HTML rework of the SeekingChartis surface. Scope: visual language, page composition, component library, navigation, density, color, typography. All of that can change freely.

## What "stays connected" means

The rework cannot break:

| Connection | Why it matters | How we lock it |
|---|---|---|
| **Routes** | Bookmarks, copy-pasted URLs, mobile shortcuts must keep working | `tests/test_ui_rework_contract.py::test_critical_pages_resolve` |
| **`/health` + `/healthz` body=`"ok"`** | Docker healthcheck + Caddy + uptime probes depend on this exact body | `tests/test_ui_rework_contract.py::test_health_endpoints_return_ok_body` |
| **Auth round-trip** | Session cookies, CSRF, login flow | `tests/test_ui_rework_contract.py::test_login_round_trip` |
| **`DealAnalysisPacket` load-bearing fields** | Every UI surface reads from this single dataclass | `tests/test_ui_rework_contract.py::test_packet_dataclass_load_bearing_fields` |
| **OpenAPI surface** | External callers / integrations / `gh` workflows | `tests/test_ui_rework_contract.py::test_openapi_spec_loads` |
| **JSON endpoints stay JSON** | Any `/api/*` that returns HTML by accident is a regression | `tests/test_ui_rework_contract.py::test_authenticated_data_endpoint_returns_json` |
| **All schema migrations apply** | Server boot must not regress | `tests/test_ui_rework_contract.py::test_all_migrations_applied` |
| **Single shell()-style renderer** | Global treatment consistency depends on one insertion point | `tests/test_ui_rework_contract.py::test_ui_kit_shell_function_exists` |

The contract test runs in <2 seconds and is the pre-flight before any push to this branch.

## What CAN change freely

- Colors, fonts, spacing, shadows, radii, transitions
- HTML structure (div/section/article — refactor at will)
- CSS class names (rename them, just keep data flowing through)
- JavaScript behavior (animations, loading states, empty-state copy)
- Page composition (which components appear where on a page)
- Component library API (`power_table`, `power_chart`, `_ui_kit.*` can all change)
- Navigation IA (move things between pages — but keep the old URL redirecting if it's externally bookmarked)
- Density, typography, voice, microcopy

## Recommended architecture: feature flag for coexistence

Don't replace `rcm_mc/ui/` in-place — that's how the prior reskin broke and got reverted (commit `d8bfac4 revert(ui): restore dark terminal shell`). Instead:

```
rcm_mc/
├── ui/         ← v2 — keeps rendering exactly as today
└── ui_v3/      ← v3 — new look. Renders only when flag is on.
```

**Flag detection** (one-liner in `server.py`):

```python
def _ui_version(self) -> str:
    # Query param overrides env for per-request testing.
    if "ui" in self.query_params:
        return self.query_params["ui"]
    return os.environ.get("RCM_MC_UI_VERSION", "v2")
```

**Routing** (each page picks its renderer):

```python
if self._ui_version() == "v3":
    from .ui_v3 import deal_profile
    return deal_profile.render(packet)
from .ui import deal_profile_v2
return deal_profile_v2.render(packet)
```

This lets Claude Design rebuild any page without touching the v2 surface. Toggle `?ui=v3` in the browser to preview; toggle `RCM_MC_UI_VERSION=v3` on a staging VM to run an isolated end-to-end test.

## Phase plan

| Phase | Scope | Exit criteria |
|---|---|---|
| **1. Foundation (Week 1)** | Design tokens, typography scale, color palette, base components (`Button`, `Card`, `Input`, `KPI`, `Table` shell). Build `ui_v3/_kit.py`. | Contract tests still green; `?ui=v3` renders a single page identically functional to v2 |
| **2. Marquee surfaces (Week 2-3)** | Dashboard, Deal Profile, Screening, Analysis Workbench. The 4 pages that drive 80% of partner time | Each page passes contract tests in both `?ui=v3` and unset; partner walkthrough doesn't surface a regression |
| **3. Long tail (Week 4-5)** | The remaining 30+ pages (LP digest, audit log, settings, calibration, etc.) | All pages render in `?ui=v3` mode |
| **4. Cutover (Week 6)** | Flip `RCM_MC_UI_VERSION=v3` default. Old `ui/` package stays for 30 days as a rollback option | Live traffic on v3, no rollback fired in first 7 days |
| **5. Cleanup (Week 8+)** | Delete old `ui/` package after 30-day soak | Tests still green, package deletion is a single-PR diff |

## Daily-driver: how to test that nothing's broken

```bash
# Before any commit on this branch
cd RCM_MC
.venv/bin/python -m pytest tests/test_ui_rework_contract.py -v

# Before any push
.venv/bin/python -m pytest \
  tests/test_ui_rework_contract.py \
  tests/test_healthz.py \
  tests/test_api_endpoints_smoke.py \
  tests/test_full_pipeline_10_hospitals.py \
  tests/test_readme_links.py \
  tests/test_auth.py \
  tests/test_csrf.py
```

## Rollback procedure

The branch is pure-additive (new `ui_v3/` package + flag check). To roll back:

```bash
# Local
git checkout main
# nothing else needed — main never sees ui_v3/

# Production VM (only relevant after Phase 4 cutover)
ssh azureuser@pedesk.app
sudo -E RCM_MC_UI_VERSION=v2 systemctl restart rcm-mc
# Or: cd /opt/rcm-mc && sudo git checkout <commit-before-cutover>
# Then: sudo docker compose -f RCM_MC/deploy/docker-compose.yml up -d --build
```

## Critical: do NOT merge to main until contract tests pass

The `deploy.yml` workflow auto-deploys `main` to `pedesk.app` on every push. So:

1. Work on `feat/ui-rework-v3` until contract tests are 8/8 green AND every CRITICAL_PAGES route renders in `?ui=v3` mode.
2. Open a PR — never push directly to main.
3. Merge only after a stakeholder has clicked through the v3 surface end-to-end and signed off.
4. On merge, watch the deploy workflow run; have the rollback command ready.

## Why the prior rework was reverted

For learning purposes — these are the connection patterns the prior reskin broke:

1. **In-place CSS replacement** — every page changed at once, no way to A/B test.
2. **No flag** — couldn't preview without affecting all users.
3. **Renamed `_ui_kit.shell()` arguments** — silently broke 14 tests that passed kwargs.
4. **Removed several existing CSS classes** — workbench tabs lost their highlight states.
5. **Different approach for tables across pages** — broke the `power_table` consistency contract.

Today's rework can avoid all five by gating with a flag, keeping the v2 package alongside, and running the contract test on every commit.

## Open questions for Claude Design

- Do we want a single global theme toggle (dark/light/editorial) or per-page treatments?
- Are we keeping the dense-data tables (power_table) as-is for analyst use, with a friendlier surface for partner use?
- Is the navigation moving (sidebar → top-bar, breadcrumbs, command-palette)?
- Is there a typography pairing already chosen?

Document the answers in this file as decisions are made — they become the design system spec.
