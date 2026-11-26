# 09 Machine-Readable Contracts — PocketBase v0.40.6

All machine-readable contract artifacts reside under `09_contracts/` and are validated automatically by `scripts/validate_bundle.py` (including executing `schema.sql` against a fresh in-memory SQLite engine).

| Contract File | Format | Scope & Linked Feature IDs |
|---|---|---|
| `09_contracts/openapi.json` | OpenAPI 3.1 JSON | Health (`F-003`), Superuser Auth (`F-004`), Collections (`F-005`, `F-006`), Records CRUD & Query (`F-007`, `F-008`), Realtime SSE (`F-009`), Settings (`F-010`), Backups (`F-011`), Crons (`F-015`) |
| `09_contracts/collection.schema.json` | JSON Schema 2020-12 | Dynamic collection creation payload (`F-006`) |
| `09_contracts/realtime_event.schema.json` | JSON Schema 2020-12 | SSE `PB_CONNECT` and record mutation frames (`F-009`) |
| `09_contracts/error.schema.json` | JSON Schema 2020-12 | Standard `{status, message, data}` error envelope (`F-004`, `F-005`, `F-007`) |
| `09_contracts/schema.sql` | SQLite DDL (21 statements) | Live-extracted DDL from `pb_data/data.db` (`_collections`, `_params`, `_superusers`, `_mfas`, `_otps`, `_authOrigins`, `_externalAuths`, `users`, `articles` + unique indexes) (`F-006`, `F-012`) |

## Verified Wire Error Examples (`06_evidence/ledger.jsonl`)
- **Validation Min-Length Error (`EV-008`, HTTP `400`)**:
  ```json
  {"status": 400, "message": "Failed to create record.", "data": {"title": {"code": "validation_min_text_constraint", "message": "Must be at least 3 character(s).", "params": {"min": 3}}}}
  ```
- **Unique Index Conflict (`EV-010`, HTTP `400`)**:
  ```json
  {"status": 400, "message": "Failed to create record.", "data": {"slug": {"code": "validation_not_unique", "message": "Value must be unique."}}}
  ```
- **Unauthorized Superuser Endpoint (`EV-006`, HTTP `401`)**:
  ```json
  {"status": 401, "message": "The request requires valid record authorization token.", "data": {}}
  ```
