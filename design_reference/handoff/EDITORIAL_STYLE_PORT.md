# SeekingChartis — Editorial Style Port

**Audience:** Claude Code, working in the `RCM_MC` repository.
**Goal:** Replace the current dark-themed deployed UI (`pedesk.app`) with the editorial parchment-and-serif style established in this design project's `SeekingChartis.html`, `login.html`, `forgot.html`, and `SeekingChartis Command Center.html`.
**Reference designs:** sit alongside this file in `handoff/` and at the project root.

---

## 0. The decision

**Adopt the editorial style as the canonical SeekingChartis aesthetic.** The dark navy + cyan terminal look (`/diligence/deal/<slug>`, RCM Diligence sidebar, etc.) is being retired. New UI is:

- **Parchment background** (`#F2EDE3`), white panels (`#FFFFFF`)
- **Source Serif 4** for display + body, **Inter** for labels/UI, **JetBrains Mono** for numbers/source paths
- **Teal `#1F7A75`** as the only accent — a one-rule editorial accent, never a fill
- **Italics** for emphasis (e.g. *one source of truth*) — never bold for emphasis
- **Bordered viz + dataset pairs** as the signature module pattern (chart on the left, raw table on the right, both inside one outer rule)
- **Square corners**, hairline `1px` rules in `#D6CFC0` / `#BFB6A2`, no shadows, no glows, no gradients

Every new screen and every existing screen ported.

---

## 1. Source-of-truth files in this design project

Open these and read them before touching the repo:

| File | What it is | What to copy from it |
|---|---|---|
| `SeekingChartis.html` | Marketing landing | Hero, value-prop trio, paired funnel + dataset, proof grid, module catalog, pull-quote, dark CTA strip |
| `login.html` | Sign-in / Request Access | Split editorial layout, last-session teaser card, SSO row, tabs |
| `forgot.html` | Password recovery | Single-card editorial form pattern |
| `SeekingChartis Command Center.html` (+ `cc-app.jsx`, `cc-components.jsx`, `cc-data.jsx`) | The canonical dashboard | Topbar, crumbs, page header, KPI strip, **all paired viz+dataset blocks**, deal context bar, covenant heatmap, drag bar, initiative tracker, alerts |

The CSS in each file is **self-contained and consistent** — same custom-property names, same spacing, same type. When porting, lift the `:root` block and the component CSS into your own stylesheet.

---

## 2. The flow

```
SeekingChartis.html  (marketing — public)
       │
       ▼
login.html           (sign in / request access / SSO)
       │   ↘ forgot.html
       ▼
SeekingChartis Command Center.html  (the live dashboard)
```

Marketing is the entry point. Login is gating. Dashboard is the only authenticated surface.

In the deployed app, the routes should be:

| Route | File / view |
|---|---|
| `/` | landing (replaces current `/diligence` index) |
| `/login` | login (new) |
| `/forgot` | forgot password (new) |
| `/app` (or `/dashboard`) | command center (replaces current `/diligence/deal/<slug>` console) |
| `/app/deal/<slug>/profile` | deal profile (port to editorial style) |
| `/app/deal/<slug>/3-stmt` | financials (port — no more dark table) |
| `/app/deal/<slug>/<module>` | every other module |

The current sidebar (Deal Profile, Thesis Pipeline, Checklist, Ingestion, Benchmarks, etc.) becomes the **left-rail navigation inside `/app`**, but rendered in the editorial style — see §5.

---

## 3. Design tokens (paste into `chartis_tokens.css` as the single source of truth)

```css
:root {
  /* surfaces */
  --bg:           #F2EDE3;   /* parchment page */
  --bg-alt:       #ECE5D6;   /* deeper parchment for sources block */
  --bg-tint:      #E8E0D0;   /* row hover, hot rows */
  --paper:        #FAF7F0;   /* near-white panels */
  --paper-pure:   #FFFFFF;   /* primary card surface */

  /* rules */
  --border:       #D6CFC0;   /* hairline, internal */
  --border-strong:#C2B9A6;   /* heavier internal */
  --rule:         #BFB6A2;   /* outer rule on cards */

  /* ink */
  --ink:          #0F1C2E;   /* near-black navy */
  --ink-2:        #1A2840;
  --muted:        #5C6878;
  --faint:        #8A92A0;

  /* accent */
  --teal:         #1F7A75;   /* the only accent — always a 1px rule or italic text */
  --teal-soft:    #D4E4E2;
  --teal-deep:    #155752;

  /* status (use sparingly — for numbers and pills only) */
  --green:        #3F7D4D;  --green-soft: #DCE6D9;
  --amber:        #B7791F;  --amber-soft: #EFE2BC;
  --red:          #A53A2D;  --red-soft:   #EBD3CD;
  --blue:         #2C5C84;  --blue-soft:  #D6E1EB;
}
```

Do **not** introduce new accent colors. Do **not** use shadows. Do **not** use gradients. Do **not** round corners more than `0px`. (Pills are an exception — they use `999px`.)

---

## 4. Type stack

```css
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

body { font-family: "Source Serif 4", Georgia, serif; }
.sans { font-family: "Inter", -apple-system, sans-serif; }
.mono { font-family: "JetBrains Mono", "SF Mono", monospace; font-feature-settings: "tnum" on; }
```

**Type rules:**

- **H1 / Display:** Source Serif 4, weight 400, `clamp(2.6rem, 4.8vw, 5.5rem)`, line-height 1.0–1.05, letter-spacing `-0.022em`. **Italicize one phrase per headline** for editorial rhythm (color the italic span `var(--teal-deep)`).
- **H2:** Source Serif 4, 400, `clamp(2.3rem, 3.6vw, 3.4rem)`, often two lines with a `<br/>`.
- **H3 (panel titles):** Source Serif 4, 400, `1.2rem`.
- **Body / lede:** Source Serif 4, `1.05–1.4rem`, `var(--muted)`.
- **Labels / nav / buttons:** Inter, 700, `.68–.76rem`, `letter-spacing: .14em`, `text-transform: uppercase`.
- **Numbers / source paths / file names:** JetBrains Mono, `tabular-nums`. Sources colored `var(--teal-deep)`.
- **Eyebrow micro-label:** `.micro` class — Inter 700, `.68rem`, `.18em` letter-spacing, uppercase, `var(--muted)`.

**Never use bold for emphasis in body copy. Use italics.**

---

## 5. The signature pattern — paired viz + dataset

Every analytical section in the dashboard renders as a **`.pair`** block: visualization on the left (1.4fr), live dataset table on the right (1fr), both wrapped in one outer rule.

```html
<div class="pair">
  <div class="viz">
    <!-- chart, sparkline, funnel, heatmap, drag bar, etc. -->
  </div>
  <div class="data">
    <div class="data-h">
      <span>SECTION LABEL · UPPERCASE</span>
      <span class="src">source_file.csv</span>   <!-- mono, teal -->
    </div>
    <table>
      <thead><tr><th>...</th><th class="r">...</th></tr></thead>
      <tbody>
        <tr><td class="lbl">...</td><td class="r">...</td></tr>
        <tr class="hot"><!-- highlighted row, amber left border --></tr>
      </tbody>
    </table>
  </div>
</div>
```

CSS is in `cc-app` styles — copy it verbatim. The whole point of this pattern: **no chart is ever shown without its underlying numbers.** Partners trust it because they can verify it.

When porting an existing module that's a chart-only or table-only view, you must rebuild it as a paired block. Do not skip the data table.

---

## 6. Component inventory (what to build / port)

### 6.1 Chrome (used on every authenticated page)

```html
<header class="topbar">
  <a href="/app" class="brand">
    <div class="brand-mark">SC</div>
    <div class="brand-name">Seeking<em>Chartis</em></div>
  </a>
  <nav class="topnav">
    <button class="active">DEALS <span class="caret">▾</span></button>
    <button>ANALYSIS <span class="caret">▾</span></button>
    <button>PORTFOLIO <span class="caret">▾</span></button>
    <button>MARKET <span class="caret">▾</span></button>
    <button>TOOLS <span class="caret">▾</span></button>
  </nav>
  <div class="topbar-right">
    <div class="search"><span class="ico">⌕</span><input placeholder="Search…"/><span class="kbd">⌘K</span></div>
    <a href="/login" class="signin">SIGN OUT</a>
  </div>
</header>

<div class="crumbs">
  <a href="/app">Home</a>
  <span class="sep">›</span>
  <a href="/app/portfolio">Portfolio &amp; diligence</a>
  <span class="sep">›</span>
  <span class="here">Command center</span>
</div>
```

The brand mark links home. The SIGN OUT link goes to `/login`. Nav buttons get the teal underline rule on `.active`.

### 6.2 Page header

```html
<div class="pg-head">
  <div>
    <div class="eyebrow">
      <span>PORTFOLIO &amp; DILIGENCE</span><span class="dot">·</span>
      <span>FUND&nbsp;II</span><span class="dot">·</span>
      <span class="slug">/COMMAND-CENTER</span>
    </div>
    <h1 class="title">Command center</h1>
    <p class="lede">Hold-period rollup, active diligence, screening flow — one canvas.</p>
  </div>
  <div class="meta-col">  <!-- mono, right-aligned ID/STATUS/AS-OF -->
    <div>ID <span class="dot">·</span> <span class="v">CCF-FUND2</span></div>
    <div>STATUS <span class="dot">·</span> <span class="v" style="color:var(--green)">LIVE</span></div>
    <div>AS&nbsp;OF <span class="dot">·</span> <span class="v">2026-04-15</span></div>
  </div>
</div>
```

### 6.3 KPI strip

8-cell horizontal grid, each cell: large mono value, label, delta with arrow, sparkline at the bottom. **Pair the strip with a quarterly values table on the right** (hover a cell → table updates to that KPI's quarterly history).

### 6.4 Pipeline funnel

7 stages (Sourced → Hold), each with count + EV + a stage-relative bar. **Clickable** — click filters the deals table beneath. Pair with a conversion-percentage table.

### 6.5 Deals table

Single-line rows: deal id + name, stage pill, EV, MOIC, IRR, covenant pill, drift, headline. **Click a row to set the focused deal.** Highlight the focused row with `var(--bg-tint)` and a teal `●` next to the id.

### 6.6 Focused-deal context bar

A `.deal-bar` between the deals table and downstream sections: shows focused deal name + id + stage + EV + MOIC/IRR, with toggle buttons on the right to switch between held deals. **Covenants, drag, and initiatives sections all read from this selected deal.**

### 6.7 Covenant heatmap

6 covenants × 8 quarters. Each cell colored by `safe` / `watch` / `trip` band (use `--green-soft` / `--amber-soft` / `--red-soft` backgrounds with matching strong border). Trend column on the right. **Pair with a state-counts table** showing safe/watch/trip totals per row.

### 6.8 EBITDA drag

Stacked horizontal bar (single row, 5 segments by drag component, colors from data spec) + per-component rows below with swatch + label + % + $. **Pair with a raw breakdown table** + recovery quarters table beneath. The recovery sparkline lives inside the viz column.

### 6.9 Initiative tracker

Variance-sorted rows, each with status icon (✓/!/✕), name, deal, actual, variance %, progress bar. **Pair with a variance dot-plot** (small SVG: dots on a `−30% … +30%` axis) + a playbook-signal counts table.

### 6.10 Alerts

Stacked alert cards with tone (`amber` / `red` / `blue`), icon, title, description, CTA on the right. **Pair with a triage table** (red/amber/blue counts) + a rules-fired log.

### 6.11 Deliverables

4-column manifest grid of artifacts (HTML / CSV / JSON / XLS), each with kind pill, filename, size + date. **Pair with a manifest counts table.**

---

## 7. Specific ports — file by file

### 7.1 Replace the dark home (`/diligence`)
- Delete the dark `RCM Diligence` sidebar layout for the public landing.
- Render `SeekingChartis.html` content as the new `/` route.
- The "Sign In" / "Request Access" buttons in the topbar both link to `/login`.

### 7.2 Replace `/diligence/deal/<slug>` (deal profile entry)
- Becomes the editorial **Deal Profile** screen: an editorial form card (parchment, white inner panel, single field for slug, OPEN PROFILE button is `var(--ink)` background).
- Saved-deal list below renders as a paired block: deal cards on the left, mono table of last-accessed timestamps on the right.

### 7.3 Replace the 3-statement screen (the `FINANCIALS — ST. LUKES HOSPITAL` page in the screenshot)
- Page header with eyebrow `DEAL · ST_LUKES · /3-STMT`.
- Sub-tab nav (`PROFILE | IC MEMO | BRIDGE | COMP INTEL | SCENARIOS | ML | DCF | LBO | 3-STMT | MARKET | DENIAL | RETURNS | LEVERS | WATERFALL | PLAYBOOK | TRENDS | PREDICTED | MEMO`) becomes the **`.topnav` inside the page body**, not a separate dark band — same uppercase Inter, `.14em` spacing, teal underline on `.active`.
- The income statement / balance sheet / cash flow tables go inside `.pair` blocks: the table itself in `.viz`, a **summary panel** (Σ totals, computed/estimated counts, source-file mix) in `.data`.
- Replace the current `BENCHMARK 3% NPR` / `COMPUTED` / `ESTIMATED` chip styles with editorial pills:
  ```html
  <span class="pill muted">ESTIMATED</span>
  <span class="pill teal">COMPUTED</span>
  <span class="pill amber">BENCHMARK 3%</span>
  ```
  CSS for `.pill` is already in `cc-components.jsx` styles.
- Numbers right-aligned, JetBrains Mono, tabular-nums. Negatives prefixed `−` (true minus sign), red. Positives just numeric.

### 7.4 Sidebar modules (Deal Profile, Thesis Pipeline, Checklist, Ingestion, Benchmarks, HCRIS X-Ray, Root Cause, Value Creation, Risk Workbench, Counterfactual, Compare, Market Intel, Seeking Alpha, Bankruptcy Scan, QoE Memo, Denial Predict, Deal Autopsy, Physician Attrition, Provider Economics, Management, Deal MC, Exit Timing, Reg Calendar, Covenant Stress, Bridge Audit, Bear Case, Payer Stress, IC Packet, Engagements)
- Render the sidebar with the editorial style:
  ```css
  .rail {
    width: 240px; background: var(--paper-pure); border-right: 1px solid var(--rule);
    padding: 1.5rem 0;
  }
  .rail-h { /* "RCM DILIGENCE" eyebrow */
    font-family: "Inter", sans-serif; font-size: .68rem; font-weight: 700;
    letter-spacing: .18em; text-transform: uppercase; color: var(--muted);
    padding: 0 1.5rem; margin-bottom: .75rem;
  }
  .rail a {
    display: flex; align-items: center; gap: .65rem;
    padding: .55rem 1.5rem; font-family: "Inter", sans-serif; font-size: .88rem;
    color: var(--ink); text-decoration: none; border-left: 2px solid transparent;
  }
  .rail a:hover { background: var(--bg-tint); }
  .rail a.active { border-left-color: var(--teal); background: var(--bg-tint); font-weight: 600; }
  .rail a .ico { width: 14px; height: 14px; opacity: .55; }
  ```
- **Each module page must render its content as paired viz+dataset blocks.** No more single-column dark tables.

### 7.5 The "Public data only — no PHI" banner
- Keep it. Restyle:
  ```html
  <div class="phi-banner">🛡 Public data only — no PHI permitted on this instance.</div>
  ```
  ```css
  .phi-banner {
    background: var(--green-soft); border: 1px solid var(--green); color: var(--green);
    padding: .75rem 1.5rem; font-family: "Inter", sans-serif; font-size: .82rem;
    text-align: center; margin: 1rem 2rem;
  }
  ```

### 7.6 Module cards on the home dashboard (HCRIS Peer X-Ray, Reg Calendar, Covenant Stress, Bridge Auto-Audit, Payer Stress, Bear Case Auto-Gen, Seeking Alpha)
- Render as a 4-column grid of editorial cards (matching `.deliv-grid` style):
  ```html
  <div class="module-grid">
    <a href="/app/hcris-xray" class="module-card">
      <span class="kind">HCRIS</span>
      <div class="nm">Peer X-Ray</div>
      <div class="sub">17,000 filed Medicare cost reports</div>
    </a>
    ...
  </div>
  ```
- Same border / hover / spacing as `.deliv` cards. Color the `.kind` pill teal.

### 7.7 The Pipeline Funnel + Active Alerts + Portfolio Health + Recent Deals quad on the home page
- Replace the dark four-quadrant grid with two `.pair` blocks stacked:
  - **Pipeline Funnel** + (its conversion table)
  - **Active Alerts** + (alert triage table)
- Then a third row: **Portfolio Health** as a paired covenant heatmap mini + state counts.
- "Recent deals" becomes a single editorial table at the bottom, full-width.

---

## 8. Buttons & interaction states

### 8.1 Primary CTA (dark)
```css
.cta-btn {
  background: var(--ink); color: var(--paper);
  font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase;
  padding: .8rem 1.4rem; border: none; cursor: pointer;
}
.cta-btn:hover { background: var(--teal-deep); }
```

### 8.2 Ghost / link button
```css
.ghost-btn {
  font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase; color: var(--ink);
  padding: .8rem 0; border-bottom: 1px solid var(--ink); text-decoration: none;
}
.ghost-btn:hover { color: var(--teal-deep); border-bottom-color: var(--teal-deep); }
```

### 8.3 Tab / nav (uppercase Inter)
```css
.tab {
  background: transparent; border: none; padding: .9rem 0;
  font-family: "Inter", sans-serif; font-size: .72rem; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase; color: var(--muted);
  border-bottom: 2px solid transparent;
}
.tab.active { color: var(--ink); border-bottom-color: var(--teal); }
```

### 8.4 Pills (status)
```css
.pill { display: inline-flex; align-items: center; gap: .35rem; padding: .15rem .55rem;
  font-family: "Inter", sans-serif; font-size: .68rem; font-weight: 600;
  letter-spacing: .08em; text-transform: uppercase; border-radius: 999px;
  border: 1px solid currentColor; background: transparent;
}
.pill .dot { width: 6px; height: 6px; border-radius: 999px; background: currentColor; }
.pill.green { color: var(--green); background: var(--green-soft); }
.pill.amber { color: var(--amber); background: var(--amber-soft); }
.pill.red { color: var(--red); background: var(--red-soft); }
.pill.blue { color: var(--blue); background: var(--blue-soft); }
.pill.muted { color: var(--muted); }
```

### 8.5 Inputs
```css
input { padding: .9rem 1rem; border: 1px solid var(--border); background: var(--bg);
  font-family: "Inter", sans-serif; font-size: .95rem; color: var(--ink);
  border-radius: 0; outline: none; transition: border-color .15s; }
input:focus { border-color: var(--teal); background: var(--paper-pure); }
```

---

## 9. Wiring — every button, every link

| Where | Element | Goes to |
|---|---|---|
| Landing topbar | `Sign In` | `/login` |
| Landing topbar | `Request Access` | `/login?tab=request` |
| Landing topbar | nav (Platform / Modules / Proof / Data sources) | `#anchor` smooth-scroll |
| Landing hero | `Open Command Center` | `/login` |
| Landing hero | `See how it works ↓` | `#platform` smooth-scroll |
| Landing CTA strip | `Sign In →` | `/login` |
| Landing CTA strip | `Request Access` | `/login?tab=request` |
| Login | brand mark | `/` |
| Login | `← Back to home` | `/` |
| Login form submit | (any of email or SSO) | `/app` |
| Login | `Forgot password?` | `/forgot` |
| Login | tab `Request Access` | switches form (no redirect) |
| Forgot | brand | `/` |
| Forgot | `← Back to sign in` | `/login` |
| Forgot submit | (POST recovery) | inline success card |
| Dashboard | brand mark | `/` (or stays on `/app`) |
| Dashboard | `SIGN OUT` | `/login` |
| Dashboard | nav buttons | switch view (in-page state) |
| Dashboard | pipeline stage | filter deals table |
| Dashboard | deals table row | set focused deal context |
| Dashboard | focused-deal switcher | swap context |
| Dashboard | alert CTA `Open Variance →` | `/app/deal/<slug>/variance` |
| Dashboard | alert CTA `View Source →` | `/app/deal/<slug>/ingestion` |
| Dashboard | alert CTA `Inspect Playbook →` | `/app/playbook` |
| Dashboard | deliverable card | open file (HTML preview, CSV/XLS download) |

---

## 10. What NOT to do

- ❌ No more dark navy `#0b2341` / cyan terminal palette anywhere.
- ❌ No `border-radius` > 0 except pills (`999px`).
- ❌ No `box-shadow`, no `filter: drop-shadow()`, no `backdrop-filter`.
- ❌ No emoji as functional UI (only the 🛡 in the PHI banner is allowed; replace any other emoji with serif glyphs / Inter labels).
- ❌ No icon-only buttons. Every action has a text label.
- ❌ No new accent colors. Only `--teal` and the four status hues.
- ❌ No charts without a paired dataset table.
- ❌ No `<h1>` with a bold weight. Always 400, italicize for emphasis.
- ❌ No "data slop" — every number on every page must trace to a source file in JetBrains Mono next to it.

---

## 11. Acceptance criteria

The port is done when:

1. `/`, `/login`, `/forgot`, `/app`, and at least three module pages (Deal Profile, 3-Statement, Covenant Stress) all render in editorial style with **zero remaining dark navy**.
2. Every chart on `/app` has a paired dataset table inside the same outer rule.
3. Clicking a row in the deals table updates the focused-deal context, and covenants/drag/initiatives all reflect that deal.
4. Pipeline stage clicks filter the deals table.
5. The PHI banner appears on every authenticated page.
6. Source-file paths (`portfolio.db`, `summary.csv`, `simulations.csv`, `output v1/<file>`) are visible next to every data block.
7. `Tab` order through the login form is: email → password → remember-checkbox → forgot-link → submit → SSO buttons. Submit on Enter works.
8. The brand mark links home from every page.
9. No console errors, no missing fonts, no FOUT (preconnect Google Fonts).
10. Lighthouse a11y ≥ 95 (color contrast, focus rings, labels).

---

## 12. Suggested commit sequence for Claude Code

```
1. chore(tokens): adopt editorial tokens in chartis_tokens.css
2. feat(landing): rebuild / route as SeekingChartis.html port
3. feat(auth): add /login + /forgot in editorial style
4. refactor(chrome): topbar + crumbs + sidebar shared layout component
5. feat(dashboard): /app command center with paired viz+dataset modules
6. feat(deal-profile): port to editorial; replace dark form
7. feat(3-stmt): port income / balance / cashflow as paired blocks
8. feat(modules): port covenant-stress, bridge-audit, denial-predict (3 modules per PR)
9. polish(a11y): focus rings, aria-labels, contrast pass
10. docs: update README and screenshots
```

Keep each PR scoped to one route or one shared component. Do not combine token changes with route ports.

---

## 13. Questions to ask before starting

- Which router does the deployed app use (Next.js App / Pages, Remix, plain Vite + react-router)? The handoff assumes you'll preserve it.
- Is there a server-rendered shell, or is the dark theme purely client CSS? (Determines whether tokens land in a global stylesheet or a Tailwind config.)
- Are the sidebar module routes already wired to backend endpoints, or are they currently rendering placeholder data? (Determines how aggressively to port — design-only vs. design + data wiring.)
- Are deliverable files (HTML reports in `output v1/`) served statically? If so, link them directly from the deliverables grid; otherwise wire to a download endpoint.

When in doubt, **default to matching the four reference HTML files in this design project byte-for-byte for visual fidelity, and adapt the surrounding framework code to fit.**
