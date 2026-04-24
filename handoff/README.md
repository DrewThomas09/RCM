# SeekingChartis UI Rework — Handoff Package

**Start here →** [`HANDOFF_FOR_CURSOR.md`](./HANDOFF_FOR_CURSOR.md)

## Files

| File | What it is |
|---|---|
| `HANDOFF_FOR_CURSOR.md` | Prompt-style brief. Read first. Contains the exact change set, acceptance criteria, grep commands, and Cursor copy-paste prompt. |
| `CHARTIS_KIT_REWORK.py` | Drop-in replacement for `rcm_mc/ui/_chartis_kit.py`. Same public API; new palette + shell + panel chrome. |
| `chartis_tokens.css` | CSS design tokens. Land at `rcm_mc/ui/static/chartis_tokens.css` or inline into the shell. |
| `MODULE_ROUTE_MAP.md` | Table of every module surface (79) with route and source `.py` file. Walk this to verify the reskin. |
| `SeekingChartis Rework.html` | Interactive reference mockup. Five linked screens (marketing → login → home → workbench → module pages). Open in any browser. |

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
