# CLAUDE.md — handoff for Claude Code agents

This folder is a **self-contained handoff package** for reskinning the SeekingChartis platform (`rcm_mc/ui/`) from a dark Bloomberg aesthetic to an editorial healthcare-PE look (navy + teal + parchment, Source Serif 4 + Inter Tight + JetBrains Mono).

You are Claude Code. Everything you need is in this folder.

## Read these first, in order

1. `README.md` — file index.
2. `HANDOFF_FOR_CURSOR.md` — full change spec, acceptance criteria, grep commands. (Written for Cursor, but applies to you identically.)
3. `MODULE_ROUTE_MAP.md` — 79 module surfaces with routes and source `.py` files.
4. `PATCH_GUIDES/` — per-page-family instructions keyed to the `kind` column in the route map.

## Ground rules

- **Do not change any page's signature, route, or data plumbing.** The 75+ files in `rcm_mc/ui/` keep their public API. You are replacing the shell, not rewriting pages.
- **One file does 95% of the work:** `CHARTIS_KIT_REWORK.py` → `rcm_mc/ui/_chartis_kit.py`. Drop it in first and verify the home route still renders.
- **Feature-flag everything.** `CHARTIS_UI_V2=0` must still boot the legacy shell. Don't delete the old one yet.
- **Never invent data.** If a panel needs a number that isn't already in the packet, emit a `—` dash and leave a TODO comment — don't fabricate.

## Execution loop

```bash
# 1. Land the shell + tokens
cp handoff/CHARTIS_KIT_REWORK.py rcm_mc/ui/_chartis_kit.py
mkdir -p rcm_mc/ui/static
cp handoff/chartis_tokens.css rcm_mc/ui/static/chartis_tokens.css

# 2. Boot and verify
python seekingchartis.py &
SERVER_PID=$!
sleep 2
curl -s http://localhost:8080/home > /tmp/home.html
grep -q 'chartis_tokens.css' /tmp/home.html && echo "shell OK" || echo "shell NOT LINKED"
kill $SERVER_PID

# 3. Run the hardcoded-color audit (should return hits only where you haven't swapped yet)
python handoff/verify_rework.py

# 4. Walk MODULE_ROUTE_MAP.md — hit each route, eyeball against acceptance criteria
```

## Commit hygiene

- One commit per logical slice: `chore(ui): land chartis kit v2 shell`, `fix(ui): swap hardcoded hex in payer_intelligence_page`, etc.
- Reference the module id from `MODULE_ROUTE_MAP.md` in commit bodies.
- Don't bundle unrelated refactors.

## Escalation

If you find a page whose shell call is non-standard (e.g. bypasses `chartis_shell()` and emits raw HTML), do **not** rewrite it — add it to `ESCALATIONS.md` with the file path and what's unusual. Andrew will decide whether to port it.

## What "done" looks like

All ten acceptance criteria in `HANDOFF_FOR_CURSOR.md` pass on:
- `/` (marketing)
- `/home`
- `/pipeline`
- `/deal/<id>` (pick any deal)
- `/analysis/<id>`
- `/memo/<id>` (print preview)
- `/portfolio-analytics`
- `/pe-intelligence`
- `/payer-intelligence`
- `/corpus-backtest`

If those ten pass, ship it.
