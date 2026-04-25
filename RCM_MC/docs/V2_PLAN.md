# Version 2.0 Plan — What We'd Do Differently

The platform shipped quickly and works well. After ~30 modules of new
UI + ML + data ingest + 2,500+ tests, certain architectural decisions
stand out as worth keeping, and certain ones stand out as
worth rethinking. This document is honest about both — what stays,
what changes, and how we get there incrementally without breaking
the customer.

The goal is not a rewrite. It's a **migration roadmap**: every
v2 idea expressed as a sequence of small refactors that ship as
ordinary commits, leave tests passing along the way, and let
customers keep using the system uninterrupted.

## What we'd keep (the wins)

These decisions paid off and v2 keeps them:

  1. **Pure stdlib + numpy + pandas + matplotlib + openpyxl
     dependency stance.** Every prospective dependency reviewed
     against the cost of dragging it in. We never pulled scipy,
     scikit-learn, plotly, requests, redis, celery, etc. Result:
     2-second cold start, simple deployment, fewer security
     audits.
  2. **Test culture.** ~9,700 tests as of head, all stdlib
     unittest, run in <1 minute. Every public surface has tests.
     Every recent module ships with its test file alongside.
  3. **Partner-narrative UX.** Dashboards adapt prose to the
     numbers. 'Good shape; focus on growth plays' beats a 4-card
     KPI grid. Recent UI sprint locked this in across
     dashboard_v3 + deal_profile_v2.
  4. **Provenance discipline.** Every modeled number carries (or
     can carry) a `DataPoint` with source + methodology +
     confidence + as-of-date. Recent UI sprint surfaced this in
     `provenance_badge.py` for partner-facing inspection.
  5. **Conventional commits.** `type(scope): subject` with body
     explaining *why* not *what*. Future developers read the
     commit log as documentation.
  6. **Single source-of-truth modules.** `colors.py`, `ui_kit.py`,
     `constants.py`, `metric_glossary.py`, `validators.py` —
     centralized common-pattern modules that prevent drift.

## What we'd rethink

These decisions were defensible at the time but cost us as the
codebase grew. v2 fixes them; this doc maps how to get there
incrementally.

### Lesson 1 — The DealAnalysisPacket is too monolithic

**Today**: One ~700-line dataclass with 20+ optional sections
(profile, observed_metrics, completeness, comparables,
predicted_metrics, ebitda_bridge, simulation, risk_flags,
provenance, diligence_questions, exports, regulatory_context,
v2_simulation, scenario_comparison, ...). Every new section
requires modifying the central class.

**Problem**: Tight coupling. Adding the next regulatory module
or the LEAD-track contract valuation requires editing
packet.py + adding an Optional field + threading it through 5
places.

**v2**: Section registry with typed plugin protocol.

```python
class PacketSection(Protocol):
    section_key: str
    def to_dict(self) -> Dict[str, Any]: ...
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PacketSection": ...

class Packet:
    sections: Dict[str, PacketSection]

    def add_section(self, section: PacketSection) -> None:
        self.sections[section.section_key] = section

    def get(self, section_key: str,
            type_: Type[T]) -> Optional[T]: ...
```

Each existing section migrates to a `PacketSection` subclass; the
central Packet shrinks to ~50 lines. New sections add by writing
their own dataclass, not editing a central file.

**Migration path**:

- **Step 1 (1 week)**: introduce the `PacketSection` protocol
  alongside the existing dataclass. New sections (LEAD,
  regulatory delta-impact) go through the new path; old ones
  stay.
- **Step 2 (4 weeks, one section per week)**: migrate each
  optional section to a `PacketSection` subclass. Tests verify
  byte-equivalence on `to_dict() / from_dict()` round-trip.
- **Step 3 (1 week)**: deprecate the old monolithic dataclass.
  Six weeks total.

### Lesson 2 — Asset class assumptions baked into hospital types

**Today**: `HospitalProfile` has `bed_count`, `cms_provider_id`,
fields. Predictors expect HCRIS-shaped features. Every module
named with 'hospital' in mind.

**Problem**: Multi-asset expansion (per the multi-asset plan)
requires extending or paralleling every primitive. A physician
group doesn't have `bed_count`; a behavioral health site doesn't
have `cms_provider_id`.

**v2**: Asset-class-aware `AssetProfile` protocol with
type-specific subclasses.

```python
class AssetProfile(Protocol):
    asset_id: str
    asset_class: AssetClass
    name: str
    state: str
    annual_revenue_mm: Optional[float]
    payer_mix: Dict[str, float]


class HospitalProfile(AssetProfile):
    bed_count: Optional[int]
    cms_provider_id: Optional[str]
    occupancy_rate: Optional[float]


class PhysicianGroupProfile(AssetProfile):
    npi: Optional[str]
    specialty: str
    physicians: List[PhysicianRoster]
```

**Migration path**: Already mapped in the multi-asset plan.
14-week build for the first non-hospital asset class
(physician groups); subsequent classes ~10 weeks each as the
abstraction firms up.

### Lesson 3 — server.py is a 16,000-line monolith

**Today**: All HTTP routes in one file with cascading
`if path == "/..." :` checks. Adding a route means editing
server.py at the right index position so it doesn't get
shadowed by a more general earlier match.

**Problem**: Easy to introduce route conflicts (we already
hit one — `/api/search` was claimed by cross-deal search;
new global search had to rename to `/api/global-search`).
Hard to find where a route is defined; tests for one feature
require touching the giant server.

**v2**: Per-feature router modules with explicit registration.

```python
# rcm_mc/server.py — under 500 lines
from .ui.dashboard_v3 import dashboard_v3_routes
from .data.catalog_routes import catalog_routes
from .ml.model_quality_routes import model_quality_routes

def build_handler() -> RCMHandler:
    handler = RCMHandler()
    handler.register(dashboard_v3_routes)
    handler.register(catalog_routes)
    handler.register(model_quality_routes)
    return handler
```

Each `*_routes` is a list of `Route(method, path_pattern,
handler_fn)` declarations. Conflicts caught at registration
time, not runtime.

**Migration path**:
- **Step 1 (2 weeks)**: build the router primitive +
  `Route` dataclass + registration system. server.py keeps
  its monolithic logic but registers routes through the new
  system.
- **Step 2 (8 weeks, ~10 routes/week)**: extract per-feature
  route groups. Each extraction is a self-contained PR with
  tests. End state: server.py is the application skeleton
  + middleware; every route lives in its feature module.
- **Step 3 (1 week)**: add registration-time conflict detection
  (raise on duplicate path/method registration).

### Lesson 4 — Predictors evolved with drift in their public APIs

**Today**: Each predictor (`predict_denial_rate`,
`predict_days_in_ar`, `predict_collection_rate`,
`predict_distress`) has its own signature shape. Some return
`(point, ci, explanation)` tuples; some return dicts; some
take a `state_rcm_factors` arg. The `auto_record` decorator
(per the learning loop plan) has to introspect each one.

**Problem**: Adding the 5th predictor means deciding which
signature to follow. Maintenance is harder than it should be.

**v2**: Single Predictor protocol everyone implements:

```python
class Predictor(Protocol):
    target_metric: str
    feature_names: List[str]
    sanity_range: Tuple[float, float]

    def predict(self, features: FeaturesDict) -> Prediction: ...
    def predict_with_interval(
        self, features: FeaturesDict,
    ) -> Tuple[Prediction, ConfidenceInterval]: ...
    def explain(
        self, features: FeaturesDict,
    ) -> List[FeatureContribution]: ...
```

Trained Ridge predictors, ensemble predictors, geographic
clustering — all conform. The auto_record decorator wraps
the protocol once; works on every implementation.

**Migration path**: 4 weeks. Each existing predictor gets a
thin protocol-conforming wrapper added; old direct API
remains as a deprecated alias for one release cycle.

### Lesson 5 — Configuration scattered across env vars + defaults + hardcoded values

**Today**: `RCM_MC_DB`, `RCM_MC_AUTH`, `RCM_MC_DASHBOARD`,
`CHARTIS_UI_V2`, `RCM_MC_HOMEPAGE`, plus the dataclass
defaults in `ServerConfig`, plus hardcoded thresholds in
~15 modules. Hard to know what's tunable.

**Problem**: New deployments require trial-and-error to
discover what env vars exist. Settings can drift between
environments.

**v2**: Single `Settings` module with declarative env-var
binding (similar to pydantic-settings, but stdlib-only for
the dependency stance).

```python
@dataclass
class Settings:
    db_path: str = field(
        default="~/.rcm_mc/portfolio.db",
        metadata={"env": "RCM_MC_DB"})
    auth_token: Optional[str] = field(
        default=None,
        metadata={"env": "RCM_MC_AUTH"})
    dashboard_default: str = field(
        default="legacy",
        metadata={"env": "RCM_MC_DASHBOARD",
                  "choices": ["v3", "legacy", "v2"]})
    panel_cache_ttl_seconds: int = field(
        default=300,
        metadata={"env": "RCM_MC_PANEL_TTL"})
    ...

settings = Settings.from_env()
```

Documentation auto-generates from the metadata. New env vars
can't sneak in without showing up in `Settings.from_env()`.

**Migration path**: 2 weeks. Build the `Settings` system; sweep
the codebase replacing `os.environ.get(...)` reads with
`settings.field`. Existing env-var names preserved for
compatibility.

### Lesson 6 — Storage is SQLite-only

**Today**: Every store class wraps `sqlite3` directly. Schemas
hardcoded as `CREATE TABLE IF NOT EXISTS` strings.

**Problem**: Multi-tenant deployment (per the PHI plan) needs
different storage (per-customer Postgres, S3 for blob, etc.).
Today's hard-coded `sqlite3` calls would need surgical
refactoring at every call site.

**v2**: Storage abstraction with SQLite + Postgres + DuckDB
drivers behind one interface.

```python
class Store(Protocol):
    def execute(self, sql: str, params: Tuple) -> Cursor: ...
    def begin_immediate(self) -> Transaction: ...
    def schema_migrate(self, migration: Migration) -> None: ...

class SQLiteStore(Store): ...
class PostgresStore(Store): ...
class DuckDBStore(Store): ...   # for analytical reads
```

Module code uses `Store`; deployment chooses driver. Same
patterns work for SQLite single-tenant + Postgres
multi-tenant + DuckDB analytical-cache.

**Migration path**: 8 weeks. Build the abstraction; migrate
PortfolioStore + PricingStore. Test both drivers in CI.

### Lesson 7 — Pandas creep in places dataclasses would be cleaner

**Today**: Some functions return `pd.DataFrame`; others return
`List[Dict]`; others return `List[dataclass]`. Inconsistent.
DataFrame in HTTP responses creates JSON serialization
overhead.

**Problem**: Three calling conventions, three serialization
paths. Tests have to juggle them.

**v2**: Dataclass-first. Pandas only for the analytical
operations that genuinely benefit (groupby, time-series,
cross-tab). HTTP responses always go through `to_dict()`.

**Migration path**: Slow opportunistic refactor. Each PR
that touches an old DataFrame-returning function has the
option to convert; not a forced sweep. ~6-12 months to
shake out completely.

### Lesson 8 — Inline-style HTML rendering instead of component composition

**Today**: HTML builders return string concatenations with
inline styles. Recent UI sprint introduced `ui_kit.py`
classes but didn't migrate every existing renderer.

**Problem**: Hard to unit-test a single section without
rendering the full page. Style drift (every page has its
own slightly-different button).

**v2**: Component-tree composition (still server-rendered;
no React).

```python
def render_dashboard():
    return Page(
        head=Head(title="Dashboard"),
        body=Body([
            HeroStrip(metrics),
            Section("Top opportunities",
                    OpportunitiesTable(opps)),
            Section("Key alerts",
                    AlertsList(alerts)),
        ])).render()
```

Each component is a small testable unit. Style centralized in
the canonical UI kit. Composition explicit.

**Migration path**: Already underway. The `ui_kit` + `colors`
+ `theme` + `responsive` modules are the foundation. Each
new page uses them; old pages migrate when convenient. ~6-12
months for full migration.

### Lesson 9 — Type hints exist but aren't enforced

**Today**: Most modules have type hints. mypy is in dev deps
but not in CI. Some signatures have `Any` where they could
be specific.

**Problem**: Type hints are documentation when not enforced;
they go stale.

**v2**: Strict mypy in CI. New modules ship with strict typing;
existing modules opt in incrementally.

**Migration path**: 2 weeks to set up CI + per-module mypy
override for legacy. ~6-12 months to remove the override
list as modules migrate.

---

## What v2.0 looks like end-to-end

After 12 months of incremental refactors:

```
rcm_mc/
├── core/
│   ├── settings.py          # declarative config
│   ├── storage.py           # Store protocol + drivers
│   ├── packet.py            # PacketSection registry
│   ├── predictor.py         # Predictor protocol
│   └── asset.py             # AssetProfile protocol
├── data/
│   ├── ingest/              # per-source ingestion (unchanged)
│   ├── feature_store.py     # cleaned + abstracted
│   └── catalog.py           # data inventory
├── ml/
│   ├── predictors/          # one module per predictor; all
│   │                          implement Predictor protocol
│   ├── ensemble.py          # ensemble methods
│   ├── learning/            # learning loop (auto_record etc.)
│   └── benchmarks/          # peer percentile lookup
├── ui/
│   ├── components/          # composable HTML components
│   ├── pages/               # one module per page
│   └── kit.py               # canonical styles
├── routes/                  # per-feature route registration
├── server/                  # ~500-line skeleton + middleware
├── exports/                 # multi-format renderers (unchanged)
├── auth/                    # auth + RBAC + audit (unchanged)
└── collab/                  # multi-user collaboration
```

The shape preserves what worked (small modules, clear
responsibilities, dataclass-first, no new runtime deps) while
fixing the painful coupling points.

## What we don't do in v2

  - **Rewrite from scratch.** A 12-month rewrite is a 12-month
    period of zero customer value. Every change above is an
    incremental refactor that ships through ordinary PR cycles.
  - **Switch frameworks.** No React, no FastAPI, no SQLAlchemy.
    The stdlib + numpy stance is the moat (per the keep list).
    Adding a framework in v2 dilutes that.
  - **Big-bang migrations.** Every refactor preserves
    byte-equivalent behavior on existing tests. Anywhere a new
    abstraction lands, the old API stays as a deprecation alias
    for at least one release cycle.
  - **Architecture astronaut work.** Every v2 lesson maps to a
    concrete problem we hit (route conflicts, asset class
    assumptions, monolithic packet, scattered config). No
    refactors for elegance alone.

## Migration sequence

The eight refactors above add up to roughly 35 weeks of work
serialized; ~22 weeks parallelized across two engineers. They
sequence as:

| Quarter | Focus | Lessons applied |
|---|---|---|
| Q1 | Quick wins | #5 Settings (2wk), #4 Predictor protocol (4wk), #9 mypy in CI (2wk) |
| Q2 | Routing + packet | #3 server.py extraction (8wk via 1 route group/week) |
| Q3 | Storage + asset | #1 PacketSection registry (6wk), #6 Storage abstraction (8wk) |
| Q4 | Component UI + asset class | #2 AssetProfile protocol (parallel with multi-asset expansion), #8 Component composition (rolling) |

The ordering reflects dependency: settings + protocols first
(small, low-risk), then routing (extracts feature modules), then
the deeper restructurings (packet + storage). Component UI
migration happens opportunistically throughout.

## What this enables

After v2, the things that are hard today get easy:

  - **New asset class** (post-acute, behavioral health, ASC):
    write the AssetProfile + 4-6 protocol-conforming predictors
    + add to packet section registry. ~10 weeks per class
    (down from ~14).
  - **New regulation tracking** (next CMS Innovation Center
    model, next state CPOM rule): write the data ingest +
    PacketSection. No central edits needed.
  - **Multi-tenant deployment** (per the PHI plan): swap the
    storage driver per customer. No application logic changes.
  - **Custom predictor for an Enterprise customer**: implement
    the Predictor protocol; plug in via the registry. Customer-
    specific code lives outside core, can be billed as
    professional services.
  - **Plugin marketplace**: third-party developers write
    PacketSection + Predictor implementations against the
    public protocols. The platform exposes a registration API.
    Adjacent revenue per the business model plan.

## Cost-benefit

Estimated effort: ~22 engineer-weeks parallelized across the
year. Estimated benefit:

  - **Multi-asset expansion velocity**: 30% faster per asset
    class after AssetProfile + protocol work lands.
  - **Enterprise deployment velocity**: 50% faster per customer
    after Settings + Storage + Routing extraction. Customer-
    specific configuration becomes declarative.
  - **Feature velocity**: ~20% per-feature build time savings
    once route extraction + packet section registry land. Less
    central-file touching = fewer merge conflicts + less
    review overhead.
  - **Onboarding velocity**: a new engineer reads the routing
    table + the protocol files and understands the system in
    a day. Today they read server.py for two days.

The discipline is: no refactor ships without a measurable
problem it solves. Architecture-astronaut tendencies get pushed
back at PR review.

---

## Final note: the lesson that matters most

The recent sprint shipped ~30 modules + 2,500 tests in a few
weeks. The codebase is in good shape because of the discipline
we've maintained — tests for everything, conventional commits,
no new runtime deps, semantic colors, canonical styles, central
constants, validators with clear errors.

The v2 plan above isn't a rebuke of the work. It's the natural
evolution of a fast-shipped codebase as it matures. Every lesson
is a lesson because we shipped enough to learn it. The cost of
not having known these lessons six months ago is far smaller
than the cost of having waited six months to ship anything.

The right reading of v2 is: 'we shipped, we learned, here's
what we'd refine next.' Not: 'we built the wrong thing.' The
platform works; the platform is loved; the platform has
customers. v2 makes it last.
