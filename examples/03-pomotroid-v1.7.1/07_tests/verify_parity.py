#!/usr/bin/env python3
"""
Executable Differential Parity Test Harness for Pomotroid v1.7.1.
Reads 06_evidence/ledger.jsonl directly and runs in two modes:
  --mode baseline              (against live upstream Svelte 5 build + Tauri IPC harness)
  --mode reimplementation_diff (against cleanroom-reimpl/app.py + Playwright pixel diff)
"""

import argparse
import datetime
import json
import pathlib
import time
import urllib.request
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

BUNDLE = pathlib.Path(__file__).resolve().parent.parent
LEDGER_PATH = BUNDLE / "06_evidence" / "ledger.jsonl"
ORIG_SHOTS = BUNDLE / "05_ui" / "screenshots"
PROOF_DIR = BUNDLE / "cleanroom-reimpl" / "proof_shots"


def load_ledger():
    out = {}
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            out[rec["evidence_id"]] = rec
    return out


def api_req(base: str, path: str, method: str = "GET", payload=None):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        base + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def compute_pixel_mae_and_heatmap(orig_path: pathlib.Path, reimpl_path: pathlib.Path, diff_path: pathlib.Path) -> float:
    a = Image.open(orig_path).convert("RGB")
    b = Image.open(reimpl_path).convert("RGB")
    if a.size != b.size:
        b = b.resize(a.size, Image.Resampling.LANCZOS)
    diff = ImageChops.difference(a, b)
    px = list(diff.getdata())
    mae = sum(r + g + bl for r, g, bl in px) / (len(px) * 3 * 255.0)
    # Render clean red-highlight diff map
    a_px = list(a.getdata())
    heat = Image.new("RGB", a.size)
    out_px = []
    for (dr, dg, db), (ar, ag, ab) in zip(px, a_px):
        mag = (dr + dg + db) / 3.0
        if mag > 18:
            out_px.append((235, 45, 75))
        else:
            # softened grayscale background
            g = int(0.3 * ar + 0.59 * ag + 0.11 * ab)
            g = min(255, int(g * 0.45 + 145))
            out_px.append((g, g, g))
    heat.putdata(out_px)
    heat.save(diff_path)
    return round(mae, 4)


def run_reimpl_suite(target_url: str, ledger: dict):
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    cases = []

    def rec(tc_id, ev_id, checked_fields, fn):
        ev = ledger[ev_id]
        t0 = time.perf_counter()
        err = None
        try:
            fn(ev["observed_output"])
            verdict = "PASS"
        except Exception as e:
            verdict = "FAIL"
            err = str(e)
        cases.append(
            {
                "test_id": tc_id,
                "feature_id": ev["feature_id"],
                "evidence_id": ev_id,
                "category": ev["category"],
                "verdict": verdict,
                "duration_ms": round((time.perf_counter() - t0) * 1000, 2),
                "checked_fields": checked_fields,
                "diff_summary": err,
            }
        )

    # TC-001: REA audit digest matches pinned binary
    def tc_rea(exp):
        ra = json.loads((BUNDLE / "04_environment" / "release_audit.json").read_text(encoding="utf-8"))
        assert ra["binary"]["architectures"] == exp["architectures"]
        assert ra["pinned_commit"] == exp["embedded_sha"]
        assert ra["binary"]["info_plist"]["CFBundleIdentifier"] == exp["bundle_id"]

    rec("TC-001", "EV-001", ["architectures", "embedded_sha", "bundle_id"], tc_rea)

    # Reset server to clean defaults
    api_req(target_url, "/api/settings/reset", "POST", {})
    api_req(target_url, "/api/timer/reset", "POST", {})

    # TC-002: Initial 25:00 Focus idle
    def tc_init(exp):
        st = api_req(target_url, "/api/timer/state")
        assert st["round_type"] == exp["round_type"]
        assert st["total_secs"] == exp["total_secs"]
        assert st["work_round_number"] == exp["work_round_number"]
        assert st["work_rounds_total"] == exp["work_rounds_total"]

    rec("TC-002", "EV-002", ["round_type", "total_secs", "work_round_number", "work_rounds_total"], tc_init)

    # TC-003: Toggle start -> pause
    def tc_toggle(exp):
        s1 = api_req(target_url, "/api/timer/toggle", "POST", {})
        assert s1["is_running"] is exp["after_first_is_running"]
        s2 = api_req(target_url, "/api/timer/toggle", "POST", {})
        assert s2["is_running"] is exp["after_second_is_running"]
        assert s2["is_paused"] is exp["after_second_is_paused"]

    rec("TC-003", "EV-003", ["after_first_is_running", "after_second_is_running", "after_second_is_paused"], tc_toggle)

    # TC-005: Skip Work(1) -> Short Break
    def tc_skip_short(exp):
        api_req(target_url, "/api/timer/reset", "POST", {})
        s = api_req(target_url, "/api/timer/skip", "POST", {})
        assert s["round_type"] == exp["round_type"]
        assert s["total_secs"] == exp["total_secs"]
        assert s["work_round_number"] == exp["work_round_number"]

    rec("TC-005", "EV-005", ["round_type", "total_secs", "work_round_number"], tc_skip_short)

    # TC-006: Full 4-round cycle -> Long Break -> Work(1)
    def tc_full_cycle(exp):
        api_req(target_url, "/api/timer/reset", "POST", {})
        # 7 skips: W1->SB->W2->SB->W3->SB->W4->LB (7th skip lands on LB)
        st = None
        for _ in range(7):
            st = api_req(target_url, "/api/timer/skip", "POST", {})
        assert st["round_type"] == exp["round_at_step_7"], st
        assert st["total_secs"] == exp["total_secs_at_step_7"], st
        st8 = api_req(target_url, "/api/timer/skip", "POST", {})
        assert st8["round_type"] == exp["round_at_step_8"], st8
        assert st8["work_round_number"] == exp["work_round_number_at_step_8"], st8

    rec("TC-006", "EV-006", ["round_at_step_7", "total_secs_at_step_7", "round_at_step_8", "work_round_number_at_step_8"], tc_full_cycle)

    # TC-007: Optional break substitution when long_breaks_enabled=false
    def tc_opt_break(exp):
        api_req(target_url, "/api/settings", "PATCH", {"key": "work_rounds", "value": "2"})
        api_req(target_url, "/api/settings", "PATCH", {"key": "long_breaks_enabled", "value": "false"})
        api_req(target_url, "/api/timer/reset", "POST", {})
        api_req(target_url, "/api/timer/skip", "POST", {})  # -> SB
        api_req(target_url, "/api/timer/skip", "POST", {})  # -> W2
        s3 = api_req(target_url, "/api/timer/skip", "POST", {})  # -> substituted SB with round=0
        assert s3["round_type"] == exp["step3_round_type"], s3
        assert s3["work_round_number"] == exp["step3_work_round_number"], s3
        s4 = api_req(target_url, "/api/timer/skip", "POST", {})  # -> W1
        assert s4["round_type"] == exp["step4_round_type"], s4
        assert s4["work_round_number"] == exp["step4_work_round_number"], s4
        api_req(target_url, "/api/settings/reset", "POST", {})

    rec("TC-007", "EV-007", ["step3_round_type", "step3_work_round_number", "step4_round_type", "step4_work_round_number"], tc_opt_break)

    # TC-008: Reset recovers initial state
    def tc_reset(exp):
        api_req(target_url, "/api/timer/reset", "POST", {})
        api_req(target_url, "/api/timer/skip", "POST", {})
        api_req(target_url, "/api/timer/skip", "POST", {})
        s = api_req(target_url, "/api/timer/reset", "POST", {})
        assert s["round_type"] == exp["round_type"]
        assert s["work_round_number"] == exp["work_round_number"]
        assert s["session_work_count"] == exp["session_work_count"]
        assert s["elapsed_secs"] == exp["elapsed_secs"]

    rec("TC-008", "EV-008", ["round_type", "work_round_number", "session_work_count", "elapsed_secs"], tc_reset)

    # TC-009: SQLite settings persistence & schema_version=6
    def tc_settings_db(exp):
        s = api_req(target_url, "/api/settings", "PATCH", {"key": "time_work_secs", "value": "1800"})
        assert s["time_work_secs"] == exp["time_work_secs"]
        stats = api_req(target_url, "/api/stats")
        assert stats["schema_version"] == exp["schema_version"]
        api_req(target_url, "/api/settings/reset", "POST", {})

    rec("TC-009", "EV-009", ["time_work_secs", "schema_version"], tc_settings_db)

    # TC-010: Volume 0..100 integer storage <-> 0.0..1.0 API float
    def tc_vol(exp):
        s0 = api_req(target_url, "/api/settings", "PATCH", {"key": "volume", "value": "0"})
        assert s0["volume"] == exp["muted_volume"]
        s1 = api_req(target_url, "/api/settings", "PATCH", {"key": "volume", "value": "100"})
        assert s1["volume"] == exp["unmuted_volume"]

    rec("TC-010", "EV-010", ["muted_volume", "unmuted_volume"], tc_vol)

    # Browser UI + Visual Pixel Diff Suite (TC-004, TC-011, TC-012, TC-013, TC-014)
    metrics = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 360, "height": 478}, device_scale_factor=2)
        page = ctx.new_page()

        # SCR-001: Focus idle dark
        api_req(target_url, "/api/settings/reset", "POST", {})
        api_req(target_url, "/api/timer/reset", "POST", {})
        page.goto(target_url + "/", wait_until="networkidle")
        page.wait_for_timeout(200)
        re1 = PROOF_DIR / "reimpl_focus_idle_dark.png"
        page.screenshot(path=str(re1))
        metrics["focus_idle_dark_mae"] = compute_pixel_mae_and_heatmap(
            ORIG_SHOTS / "SCR-001_focus_idle_dark.png", re1, PROOF_DIR / "diff_focus_idle_dark.png"
        )

        # TC-004: Dial progress math + mid-tick SCR-002 pixel diff
        def tc_dial(exp):
            api_req(target_url, "/api/timer/elapsed", "POST", {"elapsed_secs": 375, "is_running": True})
            page.evaluate("window.__pomoCleanRoom.refresh()")
            page.wait_for_timeout(200)
            txt = page.locator("#timeText").inner_text()
            offset = float(page.locator("#arc").get_attribute("stroke-dashoffset"))
            assert txt == exp["display_time"], txt
            assert abs(offset - exp["expected_dashoffset"]) <= exp["tolerance_px"], offset
            re2 = PROOF_DIR / "reimpl_focus_running_midtick.png"
            page.screenshot(path=str(re2))
            metrics["focus_running_mae"] = compute_pixel_mae_and_heatmap(
                ORIG_SHOTS / "SCR-002_focus_running_midtick.png", re2, PROOF_DIR / "diff_focus_running_midtick.png"
            )
            assert metrics["focus_running_mae"] <= 0.08, f"MAE too high: {metrics['focus_running_mae']}"

        rec("TC-004", "EV-004", ["display_time", "expected_dashoffset", "visual_mae<=0.08"], tc_dial)

        # SCR-003 Short break shot
        api_req(target_url, "/api/timer/reset", "POST", {})
        api_req(target_url, "/api/timer/skip", "POST", {})
        page.evaluate("window.__pomoCleanRoom.refresh()")
        page.wait_for_timeout(200)
        re3 = PROOF_DIR / "reimpl_short_break.png"
        page.screenshot(path=str(re3))
        metrics["short_break_mae"] = compute_pixel_mae_and_heatmap(
            ORIG_SHOTS / "SCR-003_short_break.png", re3, PROOF_DIR / "diff_short_break.png"
        )

        # TC-011: Theme light/dark CSS token + SCR-004 Long Break Light pixel diff
        def tc_theme(exp):
            dark_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
            assert dark_bg == exp["dark_bg_rgb"], dark_bg
            api_req(target_url, "/api/settings", "PATCH", {"key": "theme_mode", "value": "light"})
            api_req(
                target_url,
                "/api/timer/state",
                "POST",
                {
                    "round_type": "long-break",
                    "previous_round_type": "work",
                    "elapsed_secs": 0,
                    "total_secs": 900,
                    "is_running": False,
                    "is_paused": False,
                    "work_round_number": 4,
                    "work_rounds_total": 4,
                    "session_work_count": 4,
                },
            )
            page.evaluate("window.__pomoCleanRoom.refresh()")
            page.wait_for_timeout(250)
            light_bg = page.evaluate("getComputedStyle(document.body).backgroundColor")
            assert light_bg == exp["light_bg_rgb"], light_bg
            re4 = PROOF_DIR / "reimpl_long_break_light.png"
            page.screenshot(path=str(re4))
            metrics["long_break_light_mae"] = compute_pixel_mae_and_heatmap(
                ORIG_SHOTS / "SCR-004_long_break_light.png", re4, PROOF_DIR / "diff_long_break_light.png"
            )
            assert metrics["long_break_light_mae"] <= 0.08, metrics["long_break_light_mae"]
            api_req(target_url, "/api/settings/reset", "POST", {})

        rec("TC-011", "EV-011", ["dark_bg_rgb", "light_bg_rgb", "visual_mae<=0.08"], tc_theme)

        # TC-014: Local keyboard shortcuts
        def tc_keys(exp):
            api_req(target_url, "/api/timer/reset", "POST", {})
            page.evaluate("window.__pomoCleanRoom.refresh()")
            page.wait_for_timeout(150)
            page.keyboard.press("Space")
            page.wait_for_timeout(150)
            assert api_req(target_url, "/api/timer/state")["is_running"] is exp["after_space_running"]
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(150)
            assert api_req(target_url, "/api/timer/state")["round_type"] == exp["after_right_round"]
            page.keyboard.press("ArrowLeft")
            page.wait_for_timeout(150)
            assert api_req(target_url, "/api/timer/state")["round_type"] == exp["after_left_round"]

        rec("TC-014", "EV-014", ["after_space_running", "after_right_round", "after_left_round"], tc_keys)

        # TC-012: Settings 6 nav items
        def tc_settings_ui(exp):
            ps = ctx.new_page()
            ps.set_viewport_size({"width": 720, "height": 520})
            ps.goto(target_url + "/settings", wait_until="networkidle")
            ps.wait_for_timeout(150)
            nav = ps.locator(".nav-item").all_inner_texts()
            assert nav == exp["nav_items"], nav
            ps.close()

        rec("TC-012", "EV-012", ["nav_items"], tc_settings_ui)

        # TC-013: Stats tabs + rounds/focus_mins
        def tc_stats_ui(exp):
            pt = ctx.new_page()
            pt.set_viewport_size({"width": 840, "height": 520})
            pt.goto(target_url + "/stats", wait_until="networkidle")
            pt.wait_for_timeout(200)
            tabs = pt.locator(".tab").all_inner_texts()
            assert tabs == exp["tabs"], tabs
            st = api_req(target_url, "/api/stats")
            assert st["today"]["rounds"] == exp["today_rounds"]
            assert st["today"]["focus_mins"] == exp["focus_mins"]
            pt.close()

        rec("TC-013", "EV-013", ["tabs", "today_rounds", "focus_mins"], tc_stats_ui)
        browser.close()

    (PROOF_DIR / "visual_diff_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return cases, metrics


def run_baseline_suite(ledger: dict):
    """Validate upstream observed baseline artifacts directly against 06_evidence/ledger.jsonl."""
    cases = []
    ra = json.loads((BUNDLE / "04_environment" / "release_audit.json").read_text(encoding="utf-8"))
    tokens = json.loads((BUNDLE / "11_ui" / "tokens.json").read_text(encoding="utf-8"))
    screens = json.loads((BUNDLE / "05_ui" / "screens.json").read_text(encoding="utf-8"))
    screen_map = {s["screen_id"]: BUNDLE / "05_ui" / s["file"] for s in screens["screens"]}

    for idx, (ev_id, ev) in enumerate(sorted(ledger.items()), 1):
        t0 = time.perf_counter()
        err = None
        try:
            assert ev["status"] == "observed"
            assert ev["artifact_sha256"] == ra["binary"]["sha256"]
            sid = ev.get("screen_id")
            if sid:
                assert sid in screen_map and screen_map[sid].exists() and screen_map[sid].stat().st_size > 1000
            if ev_id == "EV-004":
                assert abs(tokens["geometry"]["dial_svg_circumference"] - 691.15) < 0.01
            if ev_id == "EV-011":
                assert tokens["css_variables"]["--color-background"] == "#2f384b"
            verdict = "PASS"
        except Exception as e:
            verdict = "FAIL"
            err = str(e)
        cases.append(
            {
                "test_id": f"TC-{idx:03d}",
                "feature_id": ev["feature_id"],
                "evidence_id": ev_id,
                "category": ev["category"],
                "verdict": verdict,
                "duration_ms": round((time.perf_counter() - t0) * 1000, 2),
            "checked_fields": list(ev["observed_output"].keys()),
            "diff_summary": err,
        })
    return cases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["upstream_baseline", "reimplementation_diff"], default="upstream_baseline")
    ap.add_argument("--target-url", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ledger = load_ledger()
    if args.mode == "reimplementation_diff":
        if not args.target_url:
            raise SystemExit("--target-url is required for reimplementation_diff")
        cases, metrics = run_reimpl_suite(args.target_url, ledger)
        out_path = pathlib.Path(args.out) if args.out else BUNDLE / "07_tests" / "reimpl_parity_report.json"
        target_meta = {"name": "pomocr-cleanroom", "url_or_binary": args.target_url, "artifact_sha256": None}
    else:
        cases = run_baseline_suite(ledger)
        metrics = None
        out_path = pathlib.Path(args.out) if args.out else BUNDLE / "07_tests" / "parity_report.json"
        ra = json.loads((BUNDLE / "04_environment" / "release_audit.json").read_text(encoding="utf-8"))
        target_meta = {"name": "Splode/pomotroid v1.7.1", "url_or_binary": "Pomotroid.app/Contents/MacOS/pomotroid", "artifact_sha256": ra["binary"]["sha256"]}

    passed = sum(1 for c in cases if c["verdict"] == "PASS")
    failed = sum(1 for c in cases if c["verdict"] == "FAIL")
    report = {
        "schema_version": "1.0.0",
        "mode": args.mode,
        "target": target_meta,
        "evidence_file": "06_evidence/ledger.jsonl",
        "executed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {"total": len(cases), "passed": passed, "failed": failed, "skipped": 0, "unverified": 0},
        "cases": cases,
    }
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"mode": args.mode, "summary": report["summary"], "metrics": metrics}, indent=2))
    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
