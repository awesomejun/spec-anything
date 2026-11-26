# 08 Clean-Room Implementation Blueprint — Pomotroid v1.7.1

## 1. Target Repository Structure (`cleanroom-reimpl/`)
A zero-dependency Python 3 + SQLite WAL + vanilla HTML/CSS/SVG clean-room reimplementation (`PomoCR`) built exclusively from `09_contracts/` and `11_ui/tokens.json` with a separated `CR` brand mark [REF: src-tauri/src/timer/sequence.rs:38-129] [REF: src-tauri/src/db/migrations.rs:5-91] [REF: src/lib/components/TimerDial.svelte:16-72].

## 2. Upstream-to-Clean-Room Mapping
| Upstream Module | Clean-Room Module | Parity Tests |
| :--- | :--- | :--- |
| `src-tauri/src/timer/{engine,sequence}.rs` | `cleanroom-reimpl/app.py::PomoEngine` | `TC-002`, `TC-003`, `TC-005`..`TC-008` |
| `src-tauri/src/db/{mod,migrations,queries}.rs` | `PomoEngine._migrate` & `get_stats` | `TC-009`, `TC-013` |
| `src-tauri/src/themes/mod.rs` | `THEMES` + CSS variable injector | `TC-011` |
| `src/lib/components/{Timer,TimerDial,TimerFooter}.svelte` | `INDEX_HTML` SVG dial + shortcut listener | `TC-004`, `TC-010`, `TC-014` |
| `src/routes/{settings,stats}/+page.svelte` | `SETTINGS_HTML`, `STATS_HTML` | `TC-012`, `TC-013` |

## 3. IP & Asset Isolation Rules
- Zero upstream font files (`MonaSansVF.woff2`), audio clips, or app icons are redistributed; clean-room renders system sans/monospace fonts and displays an explicit `CR` mark [REF: src/app.css:9-24].

## Sources Read
- `src-tauri/src/timer/sequence.rs`
- `src-tauri/src/db/migrations.rs`
- `src/lib/components/TimerDial.svelte`
- `src/app.css`
