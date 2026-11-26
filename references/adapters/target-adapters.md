# Target Stack Observation Adapters

Select the matching adapter(s) in **Phase 1** based on `scripts/doctor.py`, `.spec-anything/source_map.json`, and `04_environment/release_audit.json`. For optional **Ghidra**, **IDA (`idalib` / `ida-mcp`)**, **Frida**, and **Clean-Room vs. Deep** rules, follow `references/adapters/re-backends.md`.

## 1. Web & Backend Service (Go / Node / Python / Rust + SPA + DB)
- **Static Focus**: HTTP routers, middleware chains, auth/JWT/session verification, validation schemas, ORM/raw SQL migrations, WebSocket/SSE brokers, scheduled jobs, embedded SPA assets (`embed.FS`, `dist/`).
- **Release Artifact (RAA) Focus**: Verify binary/tarball SHA-256 against `checksums.txt` or npm `dist.integrity` (SHA-512), inspect `go version -m` / `otool -L` / `readelf -d` / `codesign`, check whether embedded frontend assets match the source build or include release-only flags.
- **Runtime Focus (`T2`/`T3`)**: Launch on isolated `--dir` + loopback port (`127.0.0.1:<ephemeral>`). Test CRUD, auth failure (`401`/`403`), validation error (`400`), realtime stream ordering (SSE/WS), DB file tables (`sqlite3 .schema`), and **process kill + restart persistence**. Capture multi-state & multi-viewport UI screenshots via headless Playwright and extract live `getComputedStyle` design tokens.

## 2. Desktop WebView Apps (Tauri v2 & Electron)
- **Static Focus**:
  - **Tauri v2**: Rust `#[tauri::command]` handlers, `generate_handler![]`, TypeScript bindings (`bindings.ts`), `tauri.conf.json` capabilities/CSP, SQLite WAL migrations (`MIGRATION_1..N`).
  - **Electron**: `main` process entry, `preload` `contextBridge.exposeInMainWorld`, `ipcMain.handle`/`on`, BrowserWindow flags (`contextIsolation`, `nodeIntegration`, `sandbox`), native menus, tray, auto-updater.
- **Release Artifact (RAA) Focus**: Audit `.dmg` / `.app` / `.AppImage` / `.msi` SHA-256, Mach-O architectures (`lipo -archs`), notarization/Hardened Runtime (`codesign -dv`), `Info.plist`, `app.asar` listing, and verify shipped IPC command names against source (optionally confirming native symbols via **Ghidra** or **IDA**).
- **Runtime Focus (`T2`/`T3`)**: Launch with isolated `HOME`/`APPDATA`/`userData` directory. Capture main/settings/history/modal screens across light & dark themes, verify persisted SQLite/JSON settings across restart, and optionally trace read-only IPC or SQLite C-API boundaries via `scripts/frida_trace_bridge.py`.

## 3. CLI Tool & Library / SDK
- **Static Focus**: Argument parser flags/subcommands, stdin/stdout/stderr formatting, exit codes, environment variables, config file precedence, public exported functions/types (ESM/CJS/PyPI/Crate APIs).
- **Release Artifact (RAA) Focus**: Verify archive/binary SHA-256, Mach-O/ELF dynamic links, embedded version metadata, npm `dist/prod/index.js` exported symbol inventory, manpages/completions shipped in archive.
- **Runtime Focus (`T2`/`T3`)**: Golden-file differential tests across normal, boundary, invalid-flag, non-UTF8/empty input, signal interruption (`SIGINT`), and deterministic exit code verification. Mark `05` and `11` explicitly as `N/A` (headless CLI) unless TUI/Canvas screens are captured.

## 4. Native Desktop / Mobile Application (macOS / iOS / Android / C / C++ / Rust)
- **Static Focus**: Entry lifecycle, SwiftUI/AppKit/UIKit/Jetpack Compose screens, persistence (CoreData/SQLite/Room/UserDefaults), IPC/XPC/Binder services, permissions/entitlements.
- **Release Artifact (RAA) Focus**: Within authorized scope only — inspect code signature, entitlements, `Info.plist` / `AndroidManifest.xml`, Mach-O slices (`lipo`/`otool`), exported Objective-C/Swift/JNI symbol tables (`nm`, `demangle_swift`), asset catalog metadata (`Assets.car`). When stripped or compiled binaries need function/struct verification in `deep` mode, use headless **Ghidra** (`pyghidra-mcp` / `rea-ghidra`) or **IDA Pro** (`HexRaysSA/ida-mcp` / `idalib`). Never bypass protections or DRM.
- **Runtime Focus (`T2`/`T3`)**: Isolated simulator/emulator or sandboxed user profile; capture UI hierarchy, accessibility tree, visual screenshots, storage snapshots, and optional read-only **Frida** traces (`scripts/frida_trace_bridge.py`) normalized into `06_evidence/ledger.jsonl`.
