#!/usr/bin/env python3
"""Deterministic multi-language static source-map & frontend fact extractor.

Combines:
- cc-rsg source_map_v2 role taxonomy (5 universal tables: Modules, Entities,
  Actions, Data, Dependencies) + loud warnings on unsupported/unparsed files.
- Reverse_Spec_and_PRD deterministic fact extraction (frontend routes,
  components, API/RPC calls, storage/state hooks, secret pattern scan).

Zero LLM calls: identical source tree produces identical SHA-256 output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"

ROLE_TO_TABLE = {
    "module": "Modules",
    "component": "Modules",
    "page": "Modules",
    "entity": "Entities",
    "proto_message": "Entities",
    "endpoint": "Actions",
    "rpc_service": "Actions",
    "rpc_method": "Actions",
    "route": "Actions",
    "command": "Actions",
    "callable": "Actions",
    "datastore": "Data",
    "migration": "Data",
    "config": "Dependencies",
    "dependency": "Dependencies",
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "vendor",
    "__pycache__",
    ".next",
    ".turbo",
    "coverage",
    "gen",
}

SUPPORTED_EXTS = {".go", ".proto", ".sql", ".ts", ".tsx", ".js", ".jsx", ".yml", ".yaml", ".json"}

PROTO_SERVICE_RE = re.compile(r"^\s*service\s+([A-Za-z0-9_]+)\s*\{")
PROTO_RPC_RE = re.compile(r"^\s*rpc\s+([A-Za-z0-9_]+)\s*\(([^)]+)\)\s*returns\s*\(([^)]+)\)")
PROTO_HTTP_RE = re.compile(r'\b(get|post|put|patch|delete)\s*:\s*"([^"]+)"')
PROTO_MSG_RE = re.compile(r"^\s*message\s+([A-Za-z0-9_]+)\s*\{")

GO_FUNC_RE = re.compile(r"^func\s+(?:\([^)]+\)\s+)?([A-Z][A-Za-z0-9_]*)\s*\(")
GO_TYPE_RE = re.compile(r"^type\s+([A-Z][A-Za-z0-9_]*)\s+(struct|interface)\b")
GO_EMBED_RE = re.compile(r"^//go:embed\s+(.+)$")

SQL_TABLE_RE = re.compile(r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
SQL_INDEX_RE = re.compile(r"CREATE\s+(?:UNIQUE\s+)?INDEX(?:\s+IF\s+NOT\s+EXISTS)?\s+([a-zA-Z0-9_]+)", re.IGNORECASE)

TS_ROUTE_RE = re.compile(r'path\s*:\s*["\']([^"\']+)["\']')
TS_EXPORT_COMP_RE = re.compile(r"export\s+(?:default\s+)?(?:function|const)\s+([A-Z][A-Za-z0-9_]*)\b")
TS_CONNECT_RE = re.compile(r"createClient\s*\(\s*([A-Za-z0-9_]+)\s*")

SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "aws_access_key"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "google_api_key"),
    (re.compile(r"sk_(?:live|test)_[0-9a-zA-Z]{16,}"), "stripe_secret_key"),
    (re.compile(r"gh[pousr]_[0-9A-Za-z]{20,}"), "github_token"),
    (re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"), "slack_token"),
    (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private_key_block"),
]


def sha16(text: str) -> str:
    return "sha1:" + hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def add_unit(
    units: list[dict[str, Any]],
    *,
    rel: str,
    line: int,
    language: str,
    role: str,
    kind: str,
    name: str,
    tier: str = "middle",
    extra: dict[str, Any] | None = None,
) -> None:
    uid = f"U-{len(units)+1:04d}"
    entry: dict[str, Any] = {
        "id": uid,
        "path": rel,
        "line_range": [line, line],
        "language": language,
        "role": role,
        "table": ROLE_TO_TABLE[role],
        "kind": kind,
        "tier": tier,
        "name": name,
        "fingerprint": sha16(f"{rel}:{line}:{kind}:{name}"),
    }
    if extra:
        entry.update(extra)
    units.append(entry)


def scan_tree(root: Path) -> dict[str, Any]:
    units: list[dict[str, Any]] = []
    warnings: list[str] = []
    secret_warnings: list[dict[str, Any]] = []
    files_scanned = 0
    files_skipped_ext: dict[str, int] = {}
    lang_counts: dict[str, int] = {}
    frontend_routes: list[dict[str, Any]] = []
    embed_directives: list[dict[str, Any]] = []

    all_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fname in sorted(filenames):
            all_files.append(Path(dirpath) / fname)

    for fpath in all_files:
        rel = fpath.relative_to(root).as_posix()
        ext = fpath.suffix.lower()
        if ext not in SUPPORTED_EXTS:
            if ext:
                files_skipped_ext[ext] = files_skipped_ext.get(ext, 0) + 1
            continue
        if rel.endswith("_test.go") or ".test." in fpath.name or ".spec." in fpath.name:
            continue
        files_scanned += 1
        try:
            text = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warnings.append(f"unreadable_file:{rel}:{exc}")
            continue
        lines = text.splitlines()

        # Secret scan (metadata only, never emits matched secret text)
        for idx, ln in enumerate(lines, 1):
            for pat, label in SECRET_PATTERNS:
                if pat.search(ln):
                    secret_warnings.append({"path": rel, "line": idx, "kind": label})

        if ext == ".proto":
            lang_counts["proto"] = lang_counts.get("proto", 0) + 1
            cur_svc = None
            cur_rpc = None
            cur_rpc_line = 0
            for idx, ln in enumerate(lines, 1):
                m_svc = PROTO_SERVICE_RE.match(ln)
                if m_svc:
                    cur_svc = m_svc.group(1)
                    add_unit(units, rel=rel, line=idx, language="proto", role="rpc_service", kind="proto_service", name=cur_svc, tier="macro")
                    continue
                m_rpc = PROTO_RPC_RE.match(ln)
                if m_rpc and cur_svc:
                    cur_rpc = m_rpc.group(1)
                    cur_rpc_line = idx
                    add_unit(
                        units,
                        rel=rel,
                        line=idx,
                        language="proto",
                        role="rpc_method",
                        kind="proto_rpc",
                        name=f"{cur_svc}.{cur_rpc}",
                        extra={"request": m_rpc.group(2).strip(), "response": m_rpc.group(3).strip()},
                    )
                    continue
                m_http = PROTO_HTTP_RE.search(ln)
                if m_http and cur_svc and cur_rpc:
                    add_unit(
                        units,
                        rel=rel,
                        line=idx,
                        language="proto",
                        role="endpoint",
                        kind="proto_http_binding",
                        name=f"{m_http.group(1).upper()} {m_http.group(2)}",
                        extra={"endpoint": {"method": m_http.group(1).upper(), "path": m_http.group(2), "rpc": f"{cur_svc}.{cur_rpc}", "rpc_line": cur_rpc_line}},
                    )
                    continue
                m_msg = PROTO_MSG_RE.match(ln)
                if m_msg:
                    add_unit(units, rel=rel, line=idx, language="proto", role="proto_message", kind="proto_message", name=m_msg.group(1), tier="micro")

        elif ext == ".go":
            lang_counts["go"] = lang_counts.get("go", 0) + 1
            for idx, ln in enumerate(lines, 1):
                m_emb = GO_EMBED_RE.match(ln.strip())
                if m_emb:
                    embed_directives.append({"path": rel, "line": idx, "pattern": m_emb.group(1).strip()})
                    add_unit(units, rel=rel, line=idx, language="go", role="config", kind="go_embed", name=m_emb.group(1).strip())
                m_type = GO_TYPE_RE.match(ln)
                if m_type:
                    add_unit(units, rel=rel, line=idx, language="go", role="entity", kind=f"go_{m_type.group(2)}", name=m_type.group(1))
                m_fn = GO_FUNC_RE.match(ln)
                if m_fn and (rel.startswith("server/api/") or rel.startswith("cmd/") or rel.startswith("store/")):
                    role = "command" if rel.startswith("cmd/") else "callable"
                    add_unit(units, rel=rel, line=idx, language="go", role=role, kind="go_exported_func", name=m_fn.group(1), tier="micro")

        elif ext == ".sql":
            lang_counts["sql"] = lang_counts.get("sql", 0) + 1
            role = "migration" if "migration" in rel else "datastore"
            for idx, ln in enumerate(lines, 1):
                m_tbl = SQL_TABLE_RE.search(ln)
                if m_tbl:
                    add_unit(units, rel=rel, line=idx, language="sql", role="datastore", kind="sql_table", name=m_tbl.group(1))
                m_idx = SQL_INDEX_RE.search(ln)
                if m_idx:
                    add_unit(units, rel=rel, line=idx, language="sql", role=role, kind="sql_index", name=m_idx.group(1), tier="micro")

        elif ext in {".ts", ".tsx", ".js", ".jsx"}:
            lang_counts["typescript_js"] = lang_counts.get("typescript_js", 0) + 1
            is_page = "/pages/" in f"/{rel}"
            for idx, ln in enumerate(lines, 1):
                if "router" in rel.lower():
                    for m_rt in TS_ROUTE_RE.finditer(ln):
                        frontend_routes.append({"path": rel, "line": idx, "route": m_rt.group(1)})
                        add_unit(units, rel=rel, line=idx, language="typescript", role="route", kind="react_route", name=m_rt.group(1))
                m_comp = TS_EXPORT_COMP_RE.search(ln)
                if m_comp and (is_page or "/components/" in f"/{rel}"):
                    add_unit(
                        units,
                        rel=rel,
                        line=idx,
                        language="typescript",
                        role="page" if is_page else "component",
                        kind="react_page" if is_page else "react_component",
                        name=m_comp.group(1),
                    )
                m_conn = TS_CONNECT_RE.search(ln)
                if m_conn:
                    add_unit(units, rel=rel, line=idx, language="typescript", role="dependency", kind="connect_rpc_client", name=m_conn.group(1))

        elif ext in {".yml", ".yaml", ".json"}:
            lang_counts["config"] = lang_counts.get("config", 0) + 1
            if rel.startswith(".github/workflows/") or rel in {"web/package.json", "go.mod"}:
                add_unit(units, rel=rel, line=1, language="config", role="config", kind="project_config", name=rel, tier="macro")

    # Loud warnings for unsupported non-doc/asset code extensions (cc-rsg discipline)
    for ext, cnt in sorted(files_skipped_ext.items()):
        if ext not in {".md", ".txt", ".png", ".svg", ".ico", ".webp", ".woff2", ".css", ".html", ".lock", ".sum", ".mod", ".gitignore"}:
            warnings.append(f"loud_warning:unsupported_extension:{ext}:count={cnt}:fallback=not_ast_parsed")

    by_table: dict[str, int] = {}
    by_role: dict[str, int] = {}
    for u in units:
        by_table[u["table"]] = by_table.get(u["table"], 0) + 1
        by_role[u["role"]] = by_role.get(u["role"], 0) + 1

    return {
        "schema_version": SCHEMA_VERSION,
        "extractor": "spec-anything deterministic source-map v1.0.0 (cc-rsg taxonomy + Reverse_Spec_and_PRD frontend facts)",
        "target_root_name": root.name,
        "stats": {
            "files_scanned": files_scanned,
            "total_units": len(units),
            "by_language": lang_counts,
            "by_table": by_table,
            "by_role": by_role,
            "frontend_routes_count": len(frontend_routes),
            "go_embed_directives_count": len(embed_directives),
            "secret_warnings_count": len(secret_warnings),
        },
        "go_embed_directives": embed_directives,
        "frontend_routes": frontend_routes,
        "warnings": warnings,
        "secret_warnings": secret_warnings,
        "units": units,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic source-map extractor for spec-anything")
    parser.add_argument("--source-dir", required=True, help="Pinned upstream source tree root")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    src_root = Path(args.source_dir).resolve()
    if not src_root.is_dir():
        print(f"ERROR: source directory not found: {src_root}", file=sys.stderr)
        return 2

    result = scan_tree(src_root)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["stats"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
