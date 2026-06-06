# UI Density & Wording Audit + Improvement Plan

Whole-app pass focused on **visual appeal, reduced text density, wording
quality, and de-cluttering** (not adding features). Driven by a rendered
crawl of 160 reachable pages measuring text volume, text density
(words per 1000px of page height), rendered em-dash count, panel/table
counts, plus targeted visual review.

This complements the layout/font/color sweep already shipped in PR #1614
(tooltips, tablet-responsive, charts, Guide, tools, fonts, colors, table
alignment, centering/sizing — all verified).

## Method & guardrails

- **No new clutter.** Improvements tighten wording, spacing, and
  consistency; they do not add UI or remove information partners rely on.
- **Em dashes:** target prose/copy em dashes (the "X — Y" aside that reads
  as AI-ish). The lone-glyph `—` used as a *missing-value placeholder* in
  table cells is a legitimate data convention and is left as-is (≈1,900 of
  the ~2,357 rendered em dashes are this kind).
- **Density:** prefer layout breathing room (line length, line-height,
  section spacing) over deleting partner-facing content.
- Every change is rendered-verified; the 2,878-test suite must stay green.

## Systemic findings

| Finding | Where | Action |
|---|---|---|
| Prose em dashes in shared nav descriptions | `_chartis_kit._NAV_DESC`, section blurbs | Reword (renders on every page) |
| Prose em dashes in page copy | conferences, deal-screening, deal-corpus, pe-intel, … | Reword per page |
| Dense prose walls (full-width small text) | conferences recaps, analytic intros | Cap prose line length + line-height |
| Missing-value `—` glyph | every data table | **Leave** (convention) |

## Prioritized targets (rendered crawl)

Ranked by a blend of text density (words/1000px), word count, and prose
em-dash count.

| Page | Words | Density | Prose em-dash | Note |
|---|---|---|---|---|
| `/conferences` | 3,595 | 488 | 131 | Dense recap prose; em dashes throughout |
| `/diligence/pe-library` | 3,649 | 353 | ~30 | Catalog (inherent density) + em dashes |
| `/deal-screening` | 3,524 | 310 | 78 | Thesis copy + tables |
| `/deal-quality` | 1,055 | 587 | ~5 | Tight stacked panels |
| `/pe-intelligence` | 796 | 363 | ~10 | Dense intel cards |
| `/diligence/management` | 863 | 320 | ~15 | Scorecard prose |
| `/tools` | 11,140 | 331 | ~140 | Tool index (catalog) |
| `/portfolio/regression` | 2,714 | 266 | ~35 | Heavy tables (alignment already fixed) |
| `/market-intel/seeking-alpha` | 1,923 | 261 | ~30 | Analyst prose |
| `/deal-corpus-analytics` | 908 | 185 | ~23 | Aggregate prose |

## Per-page plan (top targets)

### `/conferences` — Conference Intelligence
- **State:** masthead + long intro, a "New themes" 4-card grid (each a
  paragraph), then conference recaps that are dense bullet/prose walls at
  small size with em dashes throughout.
- **Affecting the look:** long full-width prose lines; em-dash-heavy copy;
  recap blocks read as walls.
- **Plan:** (1) reword prose em dashes → `:`/`,`/restructure; (2) cap recap
  prose line length for readability; (3) confirm section spacing rhythm.

### `/deal-screening` — Thesis-testing workspace
- **State:** thesis-as-thresholds intro + tables; 78 prose em dashes.
- **Plan:** reword em dashes in the thesis/threshold copy; verify the
  threshold table uses the now-global `.r`/`.mn` numeric styling.

### `/diligence/pe-library` & `/tools` — catalogs
- **State:** inherent density (222 / many tools). Not a wording problem.
- **Plan:** em dashes in tool descriptions only; otherwise leave (catalog).

### `/deal-quality`, `/pe-intelligence`, `/diligence/management`
- **State:** highest words-per-pixel — tightly stacked panels.
- **Plan:** section-spacing rhythm + em-dash wording; no content removal.

## Improvement roadmap (ordered, each its own commit)

1. **Shared nav em dashes** — reword `_NAV_DESC` + section blurbs (every page).
2. **Per-page prose em dashes** — conferences, deal-screening, deal-corpus,
   pe-intel, seeking-alpha, management.
3. **Prose readability** — cap body-paragraph line length where prose runs
   full panel width; confirm line-height on dense pages.
4. **Wording / title match** — page title ↔ nav label ↔ masthead consistency
   on the targets.
5. **Ghost/duplicate features** — audit for two surfaces with identical
   function (duplicate routes/links/actions); retire the stranded one.

Status is tracked by re-running the rendered crawl after each batch.
