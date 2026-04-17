# RCM-MC Developer Guide

Deep-dive into the architecture, module structure, testing patterns, and coding conventions for contributing to RCM-MC.

---

## Architecture Overview

### Layer Diagram

```
                    +------------------+
                    |    Browser/CLI   |
                    +--------+---------+
                             |
                    +--------v---------+
                    |    server.py     |  HTTP dispatch, auth, CSRF, rate-limit,
                    |   (~10K lines)   |  gzip, ETags, CORS, CSP, audit
                    +--------+---------+
                             |
              +--------------+---------------+
              |              |               |
     +--------v------+  +---v----+  +-------v-------+
     |  UI renderers |  |  API   |  |  POST handlers|
     |  (ui/*.py)    |  |  JSON  |  |  (forms, etc) |
     +--------+------+  +---+----+  +-------+-------+
              |              |               |
              +--------------+---------------+
                             |
                    +--------v---------+
                    | Feature packages |  alerts/, deals/, portfolio/,
                    |                  |  auth/, ai/, pe/, mc/, analysis/
                    +--------+---------+
                             |
                    +--------v---------+
                    |   store.py       |  SQLite connection manager
                    | (PortfolioStore) |  Single source of truth
                    +--------+---------+
                             |
                    +--------v---------+
                    |   SQLite file    |  portfolio.db
                    +------------------+
```

### Key Invariants

1. **Packet-centric rendering**: Every UI page, API endpoint, and export renders from a `DealAnalysisPacket`. Nothing renders independently.
2. **Store is the only DB accessor**: No module except `store.py` opens SQLite connections directly.
3. **Layers call down, never up**: UI imports from analysis, analysis imports from store. Never the reverse.
4. **No new runtime deps**: numpy, pandas, pyyaml, matplotlib, openpyxl are the full list. Everything else is stdlib.

---

## Module Map

### Core Engine (`rcm_mc/core/`)

| Module | Purpose |
|--------|---------|
| `simulator.py` | N-simulation Monte Carlo engine |
| `kernel.py` | Per-payer claim distribution math |
| `distributions.py` | Beta, LogNormal, Truncated Normal |
| `calibration.py` | Bayesian prior fitting from diligence data |
| `rng.py` | Seeded random number generation |

### PE Math (`rcm_mc/pe/`)

| Module | Purpose |
|--------|---------|
| `pe_math.py` | MOIC, IRR, covenant headroom |
| `rcm_ebitda_bridge.py` | 7-lever EBITDA bridge |
| `value_bridge_v2.py` | Cross-lever dependency DAG + ramp curves |
| `ramp_curves.py` | S-shaped logistic implementation curves |
| `hold_tracking.py` | Actual vs plan variance tracking |
| `value_creation_plan.py` | Auto-generated plan from packet |
| `fund_attribution.py` | Fund-level performance attribution |

### Analysis (`rcm_mc/analysis/`)

| Module | Purpose |
|--------|---------|
| `packet.py` | `DealAnalysisPacket` dataclass (canonical) |
| `packet_builder.py` | 12-step orchestrator that builds the packet |
| `completeness.py` | 38-metric RCM registry + grade computation |
| `risk_flags.py` | Automated risk detection from data patterns |
| `diligence_questions.py` | Auto-generated due diligence questions |
| `deal_overrides.py` | Analyst override management with audit trail |
| `cross_deal_search.py` | Full-text search across deals |
| `deal_sourcer.py` | Thesis-driven deal origination |

### Data Pipeline (`rcm_mc/data/`)

| Module | Purpose |
|--------|---------|
| `hcris.py` | HCRIS hospital data (6,000+ hospitals) |
| `auto_populate.py` | CCN lookup + multi-source merge |
| `document_reader.py` | Excel/CSV auto-detect with 100+ column aliases |
| `edi_parser.py` | EDI 837/835 claim-level parsing |
| `state_regulatory.py` | 50-state CON/payer profiles |

### AI (`rcm_mc/ai/`)

| Module | Purpose |
|--------|---------|
| `llm_client.py` | Anthropic Claude client with caching + fallback |
| `memo_writer.py` | IC memo generation with fact-checking |
| `document_qa.py` | Per-deal document indexing + keyword search |
| `conversation.py` | Multi-turn chat with tool dispatch |

### UI Renderers (`rcm_mc/ui/`)

| Module | Purpose |
|--------|---------|
| `_ui_kit.py` | Shared shell, BASE_CSS, dark mode, toast system |
| `analysis_workbench.py` | Bloomberg-style 7-tab workbench |
| `settings_pages.py` | Custom KPIs, automations, integrations |
| `scenarios_page.py` | Scenario explorer |
| `pressure_page.py` | Pressure test with risk flags |
| `surrogate_page.py` | Surrogate model status |
| `onboarding_wizard.py` | 5-step deal creation wizard |
| `source_page.py` | Thesis-driven sourcing |
| `deal_comparison.py` | Side-by-side + screening |
| `deal_timeline.py` | Activity timeline |
| `portfolio_heatmap.py` | Risk heatmap |
| `portfolio_map.py` | Geographic map |

### Infrastructure (`rcm_mc/infra/`)

| Module | Purpose |
|--------|---------|
| `migrations.py` | Schema version registry + auto-apply |
| `openapi.py` | OpenAPI 3.0 spec (52 paths) + Swagger UI |
| `webhooks.py` | HMAC-signed webhook delivery with retry |
| `automation_engine.py` | Event-driven rule execution |
| `rate_limit.py` | Per-key sliding window rate limiter |
| `response_cache.py` | In-memory TTL cache for expensive responses |
| `job_queue.py` | In-memory single-worker simulation queue |
| `run_history.py` | SQLite-based run tracking |

---

## Testing

### Running Tests

```bash
# Full suite (6 minutes)
.venv/bin/python -m pytest -q --ignore=tests/test_integration_e2e.py

# Specific marker
.venv/bin/python -m pytest -m api

# Single file
.venv/bin/python -m pytest tests/test_improvements_b106.py -v

# Quick smoke test (new tests only)
.venv/bin/python -m pytest tests/test_improvements_b*.py -q
```

### Test Patterns

**Server integration tests** spin up a real HTTP server on a free port:

```python
def _start(db_path):
    from rcm_mc.server import build_server
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]; s.close()
    server, _ = build_server(port=port, db_path=db_path)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start(); time.sleep(0.05)
    return server, port
```

**Shared fixtures** (from `tests/conftest.py`):

```python
def test_something(tmp_store):
    store, path = tmp_store
    store.upsert_deal("d1", name="Test")

def test_endpoint(server_port):
    port, store = server_port
    urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health")
```

### Test Conventions

- Each feature has `test_<feature>.py`
- Bug fixes have `test_bug_fixes_b<N>.py`
- No mocks for own code -- always exercise the real path
- Tests must be order-independent (conftest resets handler state)
- No `time.sleep()` under 50ms (flaky on CI)
- Registered pytest markers: `api`, `ui`, `store`, `security`, `integration`, `slow`

---

## Coding Conventions

### Python

- **Parameterized SQL only** -- never f-string values into queries
- **`html.escape()` every user string** before HTML rendering
- **`_clamp_int` every integer query param** -- never raw `int(qs[...])`
- **Timezone-aware datetimes** -- `datetime.now(timezone.utc)` always
- **Private helpers prefixed** -- `_ensure_table`, `_validate_username`
- **No new runtime deps** without discussion

### Import Shadowing (CRITICAL)

Local imports inside `_do_get_inner` or `_do_post_inner` **MUST** use aliases:

```python
# WRONG -- shadows module-level add_tag for the entire function
from .deals.deal_tags import add_tag

# RIGHT -- alias avoids shadowing
from .deals.deal_tags import add_tag as _bulk_add_tag
```

Python's scoping marks any `from X import Y` as local for the *entire* function, even lines above the import.

### UI

- **Dark mode default** -- use CSS variables (`var(--bg)`, `var(--text)`)
- **Every page uses `shell()`** -- never build standalone HTML
- **Page HTML in `ui/` modules** -- not inline in server.py
- **Forms POST** -- never GET for state changes
- **Monospace numerics** -- `font-variant-numeric: tabular-nums`

### Number Formatting

| Type | Format | Example |
|------|--------|---------|
| Financial | 2 decimal places | `$450.25M` |
| Percentage | 1 decimal place, signed | `+4.1%` |
| Multiple | 2 decimal + x | `2.50x` |
| Date | ISO | `2026-04-15` |
| Time | UTC ISO | `2026-04-15T10:00:00+00:00` |

---

## Version Management

Version is tracked in TWO places -- keep them synced:

1. `rcm_mc/__init__.py` -- `__version__ = "0.6.0"`
2. `pyproject.toml` -- `version = "0.6.0"`

Test count is tracked in CLAUDE.md in TWO places (line ~36 and ~270).

---

## Tool Configuration

### pyproject.toml

```toml
[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
ignore = ["E501", "RUF012"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
warn_unused_ignores = true
strict_optional = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
markers = [
    "api: API endpoint tests",
    "ui: UI rendering tests",
    "store: database/store tests",
    "security: auth/CSRF/rate-limit tests",
    "integration: multi-module integration tests",
    "slow: tests that take >5 seconds",
]
```

---

## OpenAPI Maintenance

The spec lives in `rcm_mc/infra/openapi.py` as a Python dict (`_SPEC`). When adding endpoints:

1. Add the path definition to `_SPEC["paths"]` BEFORE the `},` that closes the paths dict
2. Include method, summary, tags, parameters, and response descriptions
3. The `/api` index endpoint auto-generates from this spec -- no separate maintenance needed
4. Verify: `python -c "from rcm_mc.infra.openapi import get_openapi_spec; print(len(get_openapi_spec()['paths']), 'paths')"`

---

## What Was Built in This Session (B85-B133)

49 improvement passes delivered:

- **+193 tests** (2,690 -> 2,883)
- **52 OpenAPI paths** (56 methods)
- **8 route extractions** from server.py into 5 methods + 3 ui/ modules
- **3 AI endpoints** (memo, QA, chat)
- **All 4 "What needs UI" gaps closed** (scenarios, peer comparison, run history, calibration)
- **All CLI-only items closed** (every feature has a web API)
- **7 security headers** + CSP
- **Dark mode CSS** + print CSS + keyboard shortcuts + toast notifications
- **Gzip compression** + ETags + pagination + sorting
- **Schema migration registry** with auto-run on startup
- **Webhook lifecycle dispatch** on deal events
- **Idempotency key** support for POST endpoints
- **Deep health check** with component-level monitoring
