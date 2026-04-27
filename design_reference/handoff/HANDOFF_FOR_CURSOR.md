# SeekingChartis — UI Rework Handoff

**To:** Cursor (or any engineer picking this up)
**From:** Andrew / design
**Context:** `DrewThomas09/RCM` → `RCM_MC/` — RCM-MC v0.6.0.
**Reference mockup:** `SeekingChartis Rework.html` (single self-contained file; five linked screens + 79 module surfaces, all catalog-driven).

---

## TL;DR — what you are doing

Reskin the SeekingChartis platform from the **dark Bloomberg/Palantir terminal** look to an **editorial healthcare-PE** look (navy + teal + parchment, Source Serif 4 display + Inter Tight UI + JetBrains Mono numerics).

**You are not rebuilding pages.** Every existing page renderer in `rcm_mc/ui/*.py` keeps its signature, its route, its data plumbing, its Monte Carlo engine, its Bayesian posteriors, its provenance system, everything. You are replacing **one shared shell file** (`_chartis_kit.py`) and adding **one CSS token file** that the shell links — and that's 95% of the job. The remaining 5% is sanity-checking individual pages for hardcoded dark-palette hex codes and swapping them for tokens.

---

## The exact change set

### 1. Drop in the new shell

- Replace `rcm_mc/ui/_chartis_kit.py` with `CHARTIS_KIT_REWORK.py` from this handoff.
  - Signatures preserved: `chartis_shell`, `ck_table`, `ck_fmt_currency`, `ck_fmt_percent`, `ck_fmt_number`, `ck_signal_badge`, `ck_kpi_block`, `ck_section_header`, `ck_panel`, `_CORPUS_NAV`, `_LEGACY_NAV`.
  - What changes internally: the `P` palette dict, the `<head>` CSS block, the top-bar markup, and the panel chrome (header strip + `[CODE]` tag).

- Drop `handoff/chartis_tokens.css` into the repo at `rcm_mc/ui/static/chartis_tokens.css` (or wherever static assets live — see `server.py` static handler).
  - The new shell `<link>`s this file. If you prefer zero static-file plumbing, inline the `:root { … }` block into the shell's `<style>` tag; both work.

### 2. Re-wire the navigation

The current shell uses a dense left sidebar + fixed dark bar. The rework uses a **single editorial top bar** with horizontal nav — see `SeekingChartis Rework.html` screen 03 (signed-in home).

- Top-bar structure (already implemented in `CHARTIS_KIT_REWORK.py`):
  - Left: wordmark (serif "SeekingChartis" + small navy circle mark + teal diagonal accent)
  - Center: primary nav — **Home · Pipeline · Library · Research · Portfolio**
  - Right: search input, notifications bell, user chip with initials
- Secondary nav (the 40+ deep links — scenario modeler, EBITDA bridge, payer intelligence, etc.) moves into a **"Platform Index" grid on Home** and a **"Jump to…" command palette (⌘K)** on every page. The grid is already in the mockup; the palette is in `CHARTIS_KIT_REWORK.py` as `ck_command_palette()`.

### 3. Per-page audit (grep + replace)

Most pages will "just work" because they use `ck_panel`, `ck_table`, `ck_kpi_block`, etc. But some pages inline raw HTML with hardcoded colors from the old palette. Run these:

```bash
# Find hardcoded dark-palette hex codes
rg -n '#0a0a0a|#111|#1a1a1a|#202020|#2a2a2a' rcm_mc/ui/

# Find hardcoded accent colors that should be teal
rg -n '#00ff|#33ff|#ff6b|#ffab' rcm_mc/ui/

# Find any inline `background: #000` or `color: #fff` stragglers
rg -n 'background:\s*#(000|fff)' rcm_mc/ui/
rg -n 'color:\s*#(fff|f5f5)' rcm_mc/ui/
```

Replace with tokens from `chartis_tokens.css`:

| Old dark palette             | New token            |
|------------------------------|----------------------|
| `#0a0a0a` / `#111` page bg   | `var(--sc-parchment)` |
| `#1a1a1a` panel bg           | `#ffffff`            |
| `#2a2a2a` panel border       | `var(--sc-rule)`     |
| `#e0e0e0` body text          | `var(--sc-text)`     |
| `#808080` dim text           | `var(--sc-text-dim)` |
| `#00ff9c` positive signal    | `var(--sc-positive)` |
| `#ff6b6b` negative signal    | `var(--sc-negative)` |
| `#33ffff` / any cyan accent  | `var(--sc-teal)`     |
| `#ffab00` warning            | `var(--sc-warning)`  |

### 4. Typography

All pages inherit from `<body>` which now uses Inter Tight. To opt a heading into the serif display face, add class `sc-h1` / `sc-h2` / `sc-display` (defined in `chartis_tokens.css`). Numeric cells stay on JetBrains Mono via `.sc-num`.

No font files to ship — Google Fonts CDN is already linked in the shell's `<head>` (Source Serif 4, Inter Tight, JetBrains Mono).

### 5. The module catalog → route sanity check

See `MODULE_ROUTE_MAP.md` — a table of every module surface in the mockup with its route and source `.py` file. Confirm each row resolves to a working route; file bugs for any that don't.

---

## Acceptance criteria

A page is "done" when, running the repo locally (`python seekingchartis.py`) and hitting its route:

1. **Background is parchment**, not black.
2. **Panels are white cards** with a thin navy header strip and a small `[CODE]` tag (e.g. `[BRG-01]`) top-right.
3. **Display headings are serif** (Source Serif 4, weight 400, letter-spacing `-0.01em`).
4. **Body text is Inter Tight**, 15px, `#1a2332`.
5. **Numeric tables stay mono** and right-aligned with `tabular-nums`.
6. **Teal (`#2fb3ad`)** appears as an accent only — small eyebrow rules above section headers, the underline on the active nav link, the diagonal in the wordmark, and the corner brackets on hero imagery. Never as fill on large surfaces.
7. **Spacing scale** is 4/8/12/16/24/32/48/64/96 — no arbitrary values like `13px` or `27px`.
8. **Status colors** come from the `--sc-positive / --sc-warning / --sc-negative / --sc-critical` tokens, not from inline hex.
9. No horizontal scrollbar under 1280px; the top bar collapses to a hamburger under 900px.
10. Print stylesheet works for `/memo/<id>` and `/ic-packet/<id>` — the IC-memo route should save-as-PDF cleanly with no cut-off panels.

---

## Order of operations

1. Land `CHARTIS_KIT_REWORK.py` + `chartis_tokens.css`. Push, pull locally, smoke-test with `python seekingchartis.py`. You should see the new shell on the home page and every route should still render (just with the new chrome).
2. Run the grep commands above. Fix hardcoded hex codes page by page — most are one-line swaps.
3. Walk the module list in `MODULE_ROUTE_MAP.md`. For each row, hit the route and confirm acceptance criteria 1–8. Flag anything weird.
4. Do the three "hero" surfaces by hand: `/` (marketing), `/login`, `/home`. These match the mockup closely — cross-reference `SeekingChartis Rework.html` screens 01/02/03 and make sure the layout matches.
5. Ship behind a feature flag if you want: `CHARTIS_UI_V2=1` environment variable, gated in `_chartis_kit.py`'s `chartis_shell()`. Fall back to old shell when unset.

---

## What's in this handoff folder

| File | Purpose |
|---|---|
| `HANDOFF_FOR_CURSOR.md` | This file. |
| `CHARTIS_KIT_REWORK.py` | Drop-in replacement for `rcm_mc/ui/_chartis_kit.py`. |
| `chartis_tokens.css` | CSS tokens the new shell links. |
| `MODULE_ROUTE_MAP.md` | All 79 module surfaces → routes → source .py files. |
| `SeekingChartis Rework.html` | The self-contained mockup. Open in any browser. Five screens + 79 module detail pages. |

---

## Cursor prompt (copy-paste)

> You are reskinning the SeekingChartis platform (RCM-MC v0.6.0) from a dark terminal aesthetic to an editorial healthcare-PE look. The complete handoff package is in `handoff/`. Read `handoff/HANDOFF_FOR_CURSOR.md` first — it has the exact change set, acceptance criteria, and order of operations. Start by landing `CHARTIS_KIT_REWORK.py` as `rcm_mc/ui/_chartis_kit.py` and `chartis_tokens.css` as `rcm_mc/ui/static/chartis_tokens.css`, then run `python seekingchartis.py` and confirm the new shell renders on `/`. Do not change any page's signature, data source, or route. Work through `MODULE_ROUTE_MAP.md` row by row.

---

## Questions / gotchas

- **278 pages, really?** The public README says 278; the catalog in the mockup is 79 *surfaces* (pages the user lands on). The 278 figure counts every sub-route, API endpoint that returns HTML, and per-deal variant. If any of the 199 deltas are user-facing pages I missed, add them to `MODULE_ROUTE_MAP.md` and keep going.
- **Feature flag vs hard cutover?** My recommendation: feature-flag for the first merge so the team can toggle between old and new shells during review. Remove the flag once accepted.
- **What about `_chartis_kit.py`'s `_CORPUS_NAV` and `_LEGACY_NAV`?** Both preserved. `_CORPUS_NAV` drives the new top bar + Platform Index grid. `_LEGACY_NAV` is kept for backwards-compatible callers.
