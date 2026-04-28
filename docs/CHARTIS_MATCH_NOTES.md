# Chartis Match Notes

Visual-fidelity observations from chartis.com paired with the
markup + tokens needed to bring the same pattern into our editorial
kit. Each section names a pattern, sketches HTML+CSS, lists the
tokens it consumes, and identifies the target pages in our app.

These sketches are the source of truth for `_chartis_kit.py`
helpers when the next BUILD step needs them.

---

## Pattern 01 — Search hero (navy panel + chevron-cut bottom)

**Where chartis uses it.** `chartis.com/insights` and similar
content-listing pages. A navy panel with a serif "Search" label,
a wide keyword input ruled by a thin teal underline, and a
distinctive chevron-cut bottom-right corner that hands off into
the paper-background results section.

**Why we need it.** No editorial pattern in our kit currently
produces a navy hero panel with a labeled keyword input. Pages
like `/library`, `/research`, `/notes` (full-text search) and
the global Cmd-K modal would all benefit; today they get either
a bare `<input>` in inline styles or the chartis_kit `.ck-search`
that lives in the topbar (240px-wide, mono, mid-color).

**Markup.**

```html
<section class="ck-search-hero">
  <div class="ck-search-hero-inner">
    <span class="ck-search-hero-label">Search</span>
    <form class="ck-search-hero-form" method="GET" action="/library">
      <input type="search" name="q"
             class="ck-search-hero-input"
             placeholder="Keyword"
             aria-label="Search Library">
      <button class="ck-search-hero-submit" type="submit"
              aria-label="Run search">
        <svg viewBox="0 0 24 24" width="18" height="18">
          <circle cx="10" cy="10" r="6" fill="none"
                  stroke="currentColor" stroke-width="1.5"/>
          <line x1="14.5" y1="14.5" x2="20" y2="20"
                stroke="currentColor" stroke-width="1.5"/>
        </svg>
      </button>
    </form>
  </div>
  <!-- chevron-cut: a teal triangle clipped to the bottom-right -->
  <span class="ck-search-hero-chevron" aria-hidden="true"></span>
</section>
```

**CSS.**

```css
.ck-search-hero {
  position: relative;
  background: var(--sc-navy);
  color: var(--sc-on-navy);
  padding: 56px 0 64px;
  margin: 0 0 var(--sc-s-9);
  overflow: hidden;
}
.ck-search-hero-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--sc-s-7);
  display: flex;
  align-items: baseline;
  gap: var(--sc-s-7);
}
.ck-search-hero-label {
  font-family: var(--sc-serif);
  font-size: 36px;
  font-weight: 400;
  font-style: italic;
  letter-spacing: -0.01em;
  color: var(--sc-on-navy);
  flex-shrink: 0;
}
.ck-search-hero-form {
  flex: 1;
  display: flex;
  align-items: center;
  border-bottom: 1px solid var(--sc-on-navy-dim);
  padding-bottom: 8px;
}
.ck-search-hero-input {
  flex: 1;
  background: transparent;
  border: 0;
  font-family: var(--sc-serif);
  font-size: 22px;
  color: var(--sc-on-navy);
  padding: 8px 0;
  outline: none;
}
.ck-search-hero-input::placeholder {
  color: var(--sc-on-navy-faint);
  font-style: italic;
}
.ck-search-hero-input:focus + .ck-search-hero-submit { color: var(--sc-teal); }
.ck-search-hero-submit {
  background: transparent;
  border: 1px solid var(--sc-on-navy-dim);
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--sc-on-navy);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.ck-search-hero-submit:hover {
  color: var(--sc-teal);
  border-color: var(--sc-teal);
}
.ck-search-hero-chevron {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 0 0 64px 64px;
  border-color: transparent transparent var(--sc-teal) transparent;
}
```

**Tokens consumed.**
- `--sc-navy` — panel background
- `--sc-on-navy`, `--sc-on-navy-dim`, `--sc-on-navy-faint` — text
- `--sc-teal` — focus ring + chevron triangle
- `--sc-serif` — italic label + input typography
- `--sc-s-7`, `--sc-s-9` — outer + section spacing

No new tokens needed.

**Target pages.**
- `/library` — primary user (deals corpus search)
- `/research` — same shape; different content type
- `/notes` (full-text search of analyst notes)
- `/search` — generic global-search landing if it surfaces
  beyond the topbar Cmd-K modal

**Helper signature.**

```python
def ck_search_hero(
    *,
    label: str = "Search",
    placeholder: str = "Keyword",
    action: str,
    name: str = "q",
    initial: str | None = None,
) -> str:
    """Navy search hero with italic-serif label + circular submit
    + teal chevron cut. Drops onto any content-listing page above
    the filter sidebar + results list."""
```

**Build sequence.**
1. Add CSS to `_chartis_kit.py` `_CSS_INLINE_FALLBACK` block.
2. Add `ck_search_hero(...)` helper alongside `ck_section_intro`.
3. Wire to `/library` first (or stub a minimal listing surface
   if `/library` doesn't render results yet).
4. Add `tests/test_search_hero.py` — render a fixture, assert
   navy background class + italic label + form action.

---

## Pattern 02 — Filter sidebar (BY TOPIC / BY TYPE eyebrow rails)

**Where chartis uses it.** `chartis.com/insights` left rail.
Eyebrow-style headers ("BY TOPIC", "BY TYPE"), checkbox rows,
"MORE ▼" expander when there are too many to list.

**Why we need it.** Required by /library + /research + every
content-listing page that shows facet-filtered results. No
existing helper.

**Markup (sketch — refine on cycle 2 build pass).**

```html
<aside class="ck-filter-rail">
  <h2 class="ck-filter-rail-title">Filter</h2>
  <section class="ck-filter-group">
    <header class="ck-filter-group-head">By topic</header>
    <ul class="ck-filter-list">
      <li><label><input type="checkbox" name="topic" value="ai">
        Artificial intelligence (AI)</label></li>
      <li><label><input type="checkbox" name="topic" value="digital">
        Digital &amp; Technology</label></li>
      <!-- ... -->
    </ul>
    <button class="ck-filter-more" type="button">More ▼</button>
  </section>
</aside>
```

**Tokens.** All existing — eyebrow uses `--sc-mono` + `--sc-teal`,
checkbox rows use `--sc-text` + `--sc-rule` separators.

**Target pages.** Same as pattern 01.

**Build deferred to cycle 2** unless cycle 1 finishes the lazy-label
sweep with budget left.

---

## Pattern 03 — N RESULTS header with chip-clear active filters

**Where chartis uses it.** Above the results list on
`chartis.com/insights`: `46 RESULTS` in serif + a row of active
filter chips (`Partnerships ✕`) with a `CLEAR ALL ✕` link in teal.

**Why we need it.** Pairs with patterns 01 + 02; without it the
filter sidebar has no acknowledgement of what's active.

**Markup (sketch).**

```html
<header class="ck-results-header">
  <div class="ck-results-count">
    <span class="num">46</span> Results
  </div>
  <div class="ck-results-chips">
    <button class="ck-chip" type="button"
            data-remove="topic" data-value="partnerships">
      Partnerships <span class="x">✕</span>
    </button>
    <a class="ck-arrow" href="/library">Clear all</a>
  </div>
</header>
```

**Build deferred to cycle 2.** Same target pages as 01 + 02.

---

## Observations log

Add a row each iteration when a chartis-match gap is observed but
not yet closed. Use this as the work queue for cycle N+1 build
steps.

| iter | observation                                                                                  | gap-vs-chartis                          | target page(s)             |
|------|----------------------------------------------------------------------------------------------|-----------------------------------------|----------------------------|
| 3    | Search hero / filter sidebar / N-RESULTS pattern absent from kit                              | sketched above (patterns 01-03)         | /library, /research, /notes |
| 3    | Marketing landing CTAs ("Open Platform") use ink-2 fill, chartis uses teal-ink + teal accent  | minor — within existing token budget    | /                          |
| 3    | /alerts severity panels use editorial chrome but no italic-serif highlight in headline       | "Where the portfolio *needs* attention" | /alerts                    |
| 3    | Data_public pages ship `<button>Run</button>` — Chartis would never                          | lazy-label sweep — cycle 1 target        | 12 data_public pages       |
