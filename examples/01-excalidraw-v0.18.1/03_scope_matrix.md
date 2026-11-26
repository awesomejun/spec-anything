# 03 — Feature Scope Matrix (`F-001` .. `F-012`)

Canonical machine-readable matrix: `03_scope/features.json` (validated against `feature_matrix.schema.json`; **12 atomic features**, `is_macro_group` ratio = **0.000** `<= 0.15`).
Tracked repository census: `03_scope/files_census.json` (commit `a2ec2889babf7d2295469c6d90ebe77fae57df84`).

| Feature ID | Domain | Feature Name | Kind | Status | Evidence | Screens | Contracts | Parity Test |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `F-001` | `canvas_lifecycle` | Initial Whiteboard Mount & Interactive Canvas Surface | `ui_screen` | `observed` | `EV-001` | `SCR-001` | `canvas_actions.schema.json` | `TC-001` |
| `F-002` | `drawing_primitives` | Toolbar Selection & Hand-Drawn Rectangle Creation | `ui_screen` | `observed` | `EV-002` | `SCR-002` | `excalidraw_scene.schema.json`, `canvas_actions.schema.json` | `TC-002` |
| `F-003` | `drawing_primitives` | Hand-Drawn Ellipse Creation via Pointer Drag | `ui_screen` | `observed` | `EV-003` | `SCR-002` | `excalidraw_scene.schema.json`, `canvas_actions.schema.json` | `TC-003` |
| `F-004` | `connectors` | Arrow Creation & Bidirectional Shape Binding | `ui_screen` | `observed` | `EV-004` | `SCR-002` | `excalidraw_scene.schema.json`, `canvas_actions.schema.json` | `TC-004` |
| `F-005` | `typography` | Canvas Text Element Creation & Commit Flow | `ui_screen` | `observed` | `EV-005` | `SCR-002` | `excalidraw_scene.schema.json`, `canvas_actions.schema.json` | `TC-005` |
| `F-006` | `properties_inspector` | Element Selection & Left Properties Panel Mutations | `ui_screen` | `observed` | `EV-006` | `SCR-004` | `excalidraw_scene.schema.json`, `canvas_actions.schema.json` | `TC-006` |
| `F-007` | `history` | Incremental Undo & Redo Stack Transitions | `shortcut` | `observed` | `EV-007` | `SCR-004` | `canvas_actions.schema.json` | `TC-007` |
| `F-008` | `theming` | Light & Dark Theme Token Switch with Canvas Filter Inversion | `setting` | `observed` | `EV-008` | `SCR-003` | `canvas_actions.schema.json` | `TC-008` |
| `F-009` | `viewport` | Viewport Zoom Stepping & Center-Preserving Scroll Offset | `setting` | `observed` | `EV-009` | `SCR-001` | `canvas_actions.schema.json` | `TC-009` |
| `F-010` | `serialization` | Excalidraw v2 JSON Export Schema & Restore Roundtrip | `storage` | `observed` | `EV-010` | `SCR-005` | `excalidraw_scene.schema.json` | `TC-010` |
| `F-011` | `persistence` | Host localStorage Scene & AppState Persistence Across Reload | `storage` | `observed` | `EV-011` | `SCR-005` | `excalidraw_scene.schema.json`, `canvas_actions.schema.json` | `TC-011` |
| `F-012` | `release_rea` | Official npm Distribution REA Integrity & Source-vs-Bundle Audit | `release_boundary` | `observed` | `EV-012` | — | `release_audit.json` | `TC-012` |

## Static Codebase Coverage Summary (`.spec-anything/source_map.json`)
- **Total tracked files**: `1,116` (`621` supported code files across TypeScript `513`, SCSS `76`, JavaScript `27`, CSS `3`, HTML `2`; `95` test files).
- **Extracted entities**: `1,431` exported symbols; `373` CSS custom property declarations; `139` npm manifest dependencies; `0` loud parser warnings.
