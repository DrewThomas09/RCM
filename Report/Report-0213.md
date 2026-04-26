# Report 0213: Map Next Key File — `ai/llm_client.py` (241 lines, ANTHROPIC_API_KEY)

## Scope

Reads `ai/llm_client.py` head — Anthropic HTTP client. Closes Report 0212 Q1 + Report 0025 partial. Sister to Reports 0025 (Anthropic), 0212 (ai/ directory).

## Findings

### Imports (lines 12-23)

```python
from __future__ import annotations
import hashlib, json, logging, os, time
import urllib.request, urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
```

**8 stdlib only.** No third-party (no `anthropic` SDK — uses urllib directly per CLAUDE.md "stdlib-heavy").

### Env var (line 147)

```python
self._api_key = os.environ.get("ANTHROPIC_API_KEY", "")
```

**`ANTHROPIC_API_KEY`** — secret. Read on instance init.

**Default if missing**: empty string. Likely behavior: API calls fail downstream with 401.

### Cross-link to env-var registry (~14+ vars)

Adds `ANTHROPIC_API_KEY` to registry:
- RCM_MC_DB, RCM_MC_AUTH, RCM_MC_PHI_MODE, RCM_MC_SESSION_IDLE_MINUTES, RCM_MC_NO_PORTFOLIO, RCM_MC_DATA_CACHE, DOMAIN, FORCE_COLOR/NO_COLOR/TERM, HOME/USERPROFILE, RCM_MC_UI_VERSION, EXPORTS_BASE, CHARTIS_UI_V2, AZURE_VM_HOST/USER/SSH_KEY, SSH_KEY, **ANTHROPIC_API_KEY**.

**Now ~16 env vars total.**

### Cross-link to Report 0150 secret coverage

ANTHROPIC_API_KEY likely set via `.env` (per Report 0150 gitignored). **Safe** if env-only.

### Cross-link Report 0144 retry helper absence

`urllib.request` based — likely retry logic in module body (would need to read further). **Q1 below.**

## Merge risks flagged

| ID | Risk | Severity |
|---|---|---|
| **MR1001** | **`ANTHROPIC_API_KEY` env var read** at line 147 — empty default | If unset, API calls fail at runtime with 401. Should fail-fast at startup OR document in CLAUDE.md. | Medium |
| **MR1002** | **No `anthropic` SDK** — urllib direct | Per CLAUDE.md stdlib-heavy. Reduces dep but reinvents retry/error handling. | (advisory) |

## Dependencies

- **Incoming:** TBD — likely 4 sibling ai/ modules.
- **Outgoing:** stdlib + ANTHROPIC_API_KEY env.

## Open questions / Unknowns

- **Q1.** Does llm_client implement retries?

## Suggested follow-ups

| Iteration | Proposed area |
|---|---|
| **0214** | Incoming dep (in flight). |

---

Report/Report-0213.md written.
