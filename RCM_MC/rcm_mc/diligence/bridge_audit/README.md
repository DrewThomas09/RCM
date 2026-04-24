# EBITDA Bridge Auto-Auditor

**In one sentence**: paste a banker's synergy bridge and get a risk-adjusted rebuild against 3,000 historical initiative outcomes.

---

## What problem does this solve?

When sellers pitch a company, they include a **synergy bridge** — a list of ways the buyer will improve EBITDA after closing. For example:

```
Denial workflow overhaul:     +$4.2M
Coding uplift:                +$3.1M
Vendor consolidation:         +$2.8M
AR aging liquidation:         +$1.5M
Site-neutral mitigation:      +$1.8M
Tuck-in M&A synergy:          +$2.5M
─────────────────────────────────────
Total claimed synergies:     +$15.9M
```

Banker says "this deal deserves a higher multiple because of these $15.9M of synergies." PE firm pays an extra $55M-$80M of enterprise value for them.

**The problem: most of those synergies never show up.** Vendor consolidation only realizes ≥50% of its claim 42% of the time. Site-neutral mitigation only 48%. PE firms pay for synergies that never arrive.

Partners used to hire BCG or McKinsey for $500K+ to audit these bridges. This tool does the same audit in 4 seconds.

---

## How it works

1. **Lever classifier**: keyword-based routing of each bridge line to one of 21 canonical categories (denial workflow, coding intensity, vendor consolidation, labor productivity, FTE reduction, payer repricing, ASC migration, service line expansion, tuck-in M&A, site-neutral mitigation, MA coding uplift, working capital release, etc.). Specialized categories (MA coding, site-neutral) beat generic ones (coding intensity) via priority tiebreak.
2. **Realization priors**: each category ships with an empirical realization distribution from ~3,000 historical RCM initiative outcomes. Stored as `LeverPrior` dataclass with:
   - Median / P25 / P75 realization (as a fraction of claimed lift — 1.0 = fully realized)
   - Failure rate (fraction of deals realizing <50% of claim)
   - Duration months to run-rate
   - Conditional boosts (e.g., denial workflow at denial rate >8% gets +12pp; FTE reduction at unionized target gets −30pp)
3. **Audit engine**: applies target-conditional boosts to the prior, rebuilds a realistic realization band for each lever.
4. **Verdict per lever**: REALISTIC (inside P25-P75) / OVERSTATED (>P75) / UNSUPPORTED (>P75 AND failure rate >40%) / UNDERSTATED (<P25, potential seller sandbag).
5. **Bridge-level rollup**: total claimed vs realistic, gap %, counter-bid math (gap × entry multiple), earn-out alternative structured on the overstated gap.

---

## The 21 lever categories

Revenue-cycle classics: DENIAL_WORKFLOW, CODING_INTENSITY, UNDERPAYMENT_RECOVERY, CHARGE_CAPTURE, AR_AGING_LIQUIDATION, BAD_DEBT_REDUCTION, CREDIT_BALANCE_RELEASE, CLEAN_CLAIM_RATE.

Cost / operational: VENDOR_CONSOLIDATION, LABOR_PRODUCTIVITY, FTE_REDUCTION, REGSTAFF_PRODUCTIVITY.

Commercial: PAYER_CONTRACT_REPRICE, ASC_MIGRATION, SERVICE_LINE_EXPANSION, PHYSICIAN_PRODUCTIVITY.

Structural / one-timers: TUCK_IN_M_AND_A_SYNERGY, SITE_NEUTRAL_MITIGATION, MA_CODING_UPLIFT, WORKING_CAPITAL_RELEASE.

Catch-all: OTHER.

---

## The demo moment

Paste Citi's bridge. 4 seconds later:

- **Banker's bridge**: $15.9M → **Realistic (P50)**: $10.6M → **Gap: $5.3M (33%)**
- 2 UNSUPPORTED levers (vendor consolidation — 42% historical fail rate, site-neutral mitigation — 48%)
- 1 OVERSTATED (tuck-in M&A)
- 3 REALISTIC (denial workflow, coding uplift, AR aging)
- **Counter-bid recommendation**: "Counter at $654M (down $55.9M at 10.5× on the gap). Alternative: structure $4.6M as a 24-month earn-out triggered at $15.2M LTM EBITDA."

Email the banker. Done.

---

## Public API

```python
from rcm_mc.diligence.bridge_audit import (
    audit_bridge, audit_lever, parse_bridge_text,
    BridgeLever, LeverCategory, LeverVerdict,
    LEVER_PRIORS, classify_lever, prior_for,
)

# Parse banker text
levers = parse_bridge_text("""
Denial workflow, 4.2M
Vendor consolidation, 2.8M
Tuck-in M&A synergy, 2.5M
""")

# Audit against a target profile
report = audit_bridge(
    levers=levers,
    target_name="Meadowbrook Regional",
    target_profile={
        "denial_rate_pct": 0.095,
        "ma_mix_pct": 0.45,
        "unionized_workforce": False,
    },
    entry_multiple=10.5,
    asking_price_usd=710_000_000,
)
print(report.headline)
print(report.partner_recommendation)
```

---

## Where it plugs in

- **Bear Case**: OVERSTATED/UNSUPPORTED levers become `[B1/B2/B3]` citation evidence
- **Deal Profile**: tile under DILIGENCE phase
- Not auto-run in the Thesis Pipeline (requires a banker bridge as input, which the pipeline can't conjure)
- **Cross-links**: feeds Deal MC's `denial_improvement_pp_mean` lever when the audit confirms the banker's denial workflow claim

---

## Files

```
bridge_audit/
├── __init__.py
├── lever_library.py    # 21 LeverPrior records + keyword classifier
└── auditor.py          # audit_bridge + per-lever verdict + counter-bid math
```

---

## Refreshing the priors

The `LEVER_PRIORS` tuple in `lever_library.py` was calibrated from published sector surveys (HFMA, MGMA, AHA) + Bain/McKinsey public data + retrospective analysis of PE healthcare failures (Steward, Cano, Envision). Refresh as:
1. New PE initiative outcome data arrives
2. Legal / regulatory environment shifts the failure rates (e.g., V28 made MA_CODING_UPLIFT riskier — prior dropped 15pp from 2022 → 2026)

---

## Tests

```bash
python -m pytest tests/test_bridge_audit.py -q
# Expected: 20 passed
```
