#!/usr/bin/env python3
"""
Handy CR — Clean-Room Offline Speech-to-Text Desktop Web App Reimplementation.

Built strictly from spec-anything artifacts:
  - 09_contracts/history.sql (SQLite transcription_history DDL, user_version=4)
  - 09_contracts/tauri_ipc.schema.json (settings, models, history, dictation contracts)
  - 11_ui/tokens.json (measured live CSS tokens & layout geometry)
  - 06_evidence/ledger.jsonl (observed runtime behaviors)

Zero upstream source code reused. Uses Python stdlib only (http.server + sqlite3)
and a distinct clean-room brand mark ("Handy CR"). Acoustic transcription is
implemented as a deterministic offline test double separated from real SQLite
persistence, settings storage, and dictation state-machine transitions.
"""
import argparse
import datetime
import http.server
import json
import pathlib
import re
import sqlite3
import threading
import time
import urllib.parse

BUNDLE_DIR = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_SQL = BUNDLE_DIR / "09_contracts" / "history.sql"

CURATED_MODELS = [
    {
        "id": "whisper-medium",
        "name": "Whisper Medium",
        "description": "Broadest language support, but may run a bit slow",
        "filename": "whisper-medium-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/whisper-medium-gguf", "revision": "ec78f06fde"}},
        "size_mb": 793,
        "size_label": "793 MB",
        "grade": "A\u2212",
        "grade_dark": True,
        "speed_bars": 2,
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
        "source": {"HuggingFace": {"repo_id": "handy-computer/parakeet-tdt-0.6b-v3-gguf", "revision": "85ac09ea12"}},
        "size_mb": 705,
        "size_label": "705 MB",
        "grade": "A\u2212",
        "grade_dark": True,
        "speed_bars": 4,
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
        "source": {"HuggingFace": {"repo_id": "handy-computer/parakeet-unified-en-0.6b-gguf", "revision": "7e948f21b7"}},
        "size_mb": 697,
        "size_label": "697 MB",
        "grade": "A\u2212",
        "grade_dark": True,
        "speed_bars": 4,
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
        "id": "parakeet-tdt-0.6b-v2",
        "name": "Parakeet TDT 0.6B v2",
        "description": "Excellent English only model, runs on any hardware",
        "filename": "parakeet-tdt-0.6b-v2-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/parakeet-tdt-0.6b-v2-gguf", "revision": "07cee06161"}},
        "size_mb": 696,
        "size_label": "696 MB",
        "grade": "A\u2212",
        "grade_dark": True,
        "speed_bars": 4,
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
        "source": {"HuggingFace": {"repo_id": "handy-computer/cohere-transcribe-03-2026-gguf", "revision": "dfa4adebb6"}},
        "size_mb": 2299,
        "size_label": "2.2 GB",
        "grade": "B+",
        "grade_dark": False,
        "speed_bars": 3,
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
    {
        "id": "canary-180m-flash",
        "name": "Canary 180M Flash",
        "description": "Tiny, fast, and runs well on any hardware",
        "filename": "canary-180m-flash-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/canary-180m-flash-gguf", "revision": "46b86384d1"}},
        "size_mb": 208,
        "size_label": "208 MB",
        "grade": "B+",
        "grade_dark": False,
        "speed_bars": 4,
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
        "id": "nemotron-3.5-asr-streaming-0.6b",
        "name": "Nemotron Streaming 3.5",
        "description": "Fast and accurate transcription in many European languages",
        "filename": "nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf",
        "source": {"HuggingFace": {"repo_id": "handy-computer/nemotron-3.5-asr-streaming-0.6b-gguf", "revision": "6d44e540bc"}},
        "size_mb": 716,
        "size_label": "716 MB",
        "grade": "B",
        "grade_dark": False,
        "speed_bars": 4,
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
]

DEFAULT_MICROPHONES = [
    {"index": "default", "name": "MacBook Pro Microphone", "is_default": True},
    {"index": "usb-1", "name": "USB Studio Condenser", "is_default": False},
]

DEFAULT_OUTPUTS = [
    {"index": "default", "name": "MacBook Pro Speakers", "is_default": True},
    {"index": "hp-1", "name": "External Headphones", "is_default": False},
]

SEED_HISTORY = [
    (
        "handy-1795442400.wav",
        1795442400,
        0,
        "November 23, 2026 at 02:00 PM",
        "Ship the offline dictation benchmark and confirm local SQLite persistence.",
        None,
        None,
        0,
        None,
        "en",
        "selected",
    ),
    (
        "handy-1795446000.wav",
        1795446000,
        1,
        "November 23, 2026 at 03:00 PM",
        "Remember to verify the macOS arm64 codesign ticket and notarization status.",
        None,
        None,
        0,
        None,
        "en",
        "model",
    ),
    (
        "handy-1795449600.wav",
        1795449600,
        0,
        "November 23, 2026 at 04:00 PM",
        "Switch active model from Whisper Medium to Parakeet TDT for faster local inference.",
        None,
        None,
        0,
        None,
        "en",
        "detected",
    ),
]


def default_settings() -> dict:
    return {
        "settings_schema_version": 3,
        "bindings": {
            "transcribe": {
                "id": "transcribe",
                "name": "Transcribe",
                "description": "Converts your speech into text.",
                "default_binding": "option+space",
                "current_binding": "option+space",
            },
            "cancel": {
                "id": "cancel",
                "name": "Cancel",
                "description": "Cancels the current recording.",
                "default_binding": "escape",
                "current_binding": "escape",
            },
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
        "custom_words": ["Handy", "Parakeet"],
        "model_unload_timeout": "min_5",
        "history_limit": 5,
        "recording_retention_period": "preserve_limit",
        "paste_method": "ctrl_v",
        "clipboard_handling": "dont_modify",
        "auto_submit": False,
        "mute_while_recording": False,
        "append_trailing_space": True,
        "app_language": "en",
        "theme": "light",
        "experimental_enabled": False,
        "vad_enabled": True,
        "long_form_chunking": True,
        "filler_word_removal_enabled": False,
        "show_tray_icon": True,
    }


def format_utc_title(ts: int) -> str:
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    hour12 = dt.strftime("%I")
    return f"{dt.strftime('%B')} {dt.day}, {dt.year} at {hour12}:{dt.strftime('%M %p')}"


class CleanRoomStore:
    def __init__(self, data_dir: pathlib.Path, seed_demo: bool = True):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "history.db"
        self.settings_path = self.data_dir / "settings.json"
        self.lock = threading.RLock()
        self.models = json.loads(json.dumps(CURATED_MODELS))
        self.stage = "idle"
        self.is_recording = False
        self._init_db(seed_demo=seed_demo)
        self.settings = self._load_settings()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(self.db_path), check_same_thread=False)
        con.row_factory = sqlite3.Row
        return con

    def _init_db(self, seed_demo: bool):
        fresh = not self.db_path.exists()
        con = self._connect()
        try:
            if fresh:
                con.executescript(DEFAULT_SCHEMA_SQL.read_text(encoding="utf-8"))
                if seed_demo:
                    con.executemany(
                        """INSERT INTO transcription_history
                        (file_name, timestamp, saved, title, transcription_text,
                         post_processed_text, post_process_prompt, post_process_requested,
                         source_name, language, language_source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        SEED_HISTORY,
                    )
                con.commit()
        finally:
            con.close()

    def _load_settings(self) -> dict:
        if self.settings_path.exists():
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        s = default_settings()
        self._save_settings(s)
        return s

    def _save_settings(self, s: dict):
        self.settings_path.write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")

    def get_settings(self) -> dict:
        with self.lock:
            return json.loads(json.dumps(self.settings))

    def patch_settings(self, patch: dict) -> dict:
        with self.lock:
            if "shortcut_activation" in patch:
                if patch["shortcut_activation"] not in ("hold_or_toggle", "push_to_talk", "toggle"):
                    raise ValueError("Invalid shortcut_activation")
            if "theme" in patch and patch["theme"] not in ("system", "light", "dark"):
                raise ValueError("Invalid theme")
            for k, v in patch.items():
                if k in self.settings and k != "bindings":
                    self.settings[k] = v
            self._save_settings(self.settings)
            return json.loads(json.dumps(self.settings))

    def update_binding(self, bid: str, binding: str) -> dict:
        with self.lock:
            if bid not in self.settings["bindings"]:
                return {"success": False, "binding": None, "error": f"Unknown binding: {bid}"}
            self.settings["bindings"][bid]["current_binding"] = binding
            self._save_settings(self.settings)
            return {"success": True, "binding": dict(self.settings["bindings"][bid]), "error": None}

    def get_language_status(self, model_id: str | None = None) -> dict:
        with self.lock:
            lang = self.settings["selected_language"]
            if lang == "auto":
                return {"kind": "auto"}
            return {"kind": "selected", "language": lang}

    def get_models(self) -> list:
        with self.lock:
            return json.loads(json.dumps(self.models))

    def get_active_model(self) -> str:
        with self.lock:
            return self.settings["selected_model"]

    def set_active_model(self, model_id: str) -> dict:
        with self.lock:
            match = next((m for m in self.models if m["id"] == model_id), None)
            if match is None or not match["is_downloaded"]:
                raise ValueError(f"Model not downloaded or unknown: {model_id}")
            self.settings["selected_model"] = model_id
            self._save_settings(self.settings)
            return {
                "current_model": model_id,
                "is_loaded": True,
                "events": [
                    {"event": "model-state-changed", "payload": {"event_type": "loading_started", "model_id": model_id}},
                    {"event": "model-state-changed", "payload": {"event_type": "loading_completed", "model_id": model_id}},
                ],
            }

    @staticmethod
    def _row_to_entry(r: sqlite3.Row) -> dict:
        return {
            "id": r["id"],
            "file_name": r["file_name"],
            "timestamp": r["timestamp"],
            "saved": bool(r["saved"]),
            "title": r["title"],
            "transcription_text": r["transcription_text"],
            "post_processed_text": r["post_processed_text"],
            "post_process_prompt": r["post_process_prompt"],
            "post_process_requested": bool(r["post_process_requested"]),
            "source_name": r["source_name"],
            "language": r["language"],
            "language_source": r["language_source"],
        }

    def get_history(self, cursor: int | None, limit: int | None) -> dict:
        with self.lock:
            con = self._connect()
            try:
                lim = min(int(limit), 100) if limit is not None else None
                if cursor is not None and lim is not None:
                    rows = con.execute(
                        "SELECT * FROM transcription_history WHERE id < ? ORDER BY id DESC LIMIT ?",
                        (cursor, lim + 1),
                    ).fetchall()
                elif lim is not None:
                    rows = con.execute(
                        "SELECT * FROM transcription_history ORDER BY id DESC LIMIT ?",
                        (lim + 1,),
                    ).fetchall()
                else:
                    rows = con.execute(
                        "SELECT * FROM transcription_history ORDER BY id DESC"
                    ).fetchall()
                has_more = lim is not None and len(rows) > lim
                if has_more:
                    rows = rows[:lim]
                return {"entries": [self._row_to_entry(r) for r in rows], "has_more": has_more}
            finally:
                con.close()

    def toggle_history_saved(self, entry_id: int) -> dict:
        with self.lock:
            con = self._connect()
            try:
                row = con.execute("SELECT saved FROM transcription_history WHERE id = ?", (entry_id,)).fetchone()
                if row is None:
                    raise KeyError(f"History entry {entry_id} not found")
                new_val = 0 if row["saved"] else 1
                con.execute("UPDATE transcription_history SET saved = ? WHERE id = ?", (new_val, entry_id))
                con.commit()
                return {"id": entry_id, "saved": bool(new_val)}
            finally:
                con.close()

    def delete_history(self, entry_id: int) -> dict:
        with self.lock:
            con = self._connect()
            try:
                cur = con.execute("DELETE FROM transcription_history WHERE id = ?", (entry_id,))
                con.commit()
                if cur.rowcount == 0:
                    raise KeyError(f"History entry {entry_id} not found")
                return {"deleted_id": entry_id}
            finally:
                con.close()

    def dictate(self, audio_label: str, transcript_seed: str | None) -> dict:
        """Deterministic offline STT pipeline state machine + real SQLite persistence."""
        with self.lock:
            phases = ["idle", "recording", "transcribing", "completed"]
            self.stage = "recording"
            self.is_recording = True
            text = (transcript_seed or f"Transcribed audio sample: {audio_label}").strip()
            self.stage = "transcribing"
            self.is_recording = False
            ts = int(time.time())
            lang = self.settings["selected_language"]
            lang_val = "en" if lang == "auto" else lang
            lang_src = "detected" if lang == "auto" else "selected"
            file_name = f"handy-{ts}.wav"
            title = format_utc_title(ts)
            con = self._connect()
            try:
                cur = con.execute(
                    """INSERT INTO transcription_history
                    (file_name, timestamp, saved, title, transcription_text,
                     post_processed_text, post_process_prompt, post_process_requested,
                     source_name, language, language_source)
                    VALUES (?, ?, 0, ?, ?, NULL, NULL, 0, NULL, ?, ?)""",
                    (file_name, ts, title, text, lang_val, lang_src),
                )
                con.commit()
                row = con.execute("SELECT * FROM transcription_history WHERE id = ?", (cur.lastrowid,)).fetchone()
                entry = self._row_to_entry(row)
            finally:
                con.close()
            self.stage = "idle"
            return {
                "phases": phases,
                "outcome": "typed",
                "entry": entry,
                "persisted_to_sqlite": True,
                "events": [
                    {"event": "recording-state-event", "payload": {"phase": "started"}},
                    {"event": "recording-state-event", "payload": {"phase": "stopped"}},
                    {"event": "stream-phase-event", "payload": {"phase": "working", "kind": "transcribing"}},
                    {"event": "transcription-complete-event", "payload": {"outcome": "typed"}},
                    {"event": "history-update-payload", "payload": {"action": "added"}},
                ],
            }

    def cancel_dictation(self) -> dict:
        with self.lock:
            self.stage = "recording"
            self.is_recording = True
            self.stage = "idle"
            self.is_recording = False
            return {
                "phases": ["recording", "cancelled", "idle"],
                "is_recording_after": False,
                "history_rows_delta": 0,
                "events": [
                    {"event": "recording-state-event", "payload": {"phase": "started"}},
                    {"event": "recording-state-event", "payload": {"phase": "cancelled"}},
                ],
            }

    def db_schema_info(self) -> dict:
        with self.lock:
            con = self._connect()
            try:
                uv = con.execute("PRAGMA user_version").fetchone()[0]
                cols = [r["name"] for r in con.execute("PRAGMA table_info('transcription_history')").fetchall()]
                cnt = con.execute("SELECT COUNT(*) FROM transcription_history").fetchone()[0]
                return {"user_version": uv, "columns": cols, "row_count": cnt}
            finally:
                con.close()


INDEX_HTML = r"""<!doctype html>
<html lang="en" data-theme="light">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Handy CR</title>
<style>
:root {
  font-size: 15px;
  line-height: 24px;
  font-weight: 400;
  --color-text: #0f0f0f;
  --color-background: #fbfbfb;
  --color-background-ui: #da5893;
  --color-logo-primary: #faa2ca;
  --color-warning: #d97706;
  --color-error: #dc2626;
  --color-moss: #2f7d5b;
  --color-plum: #382731;
  --color-ink-2: rgba(15, 15, 15, 0.6);
  --color-ink-3: #808080;
  --color-line: rgba(128, 128, 128, 0.2);
  --color-line-strong: rgba(128, 128, 128, 0.8);
  --color-wash: rgba(128, 128, 128, 0.1);
  --font-ui: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: var(--color-text);
  background: var(--color-background);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  width: 100%;
  height: 100%;
  font-family: var(--font-ui);
  font-size: 15px;
  line-height: 24px;
  color: var(--color-text);
  background: var(--color-background);
  -webkit-font-smoothing: antialiased;
  user-select: none;
}
.app-shell {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.app-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.sidebar {
  width: 150px;
  height: 100%;
  border-right: 1px solid var(--color-line);
  padding: 0 7.5px;
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
}
.brand-box {
  width: 120px;
  height: 41px;
  margin: 15px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}
.brand-text {
  font-weight: 800;
  font-size: 21px;
  letter-spacing: -0.04em;
  color: var(--color-logo-primary);
  -webkit-text-stroke: 1.5px var(--color-plum);
  paint-order: stroke fill;
  line-height: 1;
}
.brand-tag {
  font-size: 9px;
  font-weight: 700;
  color: var(--color-plum);
  border: 1.5px solid var(--color-plum);
  border-radius: 4px;
  padding: 1px 3px;
  line-height: 1;
  background: rgba(250, 162, 202, 0.35);
}
.sidebar-nav {
  width: 100%;
  border-top: 1px solid var(--color-line);
  padding-top: 7.5px;
  display: flex;
  flex-direction: column;
  gap: 3.75px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 7.5px;
  height: 39px;
  padding: 7.5px;
  width: 100%;
  border-radius: 7.5px;
  cursor: pointer;
  color: var(--color-text);
  opacity: 0.85;
  font-size: 13.125px;
  font-weight: 500;
  border: none;
  background: transparent;
  text-align: left;
  font-family: inherit;
}
.nav-item:hover { background: var(--color-line); opacity: 1; }
.nav-item.active {
  background: rgba(250, 162, 202, 0.8);
  opacity: 1;
}
.nav-item svg { width: 22px; height: 22px; flex-shrink: 0; }
.content-wrap {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 15px;
}
.content-col {
  width: 100%;
  max-width: 720px;
  display: flex;
  flex-direction: column;
  gap: 22.5px;
}
.content-col.models-col {
  height: 100%;
  gap: 0;
}
.group-block { display: flex; flex-direction: column; gap: 7.5px; }
.group-header {
  padding: 0 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.group-title {
  font-size: 11.25px;
  font-weight: 500;
  line-height: 15px;
  color: var(--color-ink-3);
  text-transform: uppercase;
  letter-spacing: 0.025em;
}
.card {
  background: var(--color-background);
  border: 1px solid var(--color-line);
  border-radius: 7.5px;
}
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 45px;
  padding: 7.5px 15px;
  border-bottom: 1px solid var(--color-line);
}
.setting-row:last-child { border-bottom: none; }
.setting-label {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 13.125px;
  font-weight: 500;
}
.info-dot {
  width: 13px;
  height: 13px;
  border-radius: 999px;
  border: 1px solid var(--color-ink-3);
  color: var(--color-ink-3);
  font-size: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-style: normal;
  line-height: 1;
}
.ctrl-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.keycap {
  font-size: 13px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid rgba(128,128,128,0.45);
  background: rgba(128,128,128,0.08);
  color: var(--color-text);
  line-height: 18px;
}
.reset-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  opacity: 0.75;
}
.select-box {
  min-width: 195px;
  height: 30px;
  padding: 0 28px 0 10px;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  color: var(--color-text);
  background: rgba(128,128,128,0.08);
  border: 1px solid rgba(128,128,128,0.45);
  border-radius: 6px;
  appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, #333 50%), linear-gradient(135deg, #333 50%, transparent 50%);
  background-position: calc(100% - 14px) 12px, calc(100% - 9px) 12px;
  background-size: 5px 5px, 5px 5px;
  background-repeat: no-repeat;
  cursor: pointer;
}
.lang-chip {
  font-size: 12.5px;
  font-weight: 500;
  padding: 2px 9px;
  border-radius: 6px;
  background: rgba(128,128,128,0.1);
  color: var(--color-text);
}
.toggle-btn {
  width: 40px;
  height: 22px;
  border-radius: 999px;
  border: 1px solid rgba(128,128,128,0.35);
  background: rgba(128,128,128,0.16);
  position: relative;
  cursor: pointer;
  transition: background 0.15s;
}
.toggle-btn.on {
  background: var(--color-background-ui);
  border-color: var(--color-background-ui);
}
.toggle-knob {
  width: 16px;
  height: 16px;
  border-radius: 999px;
  background: #fff;
  position: absolute;
  top: 2px;
  left: 2px;
  transition: transform 0.15s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.2);
}
.toggle-btn.on .toggle-knob { transform: translateX(18px); }
.vol-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}
.vol-track {
  width: 125px;
  height: 6px;
  border-radius: 999px;
  background: linear-gradient(to right, var(--color-background-ui) 0%, var(--color-background-ui) 50%, rgba(128,128,128,0.2) 50%);
  position: relative;
}
.vol-thumb {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  background: #1a73e8;
  position: absolute;
  top: -4px;
  left: calc(50% - 7px);
}
.vol-pct { font-size: 13px; color: var(--color-text); min-width: 32px; text-align: right; }

/* Models Page */
.models-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 12px;
  margin-bottom: 16px;
}
.models-title { font-size: 18.75px; font-weight: 600; }
.link-btn {
  border: none;
  background: transparent;
  font-size: 13.125px;
  color: var(--color-text);
  text-decoration: underline;
  text-underline-offset: 3px;
  text-decoration-color: var(--color-line-strong);
  cursor: pointer;
}
.models-panel {
  flex: 1;
  border: 1px solid var(--color-line);
  border-radius: 16px;
  background: var(--color-background);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.models-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid var(--color-line);
  gap: 12px;
}
.search-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-ink-3);
}
.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text);
}
.toolbar-filters {
  display: flex;
  align-items: center;
  gap: 14px;
  border-left: 1px solid var(--color-line);
  padding-left: 14px;
  font-size: 12.5px;
  color: var(--color-ink-2);
}
.models-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px 10px 10px 10px;
}
.models-sec-head {
  display: grid;
  grid-template-columns: 1fr 48px 58px 66px 28px;
  align-items: center;
  padding: 2px 14px 4px 38px;
  font-size: 11px;
  font-weight: 500;
  color: var(--color-ink-3);
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.models-sec-head span:nth-child(n+2) { text-align: center; }
.model-row {
  display: grid;
  grid-template-columns: 28px 1fr 48px 58px 66px 28px;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border-radius: 10px;
  cursor: pointer;
}
.model-row:hover { background: var(--color-wash); }
.model-row.active { background: rgba(128, 128, 128, 0.14); }
.model-radio {
  width: 19px;
  height: 19px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.model-radio.active { background: var(--color-background-ui); color: #fff; }
.model-radio.ready { border: 1.5px solid var(--color-ink-3); }
.model-radio.remote { border: 1.5px dashed var(--color-ink-3); color: var(--color-ink-3); font-size: 11px; }
.model-name-line { display: flex; align-items: center; gap: 6px; font-size: 13.5px; font-weight: 600; }
.model-desc { font-size: 12.5px; color: var(--color-ink-3); line-height: 18px; }
.rec-pill {
  font-size: 11px;
  font-weight: 500;
  padding: 1px 7px;
  border-radius: 999px;
  border: 1px solid var(--color-line-strong);
  color: var(--color-ink-2);
}
.grade-chip {
  justify-self: center;
  min-width: 28px;
  height: 22px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(128,128,128,0.16);
  color: var(--color-text);
}
.grade-chip.dark { background: #141414; color: #fff; }
.speed-bars {
  justify-self: center;
  display: inline-flex;
  align-items: flex-end;
  gap: 2px;
  height: 13px;
}
.sbar { width: 3px; border-radius: 1px; background: rgba(128,128,128,0.28); }
.sbar.on { background: #4a4a4a; }
.size-col { text-align: center; font-size: 12px; color: var(--color-ink-3); font-variant-numeric: tabular-nums; }
.models-divider { height: 1px; background: var(--color-line); margin: 10px 0 8px 0; }

/* History Page */
.header-btns { display: flex; align-items: center; gap: 8px; }
.hdr-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 7px;
  border: 1px solid rgba(128,128,128,0.35);
  background: rgba(128,128,128,0.08);
  color: var(--color-text);
  cursor: pointer;
  font-family: inherit;
}
.hist-row {
  padding: 10px 15px 18px 15px;
  border-bottom: 1px solid var(--color-line);
  display: flex;
  flex-direction: column;
  gap: 11px;
}
.hist-row:last-child { border-bottom: none; }
.hist-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.hist-date { font-size: 13.125px; font-weight: 500; }
.hist-actions { display: flex; align-items: center; gap: 2px; }
.icon-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--color-ink-3);
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.icon-btn:hover { color: var(--color-logo-primary); }
.icon-btn.starred { color: var(--color-logo-primary); }
.hist-text {
  font-size: 13.125px;
  font-style: italic;
  color: var(--color-text);
  user-select: text;
}
.audio-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11.5px;
  color: var(--color-ink-3);
}
.audio-track {
  flex: 1;
  height: 4px;
  border-radius: 999px;
  background: rgba(128,128,128,0.22);
  position: relative;
}
.audio-dot {
  width: 13px;
  height: 13px;
  border-radius: 999px;
  background: #1a73e8;
  position: absolute;
  top: -4.5px;
  left: 0;
}

/* Footer */
.footer {
  width: 100%;
  height: 39px;
  border-top: 1px solid var(--color-line);
  padding: 0 15px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.25px;
  color: var(--color-ink-2);
  flex-shrink: 0;
}
.footer-left { display: flex; align-items: center; gap: 7px; }
.status-dot { width: 7px; height: 7px; border-radius: 999px; background: var(--color-moss); }
.footer-right { display: flex; align-items: center; gap: 5px; }
</style>
</head>
<body>
<div class="app-shell">
  <div class="app-body">
    <aside class="sidebar" id="sidebar">
      <div class="brand-box" title="Handy CR Clean-Room">
        <span class="brand-text">handy</span>
        <span class="brand-tag">CR</span>
      </div>
      <nav class="sidebar-nav" id="sidebar-nav"></nav>
    </aside>
    <main class="content-wrap">
      <div class="content-col" id="main-content"></div>
    </main>
  </div>
  <footer class="footer" id="footer">
    <div class="footer-left">
      <span class="status-dot"></span>
      <span id="footer-model">Whisper Medium</span>
      <span style="opacity:0.7">&#8964;</span>
    </div>
    <div class="footer-right">
      <span>Update Checking Disabled</span>
      <span>&bull;</span>
      <span>v0.10.2</span>
    </div>
  </footer>
</div>
<script>
const state = {
  section: "general",
  settings: null,
  models: [],
  history: [],
  searchQuery: "",
};

const NAV_ITEMS = [
  { id: "general", label: "General", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="8"/><path d="M12 8v8M8 12h8"/></svg>' },
  { id: "history", label: "History", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/></svg>' },
  { id: "models", label: "Models", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/></svg>' },
  { id: "advanced", label: "Advanced", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1L7 17M17 7l2.1-2.1"/></svg>' },
  { id: "about", label: "About", icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/></svg>' },
];

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function formatBinding(raw) {
  return raw.split("+").map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join(" + ");
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function renderSidebar() {
  const nav = document.getElementById("sidebar-nav");
  nav.innerHTML = NAV_ITEMS.map((item) => `
    <button type="button" class="nav-item ${state.section === item.id ? "active" : ""}" data-section="${item.id}">
      ${item.icon}
      <span>${item.label}</span>
    </button>
  `).join("");
  nav.querySelectorAll(".nav-item").forEach((btn) => {
    btn.onclick = async () => {
      state.section = btn.dataset.section;
      if (state.section === "history") await loadHistory();
      if (state.section === "models") await loadModels();
      render();
    };
  });
}

function renderFooter() {
  const cur = state.models.find((m) => m.id === state.settings?.selected_model);
  document.getElementById("footer-model").textContent = cur ? cur.name : (state.settings?.selected_model || "No Model");
}

function renderGeneral() {
  const s = state.settings;
  const cur = state.models.find((m) => m.id === s.selected_model);
  const modelHeading = (cur ? cur.name : s.selected_model).toUpperCase() + " SETTINGS";
  const transBind = formatBinding(s.bindings.transcribe.current_binding);
  const cancelBind = formatBinding(s.bindings.cancel.current_binding);
  const resetSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 1 1-2.6-6.3"/><path d="M21 3v6h-6"/></svg>';

  return `
    <div class="group-block">
      <div class="group-header"><h2 class="group-title">GENERAL</h2></div>
      <div class="card">
        <div class="setting-row">
          <div class="setting-label">Transcribe Shortcut <i class="info-dot">i</i></div>
          <div class="ctrl-row">
            <span class="keycap" id="transcribe-keycap">${escapeHtml(transBind)}</span>
            <button class="reset-btn" title="Reset">${resetSvg}</button>
          </div>
        </div>
        <div class="setting-row">
          <div class="setting-label">Shortcut Behavior <i class="info-dot">i</i></div>
          <select class="select-box" id="shortcut-activation-select">
            <option value="hold_or_toggle" ${s.shortcut_activation === "hold_or_toggle" ? "selected" : ""}>Auto</option>
            <option value="push_to_talk" ${s.shortcut_activation === "push_to_talk" ? "selected" : ""}>Push to Talk</option>
            <option value="toggle" ${s.shortcut_activation === "toggle" ? "selected" : ""}>Toggle</option>
          </select>
        </div>
        <div class="setting-row">
          <div class="setting-label">Cancel Shortcut <i class="info-dot">i</i></div>
          <div class="ctrl-row">
            <span class="keycap">${escapeHtml(cancelBind)}</span>
            <button class="reset-btn" title="Reset">${resetSvg}</button>
          </div>
        </div>
      </div>
    </div>
    <div class="group-block">
      <div class="group-header"><h2 class="group-title">LANGUAGES</h2></div>
      <div class="card">
        <div class="setting-row">
          <div class="setting-label">Preferred Languages <i class="info-dot">i</i></div>
          <div class="ctrl-row">
            <span class="lang-chip">English</span>
            <span style="color:var(--color-ink-3);font-size:15px">+</span>
          </div>
        </div>
      </div>
    </div>
    <div class="group-block">
      <div class="group-header"><h2 class="group-title">${escapeHtml(modelHeading)}</h2></div>
      <div class="card">
        <div class="setting-row">
          <div class="setting-label">Language <i class="info-dot">i</i></div>
          <div class="ctrl-row">
            <select class="select-box" id="selected-language-select">
              <option value="auto" ${s.selected_language === "auto" ? "selected" : ""}>Auto</option>
              <option value="en" ${s.selected_language === "en" ? "selected" : ""}>English</option>
              <option value="ko" ${s.selected_language === "ko" ? "selected" : ""}>Korean</option>
              <option value="es" ${s.selected_language === "es" ? "selected" : ""}>Spanish</option>
            </select>
            <button class="reset-btn" title="Reset">${resetSvg}</button>
          </div>
        </div>
        <div class="setting-row">
          <div class="setting-label">Translate to English <i class="info-dot">i</i></div>
          <button type="button" class="toggle-btn ${s.translate_to_english ? "on" : ""}" id="toggle-translate"><span class="toggle-knob"></span></button>
        </div>
      </div>
    </div>
    <div class="group-block">
      <div class="group-header"><h2 class="group-title">SOUND</h2></div>
      <div class="card">
        <div class="setting-row">
          <div class="setting-label">Microphone <i class="info-dot">i</i></div>
          <div class="ctrl-row">
            <select class="select-box" id="mic-select">
              <option value="MacBook Pro Microphone" ${s.selected_microphone === "MacBook Pro Microphone" ? "selected" : ""}>MacBook Pro Microphone</option>
              <option value="USB Studio Condenser" ${s.selected_microphone === "USB Studio Condenser" ? "selected" : ""}>USB Studio Condenser</option>
            </select>
            <button class="reset-btn" title="Reset">${resetSvg}</button>
          </div>
        </div>
        <div class="setting-row">
          <div class="setting-label">Mute While Recording <i class="info-dot">i</i></div>
          <button type="button" class="toggle-btn ${s.mute_while_recording ? "on" : ""}" id="toggle-mute"><span class="toggle-knob"></span></button>
        </div>
        <div class="setting-row">
          <div class="setting-label">Audio Feedback <i class="info-dot">i</i></div>
          <button type="button" class="toggle-btn ${s.audio_feedback ? "on" : ""}" id="toggle-feedback"><span class="toggle-knob"></span></button>
        </div>
        <div class="setting-row">
          <div class="setting-label">Output Device <i class="info-dot">i</i></div>
          <div class="ctrl-row">
            <select class="select-box">
              <option>MacBook Pro Speakers</option>
              <option>External Headphones</option>
            </select>
            <button class="reset-btn" title="Reset">${resetSvg}</button>
          </div>
        </div>
        <div class="setting-row">
          <div class="setting-label">Volume <i class="info-dot">i</i></div>
          <div class="vol-wrap">
            <div class="vol-track"><div class="vol-thumb"></div></div>
            <span class="vol-pct">${Math.round((s.audio_feedback_volume || 0.5) * 100)}%</span>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderSpeedBars(n) {
  const heights = [4, 7, 10, 13];
  return `<div class="speed-bars">${heights.map((h, i) => `<span class="sbar ${i < n ? "on" : ""}" style="height:${h}px"></span>`).join("")}</div>`;
}

function renderModels() {
  const curId = state.settings.selected_model;
  const q = state.searchQuery.trim().toLowerCase();
  const filterFn = (m) => !q || m.name.toLowerCase().includes(q) || m.description.toLowerCase().includes(q);
  const yours = state.models.filter((m) => m.is_downloaded && filterFn(m));
  const fits = state.models.filter((m) => !m.is_downloaded && filterFn(m));
  const trashSvg = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>';

  const rowHtml = (m) => {
    const isAct = m.id === curId;
    const radio = isAct
      ? '<span class="model-radio active">&#10003;</span>'
      : m.is_downloaded
        ? '<span class="model-radio ready"></span>'
        : '<span class="model-radio remote">&#8595;</span>';
    const rec = (!m.is_downloaded && m.is_recommended) ? '<span class="rec-pill">Recommended</span>' : '';
    return `
      <div class="model-row ${isAct ? "active" : ""}" data-model-id="${escapeHtml(m.id)}" data-downloaded="${m.is_downloaded}">
        ${radio}
        <div>
          <div class="model-name-line"><span>${escapeHtml(m.name)}</span>${rec}</div>
          <div class="model-desc">${escapeHtml(m.description)}</div>
        </div>
        <span class="grade-chip ${m.grade_dark ? "dark" : ""}">${escapeHtml(m.grade || "A\u2212")}</span>
        ${renderSpeedBars(m.speed_bars || 3)}
        <span class="size-col">${escapeHtml(m.size_label || (m.size_mb + " MB"))}</span>
        <span style="justify-self:center;color:var(--color-ink-3);opacity:0.5">${m.is_downloaded ? trashSvg : ""}</span>
      </div>
    `;
  };

  return `
    <div class="models-top">
      <h1 class="models-title">Models</h1>
      <button class="link-btn" id="change-langs-link">Change languages</button>
    </div>
    <div class="models-panel">
      <div class="models-toolbar">
        <div class="search-wrap">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
          <input class="search-input" id="model-search-input" placeholder="Search models" value="${escapeHtml(state.searchQuery)}" />
        </div>
        <div class="toolbar-filters">
          <span>Live preview</span>
          <span>Translates</span>
        </div>
      </div>
      <div class="models-list">
        <div class="models-sec-head">
          <span>ON THIS COMPUTER</span>
          <span>EN</span>
          <span>SPEED</span>
          <span>SIZE</span>
          <span>?</span>
        </div>
        ${yours.map(rowHtml).join("")}
        <div class="models-divider"></div>
        <div class="models-sec-head">
          <span>FOR YOUR LANGUAGES</span>
          <span></span><span></span><span></span><span></span>
        </div>
        ${fits.map(rowHtml).join("")}
      </div>
    </div>
  `;
}

function renderHistory() {
  const copySvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>';
  const starSvg = (filled) => `<svg width="15" height="15" viewBox="0 0 24 24" fill="${filled ? "currentColor" : "none"}" stroke="currentColor" stroke-width="1.8"><polygon points="12 2 15.1 8.3 22 9.3 17 14.1 18.2 21 12 17.8 5.8 21 7 14.1 2 9.3 8.9 8.3 12 2"/></svg>`;
  const retrySvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/></svg>';
  const delSvg = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6"/></svg>';

  const rows = state.history.length
    ? state.history.map((e) => `
      <div class="hist-row" data-entry-id="${e.id}">
        <div class="hist-top">
          <p class="hist-date">${escapeHtml(e.title)}</p>
          <div class="hist-actions">
            <button type="button" class="icon-btn" title="Copy to clipboard">${copySvg}</button>
            <button type="button" class="icon-btn star-btn ${e.saved ? "starred" : ""}" data-id="${e.id}" title="${e.saved ? "Remove from saved" : "Save to history"}">${starSvg(e.saved)}</button>
            <button type="button" class="icon-btn" title="Re-transcribe">${retrySvg}</button>
            <button type="button" class="icon-btn del-btn" data-id="${e.id}" title="Delete">${delSvg}</button>
          </div>
        </div>
        <p class="hist-text">${escapeHtml(e.transcription_text)}</p>
        <div class="audio-bar">
          <span style="color:var(--color-text);font-size:13px">&#9654;</span>
          <span>0:00</span>
          <div class="audio-track"><div class="audio-dot"></div></div>
          <span>0:00</span>
        </div>
      </div>
    `).join("")
    : `<div style="padding:16px;text-align:center;color:var(--color-ink-2)">No transcriptions yet.</div>`;

  return `
    <div class="group-block">
      <div class="group-header">
        <h2 class="group-title">HISTORY</h2>
        <div class="header-btns">
          <button type="button" class="hdr-btn">Transcribe File</button>
          <button type="button" class="hdr-btn">Open Recordings Folder</button>
        </div>
      </div>
      <div class="card">${rows}</div>
    </div>
  `;
}

function renderAdvanced() {
  const s = state.settings;
  return `
    <div class="group-block">
      <div class="group-header"><h2 class="group-title">APP</h2></div>
      <div class="card">
        <div class="setting-row"><div class="setting-label">Start Hidden <i class="info-dot">i</i></div><button type="button" class="toggle-btn ${s.start_hidden ? "on" : ""}"><span class="toggle-knob"></span></button></div>
        <div class="setting-row"><div class="setting-label">Launch on Startup <i class="info-dot">i</i></div><button type="button" class="toggle-btn ${s.autostart_enabled ? "on" : ""}"><span class="toggle-knob"></span></button></div>
        <div class="setting-row"><div class="setting-label">Show Tray Icon <i class="info-dot">i</i></div><button type="button" class="toggle-btn ${s.show_tray_icon ? "on" : ""}"><span class="toggle-knob"></span></button></div>
        <div class="setting-row"><div class="setting-label">Overlay <i class="info-dot">i</i></div><select class="select-box"><option>Live</option><option>Minimal</option><option>None</option></select></div>
        <div class="setting-row"><div class="setting-label">Overlay Position <i class="info-dot">i</i></div><select class="select-box"><option>Bottom</option><option>Top</option></select></div>
        <div class="setting-row"><div class="setting-label">Experimental Features <i class="info-dot">i</i></div><button type="button" class="toggle-btn ${s.experimental_enabled ? "on" : ""}"><span class="toggle-knob"></span></button></div>
      </div>
    </div>
    <div class="group-block">
      <div class="group-header"><h2 class="group-title">OUTPUT</h2></div>
      <div class="card">
        <div class="setting-row"><div class="setting-label">Paste Method <i class="info-dot">i</i></div><select class="select-box"><option>Clipboard (Cmd+V)</option><option>Direct</option></select></div>
        <div class="setting-row"><div class="setting-label">Clipboard Handling <i class="info-dot">i</i></div><select class="select-box"><option>Don't Modify Clipboard</option><option>Copy to Clipboard</option></select></div>
        <div class="setting-row"><div class="setting-label">Auto Submit <i class="info-dot">i</i></div><select class="select-box"><option>Off</option><option>Enter</option></select></div>
      </div>
    </div>
    <div class="group-block">
      <div class="group-header"><h2 class="group-title">TRANSCRIPTION</h2></div>
      <div class="card">
        <div class="setting-row"><div class="setting-label">Voice Activity Detection <i class="info-dot">i</i></div><button type="button" class="toggle-btn ${s.vad_enabled ? "on" : ""}"><span class="toggle-knob"></span></button></div>
        <div class="setting-row"><div class="setting-label">Long Audio Chunking <i class="info-dot">i</i></div><button type="button" class="toggle-btn ${s.long_form_chunking ? "on" : ""}"><span class="toggle-knob"></span></button></div>
      </div>
    </div>
  `;
}

function renderAbout() {
  return `
    <div class="group-block">
      <div class="group-header"><h2 class="group-title">ABOUT</h2></div>
      <div class="card">
        <div class="setting-row"><div class="setting-label">Product</div><span>Handy CR (Clean-Room Reimplementation)</span></div>
        <div class="setting-row"><div class="setting-label">Target Specification</div><span>v0.10.2</span></div>
        <div class="setting-row"><div class="setting-label">Application Theme</div><span>Light</span></div>
      </div>
    </div>
  `;
}

function bindEvents() {
  if (state.section === "general") {
    const act = document.getElementById("shortcut-activation-select");
    if (act) act.onchange = async () => { state.settings = await api("/api/settings", { method: "PATCH", body: JSON.stringify({ shortcut_activation: act.value }) }); render(); };
    const lang = document.getElementById("selected-language-select");
    if (lang) lang.onchange = async () => { state.settings = await api("/api/settings", { method: "PATCH", body: JSON.stringify({ selected_language: lang.value }) }); render(); };
    const fb = document.getElementById("toggle-feedback");
    if (fb) fb.onclick = async () => { state.settings = await api("/api/settings", { method: "PATCH", body: JSON.stringify({ audio_feedback: !state.settings.audio_feedback }) }); render(); };
  }
  if (state.section === "models") {
    const cl = document.getElementById("change-langs-link");
    if (cl) cl.onclick = () => { state.section = "general"; render(); };
    const inp = document.getElementById("model-search-input");
    if (inp) inp.oninput = () => { state.searchQuery = inp.value; render(); };
    document.querySelectorAll(".model-row").forEach((row) => {
      row.onclick = async () => {
        if (row.dataset.downloaded !== "true") return;
        await api("/api/models/active", { method: "POST", body: JSON.stringify({ model_id: row.dataset.modelId }) });
        state.settings = await api("/api/settings");
        render();
      };
    });
  }
  if (state.section === "history") {
    document.querySelectorAll(".star-btn").forEach((btn) => {
      btn.onclick = async () => {
        await api(`/api/history/${btn.dataset.id}/toggle-saved`, { method: "POST" });
        await loadHistory();
        render();
      };
    });
    document.querySelectorAll(".del-btn").forEach((btn) => {
      btn.onclick = async () => {
        await api(`/api/history/${btn.dataset.id}`, { method: "DELETE" });
        await loadHistory();
        render();
      };
    });
  }
}

function render() {
  renderSidebar();
  renderFooter();
  const main = document.getElementById("main-content");
  main.className = "content-col" + (state.section === "models" ? " models-col" : "");
  if (state.section === "general") main.innerHTML = renderGeneral();
  else if (state.section === "models") main.innerHTML = renderModels();
  else if (state.section === "history") main.innerHTML = renderHistory();
  else if (state.section === "advanced") main.innerHTML = renderAdvanced();
  else main.innerHTML = renderAbout();
  bindEvents();
}

async function loadModels() {
  const res = await api("/api/models");
  state.models = res.models;
}
async function loadHistory() {
  const res = await api("/api/history?limit=30");
  state.history = res.entries;
}
async function boot() {
  state.settings = await api("/api/settings");
  await Promise.all([loadModels(), loadHistory()]);
  render();
}
boot();
</script>
</body>
</html>
"""


def make_handler(store: CleanRoomStore):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def _send_json(self, status: int, obj: dict):
            raw = json.dumps(obj).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _send_html(self, html: str):
            raw = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> dict:
            n = int(self.headers.get("Content-Length", "0") or 0)
            if n == 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            p = parsed.path
            qs = urllib.parse.parse_qs(parsed.query)
            if p in ("/", "/index.html"):
                return self._send_html(INDEX_HTML)
            if p == "/api/health":
                return self._send_json(200, {"status": "ok", "product": "Handy CR", "spec_version": "0.10.2"})
            if p == "/api/settings":
                return self._send_json(200, store.get_settings())
            if p == "/api/audio/microphones":
                return self._send_json(200, {"microphones": DEFAULT_MICROPHONES, "outputs": DEFAULT_OUTPUTS})
            if p == "/api/language-status":
                mid = (qs.get("model_id") or [None])[0]
                return self._send_json(200, store.get_language_status(mid))
            if p == "/api/models":
                return self._send_json(200, {"models": store.get_models(), "active_model": store.get_active_model()})
            if p == "/api/models/active":
                return self._send_json(200, {"current_model": store.get_active_model(), "is_loaded": True})
            if p == "/api/history":
                cursor = int(qs["cursor"][0]) if "cursor" in qs and qs["cursor"][0] not in ("", "null") else None
                limit = int(qs["limit"][0]) if "limit" in qs and qs["limit"][0] not in ("", "null") else None
                return self._send_json(200, store.get_history(cursor, limit))
            if p == "/api/db/schema":
                return self._send_json(200, store.db_schema_info())
            return self._send_json(404, {"error": "Not found"})

        def do_PATCH(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/api/settings":
                try:
                    return self._send_json(200, store.patch_settings(self._read_json()))
                except ValueError as e:
                    return self._send_json(400, {"error": str(e)})
            return self._send_json(404, {"error": "Not found"})

        def do_POST(self):
            parsed = urllib.parse.urlparse(self.path)
            p = parsed.path
            if p == "/api/settings/binding":
                body = self._read_json()
                res = store.update_binding(body.get("id", ""), body.get("binding", ""))
                return self._send_json(200 if res["success"] else 400, res)
            if p == "/api/models/active":
                body = self._read_json()
                mid = body.get("model_id") or body.get("modelId") or ""
                try:
                    return self._send_json(200, store.set_active_model(mid))
                except ValueError as e:
                    return self._send_json(400, {"error": str(e)})
            if p == "/api/dictate":
                body = self._read_json()
                res = store.dictate(body.get("audio_label", "clip"), body.get("transcript_seed"))
                return self._send_json(201, res)
            if p == "/api/dictate/cancel":
                return self._send_json(200, store.cancel_dictation())
            m = re.match(r"^/api/history/(\d+)/toggle-saved$", p)
            if m:
                try:
                    return self._send_json(200, store.toggle_history_saved(int(m.group(1))))
                except KeyError as e:
                    return self._send_json(404, {"error": str(e)})
            return self._send_json(404, {"error": "Not found"})

        def do_DELETE(self):
            parsed = urllib.parse.urlparse(self.path)
            m = re.match(r"^/api/history/(\d+)$", parsed.path)
            if m:
                try:
                    return self._send_json(200, store.delete_history(int(m.group(1))))
                except KeyError as e:
                    return self._send_json(404, {"error": str(e)})
            return self._send_json(404, {"error": "Not found"})

    return Handler


def main():
    ap = argparse.ArgumentParser(description="Handy CR Clean-Room Server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=1430)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--no-seed", action="store_true")
    args = ap.parse_args()

    store = CleanRoomStore(pathlib.Path(args.data_dir), seed_demo=(not args.no_seed))
    srv = http.server.ThreadingHTTPServer((args.host, args.port), make_handler(store))
    print(f"Handy CR listening on http://{args.host}:{args.port} (db={store.db_path})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
