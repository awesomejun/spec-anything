# 03 Feature Scope Matrix — Pomotroid v1.7.1

Machine-readable source of truth: `03_scope/features.json` (`14` atomic features, `macro_ratio=0.000`).

| Feature ID | Name | Kind | Evidence | Screens | Test ID | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `F-001` | Official macOS Universal Tauri Bundle Provenance | `release_boundary` | `EV-001` | `SCR-001` | `TC-001` | observed |
| `F-002` | Initial Focus Idle State and 25:00 Display | `ui_screen` | `EV-002` | `SCR-001` | `TC-002` | observed |
| `F-003` | Drift-Correcting Timer Start, Tick, and Pause Toggle | `api_endpoint` | `EV-003` | `SCR-002` | `TC-003` | observed |
| `F-004` | Circular SVG Progress Dial Countdown and Elapsed Math | `ui_screen` | `EV-004` | `SCR-001`, `SCR-002` | `TC-004` | observed |
| `F-005` | Skip Round Transition (Work to Short Break) | `api_endpoint` | `EV-005` | `SCR-003` | `TC-005` | observed |
| `F-006` | Full 4-Round Cycle to Long Break and Cycle Reset | `background_job` | `EV-006` | `SCR-004` | `TC-006` | observed |
| `F-007` | Optional Break Substitution when Long Breaks Disabled | `setting` | `EV-007` | `SCR-003` | `TC-007` | observed |
| `F-008` | Restart Current Round vs Full Sequence Reset | `api_endpoint` | `EV-008` | `SCR-001` | `TC-008` | observed |
| `F-009` | SQLite WAL Settings Persistence and MIGRATION_1..6 | `migration` | `EV-009` | `SCR-005` | `TC-009` | observed |
| `F-010` | Volume 0..1 UI Slider to 0..100 SQLite Scaling & Mute | `setting` | `EV-010` | `SCR-001` | `TC-010` | observed |
| `F-011` | 38 Bundled Themes and Live Light/Dark CSS Resolution | `setting` | `EV-011` | `SCR-001`, `SCR-004` | `TC-011` | observed |
| `F-012` | Settings 6-Section Navigation Window | `ui_screen` | `EV-012` | `SCR-005` | `TC-012` | observed |
| `F-013` | Statistics Today/Week/All-Time Views & Aggregation | `storage` | `EV-013` | `SCR-006` | `TC-013` | observed |
| `F-014` | Local Keyboard Shortcuts (`Space`/`ArrowLeft`/`ArrowRight`/`m`) | `shortcut` | `EV-014` | `SCR-001` | `TC-014` | observed |
