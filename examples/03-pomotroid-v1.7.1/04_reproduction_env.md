# 04 Reproduction Environment & REA Release Audit — Pomotroid v1.7.1

## 1. Pinned Source & Official Release Provenance
- **Repository**: `https://github.com/Splode/pomotroid` (MIT License)
- **Tag / Commit SHA**: `v1.7.1` / `4a02ac7bff9083dc5b2cc42fa7c4683c1fc15805`
- **Official macOS Archive**: `Pomotroid.app.tar.gz` (`16,826,525` bytes, SHA-256 `b12dcca6a06705d773af8cffa99d2b32ea126ea441130301cde83a084e20fbdc`)
- **Official Universal Mach-O Binary**: `Pomotroid.app/Contents/MacOS/pomotroid` (SHA-256 `bacf6c674781bc0ac1cb390f1bf2bbfe7dc9aeb999d52e0d4f66fb7f2a0b4f8f`, `x86_64 + arm64`, adhoc linker-signed, `CFBundleIdentifier=com.splode.pomotroid`)
- **Provenance Match**: `strings` inspection of the official universal binary directly confirmed `[app] version=1.7.1+4a02ac7 sha=4a02ac7bff9083dc5b2cc42fa7c4683c1fc15805` — exact commit parity between source and official release.

## 2. REA Source-vs-Distribution Findings
1. `Pomotroid.app/Contents/Resources/` contains only `icon.icns`; all 38 built-in theme JSONs and compiled SvelteKit assets are embedded inside the Mach-O executable via Rust `include_str!` and Tauri asset bundling.
2. Mach-O links `WebKit`, `AppKit`, `CoreAudio`, `AudioToolbox`, `Security`, and `Carbon` with `LSMinimumSystemVersion=10.13`.
3. Machine-readable audit stored in `04_environment/release_audit.json`.

## 3. Isolated Local Runtime & Test Double Boundary
- Built upstream Svelte 5 static bundle (`bun install && bun run paraglide:compile && bun run build`, `3.03s`), served on `127.0.0.1` ephemeral port and driven in Chromium Playwright (`360×478@2x`, `720×520@2x`, `840×520@2x`) with deterministic Tauri IPC bridge and 6-session stats fixture.
