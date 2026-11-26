#!/usr/bin/env python3
"""Isolated runtime observer & Playwright UI capturer for usememos/memos 26.11.2.

Launches the official darwin_arm64 binary in an isolated directory on a dynamic
loopback port, exercises real UI + HTTP/API + SQLite + process-restart flows,
captures 8 UI screenshots (05), dumps live SQLite schema, measures DOM design
tokens (11), and writes machine-readable JSONL evidence (06) with zero raw
secret/JWT leakage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

BIN_SHA256_EXPECTED = "f6a73bf5c96d93fb8a0ec2c5bf5733a302d268cd287105f0d4a7ab6273405d5a"
PINNED_COMMIT = "00fcd170281a75fc0e95ec4f2f54f43d32fe81bd"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


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


def start_memos(binary: Path, data_dir: Path, port: int, log_path: Path) -> subprocess.Popen:
    log_f = log_path.open("ab")
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
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    opener = urllib.request.build_opener()
    deadline = time.time() + 25.0
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"memos exited early with code {proc.returncode}")
        try:
            st, _, _ = http_json(opener, "GET", f"{base}/api/instance/profile")
            if st == 200:
                return proc
        except Exception:
            pass
        time.sleep(0.25)
    proc.terminate()
    raise TimeoutError("Timed out waiting for memos /api/instance/profile")


def stop_memos(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def measure_dom_tokens(page) -> dict[str, Any]:
    return page.evaluate(
        """() => {
          const body = document.body;
          const bcs = getComputedStyle(body);
          const html = document.documentElement;
          const hcs = getComputedStyle(html);
          const heading = document.querySelector('h1, h2, h3');
          const btn = document.querySelector('button');
          const nav = document.querySelector('nav, aside, header');
          return {
            title: document.title,
            url_path: location.pathname + location.search,
            html_class: html.className,
            html_theme: html.getAttribute('data-theme') || null,
            body_bg: bcs.backgroundColor,
            body_color: bcs.color,
            body_font_family: bcs.fontFamily,
            body_font_size: bcs.fontSize,
            body_line_height: bcs.lineHeight,
            html_bg: hcs.backgroundColor,
            heading_font_size: heading ? getComputedStyle(heading).fontSize : null,
            heading_font_weight: heading ? getComputedStyle(heading).fontWeight : null,
            button_bg: btn ? getComputedStyle(btn).backgroundColor : null,
            button_radius: btn ? getComputedStyle(btn).borderRadius : null,
            nav_present: Boolean(nav),
            visible_text_sample: (body.innerText || '').trim().slice(0, 240)
          };
        }"""
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--binary", required=True)
    ap.add_argument("--work-dir", required=True)
    ap.add_argument("--bundle-dir", required=True)
    args = ap.parse_args()

    binary = Path(args.binary).resolve()
    work_dir = Path(args.work_dir).resolve()
    bundle_dir = Path(args.bundle_dir).resolve()

    data_dir = work_dir / "isolated-runtime-data"
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = work_dir / "memos-runtime.log"
    if log_path.exists():
        log_path.unlink()

    ss_dir = bundle_dir / "05_screenshots"
    ev_dir = bundle_dir / "06_evidence"
    ss_dir.mkdir(parents=True, exist_ok=True)
    ev_dir.mkdir(parents=True, exist_ok=True)

    bin_sha = sha256_file(binary)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env_label = f"macOS {platform.machine()} / Python {platform.python_version()} / Playwright Chromium / memos 26.11.2 (isolated SQLite)"

    evidence: list[dict[str, Any]] = []
    ui_records: list[dict[str, Any]] = []

    def add_ev(
        ev_id: str,
        feature_id: str,
        source_ref: str,
        input_pre: dict[str, Any],
        observed_out: dict[str, Any],
        status: str = "observed",
        limitations: str = "Observed against isolated official darwin_arm64 release binary with SQLite driver.",
        linked: dict[str, Any] | None = None,
    ) -> None:
        evidence.append(
            {
                "evidence_id": ev_id,
                "feature_id": feature_id,
                "source_ref": source_ref,
                "pinned_commit": PINNED_COMMIT,
                "artifact_sha256": bin_sha,
                "tool_and_env": env_label,
                "input_and_precondition": input_pre,
                "observed_output": observed_out,
                "status": status,
                "limitations": limitations,
                "linked_artifacts": linked or {},
            }
        )

    proc = start_memos(binary, data_dir, port, log_path)
    try:
        # 1. Embedded Frontend SPA & Cache Headers vs Source 244B Placeholder (F-001)
        anon_opener = urllib.request.build_opener()
        st_idx, hdr_idx, body_idx = http_json(anon_opener, "GET", f"{base}/")
        st_prof, hdr_prof, prof_init = http_json(anon_opener, "GET", f"{base}/api/instance/profile")
        st_robots, hdr_robots, body_robots = http_json(anon_opener, "GET", f"{base}/robots.txt")
        idx_str = body_idx if isinstance(body_idx, str) else json.dumps(body_idx)
        add_ev(
            "EV-001",
            "F-001",
            "server/frontend/frontend.go:22-119",
            {"method": "GET", "path": "/", "precondition": "fresh_isolated_instance"},
            {
                "http_status": st_idx,
                "html_bytes": len(idx_str.encode("utf-8")),
                "contains_source_placeholder": "No embeddable frontend found." in idx_str,
                "contains_vite_module_script": "/assets/" in idx_str,
                "cache_control": hdr_idx.get("cache-control", ""),
                "robots_status": st_robots,
                "robots_preview": str(body_robots)[:120],
            },
            linked={"contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S1"},
        )
        add_ev(
            "EV-002",
            "F-002",
            "server/api/instance_service.go (GetInstanceProfile)",
            {"method": "GET", "path": "/api/instance/profile", "precondition": "before_host_user_creation"},
            {
                "http_status": st_prof,
                "cache_control": hdr_prof.get("cache-control", ""),
                "version": prof_init.get("version"),
                "demo": prof_init.get("demo", False),
                "needs_setup": prof_init.get("needsSetup"),
                "access_mode": prof_init.get("accessMode"),
                "admin_present": bool(prof_init.get("admin")),
                "profile_keys": sorted(prof_init.keys()) if isinstance(prof_init, dict) else [],
            },
            linked={"contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S1"},
        )

        # 2. Unauthenticated boundary on protected endpoints (F-003)
        st_me_anon, _, body_me_anon = http_json(anon_opener, "GET", f"{base}/api/auth/me")
        st_create_anon, _, body_create_anon = http_json(
            anon_opener, "POST", f"{base}/api/memos", {"content": "unauthorized test", "visibility": "PUBLIC"}
        )
        add_ev(
            "EV-003",
            "F-003",
            "server/api/acl_config.go:11-56 & server/api/authz.go",
            {"requests": ["GET /api/auth/me", "POST /api/memos"], "auth": "none"},
            {
                "get_me_status": st_me_anon,
                "get_me_code": body_me_anon.get("code") if isinstance(body_me_anon, dict) else None,
                "post_memo_status": st_create_anon,
                "post_memo_code": body_create_anon.get("code") if isinstance(body_create_anon, dict) else None,
            },
            linked={"contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S2"},
        )

        # 3. Capture UI-01 (Onboarding / Host Sign-Up screen before host exists)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
                page = ctx.new_page()
                page.goto(f"{base}/", wait_until="load", timeout=20000)
                page.wait_for_timeout(1400)
                ui01_path = ss_dir / "UI-01_onboarding_signup_1440x900.png"
                page.screenshot(path=str(ui01_path), full_page=False)
                tok01 = measure_dom_tokens(page)
                ui_records.append(
                    {
                        "ui_id": "UI-01",
                        "feature_id": "F-002",
                        "filename": ui01_path.name,
                        "sha256": sha256_file(ui01_path),
                        "viewport": "1440x900",
                        "dpr": 1,
                        "state": "uninitialized_host_onboarding",
                        "tokens": tok01,
                    }
                )
                ctx.close()
            finally:
                browser.close()

        # 4. Create Host Admin User (F-004) & Sign In + Cookie + Refresh (F-005)
        cj = CookieJar()
        auth_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        host_user = "specadmin"
        host_pass = "SpecMemos!2026"
        st_cu, _, body_cu = http_json(
            auth_opener,
            "POST",
            f"{base}/api/users",
            {
                "username": host_user,
                "password": host_pass,
                "displayName": "Spec Admin",
                "email": "specadmin@example.local",
                "role": "ADMIN",
            },
        )
        st_prof_after, _, prof_after = http_json(anon_opener, "GET", f"{base}/api/instance/profile")
        add_ev(
            "EV-004",
            "F-004",
            "proto/api/user_service.proto:45-51 & server/api/user_service.go",
            {"method": "POST", "path": "/api/users", "username": host_user, "precondition": "zero_users_in_db"},
            {
                "http_status": st_cu,
                "user_name": body_cu.get("name"),
                "username": body_cu.get("username"),
                "role": body_cu.get("role"),
                "state": body_cu.get("state"),
                "password_field_empty_or_absent": (body_cu.get("password", "") == ""),
                "profile_needs_setup_after": prof_after.get("needsSetup"),
                "profile_admin_anon_after": prof_after.get("admin"),
            },
            linked={"ui_id": "UI-01", "contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S2"},
        )

        # Wrong password boundary (F-005)
        st_bad_pw, _, body_bad_pw = http_json(
            anon_opener,
            "POST",
            f"{base}/api/auth/signin",
            {"passwordCredentials": {"username": host_user, "password": "WrongPassword!"}},
        )

        # Valid SignIn via REST + Connect-RPC (proves HeaderCarrier Set-Cookie transport split!)
        st_si, hdr_si, body_si = http_json(
            auth_opener,
            "POST",
            f"{base}/api/auth/signin",
            {"passwordCredentials": {"username": host_user, "password": host_pass}},
        )
        rest_sets_cookie = "set-cookie" in hdr_si

        conn_cj = CookieJar()
        conn_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(conn_cj))
        st_csi, hdr_csi, body_csi = http_json(
            conn_opener,
            "POST",
            f"{base}/memos.api.AuthService/SignIn",
            {"passwordCredentials": {"username": host_user, "password": host_pass}},
        )
        access_token = body_csi.get("accessToken", "") or body_si.get("accessToken", "")
        cookie_names = [c.name for c in conn_cj]
        st_me, _, body_me = http_json(conn_opener, "GET", f"{base}/api/auth/me", bearer=access_token)
        st_ref, hdr_ref, body_ref = http_json(conn_opener, "POST", f"{base}/memos.api.AuthService/RefreshToken", {})
        refreshed_token = body_ref.get("accessToken", "") or access_token
        add_ev(
            "EV-005",
            "F-005",
            "proto/api/auth_service.proto:15-48 & server/api/header_carrier.go:75-87",
            {"flows": ["wrong_password_rest", "signin_rest", "signin_connect_rpc", "get_me", "refresh_token_connect_rpc"], "username": host_user},
            {
                "wrong_password_status": st_bad_pw,
                "rest_signin_status": st_si,
                "rest_sets_http_cookie": rest_sets_cookie,
                "connect_signin_status": st_csi,
                "access_token_issued": bool(access_token),
                "access_token_length": len(access_token),
                "connect_refresh_cookie_names": cookie_names,
                "connect_set_cookie_httponly": "httponly" in hdr_csi.get("set-cookie", "").lower(),
                "me_status": st_me,
                "me_username": (body_me.get("user") or {}).get("username"),
                "connect_refresh_status": st_ref,
                "connect_refresh_issued_token": bool(body_ref.get("accessToken")),
            },
            linked={"contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S2"},
        )
        token = refreshed_token

        # Capture UI-02 (Authenticated Empty Home state) via Playwright login
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
                page = ctx.new_page()
                page.goto(f"{base}/auth", wait_until="load", timeout=20000)
                page.wait_for_timeout(1200)
                inputs = page.locator("input")
                if inputs.count() >= 2:
                    inputs.nth(0).fill(host_user)
                    inputs.nth(1).fill(host_pass)
                    page.locator("button[type='submit']").first.click()
                    page.wait_for_timeout(1200)
                page.goto(f"{base}/", wait_until="load", timeout=20000)
                page.wait_for_timeout(1400)
                ui02_path = ss_dir / "UI-02_home_empty_1440x900.png"
                page.screenshot(path=str(ui02_path), full_page=False)
                tok02 = measure_dom_tokens(page)
                ui_records.append(
                    {
                        "ui_id": "UI-02",
                        "feature_id": "F-006",
                        "filename": ui02_path.name,
                        "sha256": sha256_file(ui02_path),
                        "viewport": "1440x900",
                        "dpr": 1,
                        "state": "authenticated_empty_timeline",
                        "tokens": tok02,
                    }
                )
                ctx.close()
            finally:
                browser.close()

        # 5. Memo CRUD, Pinned-on-create rule, Tags, Visibility, CEL Filter (F-006, F-007, F-008, F-009)
        st_m1, _, m1 = http_json(
            auth_opener,
            "POST",
            f"{base}/api/memos",
            {
                "content": "# Release Readiness\nVerified official binary checksum and embedded SPA bundle. #release #architecture",
                "visibility": "PUBLIC",
                "pinned": True,  # Spec check: proto states pinned is ignored on creation!
            },
            bearer=token,
        )
        st_m2, _, m2 = http_json(
            auth_opener,
            "POST",
            f"{base}/api/memos",
            {
                "content": "Internal audit note: discount token 50%_off must match literally without SQL wildcard leakage. #security #audit",
                "visibility": "PRIVATE",
            },
            bearer=token,
        )
        st_m3, _, m3 = http_json(
            auth_opener,
            "POST",
            f"{base}/api/memos",
            {
                "content": "Temporary scratch memo to verify ARCHIVED transition and restore flow. #archive-test",
                "visibility": "PUBLIC",
            },
            bearer=token,
        )
        st_m4, _, m4 = http_json(
            auth_opener,
            "POST",
            f"{base}/api/memos",
            {
                "content": "Ephemeral memo to verify hard DELETE and 404 boundary. #ephemeral",
                "visibility": "PRIVATE",
            },
            bearer=token,
        )

        # Pin m1 via PATCH (F-007)
        m1_name = m1["name"]
        st_pin, _, m1_pinned = http_json(
            auth_opener,
            "PATCH",
            f"{base}/api/{m1_name}?updateMask=pinned,content",
            {
                "name": m1_name,
                "content": m1["content"] + "\n- [x] Checksum verified",
                "pinned": True,
            },
            bearer=token,
        )

        # Archive m3 via PATCH (F-007)
        m3_name = m3["name"]
        st_arch, _, m3_arch = http_json(
            auth_opener,
            "PATCH",
            f"{base}/api/{m3_name}?updateMask=state",
            {"name": m3_name, "state": "ARCHIVED"},
            bearer=token,
        )

        # Delete m4 via DELETE and verify 404 on GetMemo (F-007)
        m4_name = m4["name"]
        st_del, _, _ = http_json(auth_opener, "DELETE", f"{base}/api/{m4_name}", bearer=token)
        st_get_del, _, body_get_del = http_json(auth_opener, "GET", f"{base}/api/{m4_name}", bearer=token)

        add_ev(
            "EV-006",
            "F-006",
            "proto/api/memo_service.proto:38-44 & server/api/memo_service.go (CreateMemo)",
            {"memos_created": 4, "m1_create_pinned_requested": True},
            {
                "m1_status": st_m1,
                "m1_name": m1.get("name"),
                "m1_visibility": m1.get("visibility"),
                "m1_state": m1.get("state"),
                "m1_pinned_on_create": m1.get("pinned", False),
                "m1_tags": m1.get("tags", []),
                "m2_status": st_m2,
                "m2_visibility": m2.get("visibility"),
                "m2_tags": m2.get("tags", []),
                "m3_status": st_m3,
                "m4_status": st_m4,
            },
            linked={"ui_id": "UI-03", "contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S3"},
        )
        add_ev(
            "EV-007",
            "F-007",
            "proto/api/memo_service.proto:48-61 & server/api/memo_service.go (UpdateMemo, DeleteMemo)",
            {"operations": ["patch_pin_and_content", "patch_archive", "delete_and_get_404"]},
            {
                "pin_status": st_pin,
                "m1_pinned_after_patch": m1_pinned.get("pinned"),
                "m1_has_task_list": (m1_pinned.get("property") or {}).get("hasTaskList"),
                "archive_status": st_arch,
                "m3_state_after_patch": m3_arch.get("state"),
                "delete_status": st_del,
                "get_after_delete_status": st_get_del,
                "get_after_delete_code": body_get_del.get("code") if isinstance(body_get_del, dict) else None,
            },
            linked={"ui_id": "UI-06", "contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S3"},
        )

        # 6. CEL Filter & Search + SQL Wildcard Escaping Edge Case (F-008)
        f_tag = urllib.parse.urlencode({"filter": 'tag in ["release"]'})
        st_ftag, _, body_ftag = http_json(auth_opener, "GET", f"{base}/api/memos?{f_tag}", bearer=token)

        f_wild = urllib.parse.urlencode({"filter": 'content.contains("50%_off")'})
        st_fwild, _, body_fwild = http_json(auth_opener, "GET", f"{base}/api/memos?{f_wild}", bearer=token)

        f_nonmatch = urllib.parse.urlencode({"filter": 'content.contains("50X_off")'})
        st_fnon, _, body_fnon = http_json(auth_opener, "GET", f"{base}/api/memos?{f_nonmatch}", bearer=token)

        f_bad = urllib.parse.urlencode({"filter": "invalid_field == 123"})
        st_fbad, _, body_fbad = http_json(auth_opener, "GET", f"{base}/api/memos?{f_bad}", bearer=token)

        st_list_arch, _, body_list_arch = http_json(auth_opener, "GET", f"{base}/api/memos?state=ARCHIVED", bearer=token)
        add_ev(
            "EV-008",
            "F-008",
            "filter/engine.go & server/api/memo_service.go (ListMemos)",
            {
                "tag_filter": 'tag in ["release"]',
                "wildcard_filter": 'content.contains("50%_off")',
                "wildcard_negative": 'content.contains("50X_off")',
                "invalid_filter": "invalid_field == 123",
                "archived_query": "state=ARCHIVED",
            },
            {
                "tag_status": st_ftag,
                "tag_count": len(body_ftag.get("memos", [])),
                "wildcard_status": st_fwild,
                "wildcard_count": len(body_fwild.get("memos", [])),
                "wildcard_negative_status": st_fnon,
                "wildcard_negative_count": len(body_fnon.get("memos", [])),
                "invalid_filter_status": st_fbad,
                "archived_status": st_list_arch,
                "archived_count": len(body_list_arch.get("memos", [])),
            },
            linked={"ui_id": "UI-04", "contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S4"},
        )

        # 7. Visibility Boundary & Share-Token Access on PRIVATE Memo (F-009)
        st_pub_list, _, body_pub_list = http_json(anon_opener, "GET", f"{base}/api/memos")
        m2_name = m2["name"]
        st_priv_anon, _, body_priv_anon = http_json(anon_opener, "GET", f"{base}/api/{m2_name}")
        st_share, _, body_share = http_json(
            auth_opener, "POST", f"{base}/api/{m2_name}/shares", {}, bearer=token
        )
        share_name = body_share.get("name", "")
        share_token = share_name.rsplit("/", 1)[-1] if "/" in share_name else ""
        st_get_shared, _, body_get_shared = http_json(
            anon_opener, "GET", f"{base}/api/shares/{share_token}/memo"
        )
        add_ev(
            "EV-009",
            "F-009",
            "server/api/memo_access.go & proto/api/memo_service.proto:135-154",
            {"private_memo": m2_name, "anonymous_checks": ["ListMemos", "GetMemo(private)", "GetSharedMemo(token)"]},
            {
                "anon_list_status": st_pub_list,
                "anon_list_count": len(body_pub_list.get("memos", [])),
                "anon_list_visibilities": [m.get("visibility") for m in body_pub_list.get("memos", [])],
                "anon_get_private_status": st_priv_anon,
                "create_share_status": st_share,
                "share_token_created": bool(share_token),
                "anon_get_shared_status": st_get_shared,
                "anon_get_shared_matches_private": body_get_shared.get("name") == m2_name,
            },
            linked={"ui_id": "UI-05", "contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S5"},
        )

        # 8. Capture UI-03..UI-08 via Playwright!
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                # Authenticated desktop context
                ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
                page = ctx.new_page()
                page.goto(f"{base}/auth", wait_until="load", timeout=20000)
                page.wait_for_timeout(1200)
                inputs = page.locator("input")
                if inputs.count() >= 2:
                    inputs.nth(0).fill(host_user)
                    inputs.nth(1).fill(host_pass)
                    page.locator("button[type='submit']").first.click()
                    page.wait_for_timeout(1200)

                # UI-03: Populated Home timeline
                page.goto(f"{base}/", wait_until="load", timeout=20000)
                page.wait_for_timeout(1500)
                ui03_path = ss_dir / "UI-03_home_populated_1440x900.png"
                page.screenshot(path=str(ui03_path), full_page=False)
                ui_records.append(
                    {
                        "ui_id": "UI-03",
                        "feature_id": "F-006",
                        "filename": ui03_path.name,
                        "sha256": sha256_file(ui03_path),
                        "viewport": "1440x900",
                        "dpr": 1,
                        "state": "authenticated_populated_timeline",
                        "tokens": measure_dom_tokens(page),
                    }
                )

                # UI-04: Filtered timeline (?filter=tag:release or search query)
                q_filter = urllib.parse.urlencode({"filter": 'tag in ["release"]'})
                page.goto(f"{base}/?{q_filter}", wait_until="load", timeout=20000)
                page.wait_for_timeout(1500)
                ui04_path = ss_dir / "UI-04_search_tag_filter_1440x900.png"
                page.screenshot(path=str(ui04_path), full_page=False)
                ui_records.append(
                    {
                        "ui_id": "UI-04",
                        "feature_id": "F-008",
                        "filename": ui04_path.name,
                        "sha256": sha256_file(ui04_path),
                        "viewport": "1440x900",
                        "dpr": 1,
                        "state": "tag_filter_active",
                        "tokens": measure_dom_tokens(page),
                    }
                )

                # UI-05: Memo detail page
                m1_uid = m1_name.split("/", 1)[1]
                page.goto(f"{base}/memos/{m1_uid}", wait_until="load", timeout=20000)
                page.wait_for_timeout(1500)
                ui05_path = ss_dir / "UI-05_memo_detail_1440x900.png"
                page.screenshot(path=str(ui05_path), full_page=False)
                ui_records.append(
                    {
                        "ui_id": "UI-05",
                        "feature_id": "F-009",
                        "filename": ui05_path.name,
                        "sha256": sha256_file(ui05_path),
                        "viewport": "1440x900",
                        "dpr": 1,
                        "state": "memo_detail_view",
                        "tokens": measure_dom_tokens(page),
                    }
                )

                # UI-06: Archived memos page
                page.goto(f"{base}/archived", wait_until="load", timeout=20000)
                page.wait_for_timeout(1500)
                ui06_path = ss_dir / "UI-06_archived_view_1440x900.png"
                page.screenshot(path=str(ui06_path), full_page=False)
                ui_records.append(
                    {
                        "ui_id": "UI-06",
                        "feature_id": "F-007",
                        "filename": ui06_path.name,
                        "sha256": sha256_file(ui06_path),
                        "viewport": "1440x900",
                        "dpr": 1,
                        "state": "archived_memos_view",
                        "tokens": measure_dom_tokens(page),
                    }
                )
                ctx.close()

                # UI-07: Anonymous /explore visibility boundary (PUBLIC visible, PRIVATE hidden)
                anon_ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
                apage = anon_ctx.new_page()
                apage.goto(f"{base}/explore", wait_until="load", timeout=20000)
                apage.wait_for_timeout(1500)
                ui07_path = ss_dir / "UI-07_explore_signed_out_1440x900.png"
                apage.screenshot(path=str(ui07_path), full_page=False)
                tok07 = measure_dom_tokens(apage)
                ui_records.append(
                    {
                        "ui_id": "UI-07",
                        "feature_id": "F-009",
                        "filename": ui07_path.name,
                        "sha256": sha256_file(ui07_path),
                        "viewport": "1440x900",
                        "dpr": 1,
                        "state": "signed_out_explore_public_only",
                        "tokens": tok07,
                    }
                )
                anon_ctx.close()

                # UI-08: Mobile responsive viewport (390x844)
                mob_ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2)
                mpage = mob_ctx.new_page()
                mpage.goto(f"{base}/explore", wait_until="load", timeout=20000)
                mpage.wait_for_timeout(1500)
                ui08_path = ss_dir / "UI-08_mobile_explore_390x844.png"
                mpage.screenshot(path=str(ui08_path), full_page=False)
                ui_records.append(
                    {
                        "ui_id": "UI-08",
                        "feature_id": "F-011",
                        "filename": ui08_path.name,
                        "sha256": sha256_file(ui08_path),
                        "viewport": "390x844",
                        "dpr": 2,
                        "state": "mobile_responsive_explore",
                        "tokens": measure_dom_tokens(mpage),
                    }
                )
                mob_ctx.close()
            finally:
                browser.close()

        # 9. Sign-Out Session Revocation via Connect-RPC (F-005)
        st_so, _, _ = http_json(conn_opener, "POST", f"{base}/memos.api.AuthService/SignOut", {}, bearer=token)
        st_ref_after_so, _, _ = http_json(conn_opener, "POST", f"{base}/memos.api.AuthService/RefreshToken", {})
        add_ev(
            "EV-010",
            "F-005",
            "proto/api/auth_service.proto:46-48 & server/api/auth_service_session.go:73-97",
            {"sequence": ["POST /memos.api.AuthService/SignOut", "POST /memos.api.AuthService/RefreshToken"]},
            {
                "signout_status": st_so,
                "refresh_after_signout_status": st_ref_after_so,
            },
            linked={"contract_ref": "09_contracts/openapi_v1.0.0.json", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S2"},
        )

        # 10. Inspect Live SQLite Database Schema & Persisted Rows BEFORE Restart (F-010)
        db_files = sorted(data_dir.glob("*.db"))
        if not db_files:
            raise FileNotFoundError(f"No SQLite .db file created in {data_dir}")
        db_path = db_files[0]
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()]
        ddl_rows = [r[0] + ";" for r in cur.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type DESC, name ASC").fetchall()]
        user_cnt = cur.execute("SELECT COUNT(*) FROM user").fetchone()[0]
        memo_rows = cur.execute("SELECT uid, row_status, visibility, pinned FROM memo ORDER BY id ASC").fetchall()
        share_cnt = cur.execute("SELECT COUNT(*) FROM memo_share").fetchone()[0]
        conn.close()

        live_sql_path = ev_dir / "live_sqlite_schema_v1.0.0.sql"
        live_sql_path.write_text("\n\n".join(ddl_rows) + "\n", encoding="utf-8")

        # 11. Full Process Restart Persistence Verification (F-010)
        stop_memos(proc)
        port2 = free_port()
        base2 = f"http://127.0.0.1:{port2}"
        proc = start_memos(binary, data_dir, port2, log_path)

        cj2 = CookieJar()
        re_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj2))
        st_si2, _, body_si2 = http_json(
            re_opener,
            "POST",
            f"{base2}/api/auth/signin",
            {"passwordCredentials": {"username": host_user, "password": host_pass}},
        )
        tok2 = body_si2.get("accessToken", "")
        st_lm2, _, lm2 = http_json(re_opener, "GET", f"{base2}/api/memos", bearer=tok2)
        st_la2, _, la2 = http_json(re_opener, "GET", f"{base2}/api/memos?state=ARCHIVED", bearer=tok2)
        st_sh2, _, sh2 = http_json(anon_opener, "GET", f"{base2}/api/shares/{share_token}/memo")

        add_ev(
            "EV-011",
            "F-010",
            "store/migration/sqlite/LATEST.sql & store/db/sqlite/sqlite.go",
            {"db_filename": db_path.name, "restart_sequence": ["SIGTERM", "restart_on_new_port", "signin", "list_normal_and_archived", "get_shared"]},
            {
                "sqlite_tables": tables,
                "sqlite_table_count": len(tables),
                "user_count": user_cnt,
                "memo_rows_before_restart": [
                    {"row_status": r[1], "visibility": r[2], "pinned": r[3]} for r in memo_rows
                ],
                "memo_share_count": share_cnt,
                "post_restart_signin_status": st_si2,
                "post_restart_normal_count": len(lm2.get("memos", [])),
                "post_restart_pinned_count": sum(1 for m in lm2.get("memos", []) if m.get("pinned")),
                "post_restart_archived_count": len(la2.get("memos", [])),
                "post_restart_share_status": st_sh2,
            },
            linked={"contract_ref": "09_contracts/schema_v1.0.0.sql", "diagram_ref": "10_실행_상태_도표_v1.0.0.md#S6"},
        )

        # 12. Record UI Capture Summary Evidence (F-011)
        add_ev(
            "EV-012",
            "F-011",
            "web/src/router/index.tsx & web/src/pages/*",
            {"viewports": ["1440x900@1x", "390x844@2x"], "capture_count": len(ui_records)},
            {
                "screenshots": [
                    {"ui_id": r["ui_id"], "filename": r["filename"], "sha256": r["sha256"], "state": r["state"], "viewport": r["viewport"]}
                    for r in ui_records
                ],
                "signed_out_explore_hides_private": "50%_off" not in (tok07.get("visible_text_sample") or ""),
            },
            linked={"ui_ids": [r["ui_id"] for r in ui_records], "spec_ref": "11_UI_구현_자료_v1.0.0.md"},
        )

        # 13. Explicitly record unverified external-integration boundaries (F-012)
        add_ev(
            "EV-013",
            "F-012",
            "server/api/auth_service_sso.go & server/api/attachment_service_storage.go & server/api/ai_service.go",
            {"scope": "external_oauth2_sso_and_s3_and_smtp_and_ai_provider"},
            {"status_note": "Verified at proto/Go code level only; live third-party OAuth2/S3/SMTP/AI calls excluded from isolated offline run."},
            status="code-verified",
            limitations="Requires external OAuth2 IdP, S3 bucket, SMTP server, or AI API key; re-verify using local mock IdP/MinIO/Mailpit test doubles.",
            linked={"spec_ref": "04_재현_환경_명세_v1.0.0.md"},
        )

        ev_path = ev_dir / "evidence_v1.0.0.jsonl"
        with ev_path.open("w", encoding="utf-8") as f:
            for rec in evidence:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        ui_meta_path = ev_dir / "ui_measurements_v1.0.0.json"
        ui_meta_path.write_text(json.dumps(ui_records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        print(json.dumps({"evidence_records": len(evidence), "screenshots": len(ui_records), "sqlite_tables": tables}, indent=2))
        return 0
    finally:
        stop_memos(proc)


if __name__ == "__main__":
    raise SystemExit(main())
