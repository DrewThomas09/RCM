# PEdesk Design-Handoff Contract

**Why this exists.** Claude Design produces beautiful static prototypes
(HTML/CSS/JSX in `~/Desktop/*_redesign` folders). Claude Code then has to turn
them into production PEdesk pages. When Code treats a handoff as *inspiration*
and re-skins from a screenshot, the result is a half-migration: missing
sections, prototype CSS dumped into the page body as visible text, square
"cartogram" placeholders that never became real graphics. This contract makes
the handoff a **strict spec**, not a mood board.

The rule in one line: **Design produces a spec; Code produces a component map
before touching code.** No component map → no implementation.

---

## The failure modes this prevents (all observed in this repo)

1. **Raw CSS rendered as body text.** A CSS string concatenated into the HTML
   body instead of passed through `extra_css` (which the shell wraps in
   `<style>`). Symptom: `.xr-ws{display:grid;…}` printed at the top of the page.
   *(Fixed: HCRIS X-Ray landing — `_WORKSTATION_CSS` moved to `extra_css`.)*
2. **Half-migration.** The new labels appear but major prototype sections are
   missing, so the page looks sparse versus the handoff.
3. **Placeholder that never upgrades.** "Equal-size cell cartogram" square
   tiles shipped as a stand-in for a real US map and never replaced.
4. **Prototype assets shipped raw.** React/Babel/unpkg/CDN or Google-Fonts
   runtime imports leaking from the prototype into production.
5. **Tests assert presence only.** A test checks the new label exists but not
   that the *old broken structure is gone* — so regressions pass silently.

---

## Hard rules (non-negotiable)

- **CSS never goes in the body.** Page CSS is passed via `chartis_shell(...,
  extra_css=...)` (shell wraps it in `<style>`) or returned already wrapped in
  `<style>…</style>`. Never concatenate a raw CSS string into `body`.
  Scope page CSS under a page root class (e.g. `.xr`, `.hx-wrap`).
- **Replace the route renderer, not just the CSS.** Migrate the actual
  server-rendered function, preserving its real data engine calls.
- **No prototype code ships.** No React/JSX/Babel, no `unpkg`/`jsdelivr`/CDN,
  no runtime Google-Fonts import. PEdesk renders server-side HTML + the
  editorial kit only. Prototype folders stay reference-only (never committed).
- **No synthetic data.** Sample/preview values are allowed *only* when visibly
  labelled "Sample"; real reports use real engine values or honest
  "insufficient data" states.
- **Preserve behavior.** Existing click/filter/query-param/Guide behavior must
  keep working or degrade safely.
- **Untouchable:** login/auth, Caddy, systemd, deploy workflow, secrets,
  `.pedesk_prod.env`, Ollama/Tailscale, RAG runtime.

---

## The workflow for every handoff

### 1. Read the handoff as a spec
- `cat ~/Desktop/<name>_redesign/README.md` first — it names the **selected
  variant** (e.g. "B · Workstation", "Results A v2 · Headline").
- Read the `*.html`, `styles.css`, and any `*.jsx` variant files.
- Identify which production route(s) the handoff replaces.

### 2. Write the migration doc BEFORE coding
Create `docs/PEDESK_DESIGN_HANDOFF_MIGRATION_<AREA>.md` with:
- Handoff files inspected + selected variant.
- Production route(s) and the renderer function being replaced.
- **Data engine functions to preserve** (the real values must keep flowing).
- A **component map** table (below).
- A **CSS token map** (prototype tokens → PEdesk `--sc-*` / kit tokens).
- Helpers/components to create or reuse.
- Visual acceptance checklist.
- Tests required (presence **and** absence).
- Known deviations and why.

**Component map table** — one row per visible prototype section:

| Prototype section | Handoff file | Production fn/helper | Data source | Status |
|---|---|---|---|---|
| e.g. Peer band | xray-results.html | `xray_kit.xr_peer_band` | provider_xray_benchmark | implemented |

`Status ∈ {implemented, partial, missing, intentionally-unavailable (no data)}`.
**A PR is not complete while a major section is `missing`.**

### 3. Build on a reusable kit
Render through a kit module (e.g. `rcm_mc/ui/xray_kit.py`) that emits
PEdesk-native HTML/CSS. Helpers escape all data strings, preserve leading-zero
CCNs, scope CSS under the page root, and ship no external runtime scripts.

### 4. Tests must check absence, not just presence
For every migration add tests that assert:
- route returns 200;
- **new** structure markers present (kit classes, sections);
- **old/broken** structure markers ABSENT (e.g. no `equal-size cell cartogram`
  copy, no square-tile class, no raw CSS in body — strip `<style>` blocks and
  assert the CSS selectors are gone from the remainder);
- accessibility (svg `title`/`desc`/`aria-label`, focusable interactives);
- regressions: `/login` unchanged, Guide opens, no CDN/prototype scripts, no
  fake values.

### 5. Open the PR for approval
Visible-UI PRs are **approval-gated** — never auto-merge. Report: handoff files
inspected, route files changed, sections implemented vs intentionally-
unavailable, tests + results, CI/mergeability, and the standing-rule
confirmations (no fake data, no CDN, auth/deploy untouched, Guide works).

---

## Per-handoff acceptance checklist

- [ ] Production route visibly matches the screenshot.
- [ ] All major prototype sections represented (or marked intentionally-unavailable).
- [ ] Old structures removed (asserted by tests).
- [ ] CSS loads via `<style>`/`extra_css` — none visible in body.
- [ ] No external prototype dependencies (React/Babel/CDN/Fonts runtime).
- [ ] No fake/synthetic values; samples labelled "Sample".
- [ ] `/login` + auth unaffected; Guide still opens.
- [ ] Tests check **absence** of old broken structures, not just presence of new labels.

---

## How to make Design ↔ Code "talk" (the connection fix)

The translation is slow and lossy because the prototype carries *visual* intent
but not the *production contract*. Close the gap from both sides:

**Ask Claude Design (in the prototype) to emit a machine-readable spec** in the
handoff `README.md`:
- the **selected variant** name, explicitly;
- a **section inventory** (ordered list of every section block + its purpose);
- a **token table** (each color/space/font → a semantic name, not a raw hex);
- **data bindings** (which sections are real-data vs sample, and what field
  feeds each);
- **interactions** (hover/click/keyboard behavior per element);
- **degradation** (what each section shows when its data is missing).

**Then Code's job is mechanical:** map each section/token/binding to a
production helper via the migration doc, implement, and test presence+absence.
When the prototype README already answers "what are the sections, what feeds
them, and how do they degrade," Code stops guessing from pixels — which is what
produced the raw-CSS dump and the square-tile map in the first place.

See `PEDESK_VERTICAL_DATA_DEPTH_AUDIT.md` for the data-side equivalent of this
discipline.
