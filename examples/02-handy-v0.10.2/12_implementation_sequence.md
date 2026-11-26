# 12 — Clean-Room Implementation Sequence (`cjpais/Handy v0.10.2`)

## 1. Staged Build Order
Every stage ends with an automated gate referencing `09_contracts/`, `06_evidence/ledger.jsonl`, and `07_tests/verify_parity.py` `[REF: 09_contracts/history.sql:1-35]` `[REF: 09_contracts/tauri_ipc.schema.json:1-60]` `[REF: 07_tests/verify_parity.py:1-60]`:

1. **Stage 1 — Database Schema & Persistence Core (`F-012`, `F-013`, `F-014`, `F-015`)**:
   - Execute `09_contracts/history.sql` in SQLite; assert `PRAGMA user_version == 4` and exact 12-column layout.
   - Implement cursor-paginated `get_history`, atomic `toggle_history_saved`, and `delete_history` with missing-ID errors.
   - Gate: `TC-012`, `TC-013`, `TC-014`, `TC-015` schema assertions pass.
2. **Stage 2 — Settings & Shortcut Binding Persistence (`F-002`, `F-003`, `F-004`, `F-005`, `F-006`)**:
   - Implement `AppSettings` (`settings_schema_version = 3`) JSON store, `ShortcutActivation` enum validation, `BindingResponse` mutation, `LanguageStatus` resolver, and audio device listing.
   - Gate: `TC-002` through `TC-006` pass against `06_evidence/ledger.jsonl`.
3. **Stage 3 — Offline Model Catalog & Active Selection Guard (`F-007`, `F-008`, `F-009`)**:
   - Load curated ASR catalog metadata with capability flags (`streaming`, `translation`, `language_detection`) and enforce downloaded-only validation when switching active models.
   - Gate: `TC-007`, `TC-008`, `TC-009` pass (including negative error test for undownloaded model).
4. **Stage 4 — Dictation Coordinator State Machine (`F-010`, `F-011`)**:
   - Implement `idle -> recording -> transcribing -> completed` (with SQLite row insertion) and `recording -> cancelled -> idle` (zero DB mutation) behind a swappable STT engine boundary.
   - Gate: `TC-010` and `TC-011` pass.
5. **Stage 5 — Token-Driven UI Shell & Visual Parity Proof (`F-002`, `F-007`, `F-012`, `F-015`)**:
   - Build the 5-section desktop layout (`General`, `History`, `Models`, `Advanced`, `About`) from `11_ui/tokens.json` using clean-room branding (`Handy CR`) `[REF: 11_ui/tokens.json:1-127]`.
   - Gate: Run `07_tests/verify_parity.py --mode reimplementation_diff` and verify `15 / 15 PASS` + pixel-diff MAE heatmaps (`cleanroom-reimpl/proof_shots/visual_diff_metrics.json`) well within `visual_max_diff_ratio <= 0.12`.
6. **Stage 6 — Optional Native Engine & OS Integration (Post-Parity Extension)**:
   - Swap the deterministic STT stub with `transcribe.cpp` / `whisper.cpp` GGUF inference, CoreAudio/cpal PCM recording, Silero VAD, and platform global shortcuts while keeping `07_tests/verify_parity.py` green in CI.

## Sources Read
- `09_contracts/history.sql`
- `09_contracts/tauri_ipc.schema.json`
- `11_ui/tokens.json`
- `06_evidence/ledger.jsonl`
- `07_tests/verify_parity.py` (`1-60`)
- `cleanroom-reimpl/app.py`
