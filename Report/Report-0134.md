# Report 0134: Documentation Foil — `analysis/deal_overrides.py` is exemplary; `exports/*.py` is the gap

## Scope

Reads `RCM_MC/rcm_mc/analysis/deal_overrides.py` end-to-end (410 lines). **Closes Report 0118 MR677 high (carried 7+ iterations)** + Report 0124 MR705/Report 0123/Report 0107 deal_overrides FK question. Pivots on iteration task — this module is **exemplary docs**, NOT a gap; report instead frames the doc-gap pattern by contrast.

## Findings

### CLOSES Report 0118 MR677 high — `deal_overrides` schema

`analysis/deal_overrides.py:204-225`:

```sql
CREATE TABLE IF NOT EXISTS deal_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT NOT NULL,
    override_key TEXT NOT NULL,
    override_value TEXT NOT NULL,
    set_by TEXT NOT NULL,
    set_at TEXT NOT NULL,
    reason TEXT,
    UNIQUE(deal_id, override_key),
    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
        ON DELETE CASCADE
)
```

**8 fields, 1 UNIQUE, 1 FK with CASCADE, 1 index `ix_deal_overrides_deal`.**

### Schema-inventory progress

After this report:

| Table | Walked? | FK behavior |
|---|---|---|
| `deals` | Report 0017 | (parent table) |
| `runs` | Report 0047 | none |
| `analysis_runs` | Report 0077 | (TBD per Report 0118 MR678) |
| `audit_events` | Report 0123 (cross-corrected) | none |
| `hospital_benchmarks` | Report 0102 | none |
| `webhooks` | Report 0104 | none |
| `webhook_deliveries` | Report 0104 | none (MR577 — should have FK to webhooks) |
| `data_source_status` | Report 0107 | none |
| `mc_simulation_runs` | Report 0117 | **CASCADE** |
| `generated_exports` | Report 0133 | **SET NULL** |
| **`deal_overrides`** | **0134 (this)** | **CASCADE** |
| `deal_sim_inputs` | named (Report 0110) — STILL not walked | unknown |

**11 tables walked + 1 named-but-unwalked.** Backlog: ~10 tables remain.

### Three FK-bearing tables now mapped

Per Report 0117 + Report 0133 + this report:

| Table | FK | ON DELETE |
|---|---|---|
| `mc_simulation_runs.deal_id` | → deals(deal_id) | **CASCADE** |
| `generated_exports.deal_id` | → deals(deal_id) | **SET NULL** |
| `deal_overrides.deal_id` | → deals(deal_id) | **CASCADE** |

**2 CASCADE + 1 SET NULL.** Per Report 0133 MR756: project lacks documented FK policy. Generalization: **mutable derived data → CASCADE** (mc_runs, overrides — recompile-able); **audit trail → SET NULL** (exports — preserve evidence).

### Public API surface (7 functions, 1 private helper)

| Line | Symbol | Kind | Docstring |
|---|---|---|---|
| 93 | `validate_override_key(key) -> None` | public | **YES — extensive** |
| 183 | `_coerce_for_json(value) -> Any` | private | YES |
| 204 | `_ensure_table(store)` | private | YES (short) |
| 229 | `_utcnow_iso() -> str` | private trivial | NONE (acceptable) |
| 235 | `set_override(store, deal_id, key, value, *, set_by, reason=None) -> int` | **public** | YES |
| 281 | `get_overrides(store, deal_id) -> Dict[str, Any]` | **public** | YES |
| 308 | `clear_override(store, deal_id, key) -> bool` | **public** | YES |
| 321 | `list_overrides(store, deal_id=None) -> List[Dict]` | **public** | YES |
| 361 | `group_overrides(overrides) -> Dict[str, Any]` | **public** | YES (extensive — output shape example) |

**6 of 6 public functions documented (excluding trivial `_utcnow_iso`).** **Module-level docstring is 23 lines** — explains purpose, namespaces, persistence design, hash_inputs integration, ProvenanceTag.

### CONTRAST vs documentation-gap modules

Per Reports 0104 (`infra/webhooks.py`) and 0133 (`exports/export_store.py`):

| Module | Lines | Public fns | Docstrings? |
|---|---|---|---|
| `infra/webhooks.py` | 179 | 4 | **3 of 4 missing** (Report 0104 MR575) |
| `exports/export_store.py` | 87 | 2 | **2 of 2 missing** (Report 0133 MR758) |
| **`analysis/deal_overrides.py`** | **410** | **6** | **6 of 6 PRESENT** |

**`deal_overrides.py` is the discipline foil.** Pattern: **larger / newer / analyst-facing modules document well; store-layer / CRUD modules document poorly.** Project-wide doc-gap is in the SQLite-store family.

### Why the doc gap matters (cross-link Report 0091, 0124)

Per Report 0124: `PortfolioStore` has 237 importers. The store-layer is the most-touched code. Per the pattern above, the most-touched code is the WORST-documented. Onboarding a new developer means navigating 8+ undocumented store-CRUD modules.

### `validate_override_key` — defensive validation

Lines 93-180: validates 5 prefix namespaces:
- `payer_mix.<payer>_share` (must end in `_share`, payer in `_VALID_PAYERS` 6-set)
- `method_distribution.<payer>.<method>` (both validated against 6 + 8 sets)
- `bridge.<field>` (whitelist of 12 BridgeAssumptions fields)
- `ramp.<family>.<field>` (6 families × 3 fields)
- `metric_target.<metric>` (regex `^[a-z][a-z0-9_]{1,64}$`)

**Strict validation at write time.** Prevents bad data from entering the table. Cross-correction to Report 0117 MR676 / 0102 MR560 free-form pattern: **deal_overrides DOES enforce key validation**, breaking the project-wide free-form-text pattern.

### `set_override` is UPSERT via `ON CONFLICT(deal_id, override_key) DO UPDATE`

Lines 256-268. Same UPSERT pattern as Report 0107 `data_source_status.set_status`. Atomicity good; no `BEGIN IMMEDIATE` needed since ON CONFLICT is single-statement.

### `_coerce_for_json` — type narrowing

Lines 183-199: rejects non-JSON-encodable types at write. `_coerce_for_json(value)` recurses into lists/tuples/dicts, raises `ValueError` on classes/objects/etc. **Tight type discipline** — better than Report 0117's hand-written rehydrator (which was permissive).

### `get_overrides` malformed-JSON tolerance

Lines 297-305:

```python
try:
    out[str(r["override_key"])] = json.loads(r["override_value"])
except (json.JSONDecodeError, TypeError):
    logger.warning(
        "deal_overrides: malformed JSON at deal=%s key=%s",
        deal_id, r["override_key"],
    )
```

**Logger.warning on parse failure.** Cross-link Report 0131 MR745 (playbook.yaml silently swallowed): **deal_overrides does it RIGHT** — log the failure, skip the row, don't crash. Should be the project pattern.

### `group_overrides` — namespace splitter

Lines 361-409. Returns 5-key dict matching the 5 prefixes. **Extensive output-shape docstring with example dict.** This is the doc-comment quality bar to aim for.

### Cross-link Report 0023 PHI scanner

`deal_overrides.set_by` field captures username — could potentially leak PII if usernames contain real names. Cross-link Report 0028 PHI mode + Report 0123 GDPR export (which queries `deal_overrides.set_by` for user data export). **Compliance-aware design.**

### Importers (10 production + tests TBD)

Per `grep "deal_overrides"`:

- `pe_cli.py` — CLI flag for setting overrides
- `server.py` — HTTP routes
- `ui/deal_timeline.py` — render in timeline
- `infra/data_retention.py` (Report 0123) — `export_user_data` queries `set_by` for GDPR
- `analysis/cross_deal_search.py` — search across overrides
- `analysis/packet.py` (Report 0057) — folded into packet
- `analysis/packet_builder.py` (Report 0020) — applied at build time
- `analysis/analysis_store.py` — cache invalidation via hash_inputs
- `portfolio/store.py` — possibly in `init_db`
- `tests/` — probably 3-5 test files

### Comparison vs other docstring-rich modules

| Module | Lines | Public fns | All docstrings? |
|---|---|---|---|
| `auth/auth.py` (Report 0021) | ~430 | many | YES |
| `domain/econ_ontology.py` (Report 0095) | 816 | 3 + 5 enums + 4 dataclasses | YES |
| `infra/_terminal.py` (Report 0109) | 231 | 9 | YES |
| `analysis/deal_overrides.py` (this) | 410 | 6 | **YES** |

Discipline cluster: `auth/`, `domain/`, `infra/` (most), `analysis/` (most) are well-documented. `infra/webhooks/exports/store-layer` are NOT.

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR677-CLOSED** | `deal_overrides` table schema-walked. 8 fields, FK with CASCADE, UNIQUE(deal_id, override_key). | (closure) |
| **MR761** | **3 FK-bearing tables, 2 different cascade modes (CASCADE × 2, SET NULL × 1)** | Per pattern observation: derived data CASCADE, audit-trail SET NULL. **Should be documented in CLAUDE.md / coding conventions.** Cross-link Report 0117 MR668 + 0133 MR756. | Medium |
| **MR762** | **`deal_overrides.set_by` is required (NOT NULL)** but defaults to `"unknown"` if blank | Per `set_override` line 267: `str(set_by or "unknown")`. Audit trail says "unknown" without trace. Should reject empty `set_by` instead. | Low |
| **MR763** | **`deal_overrides` is in `infra/data_retention.export_user_data` GDPR query (Report 0123)** but NOT in `DEFAULT_RETENTION_DAYS` policy | Cross-link Report 0123 MR705 (12+ tables NOT in policy). Override audit trail grows indefinitely. | Medium |
| **MR764** | **Doc-gap pattern observation**: store-layer / CRUD modules consistently lack public-fn docstrings | Reports 0104 (webhooks 3-of-4), 0133 (export_store 2-of-2), 0099 (custom_metrics partial). Pattern: foundation-data modules under-documented vs analysis-layer modules. | Medium |

## Dependencies

- **Incoming:** 10 production files (analysis chain, server, CLI, UI, data_retention).
- **Outgoing:** stdlib (`json`, `logging`, `re`, `datetime`, `typing`); SQLite via `store.connect()`.

## Open questions / Unknowns

- **Q1.** Why is `analysis_runs.deal_id` not declared as FK in audited Report 0077 — does it actually have one (per Report 0118 PRAGMA comment) or is the PRAGMA comment outdated?
- **Q2.** Is there a CLI flag for `set_override` — `rcm-mc-pe override set --deal-id X --key Y --value Z`?
- **Q3.** What's `analysis/cross_deal_search.py` — never reported.

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0135** | Schema-walk `deal_sim_inputs` (Report 0110 backlog — last named-but-unwalked table). |
| **0136** | Re-read `analysis/analysis_store.py` schema-walk to verify `analysis_runs` FK (closes MR678 + Q1). |
| **0137** | Read `cli.py` head (1,252 lines, 14+ iterations owed). |
| **0138** | Add CLAUDE.md FK-policy paragraph based on observed pattern (concrete remediation for MR761). |

---

Report/Report-0134.md written.
Next iteration should: schema-walk `deal_sim_inputs` (last named-but-unwalked table — closes Report 0110 MR616 backlog).
