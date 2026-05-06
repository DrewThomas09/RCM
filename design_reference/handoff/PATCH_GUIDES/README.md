# Patch Guides — per module kind

Every module in `MODULE_ROUTE_MAP.md` has a `kind` column. The kind tells you the layout idiom the reworked shell expects. Below are patch recipes — the minimum edits to bring an existing `rcm_mc/ui/<page>.py` in line with the new aesthetic without breaking its data plumbing.

---

## `kind: dashboard` — e.g. `home`, `pipeline`, `portfolio-analytics`

**Layout:** multi-panel grid. Each panel uses `ck_panel(body, title=, code=)`. KPIs above the fold in a 4-column strip using `ck_kpi_block`. Secondary density tables below in 6/12 or 8/12 splits.

**Recipe:**
```python
from rcm_mc.ui._chartis_kit import (
    chartis_shell, ck_panel, ck_kpi_block, ck_table, ck_section_header,
    ck_fmt_currency, ck_fmt_percent,
)

def render_home(packet):
    kpis = "".join([
        ck_kpi_block("Active deals", str(packet.deal_count), sub="3 in IC this week", code="HOM-01"),
        ck_kpi_block("Composite score", f"{packet.avg_score:.0f}", trend="+4", code="HOM-02"),
        ck_kpi_block("Corpus coverage", f"{packet.corpus_pct:.0%}", code="HOM-03"),
        ck_kpi_block("Alerts (24h)", str(packet.alert_count), trend="-2", code="HOM-04"),
    ])

    body = (
        ck_section_header("This morning", eyebrow="Partner view", code="HOM")
        + f'<div class="ck-kpi-strip">{kpis}</div>'
        + ck_panel(_pipeline_funnel(packet), title="Pipeline funnel", code="PIP-10")
        + ck_panel(_alert_feed(packet),       title="Active alerts",  code="ALT-04")
    )
    return chartis_shell(body, "Home", active_nav="home", breadcrumbs=[{"label":"Home"}])
```

**Common traps:**
- Don't re-emit your own `<style>` — the shell already loads tokens. Class names like `ck-kpi-strip` should live in `chartis_tokens.css`, not inline.
- KPI strip needs `display:grid; grid-template-columns:repeat(4,1fr); gap:var(--sc-s-5);` — add to `chartis_tokens.css` once if missing.

---

## `kind: workbench` — e.g. `analysis`, `scenario-modeler`, `ebitda-bridge`

**Layout:** six-tab console. Tab bar below breadcrumbs, each tab renders in its own `ck_panel` with `code=<TABSHORT>-NN`.

**Recipe:**
```python
TABS = [("overview","Overview"),("rcm","RCM Profile"),
        ("bridge","EBITDA Bridge"),("mc","Monte Carlo"),
        ("risk","Risk & Diligence"),("prov","Provenance")]

def render_workbench(deal_id, packet, tab="overview"):
    tab_bar = '<nav class="ck-tabs">' + "".join(
        f'<a href="/analysis/{deal_id}?tab={k}" class="{"active" if k==tab else ""}">{n}</a>'
        for k,n in TABS
    ) + "</nav>"
    body = tab_bar + _render_tab(tab, packet)
    return chartis_shell(body, f"{packet.name} · {tab}",
        active_nav="pipeline",
        breadcrumbs=[{"label":"Pipeline","href":"/pipeline"},
                     {"label":packet.name,"href":f"/deal/{deal_id}"},
                     {"label":"Analysis"}])
```

**Sliders:** debounce 300ms, POST to the bridge API, re-render the panel server-side. Keep the pattern — don't add a client framework.

---

## `kind: wizard` — e.g. `new-deal`, `onboarding`

**Layout:** stepper across the top (`ck_stepper(n=5, current=2)`), one `ck_panel` for the active step body, sticky footer with Back / Next.

Use `<progress>`-style bar: filled teal up to current step, `var(--sc-rule)` for pending. Step numerals in `var(--sc-serif)` weight 400 at 24px.

---

## `kind: long-form` — e.g. `ic-memo`, `sponsor-track-record`

**Layout:** single-column article. Max-width 68ch body, 48ch for asides. All display headings serif; body Inter Tight 16px line-height 1.65.

**Print:** add `media="print"` sheet inside `ck_panel`-less wrapper. The shell's print CSS already hides the topbar and breadcrumbs; you just need to avoid `ck-panel` shadows inside memo body.

```python
def render_ic_memo(deal_id, packet):
    body = '<article class="ck-memo">' + _memo_html(packet) + '</article>'
    return chartis_shell(body, f"IC Memo — {packet.name}",
        active_nav="pipeline", include_palette=False,
        breadcrumbs=[{"label":"Pipeline","href":"/pipeline"},
                     {"label":packet.name,"href":f"/deal/{deal_id}"},
                     {"label":"IC Memo"}])
```

Add `.ck-memo { max-width: 72ch; margin: 0 auto; }` and `.ck-memo h2 { font-family: var(--sc-serif); font-size: 28px; margin: var(--sc-s-8) 0 var(--sc-s-4); }` to `chartis_tokens.css`.

---

## `kind: compare` — e.g. `compare`

**Layout:** sticky first column, horizontal scroll for additional deals. Delta columns with arrow glyphs and signed-color text (`--sc-positive` / `--sc-negative`).

Use `ck_table` with `dense=True` and custom column defs that include a `kind="delta"` renderer (add this to `_chartis_kit.py` if not present — it should map `+X%` to positive, `-X%` to negative, `0` to dim).

---

## `kind: deal-dashboard` — e.g. `deal-dashboard`

**Layout:** header strip (name · stage · vintage · owner · composite dot · priority badge), then 2-col split: left = notes/tags/deadlines, right = stage history timeline. Sticky "Jump to…" rail with per-deal surface links.

Header strip lives outside `ck_panel` — use a dedicated `<header class="ck-deal-hero">` with navy bg, on-navy text, and the 7-column metric strip at the bottom.

---

## `kind: calendar` — e.g. `conference-roadmap`

**Layout:** 4-wide card grid, each card = conference. Month eyebrows between card groups. No `ck_panel` wrapper — cards are the panels.

---

## `kind: intake` — e.g. `quick-import`, `data-room`

**Layout:** left = form, right = preview panel (live). Form fields use native `<input>` / `<select>` styled via tokens — no custom component.

---

## `kind: hub` — e.g. `analysis-landing`, `pe-intelligence`, `diligence`

**Layout:** sectioned link grid. Each section is `ck_section_header` + a 3-wide grid of tiles. Each tile is a small `ck_panel` with the module's title, one-line purpose, route, and a teal right-arrow.

This is effectively the "Platform Index" pattern from the mockup's Home — reuse that CSS.

---

## Cheat sheet: which kinds use `ck_panel`

| Kind | Wrap content in `ck_panel`? |
|---|---|
| dashboard | Yes — one per region |
| workbench | Yes — one per tab body |
| wizard | Yes — just the active step |
| long-form | **No** — print bleeds badly |
| compare | No — table lives in a page-wide container |
| deal-dashboard | Mixed — header is bare, right/left columns are panels |
| calendar | No — cards are self-contained |
| intake | Yes — form and preview each in their own panel |
| hub | Yes — one per tile, bone-tinted |
