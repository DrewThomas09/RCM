# RAG source — CMS Provider X-Ray: how it resolves a provider

**What X-Ray is.** A universal CMS diligence scanner. Enter a CCN, provider
id, or facility name and PEdesk resolves the provider across every live CMS
vertical (Hospital/HCRIS, SNF, Home Health, Hospice, Dialysis, IRF, LTCH),
detects the vertical, benchmarks it against peers, and renders a transparent
diligence report. Route: `/diligence/xray`.

**How resolution works.**
- Identifiers are **strings with leading zeroes preserved** — `015009` is not
  `15009`.
- **Exact CCN/id match wins first**, searched across all seven verticals in
  the order Hospital → SNF → Home Health → Hospice → Dialysis → IRF → LTCH.
- If no exact id match, it falls back to **case-insensitive name-contains**,
  optionally narrowed by a state postal code.
- A query that matches **more than one** provider returns **all** of them and
  the UI shows a resolver table — it never guesses.

**Why a CCN can resolve to more than one vertical.** Hospital-based **IRF and
LTCH units share their CCN with the HCRIS hospital record**. So an IRF/LTCH
CCN legitimately resolves to multiple matches (e.g. the hospital *and* the
rehab unit). SNF / Home Health / Hospice / Dialysis CCN ranges do not collide
with HCRIS and resolve singly.

**What X-Ray does NOT do.** It does not vendor new data, call external
services, or invent providers. Unknown identifiers return an honest
not-found state. Hospital benchmarking (beds/revenue/margin) lives in the
HCRIS-powered hospital profile, not in this post-acute X-Ray view.

**Good questions it can answer.** "What vertical is this CCN?" · "Why did this
CCN match two verticals?" · "Is there a provider by this name in Texas?" ·
"Where does this provider's data come from?"
