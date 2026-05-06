# SeekingChartis design handoff

This folder is the **complete handoff bundle** for the editorial-style port to the `RCM_MC` repository. Drop it in at `RCM_MC/docs/design-handoff/`.

## Contents

| Path | What it is |
|---|---|
| `EDITORIAL_STYLE_PORT.md` | **The spec.** Single source of truth. Read this first. |
| `tokens/chartis_tokens.css` | Canonical CSS custom properties — the `:root` block to lift verbatim |
| `reference/01-landing.html` | Marketing landing page (`/`) — visual ground truth |
| `reference/02-login.html` | Sign-in / Request Access (`/login`) |
| `reference/03-forgot.html` | Password recovery (`/forgot`) |
| `reference/04-command-center.html` | Authenticated dashboard (`/app`) — the canonical screen |
| `reference/cc-app.jsx` | Dashboard React app (loaded by `04-command-center.html`) |
| `reference/cc-components.jsx` | Dashboard component library — paired viz+dataset blocks, KPI strip, funnel, covenant heatmap, etc. |
| `reference/cc-data.jsx` | Mock data feeding the dashboard — useful for matching number formats |

## How to use this bundle

1. **Read `EDITORIAL_STYLE_PORT.md`.** It has 13 sections covering tokens, type, the signature paired-viz-dataset pattern, file-by-file ports, button/link wiring, and acceptance criteria.
2. **Diff `tokens/chartis_tokens.css` against the `:root` blocks in the four reference HTML files.** They match by design — if your port drifts, the tokens file is the authority.
3. **Treat the `reference/` HTML files as visual ground truth, not text-to-copy.** The question to answer when porting any screen: *"Does my v3 page render to look like this?"* — not *"did I include this exact div?"*
4. **The CSS lives inline in each HTML file's `<style>` block.** There are no separate stylesheets. Lift component CSS into your own stylesheets per §3 of the spec.

## What is NOT in this bundle

- No tarball, no remote URL, no `api.anthropic.com` endpoint. The earlier mention of one was a hallucination — disregard it.
- No `tokens/` or `components/` subdirectories beyond what's listed above. Component CSS is inline in the reference HTML.
- No backend / data wiring — this bundle is design only. The repo's existing data layer stays.

## The flow

```
01-landing.html  →  02-login.html  →  04-command-center.html
                       ↘ 03-forgot.html
```

Routes in the deployed app per §2 of the spec:

| Route | Reference file |
|---|---|
| `/` | `01-landing.html` |
| `/login` | `02-login.html` |
| `/forgot` | `03-forgot.html` |
| `/app` | `04-command-center.html` |

## The signature pattern (don't skip this)

Every analytical section in the dashboard renders as a **`.pair`** block: visualization on the left, raw dataset table on the right, both inside one outer rule. **No chart is ever shown without its underlying numbers.** See §5 of the spec and `cc-components.jsx` for the implementation.

If a ported module has a chart but no paired data table, it isn't done.
