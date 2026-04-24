# Regulatory Calendar × Thesis Kill-Switch

**In one sentence**: tells you exactly when a government rule change will damage or kill your investment thesis.

---

## What problem does this solve?

Every PE healthcare deal dies on a regulatory surprise the firm knew was coming. CMS, OIG, FTC, DOJ, and CMS IDR all publish their rule-making calendars publicly. Nobody productizes them against a specific target's thesis drivers.

Traditional diligence says "regulatory risk is moderate" — fuzzy, unhelpful.

**This module says**: *"Your thesis driver 'MA margin lift' dies on 2027-01-01 when CMS V28 final rule takes effect. Residual value: 0.0 pp out of claimed 5.5 pp. On the same day, your 'coding intensity uplift' driver dies too."*

Specific date. Specific driver. Specific dollar impact. That's the demo moment no other diligence tool produces.

---

## How it works

1. **Curated library of 11 regulatory events** (CMS V28 HCC, OPPS site-neutral CY2026, TEAM mandatory bundled payment, NSA IDR QPA recalculation, ESRD PPS CY2027, FTC HSR expansion, USAP FTC consent order, Connecticut HB 5316 sale-leaseback phaseout, CMS PFS E/M updates, OIG management-fee advisory opinion, DOJ FCA retroactive coding). Each carries:
   - Publish date + effective date
   - Affected specialties
   - Expected revenue / margin impact
   - Named thesis drivers it kills (MA_MARGIN_LIFT, CODING_INTENSITY_UPLIFT, HOPD_REVENUE, LEJR_MARGIN, etc.)
   - Source URL (public docket)
   - Narrative explanation

2. **Impact mapper** takes your target profile (specialty, MA mix, payer share, HOPD revenue, REIT landlord) and figures out which drivers the event actually hits on your specific hospital. A 90%-MA platform is KILLED by V28; a 30%-MA hybrid is DAMAGED; a 5%-MA community hospital is UNAFFECTED.

3. **Kill-switch verdict engine** rolls up to a PASS / CAUTION / WARNING / FAIL verdict plus:
   - Risk score 0-100
   - Per-driver timeline with first-kill date
   - EBITDA overlay (per-year $ impact that feeds Deal MC's `reg_headwind_usd` lever)

---

## Verdict thresholds

| Verdict | Meaning |
|---------|---------|
| **PASS** | No driver impaired >10% |
| **CAUTION** | 1 driver damaged, none killed |
| **WARNING** | 1 driver killed OR 2+ damaged |
| **FAIL** | 2+ drivers killed |

---

## The demo moment

Partner opens /diligence/regulatory-calendar with a hospital deal. They see:

- **Verdict: FAIL** · Risk score 90
- Red chip: *"Net Leverage covenant dies on 2026-01-01"*
- **Gantt timeline**: thesis drivers on the Y axis, calendar dates on the X axis. Red dots mark KILLED events. Amber dots mark DAMAGED.
- **EBITDA overlay table**: −$2.7M (2026) · −$10.6M (2027) · −$1.8M (2028) · total −$15.1M over the hold

The partner immediately knows *which specific driver* dies *on which specific date* — and that overlay feeds the downstream Deal MC cone.

---

## Public API

```python
from rcm_mc.diligence.regulatory_calendar import (
    analyze_regulatory_exposure,
    upcoming_events,
    events_for_specialty,
    map_event_to_drivers,
    RegulatoryEvent,
    KillSwitchVerdict,
    ThesisDriver,
    DEFAULT_THESIS_DRIVERS,
)

# Full analysis
report = analyze_regulatory_exposure(
    target_profile={
        "specialties": ["HOSPITAL", "MA_RISK_PRIMARY_CARE"],
        "ma_mix_pct": 0.55,
        "has_hopd_revenue": True,
        "has_reit_landlord": True,
        "revenue_usd": 450_000_000,
        "ebitda_usd": 67_500_000,
    },
    horizon_months=24,
)
print(report.verdict)
print(report.headline)
for tl in report.driver_timelines:
    if tl.worst_verdict.value != "UNAFFECTED":
        print(f"{tl.driver_label}: {tl.worst_verdict.value} on {tl.first_kill_date}")
```

---

## Where it plugs in

- **Thesis Pipeline**: auto-runs; overlay feeds `DealScenario.reg_headwind_usd`
- **Bear Case**: KILLED drivers become `[R1]` citation evidence
- **Deal Profile**: has a tile under DILIGENCE phase
- **IC Packet**: a Regulatory Timeline block is auto-injected into the memo HTML

---

## Files in this module

```
regulatory_calendar/
├── __init__.py         # Public API re-exports
├── calendar.py         # 11 curated regulatory events + query helpers (401 LOC)
├── impact_mapper.py    # Per-driver impact verdict given target profile (395 LOC)
└── killswitch.py       # Overall verdict + EBITDA overlay + narrative (487 LOC)
```

### `__init__.py` (thin)
Re-exports the public API: `analyze_regulatory_exposure`, `upcoming_events`, `events_for_specialty`, `map_event_to_drivers`, `RegulatoryEvent`, `KillSwitchVerdict`, `ThesisDriver`, `DEFAULT_THESIS_DRIVERS`.

### `calendar.py` (401 LOC)
The **curated event library**. One hand-written `RegulatoryEvent` dataclass per rule (11 today). Each event carries publish date, effective date, affected specialties, expected revenue/margin impact, thesis drivers it kills, source URL, and narrative. Query helpers:

- `upcoming_events(horizon_months)` — events effective in the next N months
- `events_for_specialty(specialty)` — filter by specialty tag
- `events_affecting_driver(driver_name)` — reverse lookup by driver

**To add a new event** (e.g., a 2027 CMS rule): append a `RegulatoryEvent(...)` to `REGULATORY_EVENTS` at the bottom of this file. No other code changes needed.

### `impact_mapper.py` (395 LOC)
Takes **one event × one target profile** and returns the impact verdict (`UNAFFECTED / DAMAGED / KILLED`) per thesis driver. This is where the MA-mix-sensitive logic lives — a 90%-MA platform gets KILLED by V28 but a 5%-MA community hospital is UNAFFECTED. Pure functions, no I/O.

Key entry: `map_event_to_drivers(event, target_profile, drivers) → List[DriverImpact]`.

### `killswitch.py` (487 LOC)
The **partner-facing synthesizer**. Runs every event through `impact_mapper`, rolls per-driver verdicts into a calendar timeline (first-kill date per driver), computes per-year EBITDA overlay (feeds Deal MC's `reg_headwind_usd`), produces partner narrative, and assigns the final PASS/CAUTION/WARNING/FAIL verdict.

Key entry: `analyze_regulatory_exposure(target_profile, horizon_months) → RegulatoryExposureReport`.

---

## Adjacent files

- **[`rcm_mc/ui/regulatory_calendar_page.py`](../../ui/regulatory_calendar_page.py)** — web page at `/diligence/regulatory-calendar`
- **[`tests/test_regulatory_calendar.py`](../../../tests/test_regulatory_calendar.py)** — 21 tests covering mapper logic, verdict thresholds, overlay math

---

## Refreshing the event library

The YAML-style dataclass library in `calendar.py` is hand-curated. Refresh quarterly by:
1. Scanning the Federal Register for new CMS proposed rules
2. Checking OIG advisory opinions issued
3. Watching FTC consent orders in healthcare
4. Reviewing state legislative actions (CPOM, sale-leaseback bans, etc.)
5. Updating dates + impact estimates in `calendar.py::REGULATORY_EVENTS`

---

## Tests

```bash
python -m pytest tests/test_regulatory_calendar.py -q
# Expected: 21 passed
```
