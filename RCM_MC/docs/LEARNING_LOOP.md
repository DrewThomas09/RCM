# Learning Loop Architecture

The platform has the bones of a learning loop — `prediction_ledger.py`
records predictions + actuals, `model_quality.py` runs backtests with
CI calibration, the trained-predictor scaffold supports model
retraining. What's missing is the **closed-loop machinery** that
ties them together: every prediction is recorded automatically
(not opt-in), actuals get matched as they arrive, drift gets
detected, and retraining gets triggered.

This document maps the path from the existing partial pieces to a
true closed feedback loop where the platform's predictions get
better every quarter.

## What exists today

| Component | Module | Status |
|---|---|---|
| `predictions` table | `prediction_ledger.py` | Persists per-prediction record |
| `prediction_actuals` table | `prediction_ledger.py` | Links actuals to predictions |
| `model_performance_log` | `prediction_ledger.py` | Aggregate metrics over time |
| `record_prediction(...)` | `prediction_ledger.py` | Manual write — caller must remember |
| `record_actual(...)` | `prediction_ledger.py` | Manual write — caller must remember |
| `compute_metric_performance(...)` | `prediction_ledger.py` | MAE/RMSE/R²/coverage rate |
| `model_quality.py` backtests | `ml/model_quality.py` | CV R² + CI calibration |
| `temporal_forecaster.py` | `ml/temporal_forecaster.py` | Per-metric trend detection + forecasting |

The infrastructure is there. The gap is **automatic capture** + **drift
detection** + **retraining triggers**.

## Gap analysis: what makes this a true closed loop

### 1. Automatic prediction capture

**Today**: `record_prediction(...)` is a manual call. Callers
generally don't make it. Most prediction outputs disappear after
the partner views them — there's no learning from those.

**Need**: every call to a `predict_*()` function across the platform
auto-records. A decorator + a global ledger handle:

```python
@auto_record(metric="denial_rate")
def predict_denial_rate(predictor, hospital, ...):
    ...
```

The decorator extracts `(deal_id, metric, predicted_value, ci_low,
ci_high, model_version, predictor_id)` and writes to the ledger
without the caller doing anything.

### 2. Actual ingestion

**Today**: Actuals arrive via manual `record_actual(prediction_id,
value)` calls. No automated reconciliation.

**Need**: when fresh data lands (HCRIS refresh, internal portfolio
data, partner-supplied final numbers), the system finds matching
predictions and writes the actual:

```python
# Run during the data refresh job
from rcm_mc.learning import reconcile_actuals
n_matched = reconcile_actuals(
    store,
    metric="denial_rate",
    new_values={"450001": 0.094, ...},
    actual_period="2024-Q4")
```

`reconcile_actuals` walks the `predictions` table for predictions
whose target period matches `actual_period` and the entity matches,
and writes the actual.

### 3. Calibration drift detection

**Today**: `model_quality.calibrate_confidence_intervals()` checks
calibration on a held-out set at training time. Doesn't run on
production predictions over time.

**Need**: a recurring drift check. Every week, look at the
last-4-weeks of predictions whose actuals have arrived. Compute
CI coverage. If observed coverage drifts >5pp from nominal, fire
an alert.

```python
from rcm_mc.learning import drift_check
result = drift_check(
    store,
    metric="denial_rate",
    lookback_days=28,
    nominal_coverage=0.90)
if result.drifted:
    create_alert(
        kind="model_drift",
        message=f"denial_rate CI drift: "
                f"observed {result.observed_coverage:.0%} "
                f"vs nominal 90%")
```

### 4. Cohort failure analysis

**Today**: Aggregate metrics. No per-cohort breakdown.

**Need**: when overall MAE looks fine but the model is failing on
a subset (e.g., rural critical-access hospitals), surface that
specifically. Reuses the existing `cross_validate_across_cohorts`
machinery from `trained_rcm_predictor.py`.

```python
from rcm_mc.learning import cohort_failure_analysis
report = cohort_failure_analysis(
    store, metric="denial_rate",
    cohort_dimension="bed_size_bucket")
report.worst_cohort     # → 'critical_access'
report.worst_cohort_mae # → 0.045 vs overall 0.018
```

### 5. Override capture + learning

**Today**: When a partner overrides a prediction (sets
denial_rate manually because they have the actual data), the
override is stored on the deal but not fed back into the model.

**Need**: every override is a labeled training example —
high-confidence ground truth that should improve the model. Capture
override events; periodically retrain incorporating them.

```python
from rcm_mc.learning import override_event
override_event(
    store,
    deal_id="aurora",
    metric="denial_rate",
    predicted=0.10,
    actual_per_partner=0.08,
    partner_username="alice",
    note="from internal claim data")
```

These flow into a separate `override_log` table that the retraining
job consumes alongside the regular actuals.

### 6. Versioned retraining + champion/challenger

**Today**: A predictor is retrained ad-hoc; the new version replaces
the old. No way to compare new vs old on the same data.

**Need**: every retraining produces a new version that runs as a
**challenger** alongside the **champion** (the production version).
Both predict on every deal; we record both. After 4-8 weeks of
challenger data, decide whether to promote based on cohort-level
MAE comparison.

```python
from rcm_mc.learning import (
    train_challenger,
    evaluate_challenger,
    promote_challenger,
)

# Monthly retraining job
new_predictor = train_challenger(
    store, metric="denial_rate",
    base_version="v3.2")
# 4 weeks of side-by-side scoring later:
report = evaluate_challenger(
    store, metric="denial_rate")
if report.challenger_mae < report.champion_mae * 0.95:
    promote_challenger(
        store, metric="denial_rate")
```

## Architecture

### New module: `rcm_mc/learning/`

```
rcm_mc/learning/
├── __init__.py
├── auto_record.py       # decorator wrapping predict functions
├── reconcile.py         # match incoming actuals to open predictions
├── drift.py             # calibration drift detection + alerts
├── cohort.py            # per-cohort failure analysis
├── override.py          # capture partner overrides as labels
├── champion_challenger.py # versioned retraining + comparison
└── retrain_job.py       # periodic retraining orchestrator
```

### Schema additions

Existing tables (predictions, prediction_actuals, model_performance_log)
stay; we add:

```sql
CREATE TABLE override_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    prediction_id INTEGER,
    predicted_value REAL,
    actual_per_partner REAL NOT NULL,
    partner_username TEXT,
    note TEXT,
    captured_at TEXT NOT NULL,
    FOREIGN KEY (prediction_id) REFERENCES predictions(id)
);

CREATE TABLE model_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    version_label TEXT NOT NULL,
    role TEXT NOT NULL,        -- 'champion' | 'challenger' | 'retired'
    trained_at TEXT NOT NULL,
    train_window_start TEXT,
    train_window_end TEXT,
    n_train INTEGER,
    cv_r2 REAL,
    cv_mae REAL,
    promoted_at TEXT,
    notes TEXT,
    UNIQUE(metric, version_label)
);
CREATE INDEX idx_mv_metric_role
    ON model_versions(metric, role);

CREATE TABLE drift_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    observed_coverage REAL,
    nominal_coverage REAL,
    n_predictions INTEGER,
    severity TEXT,    -- 'minor' | 'major'
    resolved_at TEXT
);
```

### Public API surface

```python
# Auto-recording decorator (wraps every predict_*())
from rcm_mc.learning import auto_record

@auto_record(metric="denial_rate")
def predict_denial_rate(predictor, hospital):
    ...

# Reconciliation when actuals arrive
from rcm_mc.learning import reconcile_actuals
n = reconcile_actuals(
    store, metric="denial_rate",
    new_values={"450001": 0.094, ...})

# Drift detection (run weekly)
from rcm_mc.learning import drift_check, list_drifted_metrics
for metric in list_drifted_metrics(store):
    print(f"{metric} CI drifted; review needed")

# Cohort failure analysis (run monthly)
from rcm_mc.learning import cohort_failure_analysis
report = cohort_failure_analysis(
    store, metric="denial_rate",
    cohort_dimension="bed_size_bucket")

# Override capture (called from UI on every partner override)
from rcm_mc.learning import override_event
override_event(store, deal_id="aurora",
               metric="denial_rate",
               predicted=0.10,
               actual_per_partner=0.08,
               partner_username="alice")

# Champion/challenger lifecycle
from rcm_mc.learning import (
    train_challenger, evaluate_challenger,
    promote_challenger,
)
new_v = train_challenger(store, metric="denial_rate")
# ... 4 weeks of dual-scoring ...
report = evaluate_challenger(store, metric="denial_rate")
if report.challenger_mae < report.champion_mae * 0.95:
    promote_challenger(store, metric="denial_rate")
```

### UI changes

**Model quality dashboard** (`/models/quality`) gains:

- **Drift alert badges** — when a model has drifted, show
  the calibration band in red on the dashboard with a link to
  the drift_events history.
- **Champion/challenger view** — when a metric has both versions,
  show side-by-side MAE / R² / coverage so the partner sees
  what's being evaluated.
- **Cohort failure breakdown** — expandable section per metric
  showing per-cohort MAE; surfaces 'overall MAE 0.018, but
  critical_access 0.045' patterns.

**Per-deal override surface**:

- Inline 'override' link next to every modeled value on
  `/deal/<id>/profile`. Click → modal with optional note field.
- Saving captures both the override (which sets the deal-level
  value) AND the override_log entry (which feeds learning).

### Operational jobs

The learning loop runs continuously through three scheduled jobs:

| Job | Frequency | What it does |
|---|---|---|
| `reconcile_actuals` | Daily (after data refresh) | Match incoming HCRIS / portfolio data to open predictions; write actuals |
| `drift_check` | Weekly (Sunday night) | Calibration drift per metric; create alert if detected |
| `cohort_failure_analysis` | Monthly | Per-cohort MAE breakdown; surface worst cohort to /models/quality |
| `train_challenger` | Monthly (or after major drift) | Train a new version on accumulated actuals + overrides |
| `evaluate_challenger` | Weekly (after 4-8 weeks of dual-scoring) | Side-by-side champion-vs-challenger comparison |

## Build sequence

### Phase 1 — Auto-recording (3 weeks)

1. **Week 1**: `auto_record.py` decorator. Wraps every existing
   `predict_*()` function across the platform without changing
   their signatures. Tests verify side effects (writes to ledger)
   without affecting prediction values.
2. **Week 2**: Migrate the 4 existing trained-predictor public
   functions (`predict_denial_rate`, `predict_days_in_ar`,
   `predict_collection_rate`, `predict_distress`) to use the
   decorator.
3. **Week 3**: Backfill: for predictions made before
   auto-recording was wired in, no recovery — but document the
   data discontinuity in the model_quality dashboard.

### Phase 2 — Actual reconciliation (3 weeks)

1. **Week 1**: `reconcile.py` — match incoming actuals to open
   predictions by `(metric, entity_id, target_period)`.
2. **Week 2**: Hook into the existing data refresh job:
   after `cms_hcris.load(...)` writes new HCRIS rows, call
   `reconcile_actuals` for the metrics derived from them.
3. **Week 3**: UI surface — `/models/quality` shows
   'predictions matched' counts per metric over time.

### Phase 3 — Drift + cohort analysis (3 weeks)

1. **Week 1**: `drift.py` weekly drift_check job + drift_events
   table.
2. **Week 2**: `cohort.py` reusing the existing
   `cross_validate_across_cohorts` machinery.
3. **Week 3**: UI integration — drift badges + cohort failure
   breakdown on `/models/quality`.

### Phase 4 — Override capture (2 weeks)

1. **Week 1**: `override.py` + override_log schema. UI surfaces:
   override link per modeled value + modal.
2. **Week 2**: Tests verify override events flow into
   `train_challenger` correctly.

### Phase 5 — Champion/challenger (4 weeks)

1. **Week 1**: `champion_challenger.py` with `model_versions`
   schema; train_challenger orchestrator.
2. **Week 2**: Dual-scoring infrastructure — every prediction
   call records both champion and challenger.
3. **Week 3**: `evaluate_challenger` + `promote_challenger` with
   the 5%-MAE-improvement threshold.
4. **Week 4**: UI integration — champion vs challenger comparison
   on `/models/quality`.

**Total: 15 weeks for the full learning loop.**

If parallelized across two engineers: ~9 weeks.

## Risk + mitigation

- **Volume of predictions**: every UI render that surfaces a
  prediction triggers an auto-record write. At scale, this is
  hot — predictions table grows by 100K+ rows/day for a busy
  shop. Mitigation: write-batched + nightly archival of records
  >1 year old to a `predictions_archive` table.
- **Actual-prediction matching false positives**: a prediction
  for FY2024 denial_rate matched against an FY2023 actual is
  garbage data. Strict matching: `(metric, entity_id, period)`
  triple-key, with period validation.
- **Override quality**: not every partner override is ground truth.
  The `note` field captures the reason; retraining weighs override
  examples lower than direct-from-data actuals (0.5 vs 1.0
  weight) until the partner has a consistent track record.
- **Champion regression**: a challenger that looks better on the
  4-week window can be lucky. Promotion requires 5% improvement
  AND statistical-significance test (paired t-test on errors,
  p<0.05).
- **Privacy**: predictions tied to deal_id mean the ledger
  inherits deal-level access controls. The existing
  `external_users.can_access_deal()` check applies to ledger
  reads.

## Success metrics

After full rollout:

  - **Prediction recall**: every model output recorded; coverage
    rate in `model_performance_log` rises from ~0% to >95%.
  - **Time-to-actual**: median days between prediction and
    matched actual drops from undefined (manual recording) to
    <90 days (next HCRIS refresh).
  - **CI calibration**: observed coverage stays within ±3pp of
    nominal across all production predictors. Drift events
    decrease quarter-over-quarter.
  - **Cohort coverage**: `worst_cohort_mae / overall_mae` ratio
    drops as cohort-specific calibration improves over time.
  - **Model improvement velocity**: new champion promotion every
    1-2 quarters per metric, with each promotion documented in
    `model_versions` for IC defensibility.

## What this enables

The learning loop transforms the platform from a static analysis
tool into a **self-improving system**:

- Year 1 model: trained on calibration corpus + literature; ~75%
  of partner-quality predictions.
- Year 2 model: incorporates 12 months of actuals; ~85% of
  partner-quality predictions.
- Year 3 model: incorporates 24 months of actuals + partner
  overrides + cohort-specific calibrations; ~92% of partner-
  quality predictions.

That trajectory is the moat. Once 3 years of actuals are
incorporated, it becomes prohibitively expensive for a competitor
to catch up — they'd need a similar feedback loop running for the
same duration.

## What we don't try to do

  - **Online learning** (update model on every actual): too
    operationally complex; batch retraining on monthly cadence
    is plenty.
  - **Reinforcement learning**: the platform isn't choosing
    actions — it's predicting outcomes. Standard supervised
    retraining is the right tool.
  - **Generative model fine-tuning**: the platform's ML is Ridge
    regression + Bayesian shrinkage + ensemble methods. No LLMs
    in the prediction loop. Adding generative components later
    is opt-in via the same auto_record + champion/challenger
    framework — they slot in without re-architecting.
