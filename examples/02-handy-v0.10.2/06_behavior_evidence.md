# 06 — Behavior Evidence Ledger Summary (`cjpais/Handy v0.10.2`)

- **Canonical Machine Ledger**: `06_evidence/ledger.jsonl` (`15` records, `15/15 observed`, schema-validated against `evidence.schema.json`)
- **Primary Artifact Digest**: `6e0a7eac87e26690fec595f9e98bce2ac9979b7a20752f0b7abbd615b5d9ef3e` (`Handy.app/Contents/MacOS/handy`, thin `arm64` Mach-O)
- **Consumed Directly By**: `07_tests/verify_parity.py` (reads `06_evidence/ledger.jsonl` at runtime for both baseline and clean-room differential tests)

## Evidence Inventory (`EV-001` – `EV-015`)
| Evidence ID | Feature ID | Category | Status | Observed Verification Summary | Screens |
|---|---|---|---|---|---|
| `EV-001` | `F-001` | `release_rea` | `observed` | Official `Handy_0.10.2_aarch64.dmg` digest verified; Mach-O `arm64` notarized; 133/133 IPC commands matched. | — |
| `EV-002` | `F-002` | `normal` | `observed` | `get_app_settings` returns schema v3 defaults (`hold_or_toggle`, `auto`, `whisper-medium`, `light`, `option+space`). | `SCR-001` |
| `EV-003` | `F-003` | `normal` | `observed` | `change_shortcut_activation_setting("push_to_talk")` updates persisted activation mode from `hold_or_toggle`. | `SCR-001` |
| `EV-004` | `F-004` | `normal` | `observed` | `change_binding("transcribe", "ctrl+shift+space")` returns `BindingResponse(success=true)` while preserving `default_binding`. | `SCR-001` |
| `EV-005` | `F-005` | `normal` | `observed` | `change_selected_language_setting("en")` updates `get_language_status` to `{ kind: "selected", language: "en" }`. | `SCR-001` |
| `EV-006` | `F-006` | `normal` | `observed` | `change_audio_feedback_setting(false)` persists toggle; `get_available_microphones` returns 2 devices with default flagged. | `SCR-001` |
| `EV-007` | `F-007` | `normal` | `observed` | `get_available_models` returns 7 curated ASR models (2 downloaded, streaming & translation capabilities flagged). | `SCR-002` |
| `EV-008` | `F-008` | `normal` | `observed` | `set_active_model("parakeet-tdt-0.6b-v3")` switches active model and emits ordered `loading_started -> loading_completed`. | `SCR-002` |
| `EV-009` | `F-009` | `error` | `observed` | `set_active_model("canary-180m-flash")` (not downloaded) is rejected and leaves active model unchanged. | `SCR-002` |
| `EV-010` | `F-010` | `realtime` | `observed` | Dictation pipeline transitions `idle -> recording -> transcribing -> completed`, yields `outcome="typed"`, and inserts SQLite row. | `SCR-001`, `SCR-003` |
| `EV-011` | `F-011` | `cancel_retry` | `observed` | `cancel_operation` transitions `recording -> cancelled -> idle`, resets `is_recording=false`, with 0 history row delta. | `SCR-001` |
| `EV-012` | `F-012` | `normal` | `observed` | `get_history_entries(cursor=null, limit=2)` returns 2 newest-first rows with `has_more=true`; cursor page 2 returns 1 row (`has_more=false`). | `SCR-003` |
| `EV-013` | `F-013` | `persistence` | `observed` | `toggle_history_entry_saved(3)` flips `saved` `false -> true -> false` in SQLite `transcription_history`. | `SCR-003`, `SCR-004` |
| `EV-014` | `F-014` | `persistence` | `observed` | `delete_history_entry(1)` removes row from SQLite (`3 -> 2`); second delete of ID `1` is rejected as missing. | `SCR-003`, `SCR-004` |
| `EV-015` | `F-015` | `ui_state` | `observed` | SQLite `PRAGMA user_version = 4` with exact 12 columns; live DOM tokens match `#fbfbfb`, `#0f0f0f`, `#faa2ca`, `#da5893`, `150px` sidebar, `39px` footer. | `SCR-005` |
