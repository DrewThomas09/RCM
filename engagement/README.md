# engagement/ - licensed engagement-side work (firewalled from the public master)

This directory holds engagement-side deliverables built against LICENSED data.
It is a **one-way consumer** of the public master
(`../RCM_MC/deliverables/IFT_Sourced_Evidence_Master`): it imports public
benchmark values (with their fact IDs) and returns **nothing**. Nothing in this
directory is ever cited by, linked from, or merged into the master. The
`leak_check_master` script enforces that the master carries zero engagement-
derived values.

## Komodo Calibration v1

Calibrates the Komodo Health ambulance claims extract (calendar 2025) against the
verified public benchmarks in the master, and packages what the extract is good
for - the Medicare capture / gross-up factor, the commercial realized-price
multiples, the estimated-allowed disclosure, the institutional-lines verdict, and
the payer mix - for the sizing team.

| File | What it is |
|---|---|
| `Komodo_Calibration_v1.xlsx` | The workbook: ReadMe, Benchmarks_Public, Observed_Inputs (T1), T2-T10 panels, GrossUp_Factors, Commercial_Rate_Table, Calibration_Memo, Run_Log. Live formulas; bordered PENDING where a raw-file value is still needed. |
| `Komodo_Calibration_Memo.md` | The one-page memo for Ray (also the Calibration_Memo tab). |
| `build_komodo_calibration.py` | The builder. Reproduces the workbook; reuses the master's `v3lib` CIM formatting. |
| `v3lib.py` | Vendored copy of the master's formatting library so the builder runs standalone. |
| `leak_check_master.py` / `leak_check_master.json` | The firewall check + its logged result: zero Komodo-derived values in the master or its `RCM_MC/` tree. |

### Status
**SKELETON.** Benchmarks and all ten test panels are live and already reproduce
the transcribed headline checks (A0428 ~$533/claim, ~34% estimated-allowed,
~80% open, ~77% Medicare on A0428, ~50% Medicare capture / ~2.0x gross-up). It
awaits the raw extract from Andrew: T1 re-derives every observed input from the
raw file, hashes it on Run_Log, and every panel recomputes.

### Reproduce
```
cd engagement && python3 build_komodo_calibration.py     # writes Komodo_Calibration_v1.xlsx
python3 leak_check_master.py                              # confirms the master is untouched
```

### Firewall notes
- One RVU correction: A0426 (ALS1 non-emergency) = **1.20** per the master
  Payment_Rules (GOV-A). The calibration order's 1.75 is the A0432 paramedic-
  intercept RVU and is not used. The master governs.
- The Komodo extract file itself is NOT committed here; only the calibration
  workbook and its code. Deliver the raw extract out-of-band.
