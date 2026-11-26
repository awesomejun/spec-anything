#!/usr/bin/env python3
"""
REA Release Artifact Inspector for spec-anything (v4.0.0).
Inspects authorized official release binaries, archives (.zip, .tar.gz, .tgz),
Mach-O/ELF/PE executables, Go/Rust/Tauri/Electron/npm build metadata, code signatures,
exported symbols, and custom embedded string probes — and detects optional Ghidra/IDA
deep static decompiler backends when installed.
"""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import shutil
import subprocess
import tarfile
import zipfile


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run_cmd(cmd: list[str], timeout: int = 30) -> dict:
    if not shutil.which(cmd[0]):
        return {"available": False, "returncode": None, "stdout": "", "stderr": f"tool_not_found: {cmd[0]}"}
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return {"available": True, "returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}


def parse_checksums(path: pathlib.Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and len(parts[0]) == 64:
            mapping[parts[1].lstrip("*")] = parts[0].lower()
    return mapping


def detect_decompiler_backends(requested: str) -> dict:
    ghidra_dir = os.environ.get("GHIDRA_INSTALL_DIR")
    ghidra_headless = shutil.which("analyzeHeadless")
    if not ghidra_headless and ghidra_dir:
        cand = pathlib.Path(ghidra_dir) / "support" / "analyzeHeadless"
        if cand.exists():
            ghidra_headless = str(cand)
    ida_headless = shutil.which("idat") or shutil.which("idat64") or shutil.which("ida-hcli")
    selected = requested
    if requested == "auto":
        if ghidra_headless:
            selected = "ghidra+os"
        elif ida_headless:
            selected = "ida+os"
        else:
            selected = "os"
    return {
        "requested": requested,
        "selected": selected,
        "ghidra_headless_available": bool(ghidra_headless),
        "ida_headless_available": bool(ida_headless),
    }


def list_archive_entries(arch: pathlib.Path) -> list[str]:
    low = arch.name.lower()
    if low.endswith(".zip"):
        with zipfile.ZipFile(arch) as zf:
            return sorted(zf.namelist())
    if low.endswith((".tar.gz", ".tgz", ".tar.xz", ".tar.bz2")):
        with tarfile.open(arch, "r:*") as tf:
            return sorted(m.name for m in tf.getmembers())
    return []


def inspect_binary(bin_path: pathlib.Path, source_dir: pathlib.Path | None, custom_probes: list[str], backend: str) -> dict:
    info: dict = {
        "binary_path": bin_path.name,
        "size_bytes": bin_path.stat().st_size,
        "sha256": sha256_file(bin_path),
        "backend": detect_decompiler_backends(backend),
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

    # macOS Mach-O slices, dynamic libraries, code signature, exported symbols
    if platform.system() == "Darwin":
        lipo_res = run_cmd(["lipo", "-archs", str(bin_path)])
        if lipo_res["available"] and lipo_res["returncode"] == 0 and lipo_res["stdout"]:
            info["macho_architectures"] = lipo_res["stdout"].split()
        otool_res = run_cmd(["otool", "-L", str(bin_path)])
        if otool_res["available"] and otool_res["returncode"] == 0:
            libs = [ln.strip().split(" (")[0] for ln in otool_res["stdout"].splitlines()[1:] if ln.strip()]
            info["linked_libraries"] = libs
        cs_res = run_cmd(["codesign", "-dv", "--verbose=2", str(bin_path)])
        cs_text = "\n".join(x for x in [cs_res["stdout"], cs_res["stderr"]] if x)
        info["codesign"] = {
            "signed": cs_res["returncode"] == 0,
            "summary_lines": [
                ln for ln in cs_text.splitlines()
                if any(k in ln for k in ("Identifier=", "Format=", "Signature=", "CDHash=", "Authority=", "Runtime Version=", "not signed"))
            ][:14],
        }
        nm_res = run_cmd(["nm", "-gU", str(bin_path)])
        if nm_res["available"] and nm_res["returncode"] == 0:
            syms = [ln.strip() for ln in nm_res["stdout"].splitlines() if ln.strip()]
            info["exported_symbols"] = {"count": len(syms), "sample": syms[:25]}
    else:
        readelf_res = run_cmd(["readelf", "-d", str(bin_path)])
        if readelf_res["available"] and readelf_res["returncode"] == 0:
            needed = [ln.strip() for ln in readelf_res["stdout"].splitlines() if "(NEEDED)" in ln]
            info["linked_libraries"] = needed[:40]

    # Stack & embedded runtime probes (generic across Tauri, Electron, Rust, Go, Web/SPA + caller custom probes)
    raw_bytes = bin_path.read_bytes()
    default_probes = [
        "index.html",
        "tauri://localhost",
        "ipc://localhost",
        "electron",
        "app.asar",
        "rustc",
        "sqlite3",
    ]
    all_probes = list(dict.fromkeys(default_probes + custom_probes))
    probe_hits = {p: (p.encode("utf-8") in raw_bytes) for p in all_probes}
    info["embedded_string_probes"] = probe_hits

    detected_runtimes = []
    if "go_buildinfo" in info:
        detected_runtimes.append("go")
    if probe_hits.get("tauri://localhost") or probe_hits.get("ipc://localhost"):
        detected_runtimes.append("tauri")
    if probe_hits.get("app.asar") or probe_hits.get("electron"):
        detected_runtimes.append("electron")
    if probe_hits.get("rustc"):
        detected_runtimes.append("rust")
    if probe_hits.get("sqlite3"):
        detected_runtimes.append("sqlite")
    info["detected_runtimes"] = detected_runtimes

    # Source alignment checks
    alignment: dict = {"status": "unverified", "checks": []}
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
        cargo_toml = source_dir / "Cargo.toml"
        tauri_conf = next(iter(source_dir.glob("**/tauri.conf.json")), None)
        if tauri_conf and tauri_conf.exists():
            alignment["checks"].append({
                "check": "tauri_runtime_match",
                "source_value": tauri_conf.name,
                "release_value": f"tauri_detected={'tauri' in detected_runtimes}",
                "matched": ("tauri" in detected_runtimes),
            })
        elif cargo_toml.exists():
            alignment["checks"].append({
                "check": "rust_binary_match",
                "source_value": "Cargo.toml present",
                "release_value": f"rustc_marker={probe_hits.get('rustc')}",
                "matched": bool(probe_hits.get("rustc")),
            })
        for p in custom_probes:
            alignment["checks"].append({
                "check": f"custom_probe:{p}",
                "source_value": p,
                "release_value": str(probe_hits.get(p)),
                "matched": bool(probe_hits.get(p)),
            })
        if alignment["checks"] and all(c["matched"] for c in alignment["checks"]):
            alignment["status"] = "observed"
        elif alignment["checks"]:
            alignment["status"] = "inferred"
    info["source_alignment"] = alignment
    return info


def main() -> None:
    ap = argparse.ArgumentParser(description="REA official release artifact inspector")
    ap.add_argument("--archive", help="Path to official release archive (.zip/.tar.gz/.tgz)")
    ap.add_argument("--binary", required=True, help="Path to extracted official executable or main bundle")
    ap.add_argument("--checksums", help="Path to official upstream checksums.txt")
    ap.add_argument("--source", help="Path to pinned upstream source directory")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--commit", default=None)
    ap.add_argument("--probe", action="append", default=[], help="Custom ASCII/UTF-8 marker string to probe inside binary (repeatable)")
    ap.add_argument("--backend", choices=["auto", "os", "ghidra", "ida"], default="auto", help="Preferred static REA inspection backend")
    ap.add_argument("--out", required=True, help="Output release_audit.json path")
    args = ap.parse_args()

    result = {
        "schema_version": "1.1.0",
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
        entries = list_archive_entries(arch)
        result["archive"] = {
            "filename": arch.name,
            "size_bytes": arch.stat().st_size,
            "sha256": arch_sha,
            "upstream_checksum_expected": expected,
            "upstream_checksum_verified": (expected == arch_sha) if expected else None,
            "entry_count": len(entries),
            "entries_sample": entries[:100],
        }

    src_dir = pathlib.Path(args.source) if args.source else None
    result["binary"] = inspect_binary(pathlib.Path(args.binary), src_dir, args.probe, args.backend)

    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "ok",
        "archive_verified": (result["archive"] or {}).get("upstream_checksum_verified"),
        "binary_sha256": result["binary"]["sha256"],
        "detected_runtimes": result["binary"]["detected_runtimes"],
        "backend": result["binary"]["backend"]["selected"],
        "source_alignment": result["binary"]["source_alignment"]["status"],
    }, indent=2))


if __name__ == "__main__":
    main()
