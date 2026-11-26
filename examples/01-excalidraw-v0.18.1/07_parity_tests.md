# 07 — Executable Differential Parity Tests & Visual Pixel-Diff Proof

Executable harness: `07_tests/verify_parity.py` (reads `06_evidence/ledger.jsonl` directly, validates `.excalidraw` v2 JSON against `09_contracts/excalidraw_scene.schema.json`, and computes RGB pixel-diff MAE heatmaps in `reimplementation_diff` mode).

## 1. Execution Commands
```bash
# 1. Upstream Baseline Verification (@excalidraw/excalidraw@0.18.1)
PYTHONDONTWRITEBYTECODE=1 python3 07_tests/verify_parity.py \
  --mode baseline \
  --target-url http://127.0.0.1:4173/

# 2. Clean-Room Differential Parity & Visual Pixel-Diff Verification (SketchBoard CR)
PYTHONDONTWRITEBYTECODE=1 python3 cleanroom-reimpl/server.py --port 4183 &
PYTHONDONTWRITEBYTECODE=1 python3 07_tests/verify_parity.py \
  --mode reimplementation_diff \
  --target-url http://127.0.0.1:4183/
```

## 2. Differential Parity Summary
| Target | Report File | Mode | Total | Passed | Failed | Skipped | Unverified |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| `@excalidraw/excalidraw@0.18.1` (Upstream) | `07_tests/parity_report.json` | `upstream_baseline` | 12 | **12** | 0 | 0 | 0 |
| `SketchBoard CR` (Clean-Room) | `07_tests/reimpl_parity_report.json` | `reimplementation_diff` | 12 | **12** | 0 | 0 | 0 |

## 3. Per-Case Traceability Matrix (`TC-001` .. `TC-012`)
| Test ID | Feature ID | Evidence ID | Category | Upstream Baseline | Clean-Room Diff | Checked Fields / Assertions |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TC-001` | `F-001` | `EV-001` | `ui_state` | `PASS` | `PASS` | `element_count=0`, `theme=light`, `viewBackgroundColor=#ffffff`, `zoom=1`, `activeTool=selection`, `1280x800` + `empty_light` MAE `<= 8%` |
| `TC-002` | `F-002` | `EV-002` | `normal` | `PASS` | `PASS` | Rectangle tool selection, drag `(260,180)->(480,320)`, `220x140`, `#1e1e1e`, `roughness=1`, tool reset to `selection` |
| `TC-003` | `F-003` | `EV-003` | `normal` | `PASS` | `PASS` | Ellipse tool selection, drag `(700,180)->(900,320)`, `200x140`, `element_count=2`, tool reset |
| `TC-004` | `F-004` | `EV-004` | `normal` | `PASS` | `PASS` | Arrow drag `(482,250)->(696,250)`, `points>=2`, `endArrowhead=arrow`, `startBinding`, `endBinding`, reciprocal `boundElements` on 2 shapes |
| `TC-005` | `F-005` | `EV-005` | `normal` | `PASS` | `PASS` | Text tool click `(440,420)`, `"Excalidraw Parity Spec"`, `Escape` commit, `fontSize=20`, `element_count=4` + `shapes_drawn_light` MAE `<= 8%` |
| `TC-006` | `F-006` | `EV-006` | `ui_state` | `PASS` | `PASS` | Canvas edge click selection, `.App-menu__left` visible, `strokeColor=#e03131`, `backgroundColor=#a5d8ff`, `roughness=2`, `version` increment |
| `TC-007` | `F-007` | `EV-007` | `cancel_retry` | `PASS` | `PASS` | Diamond creation (`4->5`), Undo (`5->4`, Redo enabled), Redo (`4->5`), Undo (`5->4`) |
| `TC-008` | `F-008` | `EV-008` | `ui_state` | `PASS` | `PASS` | Menu Dark Mode toggle, `.theme--dark`, `--default-bg-color=#121212`, `--island-bg-color=#232329`, raw stroke preserved + `dark_theme` MAE `<= 8%` |
| `TC-009` | `F-009` | `EV-009` | `boundary` | `PASS` | `PASS` | Zoom in (`1.0->1.1`), Zoom out (`1.1->1.0`), `step_delta=0.1` |
| `TC-010` | `F-010` | `EV-010` | `persistence` | `PASS` | `PASS` | `.excalidraw` v2 JSON export validated against `09_contracts/excalidraw_scene.schema.json`, clear to `0`, restore `4` matching IDs |
| `TC-011` | `F-011` | `EV-011` | `restart_recovery` | `PASS` | `PASS` | `localStorage["excalidraw"]` & `["excalidraw-state"]` present, full reload recovers all `4` elements with identical IDs |
| `TC-012` | `F-012` | `EV-012` | `release_rea` | `PASS` | `PASS` | `04_environment/release_audit.json` binary SHA-256, archive SHA-256, `upstream_checksum_verified=true`, pinned commit verified |

## 4. Visual Pixel-Diff Proof (`cleanroom-reimpl/proof_shots/visual_diff_metrics.json`)
All three scenes were compared at `1280x800` (`DPR=1`) against live upstream screenshots using RGB Mean Absolute Error (`MAE`) with an `8.0%` acceptance gate:

| Scene | Upstream Capture | Clean-Room Capture | Diff Heatmap | MAE (%) | Changed Pixels (>15/255) | Verdict |
| :--- | :--- | :--- | :--- | ---: | ---: | :--- |
| `empty_light` | `cleanroom-reimpl/proof_shots/orig_empty_light.png` | `cleanroom-reimpl/proof_shots/reimpl_empty_light.png` | `cleanroom-reimpl/proof_shots/diff_empty_light.png` | **0.1784%** | 0.6900% | `PASS` |
| `shapes_drawn_light` | `cleanroom-reimpl/proof_shots/orig_shapes_drawn_light.png` | `cleanroom-reimpl/proof_shots/reimpl_shapes_drawn_light.png` | `cleanroom-reimpl/proof_shots/diff_shapes_drawn_light.png` | **0.4563%** | 1.2877% | `PASS` |
| `dark_theme` | `cleanroom-reimpl/proof_shots/orig_dark_theme.png` | `cleanroom-reimpl/proof_shots/reimpl_dark_theme.png` | `cleanroom-reimpl/proof_shots/diff_dark_theme.png` | **0.4361%** | 1.2860% | `PASS` |

### Claimed Parity Boundary
Parity is strictly proven for the 12 executed scenarios (`TC-001`..`TC-012`) and 3 visual comparison states above. Out-of-scope upstream capabilities (multiplayer collaboration, binary image embedding, elbowed multi-segment arrow routing, bundled `.woff2` font glyph matching) are excluded from parity claims.
