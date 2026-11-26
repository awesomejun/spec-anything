# Target Stack Observation Adapters

Select the matching adapter(s) in **Phase 1** based on `.spec-anything/source_map.json` and `04_environment/release_audit.json`.

## 1. Web & Backend Service (Go / Node / Python / Rust + SPA + DB)
- **Static Focus**: HTTP routers, middleware chains, auth/JWT/session verification, validation schemas, ORM/raw SQL migrations, WebSocket/SSE brokers, scheduled jobs, embedded SPA assets (`embed.FS`, `dist/`).
- **Release (REA) Focus**: Verify binary/tarball SHA-256 against `checksums.txt`, inspect `go version -m` / `otool -L` / `ldd` / `codesign`, check whether embedded frontend assets match the source build or include release-only flags.
- **Runtime Focus (`T2`/`T3`)**: Launch on isolated `--dir` + loopback port (`127.0.0.1:<ephemeral>`). Test CRUD, auth failure (`401`/`403`), validation error (`400`), realtime stream ordering (SSE/WS), DB file tables (`sqlite3 .schema`), and **process kill + restart persistence**. Capture UI states via headless Playwright and extract live `getComputedStyle` design tokens.

## 2. Electron Desktop Application
- **Static Focus**: `main` process entry, `preload` `contextBridge.exposeInMainWorld`, `ipcMain.handle`/`on`, BrowserWindow security flags (`contextIsolation`, `nodeIntegration`, `sandbox`), native menus, tray, auto-updater, local HTTP/RPC sidecars.
- **Release (REA) Focus**: Unpack/inspect `app.asar` file listing & SHA-256 against compiled source, check `Info.plist`, code signature, Electron Fuses (`@electron/fuses`), and bundled extra resources (`Resources/`). Flag any release-only modules or transpiled overlays.
- **Runtime Focus (`T2`/`T3`)**: Launch with isolated `HOME`/`APPDATA`/`userData` directory. Capture main window states, context menus, modal dialogs, IPC responses, and persisted state across restart.

## 3. CLI Tool & Library / SDK
- **Static Focus**: Argument parser flags/subcommands, stdin/stdout/stderr formatting, exit codes, environment variables, config file precedence, public exported functions/types.
- **Release (REA) Focus**: Verify binary SHA-256, Mach-O/ELF dynamic links, embedded version metadata, manpages/completions shipped in archive.
- **Runtime Focus (`T2`/`T3`)**: Golden-file differential tests across normal, boundary, invalid-flag, non-UTF8/empty input, signal interruption (`SIGINT`), and deterministic exit code verification. Mark `05` and `11` explicitly as `N/A` (headless CLI) unless TUI screens are captured.

## 4. Native Desktop / Mobile Application
- **Static Focus**: Entry lifecycle, view controllers / SwiftUI / Jetpack Compose screens, persistence (CoreData/SQLite/Room/Keychain), IPC/XPC/Binder services, permissions/entitlements.
- **Release (REA) Focus**: Within authorized scope only—inspect code signature, entitlements, `Info.plist` / `AndroidManifest.xml`, Mach-O slices (`lipo`/`otool`), exported Objective-C/Swift/JNI symbol tables, asset catalog metadata (`Assets.car`). Never bypass protections or DRM.
- **Runtime Focus (`T2`/`T3`)**: Isolated simulator/emulator or sandboxed user profile; capture UI hierarchy, accessibility tree, visual screenshots, and storage snapshots.
