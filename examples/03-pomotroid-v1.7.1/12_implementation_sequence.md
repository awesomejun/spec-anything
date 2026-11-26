# 12 Phased Implementation Sequence — Pomotroid v1.7.1

## Phase Order & Parity Gates
1. **Milestone 1 — SQLite WAL & Settings Store (`F-009`, `F-010`)**: Apply `09_contracts/pomotroid_db.sql` (`MIGRATION_1..6`), seed defaults, implement `0..100 ↔ 0.0..1.0` volume scaling. Gate: `TC-009`, `TC-010` PASS [REF: src-tauri/src/db/migrations.rs:5-135].
2. **Milestone 2 — Timer Engine & Round Sequencer (`F-002`, `F-003`, `F-005`..`F-008`)**: Implement `Work → ShortBreak → LongBreak → Work(1)` cycle including `long_breaks_enabled=false` sentinel `0→1` and full reset. Gate: `TC-002`, `TC-003`, `TC-005`..`TC-008` PASS [REF: src-tauri/src/timer/sequence.rs:77-128].
3. **Milestone 3 — Circular SVG Dial, Themes & Shortcuts (`F-004`, `F-011`, `F-014`)**: Render `220×220` SVG arc (`691.15` circumference), theme token switching, and local key bindings. Gate: `TC-004`, `TC-011`, `TC-014` PASS + pixel-diff MAE `<= 5%` [REF: src/lib/components/TimerDial.svelte:16-72].
4. **Milestone 4 — Settings & Statistics Views (`F-012`, `F-013`)**: Add 6-section `/settings` and 3-tab `/stats` with SQLite aggregation. Gate: full `14 / 14 PASS` [REF: src/routes/stats/+page.svelte:29-184].

## Sources Read
- `src-tauri/src/db/migrations.rs`
- `src-tauri/src/timer/sequence.rs`
- `src/lib/components/TimerDial.svelte`
- `src/routes/stats/+page.svelte`
