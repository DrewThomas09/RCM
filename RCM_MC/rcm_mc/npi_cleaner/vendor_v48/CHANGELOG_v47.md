# CHANGELOG v47.0.0

Builds on v46. This release opens a new front: ingesting and cleaning Medicare RIF
data (the VRDC/CCW schema, the 100% fee-for-service census) and adding the CMS
cell-suppression that lets results leave the enclave. It is the first step of a
larger arc toward deep CMS and NPI modeling, described at the end. Headline
document: V47_VRDC_AND_RIF.md.

## Why this direction

The tool had breadth: many screens, many analytical cuts, a handful of reference
files. The frontier is depth in the two things that are the actual core of claims
diligence, how billing provider identity really works and what the data does and
does not represent. Both point at the same source: VRDC, the Medicare FFS census.
It is the ground truth a sampled commercial panel gets calibrated against, and it
is the raw material for real CMS and NPI models. So v47 makes the tool able to
ingest and clean it.

## RIF ingestion (rif_schema.py)

Medicare Research Identifiable Files use column conventions entirely different from
a commercial extract. This module detects which RIF file it is looking at and maps
its columns onto the toolkit's canonical model, so every screen, recovery, and
analytic that already runs on a Komodo panel runs on VRDC data without change.

Supported file types with their real CCW variable maps:
  carrier      Part B physician/supplier: PRF_PHYSN_NPI to rendering_npi,
               ORG_NPI_NUM to billing_npi, CARR_CLM_HCPCS_CD to hcpcs,
               LINE_ALOWD_CHRG_AMT to allowed_amt, RFR_PHYSN_NPI to referring_npi,
               LINE_NDC_CD to ndc, and so on. The core file for infused drugs.
  inpatient    Part A institutional inpatient: facility org NPI, attending and
               operating physicians, principal diagnosis, revenue centers.
  outpatient   Part A institutional outpatient.
  pde          Part D drug events: PRSCRBR_ID to referring (prescriber),
               PROD_SRVC_ID to ndc, QTY_DSPNSD_NUM to units, DAYS_SUPLY_NUM to
               days_supply, plan and patient paid.

Detection is signature-based (presence of each type's characteristic columns) and
is verified not to misfire on a commercial extract. schema.standardize_any auto
routes any input to the RIF or the commercial path, so the pipeline and --clean-all
handle VRDC data transparently.

The payoff, shown in tests: the MUE and JW/JZ screens, and by construction every
other screen, run unchanged on standardized RIF data. The FFS census now flows
through the whole toolkit.

## CMS cell suppression (rif_cleaning.py)

The single most important VRDC-specific step. Nothing leaves the enclave without
small-cell suppression: any exported cell representing fewer than 11 beneficiaries
must be suppressed, and a lone small cell in a group forces complementary
suppression of a second cell so the first cannot be recovered by subtraction. This
module applies both, blanks the suppressed counts and values, and provides an
export gate that reports clean only when no small cell survives. An aggregate that
has not passed this cannot legally leave the enclave, and the tool now enforces it.

## FFS-specific recovery (rif_cleaning.py)

An FFS recovery case that commercial data does not present: the organization NPI is
blank because a solo practitioner billed under only an individual NPI, which in RIF
appears as the performing physician. These are high-confidence recoveries by
promoting the rendering NPI, and the tool flags them with the suggested billing
NPI.

## Operational reality

VRDC is a secure enclave and RIF data cannot be exported from it. This code is
built to run inside the enclave or on approved RIF-format extracts, and it is
tested against RIF-schema synthetic data, since real RIF data lives only in the
enclave. The cell-suppression tool is what makes the tool's own outputs
enclave-safe.

## Tests

15 new self-tests: detection of carrier, PDE, and inpatient files and correct
rejection of a commercial extract; the RIF-to-canonical mapping; the MUE and JW/JZ
screens running unchanged on RIF data; standardize_any routing; primary and
complementary cell suppression and the export gate; and the solo-biller FFS
recovery. 324 checks total, all passing offline.

## Roadmap: the deep CMS and NPI modeling this enables

RIF ingestion is the foundation. With the FFS census flowing through the tool, the
next builds are the depth that turns recovery from a pattern guess into a
structurally grounded model:

  PECOS reassignment graph      Individual (Type 1) NPIs reassign billing rights to
                                organizations (Type 2). Modeling the reassignment
                                relationships from Medicare enrollment data is the
                                actual mechanism of billing and would let recovery
                                resolve org-to-individual links directly rather than
                                inferring them.
  specialty-by-drug utilization Build the empirical distribution of which provider
                                specialties bill which drugs from the RIF carrier
                                census, turning the current coarse taxonomy gate
                                into a calibrated P(specialty | drug) that scores
                                recovery plausibility from real data.
  ASP payment benchmarking      Join CMS ASP pricing to compute allowed against
                                ASP plus six percent per drug and flag reimbursement
                                compression, the margin read that matters most for a
                                specialty infusion book, now against FFS ground
                                truth.
  panel calibration against FFS Use the FFS census to calibrate a commercial
                                panel's FFS coverage drug by drug, the original
                                purpose of having VRDC in reach.

These are the next arc. v47 is the ingestion layer that makes them buildable.
