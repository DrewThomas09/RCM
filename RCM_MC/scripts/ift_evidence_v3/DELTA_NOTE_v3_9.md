# IFT Sourced Evidence Master v3.9 - delta note

## What this revision does

v3.9 answers two standing asks: (a) make every page explain its usefulness for
the IFT study, and (b) advance the Run 4 tail the reviewer flagged - the
Outcome 4 corpus link-portability defect and the Outcome 6 deck-facing
synthesis. No existing fact/source/finding is renumbered; the ledgers stay
F1-F609 / S1-S435 and this pass adds no new IDs.

## 1. Every page explains its usefulness for the IFT study

- **New `Study_Synthesis` tab (up front, right after the README).** The IFT
  investment thesis as nine measured pillars - demand, the one fully-measured
  TAM floor, price and its ~43-45% mileage load, input-cost risk against the
  statutory update, supply fragmentation, the measured subject-company book,
  the structural return-leg driver, and the named forward risks. Every headline
  is a LIVE green link to its home tab (it recomputes with the workbook, so it
  cannot drift), every row carries its guardrail, and a plain-language firewall
  panel states what the study refuses to assert. Like Investor_QA and
  Slide_Feed, it summarises linked cells and creates no evidence of its own.
- **The Index now prints each section's ROLE in the IFT study** under its
  banner (read from the README section map), so every one of the 328 tabs
  inherits a stated purpose - what an investor learns from it - not just a
  title. Combined with each tab's own top-of-page subtitle, every page now says
  why it is here.

## 2. Outcome 4 - contract-corpus link portability, fixed

The reviewer flagged corpus citations pointing at local file paths
(`pdfs/topeka...`), which break the reproducible-from-the-public-internet
promise. Every such fragment is now stripped from both the Contract_Corpus
scope-note column and the underlying source locators; the retrievable public
URL already rides in its own column, so nothing is lost. Verified: **zero**
`pdfs/...`-style local paths remain anywhere in the corpus tab or its sources.

The federal award ladder is also widened from a 15-row sample to the **top 25
Department of Veterans Affairs V225 (Ambulance Service) awards by amount** - the
VA is the largest public interfacility-transport buyer in the 300-record pull -
each retrievable by PIID on USAspending.gov.

## 3. Outcome 6 - deck-facing synthesis and extract

- `Study_Synthesis` (above) is the deck spine.
- **`IFT_Deck_Feed_Extract_v3_9.xlsx`** - a small standalone workbook holding
  the three deck-facing tabs (Study_Synthesis, Slide_Feed, Investor_QA) with
  every formula resolved to the value the master recomputes to, so a deck can
  be built from a small file instead of the 31 MB master. It carries a
  provenance cover naming the master as the source of truth.

## Verification
- Two-pass LibreOffice recalc: zero error cells, carried v2.7 cells reproduce,
  all charts pass the V9 gate, format gate PASS on all tabs, ledgers contiguous
  F1-F609 / S1-S435.
- Firewall leak check clean (Study_Synthesis, Contract_Corpus and Index forced
  into the scan); static live-reference audit clean; the nine Study_Synthesis
  headline links resolve to verified measured cells (no blank-cell links).

## What still remains (the reviewer's tail)
- **Outcome 4 (further):** contract scope-flag column already present; deeper
  USAspending per-award document retrieval stays blocked by SAM.gov key-gating
  (honestly parked).
- **Outcome 5 (commercial MRF):** not attempted this pass - the regional-payer
  Transparency-in-Coverage streaming (Medica / BCBS NE / Wellmark first) or a
  Run_Log of logged attempts.
- **Outcome 6 (4.9):** the per-NPI annual trajectory (the book is still three
  vintages) is not yet run.
