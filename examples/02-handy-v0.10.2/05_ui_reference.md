# 05 — Multi-State UI Reference Gallery (`cjpais/Handy v0.10.2`)

- **Manifest**: `05_ui/screens.json`
- **Capture Configuration**: Chromium `1024x700@1x`, `theme = light`, `locale = en-US`, `timezone = UTC`
- **Upstream Source**: Live Vite `6.4.1` dev server rendering `src/App.tsx` with deterministic Tauri v2 IPC test double backed by SQLite `history.db`.

## Captured Reference Screens
| Screen ID | Feature ID | State | File | Observed UI Content |
|---|---|---|---|---|
| `SCR-001` | `F-002` | `normal` | `05_ui/screenshots/SCR-001_general_settings.png` | Left 150 px sidebar (`General` active in `#faa2ca/80%`), `GENERAL` (Transcribe `Option + Space`, Shortcut Behavior `Auto`, Cancel `Escape`), `LANGUAGES` (`English`), `WHISPER MEDIUM SETTINGS` (`Language: Auto`, `Translate to English`), `SOUND` (`MacBook Pro Microphone`, `Audio Feedback: ON`, `MacBook Pro Speakers`, `Volume 50%`), and 39 px footer (`Whisper Medium`, `v0.10.2`). |
| `SCR-002` | `F-007` | `normal` | `05_ui/screenshots/SCR-002_models_catalog.png` | `Models` header + `Change languages` link, search bar + `Live preview`/`Translates` filters, `ON THIS COMPUTER` section (`Whisper Medium` active pink check + gray highlight, `Parakeet TDT 0.6B v3` ready), and `FOR YOUR LANGUAGES` section (5 curated models with grades `A−`/`B+`/`B`, speed bars, and sizes). |
| `SCR-003` | `F-012` | `normal` | `05_ui/screenshots/SCR-003_history_list.png` | `HISTORY` header + `Transcribe File` & `Open Recordings Folder` buttons, 3 SQLite entries newest-first (`November 23, 2026 at 04:00 PM`, `03:00 PM` starred pink, `02:00 PM`), italic transcript text, Copy/Star/Retry/Delete icons, and playback scrubber. |
| `SCR-004` | `F-013` | `mutated` | `05_ui/screenshots/SCR-004_history_mutated.png` | History view after clicking Star on entry `#3` (turns active pink) and Delete on entry `#1` (removed from DOM and SQLite, leaving 2 starred entries). |
| `SCR-005` | `F-015` | `normal` | `05_ui/screenshots/SCR-005_advanced_settings.png` | `Advanced` settings groups: `APP` (`Start Hidden`, `Launch on Startup`, `Show Tray Icon`, `Overlay: Live`, `Overlay Position: Bottom`, `Unload Model`, `Experimental Features`), `OUTPUT` (`Clipboard (Cmd+V)`, `Don't Modify Clipboard`, `Auto Submit: Off`), and `TRANSCRIPTION` (`Voice Activity Detection`, `Long Audio Chunking`). |

## Visual Differential Proof Baseline
Screens `SCR-001`, `SCR-002`, and `SCR-003` serve as live pixel-diff baselines for `07_tests/verify_parity.py`, producing `orig_SCR-*.png`, `reimpl_SCR-*.png`, `diff_SCR-*.png`, and `visual_diff_metrics.json` inside `cleanroom-reimpl/proof_shots/`.
