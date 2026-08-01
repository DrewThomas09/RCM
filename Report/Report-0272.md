# Report 0272: Render-Surface XSS Sweep (clean) + chart_export_toolbar hardening (commit eb20a5e)

## Scope

Third fresh post-TRIAGE sweep. Reports 0267–0268 fixed the XSS/traversal class on `ui/` core + the main server routes; this pass extended the hunt to the render surfaces those didn't cover — market_reports/, diligence/ pages, the chart kits, and **every** HTTP error path — for the two patterns that keep recurring: (a) `html.escape` into an `onclick`/`href` JS-string (wrong codec) and (b) exceptions reflected unescaped into an error page.

## Result: no new live vulnerabilities

- **Reflected exceptions.** The seven `_error_page(title, f"CCN {ccn}: {str(exc)[:200]}")` call sites (ML analysis, data room, competitive intel, EBITDA bridge, scenario, IC memo, Bayesian) are **safe**: `_error_page` html-escapes its `message` in both its 404 and 500 branches (`html.escape(message[:...])`). The codebase routes errors through this escaping helper by convention — the three raw-`_send_html` reflections were the outliers, already fixed in 0267/0268. The `_send_json({"error": str(exc)})` sites are JSON responses (not HTML), so not an XSS vector.
- **onclick JS-string interpolation.** Repo-wide, the only instance outside the already-fixed files is `cdd_chart_kit.chart_export_toolbar`. Traced every caller (excel_mapping, chart_builder, texas_infusion ×N, further_analysis, pie_chart, exhibit): all pass a **constant** or a **validated** value — `chart_builder`'s `ctype` is checked against `CHART_TYPES` (falls back to `"column"`), the texas filenames are literals, `further_analysis` uses a catalog `dataset.id`. So it is **not reachable** with attacker text today.

Recording the clean result is the point: the class is now swept across the full render surface, not just where the first bugs were found.

## Hardening (commit eb20a5e)

`chart_export_toolbar` still had the latent wrong-codec pattern — it `html.escape(quote=True)`'d `target_id`/`filename` and inlined them into `onclick="ckDlSvg('{tid}','{fn}')"`. `html.escape` in a JS-string-inside-an-attribute is the wrong codec (the browser HTML-decodes the attribute before JS parses it), so the escaping would not stop a quote breakout if a future caller ever passed partner text. Since it's a widely-used shared primitive, hardened it: the values now ride in `data-ckt`/`data-ckf` attributes (where `html.escape(quote=True)` **is** correct) and the handlers read `this.dataset.ckt`/`this.dataset.ckf` — no data ever enters the JS-string. Same pattern as the dashboard saved-templates fix (0268).

Labeled honestly in code + commit as defense-in-depth (no current caller is exploitable), not a live-bug fix.

## Evidence

- `tests/test_dataviz_kits_improve.py` +2: values appear in `data-*` attrs not the JS call; a `x')+alert(1)+('` payload can't break out of the onclick.
- Consumer suites green: chart_builder, chart_kit, further_analysis, pie_chart, texas_infusion (+continued) → 328 passed; dataviz kit suite 88 passed.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | The XSS/injection vein is now well-mined across UI + exports. Next sweep should shift target: a never-mapped *package* audit (`pe_intelligence/` 270+ modules, or `data_public/` CMS loaders — the latter is a trust boundary parsing external data), or an auth/session hardening pass. |

---

Report/Report-0272.md written.
