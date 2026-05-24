# Diligence Workspace Reform — Loop Ledger

**Started:** 2026-05-24 (autonomous 5–8h loop).
**Goal:** make every Diligence page answer *what is it for, what data powers it,
is it real/derived/illustrative, what's the next action* — and either wire it
to real data or label it honestly. HCRIS X-Ray is the gold-standard template.

**Operating rules (this loop):** small PRs · update this ledger after each ·
**no invented data** · source/purpose clarity over visual polish · continue
autonomously through docs/source-label/Guide work while approval-gated visible
PRs wait · never touch auth/deploy/env/secrets · #579/#580 parked.

---

## Route inventory (counts)
- `/diligence/*` routes: **30** (workflow + analyzers).
- Standalone analyzer routes (mostly `ui/data_public/`): **~40** (payer / cost /
  debt / physician / retention / partner / comp / drug-shortage / biosimilars /
  esg / hcit / insurance / cms-apm / payer-rate-trends / …).

## Central finding (grounded in code)
The Diligence surface has **three tiers**:
1. **Real-data (LIVE):** HCRIS X-Ray (`diligence/hcris_xray` engine) + deal-
   workflow pages tied to `PortfolioStore` / `data.pipeline` (deal, ingest,
   checklist, IC packet, questions).
2. **Illustrative layer (`ui/data_public/`):** ~14+ analyzer pages confirmed to
   use **hardcoded dataclass lists with no real loader** — Payer Stress, Cost
   Structure, Debt Service, Physician Productivity, Provider Retention, Partner
   Economics, Mgmt Comp, Drug Shortage, Biosimilars, ESG, HCIT/SaaS, Insurance,
   CMS APM, Payer Rate Trends.
3. **Reference/corpus:** Sponsor Track Record, Payer Intelligence, Find Comps,
   Comparable Outcomes (benchmark/corpus — belong in Research, callable from a deal).

→ The reform: **label tier-2 honestly (ILLUSTRATIVE / DATA REQUIRED)**, **wire
the HCRIS-derivable ones to real data** (Cost Structure & Debt Service are
computable from HCRIS fields), and **move/defer** the rest.

---

## PR log
| PR | Title | Scope | Status |
|---|---|---|---|
| 0 | docs(diligence): workspace audit + data-source matrix | docs only | **in progress** |
| 1 | feat(diligence): source-and-purpose headers (top pages) | visible UI | planned |
| 2 | feat(diligence): illustrative-state guardrails | visible UI | planned |
| 3 | feat(diligence): HCRIS X-Ray A-v2 results | visible UI | planned (#663 path) |
| 4 | feat(diligence): Payer Stress repair / honest source | visible UI | planned |
| 5 | feat(diligence): Cost Structure + Debt Service from HCRIS | visible UI | planned |
| 6 | feat(diligence): Checklist honesty + source-aware | visible UI | planned |
| 7 | feat(diligence): workforce/provider economics source pass | visible UI | planned |
| 8 | docs(diligence): defer/delete/move candidates | docs only | planned |

## Deferrals / notes
- (none yet)
