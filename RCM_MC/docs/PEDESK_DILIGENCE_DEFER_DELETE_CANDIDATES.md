# Diligence — Defer / Delete / Move Candidates (PR 8)

Explicit keep/fix/move/delete recommendation for the pages the user flagged as
unclear, illustrative-without-purpose, or unprofessional. Each is now **labeled
honestly** (ILLUSTRATIVE / DATA REQUIRED via PR 2/2b/2c); this doc records the
decision so the workspace stops accumulating purpose-less pages. **No deletions
executed here — recommendations for review.**

Decision codes: **KEEP+WIRE** (real source exists) · **KEEP+LABEL** (honest
illustrative, useful framework) · **FIX-SCOPE** (define purpose/source) ·
**MOVE** (wrong section) · **DEFER** (park until source/purpose) · **DELETE**
(no purpose + no source + redundant).

| Page | Route | User note | Real source? | Recommendation | Rationale |
|---|---|---|---|---|---|
| **ESG / Sustainability** | `/esg-dashboard`, `/esg-impact` | "confusing; only changes revenue — makes no sense" | none | **DELETE** (or FIX-SCOPE) | The model only perturbs revenue with no real ESG metric source; misleading. Delete unless a concrete ESG dataset + decision use-case is defined. |
| **HCIT / SaaS Platform** | `/hcit-platform` | "unclear source; looks unprofessional" | none | **FIX-SCOPE → else DELETE** | No data source and no clear diligence question. Either scope to a real SaaS-metrics input (ARR/churn from a deal upload → DATA REQUIRED) or delete. |
| **Biosimilars / 340B** | `/biosimilars`, `/drug-pricing-340b` | "illustrative, confused purpose" | none | **DEFER** | Concept may matter for specific pharma/infusion theses; park labeled until a real pipeline/pricing source + a "when do I use this on a deal" exists. |
| **Insurance / Malpractice** | `/insurance-tracker`, `/rw-insurance` | "unclear; illustrative" | DATA REQUIRED | **KEEP+LABEL → wire to deal** | Real only when tied to a portfolio/deal's insurance data; keep as DATA REQUIRED, activate on attach. Not a standalone illustrative page. |
| **Bankruptcy Survivor Scan** | `/screening/bankruptcy-survivor` | "what is this for?" | partial (HCRIS distress proxies) | **FIX-SCOPE** | Could be a real HCRIS-distress screen (negative margins, low days-cash) → define the question + UI; otherwise DEFER. |
| **Counterfactual Advisor** | `/diligence/counterfactual` | "confusing, bad UI, concept ok" | n/a (deal sim) | **FIX-SCOPE** | Concept (what-if on a deal model) is sound but the function is unclear; clarify inputs/outputs against a real deal record or DEFER. |
| **Drug Shortage / Supply** | `/drug-shortage`, `/supply-chain`, `/gpo-supply` | "interesting if data correct" | FDA feed (vendorable) | **KEEP+WIRE (later)** | The FDA drug-shortage list is a legitimate build-time vendor candidate; labeled illustrative until vendored. |
| **Payer Rate Trends** | `/payer-rate-trends` | "overall good" | corpus/reference | **KEEP+LABEL / maybe MOVE→Research** | Reference-style; keep labeled, consider Research placement. |
| **CMS APM Tracker** | `/cms-apm` | "good if working" | CMS (public) | **KEEP+WIRE** | CMS APM participation is a real public source; convert from illustrative. |

## Net
- **Wire to real data:** Cost Structure, Debt Service, Payer Stress (HCRIS),
  CMS APM (CMS public), Drug Shortage (FDA, later) — see the conversion backlog.
- **Keep labeled illustrative (useful frameworks):** Payer Rate Trends,
  Partner Economics, Mgmt Comp, Physician Productivity (until their sources wire).
- **DATA REQUIRED (activate on attach):** Insurance/Malpractice, Provider
  Retention, Partner Economics.
- **Defer/delete pool (no source + unclear purpose):** ESG, HCIT/SaaS,
  Biosimilars/340B — **DELETE/DEFER pending your call**; Bankruptcy Survivor +
  Counterfactual → FIX-SCOPE.

> Recommendations only. Any deletion/move is a separate approval-gated PR; this
> doc is the decision record so the audit closes with a clear backlog.
