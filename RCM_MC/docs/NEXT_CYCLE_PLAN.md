# Next Cycle — Top 5 Highest-Impact Features

After the recent sprint shipped the UI scaffolding, predictor library,
and data ingestion layer, the platform is well-equipped to *analyze* a
deal. The gaps are now in the **workflow surrounding the analysis** —
how a deal gets in, how it moves through the pipeline, and how the
output reaches the partner's day-to-day.

Ranking by **PE analyst impact** (hours saved × frequency × decision
quality lift):

| # | Feature | Analyst Impact | Build Complexity |
|---|---|---|---|
| 1 | Document AI: CIM extraction | 4-8 hrs/deal saved × every deal | High |
| 2 | Deal pipeline tracker with stage gates | Daily; cross-deal visibility | Medium |
| 3 | Pre-IC memo auto-draft | 10+ hrs saved per IC | Medium |
| 4 | Returns backtesting library | LP/IC credibility, lower daily | High |
| 5 | Real-time collaboration / comments | Convenience, not must-have | Low |

The top three are below in implementation-plan detail. They share a
theme — they collapse the *time between data and decision*. Documents
become structured numbers automatically; pipeline state is one query
not five spreadsheets; IC memos start at 80% drafted.

---

## #1 — Document AI: CIM Extraction Pipeline

### Problem

Every PE deal starts with a CIM — a 50-150 page PDF the banker sends.
The analyst spends 4-8 hours typing numbers into spreadsheets:
historical financials, payer mix, bed counts, growth rates,
contracts, EBITDA adjustments. By the time the numbers are in, the
analyst is too steeped in mechanical work to do real analysis.

### What we ship

`rcm_mc/intake/cim_extractor.py` — pipeline that takes a CIM PDF and
produces:

- A populated `DealCandidate` with every numeric field the platform
  uses downstream (revenue, EBITDA, beds, payer mix, growth rate,
  case mix index, payer concentration).
- A **provenance trail** per number: page reference, source line,
  raw text, confidence score. Every extracted value clicks through
  to the source page so the analyst can validate.
- A **gap report** — fields the platform expected but couldn't find;
  the analyst types those manually.

### Architecture

```
CIM PDF
  ↓ (pdfplumber / pypdf2 — pure Python, no native deps)
Text + table-tagged chunks
  ↓ (regex + heuristic patterns — no LLM required for v1)
Per-field candidates (multiple guesses per field, confidence-scored)
  ↓ (rules: 'EBITDA' must be near 'M' or '$', range plausibility)
DealCandidate with provenance
```

**v1 (no LLM)**: regex + table-detection covers ~70% of fields with
high precision. Most CIMs follow boilerplate structure (Executive
Summary → Historical Financials → Operations → Customers).

**v2 (optional LLM)**: a `cim_extractor_llm.py` module that calls a
local model via prompt-template substitution if the partner has
`OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in env. Brings extraction to
~95% on free-form text. Optional — v1 provides full functionality
without external API dependency.

### Public API

```python
from rcm_mc.intake.cim_extractor import (
    extract_from_pdf, ExtractionResult, GapReport,
)

result: ExtractionResult = extract_from_pdf(
    "deals/aurora-cim.pdf",
    deal_id="aurora",
)
result.candidate          # → DealCandidate ready for screening
result.provenance         # → {field: (page, line, raw_text, confidence)}
result.gaps               # → GapReport listing fields not found
```

### Build phases

1. **Week 1**: `pdf_reader.py` — extract text + table cells with page
   references. Pure Python (`pdfplumber` if needed; degrade
   gracefully when not installed).
2. **Week 2**: `field_extractors.py` — 30 regex+heuristic extractors
   for the canonical fields. Each returns
   `(value, confidence, page, raw_text)`.
3. **Week 3**: `gap_report.py` — compares extracted set to the
   expected `DealCandidate` schema; surfaces missing fields with the
   reason (not found / low confidence).
4. **Week 4**: UI page `/intake/cim/<deal_id>` — drag-and-drop PDF,
   shows extracted values in the existing power_table component
   with provenance icons (using the recent-sprint
   `provenance_badge`); analyst confirms / overrides each value;
   "Save to deal" button.
5. **Test scope**: 5-10 sample anonymized CIMs in `tests/fixtures/`,
   verify ≥70% field-level extraction accuracy on the canonical
   schema.

### Risk + mitigation

- **PDF format variation**: Some CIMs are scanned images; they need
  OCR. v1 supports text-PDFs only; OCR is a stretch goal in v2.
- **Confidence calibration**: Wrong-but-confident extractions are
  worse than gaps. Conservative defaults — when uncertain, flag as
  gap rather than fill in noise. The partner reviews every value
  before it commits to the deal record.
- **Privacy**: CIMs are confidential. v1 runs entirely locally; no
  external API calls. v2 LLM mode is opt-in with explicit consent.

### Success metric

Time-to-screening (analyst receives CIM → first screening output)
drops from 4-8 hours to <30 minutes on 80% of deals.

---

## #2 — Deal Pipeline Tracker with Stage Gates

### Problem

A typical PE shop tracks 30-50 active deals across stages — sourcing,
initial screen, IOI, management meeting, LOI, diligence, IC review,
signed, closed. Today this tracking lives in 3-5 different places: a
deal log spreadsheet, partner email, Slack channels, CRM. Partners
spend a meaningful chunk of every Monday morning reconciling state.

The platform already has analytical depth on individual deals; what's
missing is the **portfolio-of-deals workflow surface** — pipeline
coverage gaps, deal-velocity bottlenecks, who's working on what.

### What we ship

`rcm_mc/pipeline/` — stage-gate tracker with:

- **Stages registry** — 9 canonical stages (sourcing → close), each
  with required fields the deal must have to advance. e.g., 'IOI'
  requires `revenue_mm`, `ebitda_mm`, `payer_concentration`.
- **Deal record** — `Deal(deal_id, stage, owner, target_close_date,
  next_action, ...)` with stage-history audit trail.
- **Stage gates** — programmatic checks ('to advance to IC, the deal
  must have a packet, a comp set, and an EBITDA bridge'). Block
  advancement when gates fail; surface the missing piece.
- **Pipeline view** at `/pipeline` — Kanban-style columns per stage,
  drag-to-advance. Each card shows stage age, owner, next action,
  gate status (green/red dot if ready to advance).
- **Velocity dashboard** — median time-in-stage, deals stuck >N
  days, conversion rate stage-to-stage. Fed by the stage-history
  audit trail.

### Schema

```sql
CREATE TABLE pipeline_deals (
    deal_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    stage TEXT NOT NULL,
    owner_username TEXT,
    target_close_date TEXT,
    next_action TEXT,
    sector TEXT,
    estimated_ev_mm REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE pipeline_stage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    from_stage TEXT,
    to_stage TEXT NOT NULL,
    moved_by_username TEXT,
    moved_at TEXT NOT NULL,
    note TEXT
);

CREATE INDEX idx_pipeline_owner
    ON pipeline_deals(owner_username, stage);
```

### Public API

```python
from rcm_mc.pipeline import (
    Deal, Stage, advance_deal,
    list_pipeline, gate_check,
    velocity_metrics,
)

# Move a deal forward; gates run automatically
result = advance_deal(store, "aurora", to_stage="LOI",
                      moved_by="alice")
if not result.ok:
    print(result.gates_failed)  # → ['No comp set built']

# Pipeline view — partner's morning question
deals_by_stage = list_pipeline(store, owner="alice")

# Velocity view — IC question
metrics = velocity_metrics(store, lookback_days=180)
metrics.median_days_in_stage  # → {stage: days}
metrics.conversion_rate       # → {(from, to): rate}
```

### UI

- `/pipeline` — Kanban board (existing `compare.py` patterns scale
  to the column layout). Drag-to-advance triggers
  `advance_deal()`; failed gates show the inline empty-state
  pattern from `empty_states.py`.
- `/pipeline/velocity` — chart panel using `power_chart.py` for the
  median-time-in-stage line + funnel for conversion rates.
- Dashboard v3 hero strip gains a 6th KPI: 'Deals at gate' (count
  with `gate_check()` returning 'ready to advance').

### Build phases

1. **Week 1**: Schema + `Deal` dataclass + `advance_deal()` with
   stage validation. Tests cover every gate + stage transition.
2. **Week 2**: `gate_check()` + `velocity_metrics()` + the
   pipeline_stage_history audit trail. Tests for each.
3. **Week 3**: `/pipeline` Kanban view using existing UI kit.
   Drag-and-drop via vanilla JS (no framework).
4. **Week 4**: Velocity dashboard + dashboard v3 hero KPI
   integration. End-to-end HTTP test for the workflow
   (drag deal → advance → audit row written).

### Success metric

Partner answers 'where are we on Project X?' in 1 click instead of
opening 3 tools. Pipeline review meeting shrinks from 90 minutes to
30 because the data is already organized.

---

## #3 — Pre-IC Memo Auto-Draft

### Problem

The platform already produces a structured `DealAnalysisPacket` with
every number an IC memo needs (financial profile, comps, predictions,
EBITDA bridge, scenarios, risks, diligence questions). The analyst
then writes 15-30 pages of *narrative* to wrap those numbers — which
is what IC actually reads.

That writing is 10+ hours of repetitive prose: 'Project Aurora is a
{archetype} in {state} with {beds} beds operating at {margin}% EBITDA
margin against a peer median of {peer_margin}%...'. The numbers are
already in the packet; the prose is just templated narrative around
them.

### What we ship

`rcm_mc/exports/ic_memo_auto.py` — auto-drafts the IC memo as
production-ready Markdown / HTML / Word, ready for the analyst to edit.

Two-tier approach:

- **v1 (template-based)**: Jinja-style templates per memo section
  (Executive Summary, Market, Operations, Financials, Bridge,
  Scenarios, Risks, Recommendation). Pure-Python templating; no LLM.
  Produces 80% of the prose with deterministic phrasing — analyst
  edits the 20% that needs judgment.
- **v2 (optional LLM polish)**: Same skeleton, but each section's
  prose is regenerated by a local LLM call from the underlying
  numbers + a calibrated prompt. Gives the prose more variation and
  a more 'analyst voice' feel. Optional — v1 ships fully functional.

### Architecture

```
DealAnalysisPacket (already exists)
  ↓
Section templates (per IC section)
  ↓
Rendered Markdown (with provenance footnotes per number)
  ↓
HTML / Word / PDF via existing PacketRenderer
```

### Public API

```python
from rcm_mc.exports.ic_memo_auto import (
    auto_draft_memo, MemoSection, IC_MEMO_SECTIONS,
)

# Default: 8-section memo with conventional structure
draft = auto_draft_memo(packet)
draft.markdown      # → str (15-30 pages, partner edits)
draft.sections      # → list[MemoSection] for granular re-render

# Custom: render only specific sections
draft = auto_draft_memo(
    packet,
    sections=["executive_summary", "bridge", "risks"])
```

### Templates

Each of the 8 sections has its own template module:

```
rcm_mc/exports/ic_memo_auto/
├── _executive_summary.py
├── _market.py
├── _operations.py
├── _financials.py
├── _bridge.py
├── _scenarios.py
├── _risks.py
└── _recommendation.py
```

Each module exports `render(packet) -> str`, returning Markdown for
that section. Section ordering is fixed by `IC_MEMO_SECTIONS`.

Provenance — every number in the rendered prose carries a footnote
like `^[1]` linking to the source (HCRIS row, predictor model, peer
median calculation). Footnotes resolve at the end of the memo. This
matches the existing `provenance_badge.py` pattern and keeps the IC
defensible.

### UI

`/deal/<deal_id>/ic-memo` — page renders the auto-drafted memo with:
- **Edit mode** — `contenteditable` div per section; analyst types
  inline; save persists via POST to
  `/api/deals/<id>/ic-memo/section/<section>`.
- **Re-draft** button per section — re-runs the template against the
  packet (useful after the packet refreshes with new data).
- **Export** — Word/PDF/Markdown via existing `PacketRenderer`.

### Build phases

1. **Week 1**: 4 most-load-bearing templates (executive_summary,
   bridge, scenarios, risks). Each pure-function `render(packet)`
   returning Markdown. Tests verify: no traceback, key numbers
   appear in output, footnote markers present.
2. **Week 2**: Remaining 4 templates + footnote resolver +
   memo-level composer.
3. **Week 3**: `/deal/<id>/ic-memo` UI with contenteditable +
   per-section save endpoint.
4. **Week 4**: Word + PDF export integration via PacketRenderer.

### Success metric

Analyst time to produce a first-draft IC memo drops from 10-15 hours
to <2 hours (mostly editing the 20% the auto-draft can't write).

---

## Why these three (and what to defer)

The fourth and fifth ranked features (returns backtesting, real-time
collaboration) are valuable but defer for one reason each:

- **Returns backtesting** is a moat-builder for LP fundraising and IC
  credibility. It requires 5+ years of historical exit data the
  platform doesn't have curated yet. Most impactful when paired with
  a real portfolio history; until then, partner gets the same value
  from the existing predictor backtests.

- **Real-time collaboration** is a convenience that becomes a must
  when 4+ analysts work the same deal simultaneously. Most PE shops
  in the platform's current sweet spot (3-12 person investment teams)
  manage this fine via Slack threads and shared screens. Build when
  team size demands it.

The three above are **high-impact every day** for **every analyst on
every deal** — the largest realized analyst-hours saved per quarter.
