# Report 0028: Config Value Trace — `RCM_MC_PHI_MODE`

## Scope

This report traces the **`RCM_MC_PHI_MODE` environment variable** end-to-end on `origin/main` at commit `f3f7e7f`. Every read, every write, every default fallback, every test override is enumerated. The value was selected because:

- Report 0019 surfaced it as a 2-read env var with no semantic understanding (MR147 — HIGH-PRIORITY discovery).
- The name suggests HIPAA-relevant PHI (Protected Health Information) handling — security-critical.
- It has been deferred for 9 iterations (Reports 0019, 0020, 0024, 0025, 0026, 0027 all suggested following up).

Prior reports reviewed before writing: 0024-0027.

## Findings

### Definition

`RCM_MC_PHI_MODE` is an environment variable. There is **no constants file declaration** — the env-var string appears as a literal in 18 sites across the repo. Recognized values (case-insensitive):

| Value | Meaning |
|---|---|
| `"disallowed"` | Public-data-only deployment. Green banner injected. |
| `"restricted"` | PHI-eligible deployment under BAA. Amber banner injected. |
| (unset / empty / any other value) | No banner. Treated as "unconfigured." |

Defined as comments at `RCM_MC/rcm_mc/ui/_chartis_kit.py:53-56`:

```
# Controlled by env var ``RCM_MC_PHI_MODE``:
#   "disallowed" → green "no PHI" banner — public-data-only deployments
#   "restricted" → amber "PHI under BAA" banner — compliant hosts only
#   (unset)      → no banner (dev / unconfigured)
```

### Production read sites (2 unique consumer functions)

#### Site 1 — `_chartis_kit.py:_phi_banner_html()` (line 62-85)

```python
def _phi_banner_html() -> str:
    mode = _os.environ.get("RCM_MC_PHI_MODE", "").strip().lower()
    if mode == "disallowed":
        return (
            '<div ... data-phi-mode="disallowed">'
            '🛡️ Public data only — no PHI permitted on this instance.'
            '</div>'
        )
    if mode == "restricted":
        return (
            '<div ... data-phi-mode="restricted">'
            '⚠️ PHI-eligible deployment — access audit-logged. '
            'Do not export outside BAA scope.'
            '</div>'
        )
    return ""
```

- **Default if missing:** `""` (empty string) — no banner rendered.
- **Whitespace-tolerant:** `.strip()`.
- **Case-insensitive:** `.lower()`.
- **Per-render evaluation:** `os.environ.get(...)` is inside the function, called every time the shell renders.
- **Three branches:** disallowed → green banner; restricted → amber banner; else → no banner.
- **Only the banner HTML changes.** No code path is taken / skipped based on PHI mode.

#### Site 2 — `dashboard_page.py:2424` (the dashboard "PHI mode" card)

```python
phi_mode = (os.environ.get("RCM_MC_PHI_MODE") or "unset").lower()
phi_level = {"disallowed": "ok", "restricted": "stale",
             "unset": "never"}.get(phi_mode, "never")
items.append(("PHI mode", phi_level, phi_mode))
```

- **Default if missing:** `"unset"` (string sentinel).
- **3-mode mapping:** disallowed → "ok"; restricted → "stale" (?!); unset → "never".
- **Per-render** evaluation (inside the dashboard render function).
- Shown as a status card on the dashboard. The label `"stale"` for `"restricted"` is **counter-intuitive** — restricted mode is a strict HIPAA posture, not a stale data state. **Possible UI bug or repurposed status field.**

### Production write sites — NONE

`grep -rn "os\.environ\['RCM_MC_PHI_MODE'\]" RCM_MC/rcm_mc/` and `grep -rn "os\.environ\[.RCM_MC_PHI_MODE.\] *=" RCM_MC/rcm_mc/` both return empty. **The application never writes this env var** — only reads.

### Production deployment write site (docker-compose)

`RCM_MC/deploy/docker-compose.yml:42`:

```yaml
environment:
  - RCM_MC_DB=/data/rcm_mc.db
  - RCM_MC_AUTH=${RCM_MC_AUTH:-}
  - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
  - RCM_MC_PHI_MODE=${RCM_MC_PHI_MODE:-disallowed}     # ← line 42
  - RCM_MC_HOMEPAGE=${RCM_MC_HOMEPAGE:-dashboard}
  - RCM_MC_SESSION_IDLE_MINUTES=${RCM_MC_SESSION_IDLE_MINUTES:-30}
```

**Container default: `"disallowed"`.** If the host shell sets `RCM_MC_PHI_MODE=restricted` (or any other), it overrides. Otherwise the container starts with `disallowed`.

Documented at `docker-compose.yml:21` as a comment block:

```
#   RCM_MC_PHI_MODE=disallowed     # recommended (shows banner)
```

### Test override sites (4 test files, 9 unique override blocks)

| File:line | Override |
|---|---|
| `tests/test_web_production_readiness.py:65` | `with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "disallowed"}):` |
| `tests/test_web_production_readiness.py:73` | `with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "restricted"}):` |
| `tests/test_web_production_readiness.py:81` | `env = {k: v for k, v in os.environ.items() if k != "RCM_MC_PHI_MODE"}` (unset case) |
| `tests/test_web_production_readiness.py:87` | `with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "DISALLOWED"}):` (uppercase) |
| `tests/test_web_production_readiness.py:104` | `env = {"RCM_MC_PHI_MODE": "disallowed", "CHARTIS_UI_V2": "0"}` (legacy combination) |
| `tests/test_web_production_readiness.py:117` | unset case (legacy variant) |
| `tests/test_dashboard_page.py:73` | `with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "disallowed"}):` |
| `tests/test_dashboard_page.py:92` | `with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "disallowed"}):` (the dashboard PHI card test) |
| `tests/test_security_hardening.py:393` | `os.environ.pop("RCM_MC_PHI_MODE", None)` — explicit unset |
| `tests/test_security_hardening.py:398` | `with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "disallowed"}):` |
| `tests/test_security_hardening.py:405` | `with patch.dict(os.environ, {"RCM_MC_PHI_MODE": "restricted"}):` |

**Test coverage is excellent for the banner rendering** — all 3 valid states + uppercase + unset variant + missing-key-pop are exercised.

### Default-fallback inventory

| Site | Default |
|---|---|
| `_chartis_kit.py:63` (`_phi_banner_html`) | `""` — no banner |
| `dashboard_page.py:2424` (PHI card) | `"unset"` — status "never" |
| `docker-compose.yml:42` | `"disallowed"` |
| Tests | various per-test |

**Defaults are inconsistent across sites:**

- `_phi_banner_html` falls back to `""` (truthy: no banner).
- `dashboard_page.py` falls back to the string `"unset"`.
- Docker container falls back to `"disallowed"`.

**Three different "missing" semantics.** A bare-metal launch (no docker-compose) reaches the `_phi_banner_html` empty default; the dashboard card shows "unset/never". A docker launch always has a value (defaulted to "disallowed"). The two internal modules don't agree on what "no env" means.

### What `RCM_MC_PHI_MODE` does NOT do (HIGH-PRIORITY GAP)

Despite the name, **the env var only changes a banner**. It does NOT:

| Expected behavior | Implemented? |
|---|---|
| Block PHI uploads | **No** |
| Gate LLM API calls (would prevent prompt content from going to Anthropic) | **No** |
| Redact PHI from logs | **No** |
| Disable export endpoints | **No** |
| Restrict route access | **No** |
| Enable audit-log every request | **No** (claim in banner: "access audit-logged" — but the audit subsystem fires regardless of this var) |
| Reject PHI in incoming requests | **No** |
| Trigger `compliance/phi_scanner.py` to scan content | **No** |
| Skip caching (which could persist PHI in `llm_response_cache`) | **No** (cross-link Report 0025 MR213) |
| Bypass `analysis/packet_builder.py` paths that touch real-patient data | **No** |
| Refuse `/api/deals/*/export` for PHI-bearing deals | **No** |

**The banner is a UI claim with NO enforcement.** A `disallowed` deployment shows "🛡️ Public data only — no PHI permitted on this instance" but the application **does not block PHI from being uploaded, processed, or exported**. The banner lies if PHI ever enters the system.

### `compliance/phi_scanner.py` — sister module, INDEPENDENT of the env var

`RCM_MC/rcm_mc/compliance/phi_scanner.py` (252 lines) is a pattern-based PHI scanner — detects SSN, phone, DOB, MRN, NPI, email, address patterns. **Per `grep "RCM_MC_PHI_MODE" RCM_MC/rcm_mc/compliance/`: zero references.** The scanner exists but is never wired to the env var that supposedly governs PHI handling.

**This is the missing enforcement layer.** A real PHI mode should:
1. Run `phi_scanner.scan(...)` on every upload.
2. If `mode == "disallowed"` and the scanner finds PHI, reject the upload.
3. If `mode == "restricted"`, log the upload to the audit chain.
4. If unset, do nothing.

Currently the wiring is: docker-compose env → renders banner. That's it.

### Sister env vars (for context)

Per docker-compose.yml lines 38-44, the production env-var set is:

| Var | Default | Use |
|---|---|---|
| `RCM_MC_DB` | `/data/rcm_mc.db` | DB path (Report 0019) |
| `RCM_MC_AUTH` | `""` (empty = no auth) | HTTP Basic creds (Report 0019) |
| `ANTHROPIC_API_KEY` | `""` | LLM key (Report 0025) |
| **`RCM_MC_PHI_MODE`** | **`"disallowed"`** | This report |
| `RCM_MC_HOMEPAGE` | `"dashboard"` | Root redirect (Report 0019) |
| `RCM_MC_SESSION_IDLE_MINUTES` | `"30"` | Session idle (Report 0019) |

PHI_MODE is the ONLY one with a non-empty production default. That's because **the recommended posture is "I do NOT have PHI" (banner shown).**

## Merge risks flagged

| ID | Risk | Detail | Severity |
|---|---|---|---|
| **MR250** | **HIGH-PRIORITY: PHI banner is purely cosmetic — no enforcement layer** | Banner says "Public data only — no PHI permitted" but no code blocks PHI from being uploaded, processed, or exported. A user can upload PHI on a `disallowed` instance and nothing rejects it. **Banner is a misleading claim.** Recommend: wire `compliance/phi_scanner.py` to ingestion paths gated by `RCM_MC_PHI_MODE`. | **Critical** |
| **MR251** | **`compliance/phi_scanner.py` exists but is never invoked from PHI_MODE-gated paths** | 252-line module detects SSN, phone, DOB, MRN, NPI, email, address. **0 references in any `RCM_MC_PHI_MODE`-bearing site.** The scanner is the "right tool" — but unwired. | **Critical** |
| **MR252** | **Three different "missing" semantics across sites** | `_phi_banner_html` → `""`, `dashboard_page.py` → `"unset"`, `docker-compose.yml` → `"disallowed"`. **Bare-metal launches behave differently than container launches.** Recommend: pick one default (`"disallowed"` is safest) and apply everywhere. | **High** |
| **MR253** | **Banner claim "access audit-logged" (restricted mode) is unverified** | The amber-banner text promises audit logging on access. The audit-log subsystem fires on requests regardless of PHI_MODE. **The claim is true (audit log runs) but unrelated to the flag.** Misleading. | Medium |
| **MR254** | **Per-render env-var evaluation means UI changes immediately on shell change** | Ops can flip the banner without redeploying. Acceptable, but means a brief window where users see a stale banner if the value flickers. | Low |
| **MR255** | **`dashboard_page.py:2425` maps `"restricted"` → status `"stale"` — semantic mismatch** | "Stale" implies out-of-date data; restricted PHI mode is a HIPAA posture. Likely a copy-paste bug from an unrelated status enum. | Medium |
| **MR256** | **No env-var validation — typo `RCM_MC_PHI_MODE=dissallowed` silently no-ops** | Banner shows nothing; ops thinks it's set. Recommend: at boot, log warning if the var has a non-recognized value. | Medium |
| **MR257** | **LLM cache (`llm_response_cache`) stores prompt-derived text** | (Cross-link Report 0025 MR213.) If a user accidentally enters PHI into a prompt while `RCM_MC_PHI_MODE=disallowed` is set, the response (which may echo PHI) is cached forever in plaintext SQLite. **Banner claim violated.** Recommend: `RCM_MC_PHI_MODE=disallowed` should disable the LLM cache. | **Critical** |
| **MR258** | **Test coverage of banner rendering — but no test that PHI is actually blocked** | 9 test override blocks all check the *banner HTML*. None check that PHI is blocked when `disallowed`. **Tests pin the cosmetic, not the constraint.** | **High** |
| **MR259** | **`feature/workbench-corpus-polish` deletes `dashboard_page.py`** (Report 0007 MR46) | The PHI dashboard card at line 2424 disappears with the file. **The banner at `_chartis_kit.py:63` survives**, but the dashboard "PHI mode" status card does not. Cross-branch interaction with this concern. | Medium |
| **MR260** | **`feature/workbench-corpus-polish` removes `RCM_MC_DB` env-var fallback** (Report 0019 MR142) | Combined with this report's findings, that branch's removal pattern may extend to PHI_MODE. Pre-merge: cross-branch sweep needed. | Medium |
| **MR261** | **Audit log doesn't tag entries with PHI_MODE state** | If a future incident requires "show me every action while PHI_MODE was restricted", the audit log doesn't carry that field. Recommend: include PHI_MODE in audit_chain entries. | Medium |
| **MR262** | **No HIPAA-compliance test scenario** | A real HIPAA audit would require: "given PHI_MODE=disallowed, prove no PHI persists in DB after restart." That test does not exist. | **High** for any HIPAA-bound deploy |
| **MR263** | **`compliance/HIPAA_READINESS.md` exists** (per Report 0026 directory listing) — does it acknowledge this gap? | Need to read that doc to see whether the gap is documented or assumed-fixed. | Medium |

## Dependencies

- **Incoming (who reads `RCM_MC_PHI_MODE`):** `_chartis_kit.py:_phi_banner_html()` (banner renderer) + `dashboard_page.py` (dashboard status card). Both via `os.environ.get(...)`. **Two production read sites.**
- **Outgoing (what `RCM_MC_PHI_MODE` depends on):** the host environment / docker-compose / CI; transitively the `os.environ` dict.

## Open questions / Unknowns

- **Q1 (this report).** Was `RCM_MC_PHI_MODE` ever intended to be more than a banner? Git log on `_chartis_kit.py` and `dashboard_page.py` would surface the introduction commit and any rejected designs.
- **Q2.** Does `compliance/phi_scanner.py` have a `compute_phi_scanner()` entry that produces structured output? If yes, wiring it to PHI_MODE is one PR away.
- **Q3.** What does `compliance/HIPAA_READINESS.md` say about this gap? Read needed.
- **Q4.** Why does `dashboard_page.py:2425` map `"restricted"` to `"stale"`? Is this a UI bug (likely) or a deliberate semantic (unlikely)?
- **Q5.** Are there any other env vars that suggest similar "claim without enforcement" patterns? `RCM_MC_NO_PORTFOLIO` (Report 0019 inventory) is one — does it actually disable portfolio features, or just hide them?
- **Q6.** Does `feature/workbench-corpus-polish` (which removes `dashboard_page.py`) preserve the `_chartis_kit.py` banner rendering?
- **Q7.** What's in the audit log when PHI_MODE is set? Reading `auth/audit_log.py` would confirm whether requests are tagged.

## Suggested follow-ups

| Iteration | Proposed area | Why |
|---|---|---|
| **0029** | **Read `compliance/phi_scanner.py`** end-to-end — what would wiring it cost? | Resolves Q2. The single most actionable security improvement. |
| **0030** | **Read `compliance/HIPAA_READINESS.md`** — does it acknowledge MR250? | Resolves Q3 / MR263. |
| **0031** | **Audit `auth/audit_log.py`** — does it tag entries with PHI_MODE? | Resolves Q7 / MR261. Owed since Report 0021 Q1. |
| **0032** | **Audit `RCM_MC_NO_PORTFOLIO`** — sister "claim without enforcement" candidate? | Resolves Q5 / sister to MR250. |
| **0033** | **Fix MR255** — change `dashboard_page.py:2425` mapping for `"restricted"` from `"stale"` to `"warning"` or `"compliant"`. | One-line UX fix. |
| **0034** | **Implement enforcement layer** — wire `phi_scanner` into ingestion paths gated by `RCM_MC_PHI_MODE`. | Real fix for MR250 / MR251 / MR262. |
| **0035** | **Audit `RCM_MC/deploy/Dockerfile`** — owed since Report 0023. | Closes deploy stack. |

---

Report/Report-0028.md written. Next iteration should: read `RCM_MC/rcm_mc/compliance/phi_scanner.py` end-to-end and document its API surface — the single most actionable security improvement is to wire this scanner into ingestion paths gated by `RCM_MC_PHI_MODE`, and we need its API documented before that wiring is possible (closes MR250 / MR251 / Q2).

