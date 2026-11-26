# 06 Original Behavior Evidence — PocketBase v0.40.6

Machine-readable oracle consumed directly by `07_tests/verify_parity.py`: `06_evidence/ledger.jsonl` (`15` records, all `status: observed`, binary `SHA-256: d313ba59879e96a5ab566c6763f4ae9b63dc62e9fee78782276407808905d54f`).

| Evidence ID | Feature ID | Category | Entry / Input | Key Observed Output & Storage/Event Effect | Status |
|---|---|---|---|---|---|
| `EV-001` | `F-001` | `cli` | `pocketbase --version` | `exit=0`, `stdout="pocketbase version 0.40.6"` | `observed` |
| `EV-002` | `F-002` | `cli` | `superuser upsert admin@example.com` | `exit=0`, row saved in `_superusers` (`pb_data/data.db`) | `observed` |
| `EV-003` | `F-003` | `normal` | `GET /api/health` | `200`, `{"code":200,"message":"API is healthy.","data":{}}` | `observed` |
| `EV-004` | `F-004` | `auth` | `POST .../_superusers/auth-with-password` (bad pw) | `400`, `{"status":400,"message":"Failed to authenticate.","data":{}}` (`SCR-002`) | `observed` |
| `EV-005` | `F-004` | `auth` | `POST .../_superusers/auth-with-password` (valid) | `200`, 3-segment JWT present (redacted), `record.email="admin@example.com"` | `observed` |
| `EV-006` | `F-005` | `auth` | `GET /api/collections` (anonymous) | `401`, `"The request requires valid record authorization token."` | `observed` |
| `EV-007` | `F-006` | `normal` | `POST /api/collections` (`articles`) | `200`, creates SQLite table `articles` + `idx_articles_slug` (`SCR-003`) | `observed` |
| `EV-008` | `F-007` | `error` | `POST .../articles/records` (`title="ab"`) | `400`, `data.title.code="validation_min_text_constraint"` (`min=3`), 0 rows added | `observed` |
| `EV-009` | `F-007` | `normal` | `POST .../articles/records` (3 valid records) | `[200,200,200]`, 15-char IDs generated, `articles` has 3 rows (`SCR-004`) | `observed` |
| `EV-010` | `F-007` | `boundary` | `POST .../articles/records` (duplicate `slug="alpha"`) | `400`, `data.slug.code="validation_not_unique"`, 0 rows added | `observed` |
| `EV-011` | `F-008` | `normal` | `GET .../articles/records?filter=(published=true && views>=40)&sort=-views` | `200`, `totalItems=2`, `ordered_slugs=["gamma","alpha"]`, `views=[100,42]` | `observed` |
| `EV-012` | `F-009` | `realtime` | `GET/POST /api/realtime` (`articles/*`) + create `realtime-1` | `POST=204`; ordered SSE stream: `[1: PB_CONNECT, 2: articles/* action=create slug=realtime-1]` | `observed` |
| `EV-013` | `F-010` | `persistence` | `PATCH /api/settings` (`appName="SpecAnythingPB"`) | `200`, persisted to `_params` (`SCR-006`) | `observed` |
| `EV-014` | `F-011` | `persistence` | `POST /api/backups` (`parity_snapshot.zip`) | `POST=204`, `GET=200`, zip listed with `size > 0` | `observed` |
| `EV-015` | `F-012` | `restart_recovery` | `SIGTERM` + relaunch on new port (`same pb_data`) | `PRAGMA journal_mode="wal"`; all 4 slugs (`alpha`,`beta`,`gamma`,`realtime-1`) and `appName="SpecAnythingPB"` survive intact | `observed` |

## Limitations & Security Hygiene
- All live JWTs were verified structurally (`3` dot-separated segments) and deliberately excluded from `ledger.jsonl` to maintain zero secret leaks (`scripts/secret_guard.py`).
- External integrations (SMTP, S3, OAuth2 IdP) and hard `SIGKILL` mid-transaction crash recovery remain outside the isolated loopback observation boundary.
