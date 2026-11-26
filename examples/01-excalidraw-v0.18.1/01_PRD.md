# 01 — Product Requirements Document (PRD): Excalidraw v0.18.1

## 1. Executive Summary
This specification defines the observable functional, visual, serialization, and persistence requirements of **`@excalidraw/excalidraw` v0.18.1** (repository `https://github.com/excalidraw/excalidraw`, tag `v0.18.1`, commit `a2ec2889babf7d2295469c6d90ebe77fae57df84`, MIT License) for clean-room functional reimplementation (`SketchBoard CR`).

The system is an interactive browser-based vector whiteboard that renders geometric primitives, bound connectors, and text with a deterministic hand-drawn stroke aesthetic while storing scenes in a portable JSON schema (`.excalidraw` v2) [REF: packages/excalidraw/index.tsx:22-151] [REF: packages/excalidraw/data/json.ts:43-69].

## 2. Target Scope & Feature Boundaries
| Domain | Feature IDs | Inclusion | Status |
| :--- | :--- | :--- | :--- |
| Canvas Lifecycle & Viewport | `F-001`, `F-009` | In Scope | `observed` |
| Hand-Drawn Primitives & Connectors | `F-002`, `F-003`, `F-004`, `F-005` | In Scope | `observed` |
| Selection, Styling Inspector & Undo/Redo | `F-006`, `F-007` | In Scope | `observed` |
| Light / Dark Theme Switching | `F-008` | In Scope | `observed` |
| `.excalidraw` v2 Serialization & Reload Persistence | `F-010`, `F-011` | In Scope | `observed` |
| Official npm Distribution REA Boundary | `F-012` | In Scope | `observed` |
| Cloud Collaboration (Firebase / WebSocket) | — | Out of Scope | `unverified` |
| AI Diagram-to-Code / Excalidraw+ Auth | — | Out of Scope | `unverified` |

## 3. Functional Requirements

### 3.1 Canvas Initialization & Interactive Surface (`F-001`, `F-009`)
- Mounting the whiteboard fills the host container (`1280x800` baseline viewport) with a full-bleed HTML5 2D canvas initialized to `viewBackgroundColor = "#ffffff"`, `theme = "light"`, `zoom.value = 1`, `scrollX = 0`, `scrollY = 0`, and `activeTool.type = "selection"` [REF: packages/excalidraw/appState.ts:20-124].
- Viewport zoom controls step zoom by `ZOOM_STEP = 0.1` within `[MIN_ZOOM = 0.1, MAX_ZOOM = 30]` while preserving the viewport center point via scroll-offset compensation [REF: packages/excalidraw/constants.ts:261-263] [REF: packages/excalidraw/scene/zoom.ts:3-35].

### 3.2 Drawing Primitives, Bound Arrows & Text (`F-002`..`F-005`)
- **Tool Selection & Unlocked Reset**: Clicking a creation tool (`rectangle`, `diamond`, `ellipse`, `arrow`, `text`) activates that tool; once the pointer gesture or text commit completes in default unlocked mode, `activeTool.type` returns automatically to `"selection"` [REF: packages/excalidraw/components/App.tsx:4676-4710].
- **Geometric Primitives (`F-002`, `F-003`)**: Pointer drag creates elements with default style properties (`strokeColor: "#1e1e1e"`, `backgroundColor: "transparent"`, `fillStyle: "solid"`, `strokeWidth: 2`, `strokeStyle: "solid"`, `roughness: 1`, `opacity: 100`) and a stable random integer `seed` so hand-drawn strokes remain invariant across re-renders [REF: packages/excalidraw/constants.ts:381-399] [REF: packages/excalidraw/element/newElement.ts:77-163].
- **Arrow Binding (`F-004`)**: Dragging an arrow between two bindable shapes populates `points` (`>= 2` local points), `endArrowhead: "arrow"`, `startBinding` and `endBinding` (`{ elementId, focus, gap }`), and reciprocal `boundElements` entries on both connected shapes [REF: packages/excalidraw/element/binding.ts:120-150] [REF: packages/excalidraw/element/types.ts:279-332].
- **Text Entry (`F-005`)**: Selecting the text tool and clicking the canvas opens an inline text editor (`fontSize: 20`, `fontFamily: 5`, `autoResize: true`); pressing `Escape` commits the text element to the scene [REF: packages/excalidraw/element/newElement.ts:238-250] [REF: packages/excalidraw/constants.ts:179-183].

### 3.3 Selection, Inspector Properties & History (`F-006`, `F-007`)
- Clicking an element selects it, draws transform bounds, and reveals the left properties inspector (`.App-menu__left`) exposing stroke color, background fill color, fill style, stroke width, stroke style, roughness (`0` Architect, `1` Artist, `2` Cartoonist), and opacity [REF: packages/excalidraw/actions/actionProperties.tsx:128-149] [REF: packages/excalidraw/colors.ts:88-105].
- Scene mutations push reversible increments onto `History.undoStack` and clear `redoStack`; triggering Undo/Redo transitions element state cleanly and toggles disabled states on Undo/Redo buttons [REF: packages/excalidraw/history.ts:16-158] [REF: packages/excalidraw/actions/actionHistory.tsx:51-128].

### 3.4 Theme Switching, Serialization & Reload Persistence (`F-008`, `F-010`, `F-011`)
- Toggling Dark Mode applies `.theme--dark` (`--default-bg-color: #121212`, `--island-bg-color: #232329`, `--theme-filter: invert(93%) hue-rotate(180deg)`) so canvas ink inverts visually without mutating raw hex color values stored in element JSON [REF: packages/excalidraw/css/theme.scss:166-268].
- Exporting serializes `{ type: "excalidraw", version: 2, elements, appState, files }` conforming to `09_contracts/excalidraw_scene.schema.json`; importing restores all elements and geometry with matching IDs [REF: packages/excalidraw/data/json.ts:43-123] [REF: packages/excalidraw/data/restore.ts:145-250].
- Host shells persist active scenes in browser `localStorage` under keys `"excalidraw"` and `"excalidraw-state"` for reload recovery (`F-011`) [REF: excalidraw-app/app_constants.ts:38-51] [REF: excalidraw-app/data/localStorage.ts:36-73].

## 4. Non-Functional & Clean-Room Constraints
- **Deterministic Rendering**: Identical element `seed` and geometry produce identical strokes across frames without flicker.
- **Visual Tolerance**: Clean-room UI reimplementation must maintain Mean Absolute Error (`MAE`) `<= 8.0%` against upstream baseline screenshots (`SCR-001`, `SCR-002`, `SCR-003`).
- **Clean-Room Separation**: Zero upstream source files, trademarks, or `.woff2` font binaries may be copied into `cleanroom-reimpl/` (see `04_environment/LICENSING.md`).

## Sources Read
- `packages/excalidraw/index.tsx` (lines 1-250)
- `packages/excalidraw/appState.ts` (lines 1-250)
- `packages/excalidraw/constants.ts` (lines 1-467)
- `packages/excalidraw/colors.ts` (lines 1-170)
- `packages/excalidraw/history.ts` (lines 1-200)
- `packages/excalidraw/store.ts` (lines 1-200)
- `packages/excalidraw/element/types.ts` (lines 1-412)
- `packages/excalidraw/element/newElement.ts` (lines 1-250)
- `packages/excalidraw/element/binding.ts` (lines 1-150)
- `packages/excalidraw/data/json.ts` (lines 1-156)
- `packages/excalidraw/data/restore.ts` (lines 1-250)
- `packages/excalidraw/scene/zoom.ts` (lines 1-35)
- `packages/excalidraw/actions/actionHistory.tsx` (lines 1-128)
- `packages/excalidraw/actions/actionCanvas.tsx` (lines 1-200)
- `packages/excalidraw/actions/actionProperties.tsx` (lines 1-150)
- `packages/excalidraw/css/theme.scss` (lines 1-268)
- `excalidraw-app/app_constants.ts` (lines 1-59)
- `excalidraw-app/data/localStorage.ts` (lines 1-99)
- `scripts/buildPackage.js` (lines 1-80)
- `packages/excalidraw/package.json` (lines 1-123)
