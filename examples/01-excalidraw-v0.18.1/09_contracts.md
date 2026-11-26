# 09 — Machine-Readable Contracts

All contracts live in `09_contracts/` as valid JSON Schema Draft 2020-12 documents and are directly executed by `07_tests/verify_parity.py` during both upstream baseline and clean-room differential runs.

## 1. Contract Inventory
| Contract File | Schema Standard | Purpose | Linked Features |
| :--- | :--- | :--- | :--- |
| `09_contracts/excalidraw_scene.schema.json` | JSON Schema Draft 2020-12 | Formal wire & file schema for `.excalidraw` v2 documents (`type: "excalidraw"`, `version: 2`, discriminated `elements[]` union covering `rectangle`, `ellipse`, `diamond`, `arrow`, `line`, `text`, `freedraw`, plus `appState` and `files`). | `F-002`, `F-003`, `F-004`, `F-005`, `F-006`, `F-010`, `F-011` |
| `09_contracts/canvas_actions.schema.json` | JSON Schema Draft 2020-12 | Action payload & capture-policy schema covering tool selection, pointer drag creation, text commit, property mutation, undo/redo, theme switch, zoom stepping, export/import, and `localStorage` keys (`"excalidraw"`, `"excalidraw-state"`). | `F-001` .. `F-011` |

## 2. Key Invariants Verified Against Live Exports
- Root envelope MUST carry `type: "excalidraw"` and integer `version: 2`.
- Every element carries `id`, `type`, `x`, `y`, `width`, `height`, `angle`, `strokeColor`, `backgroundColor`, `fillStyle`, `strokeWidth`, `strokeStyle`, `roughness` (`0..2`), `opacity` (`0..100`), integer `seed`, `version >= 1`, `versionNonce`, `isDeleted`, `groupIds`, `boundElements`, `link`, `locked`.
- `arrow` elements require `points` (`minItems: 2`), `startBinding`, `endBinding`, `startArrowhead`, `endArrowhead`.
- `text` elements require `text`, `originalText`, `fontSize >= 1`, `fontFamily` (`1|2|3|5|6|7|8|9`), `textAlign`, `verticalAlign`, `containerId`, `autoResize`, `lineHeight > 0`.
- `appState` exported in local JSON strips transient selection/hover/cursor keys and retains `viewBackgroundColor`, `gridSize`, `gridStep`, `gridModeEnabled`.

## 3. Contract Verification Evidence
- Upstream live `serializeAsJSON(elements, appState, files, "local")` export validated cleanly against `09_contracts/excalidraw_scene.schema.json` (`TC-010` PASS in `07_tests/parity_report.json`).
- Clean-room `window.__whiteboardAPI.exportExcalidrawJSON()` output validated cleanly against the identical schema (`TC-010` PASS in `07_tests/reimpl_parity_report.json`).
