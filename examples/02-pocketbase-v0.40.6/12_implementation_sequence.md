# 12 Implementation Sequence & Parity Pass Gates

Ordered execution roadmap for building a clean-room PocketBase-compatible server + Admin UI verified continuously by `07_tests/verify_parity.py`.

## Milestone 1 — Vertical Slice: Storage, CLI Bootstrap & Auth (Prerequisite)
- **Scope**: `F-001`, `F-002`, `F-003`, `F-004`, `F-005`, `F-012` `[REF: cmd/serve.go:14-45]` `[REF: core/db.go:1-120]`.
- **Deliverables**: SQLite WAL bootstrap (`09_contracts/schema.sql`), `--version`, `superuser upsert`, `GET /api/health`, superuser JWT auth & `401` guard.
- **Parity Gate**: `TC-001` through `TC-006` PASS against `06_evidence/ledger.jsonl`.

## Milestone 2 — Dynamic Collection DDL, Record Validation & Filter Engine (Core API)
- **Scope**: `F-006`, `F-007`, `F-008` `[REF: apis/collection.go:100-140]` `[REF: apis/record_crud.go:39-260]`.
- **Deliverables**: `POST /api/collections` table/index materializer, field validators (`validation_min_text_constraint`), unique index error mapper (`validation_not_unique`), `fexpr` filter + sort + pagination.
- **Parity Gate**: `TC-007` through `TC-011` PASS.

## Milestone 3 — Parallelizable Tracks: Realtime SSE, Settings/Backups & Admin UI
These three tracks have zero write-conflict once Milestone 2 passes and can run in parallel:
- **Track 3A (Realtime Streaming)**: `F-009` SSE `/api/realtime` (`PB_CONNECT` + post-commit topic broadcast) `[REF: apis/realtime.go:32-190]` -> Gate: `TC-012` PASS.
- **Track 3B (Operations & Durability)**: `F-010` settings, `F-011` zip backups, `F-012` graceful `SIGTERM` restart durability -> Gate: `TC-013`, `TC-014`, `TC-015` PASS.
- **Track 3C (Clean-Room Admin UI)**: `F-013`, `F-020` login, collections sidebar, populated table, API preview modal, settings view using `11_ui/tokens.json` -> Gate: `TC-016` (`visual_diff_ratio <= 0.05` on baseline or approved clean-room skin).

## Milestone 4 — Extended Features Beyond Initial Baseline
- **Scope**: `F-015` (crons), `F-016` (logs in `auxiliary.db`), `F-017` (multipart file serving & tokens), `F-018` (OAuth2/OTP/SMTP with local Mailpit/OIDC test doubles), `F-019` (JS hooks runtime).
- **Parity Gate**: Extend `06_evidence/ledger.jsonl` and `07_tests/verify_parity.py` per the re-verification recipes in `03_scope/features.json`.

## Sources Read
- `cmd/serve.go`
- `core/db.go`
- `apis/collection.go`
- `apis/record_crud.go`
- `apis/realtime.go`
- `03_scope/features.json`
- `07_tests/verify_parity.py`
