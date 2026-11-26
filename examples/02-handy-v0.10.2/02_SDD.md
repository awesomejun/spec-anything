# 02 — Software Design Document (SDD): `cjpais/Handy` (`v0.10.2`)

## 1. System Architecture
Handy `v0.10.2` uses a **Tauri v2 hybrid desktop architecture** combining a React 18 + TypeScript + Zustand + Tailwind CSS v4 frontend (`src/`) with a Rust native core (`src-tauri/src/`) communicating exclusively across 133 `tauri-specta`-typed IPC commands and 7 typed push events `[REF: src/bindings.ts:7-1076]` `[REF: src-tauri/tauri.conf.json:1-92]`.

### Major Subsystems
1. **Frontend UI & State Stores (`src/`)**:
   - `App.tsx` manages onboarding gates (`flow | permissions | migration | replaceModel | done`), keyboard debug shortcut (`Cmd/Ctrl+Shift+D`), and the primary shell (`Sidebar` + scrollable section view + fixed `Footer` + `FileDropOverlay`) `[REF: src/App.tsx:41-356]`.
   - `settingsStore.ts` (Zustand + `subscribeWithSelector`) maps every `AppSettings` key to its typed `commands.change*` IPC mutator with optimistic updates and error rollback `[REF: src/stores/settingsStore.ts:88-245]`.
   - `modelStore.ts` (Zustand + Immer) manages catalog hydration, active model selection, download progress events, and local directory rescans `[REF: src/stores/modelStore.ts:53-300]`.
2. **Tauri IPC & Settings Persistence (`src-tauri/src/settings.rs`, `src-tauri/src/commands/`)**:
   - `AppSettings` (`settings_schema_version = 3`) persists via `tauri-plugin-store` (`settings_store.json`) with `#[serde(default)]` field fallbacks and forward migrations (e.g., migrating legacy boolean `push_to_talk` into the 3-variant `ShortcutActivation` enum) `[REF: src-tauri/src/settings.rs:173-186]` `[REF: src-tauri/src/settings.rs:581-650]`.
3. **Dictation Coordinator (`src-tauri/src/transcription_coordinator.rs`)**:
   - A dedicated single-threaded command loop owns `CoordinatorState` (`Stage::Idle`, `Stage::Recording(binding_id)`, `Stage::Processing`) with 30 ms input debounce, 50 ms X11 auto-repeat release grace, hold-vs-tap classification (`hold_threshold_ms = 300`), and busy-pipeline `PendingPress` remember/forget parity `[REF: src-tauri/src/transcription_coordinator.rs:14-291]`.
4. **Offline Model Catalog & Inference (`src-tauri/src/catalog/`, `src-tauri/src/managers/model.rs`)**:
   - Compiles `catalog.json` (schema v2, `transcribeCpp` 0.4.0, 76 models, 29 curated ASR entries) directly into the binary so the Models screen operates offline `[REF: src-tauri/src/catalog/mod.rs:1-154]`.
   - Links macOS `Metal.framework`, `MetalKit.framework`, `Accelerate.framework`, `AVFoundation.framework`, `AudioToolbox.framework`, and weak `CoreAudio.framework` / `FoundationModels.framework` in the official `arm64` Mach-O executable `[REF: 04_environment/release_audit.json:24-75]`.
5. **SQLite History Persistence (`src-tauri/src/managers/history.rs`)**:
   - Stores transcripts and recording metadata in `<app_data_dir>/history.db` using `rusqlite` + `rusqlite_migration` (`PRAGMA user_version = 4`) plus 3 dynamically appended nullable columns (`source_name`, `language`, `language_source`) so older release builds can still open newer databases `[REF: src-tauri/src/managers/history.rs:22-45]` `[REF: src-tauri/src/managers/history.rs:164-195]`.

## 2. REA Triangulation Findings (Source vs. Official macOS Binary)
- **Exact IPC Parity**: All **133/133** `TAURI_INVOKE` commands in `src/bindings.ts` were verified present as embedded symbols/strings inside the official `Handy.app/Contents/MacOS/handy` Mach-O binary (`6e0a7eac87e26690fec595f9e98bce2ac9979b7a20752f0b7abbd615b5d9ef3e`) `[REF: 04_environment/release_audit.json:112-155]`.
- **Retired Command Confirmation**: Pre-`v0.10` command names `change_push_to_talk` and `change_bound_keys` are confirmed **absent** from both `src/bindings.ts` and the official Mach-O binary; they were superseded by `change_shortcut_activation_setting` and `change_binding`.
- **CI Release Signing Override**: `src-tauri/tauri.conf.json` specifies `"signingIdentity": "-"` for local builds, while the official macOS release DMG is signed with `Developer ID Application: Christopher Pais (UWFLB4GC25)`, Hardened Runtime (`0x10000`), and a stapled Apple notarization ticket `[REF: src-tauri/tauri.conf.json:39-45]` `[REF: 04_environment/release_audit.json:76-92]`.

## 3. Clean-Room Architectural Mapping
The clean-room reimplementation (`cleanroom-reimpl/app.py`) implements the exact functional contracts (`09_contracts/history.sql`, `09_contracts/tauri_ipc.schema.json`) and visual design tokens (`11_ui/tokens.json`) as a zero-dependency Python 3 stdlib HTTP server + real SQLite `history.db` + vanilla HTML/CSS/JS SPA, replacing Tauri IPC invokes with RESTful JSON endpoints while maintaining 1-to-1 behavioral equivalence across all 15 verified test cases `[REF: 07_tests/reimpl_parity_report.json:1-30]`.

## Sources Read
- `src/bindings.ts` (`1-1611`)
- `src/App.tsx` (`1-367`)
- `src/stores/settingsStore.ts` (`1-250`)
- `src/stores/modelStore.ts` (`1-300`)
- `src-tauri/tauri.conf.json` (`1-92`)
- `src-tauri/src/settings.rs` (`1-650`)
- `src-tauri/src/transcription_coordinator.rs` (`1-300`)
- `src-tauri/src/managers/history.rs` (`1-600`)
- `src-tauri/src/catalog/mod.rs` (`1-160`)
- `04_environment/release_audit.json`
- `07_tests/reimpl_parity_report.json`
