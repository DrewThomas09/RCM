# Standard Page Actions (Copy Share Link, Print, Shortcuts, Quick Jump, Glossary, Methodology, Back to Top)

How the seven standard action affordances on every PEdesk page work, so the
Guide can answer "how do I share this view", "can I print this", "how do I
look up that metric", "what's the keyboard shortcut for X".

## The seven standard actions

Every page on PEdesk renders a uniform action row near the bottom of the body
content via the shared `ck_page_actions()` helper (defined in
`rcm_mc/ui/_chartis_kit.py`). The row contains six inline pill buttons plus
one floating button:

1. **Copy share link** — Puts the current URL on the clipboard with every
   filter, sort, layer, scope, refine, hide, compare, and limit param
   server-encoded into the query string. A teammate clicking the link gets
   the exact same view. Use this any time you say "look at this".
2. **Print this view** — Opens the browser print dialog. The action row
   and the floating back-to-top button hide automatically via
   `@media print` so the printed output is partner-presentable. Many
   editorial panels already carry `@media print` rules in
   `chartis_tokens.css` so chrome is suppressed and panels avoid
   page-breaks.
3. **? Shortcuts** — Opens the in-page keyboard-shortcut overlay (the
   `.ck-shortcuts` modal that's always installed by `chartis_shell`).
   Lists all of the shortcuts a partner can use on this page.
4. **⌘K Quick jump** — Opens the command palette (the `.ck-palette` modal
   that's also always installed). Partners type any route name (or part
   of it) and the palette navigates them there. Same effect as pressing
   Cmd-K / Ctrl-K or the `g+k` keyboard sequence.
5. **📖 Glossary** — Direct link to `/metric-glossary` where every metric
   the platform reports has its definition, rationale, formula, and source
   documents documented.
6. **🔬 Methodology** — Direct link to `/methodology` where every model on
   the platform has its inputs, assumptions, formulas, and validation
   references.
7. **Back to top** — Floating pill in the bottom-right corner. Appears
   only after the partner scrolls more than 600px down; smooth-scrolls to
   the top of the page. Auto-hides in print media.

## Idempotent JS install guards

Each helper carries its own idempotent install guard
(`__rcmCopyShareLinkInstalled`, `__rcmPrintViewInstalled`,
`__rcmPaletteOpenInstalled`, `__rcmBackToTopInstalled`) so dropping the
helper twice on one page never double-binds the click handlers. Pages that
have their own custom share button (currently only `/target-screener`)
pass `share=False` to `ck_page_actions()` so the row doesn't render a
duplicate.

## Keyboard shortcuts (separate from buttons)

Beyond the visible buttons, the shell also wires:

- **`/`** — focus the table search input (on pages that have one, like
  `/target-screener`).
- **ESC** — clear the focused search input + blur it.
- **`?`** — open the shortcuts overlay (same as clicking the button).
- **⌘K / Ctrl-K** — open the command palette.
- **g k** — also opens the palette (vim-style).

## Partner-day examples

- *"Send me this view of the Texas hospitals filtered to amber alerts"* →
  Copy share link, paste into Slack.
- *"Let me print this for the IC packet"* → Print this view.
- *"What's MOIC formally?"* → 📖 Glossary.
- *"How does the EBITDA bridge get computed?"* → 🔬 Methodology.
- *"How do I get to the compare screen quickly?"* → ⌘K Quick jump, type
  "compare".

## Why this design

Pre-loop (2026-05-28), pages each rolled their own action chrome — some
had share buttons, some didn't, locations varied, the keyboard shortcuts
were buried. The unified `ck_page_actions()` helper means the affordance
is identical on every page so partners build muscle memory.

## What it does NOT do

- Does not save the view to a backend bookmark — share-link is the
  bookmark mechanism (the URL IS the state).
- Does not export to PDF beyond what the browser print dialog supports.
- Does not require authentication — every action runs entirely client-
  side once the page is rendered.

## Related surfaces

- `/metric-glossary` — what 📖 Glossary points at.
- `/methodology` — what 🔬 Methodology points at.
- `/target-screener` — the flagship page where the share button has its
  own custom location (Active-screen sub-block eyebrow row).
