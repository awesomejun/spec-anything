# 08 Implementation Blueprint — Clean-Room Reimplementation Architecture

## 1. Target Clean-Room Repository Tree (Language-Agnostic Example: Rust or Go)
```text
pb-cleanroom/
├── cmd/server/                 # CLI parser (--version, serve, superuser upsert) [F-001, F-002]
├── internal/
│   ├── storage/                # SQLite WAL engine, _collections/_params/_superusers DDL [F-012]
│   ├── schema/                 # Collection model, DDL compiler, unique index error mapper [F-006]
│   ├── filter/                 # fexpr tokenizer/parser -> parameterized SQL WHERE/ORDER BY [F-008]
│   ├── auth/                   # Password verifier, JWT issuer/validator, auth middleware [F-004, F-005]
│   ├── realtime/               # SSE client registry, topic matcher, post-commit broadcaster [F-009]
│   ├── backup/                 # Zip snapshot lock + pb_data archiver [F-011]
│   ├── settings/               # _params settings store & PATCH merger [F-010]
│   └── httpapi/                # Router, middleware chain, JSON error envelope [F-003, F-007]
├── web-ui/                     # Clean-room Admin SPA (replaces brand marks/assets) [F-013, F-020]
└── tests/                      # Executes 07_tests/verify_parity.py --target-url against build
```

## 2. Module Responsibilities & Dependency Direction
- Dependency DAG strictly flows inward: `cmd -> httpapi -> {auth, schema, filter, realtime, backup, settings} -> storage`.
- `storage` holds zero HTTP imports; `filter` is a pure function module (`(expr, allowed_fields) -> (sql_where, params)`) testable in isolation `[REF: apis/record_crud.go:39-125]`.
- `realtime` subscribes to post-commit storage notifications and evaluates collection read rules before serializing SSE frames `[REF: apis/realtime.go:32-190]`.

## 3. Upstream Source -> Clean-Room Module -> Parity Test Mapping
| Upstream Source | Clean-Room Module | Feature IDs | Parity Tests |
|---|---|---|---|
| `[REF: pocketbase.go:108-120]`, `[REF: cmd/superuser.go:32-72]` | `cmd/server` | `F-001`, `F-002` | `TC-001`, `TC-002` |
| `[REF: apis/health.go:18-45]`, `[REF: apis/base.go:19-45]` | `internal/httpapi` | `F-003` | `TC-003` |
| `[REF: apis/record_auth_with_password.go:15-105]`, `[REF: apis/middlewares.go:30-90]` | `internal/auth` | `F-004`, `F-005` | `TC-004`, `TC-005`, `TC-006` |
| `[REF: apis/collection.go:100-140]` | `internal/schema` | `F-006` | `TC-007` |
| `[REF: apis/record_crud.go:39-260]`, `[REF: core/record_model.go:1-120]` | `internal/httpapi` + `internal/filter` | `F-007`, `F-008` | `TC-008`–`TC-011` |
| `[REF: apis/realtime.go:32-190]` | `internal/realtime` | `F-009` | `TC-012` |
| `[REF: apis/settings.go:15-95]`, `[REF: apis/backup.go:18-130]`, `[REF: core/db.go:1-120]` | `internal/settings`, `backup`, `storage` | `F-010`–`F-012` | `TC-013`–`TC-015` |
| `[REF: ui/src/auth/pageSuperuserLogin.js:1-120]`, `[REF: ui/src/css/vars.css:1-120]` | `web-ui` | `F-013`, `F-020` | `TC-016` |

## Sources Read
- `examples/base/main.go`
- `apis/base.go`
- `apis/collection.go`
- `apis/record_crud.go`
- `apis/realtime.go`
- `core/db.go`
- `cmd/superuser.go`
