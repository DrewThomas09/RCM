# Demo diligence data package

This folder contains a tiny **synthetic** data package (not real PHI) to demonstrate the calibration workflow.

Run:

```bash
python -m rcm_mc.cli \
  --actual configs/actual.yaml \
  --benchmark configs/benchmark.yaml \
  --actual-data-dir data_demo/target_pkg \
  --n-sims 20000 \
  --outdir outputs_demo_calibrated
```

You should see additional outputs:

- `outputs_demo_calibrated/calibration_actual_report.csv`
- `outputs_demo_calibrated/calibrated_actual.yaml`
