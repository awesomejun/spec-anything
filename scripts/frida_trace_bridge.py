#!/usr/bin/env python3
"""
Authorized Clean-Room Frida Dynamic Tracing Bridge for spec-anything.
1. Generates read-only Frida Gum JS observation hooks (SQLite C-API, ObjC UI/Storage,
   POSIX file/socket I/O, Desktop IPC) strictly for authorized functional parity.
2. Parses captured Frida JSONL event logs OR frida-itrace ITR2/ITRC binary traces
   (big-endian uint32 record framing per frida/frida-tools) into schema-valid
   06_evidence/ledger.jsonl records.
3. Supports --self-test without requiring a live Frida installation.

Non-goals: Never emits memory patches, anti-debug evasion, DRM/auth bypass, or exploit hooks.
"""
import argparse
import hashlib
import json
import pathlib
import platform
import struct
import sys
import tempfile


HOOK_TEMPLATES = {
    "sqlite": """// spec-anything read-only SQLite C-API observer (authorized functional parity only)
'use strict';
const target = Module.findExportByName(null, 'sqlite3_prepare_v2') || Module.findExportByName(null, 'sqlite3_prepare_v3');
if (target) {
  Interceptor.attach(target, {
    onEnter(args) {
      const sql = args[1].isNull() ? '' : args[1].readUtf8String();
      send({ kind: 'sqlite_prepare', sql, ts_ms: Date.now() });
    }
  });
}
""",
    "objc-storage": """// spec-anything read-only macOS ObjC NSUserDefaults/File observer (authorized parity only)
'use strict';
if (ObjC.available) {
  const NSUserDefaults = ObjC.classes.NSUserDefaults;
  if (NSUserDefaults && NSUserDefaults['- setObject:forKey:']) {
    Interceptor.attach(NSUserDefaults['- setObject:forKey:'].implementation, {
      onEnter(args) {
        const key = new ObjC.Object(args[3]).toString();
        send({ kind: 'user_defaults_write', key, ts_ms: Date.now() });
      }
    });
  }
}
""",
    "posix-io": """// spec-anything read-only POSIX open/rename observer (authorized storage layout tracing)
'use strict';
const openPtr = Module.findExportByName(null, 'open');
if (openPtr) {
  Interceptor.attach(openPtr, {
    onEnter(args) {
      const p = args[0].isNull() ? '' : args[0].readUtf8String();
      if (p && !p.startsWith('/System/') && !p.startsWith('/usr/lib/')) {
        send({ kind: 'posix_open', path: p, flags: args[1].toInt32(), ts_ms: Date.now() });
      }
    }
  });
}
""",
    "ipc": """// spec-anything read-only IPC message boundary observer (JSON-RPC / Tauri / Electron stdout)
'use strict';
const writePtr = Module.findExportByName(null, 'write');
if (writePtr) {
  Interceptor.attach(writePtr, {
    onEnter(args) {
      const fd = args[0].toInt32();
      const len = Math.min(args[2].toInt32(), 512);
      if ((fd === 1 || fd === 2) && len > 0) {
        const preview = args[1].readUtf8String(len);
        if (preview && preview.includes('{')) {
          send({ kind: 'ipc_stream_frame', fd, bytes: len, preview, ts_ms: Date.now() });
        }
      }
    }
  });
}
""",
}


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_itrace_binary(path: pathlib.Path) -> dict:
    """Parse frida-itrace ITR2/ITRC binary container (big-endian uint32 type=1 MESSAGE, type=2 CHUNK)."""
    raw = path.read_bytes()
    if len(raw) < 4:
        raise ValueError("itrace file shorter than 4-byte magic header")
    magic = raw[:4].decode("ascii", errors="replace")
    if magic not in ("ITR2", "ITRC"):
        raise ValueError(f"unsupported itrace magic: {magic!r} (expected ITR2 or ITRC)")

    pos = 4
    messages = []
    chunks = []
    lost_total = 0

    while pos + 4 <= len(raw):
        (rec_type,) = struct.unpack(">I", raw[pos:pos + 4])
        pos += 4
        if rec_type == 1:  # MESSAGE
            if pos + 4 > len(raw):
                raise ValueError("truncated MESSAGE length")
            (msg_len,) = struct.unpack(">I", raw[pos:pos + 4])
            pos += 4
            msg_bytes = raw[pos:pos + msg_len]
            pos += msg_len
            if pos + 4 > len(raw):
                raise ValueError("truncated MESSAGE data_size")
            (data_size,) = struct.unpack(">I", raw[pos:pos + 4])
            pos += 4
            pos += data_size
            payload = json.loads(msg_bytes.decode("utf-8"))
            if isinstance(payload, dict) and payload.get("type") == "itrace:lost":
                lost_total += int(payload.get("count", 0))
            messages.append({"payload": payload, "data_size": data_size})
        elif rec_type == 2:  # CHUNK
            if pos + 4 > len(raw):
                raise ValueError("truncated CHUNK size")
            (chunk_size,) = struct.unpack(">I", raw[pos:pos + 4])
            pos += 4
            chunk_bytes = raw[pos:pos + chunk_size]
            pos += chunk_size
            chunks.append({"size": chunk_size, "sha256": hashlib.sha256(chunk_bytes).hexdigest()[:16]})
        else:
            raise ValueError(f"unknown itrace record type: {rec_type}")

    return {
        "magic": magic,
        "message_count": len(messages),
        "chunk_count": len(chunks),
        "lost_records": lost_total,
        "messages": messages[:50],
        "chunks_summary": chunks[:50],
    }


def make_evidence_record(
    evidence_id: str,
    feature_id: str,
    category: str,
    source_location: str,
    artifact_sha256: str,
    observation_tool: str,
    precondition: dict,
    inp: dict,
    observed_output: dict,
    event_sequence: list,
    limitations: str,
) -> dict:
    return {
        "evidence_id": evidence_id,
        "feature_id": feature_id,
        "category": category,
        "source_location": source_location,
        "artifact_sha256": artifact_sha256,
        "observation_tool": observation_tool,
        "environment": f"{platform.system()} {platform.machine()} Python {platform.python_version()}",
        "precondition": precondition,
        "input": inp,
        "observed_output": observed_output,
        "event_sequence": event_sequence,
        "storage_effect": None,
        "screen_ids": [],
        "contract_ref": None,
        "state_transition_ref": None,
        "comparison_rules": {
            "exact_fields": list(observed_output.keys()),
            "ignored_fields": ["ts_ms"],
            "order_sensitive": True,
            "visual_max_diff_ratio": None,
        },
        "status": "observed",
        "limitations": limitations,
    }


def cmd_emit_hook(args) -> None:
    src = HOOK_TEMPLATES[args.profile]
    if args.out:
        out_path = pathlib.Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(src, encoding="utf-8")
        print(json.dumps({"status": "ok", "profile": args.profile, "out": str(out_path)}, indent=2))
    else:
        print(src)


def cmd_ingest_jsonl(args) -> None:
    in_path = pathlib.Path(args.input)
    events = [json.loads(ln) for ln in in_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    art_sha = args.artifact_sha256 or sha256_file(in_path)
    rec = make_evidence_record(
        evidence_id=args.evidence_id,
        feature_id=args.feature_id,
        category=args.category,
        source_location=args.source_location,
        artifact_sha256=art_sha,
        observation_tool="frida-gum-interceptor",
        precondition={"hook_profile": args.profile, "authorized_clean_room_only": True},
        inp={"trace_file": in_path.name, "event_count": len(events)},
        observed_output={
            "event_count": len(events),
            "event_kinds": sorted({str(e.get("kind", "unknown")) for e in events if isinstance(e, dict)}),
        },
        event_sequence=events[:100],
        limitations="Read-only dynamic observation captured via Frida Interceptor; scope limited to hooked symbols in the executed scenario.",
    )
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a" if args.append else "w", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "ok", "evidence_id": rec["evidence_id"], "events": len(events), "out": str(out_path)}, indent=2))


def cmd_ingest_itrace(args) -> None:
    in_path = pathlib.Path(args.input)
    parsed = parse_itrace_binary(in_path)
    art_sha = args.artifact_sha256 or sha256_file(in_path)
    rec = make_evidence_record(
        evidence_id=args.evidence_id,
        feature_id=args.feature_id,
        category="release_rea",
        source_location=args.source_location,
        artifact_sha256=art_sha,
        observation_tool="frida-itrace",
        precondition={"format_magic": parsed["magic"], "authorized_clean_room_only": True},
        inp={"itrace_file": in_path.name},
        observed_output={
            "magic": parsed["magic"],
            "message_count": parsed["message_count"],
            "chunk_count": parsed["chunk_count"],
            "lost_records": parsed["lost_records"],
        },
        event_sequence=[m["payload"] for m in parsed["messages"] if isinstance(m.get("payload"), dict)],
        limitations=(
            f"Parsed frida-itrace {parsed['magic']} container; lost_records={parsed['lost_records']}. "
            "Raw register blocks summarized by digest without re-executing target instructions."
        ),
    )
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a" if args.append else "w", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps({"status": "ok", "evidence_id": rec["evidence_id"], "parsed": parsed}, indent=2))


def cmd_self_test(_args) -> None:
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        # 1. Build synthetic ITR2 binary stream (MESSAGE start + CHUNK block + MESSAGE end)
        itr = tmp / "sample.itrace"
        m1 = json.dumps({"type": "itrace:start", "arch": "arm64"}).encode("utf-8")
        m2 = json.dumps({"type": "itrace:end", "reason": "range_complete"}).encode("utf-8")
        chunk = struct.pack("<QQ", 0x100004000, 0x100004040)
        blob = (
            b"ITR2"
            + struct.pack(">II", 1, len(m1)) + m1 + struct.pack(">I", 0)
            + struct.pack(">II", 2, len(chunk)) + chunk
            + struct.pack(">II", 1, len(m2)) + m2 + struct.pack(">I", 0)
        )
        itr.write_bytes(blob)
        parsed = parse_itrace_binary(itr)
        assert parsed["magic"] == "ITR2"
        assert parsed["message_count"] == 2
        assert parsed["chunk_count"] == 1
        assert parsed["lost_records"] == 0

        # 2. Validate generated JSONL record against repository evidence schema if available
        rec = make_evidence_record(
            evidence_id="EV-901",
            feature_id="F-001",
            category="release_rea",
            source_location="frida-itrace:sample.itrace",
            artifact_sha256=sha256_file(itr),
            observation_tool="frida-itrace",
            precondition={"self_test": True},
            inp={"itrace_file": itr.name},
            observed_output={
                "magic": parsed["magic"],
                "message_count": parsed["message_count"],
                "chunk_count": parsed["chunk_count"],
                "lost_records": parsed["lost_records"],
            },
            event_sequence=[m["payload"] for m in parsed["messages"]],
            limitations="Synthetic self-test trace for CI verification.",
        )
        schema_path = pathlib.Path(__file__).resolve().parent.parent / "schemas" / "evidence.schema.json"
        schema_checked = False
        if schema_path.exists():
            try:
                import jsonschema  # type: ignore
                jsonschema.validate(rec, json.loads(schema_path.read_text(encoding="utf-8")))
                schema_checked = True
            except ImportError:
                schema_checked = False

        print(json.dumps({
            "self_test": "PASS",
            "profiles_available": sorted(HOOK_TEMPLATES.keys()),
            "itrace_parsed": {
                "magic": parsed["magic"],
                "messages": parsed["message_count"],
                "chunks": parsed["chunk_count"],
            },
            "evidence_schema_validated": schema_checked,
        }, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description="Clean-room Frida tracing & evidence ledger bridge")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_emit = sub.add_parser("emit-hook", help="Generate a read-only Frida Gum JS observation hook")
    p_emit.add_argument("--profile", choices=sorted(HOOK_TEMPLATES.keys()), required=True)
    p_emit.add_argument("--out", help="Write JS hook to file (default: stdout)")
    p_emit.set_defaults(func=cmd_emit_hook)

    p_j = sub.add_parser("ingest-jsonl", help="Normalize Frida JSONL events into 06_evidence/ledger.jsonl")
    p_j.add_argument("--input", required=True)
    p_j.add_argument("--out", required=True)
    p_j.add_argument("--evidence-id", required=True)
    p_j.add_argument("--feature-id", required=True)
    p_j.add_argument("--category", default="persistence")
    p_j.add_argument("--profile", default="sqlite")
    p_j.add_argument("--source-location", default="frida:interceptor")
    p_j.add_argument("--artifact-sha256", default=None)
    p_j.add_argument("--append", action="store_true")
    p_j.set_defaults(func=cmd_ingest_jsonl)

    p_i = sub.add_parser("ingest-itrace", help="Parse frida-itrace ITR2/ITRC binary into 06_evidence/ledger.jsonl")
    p_i.add_argument("--input", required=True)
    p_i.add_argument("--out", required=True)
    p_i.add_argument("--evidence-id", required=True)
    p_i.add_argument("--feature-id", required=True)
    p_i.add_argument("--source-location", default="frida:itrace")
    p_i.add_argument("--artifact-sha256", default=None)
    p_i.add_argument("--append", action="store_true")
    p_i.set_defaults(func=cmd_ingest_itrace)

    p_t = sub.add_parser("self-test", help="Verify ITR2 parser and 06 evidence schema emission offline")
    p_t.set_defaults(func=cmd_self_test)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
