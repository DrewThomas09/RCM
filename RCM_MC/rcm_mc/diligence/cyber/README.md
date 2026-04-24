# cyber/

**Cybersecurity posture + business-interruption risk** (Prompt K). Anchored to the **Change Healthcare 2024 ransomware attack** as the causal story. Every PE sponsor now treats cyber as a board-level screening issue — this module integrates it into the packet and the Deal MC.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package docstring with Change Healthcare causal framing. |
| `cyber_score.py` | **CyberScore composite (0-100)** + bridge-reserve lever. Rolls submodule outputs into single score displayed on packet overview alongside EBITDA + EV. **Lower = worse.** |
| `bi_loss_model.py` | **Business-interruption loss Monte Carlo.** For a target with `revenue_per_day_baseline`, `probability_of_incident_per_year`, `days_of_disruption` distribution, produces $ loss distribution. Feeds the bridge-reserve lever. |
| `business_associate_map.py` | **BA cascade risk detector.** Cross-references target's disclosed BA list (clearinghouse, billing, RCM BPO, telehealth, PACS) against known-catastrophic BA catalogue (YAML). Change Healthcare is tier-0. |
| `ehr_vendor_risk.py` | EHR vendor risk score lookups — per-vendor posture ratings, known-vuln history. |
| `deferred_it_capex_detector.py` | **IT capex underinvestment detector.** Flags overdue EHR replacements (Epic 7-10yr cycle, community EHRs 5-7yr) + understaffed IT (industry benchmark ~1 FTE per $8-10M revenue). |

## CyberScore bands

| Score | Tier | Meaning |
|-------|------|---------|
| 80-100 | GREEN | Strong posture — routine monitoring |
| 60-79 | YELLOW | Exposed — require remediation plan at close |
| 40-59 | AMBER | Material — bridge-reserve lever activated |
| 0-39 | RED | Deal-killer territory — walk or re-price |

## The Change Healthcare anchor

Change Healthcare ransomware (Feb 2024) disrupted claim processing for 1/3 of U.S. healthcare for ~3 months. Pre-incident, most diligence treated cyber as a generic "yes we have cyber insurance" checkbox. Post-incident, every PE sponsor asks:

1. **Does the target rely on a tier-0 BA** (Change Healthcare / Optum / similar)? → `business_associate_map`
2. **What's the $ BI loss if that BA goes down for 90 days?** → `bi_loss_model`
3. **Is the target itself under-invested in IT?** → `deferred_it_capex_detector`
4. **What's the composite posture score?** → `cyber_score`

## Where it plugs in

- **Thesis Pipeline step 8** — CyberScore feeds Deal MC cyber-incident-probability driver
- **Bankruptcy-Survivor Scan** — CyberScore is one of the 12 pattern checks (score <40 = RED)
- **Bear Case** — CyberScore + BI loss feed OPERATIONAL theme

## Data sources

- `content/ba_catalog.yaml` — known-catastrophic BAs (Change Healthcare = tier-0; Optum, Epic Cloud, etc. = tier-1). Refresh after each major public BA incident.
- `content/ehr_vendor_risks.yaml` — per-vendor posture based on public incident history + CVE disclosures.

## Tests

`tests/test_cyber*.py` — scoring thresholds + BI MC distribution + BA cascade matching.
