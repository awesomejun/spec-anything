#!/usr/bin/env python3
"""Executable parity verification harness for usememos/memos 26.11.2.

Reads expected observations DIRECTLY from 06_evidence/evidence_v1.0.0.jsonl
and verifies them against either:
  1. --binary <path>  : spawns a fresh isolated target binary (full lifecycle + restart parity)
  2. --base-url <url> : runs non-restart HTTP/API parity against an already-running target
                        (e.g., a clean-room reimplementation in Rust/Go/TypeScript).

Outputs deterministic machine-readable results to --report-out.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def load_evidence(jsonl_path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for ln in jsonl_path.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        obj = json.loads(ln)
        records[obj["evidence_id"]] = obj
    return records


def http_json(
    opener: urllib.request.OpenerDirector,
    method: str,
    url: str,
    body: dict[str, Any] | None = None,
    bearer: str | None = None,
) -> tuple[int, dict[str, str], Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            try:
                parsed = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                parsed = raw
            return resp.status, hdrs, parsed
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8", errors="replace")
        hdrs = {k.lower(): v for k, v in err.headers.items()}
        try:
            parsed = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            parsed = raw
        return err.code, hdrs, parsed


def start_target(binary: Path, data_dir: Path, port: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        [
            str(binary),
            "--addr",
            "127.0.0.1",
            "--port",
            str(port),
            "--data",
            str(data_dir),
            "--driver",
            "sqlite",
            "--rate-limit=false",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    opener = urllib.request.build_opener()
    deadline = time.time() + 25.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"target binary exited early with code {proc.returncode}")
        try:
            st, _, _ = http_json(opener, "GET", f"{base}/api/instance/profile")
            if st == 200:
                return proc
        except Exception:
            pass
        time.sleep(0.2)
    proc.terminate()
    raise TimeoutError("Timed out waiting for target binary")


def stop_target(proc: subprocess.Popen | None) -> None:
    if proc is not None and proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def main() -> int:
    ap = argparse.ArgumentParser(description="Parity test harness driven directly by 06_evidence JSONL")
    ap.add_argument("--evidence", required=True, help="Path to 06_evidence/evidence_v1.0.0.jsonl")
    ap.add_argument("--binary", default="", help="Path to memos or reimplementation binary for isolated run")
    ap.add_argument("--base-url", default="", help="Existing server URL if not launching --binary")
    ap.add_argument("--target-label", default="upstream_official_26.11.2_darwin_arm64")
    ap.add_argument("--report-out", default="")
    args = ap.parse_args()

    ev_path = Path(args.evidence).resolve()
    ev = load_evidence(ev_path)

    proc: subprocess.Popen | None = None
    tmp_dir: Path | None = None
    results: list[dict[str, Any]] = []

    def record(case_id: str, feature_id: str, ev_id: str, category: str, passed: bool, expected: Any, actual: Any) -> None:
        results.append(
            {
                "case_id": case_id,
                "feature_id": feature_id,
                "evidence_id": ev_id,
                "category": category,
                "status": "PASS" if passed else "FAIL",
                "expected": expected,
                "actual": actual,
            }
        )

    try:
        if args.binary:
            binary = Path(args.binary).resolve()
            tmp_dir = Path(tempfile.mkdtemp(prefix="spec-anything-memos-parity-"))
            port = free_port()
            proc = start_target(binary, tmp_dir, port)
            base = f"http://127.0.0.1:{port}"
        elif args.base_url:
            base = args.base_url.rstrip("/")
        else:
            raise SystemExit("Either --binary or --base-url must be provided")

        anon = urllib.request.build_opener()

        # T-001 (EV-001 / F-001): Embedded SPA served, not 244B placeholder, strict cache headers
        exp1 = ev["EV-001"]["observed_output"]
        st_idx, hdr_idx, body_idx = http_json(anon, "GET", f"{base}/")
        idx_s = body_idx if isinstance(body_idx, str) else json.dumps(body_idx)
        actual1 = {
            "http_status": st_idx,
            "contains_source_placeholder": "No embeddable frontend found." in idx_s,
            "contains_vite_module_script": "/assets/" in idx_s,
            "cache_control": hdr_idx.get("cache-control", ""),
        }
        pass1 = (
            actual1["http_status"] == exp1["http_status"]
            and actual1["contains_source_placeholder"] == exp1["contains_source_placeholder"]
            and actual1["contains_vite_module_script"] == exp1["contains_vite_module_script"]
            and actual1["cache_control"] == exp1["cache_control"]
        )
        record("T-001", "F-001", "EV-001", "normal", pass1, {k: exp1[k] for k in actual1}, actual1)

        # T-002 (EV-002 / F-002): Pre-onboarding InstanceProfile (needsSetup + accessMode)
        exp2 = ev["EV-002"]["observed_output"]
        st_p, hdr_p, prof = http_json(anon, "GET", f"{base}/api/instance/profile")
        actual2 = {
            "http_status": st_p,
            "cache_control": hdr_p.get("cache-control", ""),
            "needs_setup": prof.get("needsSetup"),
            "access_mode": prof.get("accessMode"),
            "admin_present": bool(prof.get("admin")),
        }
        pass2 = (
            actual2["http_status"] == exp2["http_status"]
            and "no-store" in actual2["cache_control"].lower()
            and actual2["access_mode"] == exp2["access_mode"]
            and (actual2["needs_setup"] == exp2["needs_setup"] if args.binary else True)
            and actual2["admin_present"] == exp2["admin_present"]
        )
        record("T-002", "F-002", "EV-002", "normal", pass2, {k: exp2[k] for k in actual2}, actual2)

        # T-003 (EV-003 / F-003): Unauthenticated rejection on /api/auth/me and POST /api/memos
        exp3 = ev["EV-003"]["observed_output"]
        st_me0, _, b_me0 = http_json(anon, "GET", f"{base}/api/auth/me")
        st_cm0, _, b_cm0 = http_json(anon, "POST", f"{base}/api/memos", {"content": "denied", "visibility": "PUBLIC"})
        actual3 = {"get_me_status": st_me0, "post_memo_status": st_cm0}
        pass3 = actual3["get_me_status"] == exp3["get_me_status"] and actual3["post_memo_status"] == exp3["post_memo_status"]
        record("T-003", "F-003", "EV-003", "error_auth_boundary", pass3, {k: exp3[k] for k in actual3}, actual3)

        # T-004 (EV-004 / F-004): Host ADMIN onboarding & password omission
        exp4 = ev["EV-004"]["observed_output"]
        cj = CookieJar()
        auth = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        uname = "parityadmin"
        upass = "ParityPass!2026"
        st_cu, _, b_cu = http_json(
            auth,
            "POST",
            f"{base}/api/users",
            {"username": uname, "password": upass, "displayName": "Parity Admin", "role": "ADMIN"},
        )
        actual4 = {
            "http_status": st_cu,
            "role": b_cu.get("role"),
            "state": b_cu.get("state"),
            "password_field_empty_or_absent": (b_cu.get("password", "") == ""),
        }
        pass4 = all(actual4[k] == exp4[k] for k in actual4)
        record("T-004", "F-004", "EV-004", "normal", pass4, {k: exp4[k] for k in actual4}, actual4)

        # T-005 (EV-005 / F-005): Wrong password 400, REST vs Connect-RPC HeaderCarrier cookie split, /me, Refresh rotation
        exp5 = ev["EV-005"]["observed_output"]
        st_bad, _, _ = http_json(anon, "POST", f"{base}/api/auth/signin", {"passwordCredentials": {"username": uname, "password": "Bad!"}})
        st_si, hdr_si, b_si = http_json(auth, "POST", f"{base}/api/auth/signin", {"passwordCredentials": {"username": uname, "password": upass}})
        conn_cj = CookieJar()
        conn_auth = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(conn_cj))
        st_csi, hdr_csi, b_csi = http_json(conn_auth, "POST", f"{base}/memos.api.AuthService/SignIn", {"passwordCredentials": {"username": uname, "password": upass}})
        tok = b_csi.get("accessToken", "") or b_si.get("accessToken", "")
        st_me, _, b_me = http_json(conn_auth, "GET", f"{base}/api/auth/me", bearer=tok)
        st_ref, _, b_ref = http_json(conn_auth, "POST", f"{base}/memos.api.AuthService/RefreshToken", {})
        tok = b_ref.get("accessToken", "") or tok
        actual5 = {
            "wrong_password_status": st_bad,
            "rest_signin_status": st_si,
            "rest_sets_http_cookie": ("set-cookie" in hdr_si),
            "connect_signin_status": st_csi,
            "access_token_issued": bool(tok),
            "connect_set_cookie_httponly": "httponly" in hdr_csi.get("set-cookie", "").lower(),
            "me_status": st_me,
            "connect_refresh_status": st_ref,
            "connect_refresh_issued_token": bool(b_ref.get("accessToken")),
        }
        pass5 = all(actual5[k] == exp5[k] for k in actual5)
        record("T-005", "F-005", "EV-005", "normal_and_error", pass5, {k: exp5[k] for k in actual5}, actual5)

        # T-006 (EV-006 / F-006): CreateMemo ignores pinned=True on create & extracts tags
        exp6 = ev["EV-006"]["observed_output"]
        st_m1, _, m1 = http_json(
            auth,
            "POST",
            f"{base}/api/memos",
            {"content": "# Release Readiness\nParity check #release #architecture", "visibility": "PUBLIC", "pinned": True},
            bearer=tok,
        )
        st_m2, _, m2 = http_json(
            auth,
            "POST",
            f"{base}/api/memos",
            {"content": "Secret note 50%_off wildcard test #security #audit", "visibility": "PRIVATE"},
            bearer=tok,
        )
        st_m3, _, m3 = http_json(
            auth,
            "POST",
            f"{base}/api/memos",
            {"content": "Archive candidate #archive-test", "visibility": "PUBLIC"},
            bearer=tok,
        )
        st_m4, _, m4 = http_json(
            auth,
            "POST",
            f"{base}/api/memos",
            {"content": "Delete candidate #ephemeral", "visibility": "PRIVATE"},
            bearer=tok,
        )
        actual6 = {
            "m1_status": st_m1,
            "m1_visibility": m1.get("visibility"),
            "m1_state": m1.get("state"),
            "m1_pinned_on_create": m1.get("pinned", False),
            "m1_tags": sorted(m1.get("tags", [])),
            "m2_status": st_m2,
            "m2_visibility": m2.get("visibility"),
        }
        exp6_cmp = {
            "m1_status": exp6["m1_status"],
            "m1_visibility": exp6["m1_visibility"],
            "m1_state": exp6["m1_state"],
            "m1_pinned_on_create": exp6["m1_pinned_on_create"],
            "m1_tags": sorted(exp6["m1_tags"]),
            "m2_status": exp6["m2_status"],
            "m2_visibility": exp6["m2_visibility"],
        }
        record("T-006", "F-006", "EV-006", "normal_and_boundary", actual6 == exp6_cmp, exp6_cmp, actual6)

        # T-007 (EV-007 / F-007): PATCH pin/task-list, PATCH archive, DELETE + 404 verification
        exp7 = ev["EV-007"]["observed_output"]
        st_pin, _, m1p = http_json(
            auth,
            "PATCH",
            f"{base}/api/{m1['name']}?updateMask=pinned,content",
            {"name": m1["name"], "content": m1["content"] + "\n- [x] Verified", "pinned": True},
            bearer=tok,
        )
        st_arch, _, m3a = http_json(
            auth,
            "PATCH",
            f"{base}/api/{m3['name']}?updateMask=state",
            {"name": m3["name"], "state": "ARCHIVED"},
            bearer=tok,
        )
        st_del, _, _ = http_json(auth, "DELETE", f"{base}/api/{m4['name']}", bearer=tok)
        st_g404, _, _ = http_json(auth, "GET", f"{base}/api/{m4['name']}", bearer=tok)
        actual7 = {
            "pin_status": st_pin,
            "m1_pinned_after_patch": m1p.get("pinned"),
            "m1_has_task_list": (m1p.get("property") or {}).get("hasTaskList"),
            "archive_status": st_arch,
            "m3_state_after_patch": m3a.get("state"),
            "delete_status": st_del,
            "get_after_delete_status": st_g404,
        }
        pass7 = all(actual7[k] == exp7[k] for k in actual7)
        record("T-007", "F-007", "EV-007", "normal_and_error", pass7, {k: exp7[k] for k in actual7}, actual7)

        # T-008 (EV-008 / F-008): CEL tag filter, literal SQL wildcard escaping (50%_off vs 50X_off), invalid filter error, ARCHIVED list
        exp8 = ev["EV-008"]["observed_output"]
        st_ft, _, b_ft = http_json(auth, "GET", f"{base}/api/memos?{urllib.parse.urlencode({'filter': 'tag in [\"release\"]'})}", bearer=tok)
        st_fw, _, b_fw = http_json(auth, "GET", f"{base}/api/memos?{urllib.parse.urlencode({'filter': 'content.contains(\"50%_off\")'})}", bearer=tok)
        st_fn, _, b_fn = http_json(auth, "GET", f"{base}/api/memos?{urllib.parse.urlencode({'filter': 'content.contains(\"50X_off\")'})}", bearer=tok)
        st_fb, _, _ = http_json(auth, "GET", f"{base}/api/memos?{urllib.parse.urlencode({'filter': 'invalid_field == 123'})}", bearer=tok)
        st_la, _, b_la = http_json(auth, "GET", f"{base}/api/memos?state=ARCHIVED", bearer=tok)
        actual8 = {
            "tag_status": st_ft,
            "tag_count": len(b_ft.get("memos", [])),
            "wildcard_status": st_fw,
            "wildcard_count": len(b_fw.get("memos", [])),
            "wildcard_negative_status": st_fn,
            "wildcard_negative_count": len(b_fn.get("memos", [])),
            "invalid_filter_status": st_fb,
            "archived_status": st_la,
            "archived_count": len(b_la.get("memos", [])),
        }
        pass8 = all(actual8[k] == exp8[k] for k in actual8)
        record("T-008", "F-008", "EV-008", "boundary_and_error", pass8, {k: exp8[k] for k in actual8}, actual8)

        # T-009 (EV-009 / F-009): Visibility boundary + Share-token access on PRIVATE memo
        exp9 = ev["EV-009"]["observed_output"]
        st_pl, _, b_pl = http_json(anon, "GET", f"{base}/api/memos")
        st_pa, _, _ = http_json(anon, "GET", f"{base}/api/{m2['name']}")
        st_sh, _, b_sh = http_json(auth, "POST", f"{base}/api/{m2['name']}/shares", {}, bearer=tok)
        sh_tok = b_sh.get("name", "").rsplit("/", 1)[-1]
        st_gs, _, b_gs = http_json(anon, "GET", f"{base}/api/shares/{sh_tok}/memo")
        actual9 = {
            "anon_list_status": st_pl,
            "anon_list_count": len(b_pl.get("memos", [])),
            "anon_list_visibilities": [m.get("visibility") for m in b_pl.get("memos", [])],
            "anon_get_private_status": st_pa,
            "create_share_status": st_sh,
            "share_token_created": bool(sh_tok),
            "anon_get_shared_status": st_gs,
            "anon_get_shared_matches_private": b_gs.get("name") == m2["name"],
        }
        pass9 = all(actual9[k] == exp9[k] for k in actual9)
        record("T-009", "F-009", "EV-009", "security_boundary", pass9, {k: exp9[k] for k in actual9}, actual9)

        # T-010 (EV-010 / F-005): Connect-RPC SignOut revokes refresh cookie
        exp10 = ev["EV-010"]["observed_output"]
        st_so, _, _ = http_json(conn_auth, "POST", f"{base}/memos.api.AuthService/SignOut", {}, bearer=tok)
        st_ra, _, _ = http_json(conn_auth, "POST", f"{base}/memos.api.AuthService/RefreshToken", {})
        actual10 = {"signout_status": st_so, "refresh_after_signout_status": st_ra}
        pass10 = all(actual10[k] == exp10[k] for k in actual10)
        record("T-010", "F-005", "EV-010", "cancel_revoke", pass10, {k: exp10[k] for k in actual10}, actual10)

        # T-011 (EV-011 / F-010): SQLite schema + full SIGTERM process restart recovery (binary mode)
        if args.binary and tmp_dir is not None:
            exp11 = ev["EV-011"]["observed_output"]
            db_file = sorted(tmp_dir.glob("*.db"))[0]
            conn = sqlite3.connect(str(db_file))
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]
            conn.close()

            stop_target(proc)
            port2 = free_port()
            proc = start_target(Path(args.binary).resolve(), tmp_dir, port2)
            base2 = f"http://127.0.0.1:{port2}"
            re_auth = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
            st_si2, _, b_si2 = http_json(re_auth, "POST", f"{base2}/api/auth/signin", {"passwordCredentials": {"username": uname, "password": upass}})
            tok2 = b_si2.get("accessToken", "")
            _, _, lm2 = http_json(re_auth, "GET", f"{base2}/api/memos", bearer=tok2)
            _, _, la2 = http_json(re_auth, "GET", f"{base2}/api/memos?state=ARCHIVED", bearer=tok2)
            st_sh2, _, _ = http_json(anon, "GET", f"{base2}/api/shares/{sh_tok}/memo")

            actual11 = {
                "sqlite_tables": tables,
                "post_restart_signin_status": st_si2,
                "post_restart_normal_count": len(lm2.get("memos", [])),
                "post_restart_pinned_count": sum(1 for m in lm2.get("memos", []) if m.get("pinned")),
                "post_restart_archived_count": len(la2.get("memos", [])),
                "post_restart_share_status": st_sh2,
            }
            pass11 = all(actual11[k] == exp11[k] for k in actual11)
            record("T-011", "F-010", "EV-011", "restart_recovery", pass11, {k: exp11[k] for k in actual11}, actual11)

        passed_cnt = sum(1 for r in results if r["status"] == "PASS")
        failed_cnt = len(results) - passed_cnt
        report = {
            "schema_version": "1.0.0",
            "target_label": args.target_label,
            "evidence_source": ev_path.name,
            "total_cases": len(results),
            "passed": passed_cnt,
            "failed": failed_cnt,
            "overall_status": "PASS" if failed_cnt == 0 else "FAIL",
            "cases": results,
        }
        if args.report_out:
            out = Path(args.report_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if failed_cnt == 0 else 1
    finally:
        stop_target(proc)
        if tmp_dir and tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
