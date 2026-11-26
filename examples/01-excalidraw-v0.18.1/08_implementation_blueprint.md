# 08 — Clean-Room Implementation Blueprint (`SketchBoard CR`)

## 1. Clean-Room Engineering Boundary
`SketchBoard CR` (`cleanroom-reimpl/`) is a zero-dependency, standalone HTML5 Canvas + vanilla JavaScript + CSS clean-room reimplementation derived strictly from:
- Machine contracts in `09_contracts/excalidraw_scene.schema.json` and `09_contracts/canvas_actions.schema.json`
- Extracted design tokens and measured chrome bounding rects in `11_ui/tokens.json`
- Runtime evidence ledger in `06_evidence/ledger.jsonl`

No source files, RoughJS internals, React components, trademarks, or `.woff2` font files from `excalidraw/excalidraw` are copied (see `04_environment/LICENSING.md`).

## 2. Module Decomposition (`cleanroom-reimpl/`)
| File | Responsibility | Upstream Functional Equivalent |
| :--- | :--- | :--- |
| `cleanroom-reimpl/index.html` | Full-viewport 2D canvas, floating top toolbar island, top-left menu, left inspector panel, bottom-left zoom/undo controls, inline `<textarea>` text editor. | [REF: packages/excalidraw/index.tsx:22-151] |
| `cleanroom-reimpl/styles.css` | Light and `.theme--dark` CSS custom property tokens, island shadows, exact chrome coordinates, and `--theme-filter: invert(93%) hue-rotate(180deg)` canvas inversion. | [REF: packages/excalidraw/css/theme.scss:4-268] |
| `cleanroom-reimpl/app.js` | Deterministic seeded sketchy renderer (Mulberry32 PRNG), scene state & element constructors, bidirectional arrow binding, hit-testing, immutable snapshot Undo/Redo stack, center-preserving zoom math, `.excalidraw` v2 JSON serializer/restorer, `localStorage` persistence, and `window.__whiteboardAPI`. | [REF: packages/excalidraw/element/newElement.ts:77-250] [REF: packages/excalidraw/history.ts:16-158] [REF: packages/excalidraw/data/json.ts:43-123] |
| `cleanroom-reimpl/server.py` | Zero-dependency Python stdlib `http.server` static file server binding to `127.0.0.1:4183`. | Isolated test/preview server |

## 3. Deterministic Hand-Drawn Rendering Algorithm
Instead of bundling `roughjs`, `cleanroom-reimpl/app.js` implements a self-contained deterministic PRNG (`createRng(element.seed)` using Mulberry32):
1. **Roughness 0 (Architect)**: Single clean geometric pass using adaptive rounded rectangle corner radius `min(32, min(w, h) * 0.25)` [REF: packages/excalidraw/constants.ts:346-367].
2. **Roughness 1 (Artist) & 2 (Cartoonist)**: Dual-pass quadratic Bezier perturbation for rectangle edges, diamond edges, and arrow shafts, plus 28-segment dual-pass perturbed ellipse sweeps seeded strictly by `element.seed` so frames never jitter on redraw [REF: packages/excalidraw/element/types.ts:53-55].
3. **Fill Modes**: `solid` fills the clipped shape path directly; `hachure` and `cross-hatch` clip to the shape path and draw diagonal hatching strokes spaced at `8px`.

## 4. Bidirectional Arrow Binding & Hit-Testing
- On arrow `pointerup`, `findBindingTarget` evaluates edge distance against every non-deleted `rectangle`, `ellipse`, and `diamond` within a `18px` snap radius.
- Matched endpoints populate `arrow.startBinding` / `arrow.endBinding` (`{ elementId, focus: 0, gap }`) and append `{ id: arrow.id, type: "arrow" }` to the connected shape's `boundElements` array while incrementing shape `version` [REF: packages/excalidraw/element/binding.ts:120-150].

## 5. Programmatic Test & Integration Surface (`window.__whiteboardAPI`)
- `getSceneElements()`: Returns deep-cloned non-deleted elements array conforming to `09_contracts/excalidraw_scene.schema.json`.
- `getAppState()`: Returns deep-cloned viewport, theme, zoom, selection, and active tool state.
- `updateScene({ elements, appState, captureUpdate })`: Applies normalized scene/state updates, optionally captures history (`"IMMEDIATELY"`), persists to `localStorage`, and redraws.
- `exportExcalidrawJSON()` / `importExcalidrawJSON(json)`: Lossless `.excalidraw` v2 roundtrip.
- `setTheme(theme)`, `undo()`, `redo()`: Direct imperative theme and history triggers.

## Sources Read
- `packages/excalidraw/index.tsx` (lines 22-151)
- `packages/excalidraw/element/types.ts` (lines 38-332)
- `packages/excalidraw/element/newElement.ts` (lines 77-250)
- `packages/excalidraw/element/binding.ts` (lines 120-150)
- `packages/excalidraw/history.ts` (lines 16-158)
- `packages/excalidraw/data/json.ts` (lines 43-123)
- `packages/excalidraw/css/theme.scss` (lines 4-268)
- `packages/excalidraw/constants.ts` (lines 346-399)
