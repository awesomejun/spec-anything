# 04 — Reproduction Environment & Official Release REA Audit

## 1. Pinned Source & Official Release Digests
- **Upstream Repository**: `https://github.com/cjpais/Handy`
- **Pinned Git Tag**: `v0.10.2`
- **Pinned Commit SHA**: `a822741f9c697b6f6a00c557e4817bf59ae70867`
- **Release Published At**: `2026-11-24T06:28:41Z`
- **Official macOS Installer Archive**: `Handy_0.10.2_aarch64.dmg`
  - **Size**: `14,979,688` bytes
  - **SHA-256**: `b8b893fbf9e8262abb0e363cb0ac6715cc69eac2fd6ffd8c0785278083a0e3ca`
  - **Upstream Checksum Verification**: `true` (matched GitHub Releases API v3 `digest` field bit-for-bit)
- **Official Extracted Mach-O Executable**: `Handy.app/Contents/MacOS/handy`
  - **Size**: `31,231,456` bytes
  - **SHA-256**: `6e0a7eac87e26690fec595f9e98bce2ac9979b7a20752f0b7abbd615b5d9ef3e`
  - **Architecture (`lipo -info`)**: `Non-fat file: Mach-O 64-bit executable arm64`
  - **Code Signing (`codesign -dvv`)**: `com.pais.handy`, `Developer ID Application: Christopher Pais (UWFLB4GC25)`, Hardened Runtime (`0x10000`), `Notarization Ticket=stapled`, `Runtime Version=26.5.0`, `Sealed Resources files=19`
- **Machine Audit Artifact**: `04_environment/release_audit.json`
- **Licensing Boundary**: `04_environment/LICENSING.md`

## 2. REA Source-vs-Binary Verification Summary
1. **133 / 133 Tauri IPC Commands Matched**: Every `TAURI_INVOKE` symbol exported by `src/bindings.ts` was found verbatim inside `Handy.app/Contents/MacOS/handy`.
2. **Retired Pre-0.10 Commands Confirmed Absent**: `change_push_to_talk` and `change_bound_keys` do not exist in either `v0.10.2` source or the official Mach-O binary; they were superseded by `change_shortcut_activation_setting` and `change_binding`.
3. **SQLite & Embedded Frontend Markers Confirmed**: `history.db`, `transcription_history`, `post_processed_text`, `post_process_requested`, `source_name`, `language_source`, `settings_store.json`, `index.html`, `tauri://localhost`, `transcribeCpp`, and all 7 event channel names are verified present in the official binary.
4. **Native Frameworks (`otool -L`)**: Confirmed dynamic linkage to `Metal`, `MetalKit`, `Accelerate`, `AVFoundation`, `AudioToolbox`, `CoreAudio (weak)`, `Carbon`, `ApplicationServices`, `WebKit`, and `FoundationModels (weak)` (Apple Intelligence).
5. **Signing Override Explained**: Repository `tauri.conf.json` sets `signingIdentity: "-"` (local dev default), while CI release signing injects Developer ID `UWFLB4GC25` + stapled notarization.

## 3. Analysis Toolchain & Host Environment
- **Host OS / Arch**: Darwin (`arm64`)
- **Frontend Runner**: `bun` `1.3.6` + `vite` `6.4.1` (`127.0.0.1:1420`)
- **Browser Automation**: Python `3.13` + `playwright` (Chromium headless, `1024x700@1x`, `color_scheme="light"`, `locale="en-US"`, `timezone_id="UTC"`)
- **Database Engine**: `sqlite3` (in-process Python stdlib `sqlite3` executing `09_contracts/history.sql`)
- **Binary Inspection Tools**: `hdiutil` (read-only attach/detach), `shasum -a 256`, `lipo -info`, `otool -L`, `codesign -dvv`, `plutil -convert json`

## 4. Deterministic Test Double & Synthetic Seed Separation
Per REA verification discipline, **non-deterministic / hardware-bound layers are explicitly separated from verified app logic**:
- **Real / Unstubbed**: Upstream React UI (`src/App.tsx`, `GeneralSettings`, `ModelsSettings`, `HistorySettings`, `AdvancedSettings`, `AboutSettings`, `Footer`), Zustand stores (`settingsStore`, `modelStore`), Tailwind CSS v4 tokens (`src/styles/theme.css`), `@handy-computer/models` grading join, and SQLite `transcription_history` DDL + CRUD queries (`09_contracts/history.sql`).
- **Deterministic Test Double (`window.__TAURI_INTERNALS__`)**:
  - Replaces Tauri native invoke bridge in Playwright so the real upstream Vite frontend executes without macOS TCC Microphone/Accessibility modal blocks.
  - Provides 7 curated ASR models copied verbatim from `src-tauri/src/catalog/catalog.json` (`whisper-medium` active & downloaded, `parakeet-tdt-0.6b-v3` downloaded, 5 remote models).
  - Seeds 3 deterministic history rows in SQLite `transcription_history` (`timestamps` `1795442400`, `1795446000`, `1795449600` UTC).
  - Stubs local acoustic capture and GGUF neural decoding deterministically while preserving exact coordinator state transitions (`idle -> recording -> transcribing -> completed` and `recording -> cancelled -> idle`).
