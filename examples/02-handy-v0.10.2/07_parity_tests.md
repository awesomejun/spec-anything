# 07 — Executable Differential Parity Tests (`cjpais/Handy v0.10.2`)

## 1. Test Harness Architecture
- **Executable Script**: `07_tests/verify_parity.py`
- **Direct Evidence Input**: Loads all 15 expected observations, inputs, and comparison rules directly from `06_evidence/ledger.jsonl` at runtime (no duplicated hardcoded expectations).
- **Execution Modes**:
  1. `--mode baseline --target-url http://127.0.0.1:1420`: Launches Playwright (`1024x700@1x`, light theme, `en-US`, `UTC`) against the live upstream Vite server with a deterministic Tauri v2 IPC test double backed by SQLite `history.db` (`09_contracts/history.sql`), verifies `TC-001`–`TC-015`, captures `cleanroom-reimpl/proof_shots/orig_SCR-001..003.png`, and writes `07_tests/parity_report.json`.
  2. `--mode reimplementation_diff --target-url http://127.0.0.1:1430`: Runs the identical 15 test cases against `cleanroom-reimpl/app.py`, captures `reimpl_SCR-001..003.png`, computes RGB MAE pixel-diff heatmaps (`diff_SCR-001..003.png` + `visual_diff_metrics.json`), enforces `normalized_mae <= 0.12`, and writes `07_tests/reimpl_parity_report.json`.

## 2. Differential Verdict Summary
| Target | Mode | Report File | Total | Passed | Failed | Skipped |
|---|---|---|---|---|---|---|
| `cjpais/Handy v0.10.2` (Upstream Vite UI + Tauri IPC Double + SQLite) | `upstream_baseline` | `07_tests/parity_report.json` | `15` | `15` | `0` | `0` |
| `Handy CR` (`cleanroom-reimpl/app.py` Python/SQLite/HTML) | `reimplementation_diff` | `07_tests/reimpl_parity_report.json` | `15` | `15` | `0` | `0` |

## 3. Visual Pixel-Diff Proof Metrics (`cleanroom-reimpl/proof_shots/visual_diff_metrics.json`)
Measured at `1024x700@1x` (light theme, `en-US`, `UTC`) comparing live upstream screenshots (`orig_SCR-*.png`) vs. clean-room screenshots (`reimpl_SCR-*.png`) with separated **`Handy CR`** brand mark:

| Screen ID | View | RGB MAE (`0..255`) | Normalized MAE (`0..1`) | Pixels with Max-Channel Diff `> 15` | Tolerance (`<= 0.12`) | Proof Artifacts |
|---|---|---|---|---|---|---|
| `SCR-001` | General Settings | `4.2514` | `0.016672` (`1.67%`) | `5.800%` | **PASS** | `orig_SCR-001.png`, `reimpl_SCR-001.png`, `diff_SCR-001.png` |
| `SCR-002` | Models Catalog | `8.0871` | `0.031714` (`3.17%`) | `8.545%` | **PASS** | `orig_SCR-002.png`, `reimpl_SCR-002.png`, `diff_SCR-002.png` |
| `SCR-003` | Transcription History | `6.2716` | `0.024595` (`2.46%`) | `7.558%` | **PASS** | `orig_SCR-003.png`, `reimpl_SCR-003.png`, `diff_SCR-003.png` |

## 4. Scope & Non-Verified Boundary Statement
Claimed functional and visual parity covers the exact 15 executed cases (`TC-001`–`TC-015`) across settings read/write, shortcut activation mode switching, shortcut keybinding mutation, language selection/status, audio feedback & microphone listing, model catalog & active-model switching, undownloaded-model error rejection, dictation state machine (`idle -> recording -> transcribing -> completed`), cancellation (`recording -> cancelled -> idle`), cursor-paginated history listing, SQLite star toggle, SQLite delete & missing-ID error, SQLite v4 schema migration, measured light-mode CSS tokens, and `SCR-001`–`SCR-003` visual tolerance. Native CoreAudio microphone capture, macOS Carbon/CGEventTap global hooks, and Metal GGUF neural inference remain explicitly outside the deterministic test double boundary.
