# Acceptance Checklist

Print this, walk the platform, and check off each row. A page is "done" only when every row passes.

## Global chrome (check on any page)

- [ ] Background is parchment (`#f5f1ea`), not black.
- [ ] Top bar is white with a 1px `--sc-rule` bottom border.
- [ ] Wordmark: small navy circle mark + teal diagonal accent + serif "SeekingChartis" at 19px.
- [ ] Primary nav: Home · Pipeline · Library · Research · Portfolio (5 links, 13px, weight 500).
- [ ] Active nav link has a 2px teal underline. Inactive links are `--sc-text-dim`.
- [ ] Search input on the right is 220px wide minimum, bone-tinted, 1px rule border.
- [ ] User chip is a 32px navy circle with white initials, serif weight 600 12px.
- [ ] `⌘K` opens the command palette from anywhere. `Esc` closes it.
- [ ] Breadcrumbs row: mono 11px uppercase, teal `/` separators? (spec says `--sc-rule-2` separators — confirm).

## Typography

- [ ] Display headings (`.sc-display`, `.sc-h1`) render in **Source Serif 4** weight 400 with `-0.01em` tracking.
- [ ] Body copy renders in **Inter Tight** at 15px, line-height 1.55, color `--sc-text`.
- [ ] Numeric table cells render in **JetBrains Mono** with `font-variant-numeric: tabular-nums`.
- [ ] Eyebrows: 11px uppercase, weight 600, letter-spacing `0.18em`, with a 24×2 teal rule to the left.

## Data panels

- [ ] White card with 1px `--sc-rule` border, 2px radius, subtle shadow-1.
- [ ] Header strip is navy (`--sc-navy`) with uppercase tracked title on the left, `[CODE]` tag on the right in mono 10px.
- [ ] Body padding is exactly 24px (`--sc-s-6`). Not 20. Not 30.
- [ ] KPI blocks: 4-column grid, 11px uppercase label, 28px serif value, optional `+/-` trend in mono colored by sign.

## Tables

- [ ] Thead: bone background, 11px uppercase tracked column titles.
- [ ] Tbody: 8px/12px padding (5px/10px in `.ck-dense`).
- [ ] Numeric columns right-aligned with tabular-nums.
- [ ] Row dividers are 1px `--sc-rule`.
- [ ] No zebra striping unless explicitly requested.

## Accents (the teal budget)

Teal appears **only** as:
- [ ] The eyebrow rule before section headers.
- [ ] The underline on the active nav link.
- [ ] The diagonal on the wordmark mark.
- [ ] Corner brackets on hero imagery (`.sc-frame::before`, `.sc-frame::after`).
- [ ] Small ghost-button underlines.
- [ ] **Not** as fill on large surfaces. If you see a teal panel, that's a bug.

## Status colors

- [ ] Positive: `--sc-positive` (`#0a8a5f`) — never `#00ff9c` or `green`.
- [ ] Warning: `--sc-warning` (`#b8732a`) — never `#ffab00` or `orange`.
- [ ] Negative: `--sc-negative` (`#b5321e`) — never `#ff6b6b` or `red`.
- [ ] Critical: `--sc-critical` (`#8a1e0e`) for genuine alerts only.

## Spacing

- [ ] All paddings / margins come from the scale: 2/4/8/12/16/24/32/48/64/96.
- [ ] No stray `13px`, `27px`, `35px`.

## Responsive

- [ ] No horizontal scrollbar between 1024px and 1920px width.
- [ ] Top bar collapses to a hamburger under 900px.
- [ ] Data tables get an internal horizontal scroll before the page does.

## Print (for `/memo/<id>`, `/ic-packet/<id>`)

- [ ] Top bar, breadcrumbs, and palette hidden.
- [ ] Page background white, not parchment.
- [ ] Panels lose shadow, gain `break-inside: avoid`.
- [ ] Save-as-PDF produces a clean document with no cut-off panels.

## The ten gates (`HANDOFF_FOR_CURSOR.md` criteria)

These ten routes must pass every row above before you merge:

- [ ] `/` (marketing)
- [ ] `/home`
- [ ] `/pipeline`
- [ ] `/deal/<id>` (any deal)
- [ ] `/analysis/<id>`
- [ ] `/memo/<id>` (print preview)
- [ ] `/portfolio-analytics`
- [ ] `/pe-intelligence`
- [ ] `/payer-intelligence`
- [ ] `/corpus-backtest`
