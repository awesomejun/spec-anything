# 03 Scope Matrix — PocketBase v0.40.6 Feature Registry

Machine-readable source of truth: `03_scope/features.json` (`20` atomic features, `0` macro groups, `macro_ratio = 0.000 <= 0.15`). Every deliverable (`01`–`12`), screenshot (`05`), observation (`06`), contract (`09`), and parity test (`07`) joins on `Feature ID`.

| Feature ID | Domain | Feature Name | Kind | Status | Evidence IDs | Screen IDs | Test IDs | Source Ref |
|---|---|---|---|---|---|---|---|---|
| `F-001` | cli | CLI Version Flag (`--version`) | `cli_command` | `observed` | `EV-001` | — | `TC-001` | `[REF: pocketbase.go:108-120]` |
| `F-002` | cli | CLI Superuser Account Upsert | `cli_command` | `observed` | `EV-002` | — | `TC-002` | `[REF: cmd/superuser.go:18-72]` |
| `F-003` | health | API Liveness & Backup Readiness Check | `api_endpoint` | `observed` | `EV-003` | — | `TC-003` | `[REF: apis/health.go:18-45]` |
| `F-004` | auth | Superuser Password Auth & Admin Login UI | `auth` | `observed` | `EV-004`, `EV-005` | `SCR-001`, `SCR-002` | `TC-004`, `TC-005`, `TC-016` | `[REF: apis/record_auth_with_password.go:15-105]` |
| `F-005` | auth | Superuser Auth Guard on Collections API | `auth` | `observed` | `EV-006` | — | `TC-006` | `[REF: apis/collection.go:19-35]` |
| `F-006` | collections | Dynamic Base Collection Creation & DDL | `api_endpoint` | `observed` | `EV-007` | `SCR-003` | `TC-007` | `[REF: apis/collection.go:100-140]` |
| `F-007` | records | Record CRUD, Field Validation & Unique Index Errors | `api_endpoint` | `observed` | `EV-008`, `EV-009`, `EV-010` | `SCR-004` | `TC-008`, `TC-009`, `TC-010` | `[REF: apis/record_crud.go:195-260]` |
| `F-008` | records | Record Filter (`fexpr`), Sort & Pagination | `api_endpoint` | `observed` | `EV-011` | `SCR-004` | `TC-011` | `[REF: apis/record_crud.go:39-125]` |
| `F-009` | realtime | Realtime SSE Connect, Subscribe & Broadcast | `realtime_stream` | `observed` | `EV-012` | — | `TC-012` | `[REF: apis/realtime.go:32-190]` |
| `F-010` | settings | Application Settings Read/Update & UI | `setting` | `observed` | `EV-013` | `SCR-006` | `TC-013` | `[REF: apis/settings.go:15-95]` |
| `F-011` | backups | On-Demand Zip Backup Creation & Listing | `storage` | `observed` | `EV-014` | — | `TC-014` | `[REF: apis/backup.go:18-130]` |
| `F-012` | storage | SQLite WAL Persistence & SIGTERM Restart Recovery | `storage` | `observed` | `EV-015` | `SCR-004`, `SCR-006` | `TC-015` | `[REF: core/db.go:1-120]` |
| `F-013` | ui | Admin UI API Preview Documentation Modal | `ui_screen` | `observed` | — | `SCR-005` | `TC-016` | `[REF: ui/src/apiPreview/apiPreviewModal.js:1-100]` |
| `F-014` | release_rea | Official Binary Build Provenance & Embedded UI | `release_boundary` | `observed` | — | `SCR-001` | — | `[REF: examples/base/main.go:1-135]` |
| `F-015` | background_jobs | Cron Job Registry & Manual Trigger API | `background_job` | `code-verified` | — | — | — | `[REF: apis/cron.go:15-50]` |
| `F-016` | observability | Request Logs Listing & Stats API | `api_endpoint` | `code-verified` | — | — | — | `[REF: apis/logs.go:18-60]` |
| `F-017` | files | Record File Serving & Protected File Token | `api_endpoint` | `code-verified` | — | — | — | `[REF: apis/file.go:40-90]` |
| `F-018` | auth | OAuth2, OTP & Email Verification Flows | `auth` | `code-verified` | — | — | — | `[REF: apis/record_auth.go:12-68]` |
| `F-019` | plugins | Embedded JavaScript VM App Hooks (`goja`) | `background_job` | `code-verified` | — | — | — | `[REF: examples/base/main.go:26-75]` |
| `F-020` | ui | Embedded Admin SPA & Public Dir Fallback | `ui_screen` | `observed` | — | `SCR-001`, `SCR-003`, `SCR-004`, `SCR-005`, `SCR-006` | `TC-016` | `[REF: apis/serve.go:84]` |

## Unverified / Deferred Live Verification Scope
Features `F-015` through `F-019` are statically verified (`code-verified`) against pinned source and release metadata; exact deferral reasons and deterministic re-verification procedures are stored per feature inside `03_scope/features.json`.
