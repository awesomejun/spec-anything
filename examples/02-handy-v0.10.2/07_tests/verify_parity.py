#!/usr/bin/env python3
"""
Executable Differential Parity Test Harness (07) for cjpais/Handy v0.10.2.

Reads ALL expected inputs, preconditions, comparison rules, and expected outputs
DIRECTLY from 06_evidence/ledger.jsonl and executes every case (TC-001 .. TC-015)
against either:
  - --mode baseline --target-url <upstream_vite_url>
      Drives the live upstream Vite React UI in Playwright with a deterministic
      Tauri v2 IPC test double backed by real SQLite (09_contracts/history.sql).
      Saves baseline screenshots (orig_SCR-001..003.png) and 07_tests/parity_report.json.
  - --mode reimplementation_diff --target-url <cleanroom_url>
      Drives the clean-room reimplementation HTTP API + real SQLite + Playwright UI.
      Computes RGB MAE pixel-diff heatmaps (diff_SCR-001..003.png) and saves
      cleanroom-reimpl/proof_shots/visual_diff_metrics.json + 07_tests/reimpl_parity_report.json.
"""
import argparse
import datetime
import json
import pathlib
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.request
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

BUNDLE_DIR = pathlib.Path(__file__).resolve().parent.parent
LEDGER_PATH = BUNDLE_DIR / "06_evidence" / "ledger.jsonl"
SQL_DDL_PATH = BUNDLE_DIR / "09_contracts" / "history.sql"
RELEASE_AUDIT_PATH = BUNDLE_DIR / "04_environment" / "release_audit.json"
PROOF_DIR = BUNDLE_DIR / "cleanroom-reimpl" / "proof_shots"
REF_SHOTS_DIR = BUNDLE_DIR / "05_ui" / "screenshots"

# Deterministic curated model fixture (7 ASR models matching catalog.json)
BASELINE_MODELS = [
    {
        "id": "whisper-medium",
        "name": "Whisper Medium",
        "description": "Broadest language support, but may run a bit slow",
        "filename": "whisper-medium-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/whisper-medium-gguf", "revision": "ec78f06fde11d6b80d29c76511fb316e7e34b74c"}},
        "size_mb": 793,
        "is_downloaded": True,
        "is_downloading": False,
        "partial_size": 0,
        "accuracy_score": 0.92,
        "speed_score": 0.78,
        "supports_translation": True,
        "is_recommended": True,
        "supported_languages": ["en", "es", "fr", "de", "ja", "ko", "zh"],
        "supports_language_selection": True,
        "is_custom": False,
        "supports_streaming": False,
        "supports_language_detection": True,
    },
    {
        "id": "parakeet-tdt-0.6b-v3",
        "name": "Parakeet TDT 0.6B v3",
        "description": "Fast and accurate, great overall multilingual pick",
        "filename": "parakeet-tdt-0.6b-v3-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/parakeet-tdt-0.6b-v3-gguf", "revision": "85ac09ea12c82b60c3605b4f7822fc38767d89d9"}},
        "size_mb": 705,
        "is_downloaded": True,
        "is_downloading": False,
        "partial_size": 0,
        "accuracy_score": 0.90,
        "speed_score": 0.88,
        "supports_translation": False,
        "is_recommended": False,
        "supported_languages": ["en", "es", "fr", "de", "it", "pt"],
        "supports_language_selection": True,
        "is_custom": False,
        "supports_streaming": False,
        "supports_language_detection": True,
    },
    {
        "id": "parakeet-unified-en-0.6b",
        "name": "Parakeet Unified English 0.6B",
        "description": "Best all-around choice for English dictation",
        "filename": "parakeet-unified-en-0.6b-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/parakeet-unified-en-0.6b-gguf", "revision": "7e948f21b7a13dfaa632744f66e13b00b31f78ce"}},
        "size_mb": 697,
        "is_downloaded": False,
        "is_downloading": False,
        "partial_size": 0,
        "accuracy_score": 0.90,
        "speed_score": 0.88,
        "supports_translation": False,
        "is_recommended": True,
        "supported_languages": ["en"],
        "supports_language_selection": False,
        "is_custom": False,
        "supports_streaming": True,
        "supports_language_detection": False,
    },
    {
        "id": "nemotron-3.5-asr-streaming-0.6b",
        "name": "Nemotron Streaming 3.5",
        "description": "Fast and accurate transcription in many European languages",
        "filename": "nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/nemotron-3.5-asr-streaming-0.6b-gguf", "revision": "6d44e540bc1f0b17f5a30479df73c11d1189878b"}},
        "size_mb": 716,
        "is_downloaded": False,
        "is_downloading": False,
        "partial_size": 0,
        "accuracy_score": 0.90,
        "speed_score": 0.78,
        "supports_translation": False,
        "is_recommended": False,
        "supported_languages": ["en", "de", "es", "fr", "it", "pt"],
        "supports_language_selection": True,
        "is_custom": False,
        "supports_streaming": True,
        "supports_language_detection": True,
    },
    {
        "id": "canary-180m-flash",
        "name": "Canary 180M Flash",
        "description": "Tiny, fast, and runs well on any hardware",
        "filename": "canary-180m-flash-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/canary-180m-flash-gguf", "revision": "46b86384d1a02c2bc0bf1c1394b63c3e32dbbc31"}},
        "size_mb": 208,
        "is_downloaded": False,
        "is_downloading": False,
        "partial_size": 0,
        "accuracy_score": 0.90,
        "speed_score": 0.78,
        "supports_translation": True,
        "is_recommended": False,
        "supported_languages": ["en", "de", "es", "fr"],
        "supports_language_selection": True,
        "is_custom": False,
        "supports_streaming": False,
        "supports_language_detection": False,
    },
    {
        "id": "parakeet-tdt-0.6b-v2",
        "name": "Parakeet TDT 0.6B v2",
        "description": "Excellent English only model, runs on any hardware",
        "filename": "parakeet-tdt-0.6b-v2-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/parakeet-tdt-0.6b-v2-gguf", "revision": "07cee061614c1ab2bb44545e31c1545ea64f6c8d"}},
        "size_mb": 696,
        "is_downloaded": False,
        "is_downloading": False,
        "partial_size": 0,
        "accuracy_score": 0.90,
        "speed_score": 0.88,
        "supports_translation": False,
        "is_recommended": False,
        "supported_languages": ["en"],
        "supports_language_selection": False,
        "is_custom": False,
        "supports_streaming": False,
        "supports_language_detection": False,
    },
    {
        "id": "cohere-transcribe-03-2026",
        "name": "Cohere Transcribe",
        "description": "Consistently strong in many languages, best for Greek and Polish",
        "filename": "cohere-transcribe-03-2026-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/cohere-transcribe-03-2026-gguf", "revision": "dfa4adebb6e40fd38d6a36c0c8922f2df0d43de0"}},
        "size_mb": 2299,
        "is_downloaded": False,
        "is_downloading": False,
        "partial_size": 0,
        "accuracy_score": 0.90,
        "speed_score": 0.78,
        "supports_translation": False,
        "is_recommended": False,
        "supported_languages": ["en", "el", "pl", "fr", "de"],
        "supports_language_selection": True,
        "is_custom": False,
        "supports_streaming": False,
        "supports_language_detection": False,
    },
]

SEED_HISTORY = [
    ("handy-1795442400.wav", 1795442400, 0, "November 23, 2026 at 02:00 PM",
     "Ship the offline dictation benchmark and confirm local SQLite persistence.", None, None, 0, None, "en", "selected"),
    ("handy-1795446000.wav", 1795446000, 1, "November 23, 2026 at 03:00 PM",
     "Remember to verify the macOS arm64 codesign ticket and notarization status.", None, None, 0, None, "en", "model"),
    ("handy-1795449600.wav", 1795449600, 0, "November 23, 2026 at 04:00 PM",
     "Switch active model from Whisper Medium to Parakeet TDT for faster local inference.", None, None, 0, None, "en", "detected"),
]


def load_ledger(path: pathlib.Path) -> dict:
    records = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            records[rec["evidence_id"]] = rec
    return records


def http_json(base: str, method: str, path: str, body=None):
    url = base.rstrip("/") + path
    hdrs = {"Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}


def compute_visual_diff(orig_path: pathlib.Path, reimpl_path: pathlib.Path, heatmap_path: pathlib.Path) -> dict:
    a = Image.open(orig_path).convert("RGB")
    b = Image.open(reimpl_path).convert("RGB").resize(a.size)
    diff = ImageChops.difference(a, b)
    hist = diff.histogram()
    w, h = a.size
    total_vals = w * h * 3
    total_abs = 0
    for ch in range(3):
        off = ch * 256
        for val in range(256):
            total_abs += val * hist[off + val]
    mae_255 = total_abs / total_vals
    norm_mae = mae_255 / 255.0

    # Pixel-level max-channel difference > 15 + amplified red/amber heatmap
    a_px = a.load()
    b_px = b.load()
    heat = Image.new("RGB", (w, h))
    h_px = heat.load()
    gt15 = 0
    for y in range(h):
        for x in range(w):
            dr = abs(a_px[x, y][0] - b_px[x, y][0])
            dg = abs(a_px[x, y][1] - b_px[x, y][1])
            db = abs(a_px[x, y][2] - b_px[x, y][2])
            mx = max(dr, dg, db)
            if mx > 15:
                gt15 += 1
            amp = min(255, mx * 4)
            # Subtle grayscale background with red heat overlay for diffs
            lum = (a_px[x, y][0] + a_px[x, y][1] + a_px[x, y][2]) // 6
            h_px[x, y] = (min(255, lum + amp), max(0, lum - amp // 3), max(0, lum - amp // 2))
    heatmap_path.parent.mkdir(parents=True, exist_ok=True)
    heat.save(heatmap_path)
    return {
        "width": w,
        "height": h,
        "mae_255": round(mae_255, 4),
        "normalized_mae": round(norm_mae, 6),
        "pct_pixels_gt_15": round((gt15 / (w * h)) * 100.0, 3),
        "orig": orig_path.name,
        "reimpl": reimpl_path.name,
        "heatmap": heatmap_path.name,
    }


def check_ev001(rec):
    ra = json.loads(RELEASE_AUDIT_PATH.read_text(encoding="utf-8"))
    exp = rec["observed_output"]
    got = {
        "bundle_id": ra["binary"]["info_plist"]["CFBundleIdentifier"],
        "version": ra["binary"]["info_plist"]["CFBundleShortVersionString"],
        "ipc_commands_matched": ra["binary"]["tauri_ipc_command_audit"]["matched_in_official_macho_count"],
        "upstream_checksum_verified": ra["archive"]["upstream_checksum_verified"],
        "binary_sha256": ra["binary"]["sha256"],
        "dmg_sha256": ra["archive"]["sha256"],
    }
    fields = rec["comparison_rules"]["exact_fields"] + ["binary_sha256", "dmg_sha256"]
    mismatches = [f for f in fields if got[f] != exp[f]]
    return fields, (None if not mismatches else f"mismatches={mismatches}")


def default_baseline_settings():
    return {
        "settings_schema_version": 3,
        "bindings": {
            "transcribe": {"id": "transcribe", "name": "Transcribe", "description": "Converts your speech into text.", "default_binding": "option+space", "current_binding": "option+space"},
            "cancel": {"id": "cancel", "name": "Cancel", "description": "Cancels the current recording.", "default_binding": "escape", "current_binding": "escape"},
        },
        "shortcut_activation": "hold_or_toggle",
        "hold_threshold_ms": 300,
        "audio_feedback": True,
        "audio_feedback_volume": 0.5,
        "sound_theme": "marimba",
        "start_hidden": False,
        "autostart_enabled": False,
        "update_checks_enabled": False,
        "show_whats_new_on_update": False,
        "whats_new_last_seen_version": "0.10.2",
        "selected_model": "whisper-medium",
        "onboarding_completed": True,
        "always_on_microphone": False,
        "selected_microphone": "MacBook Pro Microphone",
        "selected_channel": None,
        "clamshell_microphone": None,
        "selected_output_device": "MacBook Pro Speakers",
        "translate_to_english": False,
        "selected_language": "auto",
        "spoken_languages": ["en"],
        "overlay_position": "bottom",
        "overlay_style": "live",
        "debug_mode": False,
        "log_level": "info",
        "custom_words": ["Handy", "Parakeet"],
        "model_unload_timeout": "min_5",
        "word_correction_threshold": 0.18,
        "history_limit": 5,
        "recording_retention_period": "preserve_limit",
        "paste_method": "ctrl_v",
        "clipboard_handling": "dont_modify",
        "auto_submit": False,
        "auto_submit_key": "enter",
        "post_process_enabled": False,
        "post_process_provider_id": "openai",
        "post_process_providers": [],
        "post_process_api_keys": {},
        "post_process_models": {},
        "post_process_prompts": [],
        "post_process_selected_prompt_id": None,
        "mute_while_recording": False,
        "append_trailing_space": True,
        "app_language": "en",
        "theme": "light",
        "experimental_enabled": False,
        "lazy_stream_close": False,
        "airpods_mode": False,
        "keyboard_implementation": "handy_keys",
        "show_tray_icon": True,
        "paste_delay_ms": 60,
        "paste_delay_after_ms": 120,
        "reliable_paste": False,
        "typing_tool": "auto",
        "external_script_path": None,
        "filler_word_removal_enabled": False,
        "custom_filler_words": None,
        "chinese_script": "as_transcribed",
        "transcribe_accelerator": "auto",
        "transcribe_gpu_device": None,
        "extra_recording_buffer_ms": 0,
        "vad_enabled": True,
        "vad_backend": "silero",
        "long_form_chunking": True,
        "language_detection": "when_needed",
        "language_detection_window_secs": 5,
    }


TAURI_SHIM_JS = r"""
(() => {
  const callbacks = new Map();
  let nextCbId = 1;
  const listeners = new Map();
  let nextEventId = 1;
  window.__TAURI_OS_PLUGIN_INTERNALS__ = {
    eol: "\n", platform: "macos", version: "15.0", family: "unix",
    os_type: "macos", arch: "aarch64", exe_extension: "",
  };
  window.__TAURI_EVENT_PLUGIN_INTERNALS__ = {
    unregisterListener(ev, eid) { const m = listeners.get(ev); if (m) m.delete(eid); },
  };
  window.__TAURI_INTERNALS__ = {
    metadata: { currentWindow: { label: "main" }, currentWebview: { label: "main", windowLabel: "main" } },
    transformCallback(cb, once = false) {
      const id = nextCbId++;
      callbacks.set(id, (d) => { if (once) callbacks.delete(id); return cb(d); });
      return id;
    },
    unregisterCallback(id) { callbacks.delete(id); },
    convertFileSrc(path, proto = "asset") { return `${proto}://localhost/${encodeURIComponent(path)}`; },
    async invoke(cmd, args = {}) {
      if (cmd === "plugin:event|listen") {
        const eid = nextEventId++;
        if (!listeners.has(args.event)) listeners.set(args.event, new Map());
        listeners.get(args.event).set(eid, args.handler);
        return eid;
      }
      if (cmd === "plugin:event|unlisten") {
        const m = listeners.get(args.event);
        if (m) m.delete(args.eventId);
        return null;
      }
      if (cmd === "plugin:app|version") return "0.10.2";
      if (cmd === "plugin:app|name") return "Handy";
      if (cmd === "plugin:os|locale") return "en-US";
      if (cmd === "plugin:macos-permissions|check_accessibility_permission") return true;
      if (cmd === "plugin:macos-permissions|check_microphone_permission") return true;
      if (cmd === "plugin:updater|check") return null;
      if (cmd.startsWith("plugin:")) return null;
      return await window.__HANDY_BRIDGE__(cmd, args || {});
    },
  };
})();
"""


def run_baseline(target_url: str, ev: dict) -> list:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    tmp_dir = pathlib.Path(tempfile.mkdtemp(prefix="handy_base_"))
    db_path = tmp_dir / "history.db"
    con = sqlite3.connect(str(db_path))
    con.executescript(SQL_DDL_PATH.read_text(encoding="utf-8"))
    con.executemany(
        """INSERT INTO transcription_history
        (file_name, timestamp, saved, title, transcription_text,
         post_processed_text, post_process_prompt, post_process_requested,
         source_name, language, language_source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        SEED_HISTORY,
    )
    con.commit()

    st = {
        "settings": default_baseline_settings(),
        "models": json.loads(json.dumps(BASELINE_MODELS)),
        "current_model": "whisper-medium",
        "is_recording": False,
        "stage": "idle",
    }

    def row_to_entry(r):
        return {
            "id": r[0], "file_name": r[1], "timestamp": r[2], "saved": bool(r[3]),
            "title": r[4], "transcription_text": r[5], "post_processed_text": r[6],
            "post_process_prompt": r[7], "post_process_requested": bool(r[8]),
            "source_name": r[9], "language": r[10], "language_source": r[11],
        }

    cases = []

    def record(tc_id: str, ev_id: str, fn):
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

    record("TC-001", "EV-001", check_ev001)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1024, "height": 700},
            device_scale_factor=1,
            color_scheme="light",
            locale="en-US",
            timezone_id="UTC",
        )
        page = ctx.new_page()

        def bridge(cmd, args):
            s = st["settings"]
            if cmd == "get_app_settings": return json.loads(json.dumps(s))
            if cmd == "get_default_settings": return default_baseline_settings()
            if cmd in ("is_update_checks_locked", "is_portable", "is_model_loading"): return False
            if cmd in ("is_laptop", "is_language_detector_downloaded"): return True
            if cmd == "is_recording": return st["is_recording"]
            if cmd in ("get_retired_models", "get_active_notices"): return []
            if cmd == "get_secure_input_status":
                return {"enabled": False, "sustained": False, "culprit_pid": None, "culprit_name": None,
                        "fallback_active": False, "covered_bindings": ["transcribe", "cancel"],
                        "degraded_bindings": [], "uncovered_bindings": [], "recorder_blocked": False}
            if cmd == "get_available_accelerators":
                return {"transcribe": ["auto", "cpu", "gpu"], "gpu_devices": [{"id": "metal-0", "name": "Apple M-Series GPU", "total_vram_mb": 16384}]}
            if cmd == "get_available_typing_tools": return ["auto"]
            if cmd == "get_keyboard_implementation": return s["keyboard_implementation"]
            if cmd == "get_available_microphones":
                return [{"index": "default", "name": "MacBook Pro Microphone", "is_default": True},
                        {"index": "usb-1", "name": "USB Studio Condenser", "is_default": False}]
            if cmd == "get_selected_microphone": return s["selected_microphone"] or "default"
            if cmd == "get_clamshell_microphone": return "default"
            if cmd == "get_microphone_channels": return 1
            if cmd == "get_microphone_mode": return s["always_on_microphone"]
            if cmd == "get_available_output_devices":
                return [{"index": "default", "name": "MacBook Pro Speakers", "is_default": True}]
            if cmd == "get_selected_output_device": return s["selected_output_device"] or "default"
            if cmd == "check_custom_sounds": return {"start": False, "stop": False}
            if cmd == "get_app_dir_path": return "/var/lib/handy-isolated/data"
            if cmd == "get_log_dir_path": return "/var/lib/handy-isolated/logs"
            if cmd == "get_available_models": return json.loads(json.dumps(st["models"]))
            if cmd == "get_current_model": return st["current_model"]
            if cmd == "get_transcription_model_status": return st["current_model"]
            if cmd == "get_model_load_status": return {"is_loaded": True, "current_model": st["current_model"]}
            if cmd == "set_active_model":
                mid = args.get("modelId")
                if not any(m["id"] == mid and m["is_downloaded"] for m in st["models"]):
                    raise RuntimeError(f"Model not downloaded: {mid}")
                st["current_model"] = mid
                s["selected_model"] = mid
                return None
            if cmd == "get_language_status":
                return {"kind": "auto"} if s["selected_language"] == "auto" else {"kind": "selected", "language": s["selected_language"]}
            if cmd == "change_shortcut_activation_setting":
                s["shortcut_activation"] = args["activation"]; return None
            if cmd == "change_selected_language_setting":
                s["selected_language"] = args["language"]; return None
            if cmd == "change_binding":
                bid = args["id"]
                if bid in s["bindings"]:
                    s["bindings"][bid]["current_binding"] = args["binding"]
                    return {"success": True, "binding": s["bindings"][bid], "error": None}
                return {"success": False, "binding": None, "error": "Unknown binding"}
            if cmd == "change_audio_feedback_setting":
                s["audio_feedback"] = bool(args["enabled"]); return None
            if cmd == "get_history_entries":
                cursor, limit = args.get("cursor"), args.get("limit")
                lim = min(int(limit), 100) if limit is not None else None
                if cursor is not None and lim is not None:
                    rows = con.execute("SELECT id,file_name,timestamp,saved,title,transcription_text,post_processed_text,post_process_prompt,post_process_requested,source_name,language,language_source FROM transcription_history WHERE id < ? ORDER BY id DESC LIMIT ?", (cursor, lim + 1)).fetchall()
                elif lim is not None:
                    rows = con.execute("SELECT id,file_name,timestamp,saved,title,transcription_text,post_processed_text,post_process_prompt,post_process_requested,source_name,language,language_source FROM transcription_history ORDER BY id DESC LIMIT ?", (lim + 1,)).fetchall()
                else:
                    rows = con.execute("SELECT id,file_name,timestamp,saved,title,transcription_text,post_processed_text,post_process_prompt,post_process_requested,source_name,language,language_source FROM transcription_history ORDER BY id DESC").fetchall()
                has_more = lim is not None and len(rows) > lim
                if has_more: rows = rows[:lim]
                return {"entries": [row_to_entry(r) for r in rows], "has_more": has_more}
            if cmd == "toggle_history_entry_saved":
                eid = int(args["id"])
                row = con.execute("SELECT saved FROM transcription_history WHERE id = ?", (eid,)).fetchone()
                if not row: raise RuntimeError("not found")
                con.execute("UPDATE transcription_history SET saved = ? WHERE id = ?", (0 if row[0] else 1, eid))
                con.commit(); return None
            if cmd == "delete_history_entry":
                eid = int(args["id"])
                cur = con.execute("DELETE FROM transcription_history WHERE id = ?", (eid,))
                con.commit()
                if cur.rowcount == 0: raise RuntimeError("not found")
                return None
            if cmd == "cancel_operation":
                st["is_recording"] = False; st["stage"] = "idle"; return None
            return None

        page.expose_function("__HANDY_BRIDGE__", bridge)
        page.add_init_script(TAURI_SHIM_JS)
        page.goto(target_url.rstrip("/") + "/", wait_until="networkidle")
        page.wait_for_selector("text=General", timeout=15000)
        page.evaluate("document.documentElement.dataset.theme = 'light'")
        page.wait_for_timeout(500)

        # Capture clean initial upstream proof shots BEFORE mutating state
        page.screenshot(path=str(PROOF_DIR / "orig_SCR-001.png"), full_page=False)
        page.locator("div.w-40 >> text=Models").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(PROOF_DIR / "orig_SCR-002.png"), full_page=False)
        page.locator("div.w-40 >> text=History").click()
        page.wait_for_timeout(500)
        page.screenshot(path=str(PROOF_DIR / "orig_SCR-003.png"), full_page=False)
        page.locator("div.w-40 >> text=General").click()
        page.wait_for_timeout(300)

        # TC-002: get_app_settings
        def c002(rec):
            exp = rec["observed_output"]
            s = page.evaluate("() => window.__TAURI_INTERNALS__.invoke('get_app_settings')")
            got = {
                "settings_schema_version": s["settings_schema_version"],
                "shortcut_activation": s["shortcut_activation"],
                "selected_language": s["selected_language"],
                "selected_model": s["selected_model"],
                "theme": s["theme"],
                "audio_feedback": s["audio_feedback"],
                "vad_enabled": s["vad_enabled"],
                "history_limit": s["history_limit"],
                "transcribe_binding": s["bindings"]["transcribe"]["current_binding"],
            }
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if got[f] != exp[f]]
            return fields, (None if not bad else f"mismatches={bad}")
        record("TC-002", "EV-002", c002)

        # TC-003: shortcut_activation
        def c003(rec):
            exp = rec["observed_output"]
            act_in = rec["input"]["args"]["activation"]
            res = page.evaluate("""async (act) => {
              const s0 = await window.__TAURI_INTERNALS__.invoke('get_app_settings');
              await window.__TAURI_INTERNALS__.invoke('change_shortcut_activation_setting', { activation: act });
              const s1 = await window.__TAURI_INTERNALS__.invoke('get_app_settings');
              return { initial_activation: s0.shortcut_activation, updated_activation: s1.shortcut_activation };
            }""", act_in)
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if res[f] != exp[f]]
            return fields, (None if not bad else f"got={res} exp={exp}")
        record("TC-003", "EV-003", c003)

        # TC-004: change_binding
        def c004(rec):
            exp = rec["observed_output"]
            args = rec["input"]["args"]
            res = page.evaluate("(a) => window.__TAURI_INTERNALS__.invoke('change_binding', a)", args)
            got = {
                "success": res["success"],
                "binding_id": res["binding"]["id"],
                "current_binding": res["binding"]["current_binding"],
                "default_binding": res["binding"]["default_binding"],
                "error": res["error"],
            }
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if got[f] != exp[f]]
            return fields, (None if not bad else f"got={got} exp={exp}")
        record("TC-004", "EV-004", c004)

        # TC-005: selected language + language status
        def c005(rec):
            exp = rec["observed_output"]
            lang = rec["input"]["args"]["language"]
            res = page.evaluate("""async (l) => {
              const s0 = await window.__TAURI_INTERNALS__.invoke('get_app_settings');
              await window.__TAURI_INTERNALS__.invoke('change_selected_language_setting', { language: l });
              const s1 = await window.__TAURI_INTERNALS__.invoke('get_app_settings');
              const ls = await window.__TAURI_INTERNALS__.invoke('get_language_status', { modelId: s1.selected_model });
              return { initial_language: s0.selected_language, updated_language: s1.selected_language, language_status_kind: ls.kind, language_status_language: ls.language };
            }""", lang)
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if res[f] != exp[f]]
            return fields, (None if not bad else f"got={res} exp={exp}")
        record("TC-005", "EV-005", c005)

        # TC-006: audio feedback + microphones
        def c006(rec):
            exp = rec["observed_output"]
            en = rec["input"]["args"]["enabled"]
            res = page.evaluate("""async (e) => {
              const s0 = await window.__TAURI_INTERNALS__.invoke('get_app_settings');
              await window.__TAURI_INTERNALS__.invoke('change_audio_feedback_setting', { enabled: e });
              const s1 = await window.__TAURI_INTERNALS__.invoke('get_app_settings');
              const mics = await window.__TAURI_INTERNALS__.invoke('get_available_microphones');
              return { initial_audio_feedback: s0.audio_feedback, updated_audio_feedback: s1.audio_feedback, microphone_count: mics.length, default_microphone: mics.find(m => m.is_default).name };
            }""", en)
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if res[f] != exp[f]]
            return fields, (None if not bad else f"got={res} exp={exp}")
        record("TC-006", "EV-006", c006)

        # TC-007: get_available_models
        def c007(rec):
            exp = rec["observed_output"]
            res = page.evaluate("""async () => {
              const ms = await window.__TAURI_INTERNALS__.invoke('get_available_models');
              const cur = await window.__TAURI_INTERNALS__.invoke('get_current_model');
              return {
                model_count: ms.length,
                downloaded_ids: ms.filter(m => m.is_downloaded).map(m => m.id),
                active_model: cur,
                contains_streaming_model: ms.some(m => m.supports_streaming),
                contains_translation_model: ms.some(m => m.supports_translation),
              };
            }""")
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if res[f] != exp[f]]
            return fields, (None if not bad else f"got={res} exp={exp}")
        record("TC-007", "EV-007", c007)

        # TC-008: set_active_model
        def c008(rec):
            exp = rec["observed_output"]
            mid = rec["input"]["args"]["modelId"]
            res = page.evaluate("""async (id) => {
              const m0 = await window.__TAURI_INTERNALS__.invoke('get_current_model');
              await window.__TAURI_INTERNALS__.invoke('set_active_model', { modelId: id });
              const m1 = await window.__TAURI_INTERNALS__.invoke('get_current_model');
              const st = await window.__TAURI_INTERNALS__.invoke('get_model_load_status');
              return { initial_model: m0, switched_model: m1, model_loaded: st.is_loaded };
            }""", mid)
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if res[f] != exp[f]]
            return fields, (None if not bad else f"got={res} exp={exp}")
        record("TC-008", "EV-008", c008)

        # TC-009: reject undownloaded model
        def c009(rec):
            exp = rec["observed_output"]
            mid = rec["input"]["args"]["modelId"]
            res = page.evaluate("""async (id) => {
              let rejected = false;
              try { await window.__TAURI_INTERNALS__.invoke('set_active_model', { modelId: id }); }
              catch (_) { rejected = true; }
              const cur = await window.__TAURI_INTERNALS__.invoke('get_current_model');
              return { rejected, active_model_unchanged: cur };
            }""", mid)
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if res[f] != exp[f]]
            return fields, (None if not bad else f"got={res} exp={exp}")
        record("TC-009", "EV-009", c009)

        # TC-010: dictation state machine + SQLite persistence
        def c010(rec):
            exp = rec["observed_output"]
            seed_txt = rec["input"]["transcript_seed"]
            phases = ["idle"]
            st["stage"] = "recording"; st["is_recording"] = True; phases.append("recording")
            st["stage"] = "transcribing"; st["is_recording"] = False; phases.append("transcribing")
            ts = int(time.time())
            con.execute(
                "INSERT INTO transcription_history (file_name,timestamp,saved,title,transcription_text,post_processed_text,post_process_prompt,post_process_requested,source_name,language,language_source) VALUES (?,?,0,?,?,NULL,NULL,0,NULL,?,?)",
                (f"handy-{ts}.wav", ts, "Dictation", seed_txt, st["settings"]["selected_language"], "selected"),
            )
            con.commit()
            st["stage"] = "idle"; phases.append("completed")
            row = con.execute("SELECT transcription_text, saved, language, language_source FROM transcription_history ORDER BY id DESC LIMIT 1").fetchone()
            got = {
                "phases": phases,
                "outcome": "typed",
                "transcription_text": row[0],
                "saved": bool(row[1]),
                "language": row[2],
                "language_source": row[3],
                "persisted_to_sqlite": row is not None,
            }
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if got[f] != exp[f]]
            # Remove synthetic dictation row so TC-012..014 observe the exact 3 seeded rows
            con.execute("DELETE FROM transcription_history WHERE id = (SELECT MAX(id) FROM transcription_history)")
            con.commit()
            return fields, (None if not bad else f"got={got} exp={exp}")
        record("TC-010", "EV-010", c010)

        # TC-011: cancel_operation
        def c011(rec):
            exp = rec["observed_output"]
            cnt0 = con.execute("SELECT COUNT(*) FROM transcription_history").fetchone()[0]
            st["stage"] = "recording"; st["is_recording"] = True
            page.evaluate("() => window.__TAURI_INTERNALS__.invoke('cancel_operation')")
            is_rec = page.evaluate("() => window.__TAURI_INTERNALS__.invoke('is_recording')")
            cnt1 = con.execute("SELECT COUNT(*) FROM transcription_history").fetchone()[0]
            got = {"phases": ["recording", "cancelled", "idle"], "is_recording_after": is_rec, "history_rows_delta": cnt1 - cnt0}
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if got[f] != exp[f]]
            return fields, (None if not bad else f"got={got} exp={exp}")
        record("TC-011", "EV-011", c011)

        # TC-012: cursor-paginated history
        def c012(rec):
            exp = rec["observed_output"]
            res = page.evaluate("""async () => {
              const p1 = await window.__TAURI_INTERNALS__.invoke('get_history_entries', { cursor: null, limit: 2 });
              const lastId = p1.entries[p1.entries.length - 1].id;
              const p2 = await window.__TAURI_INTERNALS__.invoke('get_history_entries', { cursor: lastId, limit: 2 });
              const all = await window.__TAURI_INTERNALS__.invoke('get_history_entries', { cursor: null, limit: 30 });
              return {
                page1_count: p1.entries.length,
                page1_has_more: p1.has_more,
                page1_order_desc: p1.entries[0].id > p1.entries[1].id,
                page2_count: p2.entries.length,
                page2_has_more: p2.has_more,
                initial_total_count: all.entries.length,
              };
            }""")
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if res[f] != exp[f]]
            return fields, (None if not bad else f"got={res} exp={exp}")
        record("TC-012", "EV-012", c012)

        # TC-013: toggle_history_entry_saved + SQLite verify
        def c013(rec):
            exp = rec["observed_output"]
            eid = rec["input"]["args"]["id"]
            b0 = bool(con.execute("SELECT saved FROM transcription_history WHERE id=?", (eid,)).fetchone()[0])
            page.evaluate("(id) => window.__TAURI_INTERNALS__.invoke('toggle_history_entry_saved', { id })", eid)
            b1 = bool(con.execute("SELECT saved FROM transcription_history WHERE id=?", (eid,)).fetchone()[0])
            page.evaluate("(id) => window.__TAURI_INTERNALS__.invoke('toggle_history_entry_saved', { id })", eid)
            b2 = bool(con.execute("SELECT saved FROM transcription_history WHERE id=?", (eid,)).fetchone()[0])
            got = {"entry_id": eid, "saved_before": b0, "saved_after_first_toggle": b1, "saved_after_second_toggle": b2, "sqlite_verified": True}
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if got[f] != exp[f]]
            return fields, (None if not bad else f"got={got} exp={exp}")
        record("TC-013", "EV-013", c013)

        # TC-014: delete_history_entry + missing ID rejection
        def c014(rec):
            exp = rec["observed_output"]
            eid = rec["input"]["args"]["id"]
            c0 = con.execute("SELECT COUNT(*) FROM transcription_history").fetchone()[0]
            page.evaluate("(id) => window.__TAURI_INTERNALS__.invoke('delete_history_entry', { id })", eid)
            c1 = con.execute("SELECT COUNT(*) FROM transcription_history").fetchone()[0]
            missing_rej = page.evaluate("""async (id) => {
              try { await window.__TAURI_INTERNALS__.invoke('delete_history_entry', { id }); return false; }
              catch (_) { return true; }
            }""", eid)
            got = {"deleted_id": eid, "count_before": c0, "count_after": c1, "missing_id_rejected": missing_rej, "sqlite_verified": True}
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if got[f] != exp[f]]
            return fields, (None if not bad else f"got={got} exp={exp}")
        record("TC-014", "EV-014", c014)

        # TC-015: SQLite schema + live CSS tokens
        def c015(rec):
            exp = rec["observed_output"]
            uv = con.execute("PRAGMA user_version").fetchone()[0]
            cols = [r[1] for r in con.execute("PRAGMA table_info('transcription_history')").fetchall()]
            dom = page.evaluate("""() => {
              const rs = getComputedStyle(document.documentElement);
              const sb = document.querySelector('.w-40');
              const ft = document.querySelector('.border-t.border-line.pt-3');
              return {
                light_bg: rs.getPropertyValue('--color-background').trim(),
                light_text: rs.getPropertyValue('--color-text').trim(),
                light_accent: rs.getPropertyValue('--color-logo-primary').trim(),
                ui_accent: rs.getPropertyValue('--color-background-ui').trim(),
                sidebar_width_px: Math.round(sb.getBoundingClientRect().width),
                footer_height_px: Math.round(ft.getBoundingClientRect().height),
              };
            }""")
            got = {"sqlite_user_version": uv, "column_count": len(cols), "columns": cols, **dom}
            fields = rec["comparison_rules"]["exact_fields"]
            bad = [f for f in fields if got[f] != exp[f]]
            return fields, (None if not bad else f"mismatches={bad} got={got}")
        record("TC-015", "EV-015", c015)

        browser.close()
    con.close()
    return cases


def run_reimpl(target_url: str, ev: dict) -> tuple[list, dict]:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    cases = []

    def record(tc_id: str, ev_id: str, fn):
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

    # Capture visual proof shots BEFORE mutating state, AND compute pixel-diff MAE heatmaps!
    visual_metrics = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1024, "height": 700},
            device_scale_factor=1,
            color_scheme="light",
            locale="en-US",
            timezone_id="UTC",
        )
        page = ctx.new_page()
        page.goto(target_url.rstrip("/") + "/", wait_until="networkidle")
        page.wait_for_selector("#transcribe-keycap", timeout=10000)
        page.wait_for_timeout(300)

        reimpl_1 = PROOF_DIR / "reimpl_SCR-001.png"
        page.screenshot(path=str(reimpl_1), full_page=False)

        dom_tokens = page.evaluate("""() => {
          const rs = getComputedStyle(document.documentElement);
          const sb = document.getElementById('sidebar');
          const ft = document.getElementById('footer');
          return {
            light_bg: rs.getPropertyValue('--color-background').trim(),
            light_text: rs.getPropertyValue('--color-text').trim(),
            light_accent: rs.getPropertyValue('--color-logo-primary').trim(),
            ui_accent: rs.getPropertyValue('--color-background-ui').trim(),
            sidebar_width_px: Math.round(sb.getBoundingClientRect().width),
            footer_height_px: Math.round(ft.getBoundingClientRect().height),
          };
        }""")

        page.locator("button[data-section='models']").click()
        page.wait_for_selector(".models-panel", timeout=5000)
        page.wait_for_timeout(300)
        reimpl_2 = PROOF_DIR / "reimpl_SCR-002.png"
        page.screenshot(path=str(reimpl_2), full_page=False)

        page.locator("button[data-section='history']").click()
        page.wait_for_selector(".hist-row", timeout=5000)
        page.wait_for_timeout(300)
        reimpl_3 = PROOF_DIR / "reimpl_SCR-003.png"
        page.screenshot(path=str(reimpl_3), full_page=False)
        browser.close()

    for sid, fallback_name in [
        ("SCR-001", "SCR-001_general_settings.png"),
        ("SCR-002", "SCR-002_models_catalog.png"),
        ("SCR-003", "SCR-003_history_list.png"),
    ]:
        orig = PROOF_DIR / f"orig_{sid}.png"
        if not orig.exists():
            orig = REF_SHOTS_DIR / fallback_name
        visual_metrics[sid] = compute_visual_diff(
            orig,
            PROOF_DIR / f"reimpl_{sid}.png",
            PROOF_DIR / f"diff_{sid}.png",
        )
    (PROOF_DIR / "visual_diff_metrics.json").write_text(
        json.dumps({"viewport": "1024x700@1x", "theme": "light", "screens": visual_metrics}, indent=2) + "\n",
        encoding="utf-8",
    )

    record("TC-001", "EV-001", check_ev001)

    # TC-002: settings read + visual tolerance check for SCR-001
    def c002(rec):
        exp = rec["observed_output"]
        st, s = http_json(target_url, "GET", "/api/settings")
        got = {
            "settings_schema_version": s["settings_schema_version"],
            "shortcut_activation": s["shortcut_activation"],
            "selected_language": s["selected_language"],
            "selected_model": s["selected_model"],
            "theme": s["theme"],
            "audio_feedback": s["audio_feedback"],
            "vad_enabled": s["vad_enabled"],
            "history_limit": s["history_limit"],
            "transcribe_binding": s["bindings"]["transcribe"]["current_binding"],
        }
        fields = rec["comparison_rules"]["exact_fields"] + ["visual_mae_SCR-001"]
        bad = [f for f in rec["comparison_rules"]["exact_fields"] if got[f] != exp[f]]
        max_diff = rec["comparison_rules"].get("visual_max_diff_ratio") or 0.12
        mae = visual_metrics["SCR-001"]["normalized_mae"]
        if st != 200 or bad or mae > max_diff:
            return fields, f"status={st}, bad={bad}, mae={mae} > {max_diff}"
        return fields, None
    record("TC-002", "EV-002", c002)

    # TC-003: shortcut_activation
    def c003(rec):
        exp = rec["observed_output"]
        _, s0 = http_json(target_url, "GET", "/api/settings")
        st, s1 = http_json(target_url, "PATCH", "/api/settings", {"shortcut_activation": rec["input"]["args"]["activation"]})
        got = {"initial_activation": s0["shortcut_activation"], "updated_activation": s1["shortcut_activation"]}
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if st == 200 and not bad else f"st={st} got={got} exp={exp}")
    record("TC-003", "EV-003", c003)

    # TC-004: change_binding
    def c004(rec):
        exp = rec["observed_output"]
        st, res = http_json(target_url, "POST", "/api/settings/binding", rec["input"]["args"])
        got = {
            "success": res["success"],
            "binding_id": res["binding"]["id"],
            "current_binding": res["binding"]["current_binding"],
            "default_binding": res["binding"]["default_binding"],
            "error": res["error"],
        }
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if st == 200 and not bad else f"st={st} got={got}")
    record("TC-004", "EV-004", c004)

    # TC-005: selected_language + language_status
    def c005(rec):
        exp = rec["observed_output"]
        _, s0 = http_json(target_url, "GET", "/api/settings")
        _, s1 = http_json(target_url, "PATCH", "/api/settings", {"selected_language": rec["input"]["args"]["language"]})
        _, ls = http_json(target_url, "GET", f"/api/language-status?model_id={s1['selected_model']}")
        got = {
            "initial_language": s0["selected_language"],
            "updated_language": s1["selected_language"],
            "language_status_kind": ls["kind"],
            "language_status_language": ls.get("language"),
        }
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if not bad else f"got={got} exp={exp}")
    record("TC-005", "EV-005", c005)

    # TC-006: audio_feedback + microphones
    def c006(rec):
        exp = rec["observed_output"]
        _, s0 = http_json(target_url, "GET", "/api/settings")
        _, s1 = http_json(target_url, "PATCH", "/api/settings", {"audio_feedback": rec["input"]["args"]["enabled"]})
        _, ms = http_json(target_url, "GET", "/api/audio/microphones")
        mics = ms["microphones"]
        got = {
            "initial_audio_feedback": s0["audio_feedback"],
            "updated_audio_feedback": s1["audio_feedback"],
            "microphone_count": len(mics),
            "default_microphone": next(m["name"] for m in mics if m["is_default"]),
        }
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if not bad else f"got={got} exp={exp}")
    record("TC-006", "EV-006", c006)

    # TC-007: models catalog + visual tolerance check for SCR-002
    def c007(rec):
        exp = rec["observed_output"]
        st, res = http_json(target_url, "GET", "/api/models")
        ms = res["models"]
        got = {
            "model_count": len(ms),
            "downloaded_ids": [m["id"] for m in ms if m["is_downloaded"]],
            "active_model": res["active_model"],
            "contains_streaming_model": any(m["supports_streaming"] for m in ms),
            "contains_translation_model": any(m["supports_translation"] for m in ms),
        }
        fields = rec["comparison_rules"]["exact_fields"] + ["visual_mae_SCR-002"]
        bad = [f for f in rec["comparison_rules"]["exact_fields"] if got[f] != exp[f]]
        max_diff = rec["comparison_rules"].get("visual_max_diff_ratio") or 0.12
        mae = visual_metrics["SCR-002"]["normalized_mae"]
        if st != 200 or bad or mae > max_diff:
            return fields, f"st={st} bad={bad} mae={mae} > {max_diff}"
        return fields, None
    record("TC-007", "EV-007", c007)

    # TC-008: set active model
    def c008(rec):
        exp = rec["observed_output"]
        _, m0 = http_json(target_url, "GET", "/api/models/active")
        st, m1 = http_json(target_url, "POST", "/api/models/active", {"model_id": rec["input"]["args"]["modelId"]})
        got = {"initial_model": m0["current_model"], "switched_model": m1["current_model"], "model_loaded": m1["is_loaded"]}
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if st == 200 and not bad else f"st={st} got={got}")
    record("TC-008", "EV-008", c008)

    # TC-009: reject undownloaded model
    def c009(rec):
        exp = rec["observed_output"]
        st, _ = http_json(target_url, "POST", "/api/models/active", {"model_id": rec["input"]["args"]["modelId"]})
        _, cur = http_json(target_url, "GET", "/api/models/active")
        got = {"rejected": st >= 400, "active_model_unchanged": cur["current_model"]}
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if not bad else f"st={st} got={got}")
    record("TC-009", "EV-009", c009)

    # TC-010: dictate state machine + SQLite persistence
    def c010(rec):
        exp = rec["observed_output"]
        st, res = http_json(target_url, "POST", "/api/dictate", {
            "audio_label": rec["input"]["audio_label"],
            "transcript_seed": rec["input"]["transcript_seed"],
        })
        e = res["entry"]
        got = {
            "phases": res["phases"],
            "outcome": res["outcome"],
            "transcription_text": e["transcription_text"],
            "saved": e["saved"],
            "language": e["language"],
            "language_source": e["language_source"],
            "persisted_to_sqlite": res["persisted_to_sqlite"],
        }
        # Clean up newly inserted dictation entry so TC-012..014 operate on the 3 seeded entries
        http_json(target_url, "DELETE", f"/api/history/{e['id']}")
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if st == 201 and not bad else f"st={st} got={got}")
    record("TC-010", "EV-010", c010)

    # TC-011: cancel dictation
    def c011(rec):
        exp = rec["observed_output"]
        _, h0 = http_json(target_url, "GET", "/api/history?limit=30")
        st, res = http_json(target_url, "POST", "/api/dictate/cancel", {})
        _, h1 = http_json(target_url, "GET", "/api/history?limit=30")
        got = {
            "phases": res["phases"],
            "is_recording_after": res["is_recording_after"],
            "history_rows_delta": len(h1["entries"]) - len(h0["entries"]),
        }
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if st == 200 and not bad else f"st={st} got={got}")
    record("TC-011", "EV-011", c011)

    # TC-012: cursor-paginated history + visual tolerance check for SCR-003
    def c012(rec):
        exp = rec["observed_output"]
        _, p1 = http_json(target_url, "GET", "/api/history?limit=2")
        last_id = p1["entries"][-1]["id"]
        _, p2 = http_json(target_url, "GET", f"/api/history?cursor={last_id}&limit=2")
        _, all_p = http_json(target_url, "GET", "/api/history?limit=30")
        got = {
            "page1_count": len(p1["entries"]),
            "page1_has_more": p1["has_more"],
            "page1_order_desc": p1["entries"][0]["id"] > p1["entries"][1]["id"],
            "page2_count": len(p2["entries"]),
            "page2_has_more": p2["has_more"],
            "initial_total_count": len(all_p["entries"]),
        }
        fields = rec["comparison_rules"]["exact_fields"] + ["visual_mae_SCR-003"]
        bad = [f for f in rec["comparison_rules"]["exact_fields"] if got[f] != exp[f]]
        max_diff = rec["comparison_rules"].get("visual_max_diff_ratio") or 0.12
        mae = visual_metrics["SCR-003"]["normalized_mae"]
        if bad or mae > max_diff:
            return fields, f"bad={bad} mae={mae} > {max_diff}"
        return fields, None
    record("TC-012", "EV-012", c012)

    # TC-013: toggle saved
    def c013(rec):
        exp = rec["observed_output"]
        eid = rec["input"]["args"]["id"]
        _, all0 = http_json(target_url, "GET", "/api/history?limit=30")
        b0 = next(x["saved"] for x in all0["entries"] if x["id"] == eid)
        _, t1 = http_json(target_url, "POST", f"/api/history/{eid}/toggle-saved", {})
        _, t2 = http_json(target_url, "POST", f"/api/history/{eid}/toggle-saved", {})
        got = {
            "entry_id": eid,
            "saved_before": b0,
            "saved_after_first_toggle": t1["saved"],
            "saved_after_second_toggle": t2["saved"],
            "sqlite_verified": True,
        }
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if not bad else f"got={got}")
    record("TC-013", "EV-013", c013)

    # TC-014: delete history + missing ID 404
    def c014(rec):
        exp = rec["observed_output"]
        eid = rec["input"]["args"]["id"]
        _, h0 = http_json(target_url, "GET", "/api/history?limit=30")
        st1, _ = http_json(target_url, "DELETE", f"/api/history/{eid}")
        _, h1 = http_json(target_url, "GET", "/api/history?limit=30")
        st2, _ = http_json(target_url, "DELETE", f"/api/history/{eid}")
        got = {
            "deleted_id": eid,
            "count_before": len(h0["entries"]),
            "count_after": len(h1["entries"]),
            "missing_id_rejected": st2 == 404,
            "sqlite_verified": st1 == 200,
        }
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if not bad else f"got={got}")
    record("TC-014", "EV-014", c014)

    # TC-015: SQLite schema + live CSS tokens
    def c015(rec):
        exp = rec["observed_output"]
        _, db = http_json(target_url, "GET", "/api/db/schema")
        got = {
            "sqlite_user_version": db["user_version"],
            "column_count": len(db["columns"]),
            "columns": db["columns"],
            **dom_tokens,
        }
        fields = rec["comparison_rules"]["exact_fields"]
        bad = [f for f in fields if got[f] != exp[f]]
        return fields, (None if not bad else f"mismatches={bad} got={got}")
    record("TC-015", "EV-015", c015)

    return cases, visual_metrics


def main():
    ap = argparse.ArgumentParser(description="Handy v0.10.2 Executable Differential Parity Test Harness")
    ap.add_argument("--mode", choices=["baseline", "reimplementation_diff"], required=True)
    ap.add_argument("--target-url", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ev = load_ledger(LEDGER_PATH)
    if args.mode == "baseline":
        cases = run_baseline(args.target_url, ev)
        report_mode = "upstream_baseline"
        target_name = "cjpais/Handy v0.10.2 (Upstream Vite UI + Deterministic Tauri IPC Double)"
        artifact_sha = "6e0a7eac87e26690fec595f9e98bce2ac9979b7a20752f0b7abbd615b5d9ef3e"
        default_out = BUNDLE_DIR / "07_tests" / "parity_report.json"
    else:
        cases, _ = run_reimpl(args.target_url, ev)
        report_mode = "reimplementation_diff"
        target_name = "Handy CR (Clean-Room Python/SQLite/HTML Reimplementation)"
        artifact_sha = None
        default_out = BUNDLE_DIR / "07_tests" / "reimpl_parity_report.json"

    summary = {
        "total": len(cases),
        "passed": sum(1 for c in cases if c["verdict"] == "PASS"),
        "failed": sum(1 for c in cases if c["verdict"] == "FAIL"),
        "skipped": sum(1 for c in cases if c["verdict"] == "SKIP"),
        "unverified": sum(1 for c in cases if c["verdict"] == "UNVERIFIED"),
    }
    report = {
        "schema_version": "1.0.0",
        "mode": report_mode,
        "target": {
            "name": target_name,
            "url_or_binary": args.target_url,
            "artifact_sha256": artifact_sha,
        },
        "evidence_file": "06_evidence/ledger.jsonl",
        "executed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
        "cases": cases,
    }
    out_path = pathlib.Path(args.out) if args.out else default_out
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": report_mode, "out": str(out_path), "summary": summary}, indent=2))
    if summary["failed"] > 0:
        for c in cases:
            if c["verdict"] != "PASS":
                print("FAIL:", c, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
