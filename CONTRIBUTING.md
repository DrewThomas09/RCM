# Contributing

Thanks for reading. This repo is a healthcare-PE diligence platform
with a small, carefully-chosen dependency surface and strong
reproducibility guarantees. The rules below exist because a partner
citing a number in IC needs to rebuild the same number next quarter.

## Setup

```bash
git clone <this-repo> seekingchartis
cd seekingchartis/RCM_MC
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m pytest -q --ignore=tests/test_integration_e2e.py
```

Python 3.10+ required. 3.14 is the canonical target.

## Feature-branch workflow

- `main` is the stable baseline.
- New work lives on a `feature/*` or `chore/*` branch.
- PRs merge to `main` only after the full test suite passes.
- No merging to `main` from the CLI is required — open a PR, let CI
  run, review, merge via GitHub.

### The PE-intelligence non-modification contract

The `feature/pe-intelligence` branch operates under a strict
non-modification contract. It only *adds* files under:

- `rcm_mc/pe_intelligence/` — new partner-brain modules
- `docs/PE_HEURISTICS.md` — new doc sections
- `tests/test_pe_intelligence.py` — new test blocks

**Nothing else** in the tree is touched from that branch. If you need
to modify a shared module or add a general-purpose dependency, branch
from `main` instead.

## Code conventions (the ten rules)

Distilled from `RCM_MC/CLAUDE.md`:

1. **No new runtime dependencies** without discussion. The current
   surface is `numpy`, `pandas`, `pyyaml`, `matplotlib`, `openpyxl`.
   Optional: `python-pptx`, `python-docx`, `plotly` with graceful
   fallbacks when absent.
2. **Parameterized SQL only** — never f-string values into SQL.
3. **`BEGIN IMMEDIATE`** around check-then-write sequences in SQLite.
   See `deal_deadlines.add_deadline`, `auth.delete_user`,
   `watchlist.toggle_star` for examples.
4. **`html.escape()` every user-supplied string** before rendering to
   HTML. Attribute context escapes `"`; content context escapes
   `<>&`.
5. **`_clamp_int` every integer query parameter** — never
   `int(qs[...])` unchecked.
6. **Timezone-aware datetimes.** `datetime.now(timezone.utc)` unless
   comparing to other naive times.
7. **Private helpers prefix with underscore** (`_ensure_table`,
   `_validate_username`). Module-private state prefixed too
   (`_EVALUATOR_FAILURES`).
8. **Docstrings explain *why*, not *what*.** The code says what; the
   docstring explains the constraint or the prior incident that
   drove the decision.
9. **Additive dataclass changes only.** Every new field gets a
   sensible default so old packets still JSON-roundtrip.
10. **Output formatting discipline** — financial figures 2 decimals
    (`$450.25M`), percentages 1 decimal (`15.3%`, sign when
    meaningful), multiples 2 decimals + `x` (`2.50x`), dates ISO
    (`2026-04-15`), times UTC ISO.

## Testing

- **Each feature gets a `test_<feature>.py`** in `tests/`.
- **Bug fixes get `test_bug_fixes_b<N>.py`** and a regression
  assertion.
- **Multi-step workflows are tested end-to-end** via a real HTTP
  server on a free port, using `urllib.request`.
- **No mocks of our own code** — always exercise the real path.
  `unittest.mock` is acceptable only for external stubs (e.g., a
  failing `log_event` to verify silent-failure handling).
- **Order-independent tests.** Class-level state reset in
  `setUp` / `tearDown` (for example, the login-fail log on
  `RCMHandler`).

## Before you open a PR

- [ ] Full suite passes: `python -m pytest -q
      --ignore=tests/test_integration_e2e.py`.
- [ ] Your feature has its own `test_<feature>.py` file with both
      happy-path and edge-case assertions.
- [ ] No new runtime deps unless discussed.
- [ ] No data files added (secrets, personally-identifiable
      information, seller-supplied diligence material).
- [ ] Docstrings explain *why* for any non-obvious decision.
- [ ] If you added a new metric or lever, the ontology / registry /
      bridge / MC / workbench all know about it.

## PR description template

```
## What

One-paragraph summary. Imperative mood, concrete nouns.

## Why

The constraint or incident that drove this. Not "makes the code
cleaner" — *what went wrong without it?*

## Tests

- new: tests/test_<feature>.py
- regression: tests/test_bug_fixes_b<N>.py (if applicable)
- suite: N passing

## Non-goals

Things a reviewer might expect but that this PR explicitly does not
address. Avoids scope creep in review.
```

## Reporting a security concern

If you find a credential-handling bug, SQL injection vector, XSS
vector, or any other security-sensitive issue, **do not open a public
issue**. Email the maintainer directly.

## Questions

Open a GitHub issue or reach the maintainer at the email on the
profile. For architectural discussions, link to the relevant
[`RCM_MC/docs/README_LAYER_*.md`](RCM_MC/docs/) so we can ground the
conversation in the current design.
