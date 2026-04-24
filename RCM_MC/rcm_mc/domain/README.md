# Domain

Healthcare revenue-cycle domain modeling: the economic ontology and custom metric registry. Provides the single source of truth for metric classification, causal relationships, and financial pathway mappings used across all downstream models.

---

## `econ_ontology.py` — Healthcare Revenue-Cycle Economic Ontology

**What it does:** Maps every metric the platform uses to its revenue-cycle domain, P&L pathway, causal parents/children, directionality (higher-is-better vs. lower-is-better), and reimbursement sensitivity. This is the single source of truth for metric semantics — every module that needs to understand *what a metric means economically* consults this module.

**How it works:** Defines a `MetricNode` dataclass per metric with fields: `domain` (enum: COVERAGE_PAYER_MIX / FRONT_END_ACCESS / MIDDLE_CYCLE_CODING / BACK_END_CLAIMS / WORKING_CAPITAL / PROFITABILITY / POLICY_REGULATORY / MARKET_STRUCTURE), `directionality` (HIGHER_IS_BETTER / LOWER_IS_BETTER), `causal_parents` (list of metric keys), `causal_children` (list of metric keys), `pl_pathway` (REVENUE / COST / WORKING_CAPITAL / MIXED), `reimbursement_sensitivity` (0.0–1.0 by method), `ebitda_sensitivity_weight` (used by `completeness.py` for data quality scoring), and `hfma_map_key` (HFMA MAP Keys reference for calibration defense). The full `METRIC_ONTOLOGY` dict has entries for all ~40 platform metrics. Module docstring cites HFMA MAP Keys 2023, AHRQ HCUP, and CMS IPPS rulemaking as the classification sources.

**Data in:** Static — the ontology is hand-authored and updated manually when the metric registry expands.

**Data out:** `MetricNode` objects consumed by: `ml/comparable_finder.py` (directionality), `ml/anomaly_detector.py` (causal consistency checks), `pe/lever_dependency.py` (dependency walk), `analysis/completeness.py` (sensitivity weights), `analysis/risk_flags.py` (domain classification), `analysis/deal_query.py` (field aliases), `analysis/cross_deal_search.py` (jargon expansion).

---

## `custom_metrics.py` — User-Defined Custom KPI Registry

**What it does:** Allows fund analysts to define custom KPIs beyond the standard metric registry — e.g., "same-day auth approval rate" for a specific specialty platform. Custom metrics integrate with the completeness scorer, risk flags, and the workbench display.

**How it works:** CRUD layer over the `custom_metrics` SQLite table. Each custom metric has: `metric_key` (unique), `display_name`, `unit` (percentage / dollar / days / ratio), `directionality` (higher/lower is better), `valid_min`, `valid_max`, and optional `ebitda_sensitivity_weight`. Custom metrics are merged into the effective metric registry at runtime — `get_effective_registry()` returns the standard ontology extended with any deal-specific or fund-wide custom metrics. Custom metrics cannot shadow standard metrics (the key must be unique across both registries).

**Data in:** Analyst-entered custom metric definitions via `POST /api/metrics/custom` or CLI; `custom_metrics` SQLite table.

**Data out:** Extended metric registry for `analysis/completeness.py`, `analysis/risk_flags.py`, and the workbench metric display.

---

## Key Concepts

- **Explicit mappings, not inference**: Every metric's classification is a hand-written dict entry partners can defend in IC. The ontology is not auto-learned from data.
- **Single source of truth**: Any code that needs to know "is `denial_rate` lower-is-better?" or "does this metric move revenue or cost?" consults `econ_ontology.py` — there is no other source.
- **Causal DAG**: The parent/child structure encodes healthcare revenue-cycle causality. Eligibility denial is a parent of total denial rate; total denial rate is a parent of net collection rate. This DAG powers both the double-counting prevention in the bridge and the anomaly detector's consistency checks.
- **Extensibility without shadowing**: Custom metrics extend the registry but cannot override standard classifications, preserving the audit trail.
