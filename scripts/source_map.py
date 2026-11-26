#!/usr/bin/env python3
"""
Deterministic multi-language static extractor for spec-anything.
Combines role-typed canonical extraction (Modules, Entities, Actions, Data, Dependencies)
with frontend route/API/component fact tables and Loud Warnings for unsupported languages
or low parser coverage. Same source tree always produces identical sorted output.
"""
import argparse
import collections
import json
import pathlib
import re

SUPPORTED_LANGS = {
    ".go": "go",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".svelte": "svelte",
    ".vue": "vue",
    ".py": "python",
    ".rs": "rust",
    ".sql": "sql",
    ".html": "html",
    ".scss": "scss",
    ".css": "css",
}

IGNORED_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", ".next", ".nuxt",
    "__pycache__", ".venv", "venv", "target", ".spec-anything", ".cc-rsg",
}

SECRET_FILENAMES = {".env", ".env.local", "secrets.json", "credentials.json", "id_rsa", "id_rsa.pub"}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx")

# Role extractors
GO_ROUTE_RE = re.compile(r'\.(GET|POST|PUT|PATCH|DELETE|Any|BindFunc)\(\s*"([^"]+)"')
GO_CMD_RE = re.compile(r'Use:\s*"([^"]+)"')
GO_STRUCT_RE = re.compile(r'^type\s+([A-Z][A-Za-z0-9_]*)\s+struct\b', re.M)
GO_FUNC_RE = re.compile(r'^func\s+(?:\([^)]+\)\s+)?([A-Z][A-Za-z0-9_]*)\s*\(', re.M)
GO_MIGRATION_RE = re.compile(r'CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+[`"\[]?([A-Za-z0-9_]+)[`"\]]?', re.I)

JS_ROUTE_RE = re.compile(r'''(?:path\s*:\s*|route\(\s*|["'])(/[A-Za-z0-9_:\-/{}*]+)''')
JS_API_RE = re.compile(r'''(?:fetch|axios\.\w+|ApiClient\.\w+|send)\(\s*[`"']([^`"']+)[`"']''')
JS_EXPORT_RE = re.compile(r'export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const)\s+([A-Za-z0-9_]+)')
SVELTE_ROUTE_RE = re.compile(r'''["'](/[A-Za-z0-9_:\-/{}*]*)["']\s*:\s*([A-Z][A-Za-z0-9_]+)''')
CSS_VAR_RE = re.compile(r'(--[a-zA-Z0-9\-]+)\s*:\s*([^;}{]+);')

PY_ROUTE_RE = re.compile(r'@\w+\.(get|post|put|patch|delete|route)\(\s*["\']([^"\']+)["\']')
PY_CLASS_RE = re.compile(r'^class\s+([A-Za-z0-9_]+)', re.M)
PY_DEF_RE = re.compile(r'^(?:async\s+)?def\s+([A-Za-z0-9_]+)\s*\(', re.M)

RUST_STRUCT_RE = re.compile(r'^pub\s+(?:struct|enum|trait)\s+([A-Za-z0-9_]+)', re.M)
RUST_FN_RE = re.compile(r'^pub\s+(?:async\s+)?fn\s+([A-Za-z0-9_]+)', re.M)


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def extract_dependencies(root: pathlib.Path) -> list:
    deps = []
    go_mod = root / "go.mod"
    if go_mod.exists():
        in_req = False
        for idx, raw in enumerate(go_mod.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            line = raw.strip()
            if line.startswith("require ("):
                in_req = True
                continue
            if in_req and line == ")":
                in_req = False
                continue
            if line.startswith("require ") and "(" not in line:
                parts = line.split()
                if len(parts) >= 3:
                    deps.append({"ecosystem": "go", "name": parts[1], "version": parts[2], "indirect": "// indirect" in line, "ref": f"go.mod:{idx}"})
            elif in_req and line and not line.startswith("//"):
                parts = line.split()
                if len(parts) >= 2:
                    deps.append({"ecosystem": "go", "name": parts[0], "version": parts[1], "indirect": "// indirect" in line, "ref": f"go.mod:{idx}"})
    for pkg_json in sorted(root.rglob("package.json")):
        if any(p in IGNORED_DIRS for p in pkg_json.parts):
            continue
        rel = pkg_json.relative_to(root).as_posix()
        try:
            d = json.loads(pkg_json.read_text(encoding="utf-8"))
        except Exception:
            continue
        for section in ("dependencies", "devDependencies"):
            for k, v in sorted((d.get(section) or {}).items()):
                deps.append({"ecosystem": "npm", "name": k, "version": str(v), "indirect": section == "devDependencies", "ref": rel})
    return sorted(deps, key=lambda x: (x["ecosystem"], x["name"], x["ref"]))


def scan_repo(root: pathlib.Path) -> dict:
    modules = collections.defaultdict(lambda: {"files": 0, "languages": set(), "lines": 0})
    entities = []
    actions = []
    data_schemas = []
    frontend_routes = []
    css_tokens = []
    lang_counts = collections.Counter()
    unsupported_exts = collections.Counter()
    skipped_secrets = []
    total_files = 0
    test_files = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(p in IGNORED_DIRS for p in rel_parts):
            continue
        rel = path.relative_to(root).as_posix()
        if path.name in SECRET_FILENAMES or path.suffix.lower() in SECRET_SUFFIXES:
            skipped_secrets.append(rel)
            continue
        total_files += 1
        ext = path.suffix.lower()
        lang = SUPPORTED_LANGS.get(ext)
        if not lang:
            if ext:
                unsupported_exts[ext] += 1
            continue
        lang_counts[lang] += 1
        top_mod = rel_parts[0] if len(rel_parts) > 1 else "."
        text = path.read_text(encoding="utf-8", errors="replace")
        line_cnt = text.count("\n") + 1
        modules[top_mod]["files"] += 1
        modules[top_mod]["languages"].add(lang)
        modules[top_mod]["lines"] += line_cnt

        is_test = ("_test." in path.name or ".test." in path.name or ".spec." in path.name or "tests/" in rel)
        if is_test:
            test_files += 1
            continue

        if lang == "go":
            for m in GO_ROUTE_RE.finditer(text):
                actions.append({"role": "http_route", "method": m.group(1), "target": m.group(2), "ref": f"{rel}:{line_of(text, m.start())}"})
            if rel.startswith("cmd/"):
                for m in GO_CMD_RE.finditer(text):
                    actions.append({"role": "cli_command", "method": "CLI", "target": m.group(1), "ref": f"{rel}:{line_of(text, m.start())}"})
            for m in GO_STRUCT_RE.finditer(text):
                entities.append({"role": "go_struct", "name": m.group(1), "ref": f"{rel}:{line_of(text, m.start())}"})
            for m in GO_MIGRATION_RE.finditer(text):
                data_schemas.append({"role": "sql_table", "table": m.group(1), "ref": f"{rel}:{line_of(text, m.start())}"})
        elif lang in ("javascript", "typescript", "svelte", "vue"):
            for m in SVELTE_ROUTE_RE.finditer(text):
                frontend_routes.append({"route": m.group(1), "component": m.group(2), "ref": f"{rel}:{line_of(text, m.start())}"})
            for m in JS_API_RE.finditer(text):
                actions.append({"role": "frontend_api_call", "method": "CLIENT", "target": m.group(1), "ref": f"{rel}:{line_of(text, m.start())}"})
            for m in JS_EXPORT_RE.finditer(text):
                entities.append({"role": "js_export", "name": m.group(1), "ref": f"{rel}:{line_of(text, m.start())}"})
        elif lang in ("scss", "css"):
            for m in CSS_VAR_RE.finditer(text):
                val = m.group(2).strip()
                if len(val) <= 80:
                    css_tokens.append({"token": m.group(1), "value": val, "ref": f"{rel}:{line_of(text, m.start())}"})
        elif lang == "python":
            for m in PY_ROUTE_RE.finditer(text):
                actions.append({"role": "http_route", "method": m.group(1).upper(), "target": m.group(2), "ref": f"{rel}:{line_of(text, m.start())}"})
            for m in PY_CLASS_RE.finditer(text):
                entities.append({"role": "py_class", "name": m.group(1), "ref": f"{rel}:{line_of(text, m.start())}"})
        elif lang == "rust":
            for m in RUST_STRUCT_RE.finditer(text):
                entities.append({"role": "rust_type", "name": m.group(1), "ref": f"{rel}:{line_of(text, m.start())}"})
        elif lang == "sql":
            for m in GO_MIGRATION_RE.finditer(text):
                data_schemas.append({"role": "sql_table", "table": m.group(1), "ref": f"{rel}:{line_of(text, m.start())}"})

    # Deduplicate deterministically
    def dedup(items, key_fn):
        seen = set()
        out = []
        for it in sorted(items, key=key_fn):
            k = key_fn(it)
            if k not in seen:
                seen.add(k)
                out.append(it)
        return out

    entities = dedup(entities, lambda x: (x["role"], x["name"], x["ref"]))
    actions = dedup(actions, lambda x: (x["role"], x["method"], x["target"], x["ref"]))
    data_schemas = dedup(data_schemas, lambda x: (x["role"], x["table"], x["ref"]))
    frontend_routes = dedup(frontend_routes, lambda x: (x["route"], x["component"], x["ref"]))
    css_tokens = dedup(css_tokens, lambda x: (x["token"], x["ref"]))
    dependencies = extract_dependencies(root)

    mod_list = [
        {"module": k, "files": v["files"], "lines": v["lines"], "languages": sorted(v["languages"])}
        for k, v in sorted(modules.items())
    ]

    # Loud Warnings (absorbed from cc-rsg & Reverse_Spec_and_PRD)
    loud_warnings = []
    supported_code_files = sum(lang_counts.values())
    code_like_unsupported = {k: v for k, v in unsupported_exts.items() if k in {".java", ".cs", ".php", ".rb", ".cbl", ".cob", ".swift", ".kt", ".cpp", ".c", ".h"}}
    if code_like_unsupported:
        loud_warnings.append({
            "code": "UNSUPPORTED_LANGUAGE_FILES",
            "severity": "warning",
            "message": f"Unsupported source extensions detected (manual inspection required): {dict(sorted(code_like_unsupported.items()))}",
        })
    extracted_total = len(entities) + len(actions) + len(data_schemas) + len(frontend_routes)
    if supported_code_files >= 20 and extracted_total < max(10, supported_code_files // 10):
        loud_warnings.append({
            "code": "LOW_PARSER_COVERAGE",
            "severity": "warning",
            "message": f"Extracted only {extracted_total} items across {supported_code_files} code files; inspect dynamic routing or framework conventions manually.",
        })
    if skipped_secrets:
        loud_warnings.append({
            "code": "SECRET_FILES_EXCLUDED",
            "severity": "info",
            "message": f"Excluded potential secret files from static extraction: {sorted(skipped_secrets)}",
        })

    return {
        "schema_version": "1.0.0",
        "root": str(root),
        "coverage_stats": {
            "total_files": total_files,
            "supported_code_files": supported_code_files,
            "test_files": test_files,
            "languages": dict(sorted(lang_counts.items())),
            "modules_count": len(mod_list),
            "entities_count": len(entities),
            "actions_count": len(actions),
            "data_schemas_count": len(data_schemas),
            "frontend_routes_count": len(frontend_routes),
            "css_tokens_count": len(css_tokens),
            "dependencies_count": len(dependencies),
            "recommended_min_inventory": max(20, supported_code_files // 20),
        },
        "loud_warnings": loud_warnings,
        "modules": mod_list,
        "entities": entities,
        "actions": actions,
        "data_schemas": data_schemas,
        "frontend_routes": frontend_routes,
        "css_tokens": css_tokens,
        "dependencies": dependencies,
    }


def write_facts_md(data: dict, out_path: pathlib.Path):
    st = data["coverage_stats"]
    lines = [
        "# Deterministic Static Fact Sheet",
        "",
        "Generated mechanically by `scripts/source_map.py`. LLM synthesis must remain grounded in these facts and live runtime observations.",
        "",
        "## Coverage Statistics",
        f"- Total files scanned: `{st['total_files']}`",
        f"- Supported code files: `{st['supported_code_files']}` (test files: `{st['test_files']}`)",
        f"- Languages: `{json.dumps(st['languages'])}`",
        f"- Extracted inventory: `{st['modules_count']}` modules, `{st['entities_count']}` entities, `{st['actions_count']}` actions/routes, `{st['data_schemas_count']}` SQL tables, `{st['frontend_routes_count']}` frontend routes, `{st['css_tokens_count']}` CSS variables, `{st['dependencies_count']}` dependencies",
        "",
    ]
    if data["loud_warnings"]:
        lines.append("## Loud Warnings")
        for w in data["loud_warnings"]:
            lines.append(f"- **[{w['code']}]** ({w['severity']}): {w['message']}")
        lines.append("")

    lines += ["## 1. Modules", "| Module | Files | Lines | Languages |", "|---|---:|---:|---|"]
    for m in data["modules"]:
        lines.append(f"| `{m['module']}` | {m['files']} | {m['lines']} | {', '.join(m['languages'])} |")
    lines += ["", "## 2. HTTP Routes & CLI Commands (Sample Top 80)", "| Role | Method | Target | Ref |", "|---|---|---|---|"]
    for a in data["actions"][:80]:
        lines.append(f"| `{a['role']}` | `{a['method']}` | `{a['target']}` | `[REF: {a['ref']}]` |")
    lines += ["", "## 3. Frontend Routes", "| Route | Component | Ref |", "|---|---|---|"]
    for r in data["frontend_routes"][:60]:
        lines.append(f"| `{r['route']}` | `{r['component']}` | `[REF: {r['ref']}]` |")
    lines += ["", "## 4. SQL Tables Detected in Migrations/Code", "| Table | Ref |", "|---|---|"]
    for t in data["data_schemas"][:60]:
        lines.append(f"| `{t['table']}` | `[REF: {t['ref']}]` |")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Deterministic multi-language source map extractor")
    ap.add_argument("source_dir")
    ap.add_argument("--out", required=True, help="Output JSON path")
    ap.add_argument("--facts", required=True, help="Output deterministic facts Markdown path")
    args = ap.parse_args()

    root = pathlib.Path(args.source_dir).resolve()
    data = scan_repo(root)
    out_json = pathlib.Path(args.out)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    out_md = pathlib.Path(args.facts)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    write_facts_md(data, out_md)
    print(json.dumps({"status": "ok", "stats": data["coverage_stats"], "loud_warnings": len(data["loud_warnings"])}, indent=2))


if __name__ == "__main__":
    main()
