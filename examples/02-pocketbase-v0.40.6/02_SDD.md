# 02 SDD — PocketBase v0.40.6 Software Design & Architecture

## 1. System Architecture & Official Release Entrypoint (REA Finding)
Inspecting the official macOS arm64 binary via `go version -m` (`04_environment/release_audit.json`) reveals a critical architectural fact: the distributed binary compiles **`examples/base/main.go`** (not root `pocketbase.go`) using **`go1.27.3`**, **`CGO_ENABLED=0`**, and `vcs.revision=9d281ccaba65f2686eb7b0b614ccda72d1116a1b` `[REF: examples/base/main.go:19-75]`. This registers:
- Embedded pure-Go SQLite (`modernc.org/sqlite`) with WAL journaling (`EV-015`, `F-012`) `[REF: core/db.go:1-120]`
- Embedded vanilla-JS Admin UI SPA mounted at `/_/{path...}` (`F-020`, `F-014`) `[REF: apis/serve.go:84-95]`
- Embedded `goja` JavaScript VM hooks plugin (`--hooksDir`, `--hooksWatch`, `F-019`) `[REF: examples/base/main.go:26-45]`
- Automatic migration command plugin (`--migrationsDir`, `migratecmd`) `[REF: examples/base/main.go:13-16]`

## 2. HTTP Router & Middleware Pipeline
`apis.NewRouter` binds middlewares in deterministic order before dispatching to resource routes `[REF: apis/base.go:19-45]`:
1. `activityLogger()` — asynchronously buffers request metrics to `auxiliary.db` (`F-016`) `[REF: apis/logs.go:18-45]`.
2. `panicRecover()` — converts panics into structured `500` JSON errors.
3. `rateLimit()` — optional token-bucket throttling configured via `_params` settings (`F-010`).
4. `loadAuthToken()` — parses `Authorization` JWT (`github.com/golang-jwt/jwt/v5`), hydrating `e.Auth` for superuser or auth-collection records (`F-004`, `F-005`) `[REF: apis/middlewares.go:30-90]`.
5. `superuserIPsWhitelist()` & `securityHeaders()` — enforces optional IP restrictions and HTTP security headers.

## 3. Core Algorithms & Business Rules
- **Collection Materialization (`F-006`)**: `POST /api/collections` validates field definitions and index DDL strings, writes metadata to `_collections`, and executes `CREATE TABLE` + `CREATE [UNIQUE] INDEX` atomically inside a SQLite transaction (`EV-007`, `09_contracts/schema.sql`) `[REF: apis/collection.go:100-140]`.
- **Record Validation & Unique Error Mapping (`F-007`)**: Every field runs type/min/max/required validators (`ozzo-validation`), emitting field-keyed envelopes (`data.<field>.code = "validation_min_text_constraint"`, `EV-008`). SQLite `UNIQUE constraint failed` errors are intercepted and mapped to `data.<field>.code = "validation_not_unique"` (`EV-010`) `[REF: apis/record_crud.go:195-260]`.
- **Filter Expression Engine (`F-008`)**: Query `filter` strings are parsed via `github.com/ganigeorgiev/fexpr` into parameterized SQL `WHERE` predicates combined with collection `listRule`, preventing SQL injection while supporting operators (`=`, `>=`, `&&`, `||`) and multi-key `sort` (`-views`, `EV-011`) `[REF: apis/record_crud.go:39-125]`.
- **SSE Realtime Broker (`F-009`)**: `GET /api/realtime` allocates a per-connection buffered channel, registers a random `clientId`, immediately flushes `event: PB_CONNECT`, and streams subsequent record hooks (`OnRecordAfterCreateSuccess` / update / delete) filtered by subscription topic (`articles/*`) and per-client collection view/list rules (`EV-012`) `[REF: apis/realtime.go:32-190]`.

## 4. Persistence, Concurrency & Failure Recovery
- **Dual SQLite WAL Databases (`F-012`)**: Primary state resides in `pb_data/data.db` (`PRAGMA journal_mode = wal`, observed `EV-015`), separating write contention from request logs in `pb_data/auxiliary.db`.
- **Graceful Shutdown & Backup Locking (`F-011`, `F-012`)**: `SIGTERM` flushes WAL checkpoints cleanly so relaunching on a fresh port preserves all 4 seeded records and updated `_params` settings (`EV-015`). Backup creation (`POST /api/backups`, `EV-014`) snapshots `pb_data` safely into `pb_data/backups/*.zip` while preventing concurrent destructive restores `[REF: apis/backup.go:18-130]`.

## 5. Security Boundaries
- Privileged endpoints (`/api/collections`, `/api/settings`, `/api/backups`, `/api/crons`, `/api/logs`) require a valid `_superusers` JWT; anonymous calls return `401` (`EV-006`).
- Passwords are stored salted/hashed; raw JWTs are excluded from `06_evidence/ledger.jsonl` and checked by `scripts/secret_guard.py`.

## Sources Read
- `examples/base/main.go`
- `apis/base.go`
- `apis/middlewares.go`
- `apis/collection.go`
- `apis/record_crud.go`
- `apis/record_auth_with_password.go`
- `apis/realtime.go`
- `apis/settings.go`
- `apis/backup.go`
- `apis/logs.go`
- `core/db.go`
- `04_environment/release_audit.json`
