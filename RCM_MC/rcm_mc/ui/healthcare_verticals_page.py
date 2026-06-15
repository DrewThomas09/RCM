"""Healthcare Verticals deep-dive — static reference report page.

Renders the US Healthcare Verticals Deep-Dive (PEDesk/RCM-MC Series)
as an editorial Library reference surface. The report profiles 19 US
healthcare verticals across codes, epidemiology, provider counts,
benchmarks, reimbursement regimes, and data sources.

The report body is embedded as a module-level string (not read from
disk) on purpose: the platform is offline-first and ships as a Python
package, so a packaged deploy that omits the repo `docs/` tree must
still render this page. The canonical source-of-truth document lives
at ``RCM_MC/docs/PEDESK_HEALTHCARE_VERTICALS_DEEP_DIVE.md``; keep the
two in sync when either changes.
"""
from __future__ import annotations

import html
import re

from ._chartis_kit import chartis_shell, ck_editorial_head, ck_kpi_block, ck_panel


def _md_inline(text: str) -> str:
    """Convert the inline-markdown subset used in the report to HTML.

    Escapes first (defence-in-depth even though the content is trusted
    server markup), then applies ``**bold**`` → ``<strong>``,
    ``*italic*`` → ``<em>`` (after bold so ``**`` is already consumed),
    and `` `code` `` → ``<code>``.
    """
    out = html.escape(text)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\*([^*\n]+?)\*", r"<em>\1</em>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return "hv-" + (s or "section")


def _render_report(md: str) -> tuple[str, list[tuple[str, str]]]:
    """Render the embedded report markdown to editorial HTML.

    Heading levels are demoted by one (``#`` → ``<h2>``) so the page
    keeps a single ``<h1>`` (emitted by ``ck_editorial_head``) — the
    one-h1 accessibility invariant the editorial kit enforces. Each
    former-``#`` section header gets an id anchor and a table-of-
    contents entry. Returns ``(body_html, toc)``.
    """
    lines = md.split("\n")
    parts: list[str] = []
    toc: list[tuple[str, str]] = []
    para: list[str] = []
    items: list[str] = []
    list_kind: str | None = None

    def flush_para() -> None:
        if para:
            text = " ".join(s.strip() for s in para).strip()
            if text:
                parts.append(f'<p class="hv-p">{_md_inline(text)}</p>')
            para.clear()

    def flush_list() -> None:
        nonlocal list_kind
        if items:
            tag = "ol" if list_kind == "ol" else "ul"
            body = "".join(f"<li>{_md_inline(x)}</li>" for x in items)
            parts.append(f'<{tag} class="hv-list">{body}</{tag}>')
            items.clear()
        list_kind = None

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            flush_para()
            flush_list()
            continue
        if set(stripped) == {"-"} and len(stripped) >= 3:
            flush_para()
            flush_list()
            parts.append('<hr class="hv-hr">')
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if m:
            flush_para()
            flush_list()
            level = len(m.group(1))
            text = m.group(2).strip()
            out_level = min(level + 1, 6)
            if level == 1:
                anchor = _slug(text)
                toc.append((anchor, text))
                parts.append(
                    f'<h{out_level} id="{anchor}" class="hv-h2">'
                    f'{_md_inline(text)}</h{out_level}>'
                )
            else:
                parts.append(
                    f'<h{out_level} class="hv-h{out_level}">'
                    f'{_md_inline(text)}</h{out_level}>'
                )
            continue
        m = re.match(r"^[-*]\s+(.*)$", stripped)
        if m:
            flush_para()
            if list_kind not in (None, "ul"):
                flush_list()
            list_kind = "ul"
            items.append(m.group(1).strip())
            continue
        m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if m:
            flush_para()
            if list_kind not in (None, "ol"):
                flush_list()
            list_kind = "ol"
            items.append(m.group(1).strip())
            continue
        if items:
            flush_list()
        para.append(stripped)

    flush_para()
    flush_list()
    return "".join(parts), toc


_EXTRA_CSS = """
.hv-body{max-width:64rem;}
.hv-body .hv-h2{font-family:'Source Serif 4',Georgia,serif;font-size:1.55rem;
  line-height:1.2;margin:2.2rem 0 .6rem;padding-top:1.4rem;
  border-top:1px solid rgba(11,35,65,.14);color:#0b2341;}
.hv-body .hv-h3{font-family:'Inter Tight',system-ui,sans-serif;font-size:1.15rem;
  margin:1.5rem 0 .4rem;color:#155752;font-weight:600;}
.hv-body .hv-h4,.hv-body .hv-h5,.hv-body .hv-h6{font-family:'Inter Tight',system-ui,sans-serif;
  font-size:1rem;margin:1.1rem 0 .3rem;color:#1a2332;font-weight:600;}
.hv-body .hv-p{line-height:1.62;margin:.55rem 0;color:#1a2332;}
.hv-body .hv-list{margin:.4rem 0 .9rem 1.3rem;line-height:1.55;color:#1a2332;}
.hv-body .hv-list li{margin:.28rem 0;}
.hv-body .hv-hr{border:none;border-top:1px solid rgba(11,35,65,.16);margin:1.7rem 0;}
.hv-body code{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:.85em;
  background:rgba(21,87,82,.08);padding:.05em .32em;border-radius:3px;}
.hv-toc-list{columns:2;column-gap:2rem;}
.hv-toc-list a{display:block;padding:.22rem 0;color:#155752;text-decoration:none;
  font-family:'Inter Tight',system-ui,sans-serif;font-size:.95rem;
  break-inside:avoid;}
.hv-toc-list a:hover{text-decoration:underline;}
@media (max-width:720px){.hv-toc-list{columns:1;}}
"""


def render_healthcare_verticals() -> str:
    """Render the Healthcare Verticals deep-dive reference page."""
    head = ck_editorial_head(
        eyebrow="LIBRARY · REFERENCE",
        title="Healthcare Verticals Deep-Dive",
        meta="19 VERTICALS · CODES · EPIDEMIOLOGY · BENCHMARKS · REIMBURSEMENT",
        lede_italic_phrase=(
            "Nineteen US healthcare verticals, profiled chart-ready across "
            "the same six dimensions."
        ),
        lede_body=(
            "Dental specialties, hospital sub-types, physician-organization "
            "structures, diagnostics &amp; biologics, and a veterinary cash-pay "
            "comparison &mdash; each covered by codes (CDT / CPT / MS-DRG / "
            "ICD-10 / NPPES taxonomy), epidemiology, provider counts, "
            "operational and financial benchmarks, reimbursement regime, and "
            "data sources, plus the 2025/2026 cross-cutting reimbursement "
            "updates."
        ),
        source_note=(
            "Source: PEDESK_HEALTHCARE_VERTICALS_DEEP_DIVE.md "
            "(ADA HPI, CMS, OPTN/UNOS, RHIhub, FDA, AVMA/Brakke, and others)"
        ),
        show_legend=False,
    )

    kpis = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Verticals Profiled", "19", sub="dental → veterinary")
        + ck_kpi_block("Active US Dentists", "202,485", sub="2024 · 59.5 / 100k")
        + ck_kpi_block("Organ Transplants", "48,149", sub="2024 · record · 132/day")
        + ck_kpi_block("Critical Access Hospitals", "1,367", sub="July 2024 · 45 states")
        + ck_kpi_block("Rural Emergency Hospitals", "42", sub="Oct 2025 · since 2023")
        + ck_kpi_block("2026 PFS Conversion Factor", "$33.40", sub="non-QP · +3.26%")
        + "</div>"
    )

    body_html, toc = _render_report(_REPORT_MD)

    toc_links = "".join(
        f'<a href="#{anchor}">{html.escape(title)}</a>' for anchor, title in toc
    )
    toc_panel = ck_panel(
        f'<div class="hv-toc-list">{toc_links}</div>', title="Contents"
    )

    body = (
        head
        + kpis
        + toc_panel
        + f'<div class="hv-body">{body_html}</div>'
    )

    return chartis_shell(
        body_html=body,
        title="Healthcare Verticals Deep-Dive",
        active_nav="/healthcare-verticals",
        breadcrumbs=[
            {"label": "Library", "href": "/methodology"},
            {"label": "Healthcare Verticals", "href": "/healthcare-verticals"},
        ],
        extra_css=_EXTRA_CSS,
    )


# ── Embedded report (from TL;DR onward; the report title + subtitle are
#    carried by the editorial masthead above). Keep in sync with
#    RCM_MC/docs/PEDESK_HEALTHCARE_VERTICALS_DEEP_DIVE.md. ──
_REPORT_MD = r"""
**TL;DR**

- This report profiles 19 US healthcare verticals across codes, epidemiology, provider counts, access, operational/financial benchmarks, reimbursement, and data sources — all structured chart-ready. Anchor facts: ~202,485 active US dentists (59.5/100,000, 2024); 48,149 organ transplants in 2024 (first year ever above 48,000; 132/day); 1,367 Critical Access Hospitals (July 2024); 42 Rural Emergency Hospitals (Oct 2025); 2026 PFS conversion factor $33.40 (non-QP).
- The dental specialties are predominantly cash-pay/financed (orthodontics ~$5,000–5,500 average case) or insurance-crossover (oral surgery), while hospital sub-types live or die on government payer mix (children's hospitals ~50%+ Medicaid; CAHs on 101% cost-based reimbursement; REHs on a $285,625.90/month facility payment plus OPPS+5%).
- Diagnostics/biologics verticals are governed by distinct payment regimes (MolDX/Z-codes for molecular tests; CLFS; IPF-PPS at $892.87/day for FY2026 psychiatric care; transplant cost reporting), and veterinary medicine provides an instructive cash-pay contrast (per Brakke Consulting's John Volk at NAVC's 2026 VMX: ~2.5% revenue growth in 2025 even as visits fell ~3%, a four-year trend, with 81% of vets reporting clients more cost-sensitive than in 2024).

-----

# KEY FINDINGS

1. **Dental specialties split cleanly by payment model.** Orthodontics, endodontics, and (largely) general dentistry are cash/financed or commercial-PPO; oral & maxillofacial surgery uniquely straddles medical and dental insurance (cross-coding D7240→CPT); pediatric dentistry is Medicaid/CHIP-dominated. CDT codes are the operational currency throughout.
1. **Rural hospital policy is the most dynamic facility story.** 152 rural hospitals closed/dropped inpatient care 2010–Oct 2025; the new REH designation (effective 2023) had only 42 conversions by Oct 2025 despite ~389 candidates, with the loss of 340B and swing-bed revenue the key disincentives.
1. **Transplantation hit an all-time record** (48,149 in 2024) but demand vastly outstrips supply (kidney waitlist 89,792 alone in Sept 2024).
1. **Molecular diagnostics reimbursement is structurally unstable** — MolDX/Z-code gatekeeping, PAMA/CLFS pressure, and a Feb 2026 CMS RFI on national MolDX expansion.
1. **Veterinary medicine is the instructive cash-pay mirror** — corporatized (Mars owns 2,000+ hospitals), low insurance penetration (~2%), and now showing demand softening as fees outpace inflation.

-----

# GROUP A — DENTAL SPECIALTIES

## Baseline: General Dentistry & DSO Operations

**(a) Codes:** D0120 (periodic oral eval), D0150 (comprehensive eval), D0210 (full-mouth X-ray series), D0220 (periapical), D1110 (adult prophylaxis), D1120 (child prophylaxis), D1208 (fluoride), D2391–D2394 (posterior composites), D2740 (porcelain crown), D2750 (PFM crown), D2950 (core buildup). Taxonomy: 122300000X (Dentist), 1223G0001X (General Practice).

**(b) Population/epidemiology:** Dental care touches the majority of the US population annually; hygiene recall (6-month prophylaxis) is the backbone visit. ~65% of privately insured children had a dental visit in 2023 vs. 42% publicly insured (ADA HPI).

**(c) Providers/workforce:** 202,485 professionally active US dentists in 2024; 59.5 dentists per 100,000 (range 40.2 Arkansas to 103.2 DC); 21.2% report a recognized specialty; 39.6% female (ADA HPI, "U.S. Dentist Workforce – 2025 update"). DSO affiliation: 16.1% of US dentists in 2024, more than doubled since 2015 (7.4%→8.8%→10.4%→13%→13.8%→16.1%); 27% of early-career dentists (≤10 yrs) DSO-affiliated vs 9% of those >25 years out (ADA HPI).

**(c2) Access:** Dental Health Professional Shortage Areas (dental HPSAs) are tracked by HRSA; rural and low-income areas chronically under-served. 41% of US dentists participate in Medicaid/CHIP (2024, ADA HPI), roughly flat since 2015.

**(d) Benchmarks:** Average dental practice overhead 60–65% of collections (ADA-cited). Category breakdown (industry benchmarks): staff/payroll ~25–30% (largest), clinical supplies ~5–8%, lab fees ~5–8%, facility ~7–10%. Overhead scales inversely with size (<$750K collections ~70–80%; >$1.5M under 60%). Average GP net income $207,980 (2024); specialists $338,900; average gross billings $942,290 (GP), $1,146,320 (specialists); 2025 GP income $215,320 (ADA HPI Survey of Dental Practice).

**(e) Reimbursement:** CDT fee schedules; commercial dental PPO, Medicaid (variable, often <50% of charges), and cash. No Medicare dental except limited medically-necessary services.

**(f) Data sources:** ADA Health Policy Institute (Survey of Dental Practice, US Dentist Workforce), BLS OEWS, CMS T-MSIS, MEPS.

**Viz:** DSO penetration 2015–2024 → line; overhead breakdown → stacked bar/pie; GP vs specialist income → bar.

## 1. Orthodontics

**(a) Codes:** D8010–D8090 (comprehensive ortho by dentition: D8070 transitional, D8080 adolescent, D8090 adult), D8210/D8220 (removable/fixed appliance), D8660 (pre-ortho visit), D8670 (periodic ortho treatment visit), D8680 (debanding/retainer). ICD-10: M26.x (dentofacial anomalies/malocclusion), e.g., M26.211 crowding. Taxonomy: 1223X0400X (Orthodontics).

**(b) Population/epidemiology:** ~6.66 million total patients in active treatment among AAO members (US+Canada, 2024). Adults are 25% of treatments (1 in 4). Children typically begin ages 10–14; AAO recommends first evaluation by age 7. ~1 million Americans over 18 visit orthodontists annually (ADA Survey of Dental Fees, cited).

**(c) Providers/workforce:** ~10,830 orthodontists licensed (2024, ADA via Statista); AAO represents ~19,000 members (US+Canada+abroad); 9,554-member AAO Active/Life Active database used for population estimates.

**(d) Benchmarks:** Per-member active patient count reached record 696 in 2024 (up from 574 in 2022) — highest in the 38-year survey history. ~28,000 patients started treatment via AAO "Find an Orthodontist" tool in 2024; ~44,000 examined. Average case value ~$5,500. Conversion (case acceptance) rate 64–68% (Gaidge 68%, Planet DDS 64.4%). Treatment duration 10–20 months typically. Solo-practice healthy range 15–30 new exams/month.

**(e) Reimbursement:** Predominantly cash-pay/financed (interest-free in-house payment plans, 12–36 months). Insurance lifetime ortho max commonly ~$1,000–$3,000 (OrthoFi 2021 data: average coverage $1,772; 92% qualify up to $3,000). Clear aligners national average ~$5,108 (range $1,800–$8,100); braces $3,000–$8,000.

**(f) Data sources:** AAO Economics of Orthodontics and Patient Census Survey, Planet DDS Dental Industry Outlook, Gaidge Analytics, ADA HPI.

**Viz:** Case starts/exams 2018–2024 → bar; per-member patient count trend → line; case value vs conversion sensitivity → bar; aligner cost range → box/range plot.

## 2. Oral & Maxillofacial Surgery

**(a) Codes:** Extractions — D7140 (erupted tooth), D7210 (surgical, bone removal), D7220 (soft tissue impaction), D7230 (partial bony), D7240 (complete bony), D7241 (complete bony w/ complications), D7250 (residual roots), D7251 (coronectomy). Implants — D6010 (surgical placement endosteal implant), D6056/D6057 (abutments), D6058 (abutment-supported crown). Anesthesia — D9222/D9223 (deep sedation/GA first 15 min/each addl 15), D9230 (nitrous), D9239/D9243 (IV moderate sedation). Cross-coded CPT: 00170 (anesthesia intraoral), 99152 (moderate sedation). ICD-10: K01.1 (impacted teeth), M26.31 (crowding). Taxonomy: 1223S0112X (Oral & Maxillofacial Surgery).

**(b) Population/epidemiology:** Third-molar extraction is likely the most common surgery in US adolescents/young adults. Per Friedman JW, "The Prophylactic Extraction of Third Molars: A Public Health Hazard," *Am J Public Health*: "Ten million third molars (wisdom teeth) are extracted from approximately 5 million people in the United States each year at an annual cost of over $3 billion." ~50% of patients undergo ≥1 third-molar (3M) extraction by age 25; ~80% have ≥1 extraction of any tooth by 25 (MarketScan Dental Database, 2007–2016). Female sex (aHR 1.08) and residence in West (aHR 1.82) or South (aHR 1.5) associated with higher 3M extraction vs Northeast. Wisdom teeth typically extracted ages 17–25.

**(c) Providers/workforce:** ~7,529 OMS (ADA Masterfile 2020); AAOMS membership "over 7,000."

**(e) Reimbursement:** Medical/dental insurance crossover is the defining operational feature. Medical plans often require dental denial first ("dental first" rule); D7240 requires documentation of bony encasement (panoramic/CBCT) or claims down-code to D7220. Letters of Medical Necessity speed approval. Cash, dental PPO, and medical cross-coding.

**(f) Data sources:** AAOMS White Paper on Third Molars (2016, updated 2024), IBM MarketScan Dental Database, ADA CDT, Aetna/UHC dental clinical policies.

**Viz:** Cumulative 3M extraction incidence by age (Kaplan-Meier) → line; extraction codes by impaction type → bar; regional variation → choropleth.

## 3. Endodontics

**(a) Codes:** D3310 (anterior root canal), D3320 (premolar/bicuspid), D3330 (molar), D3331 (root canal obstruction, non-surgical), D3332 (incomplete, inoperable), D3346 (retreatment anterior), D3347 (retreatment premolar), D3348 (retreatment molar), D3410/D3421/D3425 (apicoectomy), D3220 (therapeutic pulpotomy). Supporting: D2950 (core buildup), D2954 (post and core), D0140 (limited exam), D0220 (periapical). Taxonomy: 1223E0200X (Endodontics).

**(d) Benchmarks/economics:** Anterior root canal (D3310) without insurance ~$500–$900; total with crown $1,500–$2,800. Endodontists charge 15–50% more per line than general dentists (widest gap on molars/retreatments). Retreatment (D3346–D3348) ~$900–$2,000. Most plans cover RCT 50–80% as basic/major after deductible. Billing date = date of obturation; code by tooth type, not canal count.

**(c) Providers:** ~5,745 endodontists (ADA Masterfile 2020); AAE membership "over 8,000."

**(f) Data sources:** AAE Endodontists' Guide to CDT, ADA CDT 2025, FAIR Health, Delta Dental fee data.

**Viz:** Root canal cost by tooth type (D3310/D3320/D3330) → bar; line-item stack (exam, RCT, buildup, crown) → stacked bar; GP vs endodontist fee premium → grouped bar.

## 4. Periodontics

**(a) Codes:** D4341 (scaling & root planing, 4+ teeth/quadrant), D4342 (SRP, 1–3 teeth/quadrant), D4346 (scaling w/ generalized moderate-severe gingival inflammation, no bone loss), D4210/D4211 (gingivectomy), D4240/D4241 (gingival flap), D4260/D4261 (osseous surgery), D4910 (periodontal maintenance), D1110 (prophylaxis). Implants D6010. Taxonomy: 1223P0221X (Periodontics).

**(b) Epidemiology:** Per Eke PI et al., "Periodontitis in US Adults: National Health and Nutrition Examination Survey 2009–2014," *J Am Dent Assoc* 2018;149(7):576-588: "Overall, 42.2%…of adults 30 years or older in the United States had total periodontitis, consisting of 7.8% with severe periodontitis and 34.4% with nonsevere periodontitis" (≈61 million adults, per NIDCR). SRP indicated for pocket depths >4mm, bleeding on probing, radiographic bone loss.

**(c) Providers:** ~5,723 periodontists (ADA Masterfile 2020); AAP represents ~8,200 members (~90% of US periodontists).

**(d/e) Benchmarks/reimbursement:** D4341 distinct from prophylaxis (D1110) and D4346. Reporting SRP in >2 quadrants in one visit triggers documentation requests (full-mouth perio charting, X-rays, diagnosis, treatment plan). Many payers limit SRP to 2 quadrants per date of service. Documentation: 6-point pocket charting per tooth + bleeding on probing.

**(f) Data sources:** AAP, CDC NHANES periodontal surveillance (Eke et al.), ADA CDT, payer dental CPBs (Aetna DCPB041).

**Viz:** Adult periodontitis prevalence by severity (severe 7.8% / non-severe 34.4%) → stacked bar; SRP code-selection logic → decision/funnel.

## 5. Pediatric Dentistry

**(a) Codes:** D0145 (oral eval <3 yr), D1120 (child prophylaxis), D1206/D1208 (fluoride), D1351 (sealant), D2930/D2931 (stainless-steel crowns primary/permanent), D3220 (pulpotomy), pulpectomy primary teeth, sedation D9230/D9222/D9223. Taxonomy: 1223P0700X (Pediatric Dentistry).

**(b) Epidemiology:** Medicaid/CHIP cover ~half of US children; nearly half of Medicaid/CHIP children receive ≥1 dental service/year (KFF/T-MSIS). 38% of children 0–18 have Medicaid/CHIP dental benefits; 42% of publicly insured children had a dental visit in 2023 vs 65% privately insured (ADA HPI). Pediatric dentist count grew 121% since 2001 (ADA HPI).

**(c) Providers:** ~8,561 pediatric dentists (ADA Masterfile 2020); AAPD membership "over 10,000."

**(e) Reimbursement:** Heavily Medicaid/CHIP-dependent (payer mix the defining feature); Medicaid FFS reimbursement below 50% of charges, ~60% of private in most states. Sedation/GA for young/uncooperative patients adds significant per-case cost.

**(f) Data sources:** ADA HPI, AAPD, CMS T-MSIS, KFF, CMS-416 EPSDT reports.

**Viz:** Pediatric dental visit rate by coverage (private/Medicaid/uninsured) → bar; Medicaid pediatric dental utilization trend → line.

-----

# GROUP B — HOSPITAL & FACILITY SUB-TYPES

## 7. Critical Access Hospitals (CAHs)

**(a) Codes:** Bill types 11x (inpatient), 85x (CAH outpatient); revenue codes for facility services; CAH services settled on cost report (CMS-2552). MS-DRGs NOT used for CAH payment (cost-based).

**(b/c) Counts/role:** 1,367 CAHs across 45 states as of July 2024 (>1,350 commonly cited). Highest concentrations in Midwest, Great Plains, Mountain West. Nearly all participate in MBQIP.

**(c2) Access:** Statutory location: >35-mile drive from another hospital/CAH (or >15 miles in mountainous/secondary-road terrain), unless grandfathered "necessary provider" pre-2006. 24/7 emergency care with provider on-site or available within 30 min (60 in frontier). OIG found 87 of 100 sampled CAHs within 35 miles of an alternative SNF facility (estimating 1,128 of 1,297 in the sampling frame).

**(d) Structure/benchmarks:** Max 25 inpatient beds; average annual acute LOS ≤96 hours. Swing beds (acute or SNF-equivalent). Up to 10 psychiatric + rehab distinct-part beds not counted in the 25. Total margins for rural CAHs ranged -20.5% to 28.0% in 2022–2023 (NC Rural Health Research Program).

**(e) Reimbursement:** 101% of reasonable cost for inpatient, outpatient, swing-bed (Section 1834(g)). MedPAC notes CAHs may not get full 101% due to sequestration. Optional Method II: facility cost + 115% of PFS for professional. Psychiatric distinct-part units paid under IPF-PPS. MA growth erodes the cost-based model (was 14% MA at program inception). Effective Jan 1, 2026, CAHs offering OB must meet new staffing requirements.

**(f) Data sources:** CMS MLN006400, Flex Monitoring Team CAH Financial Indicators Report, NC Rural Health Research Program, RHIhub, HHS OIG.

**Viz:** CAH count by state → choropleth; total margin distribution → box plot; cost-based vs PPS payment → comparison bar.

## 8. Children's Hospitals

**(b/d) Population/case mix:** Provide care for nearly half of all hospitalized children and the majority with chronic/complex conditions. Children with medical complexity (CMC) = 6% of pediatric Medicaid population but 40% of Medicaid pediatric spend; at pediatric academic medical centers, CMC may be up to 80% of total hospital days. Kids' Inpatient Database: 26,342,497 pediatric discharges 2000–2022, with rising share attributable to complex chronic conditions.

**(c) Counts:** Children's Hospital Association represents "more than 200 children's hospitals" (includes some international members).

**(e) Reimbursement:** Medicaid covers ~half of children's hospital patients (closer to three-quarters at some); Medicaid pays <80% of cost of care. GME via Children's Hospitals GME (CHGME) Payment Program (HRSA, since freestanding children's hospitals aren't paid under IPPS). Psychiatric hospitals, REHs, and children's hospitals have higher-than-average Medicaid share.

**(f) Data sources:** Children's Hospital Association, HCUP Kids' Inpatient Database (KID), HRSA CHGME, CMS.

**Viz:** Payer mix → stacked bar; CMC share of spend vs population → grouped bar; complex chronic condition discharge trend → line.

## 9. Academic Medical Centers / Teaching Hospitals

**(a/d) Mission/case mix:** Tripartite mission (clinical care, research, education). Higher case-mix index (CMI) than community hospitals reflecting acuity.

**(c) Counts:** AAMC network includes ~400 major teaching hospitals (former COTH, renamed Council of Academic Health System Executives/CAHSE as of July 1, 2024); 156 medical schools.

**(e) Reimbursement — GME/IME/340B:** Medicare GME = Direct GME (DGME, "pass-through") + Indirect Medical Education (IME, IPPS add-on per discharge based on resident-to-bed ratio). FY2020: Medicare paid $4.5B DGME and ~$11.68B IME, supporting 98,542 FTEs. FTE caps frozen at 1996 levels (BBA 1997); per-resident amounts based on 1984/85 base years updated by CPI-U. DSH payments and 340B drug discounts (covered-entity disproportionate share) are key margin supports for safety-net AMCs.

**(f) Data sources:** AAMC, CMS cost reports, AMA GME Compendium, Congress.gov CRS (IF10960, IF13088).

**Viz:** GME funding DGME vs IME → bar; CMI comparison AMC vs community → bar; resident FTEs over time → line.

## 10. Rural Hospitals & Rural Emergency Hospitals (REHs)

**(b/c) Closures/counts:** 152 rural hospitals closed or stopped inpatient services Jan 2010–Oct 2025 (NC Rural Health Research Program). A Feb 2025 Chartis report identified 432 financially vulnerable rural hospitals at risk of closing. Feb 2023 Chartis: 389 rural hospitals may consider REH conversion, 77 "ideal candidates."

**REH designation:** Effective Jan 1, 2023 (CAA 2021). 42 REHs as of October 2025. 21 converted in first year. Eligibility: CAHs or rural hospitals ≤50 beds as of Dec 27, 2020. OBBBA (July 2025) broadened eligibility to hospitals operating Jan 1, 2014–Dec 26, 2020 that later closed.

**(d) Requirements:** 24/7 emergency + observation; no inpatient beds (except distinct-part SNF); annual per-patient average LOS ≤24 hours.

**(e) Reimbursement:** Monthly facility payment $285,625.90 (CY2025; >$3.4M annually), updated by hospital market basket; OPPS rate +5% for outpatient services (no beneficiary coinsurance on the 5%). NOT eligible for 340B or Method II billing — a key conversion disincentive (forgoing 25–50% drug savings). NCRHRP REH candidate predictors: 3 yrs negative total margin; ADC (acute+swing) <3; net patient revenue <$20M.

**(f) Data sources:** RHIhub, CMS (REH final rule, 42 CFR 419 Subpart J), NC Rural Health Research Program, Chartis, MedPAC.

**Viz:** Rural hospital closures 2010–2025 → line; REH count growth → line; REH vs CAH payment structure → comparison table/bar.

-----

# GROUP C — PHYSICIAN ORGANIZATION & CARE-MODEL STRUCTURES

## 11. MSOs and IPAs

**Structure:** MSO = non-clinical entity handling billing, HR, IT, compliance, credentialing, payer contracting, and facilities under a Management Services Agreement (MSA). IPA = network of independent physicians contracting collectively with health plans (capitation, flat retainer, or negotiated FFS), preserving independence.

**Friendly-PC model:** Complies with Corporate Practice of Medicine (CPOM) laws (majority of states) — a physician-owned PC/PLLC employs clinicians; the MSO (may be non-physician/investor-owned) provides services. A stock transfer restriction agreement keeps the PC "friendly." Fee structures: fixed fee, cost-plus, or % of revenue (% may violate fee-splitting laws, e.g., NY). Admin tasks consume 10–20 hrs/week for a typical primary care practice.

**(d) Evidence:** Health Affairs study (1,164 practices): IPA/group providers delivered ~3× the care-management processes for chronic conditions (10.45% vs 3.85%). Minimum viable group ~6 providers.

**(f) Data sources:** Definitive Healthcare, Health Affairs, state CPOM statutes, MGMA.

**Viz:** MSO-PC entity structure → flow diagram; admin hours saved → bar.

## 12. Direct Primary Care (DPC) & Concierge Medicine

**(b/c/d) Model:** DPC = insurance-free monthly membership ($50–$100/mo typical), panels 600–800 (some cite 300–600). Concierge = annual retainer ($1,500–$25,000+/yr; commonly $100–$200/mo), often still bills insurance, panels 300–600. As of 2023, ~10% of AAFP members surveyed were in DPC (up from 5% in 2021). DPC family physician average full-time income $288,779 (2024, AAFP Career Benchmark). 94% of DPC physicians satisfied vs 57% non-DPC; 49% report no burnout vs 14%. Startup $5,000 (low-overhead) to $100,000+. Common procedures: EKGs.

**(e) Reimbursement:** Membership/retainer; not insurance-billed for primary care (DPC). Concierge may "double-dip" (membership + insurance). Medicare opt-out considerations for DPC.

**(f) Data sources:** AAFP DPC data brief (2024), DPC Frontier, Concierge Medicine Today.

**Viz:** DPC vs concierge fee/panel comparison → grouped bar; DPC adoption among AAFP members → line; physician satisfaction/burnout → bar.

## 13. Retail Health, Worksite/Employer & School-Based Clinics

**Model:** On-site (at employer) and near-site convenient-care clinics; retail clinics (in pharmacies/big-box); school-based health centers (SBHCs). Convenient-care emphasizes walk-in, lower-acuity, transparent pricing. **Note:** Provider counts (retail clinic count, SBHC count, worksite clinic count) were not retrieved within research budget and require verification from the School-Based Health Alliance census, the Convenient Care Association, and the National Association of Worksite Health Centers (NAWHC).

**(f) Data sources:** School-Based Health Alliance census, NAWHC, Convenient Care Association.

**Viz:** Clinic counts by type → bar (pending sourcing).

-----

# GROUP D — DIAGNOSTICS, BIOLOGICS & SPECIALIZED SERVICES

## 14. Genetic & Molecular Diagnostics / Precision Medicine

**(a) Codes:** Molecular CPT Tier 1 (81162 BRCA1/2, 81235 EGFR, etc.), Tier 2 (81400–81408), genomic sequencing procedures (81445 targeted 5–50 genes solid tumor, 81455 50+ genes), 81459/81479 (comprehensive genomic profiling, unlisted molecular) + DEX Z-Code, PLA codes (e.g., 0037U), 87798 (infectious agent molecular, catchall). MolDX DEX Z-Codes (5-char alphanumeric). ICD-10 Z-codes for genetic susceptibility.

**(b) Pathways:** Germline (hereditary) and somatic (tumor) testing; liquid biopsy; companion diagnostics; NGS panels (targeted "hotspot" vs comprehensive genomic profile).

**(e) Reimbursement — MolDX/Z-codes:** MolDX program (Palmetto GBA, est. 2011) provides uniform policies across 4 MACs (Palmetto, Noridian, WPS, CGS) covering 28 states. Labs register tests in the DEX Diagnostics Exchange → unique Z-Code → Technical Assessment → coverage + pricing. CGP billed with 81459/81479 + Z-Code (limited to 1 test per surgical specimen). MolDX functions as a "prior authorization surrogate." Commercial payers (UnitedHealthcare, Humana) use DEX/Z-code nationwide. PAMA drives CLFS instability. CMS RFI (Feb 27, 2026) on national MolDX expansion; 87798 denial spike since mid-Feb 2026. OIG flagged $888M improper payment risk on CPT 81408 (2023 audit).

**(f) Data sources:** CMS MolDX LCDs/articles (A55197, A54901), Palmetto GBA DEX, AMP "Molecular Pathology Economics 101," CMS CLFS.

**Viz:** Molecular test claim volume by jurisdiction → bar; Z-code workflow → flow; germline vs somatic vs liquid biopsy → categorical.

## 15. Blood & Plasma

**(b/c/d) Blood banking:** FDA/CBER oversees ~11 million units of whole blood donated/year (FDA); Red Cross cites 13.6M units whole blood/RBC collected, ~6.8M donors annually; ~29,000 RBC units needed daily; ~16M components transfused/year. ~180 blood centers (~45 ARC, rest community); America's Blood Centers members supply 60% of US blood and serve 3,500+ hospitals. ~4M apheresis platelet/plasma units collected/year.

**Source plasma:** >40 million source-plasma collections/year for further manufacturing (immune globulins, albumin) (FDA). 800+ plasma donation centers. FDA allows donation up to 2×/week (24-hr gap), up to 104/year. Donor compensation historically $15–$20/donation (older NCBI/ABRA figure); ~$500/month commonly cited now. Plasma industry historically employed >12,000 (ABRA). Plasma is ~55% of blood; donation 690–880 mL by weight.

**(f) Data sources:** FDA CBER, AABB, America's Blood Centers, Red Cross, ARCNET, NCBI.

**Viz:** Whole blood vs apheresis vs source plasma collections → bar; plasma center growth → line; blood type distribution → pie.

## 16. Organ Transplantation

**(b/c/d) Volumes:** Per the UNOS announcement (Jan 15, 2025, OPTN preliminary data): 2024 was "the first time the United States has ever performed more than 48,000 organ transplants in one year" — 48,149 total, a 132/day average and a 3.3% increase over 2023, made possible by 16,988 deceased donors and 7,030 living donors. Of these, 41,119 were deceased-donor + 7,030 living-donor transplants. By organ growth: lung 3,026→3,340 (+10.4%); female liver transplants 4,721 (+12.4%, after a July 2023 policy change). Waitlist (Sept 2024): kidney 89,792, liver 9,424, heart 3,456, lung 898, pancreas 850, kidney/pancreas 2,177; >100,000 total candidates, ~61,671 active. DCD donors 7,280 (+23.5%); brain-death donors 9,706 (-7%, first decrease since 2013).

**Graft survival:** ~95% kidney graft function at 1 yr, ~80% at 5 yr; pancreas ~80% at 1 yr, 55–60% at 5 yr.

**Ecosystem:** OPTN (operated by UNOS under HRSA contract); OPOs (organ procurement organizations) in DSAs; SRTR analytics. Kidneys preservable up to 36 hrs. New mandatory IOTA (Increasing Organ Transplant Access) model — ~half of DSAs and their kidney transplant hospitals; organ-offer acceptance ratio a key metric.

**(e) Reimbursement:** Transplant cost reporting (Medicare cost-based for organ acquisition); DRGs for transplant admission; lifelong immunosuppression (J-codes/Part B/D). Incentive to accept harder-to-place kidneys (estimated to potentially prevent ~4,000 deaths).

**(f) Data sources:** OPTN/UNOS, SRTR Annual Data Report (700+ figures), HRSA, USRDS (kidney), organdonor.gov.

**Viz:** Waitlist vs transplants by organ → grouped bar; transplants 2013–2024 → line; deceased vs living donor → stacked bar; graft survival curves → line.

## 17. Medical Imaging Modalities

**(a) Codes:** CT 70450–70498/71250/74150; MRI 70551–70559/72148/73721; ultrasound 76700–76857/93306 (echo); nuclear medicine 78xxx; PET 78811–78816. Professional component modifier -26; technical component -TC. APCs under OPPS.

**(b/d) Volumes:** ~80M+ CT scans/year US (Harvard Health); ~40M MRI/year US; ~2.22M PET scans (2020). US ranks 1–2 globally in CT/MRI per capita. JAMA (Smith-Bindman et al. 2019): 135M imaging exams across 7 US systems + Ontario; CT growth slowed (11.6%→3.7% annual for adults), MRI slowed (11.4%→1.3%). ~30%+ of imaging may be unnecessary (~$30B/yr, estimate). MRI volume 39M (2016)→36M (2017) by facility type (Statista).

**(c) Workforce:** Radiologic technologists ~228,000 jobs (2024, BLS, median wage $77,660); MRI technologists ~44,100 (median $88,180).

**(e) Reimbursement:** Professional/technical split; OPPS (hospital outpatient), PFS (non-facility/imaging center, technical). CY2026 OPPS requires hospitals to publish 10th/50th/90th percentile allowed amounts.

**(f) Data sources:** BLS OEWS, JAMA/Smith-Bindman, Medicare claims, IMV Medical Information Division.

**Viz:** Scan volume by modality → bar; CT/MRI growth rate over time → line; professional vs technical split → stacked bar.

## 18. Behavioral Health Sub-Segments

**(a) Codes:** Inpatient psych MS-DRGs 880–887; CPT 90791/90792 (psych eval), 90832–90838 (psychotherapy), 90870 (ECT), H0035 (PHP per diem), S9480/S0201 (IOP), revenue codes 0124/0126/0912/0913. IPF bill type 11x. ICD-10 F-codes; eating disorders F50.x.

**(d/e) IPF-PPS:** Per CMS FY2026 IPF PPS Final Rule (CMS-1831-F, Federal Register Aug 5, 2025): FY2026 federal per diem base rate $892.87 (up from FY2025 $876.53; $875.44 for non-reporters), reflecting a 2.5% net update (3.2% 2021-based market basket − 0.7 productivity); ECT per treatment $673.85; fixed-dollar-loss outlier threshold $39,360. FY2025 base rate was $876.53 (down from $895.63 FY2024 due to refinement standardization). Patient-level adjustments (MS-DRG, age, comorbidities, variable per diem); facility adjustments (wage index, 17% rural, teaching, ED presence, AK/HI COLA). IPFQR non-reporting = -2.0 ppt.

**Sub-segments:** Eating disorder treatment, residential treatment centers (RTC), IOP, PHP, inpatient psychiatric hospitals. CAHs may have up to 10 psych beds (paid IPF-PPS, not cost-plus). CAHs bill IOP on TOB 85x at 101% cost with condition code 92.

**(f) Data sources:** CMS IPF-PPS final rules (FY2025 CMS-1806-F, FY2026 CMS-1831-F), SAMHSA N-SUMHSS facility survey, 42 CFR 412 Subpart N.

**Viz:** IPF per diem base rate trend FY2024–2027 → line; care continuum (inpatient→PHP→IOP→outpatient) by intensity → funnel; ECT payment trend → line.

-----

# GROUP E — COMPARISON VERTICAL

## 19. Veterinary Medicine

**(b/c/d) Market structure:** 28,000–32,000 US veterinary practices (2017 AVMA). ~3,500 company-owned (Brakke). ~40+ corporate veterinary groups. Corporations own ~10% of general companion-animal practices, 40–50% of referral/specialty practices. Mars Veterinary Health owns 2,000+ hospitals (Banfield >1,050 in 42 states + DC + PR, >3,400 associate vets; plus BluePearl, VCA, Pet Partners). Practice-acquisition minimum revenue threshold commonly $1.3M (VCA) for multi-doctor practices; high-water mark 2021 at 18–20× earnings.

**Economics (2025):** Per Brakke Consulting senior consultant John Volk at NAVC's 2026 VMX (Jan 19, 2026, reported by AVMA): "veterinary practices saw revenue increases of about 2.5% in 2025 even as visits were down roughly 3%, continuing a four-year trend"; 81% of surveyed vets reported clients more cost-sensitive than in 2024 (vs 72% in 2024); ~two-thirds reported revenue increases, 22% reported declines; ~10% of owners are considering selling. Diagnostics top the list of most-refused services.

**Pet insurance:** ~2.4M insured dogs/cats in 2018 (~2% of pet population, NAPHIA); vs ~25% UK penetration. Insured clients visit ~2× as often.

**(e) Reimbursement:** Cash-pay/client-paid + growing pet insurance (reimbursement model, not direct pay). No government payer.

**(f) Data sources:** AVMA (Report on Economic State of Veterinary Profession, market research), Brakke Consulting, NAPHIA, dvm360.

**Viz:** Corporate vs independent ownership by practice type → stacked bar; revenue vs visit trend → dual-axis line; pet insurance penetration US vs UK → bar; per-practice economics → bar.

-----

# Cross-Cutting 2025/2026 Reimbursement Updates

- **PFS conversion factor 2026:** $33.40 (non-qualifying APM; +3.26% from 2025's $32.35); $33.57 (qualifying APM) — first year with two factors (CMS CY2026 PFS Final Rule, CMS-1832-F, Oct 31 2025).
- **OPPS/ASC 2026:** +2.6% update; OPPS conversion factor $90.970; 340B recoupment -0.5% to CF (CMS-1834-FC, Nov 21 2025).
- **REH:** $285,625.90/month facility payment (CY2025); OPPS+5%.
- **IPF-PPS FY2026:** $892.87/day base; ECT $673.85; outlier threshold $39,360.
- **MolDX:** national-expansion RFI Feb 2026; CPT 87798 denials rising.
- **GME:** FTE caps frozen at 1996; FY2020 $4.5B DGME + $11.68B IME (98,542 FTEs).

-----

# Recommendations

1. **Build charts first where data is robust and current:** transplant waitlist-vs-transplants (OPTN, annual), CAH/REH counts and payments (CMS/RHIhub), orthodontic case economics (AAO 2024), IPF-PPS rate trends (CMS final rules). These have authoritative, recent, unambiguous numbers and will render cleanly.
1. **Flag and verify thinner data series before publishing visualizations:** retail/worksite/SBHC clinic counts (not yet sourced — pull from School-Based Health Alliance, Convenient Care Association, NAWHC); exact specialty-dentist counts (cleanest single source is ADA Masterfile 2020 — society membership numbers overstate "practicing"). Treat the ~5M wisdom-teeth (Friedman/APHA), ~$30B unnecessary-imaging, and plasma compensation figures as estimates.
1. **Benchmark thresholds that should trigger updates:** a new OPTN/SRTR Annual Data Report with 2025 transplant data → refresh Group D; CMS finalizing national MolDX expansion → materially rewrite the molecular-diagnostics reimbursement section; REH count crossing ~50 or rural closures accelerating → update Group B; the CY2027 PFS/OPPS/IPF rules → refresh the cross-cutting section.
1. **For per-unit-economics tables, separate cash-pay verticals (orthodontics, DPC/concierge, veterinary) from cost-based/PPS verticals (CAH, REH, IPF, children's hospitals).** The chart logic and payer-mix stacked bars differ fundamentally — cash-pay verticals chart best as price-range/case-value bars, PPS verticals as fee-schedule/per-diem and payer-mix stacks.
1. **Prioritize the codes (dimension a) as the join key** across the analytics platform: CDT for dental, MS-DRG/APC for facilities, molecular CPT+Z-code for diagnostics, and NPPES taxonomy for provider attribution — these are the fields that make each quantitative element directly chartable and cross-linkable.

-----

# Caveats

- Specialty dentist counts rely on the ADA Masterfile 2020 as the cleanest single source; 2024 figures are confirmed only for orthodontics (10,830). Society membership counts (AAE >8,000; AAOMS >7,000; AAP ~8,200; AAPD >10,000) include retired/international members and overstate practicing counts.
- Overhead breakdown percentages are consultant/industry benchmarks attributed to the ADA, not a single verbatim ADA HPI table; the 60–65% headline is ADA-cited.
- "Medicaid share of pediatric dental spending" as a dollar/percentage figure was not located; only coverage/utilization shares are available.
- Several cost figures (clear aligners, root canals, imaging cash prices) are market/cash-price ranges from commercial sources, not government fee schedules — treat as ranges.
- Retail health, worksite, and school-based clinic counts were not retrieved within budget and require verification.
- Some collection/volume statistics (blood, plasma) blend current FDA/Red Cross figures with older NCBI/ABRA historical data (e.g., the >12,000-employee and $15–$20/donation figures are dated) — flagged inline.
- Transplant 2024 figures are OPTN preliminary data as announced January 2025; final SRTR Annual Data Report figures may differ slightly.
- Periodontitis prevalence (42.2%) is from NHANES 2009–2014 (Eke et al. 2018) — the most authoritative full-mouth surveillance estimate, though now somewhat dated.
"""
