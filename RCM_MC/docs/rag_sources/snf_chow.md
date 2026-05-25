# CMS SNF Change of Ownership (consolidation signal)

**Source:** CMS "Skilled Nursing Facility Change of Ownership" (data.cms.gov,
public). Aggregated at ingest to ownership-change counts by state × year.
**Powers:** the consolidation-velocity line on `/market-intel/geo` state market
context.

**Coverage:** **5,141** SNF ownership changes, **2016–2025**, 51 states.
National trend rose 244 (2016) → 882 (2023). Per-state totals (TX 697, CA 393,
OH 310, IL 306, PA 283 lead).

**What it can support:** relative nursing-home M&A / consolidation velocity by
state and over time; a deal-flow / roll-up activity signal; "is this a
consolidating market?" diligence framing.

**What it cannot support:** it is **not a PE-specific flag** (the buyer type is
not classified here), **not every healthcare transaction** (Medicare-enrolled
SNF ownership changes only), and **not provider-specific performance**. It
counts ownership-change events, not deal values.

**Source label:** `CMS PUBLIC DATA`. Enrollment/NPI identifiers dropped at
ingest. Refresh by re-running `scripts/ingest_snf_chow.py`.

**Suggested Guide questions:**
- "How active is nursing-home consolidation in this state?"
- "Is SNF ownership-change activity rising nationally?"
- "Which states have the most SNF ownership changes?"
- "Does this flag private-equity buyers?" (no — buyer type unclassified)
- "Is this every transaction?" (no — Medicare-enrolled SNF CHOWs only)
