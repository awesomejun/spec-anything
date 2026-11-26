#!/usr/bin/env python3
"""
REA Release Artifact Inspector for spec-anything.
Inspects authorized official release binaries, archives, Mach-O executables,
Go build metadata, code signatures, and embedded frontend bundles, and compares
them deterministically against upstream checksums and source trees.
"""
import argparse
import hashlib
import json
import pathlib
import platform
import shutil
import subprocess
import zipfile


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(cmd: list) -> dict:
    if not shutil.which(cmd[0]):
        return {"available": False, "returncode": None, "stdout": "", "stderr": f"tool_not_found: {cmd[0]}"}
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return {"available": True, "returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def parse_checksums(path: pathlib.Path) -> dict:
    mapping = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and len(parts[0]) == 64:
            mapping[parts[1].lstrip("*")] = parts[0].lower()
    return mapping


def inspect_binary(bin_path: pathlib.Path, source_dir: pathlib.Path | None) -> dict:
    info = {
        "binary_path": bin_path.name,
        "size_bytes": bin_path.stat().st_size,
        "sha256": sha256_file(bin_path),
    }
    file_res = run_cmd(["file", "-b", str(bin_path)])
    info["file_type"] = file_res["stdout"]

    # Go build info (module path, exact Go version, vcs/build flags, dependencies)
    go_res = run_cmd(["go", "version", "-m", str(bin_path)])
    if go_res["available"] and go_res["returncode"] == 0:
        lines = go_res["stdout"].splitlines()
        go_meta = {"header": lines[0] if lines else "", "path": None, "mod": None, "build_flags": {}, "dep_count": 0, "top_deps": []}
        for ln in lines[1:]:
            parts = ln.strip().split("\t")
            if not parts:
                continue
            tag = parts[0]
            if tag == "path" and len(parts) >= 2:
                go_meta["path"] = parts[1]
            elif tag == "mod" and len(parts) >= 3:
                go_meta["mod"] = f"{parts[1]} {parts[2]}"
            elif tag == "build" and len(parts) >= 2:
                kv = parts[1].split("=", 1)
                go_meta["build_flags"][kv[0]] = kv[1] if len(kv) == 2 else ""
            elif tag == "dep" and len(parts) >= 3:
                go_meta["dep_count"] += 1
                if len(go_meta["top_deps"]) < 15:
                    go_meta["top_deps"].append(f"{parts[1]}@{parts[2]}")
        info["go_buildinfo"] = go_meta

    # macOS Mach-O dynamic libraries & code signature
    if platform.system() == "Darwin":
        otool_res = run_cmd(["otool", "-L", str(bin_path)])
        if otool_res["available"] and otool_res["returncode"] == 0:
            libs = [ln.strip().split(" (")[0] for ln in otool_res["stdout"].splitlines()[1:] if ln.strip()]
            info["linked_libraries"] = libs
        cs_res = run_cmd(["codesign", "-dv", "--verbose=2", str(bin_path)])
        cs_text = "\n".join(x for x in [cs_res["stdout"], cs_res["stderr"]] if x)
        info["codesign"] = {
            "signed": cs_res["returncode"] == 0,
            "summary_lines": [ln for ln in cs_text.splitlines() if any(k in ln for k in ("Identifier=", "Format=", "Signature=", "CDHash=", "Authority=", "not signed"))][:12],
        }

    # Probe embedded UI / API markers inside the binary vs source
    raw_bytes = bin_path.read_bytes()
    probes = [
        b"/api/health",
        b"/api/realtime",
        b"/api/collections",
        b"/api/backups",
        b"/api/settings",
        b"/api/logs",
        b"/_/",
        b"index.html",
        b"PocketBase",
    ]
    probe_hits = {p.decode("ascii"): (p in raw_bytes) for p in probes}
    info["embedded_string_probes"] = probe_hits

    # Source alignment checks
    alignment = {"status": "unverified", "checks": []}
    if source_dir and source_dir.exists():
        go_mod = source_dir / "go.mod"
        if go_mod.exists() and "go_buildinfo" in info:
            src_mod_line = next((ln.strip() for ln in go_mod.read_text(encoding="utf-8").splitlines() if ln.startswith("module ")), "")
            src_mod = src_mod_line.replace("module ", "").strip()
            bin_mod = (info["go_buildinfo"].get("mod") or "").split()[0]
            alignment["checks"].append({
                "check": "go_module_match",
                "source_value": src_mod,
                "release_value": bin_mod,
                "matched": (src_mod == bin_mod),
            })
        ui_index = source_dir / "ui" / "index.html"
        if ui_index.exists():
            alignment["checks"].append({
                "check": "embedded_ui_present",
                "source_value": "ui/index.html present",
                "release_value": f"index.html={probe_hits.get('index.html')}, /_/={probe_hits.get('/_/')}",
                "matched": bool(probe_hits.get("index.html") and probe_hits.get("/_/")),
            })
        if alignment["checks"] and all(c["matched"] for c in alignment["checks"]):
            alignment["status"] = "observed"
        elif alignment["checks"]:
            alignment["status"] = "inferred"
    info["source_alignment"] = alignment
    return info


def main():
    ap = argparse.ArgumentParser(description="REA official release artifact inspector")
    ap.add_argument("--archive", help="Path to official release archive (.zip/.tar.gz)")
    ap.add_argument("--binary", required=True, help="Path to extracted official executable")
    ap.add_argument("--checksums", help="Path to official upstream checksums.txt")
    ap.add_argument("--source", help="Path to pinned upstream source directory")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--commit", default=None)
    ap.add_argument("--out", required=True, help="Output release_audit.json path")
    args = ap.parse_args()

    result = {
        "schema_version": "1.0.0",
        "host_os": platform.system(),
        "host_arch": platform.machine(),
        "release_tag": args.tag,
        "source_commit_sha": args.commit,
        "archive": None,
        "binary": None,
    }

    upstream_sums = parse_checksums(pathlib.Path(args.checksums)) if args.checksums else {}

    if args.archive:
        arch = pathlib.Path(args.archive)
        arch_sha = sha256_file(arch)
        expected = upstream_sums.get(arch.name)
        entries = []
        if arch.suffix.lower() == ".zip":
            with zipfile.ZipFile(arch) as zf:
                entries = sorted(zf.namelist())
        result["archive"] = {
            "filename": arch.name,
            "size_bytes": arch.stat().st_size,
            "sha256": arch_sha,
            "upstream_checksum_expected": expected,
            "upstream_checksum_verified": (expected == arch_sha) if expected else None,
            "entries": entries,
        }

    src_dir = pathlib.Path(args.source) if args.source else None
    result["binary"] = inspect_binary(pathlib.Path(args.binary), src_dir)

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "archive_verified": (result["archive"] or {}).get("upstream_checksum_verified"),
        "binary_sha256": result["binary"]["sha256"],
        "source_alignment": result["binary"]["source_alignment"]["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
