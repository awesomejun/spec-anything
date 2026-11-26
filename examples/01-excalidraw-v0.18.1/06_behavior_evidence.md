# 06 — Runtime Behavior Evidence Ledger (`EV-001` .. `EV-012`)

Canonical machine-readable ledger: `06_evidence/ledger.jsonl` (12 records, all `status: "observed"`, schema-validated against `evidence.schema.json`, bound to artifact SHA-256 `7f651063487849c79a8cdedc3aa6bd04c6b0c717ee63959116f1f12dbc0a51b8`).

| Evidence ID | Feature ID | Category | Source Location | Observed Behavior Summary | Screen / Contract | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `EV-001` | `F-001` | `ui_state` | `packages/excalidraw/index.tsx:22-151` | Mounts empty `1280x800` canvas, `theme="light"`, `viewBackgroundColor="#ffffff"`, `zoom=1`, `activeTool="selection"`. | `SCR-001` / `canvas_actions.schema.json` | `observed` |
| `EV-002` | `F-002` | `normal` | `packages/excalidraw/components/App.tsx:6329-6390` | Rectangle tool drag `(260,180)->(480,320)` commits `type="rectangle"` (`220x140`, `#1e1e1e`, `roughness=1`) and resets tool to `"selection"`. | `SCR-002` / `excalidraw_scene.schema.json` | `observed` |
| `EV-003` | `F-003` | `normal` | `packages/excalidraw/element/newElement.ts:157-163` | Ellipse tool drag `(700,180)->(900,320)` commits `type="ellipse"` (`200x140`, count `2`) and resets tool to `"selection"`. | `SCR-002` / `excalidraw_scene.schema.json` | `observed` |
| `EV-004` | `F-004` | `normal` | `packages/excalidraw/element/binding.ts:120-150` | Arrow drag `(482,250)->(696,250)` commits 2-point `arrow` (`endArrowhead="arrow"`) with populated `startBinding`, `endBinding`, and reciprocal `boundElements` on both shapes. | `SCR-002` / `excalidraw_scene.schema.json` | `observed` |
| `EV-005` | `F-005` | `normal` | `packages/excalidraw/element/newElement.ts:238-250` | Text click `(440,420)` + `"Excalidraw Parity Spec"` + `Escape` commits `type="text"` (`fontSize=20`, `fontFamily=5`, count `4`). | `SCR-002` / `excalidraw_scene.schema.json` | `observed` |
| `EV-006` | `F-006` | `ui_state` | `packages/excalidraw/actions/actionProperties.tsx:128-149` | Edge click `(370,180)` selects rectangle, opens `.App-menu__left`, mutates `strokeColor="#e03131"`, `backgroundColor="#a5d8ff"`, `roughness=2`, and increments `version`. | `SCR-004` / `canvas_actions.schema.json` | `observed` |
| `EV-007` | `F-007` | `cancel_retry` | `packages/excalidraw/history.ts:16-158` | Drawing diamond (`4->5`), clicking Undo (`5->4`, Redo enabled), clicking Redo (`4->5`), and Undo (`5->4`) verifies reversible history stack transitions. | `SCR-004` / `canvas_actions.schema.json` | `observed` |
| `EV-008` | `F-008` | `ui_state` | `packages/excalidraw/css/theme.scss:166-268` | Toggling Dark Mode sets `.theme--dark`, `--default-bg-color: #121212`, `--island-bg-color: #232329`, canvas inversion filter, while keeping raw element `strokeColor="#1e1e1e"` unmutated. | `SCR-003` / `canvas_actions.schema.json` | `observed` |
| `EV-009` | `F-009` | `boundary` | `packages/excalidraw/scene/zoom.ts:3-35` | Clicking Zoom in then Zoom out steps `zoom.value` `1.0 -> 1.1 -> 1.0` (`step_delta = 0.1`). | `SCR-001` / `canvas_actions.schema.json` | `observed` |
| `EV-010` | `F-010` | `persistence` | `packages/excalidraw/data/json.ts:43-69` | `serializeAsJSON` emits valid v2 JSON (`4` elements); clearing scene (`0`) and restoring restores all `4` elements with identical IDs and types. | `SCR-005` / `excalidraw_scene.schema.json` | `observed` |
| `EV-011` | `F-011` | `restart_recovery` | `excalidraw-app/data/localStorage.ts:36-73` | Host persists `localStorage["excalidraw"]` & `["excalidraw-state"]`; full page reload hydrates all `4` elements with matching IDs. | `SCR-005` / `excalidraw_scene.schema.json` | `observed` |
| `EV-012` | `F-012` | `release_rea` | `packages/excalidraw/package.json:1-25` | Official tarball `excalidraw-0.18.1.tgz` matches npm SHA-512 & SHA-1 digests; `dist/prod/index.js` exposes 65 ESM exports and matches tag `v0.18.1`. | `release_audit.json` | `observed` |

## Limitations & Scope Boundaries
- All runtime assertions are scoped to `1280x800` desktop viewport (`DPR=1`) in Chromium; touch/pen gestures, mobile portrait drawers, multiplayer WebSocket reconciliation, and binary image blob embedding (`files` map non-empty) are outside the verified parity scope.
