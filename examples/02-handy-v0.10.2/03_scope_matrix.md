# 03 — Feature Scope Matrix (`cjpais/Handy v0.10.2`)

- **Canonical Machine File**: `03_scope/features.json` (`15` atomic features, `is_macro_group` ratio = `0.000 <= 0.15`)
- **File Census**: `03_scope/files_census.json` (tracked git inventory at commit `a822741f9c697b6f6a00c557e4817bf59ae70867`: 491 total files, 323 supported code files — 228 TypeScript, 83 Rust, 8 CSS, 2 HTML, 1 JS, 1 Python)

## Feature Traceability Table
| Feature ID | Domain | Feature Name | Kind | Status | Evidence ID | Screen IDs | Test ID |
|---|---|---|---|---|---|---|---|
| `F-001` | Release & Build | Official macOS arm64 DMG & Mach-O REA Provenance Alignment | `release_boundary` | `observed` | `EV-001` | — | `TC-001` |
| `F-002` | Settings | Application Settings Read & Schema v3 Defaults | `setting` | `observed` | `EV-002` | `SCR-001` | `TC-002` |
| `F-003` | Shortcuts | Shortcut Activation Mode Switch (`hold_or_toggle` / `push_to_talk` / `toggle`) | `shortcut` | `observed` | `EV-003` | `SCR-001` | `TC-003` |
| `F-004` | Shortcuts | Transcribe Shortcut Keybinding Update | `shortcut` | `observed` | `EV-004` | `SCR-001` | `TC-004` |
| `F-005` | Transcription | Transcription Language Selection & Effective Language Status | `setting` | `observed` | `EV-005` | `SCR-001` | `TC-005` |
| `F-006` | Audio | Audio Feedback Setting Toggle & Microphone Device Enumeration | `setting` | `observed` | `EV-006` | `SCR-001` | `TC-006` |
| `F-007` | Models | Offline ASR Model Catalog Listing & Grading Join | `ui_screen` | `observed` | `EV-007` | `SCR-002` | `TC-007` |
| `F-008` | Models | Active ASR Model Selection & Status Synchronization | `setting` | `observed` | `EV-008` | `SCR-002` | `TC-008` |
| `F-009` | Models | Reject Selecting Undownloaded or Unknown ASR Model | `api_endpoint` | `observed` | `EV-009` | `SCR-002` | `TC-009` |
| `F-010` | Dictation Pipeline | Dictation Coordinator Lifecycle (`idle -> recording -> transcribing -> completed`) | `realtime_stream` | `observed` | `EV-010` | `SCR-001`, `SCR-003` | `TC-010` |
| `F-011` | Dictation Pipeline | Active Recording Cancellation (`recording -> cancelled -> idle`) | `realtime_stream` | `observed` | `EV-011` | `SCR-001` | `TC-011` |
| `F-012` | History | Cursor-Paginated Transcription History Listing | `ui_screen` | `observed` | `EV-012` | `SCR-003` | `TC-012` |
| `F-013` | History | History Entry Save / Star Toggle With SQLite Persistence | `storage` | `observed` | `EV-013` | `SCR-003`, `SCR-004` | `TC-013` |
| `F-014` | History | History Entry Deletion & Non-Existent ID Error Handling | `storage` | `observed` | `EV-014` | `SCR-003`, `SCR-004` | `TC-014` |
| `F-015` | Persistence & UI | SQLite History Schema v4 Migration, Added Columns & Advanced Settings UI | `migration` | `observed` | `EV-015` | `SCR-005` | `TC-015` |

## Explicit Non-Scope / Unverified Native OS Boundaries
- Live macOS TCC Accessibility/Microphone permission prompts, physical CoreAudio PCM recording, live Hugging Face GGUF network downloads, Metal GPU neural decoding, and OS-level global shortcut hooks (`CGEventTap` / Carbon fallback) are intentionally isolated behind deterministic test doubles in `04_reproduction_env.md`.
