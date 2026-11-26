# Deterministic Static Fact Sheet

Generated mechanically by `scripts/source_map.py`. LLM synthesis must remain grounded in these facts and live runtime observations.

## Coverage Statistics
- Total files scanned: `833`
- Supported code files: `711` (test files: `197`)
- Languages: `{"css": 42, "go": 461, "html": 1, "javascript": 206, "typescript": 1}`
- Extracted inventory: `12` modules, `329` entities, `65` actions/routes, `3` SQL tables, `1` frontend routes, `265` CSS variables, `45` dependencies

## Loud Warnings
- **[SECRET_FILES_EXCLUDED]** (info): Excluded potential secret files from static extraction: ['ui/.env']

## 1. Modules
| Module | Files | Lines | Languages |
|---|---:|---:|---|
| `.` | 3 | 613 | go |
| `apis` | 78 | 29885 | go |
| `cmd` | 3 | 791 | go |
| `core` | 139 | 48422 | go |
| `examples` | 1 | 136 | go |
| `forms` | 8 | 1950 | go |
| `mails` | 5 | 599 | go |
| `migrations` | 8 | 1695 | go |
| `plugins` | 24 | 34453 | go, typescript |
| `tests` | 6 | 1559 | go |
| `tools` | 185 | 34292 | go |
| `ui` | 251 | 51755 | css, go, html, javascript |

## 2. HTTP Routes & CLI Commands (Sample Top 80)
| Role | Method | Target | Ref |
|---|---|---|---|
| `cli_command` | `CLI` | `create` | `[REF: cmd/superuser.go:74]` |
| `cli_command` | `CLI` | `delete` | `[REF: cmd/superuser.go:144]` |
| `cli_command` | `CLI` | `ips` | `[REF: cmd/superuser.go:216]` |
| `cli_command` | `CLI` | `otp` | `[REF: cmd/superuser.go:173]` |
| `cli_command` | `CLI` | `serve [domain(s)]` | `[REF: cmd/serve.go:20]` |
| `cli_command` | `CLI` | `superuser` | `[REF: cmd/superuser.go:18]` |
| `cli_command` | `CLI` | `update` | `[REF: cmd/superuser.go:110]` |
| `cli_command` | `CLI` | `upsert` | `[REF: cmd/superuser.go:34]` |
| `frontend_api_call` | `CLIENT` | `https://nominatim.openstreetmap.org/search.php?format=jsonv2&q=` | `[REF: ui/src/base/leaflet.js:202]` |
| `http_route` | `Any` | `details` | `[REF: apis/middlewares.go:415]` |
| `http_route` | `Any` | `error` | `[REF: apis/file.go:184]` |
| `http_route` | `Any` | `error` | `[REF: apis/realtime.go:707]` |
| `http_route` | `Any` | `error` | `[REF: core/backup_create.go:191]` |
| `http_route` | `Any` | `errors` | `[REF: apis/realtime.go:685]` |
| `http_route` | `Any` | `extension` | `[REF: apis/extensions.go:45]` |
| `http_route` | `Any` | `id` | `[REF: apis/realtime.go:386]` |
| `http_route` | `Any` | `id` | `[REF: apis/realtime.go:407]` |
| `http_route` | `Any` | `id` | `[REF: apis/realtime.go:495]` |
| `http_route` | `Any` | `meta` | `[REF: apis/middlewares.go:387]` |
| `http_route` | `Any` | `subscriptions` | `[REF: apis/realtime.go:242]` |
| `http_route` | `DELETE` | `/{collection}` | `[REF: apis/collection.go:24]` |
| `http_route` | `DELETE` | `/{collection}/truncate` | `[REF: apis/collection.go:25]` |
| `http_route` | `DELETE` | `/{id}` | `[REF: apis/record_crud.go:33]` |
| `http_route` | `DELETE` | `/{key}` | `[REF: apis/backup.go:23]` |
| `http_route` | `GET` | `/_/{path...}` | `[REF: apis/serve.go:84]` |
| `http_route` | `GET` | `/admins` | `[REF: tools/router/router.go:39]` |
| `http_route` | `GET` | `/auth-methods` | `[REF: apis/record_auth.go:22]` |
| `http_route` | `GET` | `/extensions.js` | `[REF: apis/extensions.go:55]` |
| `http_route` | `GET` | `/extensions/` | `[REF: apis/extensions.go:49]` |
| `http_route` | `GET` | `/files/{path...}` | `[REF: apis/base.go:108]` |
| `http_route` | `GET` | `/meta/oauth2-providers` | `[REF: apis/collection.go:30]` |
| `http_route` | `GET` | `/meta/scaffolds` | `[REF: apis/collection.go:27]` |
| `http_route` | `GET` | `/oauth2-redirect` | `[REF: apis/record_auth.go:12]` |
| `http_route` | `GET` | `/stats` | `[REF: apis/logs.go:21]` |
| `http_route` | `GET` | `/test` | `[REF: tools/router/router.go:35]` |
| `http_route` | `GET` | `/{collection}` | `[REF: apis/collection.go:22]` |
| `http_route` | `GET` | `/{collection}/{recordId}/{filename}` | `[REF: apis/file.go:45]` |
| `http_route` | `GET` | `/{id}` | `[REF: apis/logs.go:22]` |
| `http_route` | `GET` | `/{id}` | `[REF: apis/record_crud.go:30]` |
| `http_route` | `GET` | `/{key}` | `[REF: apis/backup.go:22]` |
| `http_route` | `GET` | `/{path...}` | `[REF: examples/base/main.go:115]` |
| `http_route` | `PATCH` | `/{collection}` | `[REF: apis/collection.go:23]` |
| `http_route` | `PATCH` | `/{id}` | `[REF: apis/record_crud.go:32]` |
| `http_route` | `POST` | `/apple/generate-client-secret` | `[REF: apis/settings.go:21]` |
| `http_route` | `POST` | `/auth-refresh` | `[REF: apis/record_auth.go:26]` |
| `http_route` | `POST` | `/auth-with-oauth2` | `[REF: apis/record_auth.go:35]` |
| `http_route` | `POST` | `/auth-with-otp` | `[REF: apis/record_auth.go:42]` |
| `http_route` | `POST` | `/auth-with-password` | `[REF: apis/record_auth.go:31]` |
| `http_route` | `POST` | `/confirm-email-change` | `[REF: apis/record_auth.go:64]` |
| `http_route` | `POST` | `/confirm-password-reset` | `[REF: apis/record_auth.go:49]` |
| `http_route` | `POST` | `/confirm-verification` | `[REF: apis/record_auth.go:56]` |
| `http_route` | `POST` | `/impersonate/{id}` | `[REF: apis/record_auth.go:68]` |
| `http_route` | `POST` | `/meta/dry-run-view` | `[REF: apis/collection.go:31]` |
| `http_route` | `POST` | `/oauth2-redirect` | `[REF: apis/record_auth.go:16]` |
| `http_route` | `POST` | `/request-email-change` | `[REF: apis/record_auth.go:60]` |
| `http_route` | `POST` | `/request-otp` | `[REF: apis/record_auth.go:39]` |
| `http_route` | `POST` | `/request-password-reset` | `[REF: apis/record_auth.go:46]` |
| `http_route` | `POST` | `/request-verification` | `[REF: apis/record_auth.go:53]` |
| `http_route` | `POST` | `/test/email` | `[REF: apis/settings.go:18]` |
| `http_route` | `POST` | `/test/s3` | `[REF: apis/settings.go:17]` |
| `http_route` | `POST` | `/token` | `[REF: apis/file.go:44]` |
| `http_route` | `POST` | `/upload` | `[REF: apis/backup.go:21]` |
| `http_route` | `POST` | `/{id}` | `[REF: apis/cron.go:18]` |
| `http_route` | `POST` | `/{key}/restore` | `[REF: apis/backup.go:24]` |
| `http_route` | `PUT` | `/import` | `[REF: apis/collection.go:26]` |

## 3. Frontend Routes
| Route | Component | Ref |
|---|---|---|
| `/prefix` | `DirFS` | `[REF: plugins/jsvm/internal/types/generated/types.d.ts:2279]` |

## 4. SQL Tables Detected in Migrations/Code
| Table | Ref |
|---|---|
| `IF` | `[REF: core/migrations_runner.go:252]` |
| `IF` | `[REF: migrations/1640988000_aux_init.go:11]` |
| `if` | `[REF: core/collection_record_table_sync.go:41]` |
