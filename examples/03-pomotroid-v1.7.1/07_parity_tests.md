# 07 Differential Parity Tests & Results — Pomotroid v1.7.1

Harness: `07_tests/verify_parity.py` (reads `06_evidence/ledger.jsonl` directly).

## 1. Execution Commands
```bash
# Upstream baseline verification
python3 07_tests/verify_parity.py --mode upstream_baseline

# Full-app clean-room reimplementation verification (behavior + Playwright pixel diff)
python3 cleanroom-reimpl/app.py --port 18771 &
python3 07_tests/verify_parity.py --mode reimplementation_diff --target-url http://127.0.0.1:18771
```

## 2. Verified Results
- **Upstream Baseline (`07_tests/parity_report.json`)**: `14 / 14 PASS`
- **Full-App Clean-Room Reimplementation (`07_tests/reimpl_parity_report.json`)**: `14 / 14 PASS`
- **Playwright Visual Pixel-Diff MAE (`cleanroom-reimpl/proof_shots/visual_diff_metrics.json`)**:
  - `SCR-001` Focus Idle Dark: `0.88%` MAE (`99.12%` similarity)
  - `SCR-002` Focus Running Mid-Tick: `0.83%` MAE (`99.17%` similarity)
  - `SCR-003` Short Break: `1.03%` MAE (`98.97%` similarity)
  - `SCR-004` Long Break Light: `0.93%` MAE (`99.07%` similarity)
