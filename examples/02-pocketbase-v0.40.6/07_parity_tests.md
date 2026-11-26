# 07 Differential Parity Tests & Baseline Results — PocketBase v0.40.6

Executable test harness: `07_tests/verify_parity.py` and `07_tests/verify_visual.py`. Structured machine report: `07_tests/parity_report.json`.

Every test case reads its expected values **directly from `06_evidence/ledger.jsonl`** rather than duplicating hardcoded assertions.

## 1. Execution Runbook
```bash
# 1. Verify upstream official binary baseline (spawns isolated temp pb_data + pb_migrations)
python3 07_tests/verify_parity.py --binary /absolute/path/to/pocketbase

# 2. Verify a clean-room reimplementation server against the exact same 06 JSONL oracle
python3 07_tests/verify_parity.py --target-url http://127.0.0.1:8090
```

## 2. Verified Upstream Baseline Results (`2026-11-25T23:42:41Z`)
- **Mode**: `upstream_baseline`
- **Target**: Official `pocketbase v0.40.6` (`darwin_arm64`, `SHA-256: d313ba59879e96a5ab566c6763f4ae9b63dc62e9fee78782276407808905d54f`)
- **Summary**: **16 / 16 PASS** (`0` FAIL, `0` SKIP, `0` UNVERIFIED)

| Test ID | Feature ID | Evidence ID | Category | Checked Fields & Tolerance | Duration (ms) | Verdict |
|---|---|---|---|---|---:|---|
| `TC-001` | `F-001` | `EV-001` | `cli` | `exit_code`, `stdout` | 11.96 | **PASS** |
| `TC-002` | `F-002` | `EV-002` | `cli` | `exit_code`, `stdout_contains_saved` | 82.60 | **PASS** |
| `TC-003` | `F-003` | `EV-003` | `normal` | `status_code`, `body.code`, `body.message` | 0.37 | **PASS** |
| `TC-004` | `F-004` | `EV-004` | `auth` | `status_code`, `body.status`, `body.message` | 49.91 | **PASS** |
| `TC-005` | `F-004` | `EV-005` | `auth` | `status_code`, `token_present`, `token_jwt_segment_count`, `record_email`, `record_collectionName` | 50.56 | **PASS** |
| `TC-006` | `F-005` | `EV-006` | `auth` | `status_code`, `body.status`, `body.message` | 0.43 | **PASS** |
| `TC-007` | `F-006` | `EV-007` | `normal` | `status_code`, `name`, `type`, `field_names`, `indexes` | 2.35 | **PASS** |
| `TC-008` | `F-007` | `EV-008` | `error` | `status_code`, `body.status`, `body.data.title.code` | 0.44 | **PASS** |
| `TC-009` | `F-007` | `EV-009` | `normal` | `status_codes`, `slugs_created`, `id_lengths` | 1.20 | **PASS** |
| `TC-010` | `F-007` | `EV-010` | `boundary` | `status_code`, `body.status`, `body.data.slug.code` | 0.31 | **PASS** |
| `TC-011` | `F-008` | `EV-011` | `normal` | `status_code`, `page`, `perPage`, `totalItems`, `ordered_slugs`, `ordered_views` | 0.74 | **PASS** |
| `TC-012` | `F-009` | `EV-012` | `realtime` | `subscribe_status`, `trigger_status`, `event_sequence[0].event`, `event_sequence[1].event`, `action`, `record_slug` | 53.42 | **PASS** |
| `TC-013` | `F-010` | `EV-013` | `persistence` | `status_code`, `appName` | 1.30 | **PASS** |
| `TC-014` | `F-011` | `EV-014` | `persistence` | `create_status`, `list_status`, `backup_found`, `backup_size_gt_0` | 10.14 | **PASS** |
| `TC-015` | `F-012` | `EV-015` | `restart_recovery` | `auth_after_restart_status`, `records_status`, `persisted_totalItems`, `persisted_slugs`, `persisted_appName`, `sqlite_journal_mode` | 214.43 | **PASS** |
| `TC-016` | `F-004` | `EV-005` | `auth` (visual) | `visual_diff_ratio <= 0.05` against `05_ui/screenshots/SCR-001_login_initial.png` at `1440x900@1x` | 1474.31 | **PASS** |

## 3. Scope Boundaries & OS Notes
- Confirmed parity is strictly bounded to the 16 executed baseline cases above (`F-001`–`F-013`, `F-020`). No clean-room reimplementation server has been executed in this release yet (`reimplementation_diff` mode awaits a candidate `--target-url`).
- `TC-001`, `TC-002`, and `TC-015` require `--binary` (process lifecycle control); `--target-url` mode runs the HTTP/SSE/visual subset (`TC-003`–`TC-014`, `TC-016`).
- Deferred features (`F-015`–`F-019`) require extended fixtures (Mailpit SMTP stub, mock OIDC IdP, multipart PNG upload, JS `pb_hooks`) documented in `03_scope/features.json`.
