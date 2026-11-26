# 01 — Product Requirements Document (PRD): `cjpais/Handy` (`v0.10.2`)

## 1. Product Overview & Value Proposition
Handy (`v0.10.2`, MIT License) is a cross-platform, privacy-first, **offline speech-to-text desktop application** built with Tauri v2 (Rust backend + React/TypeScript/Tailwind CSS v4 frontend) `[REF: package.json:1-73]` `[REF: src-tauri/tauri.conf.json:1-92]`. Users trigger dictation system-wide via configurable global keyboard shortcuts, record audio locally through CoreAudio/cpal with Voice Activity Detection (Silero or Earshot VAD), transcribe speech on-device using local GGUF models (`transcribe.cpp` 0.4.0 with Metal/Vulkan/CPU acceleration), paste the resulting transcript into the active window, and browse or manage persisted recordings in a local SQLite transcription history `[REF: src-tauri/src/managers/history.rs:15-45]` `[REF: src-tauri/src/catalog/mod.rs:1-54]`.

## 2. Target Target & Pinned Provenance
- **Repository**: `https://github.com/cjpais/Handy`
- **Pinned Tag / Commit SHA**: `v0.10.2` (`a822741f9c697b6f6a00c557e4817bf59ae70867`)
- **Official macOS Apple Silicon Release**: `Handy_0.10.2_aarch64.dmg` (14,979,688 bytes, SHA-256 `b8b893fbf9e8262abb0e363cb0ac6715cc69eac2fd6ffd8c0785278083a0e3ca`, GitHub Releases API digest verified `true`)
- **Official Mach-O Executable**: `Handy.app/Contents/MacOS/handy` (31,231,456 bytes, thin `arm64`, SHA-256 `6e0a7eac87e26690fec595f9e98bce2ac9979b7a20752f0b7abbd615b5d9ef3e`, Developer ID signed & notarization-stapled) `[REF: 04_environment/release_audit.json:1-120]`

## 3. Core Functional Requirements (Bound to Feature IDs)
| Feature ID | Requirement | Status | Evidence |
|---|---|---|---|
| `F-001` | Official macOS `arm64` DMG & Mach-O provenance matches pinned `v0.10.2` source across 133/133 Tauri IPC commands and `Info.plist`. | `observed` | `EV-001` |
| `F-002` | Load persisted application settings (`AppSettings`, `settings_schema_version = 3`) with safe partial-store fallback defaults. | `observed` | `EV-002` |
| `F-003` | Switch dictation shortcut activation mode between `hold_or_toggle` (Auto), `push_to_talk`, and `toggle` (replacing pre-0.10 boolean `push_to_talk`). | `observed` | `EV-003` |
| `F-004` | Rebind global `transcribe` and `cancel` keyboard shortcuts with structured `BindingResponse` validation. | `observed` | `EV-004` |
| `F-005` | Configure transcription language (`auto` or explicit ISO code) and resolve effective `LanguageStatus` per active model. | `observed` | `EV-005` |
| `F-006` | Toggle start/stop audio feedback chimes and enumerate available audio input/output devices. | `observed` | `EV-006` |
| `F-007` | Present offline ASR model catalog (Whisper, Parakeet, Nemotron, Canary, Cohere) split into downloaded ("On This Computer") and curated ("For Your Languages") sections with accuracy/speed/size metadata. | `observed` | `EV-007` |
| `F-008` | Switch the active ASR model among downloaded models and synchronize footer status + model-specific settings card. | `observed` | `EV-008` |
| `F-009` | Reject attempts to activate an undownloaded or unknown model without altering the active model selection. | `observed` | `EV-009` |
| `F-010` | Execute deterministic dictation lifecycle (`idle -> recording -> transcribing -> completed`) emitting typed lifecycle events and persisting completed entries to SQLite. | `observed` | `EV-010` |
| `F-011` | Cancel an active recording (`recording -> cancelled -> idle`) via `cancel_operation` with zero database writes. | `observed` | `EV-011` |
| `F-012` | Paginate transcription history entries newest-first (`ORDER BY id DESC`) with cursor-based `has_more` detection. | `observed` | `EV-012` |
| `F-013` | Star/unstar (`saved` boolean) individual history entries to exempt them from count/time retention cleanup, persisted to SQLite. | `observed` | `EV-013` |
| `F-014` | Delete individual history entries by ID from SQLite and return an error when deleting a non-existent ID. | `observed` | `EV-014` |
| `F-015` | Maintain forward-compatible SQLite `transcription_history` schema (`PRAGMA user_version = 4`, 12 columns including 3 dynamically added nullable columns) and expose Advanced settings shell. | `observed` | `EV-015` |

## 4. Non-Functional & Clean-Room Boundaries
- **Offline First**: Zero cloud API calls required for core dictation, model listing (bundled `catalog.json`), or history storage (`history.db`) `[REF: src-tauri/src/catalog/mod.rs:1-12]`.
- **Clean-Room Separation**: Functional contracts (`09`), runtime observations (`06`), and layout/token geometry (`11`) enable an independent clean-room reimplementation (`cleanroom-reimpl/app.py`, branded **`Handy CR`**) without copying upstream source code, logos, mascot art, or sound files `[REF: 04_environment/LICENSING.md:1-25]`.
- **Out-of-Scope / Stubbed in Isolated Browser Harness**: OS-level macOS TCC Microphone/Accessibility permission prompts, Carbon/CGEventTap global key interception, and Metal GGUF tensor execution are isolated behind documented test doubles so deterministic UI/IPC/SQLite parity can be proved reproducibly.

## Sources Read
- `package.json` (`1-73`)
- `src-tauri/tauri.conf.json` (`1-92`)
- `src/App.tsx` (`1-367`)
- `src/bindings.ts` (`1-1611`)
- `src-tauri/src/settings.rs` (`1-650`)
- `src-tauri/src/managers/history.rs` (`1-600`)
- `src-tauri/src/catalog/mod.rs` (`1-160`)
- `src-tauri/src/transcription_coordinator.rs` (`1-300`)
- `04_environment/release_audit.json`
- `04_environment/LICENSING.md`
