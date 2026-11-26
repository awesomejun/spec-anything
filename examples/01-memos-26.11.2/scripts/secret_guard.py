#!/usr/bin/env python3
"""Secret & credential leak guard for spec-anything bundles.

Absorbed from WindowHyun/Reverse_Spec_and_PRD secret-scanning discipline and
extended to cover bearer tokens, JWT literals, private keys, and sensitive
filenames across all generated 01-12 specs, 06 evidence JSONL, and 09 contracts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

SENSITIVE_FILENAMES = {"secrets.json", "credentials.json", "id_rsa", "id_rsa.pub", ".env"}
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx")

SECRET_REGEXES = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "google_api_key"),
    (re.compile(r"sk_(?:live|test)_[0-9a-zA-Z]{16,}"), "stripe_secret_key"),
    (re.compile(r"gh[pousr]_[0-9A-Za-z]{20,}"), "github_token"),
    (re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"), "slack_token"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PRIVATE )?PRIVATE KEY-----"), "private_key_pem"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{12,}\.eyJ[A-Za-z0-9_\-]{12,}\.[A-Za-z0-9_\-]{16,}"), "jwt_literal"),
]

TEXT_EXTS = {".md", ".json", ".jsonl", ".sql", ".py", ".mjs", ".js", ".ts", ".txt", ".html", ".yaml", ".yml"}
SKIP_DIRS = {".git", "__pycache__", "node_modules"}


def scan_bundle(root: Path) -> dict:
    findings: list[dict] = []
    scanned_files = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fname in sorted(filenames):
            fpath = Path(dirpath) / fname
            rel = fpath.relative_to(root).as_posix()
            if fname in SENSITIVE_FILENAMES or fname.endswith(SENSITIVE_SUFFIXES):
                findings.append({"path": rel, "line": 0, "kind": "sensitive_filename"})
                continue
            if fpath.suffix.lower() not in TEXT_EXTS:
                continue
            if rel == "scripts/secret_guard.py" or rel == "scripts/extract_source_map.py":
                continue
            scanned_files += 1
            text = fpath.read_text(encoding="utf-8", errors="replace")
            for idx, ln in enumerate(text.splitlines(), 1):
                for rx, kind in SECRET_REGEXES:
                    if rx.search(ln):
                        findings.append({"path": rel, "line": idx, "kind": kind})
    return {
        "bundle_root": str(root),
        "scanned_files": scanned_files,
        "findings_count": len(findings),
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scan spec-anything bundle for accidental secrets/tokens")
    ap.add_argument("--bundle-dir", required=True)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()
    report = scan_bundle(Path(args.bundle_dir).resolve())
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
