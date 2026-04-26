# Report 0076: External Dep Audit — `matplotlib`

## Scope

Per pyproject.toml:30 `matplotlib>=3.7,<4.0`. Sister to Reports 0016 (pyyaml), 0046 (numpy), 0053 (pandas).

## Findings

### Pin

`matplotlib>=3.7,<4.0`. Mirrored in `legacy/heroku/requirements.txt`. Floor 3.7 (Feb 2023); ceiling `<4.0` strict.

### Production usage

Per Report 0023 sweep, matplotlib appears in production imports — used for plotting. Estimated:

- `core/` ML / chart helpers
- `pe/` value-bridge SVGs (per Report 0029 commits like `power chart`)
- `reports/` packet renderer (chart export to PDF / PNG)

**Likely 20-50 importing files.** Smaller than numpy (134) or pandas.

### CVE history

Minimal. matplotlib has had a few low-severity issues over the years (e.g. CVE-2017-12852-style). No actively-exploitable issues at the floor 3.7+.

### Trust boundary

matplotlib renders chart data — no remote bytes. Trust = self.

### Upstream

Active. Latest 3.10+ as of audit (within 3.x). 4.0 not yet released.

### Headless / interactive concerns

matplotlib defaults to `Agg` backend on headless systems. The Dockerfile (Report 0033) doesn't set `MPLBACKEND` — relies on default.

If a feature branch depends on `interactive` extras with `plotly>=5.0` (Report 0023 — 0 imports anywhere), matplotlib remains the canonical chart engine.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR452** | **No `MPLBACKEND` env var set** | matplotlib auto-detects; usually `Agg` in container, `MacOSX` on dev. **Cross-platform inconsistency.** Recommend: explicit `MPLBACKEND=Agg` in Dockerfile. | Medium |
| **MR453** | **Matplotlib 4.0 will break things** | `<4.0` ceiling protects but eventual upgrade requires careful API audit. | Low |

## Dependencies

- **Incoming:** plotting / charting modules across rcm_mc/.
- **Outgoing:** numpy (transitive), Python C extensions (Pillow for images).

## Open questions / Unknowns

- **Q1.** Exact production matplotlib usage count.
- **Q2.** Are charts ever cached / exported via SVG vs PNG vs both?

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0077** | (Next iteration). |

---

Report/Report-0076.md written.

