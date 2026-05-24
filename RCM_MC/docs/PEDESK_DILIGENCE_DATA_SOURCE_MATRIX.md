# PEdesk Diligence Data-Source Matrix

Defines what "LIVE" means and maps each illustrative analyzer to the real
source that could activate it. **No page may claim LIVE without a named,
traceable source.**

## Confidence labels (shown on every page header)
- **LIVE** — pulls from a real source; source named; values traceable; missing
  data handled; assumptions labeled; Guide can explain it.
- **DERIVED** — computed from real values (e.g. EBITDA gap = margin-gap × NPR).
- **ILLUSTRATIVE** — hardcoded demo values / fake scenarios / no findable source.
  Must say: *"Source not wired yet — illustrative until a real source is connected."*
- **DATA REQUIRED** — needs a user upload / CCD / internal file to activate.
- **EXPERIMENTAL** — real source exists but coverage/method is partial; caveated.

## Real sources available in PEdesk (no new runtime scraping)
| Source | Provides | Already wired |
|---|---|---|
| **HCRIS** (`diligence/hcris_xray`, `data/hcris`) | hospital revenue, opex, payer-day mix, margins, opex/bed, opex/pt-day, beds, peers | yes (HCRIS X-Ray) |
| **CMS Care Compare / vertical loaders** | provider identity, quality, staffing, ownership, penalties (HH/Hospice/SNF/Dialysis/IRF/LTCH) | yes (sector verticals) |
| **Benchmark corpus** | deal comps, multiples, deal type, realized outcomes | yes (Deal Corpus Analytics, Find Comps) |
| **User deal records** (`PortfolioStore`, `data.pipeline`) | pipeline stage, notes, IC packet, checklist, uploads | yes (Pipeline/Diligence workflow) |
| **IRS 990** (`data/irs990`) | non-profit exec comp, financials | partial |
| **CMS public datasets** (APM, Open Payments, Part B/D) | APM participation, payments | vendored loaders exist (`data/cms_*`) |

## Illustrative → real conversion map (priority order)
| Page | Real source it CAN use | Convertible now? |
|---|---|---|
| **Cost Structure** | HCRIS opex / opex-per-bed / opex-per-pt-day + peer band | **Yes** (PR 5) |
| **Debt Service** | HCRIS margin/NPR proxies + benchmark band (label proxy) | **Partial** (PR 5; label assumptions) |
| **Payer Stress** | HCRIS payer-day mix (medicare/medicaid/other) + peers | **Yes** (PR 4) |
| **CMS APM Tracker** | `data/cms_*` APM participation (public) | **Likely** (verify coverage) |
| **Physician Productivity** | CMS Part B / PECOS (if vendored) | DATA-REQ / verify |
| **Mgmt Comp** | IRS 990 exec comp (non-profits) | Partial / DATA-REQ |
| **Provider Retention/Churn** | needs a roster/turnover source (SNF PBJ for SNFs only) | DATA-REQ |
| **Partner Economics** | user-entered deal model | DATA-REQ |
| **Drug Shortage / Supply Chain** | FDA drug-shortage list (build-time vendor candidate) | needs vendoring |
| **Biosimilars / 340B / ESG / HCIT / Insurance** | no clear PEdesk source | defer/label until purpose+source defined |

## Rule of thumb
- If HCRIS or a vendored CMS loader can produce the number → **wire it (LIVE/
  DERIVED)** with the source named.
- Else → **ILLUSTRATIVE / DATA REQUIRED** label, no fake "data-backed" claim.
- Never fabricate payer mix, revenue, comps, or predictions to fill a page.
