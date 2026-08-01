# Report 0268: Trust-Boundary Sweep — 4 more XSS + 1 path-traversal fixed (commit a8b5279)

## Scope

First post-TRIAGE fresh audit sweep. The two HIGH bugs in Report-0267 (unvalidated partner `deal_id` reaching a filesystem path and an HTML sink) pointed at a *class*, not two isolated defects. This iteration hunted that class systematically: a 4-lens parallel sweep (filesystem paths / HTML-XSS / SQL / other-injection) surfaced 7 candidates, each then adversarially verified (agents prompted to *refute*). 6 confirmed, 1 refuted, 0 uncertain. All 6 fixed.

Sister reports: 0267 (the two HIGH bugs that motivated this sweep), 0212 (XSS/trust-boundary origin), 0261 (sqlite3.connect census).

## Confirmed + fixed

| Sev | Site | Bug | Fix |
|---|---|---|---|
| HIGH | `ui/dashboard_page.py:1818` | "Your templates" onclick reflected a partner-supplied saved-analysis **route** into a `window.location='…'` JS-string via `html.escape` — wrong codec (browser HTML-decodes the attribute before JS parses it, so an escaped quote reverts and breaks out). Stored/cross-user: templates list unfiltered for every viewer. | Carry the route in a `data-target="{html.escape}"` attribute (correct codec there) and read `this.dataset.target` in the handler. |
| HIGH | `ui/analysis_workbench.py:1428` | Delete button interpolated partner `deal_id` into an `onclick` `fetch('/api/deals/{deal_id}')` JS-string via `html.escape` — same wrong-codec class. | New `_seg()` helper percent-encodes deal_id path segments (`quote(…, safe='')`); applied to all deal-id URLs in the header (fixes the XSS and latent URL malformation on the neighboring hrefs). |
| HIGH | `server.py:7178` (IC-memo route) | `except: return _send_html(f"…{exc}")` reflected the raw exception, which embeds the partner `deal_id` path segment, unescaped. | Escape the reflected type + message. |
| HIGH | `server.py:7313` (diligence-synthesis route) | Twin of the above. | Escape the reflected type + message. |
| MEDIUM | `server.py:20950` (`/api/jobs/run`) | Partner-supplied `outdir` written unvalidated — the code's own comment promised a traversal guard that was never implemented; `outdir` flowed into `run_main(['--outdir', outdir])` which mkdir's it and writes files. | Reject `..`/null bytes always; confine `outdir` under `self.config.outdir` when the server has an output root (mirrors the existing `_route_output` / jobs-progress base+os.sep idiom). |
| REFUTED | (1 SQL candidate) | — | verifier found parameterised / not user-reachable. |

## A latent bug this fixed in my own Report-0267 work

The screening-route exception-escape I added in 0267 used `html.escape`, but `html` is a **function-local** inside `_do_get_inner` (`html = render_*(...)` is assigned further down the method, making `html` local for the whole function). Referencing `html.escape` there raises `UnboundLocalError` — the fix would have thrown instead of rendering the escaped 500. The codebase already documents this shadow (comment near the workspace badge, and `import html as _html` at server.py:3572). All three reflected-exception fixes now use a local `import html as _html`. Reproduced the scope failure in isolation before fixing.

This is exactly why the sweep verifies and tests: a security fix that raises on the error path is not a fix. The new `test_screening.py` reflected-exc assertion and the two new server-route paths exercise the corrected code.

## Evidence

- New tests: `test_analysis_workbench.py` (deal_id can't break out of the Delete onclick), `test_dashboard_page.py` (saved-template route can't break out; payload passes `save_template`'s local-path validation yet is neutralized), `test_job_queue.py` (`..` outdir → 400).
- Full edited-surface run: `test_analysis_workbench` + `test_dashboard_page` + `test_job_queue` + `test_saved_analyses` + `test_screening` + `test_export_path_traversal` → **73 passed, 1 skipped**.

## Carry-forward notes (LOW, not queue work)

| Note | Item |
|---|---|
| MR1071 | `deals/deal_sim_inputs.py`: `set_inputs` stores `actual_path`/`benchmark_path` unvalidated and `next_outdir` permits an absolute `outdir_base`. Reachable via `/api/deals/<id>/rerun`. Needs an allowlist-inputs-dir design decision, not a one-line fix — deferred deliberately. |
| (root) | The durable fix for the whole deal_id class is to validate deal_id to a safe slug at the **ingestion boundary** (import routes / `upsert_deal`) so no downstream sink depends on correct escaping. Larger blast radius (existing deal_ids may contain arbitrary chars); the per-sink fixes here + in 0267 are the safe immediate close. |

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| next | Continue fresh sweeps: the SQL/CSV-injection lens over CSV exporters, the `pe_intelligence/` and `data_public/` never-mapped packages, or the deal_id ingestion-boundary root fix as a deliberate hardening PR. |

---

Report/Report-0268.md written.
