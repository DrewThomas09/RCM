# Editorial Style Port — Implementation Proposal

**Branch:** `feat/ui-rework-v3`
**Status:** PROPOSAL — awaiting approval before any implementation code lands
**Author:** Claude Code
**Date:** 2026-04-25
**Baseline:** contract tests `tests/test_ui_rework_contract.py` → **8/8 green** before any change

---

## TL;DR

The handoff bundle is internally consistent. The codebase has more existing UI infrastructure than the original rework plan assumed — there's an already-built UI-v2 dispatcher (`_chartis_kit_v2.py` + `rcm_mc/ui/chartis/` with 20 page renderers) gated by a `CHARTIS_UI_V2` env flag. **Recommendation: refresh that dispatcher with the new editorial palette rather than build `ui_v3/` from scratch.** It's faster, leverages working code, and survives the contract tests because the dispatcher is already proven to coexist with the legacy shell.

The biggest single risk in the bundle: it explicitly reroutes `/` away from the dashboard (currently the partner home) toward a public marketing page. That route change alone could break Lighthouse-style monitoring or partner muscle memory. **Phase 1 should NOT change `/` — only add `/login`, `/forgot`, and `/app` as new opt-in routes under `?ui=v3`.**

---

## Step 1 — Files in the bundle

### One-line summaries

| File | Summary |
|---|---|
| `README.md` | Bundle overview + how to use it. Says "if a ported module has a chart but no paired data table, it isn't done." |
| `EDITORIAL_STYLE_PORT.md` | **The spec.** 13 sections: tokens (§3), type (§4), the signature paired-viz-dataset pattern (§5), component inventory (§6), file-by-file ports (§7), button/link wiring (§9), no-go list (§10), acceptance criteria (§11), suggested commit sequence (§12) |
| `tokens/chartis_tokens.css` | 23 CSS custom properties across two `:root` blocks — surfaces, rules, ink, accent (one teal `#1F7A75`), 4-color status palette. Spec § 3 ports them verbatim |
| `reference/01-landing.html` | Marketing page (`/`). Hero with italicized phrase, value-prop trio, paired funnel + dataset, proof grid, module catalog, dark CTA strip. ~660 lines |
| `reference/02-login.html` | Sign-in / Request Access split layout, last-session teaser card, SSO row. Tab-based form switching. ~360 lines |
| `reference/03-forgot.html` | Single-card recovery form. Minimal token subset (11). ~100 lines |
| `reference/04-command-center.html` | Authenticated dashboard at `/app`. Topbar + crumbs + page header + KPI strip + paired viz-dataset blocks for pipeline / deals / covenant heatmap / EBITDA drag / initiatives / alerts / deliverables. ~650 lines, React app mounts into `#root` |
| `reference/cc-app.jsx` | 17 React components: `App`, `Topbar`, `Crumbs`, `PageHead`, `WhatBlock`, `KPIStrip`, `MetricCatalog`, `SelectedDealBar`, `Pipeline`, `DealsTable`, `CovenantSection`, `DragSection`, `InitiativeSection`, `VarianceDot`, `AlertSection`, `DelivSection`, `Footer`. Selected-deal context via React `createContext`. **Reference architecture only — we don't ship React.** |
| `reference/cc-components.jsx` | 4 atoms: `Sparkline`, `CovenantPill`, `StagePill`, `NumberMaybe` with format types (`moic`, `pct`, `ev`, `drift`) |
| `reference/cc-data.jsx` | Mock dataset: 8 KPIs, 7-stage funnel, 3 deals, 6×8 covenant grid, 6 initiatives, alerts, deliverables. Useful for matching number formats + JSON shape |

### Step 2 — Safety-rail re-read

Re-confirmed:
- `docs/UI_REWORK_PLAN.md` — 5 phases, recommends `RCM_MC_UI_VERSION=v3` env + `?ui=v3` query, gates Phase 1 to a single page rebuild, requires contract tests at every commit, Phase 4 cutover, Phase 5 cleanup
- `tests/test_ui_rework_contract.py` — 8 tests ⇒ critical pages resolve, `/health` returns body `"ok"`, auth round-trip, packet has 10 load-bearing fields, migrations apply, OpenAPI > 30 paths, JSON endpoints stay JSON, a `shell()`-style entry point exists

**Contract test baseline: 8/8 PASS** (run 2026-04-25)

```
tests/test_ui_rework_contract.py::TestUIReworkContract::test_all_migrations_applied PASSED
tests/test_ui_rework_contract.py::TestUIReworkContract::test_authenticated_data_endpoint_returns_json PASSED
tests/test_ui_rework_contract.py::TestUIReworkContract::test_critical_pages_resolve PASSED
tests/test_ui_rework_contract.py::TestUIReworkContract::test_health_endpoints_return_ok_body PASSED
tests/test_ui_rework_contract.py::TestUIReworkContract::test_login_round_trip PASSED
tests/test_ui_rework_contract.py::TestUIReworkContract::test_openapi_spec_loads PASSED
tests/test_ui_rework_contract.py::TestUIReworkContract::test_packet_dataclass_load_bearing_fields PASSED
tests/test_ui_rework_contract.py::TestUIReworkContract::test_ui_kit_shell_function_exists PASSED
============================== 8 passed in 1.68s ===============================
```

---

## Step 3 — Inventory + gap analysis

### 3a. Are tokens consistent inside the handoff?

`tokens/chartis_tokens.css` defines the canonical 23. Token coverage by file:

| Token | spec | tokens.css | 01-landing | 02-login | 03-forgot | 04-cmd-center |
|---|:-:|:-:|:-:|:-:|:-:|:-:|
| `--bg`, `--paper-pure`, `--border`, `--rule`, `--ink`, `--muted`, `--faint`, `--teal`, `--teal-soft`, `--teal-deep`, `--green` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `--bg-alt`, `--bg-tint`, `--paper`, `--ink-2`, `--amber`, `--red` | ✓ | ✓ | ✓ | partial | — | ✓ |
| `--border-strong` | ✓ | ✓ | — | — | — | ✓ |
| `--green-soft`, `--amber-soft`, `--red-soft`, `--blue`, `--blue-soft` | ✓ | ✓ | — | — | — | ✓ |

**Mismatches to flag:**

1. **Two extra tokens in `04-command-center.html` not in `chartis_tokens.css`:**
   - `--navy: #0F2A47` (a deeper navy than `--ink`)
   - `--link: #155752` (= `--teal-deep`, just an alias)

   **Decision needed.** Either drop `--navy` (only used in one place — the deeper navy can come from `--ink` ≈ `#0F1C2E` since the visual delta is 6 hex points) and alias `--link: var(--teal-deep)`. Or add both to `chartis_tokens.css` as canonical. **Recommendation: alias `--link`, drop `--navy` and replace with `--ink-2: #1A2840` which already exists in the canonical set.**

2. **No mismatches between `tokens/chartis_tokens.css` and the union of all four HTML files** — every value where they overlap matches byte-for-byte.

3. **The 4 HTML files don't all carry every token** — that's by design (login doesn't need covenant heatmap colors). Not a bug.

### 3b. Handoff tokens vs existing codebase tokens — major conflict

The codebase has **two existing token sets** that this rework will replace or supersede:

#### Token set A: `rcm_mc/ui/static/chartis_tokens.css` (the OLD reverted reskin)

Uses `--sc-*` namespace and the **prior reskin's palette** that was reverted in commit `d8bfac4`:

```
--sc-navy:      #0b2341     ← dark navy as primary (REVERTED)
--sc-teal:      #2fb3ad     ← vibrant teal (REVERTED)
--sc-parchment: #f5f1ea     ← warmer parchment (REVERTED)
```

The new spec is explicit at §0/§10: "The dark navy + cyan terminal look is being retired." The new tokens are different values:

```
--ink:   #0F1C2E    (← was navy primary; now near-black for TEXT only)
--teal:  #1F7A75    (← deeper, more muted than #2fb3ad)
--bg:    #F2EDE3    (← lighter parchment than #f5f1ea)
```

**Conclusion:** the existing `static/chartis_tokens.css` is dead code from the reverted reskin. It must NOT be used by v3. Phase 1 leaves it alone (it's referenced via `--sc-*` selectors in legacy templates); Phase 5 cleanup deletes it.

#### Token set B: `var(--accent)` references in `server.py` and elsewhere

`server.py` has **dozens** of `var(--accent)` references (line 247, 374, 454, 561, 616, 766, 895, 941…). These are wired against a different naming scheme (`--accent`, `--card`, `--accent-soft`) defined in the legacy `_ui_kit` module's BASE_CSS / `_chartis_kit_legacy.py`.

**This is the load-bearing connection.** If v3 templates use `var(--teal)` directly, `server.py`-rendered fragments that bleed into v3 pages will look wrong (teal-deep backgrounds where they expect Chartis blue). **Bridge needed:**

```css
/* In ui_v3 base CSS: alias the legacy names so server.py fragments still render */
:root {
  --accent:       var(--teal-deep);
  --accent-soft:  var(--teal-soft);
  --card:         var(--paper-pure);
}
```

Add this to the v3 page-shell CSS so injected legacy fragments don't fight the new palette.

### 3c. Existing rendering layer + React → stdlib translation

**Confirmed: codebase is Python `http.server` + string-concat HTML, not React.** Every page returns through `chartis_shell(body, title, ...)` from `rcm_mc/ui/_chartis_kit.py`, which is a dispatcher that picks between:

- `_chartis_kit_legacy.py` — current dark Bloomberg shell (default)
- `_chartis_kit_v2.py` — *prior reverted* editorial reskin (palette is `#0b2341` navy / `#2fb3ad` teal — the OLD values, NOT the new spec's)

There's also a `rcm_mc/ui/chartis/` subpackage with 20 page renderers that already use the v2 dispatcher: `marketing_page.py`, `home_page.py`, `deal_screening_page.py`, `pe_intelligence_hub_page.py`, etc.

#### Translation table — React component → server-rendered Python

| React component (`cc-app.jsx`) | Stdlib equivalent | Notes |
|---|---|---|
| `<App>` with `DealCtx.Provider` | `def render_command_center(packet, selected_deal_id) -> str:` — selected-deal carried as URL query `?deal=<id>` | No client-side state. Selecting a deal does a server round-trip with the deal id in the URL. Slower but trivially auditable. |
| `<Topbar>`, `<Crumbs>`, `<PageHead>` | `chartis_shell(body, title, ...)` already wraps these | Refresh `_chartis_kit_v2.py`'s shell to render the new editorial topbar markup |
| `<KPIStrip>` + paired hover-table | `def render_kpi_strip(kpis)` returns the 8-cell strip + a paired table that's pre-rendered for *every* KPI; CSS `:has(.kpi-cell:hover)` flips visibility | No JS round-trip; HTML/CSS-only hover state |
| `<Pipeline>` clickable stages | `<a href="?stage=Hold">` per stage | Filtering happens server-side on next request |
| `<DealsTable>` row-click → focus | `<a href="?deal=ccf_2026">` per row | Same pattern |
| `<CovenantSection>`, `<DragSection>`, `<InitiativeSection>` | One Python helper per section; each takes a packet and returns the paired `<div class="pair">` block | Pure functions over the existing `DealAnalysisPacket` |
| `<Sparkline>` | Already exists as `rcm_mc/ui/_helpers.py` SVG sparkline | Confirmed compatible |
| `<CovenantPill>`, `<StagePill>`, `<NumberMaybe>` | One module: `rcm_mc/ui/chartis/_atoms.py` with `pill(text, tone)`, `number(v, format, tone)` | These are already partly built |
| `<VarianceDot>` SVG | Pure-Python SVG generator (200 chars) | Trivial |

The signature `.pair` block (§5 of spec) becomes one function:

```python
def pair_block(viz_html: str, label: str, source: str,
               data_table: str) -> str:
    return f'''<div class="pair">
      <div class="viz">{viz_html}</div>
      <div class="data">
        <div class="data-h">
          <span>{html.escape(label)}</span>
          <span class="src">{html.escape(source)}</span>
        </div>
        {data_table}
      </div>
    </div>'''
```

Every analytical section uses it. **Contract: no chart without `pair_block`.** This becomes a new contract test in Phase 1.

---

## Step 4 — Architecture proposal

### 4a. File layout — refresh the existing v2 dispatcher; do NOT build `ui_v3/`

**Choice:** I'm proposing a deviation from `UI_REWORK_PLAN.md` based on what I found. The plan said "build `ui_v3/` package alongside `ui/`". But the codebase already has the equivalent: `_chartis_kit_v2.py` + `rcm_mc/ui/chartis/`. They're gated behind `CHARTIS_UI_V2=1`. They were built for the prior (reverted) reskin and never deleted.

**Two options:**

| | Option A: Refresh existing v2 | Option B: Build `ui_v3/` from scratch |
|---|---|---|
| Setup cost | Update `_chartis_kit_v2.py`'s `P` palette + CSS to new tokens. ~1 day | Build new package, new dispatcher, new pages. ~1 week |
| Page renderers reused | 20 already-written pages in `rcm_mc/ui/chartis/` | None — start from zero |
| Risk of palette confusion | High — the file is named `_chartis_kit_v2.py` but holds OLD reskin's palette. Easy to misread. **Mitigation:** rename to `_chartis_kit_editorial.py`, update flag to `CHARTIS_UI_EDITORIAL=1` | Low — fresh names |
| Conflicts with prior reverted code | Forces deliberate replacement. Cleanup is part of the work | Leaves dead code at `_chartis_kit_v2.py` indefinitely |
| Matches `UI_REWORK_PLAN.md` | No — deviation requires user approval | Yes |

**Recommendation: Option A.** Reasons:
1. 20 page renderers in `rcm_mc/ui/chartis/` already use the dispatcher pattern; rebuilding them in `ui_v3/` is duplicate work
2. The dispatcher pattern is already proven against contract tests
3. The "dead code" at `_chartis_kit_v2.py` is a hazard sitting in the repo regardless — better to overwrite it deliberately than leave it
4. The flag mechanism already exists (`UI_V2_ENABLED = os.environ.get("CHARTIS_UI_V2", "0") != "0"`)

**File-rename plan (under Option A):**

```
rcm_mc/ui/
├── _chartis_kit.py             ← dispatcher; updated to read CHARTIS_UI_V2 OR ?ui=v3 query
├── _chartis_kit_legacy.py      ← dark shell, unchanged
├── _chartis_kit_editorial.py   ← REPLACES _chartis_kit_v2.py with new editorial palette + shell
├── chartis/
│   ├── _atoms.py               ← pill, number, sparkline, pair_block (NEW)
│   ├── _shell_editorial.py     ← topbar/crumbs/pg-head from §6.1–6.2 of spec (NEW)
│   ├── marketing_page.py       ← UPDATE to match 01-landing.html
│   ├── login_page.py           ← NEW (matches 02-login.html)
│   ├── forgot_page.py          ← NEW (matches 03-forgot.html)
│   ├── command_center_page.py  ← NEW (matches 04-command-center.html, replaces home_page.py)
│   └── ...                     ← existing 17 pages port incrementally in later phases
└── static/
    ├── chartis_editorial.css   ← NEW. Lifts §3 tokens + base typography from spec
    └── chartis_tokens.css      ← OLD reskin's tokens; unused after Phase 1; deleted in Phase 5
```

### 4b. Feature-flag detection

The plan calls for two flags: env (`RCM_MC_UI_VERSION=v3`) and query (`?ui=v3`). The existing dispatcher reads only the env flag. **Proposal: extend to read both.**

Where in the request lifecycle:

```
RCMHandler.do_GET
   └── parses query params
   └── stashes self._ui_choice in request scope
   └── routes to _route_<page>
       └── calls render_<page>(...)
           └── calls chartis_shell(body, title, ui_choice=self._ui_choice)
               └── dispatcher inspects ui_choice → picks editorial vs legacy renderer
```

Implementation (one ~10-line patch):

```python
# In server.py, do_GET / do_POST entry:
qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
ui_q = (qs.get("ui") or [""])[0].lower()
ui_e = (os.environ.get("RCM_MC_UI_VERSION", "")
        or os.environ.get("CHARTIS_UI_V2", "")).lower()
self._ui_choice = "editorial" if ui_q in ("v3", "editorial") or ui_e in ("v3", "editorial", "1", "true") else "legacy"
```

Then `chartis_shell` accepts an explicit `ui_choice` kwarg defaulting to env. **This means `?ui=v3` works per-request without env config — exactly what Claude Design needs for previewing.**

### 4c. Phase 1 scope (proposed — smaller than the spec's §12 sequence)

The spec suggests 10-commit sequence ending at "polish + docs". For Phase 1 of THIS branch, I propose the smallest possible scope that proves the architecture works end-to-end:

**Phase 1 — Foundation only (target: 1 working day, 1 PR-able commit set)**

1. `chore(tokens): adopt editorial tokens` — write `static/chartis_editorial.css` with the §3 token block, type imports (§4), and core utility classes (`.sans`, `.mono`, `.num`, `.micro`, `.pill`, `.cta-btn`, `.ghost-btn`, `.tab`)
2. `feat(shell): editorial topbar + page-head + crumbs` — `_chartis_kit_editorial.py` with the new `chartis_shell` rendering, the `var(--accent)` legacy-bridge, and the `.pair` helper
3. `feat(flag): RCM_MC_UI_VERSION env + ?ui=v3 query` — extend the dispatcher; default OFF
4. `feat(forgot): /forgot route` — single editorial card form (smallest of the four reference pages, 100 lines, no data dependencies — perfect proof-of-architecture)
5. Add `tests/test_ui_rework_contract.py::test_pair_pattern_contract` — verify any HTML returned from a v3 page that contains `<svg` or `<canvas` also contains a `<table` within the same `.pair` block
6. Update `tests/test_ui_rework_contract.py::CRITICAL_PAGES` to include `/forgot`

**Exit criteria for Phase 1:**
- Contract tests 8/8 (or 9/9 with the new pair test) green
- `?ui=v3&path=/forgot` renders the editorial recovery card
- `?ui=v2&path=/forgot` returns 404 (legacy doesn't have the route — that's intentional; v3 introduces it)
- Visual diff vs `reference/03-forgot.html`: same brand, same fonts, same field shape, same submit button

**Phase 2 (next PR):** `/login`, then `/app`. Each its own commit set. Both gated behind `?ui=v3`.

**Phase 3+:** the existing 17 pages in `rcm_mc/ui/chartis/` get refreshed one at a time. Each refresh:
- Update palette references (`P` dict aliases)
- Rebuild any chart-only or table-only sections as `.pair` blocks per §5
- Add a contract test asserting the page passes the pair-pattern check

### 4d. CSS serving — static asset path

**Proposal: serve `chartis_editorial.css` as a static asset under `/static/v3/chartis.css`**, NOT inlined.

Reasons:
- Browser caches it
- Single source of truth — every page links the same href
- No string-concat overhead per render

Implementation: extend the existing static handler in `server.py` (which already serves `/static/...` files) to recognize `/static/v3/chartis.css` as `RCM_MC/rcm_mc/ui/static/chartis_editorial.css`. ~5-line change.

Page templates: `<link rel="stylesheet" href="/static/v3/chartis.css">` in `<head>`.

For preview-only `?ui=v3` toggling, the same stylesheet loads — no issue. The flag affects which Python renderer runs, not which CSS is served.

---

## Step 5 — Conflicts, ambiguities, and things I won't decide for you

### 5a. Conflicts between handoff and existing data model

| Conflict | Source | Resolution required from user |
|---|---|---|
| `04-command-center.html` introduces `--navy` and `--link` tokens not in canonical `chartis_tokens.css` | tokens diff | **My recommendation:** drop `--navy`, alias `--link: var(--teal-deep)`. Confirm? |
| Spec §2 reroutes `/` from current dashboard → marketing landing | `EDITORIAL_STYLE_PORT.md:53-65` | **Risk:** breaks partner muscle memory + any external monitor that expected JSON or auth challenge at `/`. **My recommendation:** Phase 1 leaves `/` alone; introduce marketing only at `/marketing` until Phase 4 cutover. The existing `RCM_MC_HOMEPAGE=dashboard` env (already in server.py:1948) handles this gracefully |
| Spec §7.2 says `/diligence/deal/<slug>` becomes the "Deal Profile" entry — but our codebase has `/deal/<slug>` (no `/diligence/` prefix) for that surface | `server.py` route inventory | **My recommendation:** Phase 3+ uses our existing `/deal/<slug>` paths under `?ui=v3`. The spec's `/app/deal/<slug>/...` URLs become **aliases** that 302 to the canonical paths, not replacements. Confirm? |
| Spec §6.1 "SIGN OUT" links to `/login`, but the existing `/api/logout` does the actual session destroy | `server.py` route inventory | **My recommendation:** v3 SIGN OUT button posts to `/api/logout` (which already 303s back to `/login`). Spec's wiring works as-is |
| `cc-data.jsx` shows mock numbers that don't necessarily match what `DealAnalysisPacket` actually exposes | `cc-data.jsx` is mock data | **No real conflict** — the data layer wins per the user's hard rule. v3 page renderers read from packet, not mock. Number formats stay (`2.69x`, `21.9%`, `−28.9%`) |

### 5b. Ambiguities — design decisions you need to make, not me

These are places the spec is silent and I'd otherwise be guessing:

1. **Sidebar navigation in `/app`** — §7.4 says the existing 29-item module list "becomes the left-rail navigation inside `/app`". But cc-app.jsx's command-center has NO sidebar — it has horizontal `topnav` only. **Question: does the editorial `/app` show the 29-module sidebar at left, OR collapse them into the topnav dropdowns?** Recommend topnav dropdowns to match the reference HTML; sidebar is too dense for editorial style.
2. **Theme toggle** — does v3 keep a dark-mode option, or is editorial parchment the only theme? Spec §10 forbids dark navy, suggesting no. **Question: confirm dark mode is dropped in v3?**
3. **`var(--accent)` in `server.py`** — there are 80+ usages. Two options: (a) v3 base CSS aliases `--accent: var(--teal-deep)` so legacy fragments tint correctly; (b) we sweep server.py and replace all `var(--accent)` with `var(--teal-deep)` in a separate refactor commit. **Recommend (a)** — sweeps are risky; aliases are reversible.
4. **The 4 module-card pills** in `01-landing.html` (HCRIS / Reg Calendar / Covenant / etc.) — do they link to live module pages, or are they marketing-only? **Recommend:** marketing-only on `/`; the actual module pages live in `/app/...` and are auth-gated.
5. **JetBrains Mono number formatting in legacy pages** — the spec demands tabular nums everywhere. Today, only the workbench uses tabular nums (the rest use proportional). **Question: scope of this rework — just v3 pages, or also retrofit legacy v2 with tabular nums via shared CSS?** Recommend: v3 pages only.

### 5c. What would force a contract-test failure if I implemented naively

These are tripwires I see in the spec; my implementation plan dodges them, but you should know they exist:

- **§7.5 PHI banner** — proposes `<div class="phi-banner">…</div>` injected at top of every authenticated page. The current PHI banner ships through `_chartis_kit_legacy.shell()`. If v3 shell forgets to render it, contract test passes but the prod-deploy check at AZURE_DEPLOY.md item #4 (`RCM_MC_PHI_MODE=disallowed` shows banner) silently breaks. **Mitigation:** add a contract test that asserts `class="phi-banner"` appears in any authenticated v3 page.
- **DealAnalysisPacket field renames** — the spec references "Σ totals, computed/estimated counts, source-file mix" in §7.3 sub-panel. If implementing this requires a new packet field, that's a data-layer change (forbidden per user's hard rule) — must be derived from existing fields. **Mitigation:** map every spec data demand onto existing packet fields before implementation; flag any that can't.
- **Health endpoint contract** — `/health` and `/healthz` must keep returning body `"ok"` (Docker depends on this). The editorial shell would never reach those routes, but if anyone adds an "editorial health page" by mistake at `/health` it would fail the deploy. **Mitigation:** existing contract test catches it.

---

## Hard-rule compliance check

Per the user's instructions:

✅ **All work stays on `feat/ui-rework-v3`.** No commits to `main`. Branch already pushed; no merges proposed.

✅ **Contract tests stay 8/8 green at every commit.** Phase 1 plan adds 1 new test (pair-pattern), keeps the 8 existing ones unchanged. Every commit runs the suite locally before push.

✅ **Data model wins over handoff.** Sections 5a + 5c flag every place the bundle wants something the data model doesn't expose; every flag has a "do less, ask user" recommendation rather than a silent compromise.

✅ **No fetching from `api.anthropic.com`.** Bundle is on disk per Step 1.

---

## What I need from you to start Phase 1

1. **Architecture: Option A (refresh existing v2 dispatcher) or Option B (fresh `ui_v3/`)?** I recommend A.
2. **`/` route policy: leave it alone in Phase 1, or reroute to marketing immediately?** I recommend leaving it alone.
3. **`--navy` + `--link` extras: drop or canonicalize?** I recommend drop+alias.
4. **`var(--accent)` strategy: alias bridge in v3 base CSS, or sweep server.py?** I recommend alias bridge.
5. **`/app` sidebar vs topnav-only?** Recommend topnav-only to match `04-command-center.html`.
6. **Dark mode in v3: kept or dropped?** Recommend dropped.
7. **Phase 1 scope: just `/forgot` as the proof-of-architecture, then `/login`+`/app` in Phase 2? Or all four reference pages in Phase 1?** I recommend `/forgot` only for Phase 1 — it's 100 lines, no data deps, perfect for proving the dispatcher + token + pair-pattern contract.

Answer those seven, and I can produce the next, smaller proposal — the actual Phase 1 PR plan with file diffs and the new contract test — without writing any implementation code yet.

---

## Phases not in this proposal

This proposal covers Phase 1 only. Phases 2–5 follow the same shape (per-page port + per-page contract test + commit). Each phase will get its own short proposal so you can redirect at any point.

When in doubt about the visual rendering, the reference HTML files are byte-for-byte ground truth.
