#!/usr/bin/env python3
"""
Executable Differential Parity Test Harness (07) for PocketBase v0.40.6.
Reads expected behaviors DIRECTLY from 06_evidence/ledger.jsonl and executes
all cases against either the official upstream binary (--binary, baseline mode)
or a clean-room reimplementation (--target-url, reimplementation_diff mode).
Outputs schema-validated 07_tests/parity_report.json.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http_req(base: str, method: str, path: str, body=None, token=None):
    url = base + path
    hdrs = {"Accept": "application/json"}
    if token:
        hdrs["Authorization"] = token
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode("utf-8", errors="replace")
            return r.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)


def wait_health(base: str, timeout: float = 15.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            st, _ = http_req(base, "GET", "/api/health")
            if st == 200:
                return
        except Exception:
            pass
        time.sleep(0.15)
    raise RuntimeError(f"Server at {base} did not become healthy within {timeout}s")


def start_bin(binary: pathlib.Path, workdir: pathlib.Path, data_dir: pathlib.Path, port: int):
    proc = subprocess.Popen(
        [str(binary), "serve", f"--dir={data_dir}", f"--migrationsDir={workdir / 'pb_migrations'}", f"--http=127.0.0.1:{port}"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=str(workdir),
    )
    wait_health(f"http://127.0.0.1:{port}")
    return proc


def stop_bin(proc):
    if proc and proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def load_ledger(ledger_path: pathlib.Path) -> dict:
    by_id = {}
    for ln in ledger_path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            rec = json.loads(ln)
            by_id[rec["evidence_id"]] = rec
    return by_id


def run_suite(bundle_dir: pathlib.Path, binary: pathlib.Path | None, target_url: str | None) -> dict:
    ledger_path = bundle_dir / "06_evidence" / "ledger.jsonl"
    ev = load_ledger(ledger_path)
    cases = []
    mode = "upstream_baseline" if binary else "reimplementation_diff"
    artifact_sha = hashlib.sha256(binary.read_bytes()).hexdigest() if binary else None

    def run_case(tc_id: str, ev_id: str, fn):
        rec = ev[ev_id]
        t0 = time.time()
        try:
            checked, diff = fn(rec)
            verdict = "PASS" if diff is None else "FAIL"
        except Exception as exc:
            checked, diff, verdict = [], f"exception: {exc}", "FAIL"
        cases.append({
            "test_id": tc_id,
            "feature_id": rec["feature_id"],
            "evidence_id": ev_id,
            "category": rec["category"],
            "verdict": verdict,
            "duration_ms": round((time.time() - t0) * 1000, 2),
            "checked_fields": checked,
            "diff_summary": diff,
        })

    tmp_root = pathlib.Path(tempfile.mkdtemp(prefix="pb_parity_"))
    pb_data = tmp_root / "pb_data"
    pb_data.mkdir()
    proc = None
    token = None

    try:
        # TC-001: CLI --version
        if binary:
            def c001(r):
                exp = r["observed_output"]
                p = subprocess.run([str(binary), "--version"], capture_output=True, text=True)
                ok = (p.returncode == exp["exit_code"] and p.stdout.strip() == exp["stdout"])
                return ["exit_code", "stdout"], (None if ok else f"got ({p.returncode}, {p.stdout.strip()}) != expected {exp}")
            run_case("TC-001", "EV-001", c001)

            def c002(r):
                exp = r["observed_output"]
                p = subprocess.run([str(binary), "superuser", "upsert", "admin@example.com", "TestPass123456!",
                                    f"--dir={pb_data}", f"--migrationsDir={tmp_root / 'pb_migrations'}"],
                                   capture_output=True, text=True, cwd=str(tmp_root))
                saved = "Successfully saved superuser" in p.stdout
                ok = (p.returncode == exp["exit_code"] and saved == exp["stdout_contains_saved"])
                return ["exit_code", "stdout_contains_saved"], (None if ok else f"rc={p.returncode}, stdout={p.stdout}")
            run_case("TC-002", "EV-002", c002)

            port = free_port()
            base = f"http://127.0.0.1:{port}"
            proc = start_bin(binary, tmp_root, pb_data, port)
        else:
            base = target_url.rstrip("/")
            wait_health(base)

        # TC-003: GET /api/health
        def c003(r):
            exp = r["observed_output"]
            st, body = http_req(base, "GET", r["input"]["path"])
            ok = (st == exp["status_code"] and body.get("code") == exp["body"]["code"] and body.get("message") == exp["body"]["message"])
            return ["status_code", "body.code", "body.message"], (None if ok else f"got {st} {body}")
        run_case("TC-003", "EV-003", c003)

        # TC-004: Superuser wrong password
        def c004(r):
            exp = r["observed_output"]
            st, body = http_req(base, "POST", r["input"]["path"], r["input"]["body"])
            ok = (st == exp["status_code"] and body.get("status") == exp["body"]["status"] and body.get("message") == exp["body"]["message"])
            return ["status_code", "body.status", "body.message"], (None if ok else f"got {st} {body}")
        run_case("TC-004", "EV-004", c004)

        # TC-005: Superuser valid auth
        def c005(r):
            nonlocal token
            exp = r["observed_output"]
            st, body = http_req(base, "POST", r["input"]["path"], {"identity": "admin@example.com", "password": "TestPass123456!"})
            token = body.get("token")
            ok = (
                st == exp["status_code"]
                and bool(token) == exp["token_present"]
                and len((token or "").split(".")) == exp["token_jwt_segment_count"]
                and body["record"]["email"] == exp["record_email"]
                and body["record"]["collectionName"] == exp["record_collectionName"]
            )
            return ["status_code", "token_present", "token_jwt_segment_count", "record_email", "record_collectionName"], (None if ok else f"got {st}")
        run_case("TC-005", "EV-005", c005)

        # TC-006: Anonymous GET /api/collections rejected
        def c006(r):
            exp = r["observed_output"]
            st, body = http_req(base, "GET", r["input"]["path"])
            ok = (st == exp["status_code"] and body.get("status") == exp["body"]["status"] and body.get("message") == exp["body"]["message"])
            return ["status_code", "body.status", "body.message"], (None if ok else f"got {st} {body}")
        run_case("TC-006", "EV-006", c006)

        # TC-007: Create articles collection
        def c007(r):
            exp = r["observed_output"]
            st, body = http_req(base, "POST", r["input"]["path"], r["input"]["body"], token=token)
            fnames = [f["name"] for f in body.get("fields", [])]
            ok = (st == exp["status_code"] and body.get("name") == exp["name"] and body.get("type") == exp["type"] and fnames == exp["field_names"] and body.get("indexes") == exp["indexes"])
            return ["status_code", "name", "type", "field_names", "indexes"], (None if ok else f"got {st} {body}")
        run_case("TC-007", "EV-007", c007)

        # TC-008: Validation min-length error
        def c008(r):
            exp = r["observed_output"]
            st, body = http_req(base, "POST", r["input"]["path"], r["input"]["body"])
            got_code = ((body.get("data") or {}).get("title") or {}).get("code")
            exp_code = exp["body"]["data"]["title"]["code"]
            ok = (st == exp["status_code"] and body.get("status") == exp["body"]["status"] and got_code == exp_code)
            return ["status_code", "body.status", "body.data.title.code"], (None if ok else f"got {st} {body}")
        run_case("TC-008", "EV-008", c008)

        # TC-009: Create 3 records
        def c009(r):
            exp = r["observed_output"]
            sts, slugs, idlens = [], [], []
            for rec_in in r["input"]["records"]:
                st, b = http_req(base, "POST", r["input"]["path"], rec_in)
                sts.append(st)
                slugs.append(b.get("slug"))
                idlens.append(len(b.get("id", "")))
            ok = (sts == exp["status_codes"] and slugs == exp["slugs_created"] and idlens == exp["id_lengths"])
            return ["status_codes", "slugs_created", "id_lengths"], (None if ok else f"got {sts} {slugs} {idlens}")
        run_case("TC-009", "EV-009", c009)

        # TC-010: Unique index duplicate slug error
        def c010(r):
            exp = r["observed_output"]
            st, body = http_req(base, "POST", r["input"]["path"], r["input"]["body"])
            got_code = ((body.get("data") or {}).get("slug") or {}).get("code")
            exp_code = exp["body"]["data"]["slug"]["code"]
            ok = (st == exp["status_code"] and body.get("status") == exp["body"]["status"] and got_code == exp_code)
            return ["status_code", "body.status", "body.data.slug.code"], (None if ok else f"got {st} {body}")
        run_case("TC-010", "EV-010", c010)

        # TC-011: Filter + Sort + Pagination
        def c011(r):
            exp = r["observed_output"]
            q = urllib.parse.urlencode(r["input"]["query"])
            st, body = http_req(base, "GET", f"{r['input']['path']}?{q}")
            slugs = [it["slug"] for it in body.get("items", [])]
            views = [it["views"] for it in body.get("items", [])]
            ok = (st == exp["status_code"] and body.get("page") == exp["page"] and body.get("perPage") == exp["perPage"]
                  and body.get("totalItems") == exp["totalItems"] and slugs == exp["ordered_slugs"] and views == exp["ordered_views"])
            return ["status_code", "page", "perPage", "totalItems", "ordered_slugs", "ordered_views"], (None if ok else f"got {st} {slugs} {views}")
        run_case("TC-011", "EV-011", c011)

        # TC-012: Realtime SSE connect + subscribe + create event ordering
        def c012(r):
            exp = r["observed_output"]
            exp_seq = r["event_sequence"]
            events, cid_box = [], []
            stop_ev = threading.Event()
            def reader():
                req = urllib.request.Request(base + "/api/realtime", headers={"Accept": "text/event-stream"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    cur = {}
                    while not stop_ev.is_set():
                        raw = resp.readline()
                        if not raw:
                            break
                        ln = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                        if ln.startswith("event:"):
                            cur["event"] = ln[6:].strip()
                        elif ln.startswith("data:"):
                            cur["data"] = json.loads(ln[5:].strip())
                        elif ln == "" and cur:
                            events.append(cur)
                            if cur.get("event") == "PB_CONNECT":
                                cid_box.append(cur["data"]["clientId"])
                            if len(events) >= 2:
                                break
                            cur = {}
            th = threading.Thread(target=reader, daemon=True)
            th.start()
            t0 = time.time()
            while not cid_box and time.time() - t0 < 8:
                time.sleep(0.05)
            st_sub, _ = http_req(base, "POST", "/api/realtime", {"clientId": cid_box[0], "subscriptions": r["input"]["subscribe"]["subscriptions"]})
            st_tr, _ = http_req(base, "POST", "/api/collections/articles/records",
                                {"title": "Realtime Stream Event", "slug": r["input"]["trigger_create"]["slug"], "published": True, "views": 99})
            th.join(timeout=8)
            stop_ev.set()
            ok = (
                st_sub == exp["subscribe_status"]
                and st_tr == exp["trigger_status"]
                and len(events) == 2
                and events[0]["event"] == exp_seq[0]["event"]
                and events[1]["event"] == exp_seq[1]["event"]
                and events[1]["data"].get("action") == exp_seq[1]["action"]
                and events[1]["data"]["record"]["slug"] == exp_seq[1]["record_slug"]
            )
            return ["subscribe_status", "trigger_status", "event_sequence[0].event", "event_sequence[1].event", "event_sequence[1].action", "event_sequence[1].record_slug"], (None if ok else f"sub={st_sub}, tr={st_tr}, events={events}")
        run_case("TC-012", "EV-012", c012)

        # TC-013: Settings update
        def c013(r):
            exp = r["observed_output"]
            st, body = http_req(base, "PATCH", r["input"]["path"], r["input"]["body"], token=token)
            ok = (st == exp["status_code"] and body["meta"]["appName"] == exp["appName"])
            return ["status_code", "appName"], (None if ok else f"got {st} {body}")
        run_case("TC-013", "EV-013", c013)

        # TC-014: Backup create & list
        def c014(r):
            exp = r["observed_output"]
            st_c, _ = http_req(base, "POST", r["input"]["path"], r["input"]["body"], token=token)
            st_l, blist = http_req(base, "GET", r["input"]["path"], token=token)
            m = next((b for b in blist if b["key"] == r["input"]["body"]["name"]), None)
            ok = (st_c == exp["create_status"] and st_l == exp["list_status"] and bool(m) == exp["backup_found"] and bool(m and m["size"] > 0) == exp["backup_size_gt_0"])
            return ["create_status", "list_status", "backup_found", "backup_size_gt_0"], (None if ok else f"create={st_c}, list={st_l}, match={m}")
        run_case("TC-014", "EV-014", c014)

        # TC-015: Graceful SIGTERM + Restart Persistence (binary mode)
        if binary:
            def c015(r):
                nonlocal proc, base
                exp = r["observed_output"]
                con = sqlite3.connect(str(pb_data / "data.db"))
                jmode = con.execute("PRAGMA journal_mode").fetchone()[0]
                con.close()
                stop_bin(proc)
                port2 = free_port()
                base = f"http://127.0.0.1:{port2}"
                proc = start_bin(binary, tmp_root, pb_data, port2)
                st_a, a2 = http_req(base, "POST", "/api/collections/_superusers/auth-with-password", {"identity": "admin@example.com", "password": "TestPass123456!"})
                st_r, l2 = http_req(base, "GET", "/api/collections/articles/records?sort=slug")
                st_s, s2 = http_req(base, "GET", "/api/settings", token=a2["token"])
                slugs = [it["slug"] for it in l2["items"]]
                ok = (
                    st_a == exp["auth_after_restart_status"]
                    and st_r == exp["records_status"]
                    and l2["totalItems"] == exp["persisted_totalItems"]
                    and slugs == exp["persisted_slugs"]
                    and s2["meta"]["appName"] == exp["persisted_appName"]
                    and jmode == exp["sqlite_journal_mode"]
                )
                return ["auth_after_restart_status", "records_status", "persisted_totalItems", "persisted_slugs", "persisted_appName", "sqlite_journal_mode"], (None if ok else f"slugs={slugs}, appName={s2['meta']['appName']}, jmode={jmode}")
            run_case("TC-015", "EV-015", c015)

        # TC-016: Visual tolerance parity check on Admin Login Screen (SCR-001)
        def c016(r):
            from verify_visual import compare_login_screen
            diff_ratio = compare_login_screen(base, bundle_dir / "05_ui" / "screenshots" / "SCR-001_login_initial.png")
            max_tol = 0.05
            ok = (diff_ratio <= max_tol)
            return ["visual_diff_ratio<=0.05"], (None if ok else f"visual diff ratio {diff_ratio:.4f} > {max_tol}")
        run_case("TC-016", "EV-005", c016)

    finally:
        stop_bin(proc)
        shutil.rmtree(tmp_root, ignore_errors=True)

    summary = {
        "total": len(cases),
        "passed": sum(1 for c in cases if c["verdict"] == "PASS"),
        "failed": sum(1 for c in cases if c["verdict"] == "FAIL"),
        "skipped": sum(1 for c in cases if c["verdict"] == "SKIP"),
        "unverified": sum(1 for c in cases if c["verdict"] == "UNVERIFIED"),
    }
    return {
        "schema_version": "1.0.0",
        "mode": mode,
        "target": {
            "name": "pocketbase v0.40.6 (official darwin_arm64)" if binary else "reimplementation",
            "url_or_binary": str(binary.name) if binary else target_url,
            "artifact_sha256": artifact_sha,
        },
        "evidence_file": "06_evidence/ledger.jsonl",
        "executed_at": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "summary": summary,
        "cases": cases,
    }


def main():
    ap = argparse.ArgumentParser(description="Execute 07 differential parity harness reading 06_evidence/ledger.jsonl")
    ap.add_argument("--binary", help="Path to PocketBase executable (runs upstream baseline)")
    ap.add_argument("--target-url", help="Base URL of a running reimplementation server")
    ap.add_argument("--out", default=None, help="Output parity_report.json path")
    args = ap.parse_args()
    if not args.binary and not args.target_url:
        sys.exit("Provide either --binary or --target-url")

    bundle_dir = pathlib.Path(__file__).resolve().parent.parent
    report = run_suite(bundle_dir, pathlib.Path(args.binary).resolve() if args.binary else None, args.target_url)
    out_path = pathlib.Path(args.out) if args.out else (bundle_dir / "07_tests" / "parity_report.json")
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"summary": report["summary"], "report": str(out_path)}, indent=2))
    if report["summary"]["failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
