# 09 — Machine-Readable Contracts (`cjpais/Handy v0.10.2`)

## 1. Contract Files
- **`09_contracts/tauri_ipc.schema.json`**: JSON Schema Draft `2020-12` specifying:
  - `AppSettings` (`settings_schema_version = 3`, `ShortcutActivation`, `ShortcutBinding`, `Theme`, `OverlayStyle`, `RecordingRetentionPeriod`, `PasteMethod`, `ClipboardHandling`)
  - `ModelInfo` and `ModelSource` (`HuggingFace | Url | Local`)
  - `HistoryEntry`, `PaginatedHistory`, and `HistoryUpdatePayload` (`added | updated | deleted | toggled`)
  - `RecordingStateEvent` (`started | locked | stopped | cancelled`) and `TranscriptionCompleteEvent` (`typed | empty | silent | failed`)
  - `LanguageStatus` (`selected | auto | detector_missing | auto_unavailable`)
  - `CoreCommands` argument and return contracts for all core Tauri `invoke` commands verified in `06_evidence/ledger.jsonl`.
- **`09_contracts/history.sql`**: Executable SQLite DDL verified in `sqlite3 :memory:` and used verbatim by both the baseline harness and `cleanroom-reimpl/app.py`:
  - Applies `MIGRATIONS[0..3]` (`transcription_history` base table + `post_processed_text`, `post_process_prompt`, `post_process_requested`).
  - Sets `PRAGMA user_version = 4` (matching `rusqlite_migration`).
  - Appends the 3 forward-compatible nullable columns (`source_name`, `language`, `language_source`) outside the `user_version` bump, preserving backwards compatibility with older release binaries.

## 2. Upstream IPC to Clean-Room HTTP Mapping
| Upstream Tauri Command (`src/bindings.ts`) | Clean-Room HTTP Endpoint (`cleanroom-reimpl/app.py`) | Feature ID |
|---|---|---|
| `get_app_settings` | `GET /api/settings` | `F-002` |
| `change_shortcut_activation_setting` | `PATCH /api/settings` (`{ shortcut_activation }`) | `F-003` |
| `change_binding` | `POST /api/settings/binding` (`{ id, binding }`) | `F-004` |
| `change_selected_language_setting` / `get_language_status` | `PATCH /api/settings` / `GET /api/language-status` | `F-005` |
| `change_audio_feedback_setting` / `get_available_microphones` | `PATCH /api/settings` / `GET /api/audio/microphones` | `F-006` |
| `get_available_models` | `GET /api/models` | `F-007` |
| `set_active_model` / `get_current_model` | `POST /api/models/active` / `GET /api/models/active` | `F-008`, `F-009` |
| Dictation coordinator (`on_input`) | `POST /api/dictate` | `F-010` |
| `cancel_operation` | `POST /api/dictate/cancel` | `F-011` |
| `get_history_entries(cursor, limit)` | `GET /api/history?cursor=&limit=` | `F-012` |
| `toggle_history_entry_saved(id)` | `POST /api/history/{id}/toggle-saved` | `F-013` |
| `delete_history_entry(id)` | `DELETE /api/history/{id}` | `F-014` |
| `HistoryManager::apply_migrations` | `GET /api/db/schema` + `09_contracts/history.sql` | `F-015` |
