# CMS Clinician MIPS Performance (PY2023 distribution)

**Source:** CMS Provider Data Catalog — "PY2023 Clinician Public Reporting:
Overall MIPS Performance" (`ec_score_file.csv`), public.
**Geography:** United States, **national distribution** (aggregated from ~541k
scored per-clinician rows).
**Coverage:** MIPS final-score distribution (mean 83.2, median 85.5/100) overall
and by reporting source (individual / group / APM / subgroup / virtual group),
a 5-band score histogram, and per-category sub-scores (Quality, Promoting
Interoperability, Improvement Activities, Cost). Build-time snapshot; runtime
reads the committed aggregate (no live API).
**Powers:** physician-quality **benchmark** on Physician Productivity, and the
sector-aware quality anchor on Quality Scorecard / Clinical Outcomes (shown for
physician sectors; nursing/post-acute sectors use CMS Care Compare instead).

**What it indicates:** how physician/clinician quality performance is
distributed nationally under MIPS — e.g. APM-track clinicians score markedly
higher (mean 94.2) than individual reporters (56.2), a real, known pattern.

**What it does NOT prove:** it is a **national benchmark distribution, not a
deal-specific score** and **not a payment/penalty figure**. A target's own
clinicians are not represented; connect the deal's TIN/NPI roster for that.

**Diligence use cases:** sanity-check a physician-group target's quality posture
against the national MIPS distribution; frame value-based-care readiness (APM vs
individual reporting gap).

**Caveats:** PY2023; **all PII (NPI, names, facility) dropped at ingest** — only
aggregates are committed. Scores missing in the source are excluded from the
sample (never counted as 0). Refreshed on re-ingest
(`scripts/ingest_mips_performance.py`).

**Suggested questions:**
- "What's the national median MIPS score?" (85.5)
- "Do APM clinicians outscore individual reporters?" (yes, materially)
- "Is this my target's score?" (no — national benchmark, connect a roster)
- "Is the MIPS score a payment figure?" (no)
