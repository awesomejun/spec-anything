#!/usr/bin/env python3
"""
Environment & Reverse-Engineering Backend Doctor for spec-anything.
Modeled after craft-anything's doctor preflight check: detects core runtime tools,
UI/review packages, OS binary inspection utilities, static decompilers (Ghidra, IDA),
and dynamic instrumentation (Frida), then reports ready observation tiers and modes.
"""
import argparse
import importlib.util
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys


def which_info(cmd: str, version_args: list[str] | None = None) -> dict:
    path = shutil.which(cmd)
    if not path:
        return {"installed": False, "path": None, "version": None}
    version = None
    if version_args:
        try:
            proc = subprocess.run([path, *version_args], capture_output=True, text=True, timeout=5)
            out = (proc.stdout or proc.stderr or "").strip()
            version = out.splitlines()[0][:120] if out else None
        except Exception:
            version = None
    return {"installed": True, "path": pathlib.Path(path).name, "version": version}


def py_pkg(mod_name: str) -> dict:
    spec = importlib.util.find_spec(mod_name)
    return {"installed": spec is not None}


def detect_ghidra() -> dict:
    install_dir = os.environ.get("GHIDRA_INSTALL_DIR")
    headless = shutil.which("analyzeHeadless")
    if not headless and install_dir:
        cand = pathlib.Path(install_dir) / "support" / "analyzeHeadless"
        if cand.exists():
            headless = str(cand)
    pyghidra_mod = importlib.util.find_spec("pyghidra") is not None
    pyghidra_mcp = shutil.which("pyghidra-mcp") is not None
    return {
        "available": bool(headless or pyghidra_mod or pyghidra_mcp),
        "analyzeHeadless": bool(headless),
        "ghidra_install_dir_set": bool(install_dir),
        "pyghidra_python": pyghidra_mod,
        "pyghidra_mcp_cli": pyghidra_mcp,
        "recommended_setup": "Install Ghidra 12+ (JDK 21/25) or uvx pyghidra-mcp for headless decompilation",
    }


def detect_ida() -> dict:
    idat = shutil.which("idat") or shutil.which("idat64")
    hcli = shutil.which("ida-hcli") or shutil.which("hcli")
    idalib_mod = importlib.util.find_spec("idalib") is not None
    ida_mcp = shutil.which("ida-pro-mcp") or shutil.which("idalib-mcp")
    mac_apps = list(pathlib.Path("/Applications").glob("IDA*.app")) if platform.system() == "Darwin" else []
    return {
        "available": bool(idat or idalib_mod or ida_mcp or mac_apps),
        "idat_headless": bool(idat),
        "idalib_python": idalib_mod,
        "ida_hcli": bool(hcli),
        "ida_mcp_cli": bool(ida_mcp),
        "app_bundle_detected": bool(mac_apps),
        "recommended_setup": "Install IDA Pro 9.4+ with idalib and official HexRaysSA/ida-mcp (uvx ida-hcli mcp install)",
    }


def detect_frida() -> dict:
    frida_cli = shutil.which("frida")
    frida_trace = shutil.which("frida-trace")
    frida_ps = shutil.which("frida-ps")
    frida_itrace = shutil.which("frida-itrace")
    frida_py = importlib.util.find_spec("frida") is not None
    return {
        "available": bool(frida_cli or frida_trace or frida_py),
        "frida_cli": bool(frida_cli),
        "frida_trace": bool(frida_trace),
        "frida_ps": bool(frida_ps),
        "frida_itrace": bool(frida_itrace),
        "frida_python": frida_py,
        "recommended_setup": "pip install frida frida-tools (authorized runtime tracing only)",
    }


def collect_report() -> dict:
    core = {
        "python3": {"installed": True, "version": platform.python_version(), "ok": sys.version_info >= (3, 10)},
        "git": which_info("git", ["--version"]),
        "sqlite3": which_info("sqlite3", ["--version"]),
        "shasum": which_info("shasum", ["--version"]),
    }
    ui_review = {
        "playwright": py_pkg("playwright"),
        "PIL": py_pkg("PIL"),
        "jsonschema": py_pkg("jsonschema"),
        "markdown": py_pkg("markdown"),
        "docx": py_pkg("docx"),
    }
    os_native = {
        "file": which_info("file", ["--version"]),
        "otool": which_info("otool", ["--version"]),
        "nm": which_info("nm", ["--version"]),
        "codesign": which_info("codesign"),
        "lipo": which_info("lipo"),
        "strings": which_info("strings"),
        "dwarfdump": which_info("dwarfdump", ["--version"]),
        "lldb": which_info("lldb", ["--version"]),
        "readelf": which_info("readelf", ["--version"]),
        "objdump": which_info("objdump", ["--version"]),
        "go": which_info("go", ["version"]),
    }
    backends = {
        "ghidra": detect_ghidra(),
        "ida": detect_ida(),
        "frida": detect_frida(),
    }

    t1_ready = core["python3"]["ok"] and core["git"]["installed"]
    t2_ready = t1_ready and core["sqlite3"]["installed"]
    t3_ready = t2_ready and ui_review["playwright"]["installed"] and ui_review["PIL"]["installed"]
    os_rea_ready = any(os_native[k]["installed"] for k in ("otool", "readelf", "objdump", "nm", "file"))

    ready_lanes = ["static_source"]
    if t3_ready:
        ready_lanes.append("live_ui_playwright")
    if os_rea_ready:
        ready_lanes.append("os_binary_rea")
    if backends["ghidra"]["available"]:
        ready_lanes.append("ghidra_decompiler")
    if backends["ida"]["available"]:
        ready_lanes.append("ida_decompiler")
    if backends["frida"]["available"]:
        ready_lanes.append("frida_dynamic_trace")

    return {
        "schema_version": "1.0.0",
        "host_os": platform.system(),
        "host_arch": platform.machine(),
        "tiers_ready": {"T1": t1_ready, "T2": t2_ready, "T3": t3_ready},
        "modes_ready": {
            "clean-room": t2_ready,
            "deep": t1_ready and os_rea_ready,
        },
        "active_analysis_lanes": ready_lanes,
        "core": core,
        "ui_review_python": ui_review,
        "os_native_tools": os_native,
        "optional_re_backends": backends,
    }


def print_human(rep: dict) -> None:
    print(f"spec-anything doctor ({rep['host_os']} / {rep['host_arch']})")
    print(f"Tiers Ready : T1={rep['tiers_ready']['T1']} | T2={rep['tiers_ready']['T2']} | T3={rep['tiers_ready']['T3']}")
    print(f"Modes Ready : clean-room={rep['modes_ready']['clean-room']} | deep={rep['modes_ready']['deep']}")
    print(f"Active Lanes: {', '.join(rep['active_analysis_lanes'])}")
    print("\n[Core Tools]")
    for k, v in rep["core"].items():
        mark = "OK" if v.get("installed") else "MISSING"
        ver = f" ({v['version']})" if v.get("version") else ""
        print(f"  - {k:12s}: {mark}{ver}")
    print("\n[UI & Review Python Packages]")
    for k, v in rep["ui_review_python"].items():
        print(f"  - {k:12s}: {'OK' if v['installed'] else 'MISSING'}")
    print("\n[OS Native Binary REA Tools]")
    present = [k for k, v in rep["os_native_tools"].items() if v["installed"]]
    missing = [k for k, v in rep["os_native_tools"].items() if not v["installed"]]
    print(f"  - installed : {', '.join(present) if present else '(none)'}")
    print(f"  - absent    : {', '.join(missing) if missing else '(none)'}")
    print("\n[Optional Deep RE Backends (Ghidra / IDA / Frida)]")
    for name, info in rep["optional_re_backends"].items():
        state = "AVAILABLE" if info["available"] else "NOT INSTALLED (fallback: OS REA + live runtime)"
        print(f"  - {name:8s}: {state}")


def main() -> None:
    ap = argparse.ArgumentParser(description="spec-anything environment and RE backend doctor")
    ap.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    ap.add_argument("--require-tier", choices=["T1", "T2", "T3"], help="Exit non-zero if requested tier is not ready")
    args = ap.parse_args()

    rep = collect_report()
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print_human(rep)

    if args.require_tier and not rep["tiers_ready"][args.require_tier]:
        sys.exit(1)


if __name__ == "__main__":
    main()
