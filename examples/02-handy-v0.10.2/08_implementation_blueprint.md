# 08 — Clean-Room Implementation Blueprint (`Handy CR`)

## 1. Module Decomposition
A clean-room implementation targeting parity with `cjpais/Handy v0.10.2` divides into five decoupled layers `[REF: src-tauri/src/managers/history.rs:86-195]` `[REF: src-tauri/src/transcription_coordinator.rs:244-292]` `[REF: src/stores/settingsStore.ts:88-221]`:
1. **Persistence Engine (`CleanRoomStore` / SQLite `history.db`)**:
   - Executes `09_contracts/history.sql` directly on fresh database creation, guaranteeing exact 12-column schema parity and `PRAGMA user_version = 4` `[REF: 09_contracts/history.sql:1-35]`.
   - Implements `get_history(cursor, limit)` with `limit = min(limit, 100)` and `LIMIT limit + 1` lookahead to compute `has_more` without an extra `COUNT(*)` query `[REF: src-tauri/src/managers/history.rs:557-600]`.
   - Implements atomic `toggle_history_saved(id)` (`0 <-> 1`) and `delete_history(id)` with explicit `404` / not-found errors when `rowcount == 0`.
2. **Settings Repository (`settings.json`)**:
   - Persists `AppSettings` (`settings_schema_version = 3`) with enum validation for `shortcut_activation` (`hold_or_toggle | push_to_talk | toggle`), `theme` (`system | light | dark`), and structured `BindingResponse` updates for `bindings[id]`.
3. **Model Registry**:
   - Loads the offline curated ASR catalog (`whisper-medium`, `parakeet-tdt-0.6b-v3`, `parakeet-unified-en-0.6b`, `parakeet-tdt-0.6b-v2`, `cohere-transcribe-03-2026`, `canary-180m-flash`, `nemotron-3.5-asr-streaming-0.6b`) with download flags and capability bits (`supports_streaming`, `supports_translation`, `supports_language_detection`).
   - Enforces the downloaded-only guard on `POST /api/models/active`: returns HTTP `400` and preserves the previous `selected_model` if a target model is not downloaded or unknown.
4. **Dictation Coordinator & Deterministic STT Boundary**:
   - Encapsulates the lifecycle transitions (`idle -> recording -> transcribing -> completed` and `recording -> cancelled -> idle`) and emits structured lifecycle events matching `RecordingStateEvent`, `StreamPhaseEvent`, `TranscriptionCompleteEvent`, and `HistoryUpdatePayload`.
   - Separates local acoustic decoding behind a clean interface so deterministic test doubles can prove state-machine and SQLite parity before attaching a native `transcribe.cpp` / ONNX / whisper.cpp engine.
5. **UI Shell (`11_ui/tokens.json`)**:
   - Renders the 150 px sidebar, 720 px max-width scrollable settings column, 39 px bottom status footer, and five sections (`General`, `History`, `Models`, `Advanced`, `About`) using the exact measured CSS tokens under the separated **`Handy CR`** brand mark.

## 2. Reference Clean-Room Implementation
The working clean-room reference resides at `cleanroom-reimpl/app.py` (Python 3 stdlib `ThreadingHTTPServer` + `sqlite3` + embedded HTML/CSS/JS SPA, zero third-party packages, zero upstream source files) and passes `15 / 15` differential parity tests in `07_tests/reimpl_parity_report.json` `[REF: 07_tests/reimpl_parity_report.json:1-35]`.

## Sources Read
- `src-tauri/src/managers/history.rs` (`1-600`)
- `src-tauri/src/transcription_coordinator.rs` (`1-300`)
- `src-tauri/src/settings.rs` (`1-650`)
- `src/stores/settingsStore.ts` (`1-250`)
- `09_contracts/history.sql`
- `09_contracts/tauri_ipc.schema.json`
- `11_ui/tokens.json`
- `07_tests/reimpl_parity_report.json`
