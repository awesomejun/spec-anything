# 12 — Implementation Sequence & Parity Verification Roadmap

## 1. Staged Clean-Room Build Order
Follow this dependency-ordered sequence to implement and verify a clean-room whiteboard compatible with `@excalidraw/excalidraw` v0.18.1 (`SketchBoard CR`):

| Stage | Scope | Feature IDs | Primary Spec Inputs | Exit Gate |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1: Canvas Shell & Theme Tokens** | Full-viewport `<canvas>`, floating chrome islands, light/dark CSS tokens, `--theme-filter` inversion, zoom bar. | `F-001`, `F-008`, `F-009` | `11_ui/tokens.json`, `05_ui/screens.json` [REF: packages/excalidraw/css/theme.scss:4-268] | `TC-001`, `TC-008`, `TC-009` PASS + `empty_light` MAE `<= 8%` |
| **Stage 2: Element Model & Deterministic Sketch Renderer** | Immutable element normalization, Mulberry32 seeded sketchy paths for rectangle, ellipse, diamond, arrow, and text. | `F-002`, `F-003`, `F-005` | `09_contracts/excalidraw_scene.schema.json` [REF: packages/excalidraw/element/newElement.ts:77-250] | `TC-002`, `TC-003`, `TC-005` PASS + `shapes_drawn_light` MAE `<= 8%` |
| **Stage 3: Bidirectional Arrow Binding** | Proximity edge hit-testing, `startBinding`/`endBinding`, and reciprocal `boundElements` maintenance. | `F-004` | `09_contracts/excalidraw_scene.schema.json` [REF: packages/excalidraw/element/binding.ts:120-150] | `TC-004` PASS |
| **Stage 4: Selection Inspector & History Stack** | Canvas hit-testing, left properties panel mutations, version bumping, and reversible `undoStack`/`redoStack`. | `F-006`, `F-007` | `09_contracts/canvas_actions.schema.json` [REF: packages/excalidraw/history.ts:16-158] | `TC-006`, `TC-007` PASS |
| **Stage 5: `.excalidraw` v2 Serialization & Reload Persistence** | Schema-compliant JSON export/import roundtrip and `localStorage` (`"excalidraw"`, `"excalidraw-state"`) hydration on boot. | `F-010`, `F-011` | `09_contracts/excalidraw_scene.schema.json` [REF: packages/excalidraw/data/json.ts:43-123] [REF: excalidraw-app/data/localStorage.ts:36-73] | `TC-010`, `TC-011` PASS |
| **Stage 6: REA Audit & Full Bundle Sealing** | Verify official npm release SHA-256/SHA-512 integrity, execute full differential parity & visual heatmaps, generate `SHA256SUMS.txt`, run 13-gate `validate_bundle.py --tier T3 --verify-checksums`. | `F-012` | `04_environment/release_audit.json` [REF: packages/excalidraw/package.json:1-123] | `TC-012` PASS + `13 / 13` Quality Gates PASS |

## 2. Continuous Regression Protocol
1. Always validate `07_tests/verify_parity.py --mode baseline` against the pinned upstream release first (`12 / 12 PASS`).
2. Run `07_tests/verify_parity.py --mode reimplementation_diff` against `cleanroom-reimpl/` after any renderer, interaction, or CSS change.
3. Re-generate `SHA256SUMS.txt` and run `validate_bundle.py --tier T3 --verify-checksums` before publishing any bundle revision.

## Sources Read
- `packages/excalidraw/css/theme.scss` (lines 4-268)
- `packages/excalidraw/element/newElement.ts` (lines 77-250)
- `packages/excalidraw/element/binding.ts` (lines 120-150)
- `packages/excalidraw/history.ts` (lines 16-158)
- `packages/excalidraw/data/json.ts` (lines 43-123)
- `excalidraw-app/data/localStorage.ts` (lines 36-73)
- `packages/excalidraw/package.json` (lines 1-123)
