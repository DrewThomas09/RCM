# Bear Case Auto-Generator

**In one sentence**: auto-writes the "what could break this thesis" memo section partners spend 3-5 hours writing by hand.

---

## What problem does this solve?

Every PE investment-committee memo has a section called the **bear case** — the honest case against the deal. Good IC members read it carefully. Lazy bear cases get the deal killed or the partner embarrassed.

Writing a bear case is laborious:
1. Partners re-read every diligence artifact
2. Pick the top 5-8 risks
3. Dollarize each one
4. Write a narrative paragraph per theme
5. Cite the source

**That's 3-5 hours per memo × 3-5 memo drafts per deal = 15-25 hours.** Gone.

This tool does it in **~100 milliseconds** — pulls evidence from 8 analytic modules, ranks by severity + dollar impact, produces a ranked evidence list + per-theme narratives + a print-ready IC-memo HTML block.

---

## How it works

1. **8 evidence extractors** — one per source module:
   - Regulatory Calendar → KILLED drivers + EBITDA overlay
   - Covenant Stress → 50%-breach covenants + equity cure size
   - Bridge Audit → OVERSTATED/UNSUPPORTED levers with $ gap
   - Deal MC → P10 MOIC tail + P(MOIC<1×)
   - Deal Autopsy → closest historical failure signature match
   - Exit Timing → 1.5× MOIC hurdle failures
   - Payer Stress → concentration risk + P10 NPR drag
   - HCRIS X-Ray → below-peer margins + deteriorating trends
2. **Ranking**: sort by severity (CRITICAL > HIGH > MEDIUM > LOW) × absolute $ impact × source-module priority
3. **Citation keys**: assign `[R1/R2]` to regulatory, `[C1]` covenant, `[B1]` bridge audit, `[M1]` MC, `[A1]` autopsy, `[E1]` exit, `[P1]` payer, `[H1]` HCRIS
4. **$ at risk aggregation**: sum gaps, but dedupe obvious overlaps (regulatory overlay vs bridge audit often double-count the same dollars)
5. **Partner-facing headline**: "Thesis is at risk on N CRITICAL items — $X M EBITDA at risk. Top drivers: [name-1, name-2, name-3]"
6. **Per-theme narratives**: grouped by REGULATORY / CREDIT / OPERATIONAL / MARKET / STRUCTURAL / PATTERN
7. **IC memo HTML**: dashed-border block with bold verdict + evidence table, print-ready via `@media print` CSS

---

## The demo moment

Partner runs the Thesis Pipeline at 10:15 AM. Clicks the Bear Case tile. 110 milliseconds later sees:

> **"Thesis is at risk on 7 CRITICAL evidence items — combined $46.8M of EBITDA at risk. Top drivers: Interest Coverage covenant, deteriorating HCRIS margin trend, V28 regulatory kill."**
>
> **29% of run-rate EBITDA at risk** (IC-killable territory)

Below that: 7-10 evidence cards color-coded by severity, each with:
- Citation key `[H1]`
- Severity chip (CRITICAL / HIGH / MEDIUM)
- Source module badge
- $ impact
- Narrative paragraph
- "Open source →" deep link back to the source module

At the bottom: a **copy-paste IC memo HTML block** in a dashed-border card. Partner Cmd-P's it into a clean PDF, pastes into Word, done.

---

## Verdict tone

| EBITDA at risk as % of run-rate | Tone |
|--------------------------------|------|
| **<3%** | clears IC |
| **3-10%** | watch |
| **10-25%** | material |
| **>25%** | IC-killable |

Rendered as a benchmark chip with peer-band coloring at the top of the page.

---

## Public API

```python
from rcm_mc.diligence.bear_case import (
    generate_bear_case,
    generate_bear_case_from_pipeline,
    Evidence, EvidenceSeverity, EvidenceSource, EvidenceTheme,
    BearCaseReport,
)

# Composed from pipeline output
from rcm_mc.diligence.thesis_pipeline import run_thesis_pipeline, PipelineInput
pipeline_report = run_thesis_pipeline(PipelineInput(
    dataset="hospital_04_mixed_payer",
    deal_name="Meadowbrook Regional",
    specialty="HOSPITAL",
    revenue_year0_usd=450_000_000,
    ebitda_year0_usd=67_500_000,
    hcris_ccn="010001",
    # ...
))
bc = generate_bear_case_from_pipeline(pipeline_report)
print(bc.headline)
print(bc.top_line_summary)
for e in bc.evidence[:5]:
    print(f"[{e.citation_key}] {e.severity.value} — {e.title}")
print(bc.ic_memo_html)  # paste into IC memo

# Or standalone with individual source reports
bc = generate_bear_case(
    target_name="Meadowbrook",
    regulatory_exposure=reg_report,
    covenant_stress=cov_report,
    bridge_audit=bridge_report,
    hcris_xray=hcris_report,
)
```

---

## Where it plugs in

- **Thesis Pipeline**: runs as a consumer step after every source module
- **IC Packet**: bear case HTML block auto-injected before `</body>`
- **Deal Profile**: tile under FINANCIAL phase
- **No-CCD fast path**: if no dataset fixture available (real deal without synthetic CCD), still runs Regulatory + HCRIS standalone

---

## Files

```
bear_case/
├── __init__.py
├── evidence.py      # Evidence dataclass + 8 extractor functions
└── generator.py     # orchestrator + ranking + narrative + IC memo HTML
```

---

## Tests

```bash
python -m pytest tests/test_bear_case.py -q
# Expected: 9 passed
```
