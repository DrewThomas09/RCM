# SeekingChartis UI Rework — Handoff Package

**Start here →** [`HANDOFF_FOR_CURSOR.md`](./HANDOFF_FOR_CURSOR.md)

## Files

| File | What it is |
|---|---|
| `HANDOFF_FOR_CURSOR.md` | Prompt-style brief. Read first. Contains the exact change set, acceptance criteria, grep commands, and Cursor copy-paste prompt. |
| `CHARTIS_KIT_REWORK.py` | Drop-in replacement for `rcm_mc/ui/_chartis_kit.py`. Same public API; new palette + shell + panel chrome. |
| `chartis_tokens.css` | CSS design tokens. Land at `rcm_mc/ui/static/chartis_tokens.css` or inline into the shell. |
| `MODULE_ROUTE_MAP.md` | Table of every module surface (79) with route and source `.py` file. Walk this to verify the reskin. |
| `SeekingChartis Rework (standalone).html` | Interactive reference mockup. Five linked screens (marketing → login → home → workbench → 79 module pages). Open in any browser. |
| `CLAUDE.md` | Handoff brief aimed at Claude Code agents. Ground rules + execution loop. |
| `PATCH_GUIDES/README.md` | Per-page-family recipes keyed to the `kind` column in `MODULE_ROUTE_MAP.md`. |
| `verify_rework.py` | Runnable audit: checks kit signatures, token file, tier-1 migration status, forbidden hex codes, smoke-boots /home. |
| `ACCEPTANCE_CHECKLIST.md` | Print-and-tick QA list. A page is "done" only when every row passes. |
| `MIGRATION_PLAYBOOK.md` | Wave-by-wave migration order (9 waves, 79 surfaces, ~23 hrs total work). |
| `PATCH_GUIDES/EXAMPLE_portfolio_heatmap.py` | Full before/after diff on a representative page. Copy this pattern for all `kind: dashboard` surfaces. |
| `ESCALATIONS.md` | Running log of pages that don't fit the recipe. Claude Code adds to this file rather than improvising. |

## How to use

1. Read `HANDOFF_FOR_CURSOR.md`.
2. Drop `CHARTIS_KIT_REWORK.py` + `chartis_tokens.css` into the repo.
3. Boot locally: `python seekingchartis.py` — confirm the new shell renders.
4. Walk `MODULE_ROUTE_MAP.md` row by row.

## Feature flag

The new shell is on by default. To A/B against the old one:

```bash
CHARTIS_UI_V2=0 python seekingchartis.py   # legacy dark shell
CHARTIS_UI_V2=1 python seekingchartis.py   # new editorial shell (default)
```

Remove the flag once the new shell is accepted.
