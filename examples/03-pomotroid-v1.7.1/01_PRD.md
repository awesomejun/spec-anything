# 01 PRD — Pomotroid v1.7.1 (Circular Pomodoro Study & Focus Timer)

## 1. Product Goal & Audience
Pomotroid v1.7.1 is a lightweight, zero-distraction circular Pomodoro timer designed for students, writers, and general desktop users to alternate timed Focus blocks (`25:00`), Short Breaks (`05:00`), and Long Breaks (`15:00`) every `4` rounds with theme customization and daily/weekly focus statistics [REF: src-tauri/tauri.conf.json:1-56] [REF: src-tauri/src/settings/defaults.rs:7-42].

## 2. Core User Flows (Linked to Feature IDs)
- **Focus Cycle (`F-002`, `F-003`, `F-004`)**: Open the `360×478` main window showing a `25:00` countdown inside a `220×220` circular SVG progress ring, press Play (`Space`) to start/pause, and watch the ring shrink (`dial_countdown=true`) or fill (`dial_countdown=false`) [REF: src/lib/components/TimerDial.svelte:16-72].
- **Round Transitions (`F-005`, `F-006`, `F-007`, `F-008`)**: Skip (`ArrowRight`) advances `work → short-break → work → ... → long-break → work(1)`. Disabling long breaks substitutes a short break with cycle sentinel reset (`work_round_number=0 → 1`) [REF: src-tauri/src/timer/sequence.rs:77-128].
- **Customization & Themes (`F-009`, `F-010`, `F-011`, `F-012`)**: Adjust work/break durations, round intervals, break toggles, mute/volume (`0..100` integer persistence), and switch across `38` bundled themes (`Pomotroid`, `Pomotroid Light`, `Nord`, `Dracula`) [REF: src-tauri/src/themes/mod.rs:27-81].
- **Session Statistics (`F-013`)**: Inspect Today (`ROUNDS`, `FOCUS TIME`, `COMPLETION`, 24-hour bar chart), This Week, and All-Time heatmap views backed by SQLite WAL [REF: src/routes/stats/+page.svelte:29-184].

## 3. Non-Goals & Clean-Room Boundaries
- Excludes proprietary distribution signing keys, Tauri auto-updater endpoints, and verbatim redistribution of bundled variable fonts or icons.

## 4. Acceptance Criteria
- All `14` Feature IDs (`F-001`..`F-014`) pass automated `07_tests/verify_parity.py` with `0` failures on both upstream baseline and full-app clean-room reimplementation (`cleanroom-reimpl/app.py`), with visual pixel-diff MAE `<= 5.0%`.

## Sources Read
- `src-tauri/tauri.conf.json` (commit `4a02ac7bff9083dc5b2cc42fa7c4683c1fc15805`)
- `src-tauri/src/settings/defaults.rs`
- `src-tauri/src/timer/sequence.rs`
- `src-tauri/src/themes/mod.rs`
- `src/lib/components/TimerDial.svelte`
- `src/routes/stats/+page.svelte`
