# 01 PRD — PocketBase v0.40.6 Clean-Room Reimplementation Specification

- **Target Repository**: `https://github.com/pocketbase/pocketbase` (`v0.40.6`, commit `9d281ccaba65f2686eb7b0b614ccda72d1116a1b`, MIT)
- **Official Release Audited**: `pocketbase_0.40.6_darwin_arm64.zip` (`SHA-256: 7f2f7544e9ee5994ab69f84b22a4ab9a3bcfed58c1dad7206d05ebeb753f968b`, upstream checksum matched)
- **Observation Tier / Depth**: `T3 (Full Release + Runtime + UI Parity)` / `comprehensive`

## 1. Product Goal & Primary Users
PocketBase is a single-binary backend-in-a-file combining an embedded SQLite WAL database, dynamic collection schema engine, REST API, Server-Sent Events (SSE) realtime subscription broker, local/S3 zip backup manager, and embedded Admin Web UI served at `/_/` `[REF: examples/base/main.go:19-135]` `[REF: apis/serve.go:84-100]`.
- **Operators / Developers**: Bootstrap a self-contained backend with `pocketbase superuser upsert` (`F-002`) and `pocketbase serve` (`F-012`), manage collections/records via Admin UI (`F-004`, `F-006`, `F-007`, `F-010`, `F-013`), and inspect API snippets (`SCR-005`).
- **Application Clients**: Query filtered/sorted collections (`F-008`), enforce schema validation and unique constraints (`F-007`), and subscribe to live record mutations over `/api/realtime` SSE (`F-009`).

## 2. Core User Flows & Functional Requirements (Linked to `03` Feature IDs)
1. **Bootstrap & Superuser Auth (`F-001`, `F-002`, `F-004`, `F-005`)**:
   - Operator queries binary version (`EV-001`) and seeds a superuser account via CLI (`EV-002`) `[REF: cmd/superuser.go:32-72]`.
   - Unauthenticated Admin UI visits at `/_/` render the superuser login view (`SCR-001`) `[REF: ui/src/auth/pageSuperuserLogin.js:1-86]`.
   - Invalid credentials return HTTP `400` (`Failed to authenticate.`) and show an error toast (`EV-004`, `SCR-002`). Valid credentials return HTTP `200` with a 3-segment JWT (`EV-005`) `[REF: apis/record_auth_with_password.go:15-105]`.
   - Anonymous requests to privileged admin endpoints (`GET /api/collections`) are rejected with HTTP `401` (`EV-006`) `[REF: apis/collection.go:19-35]`.
2. **Dynamic Collection & Record Lifecycle (`F-006`, `F-007`, `F-008`)**:
   - Superusers create collections via `POST /api/collections`, materializing SQLite tables and indexes (`EV-007`, `SCR-003`) `[REF: apis/collection.go:100-140]`.
   - Record writes enforce field constraints (`validation_min_text_constraint`, `EV-008`) and unique index constraints (`validation_not_unique`, `EV-010`), generating 15-character IDs on valid creates (`EV-009`, `SCR-004`) `[REF: apis/record_crud.go:195-260]`.
   - Record listing evaluates `fexpr` filter expressions, multi-column sort, and pagination (`EV-011`) `[REF: apis/record_crud.go:39-125]`.
3. **Realtime SSE Subscription (`F-009`)**:
   - Clients open `GET /api/realtime`, receive initial `PB_CONNECT` with a unique `clientId`, bind subscriptions via `POST /api/realtime` (`204`), and receive ordered mutation frames (`action: create|update|delete`) (`EV-012`) `[REF: apis/realtime.go:32-190]`.
4. **Settings, Backups & Restart Durability (`F-010`, `F-011`, `F-012`)**:
   - `PATCH /api/settings` updates persistent application metadata (`EV-013`, `SCR-006`) `[REF: apis/settings.go:15-95]`.
   - `POST /api/backups` snapshots `pb_data` into a zip archive listed by `GET /api/backups` (`EV-014`) `[REF: apis/backup.go:18-130]`.
   - Graceful `SIGTERM` shutdown and process restart on a new port preserve all records and settings in SQLite WAL storage (`EV-015`) `[REF: core/db.go:1-120]`.

## 3. Acceptance Criteria
A clean-room reimplementation is considered baseline-conformant for the executed scope only when:
1. All 16 executable test cases (`TC-001`–`TC-016`) in `07_tests/verify_parity.py` pass against `06_evidence/ledger.jsonl`.
2. Visual diff ratio on `SCR-001` at `1440x900@1x` remains `<= 0.05` (`07_tests/verify_visual.py`).
3. Out-of-baseline features (`F-015`–`F-019`) are explicitly tracked and verified using the re-verification procedures in `03_scope/features.json`.

## Sources Read
- `examples/base/main.go`
- `pocketbase.go`
- `cmd/serve.go`
- `cmd/superuser.go`
- `apis/base.go`
- `apis/health.go`
- `apis/collection.go`
- `apis/record_crud.go`
- `apis/record_auth.go`
- `apis/realtime.go`
- `apis/settings.go`
- `apis/backup.go`
- `ui/src/auth/pageSuperuserLogin.js`
