#!/usr/bin/env python3
"""
Secret & Credential Guard for spec-anything.
Scans deliverables (Markdown, JSON, JSONL, SQL, Python, HTML) for accidental leaks
of API keys, cloud tokens, private keys, or live JWT/Bearer secrets before sealing.
"""
import argparse
import json
import pathlib
import re
import sys

TEXT_EXTS = {".md", ".json", ".jsonl", ".sql", ".py", ".ts", ".js", ".mjs", ".html", ".txt", ".yaml", ".yml"}
SKIP_DIRS = {".git", "node_modules", "__pycache__"}

PATTERNS = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("stripe_secret_key", re.compile(r"\bsk_(?:live|test)_[0-9a-zA-Z]{16,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b")),
    ("pem_private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("bearer_jwt_token", re.compile(r"\bBearer\s+eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
    ("raw_jwt_token", re.compile(r"\beyJhbGciOi[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
]


def scan_dir(root: pathlib.Path, redact: bool = False) -> list:
    hits = []
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        modified = text
        rel = p.relative_to(root).as_posix()
        for idx, line in enumerate(text.splitlines(), 1):
            if "REDACTED_SECRET" in line or "SYNTHETIC_EXAMPLE_PATTERN" in line:
                continue
            for name, rx in PATTERNS:
                for m in rx.finditer(line):
                    hits.append({
                        "file": rel,
                        "line": idx,
                        "rule": name,
                        "preview": m.group(0)[:12] + "...[REDACTED]",
                    })
        if redact and any(h["file"] == rel for h in hits):
            for name, rx in PATTERNS:
                modified = rx.sub(f"<REDACTED_SECRET:{name}>", modified)
            p.write_text(modified, encoding="utf-8")
    return hits


def main():
    ap = argparse.ArgumentParser(description="Scan or redact secrets in spec-anything deliverables")
    ap.add_argument("target_dir")
    ap.add_argument("--redact", action="store_true", help="Replace matched secrets in place")
    ap.add_argument("--fail-on-hit", action="store_true", help="Exit non-zero if any hit is found")
    args = ap.parse_args()

    root = pathlib.Path(args.target_dir).resolve()
    hits = scan_dir(root, redact=args.redact)
    print(json.dumps({"target": str(root), "redacted": args.redact, "hit_count": len(hits), "hits": hits}, indent=2))
    if args.fail_on_hit and hits and not args.redact:
        sys.exit(2)


if __name__ == "__main__":
    main()
