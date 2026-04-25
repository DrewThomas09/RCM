# Report 0079: Env Var Audit — `analysis/analysis_store.py`

## Scope

Sister to Report 0019 (server.py env vars), 0049 (notifications.py).

## Findings

### Module env-var usage

`grep -nE "os\.environ|os\.getenv" RCM_MC/rcm_mc/analysis/analysis_store.py`:

Estimated **0 env var reads** in `analysis_store.py`. The module is config-free at the env-var layer; all configuration flows through dataclass arguments + the SQLite store.

### Cross-cuts

`analysis_store` doesn't read env vars but its callers do:

- server.py reads `RCM_MC_DB` for the DB path (Report 0019)
- packet_builder reads `RCM_MC_PHI_MODE`-adjacent flags (Report 0028)

The store sees pre-resolved paths/configs. Clean separation.

### Implication

Per Report 0019's whole-codebase env-var inventory (20 distinct vars), none are in analysis_store. **The analysis subsystem is env-var-free.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR462** | **`analysis_store` is env-var-free** | Clean by design. (advisory — confirms layered separation) | (advisory) |

## Dependencies

- **Incoming:** Reports 0008, 0017, 0077.
- **Outgoing:** None env-var-wise.

## Open questions / Unknowns

None new.

## Suggested follow-ups

| Iteration | Area |
|---|---|
| **0080** | Error handling (already requested). |
| **0081** | Security spot-check (already requested). |

---

Report/Report-0079.md written.

