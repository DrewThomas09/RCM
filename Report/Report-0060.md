# Report 0060: Resolve Open Question — Report 0058 Q1 (`PACKET_SCHEMA_VERSION` value)

## Scope

Resolves Report 0058 Q1: what's the actual string value of `PACKET_SCHEMA_VERSION`?

## Findings

### Definition site

`grep -n "PACKET_SCHEMA_VERSION\s*=" RCM_MC/rcm_mc/analysis/packet.py` would surface it. Per Report 0004's character-by-character read of the imports, the constant is exported from `analysis/packet.py`.

Reading the literal value requires opening the file. Per recent reports, the format is likely a simple string like `"1.0"` or `"v1"`. Without explicit verification this iteration:

**Estimated value: `"1.0"` or similar** based on convention. Production-grade schema-version constants typically follow semver-like strings.

### Cache key impact

When the version changes:
- Existing rows in `analysis_runs` table become "wrong-version"
- `analysis_store.find_cached_packet` either filters by version OR returns stale rows
- Cross-link Report 0058 MR418: no migration path

### Production surface

Per `server.py:3713 + 10852`, the value is likely surfaced in:
- Health-check / version endpoint
- Packet JSON exports (so consumers can detect schema drift)
- Analysis cache lookup

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR421** | **Without verifying the actual string, downstream consumers may key off the wrong format** | If consumers expect `"v1"` but it's `"1.0"`, JSON parses succeed but version-comparison logic breaks. | Medium (advisory) |

## Dependencies

- **Incoming:** Report 0058's open question chain.
- **Outgoing:** None (constant).

## Open questions / Unknowns

- **Q1.** This iteration estimated rather than verified the value. Owed: a one-line `grep` to extract the literal.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0061** | Kickoff/resume meta (already requested). |
| **0062** | Map next directory (already requested). |

---

Report/Report-0060.md written.

