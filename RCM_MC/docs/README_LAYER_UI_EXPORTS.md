# Layer: UI + Exports (`rcm_mc/ui/`, `rcm_mc/exports/`)

## TL;DR

Two sibling layers with one shared principle: **render from the
packet, never from the store.** The UI produces the Bloomberg-style
analyst workbench at `/analysis/<deal_id>`. The exports layer emits
HTML / PPTX / JSON / CSV / DOCX artifacts for diligence memos and
portfolio LP updates — every artifact footer prints the packet hash
+ run_id so partners can trace a printed deck back to the exact
analysis run that produced it.

## What this layer owns

- `rcm_mc/ui/analysis_workbench.py` — single-file HTML renderer for
  the `/analysis/<deal_id>` page.
- `rcm_mc/exports/packet_renderer.py` — 6-method `PacketRenderer`
  class covering every export format.
- `rcm_mc/exports/export_store.py` — `generated_exports` audit table.
- Older UI / report modules (`rcm_mc/ui/_ui_kit.py`,
  `rcm_mc/reports/*`) — legacy surface that coexists with the new
  packet-driven layer.

## Files — UI layer

### `analysis_workbench.py` (~930 lines)

**Purpose.** Produce one full HTML document for `/analysis/<deal_id>`.
Every tab reads from the single packet; nothing renders from separate
store queries.

**Key export.** `render_workbench(packet: DealAnalysisPacket) -> str`.

**Palette.** `PALETTE` dict — exposed so tests assert specific tokens
are in the output:
- `bg: #0a0e17`, `panel: #111827`, `panel_alt: #0f172a`,
  `border: #1e293b`.
- `text: #e2e8f0`, `text_dim: #94a3b8`, `text_faint: #64748b`.
- `positive: #10b981`, `negative: #ef4444`, `warning: #f59e0b`,
  `neutral: #6366f1`, `accent: #3b82f6`.
- Severity: `critical: #dc2626`, `high: #f59e0b`, `medium: #eab308`,
  `low: #64748b`.

**Typography.** JetBrains Mono on every `.num` cell, KPI number, and
hero number. System-sans for body copy. No border-radius > 4px. Cell
padding 6px/10px. Alternating-row table striping.

**Layout.**
1. **Sticky header** — deal name, completeness badge, freshness,
   Rebuild button, JSON / Provenance / Diligence CSV links.
2. **Sticky tab nav** — Overview / RCM Profile / EBITDA Bridge /
   Monte Carlo / Scenarios / Risk & Diligence / Provenance.
3. **Overview** — radial SVG progress ring for completeness, top-5
   missing metrics by sensitivity, key-findings list (severity-
   sorted), EBITDA hero number + EV-at-multiple strip, MOIC line,
   risk-summary colored badges.
4. **RCM Profile** — dense 8-column table (metric / current / source
   icon / P25 / P50 / P75 / Δ vs P50 / confidence bar), rows grouped
   by category header, green/amber/red coloring vs benchmark P50.
   Plus a 4-payer denial heatmap.
5. **EBITDA Bridge** — per-lever sliders on the left,
   HTML/CSS waterfall on the right, sensitivity tornado below,
   summary box at the bottom.
6. **Monte Carlo** — inline SVG histogram with P10/P50/P90 dashed
   verticals, summary stats table, MOIC band line, variance-
   contribution tornado.
7. **Scenarios** (Prompt 20) — up to four side-by-side scenario
   cards (base / upside / downside / management plan). Each card:
   scenario name, P10/P50/P90 EBITDA, P50 MOIC, inline SVG mini-
   histogram (200×60 bars from `histogram_data`, or triangular
   fallback from the percentile set), top-3 variance drivers.
   Below the cards: a pairwise-win-probability matrix (green/red
   tinting for cells above 60% / below 40%), rationale text, and
   a stacked overlay SVG with one 40%-opacity filled path per
   scenario on a shared x-axis derived from the overall
   EBITDA-impact range. The recommended scenario (max mean −
   risk_aversion×downside_σ) carries a 2px accent border and a
   pill badge. An "Add Scenario" button reveals a per-lever form
   pre-filled from the current bridge targets; submit fires
   `POST /api/analysis/<id>/simulate/compare` and reloads. The
   builder never runs comparison automatically — comparisons are
   on-demand because each is a full MC.
8. **Risk & Diligence** — left colored risk cards
   (severity border-left), right diligence questions grouped by
   P0/P1/P2.
9. **Provenance** — `<details>` tree by ID prefix (observed /
   predicted / bridge / comparables / mc), one row per node.

**Interactive JavaScript** (~80 LOC vanilla, no framework):
- Tab switching via `classList.toggle('active')`.
- Slider `oninput` → 300ms debounce → `fetch POST /api/analysis/
  <deal_id>/bridge` with JSON body `{targets, financials}` →
  re-renders waterfall + summary client-side from the response.
- `#wb-bridge-bootstrap` script tag carries the initial
  assumptions JSON.
- Scenarios tab: Add-scenario trigger toggles the form's `hidden`
  class; submit collects `[data-scenario-target]` inputs into a
  `{metric: MetricAssumption}` map, posts to
  `/api/analysis/<id>/simulate/compare`, and reloads on success.

**Design rules.**
- CSS scoped under `.analysis-workbench` so it coexists with the
  legacy `_ui_kit.py` light theme without visual collision.
- Every number runs through one of `_fmt_money`, `_fmt_pct`,
  `_fmt_num`, `_fmt_moic`, `_fmt_signed_pct` for formatting
  consistency.
- Empty-state rendering never throws — a minimal packet still
  produces a valid page.

### `_ui_kit.py` (~330 lines)

**Purpose.** Legacy shared-design-system shell used by older UI
pages (dashboard, deal page, portfolio operations). Light theme;
separate from the Bloomberg workbench CSS.

**Public.**
- `BASE_CSS` — shared stylesheet.
- `PALETTE` — named colors.
- `shell(body, title, *, back_href, subtitle, extra_css, extra_js,
  generated, omit_h1) -> str` — wraps a body fragment in the standard
  document layout with breadcrumb, title, CSRF-patching JS, footer.

### Other UI modules (legacy)

- `_html_polish.py` — HTML post-processing helpers.
- `_workbook_style.py` — Excel-style HTML table styling.
- `csv_to_html.py` — render CSV → HTML table.
- `json_to_html.py` — render JSON → HTML nested list.
- `text_to_html.py` — render plain text → HTML with glyph wrapping.

## Files — Exports layer

### `packet_renderer.py` (~740 lines)

**Purpose.** All six export paths produce artifacts from the same
`DealAnalysisPacket`. No independent store queries.

**Key class.** `PacketRenderer(out_dir=None)`. Defaults to a temp
dir; server uses a long-lived path.

**`AuditFooter` dataclass** — every export format embeds this:
```
Generated by RCM-MC v1.0 on 2026-04-15 09:23 UTC
Analysis Packet ID: 20260415T092300Z-ab12cd
Input Hash: sha256:deadbeef...
This analysis is based on 7 observed and 4 predicted metrics.
Model version: 1.0
```

**Seven render methods.**

1. **`render_diligence_memo_html(packet, *, inputs_hash) -> str`** —
   8-section IC memo. Sections: Executive Summary, Data Completeness
   & Quality, RCM Performance Summary (with source icons), EBITDA
   Value Creation Opportunity (with waterfall table), Risk
   Assessment (top-5 flags), Monte Carlo Returns Summary (P10/P50/
   P90), Key Diligence Questions (P0 only), Comparable Set. Footer
   with packet hash.

2. **`render_diligence_memo_pptx(packet, *, inputs_hash) -> Path`** —
   8-slide deck. Title / Exec / RCM Profile / Bridge / MC / Risks /
   Questions / Comparables+Audit. Uses `python-pptx` if installed.
   When absent (Prompt 22 improvement), builds a minimal valid OOXML
   `.pptx` via stdlib `zipfile` + inline XML templates — still 8
   slides, still opens in PowerPoint + LibreOffice. No more
   `.pptx.txt` sibling file.

3. **`render_deal_xlsx(packet, *, inputs_hash) -> Path`** (Prompt 22)
   — six-sheet workbook via `openpyxl`:
     - **RCM Profile** — one row per metric, `current_value` cell
       tinted green/amber/red vs registry P50 (with metric-direction
       awareness: denial_rate is lower-is-better, net_collection_rate
       is higher-is-better).
     - **EBITDA Bridge** — per-lever impact table + `TOTAL` row +
       inline bar chart.
     - **Monte Carlo** — P10/P25/P50/P75/P90 rows for EBITDA/MOIC/
       IRR, convergence flag, plus a v2 histogram block when the
       packet carries `v2_simulation`.
     - **Risk Flags** — severity-sorted; severity cell tinted with
       the workbench palette (critical red → low grey).
     - **Raw Data** — exact same columns as the CSV export (scripts
       parsing the CSV can migrate to xlsx without schema drift).
     - **Audit** — deal + run identification, completeness grade,
       observed/predicted/override counts, per-override detail block.
   Falls back to `render_raw_data_csv` when `openpyxl` is missing
   (the base dep list ships with it, so this only triggers in
   pruned environments).

4. **`render_packet_json(packet) -> str`** — `packet.to_json(indent=2)`.
   The canonical wire format.

5. **`render_raw_data_csv(packet, *, inputs_hash) -> Path`** — columns
   `metric_key, display_name, current_value, source, benchmark_p50,
   predicted_value, ci_low, ci_high, ebitda_impact, risk_flags`.
   Audit footer as trailing `# ...` comment rows.

6. **`render_lp_update_html(packets: Iterable[DealAnalysisPacket])
   -> str`** — portfolio roll-up. Headline stats (deal_count,
   total_opportunity, critical_risks) + one card per deal with name,
   EBITDA opportunity, top risk flag, top diligence question, audit
   trail.

7. **`render_diligence_questions_docx(packet, *, inputs_hash) ->
   Path`** — formatted Word doc grouped by priority → category.
   Uses `python-docx` if installed; falls back to `.md` partners
   paste into Word/Docs.

**Optional deps.** `openpyxl` is in the base dependency list — xlsx
is the primary partner download. `python-pptx` is optional (opt in
via `pip install rcm-mc[exports]`); the stdlib fallback covers the
PPTX path when it's absent. `python-docx` stays optional with the
`.md` fallback.

### `export_store.py` (~90 lines)

**Purpose.** Audit log of every export.

**Table.**
```sql
CREATE TABLE generated_exports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    analysis_run_id TEXT,
    format TEXT NOT NULL,
    filepath TEXT,                  -- NULL when rendered inline
    generated_at TEXT NOT NULL,
    generated_by TEXT,
    file_size_bytes INTEGER,
    packet_hash TEXT
);
```

**Public.**
- `record_export(store, *, deal_id, analysis_run_id, format,
  filepath, file_size_bytes, packet_hash, generated_by)`.
- `list_exports(store, deal_id=None, *, limit=100)`.

### `__init__.py`

Re-exports `PacketRenderer`, `record_export`, `list_exports`.

## API + HTTP routes

- `GET /analysis/<deal_id>` — Bloomberg workbench
  (`ui.analysis_workbench.render_workbench(packet)`).
- `GET /api/analysis/<deal_id>/export?format=html|pptx|xlsx|json|csv|questions`
  — streams the file bytes with `Content-Disposition: attachment`,
  writes one row to `generated_exports`. The `xlsx` format returns
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
  when openpyxl is installed, falling back to `text/csv` otherwise
  (same filename, `.csv` extension).
- `GET /exports/lp-update?days=30` — portfolio LP update HTML from
  all recent analysis packets.

## The footer invariant

Every format embeds the same `AuditFooter` fields:

| Format | Footer location |
|---|---|
| HTML memo | `<footer class="memo-footer">` before `</body>` |
| PPTX (python-pptx) | Slide 8 body placeholder |
| PPTX fallback (.txt) | Trailing `FOOTER\n...` block |
| JSON | Packet fields (`run_id`, `model_version`, timestamps) |
| CSV | Trailing `# ...` comment rows |
| DOCX (python-docx) | Dedicated "Audit Trail" section at end |
| DOCX fallback (.md) | Trailing `## Audit Trail` section |
| LP update | `<footer class="lp-audit">` with aggregate audit |

A partner with a printed deck can always match it back to
`analysis_runs` via the `run_id` + `input_hash`. This is the
audit-defensibility invariant.

## Current state

### Strong points
- **Single renderer per format** — if the memo and the workbench
  disagree, it's a template bug, not a data bug.
- **Graceful optional-dep fallback** — partners pasting from a
  `.pptx.txt` or `.md` file is an acceptable workflow; never a
  silent `None`.
- **Every export audited.** The `generated_exports` table records
  who / when / what format / what packet_hash — partners can answer
  "where did this deck come from?" from SQLite alone.
- **18 export tests + 14 workbench tests** verify section presence,
  specific-number quoting, palette tokens, slider JS behavior, and
  footer consistency across all four formats.

### Weak points
- **Bloomberg workbench is single-file HTML** — tab switching + slider
  debounce live in inline `<script>`. Good for "no framework" but
  limits complexity. Real dashboards with live data subscriptions
  would need a small framework.
- **No .xlsx export.** Partners sometimes want Excel-native columns
  (the CSV opens fine in Excel but lacks formatting). python-
  openpyxl would add another optional dep.
- **PPTX fallback is a flat outline**, not slide-shaped. Partners
  pasting into their own deck template is the workaround; a better
  fallback would generate a minimal Office Open XML zip by hand.
- **Export files land in a temp dir** — cleaned up on process
  restart. Long-lived deploys need a persistent directory
  convention (pointing `PacketRenderer(out_dir=...)` at a shared
  volume).
- **No scheduled LP updates.** `rcm-mc portfolio lp-update` exists;
  partners run it manually or via external cron. No built-in
  email-on-schedule flow.
