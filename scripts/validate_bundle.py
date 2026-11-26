#!/usr/bin/env python3
"""
Dual Mechanical Quality Gate Validator for spec-anything.
Enforces BOTH:
  - Static quality gates (12 fixed deliverables, [REF:] citations, ## Sources Read,
    --max-macro-ratio anti-handwaving guard, structure-only Mermaid contract)
  - Dynamic/contract/parity gates (JSON Schema checks for 03/06/07, Feature ID FK integrity,
    07 direct consumption of 06 JSONL, 09 OpenAPI/Schema/SQLite DDL syntax, REA audit,
    secret-guard clean pass, and SHA256SUMS.txt verification).
"""
import argparse
import hashlib
import json
import pathlib
import re
import sqlite3
import sys

try:
    import jsonschema
except ImportError:
    jsonschema = None

from secret_guard import scan_dir as scan_secrets

DELIVERABLES = [
    ("01", "01_PRD.md"),
    ("02", "02_SDD.md"),
    ("03", "03_scope_matrix.md"),
    ("04", "04_reproduction_env.md"),
    ("05", "05_ui_reference.md"),
    ("06", "06_behavior_evidence.md"),
    ("07", "07_parity_tests.md"),
    ("08", "08_implementation_blueprint.md"),
    ("09", "09_contracts.md"),
    ("10", "10_execution_and_state.md"),
    ("11", "11_ui_implementation.md"),
    ("12", "12_implementation_sequence.md"),
]

NARRATIVE_DOCS_NEEDING_SOURCES = [
    "01_PRD.md",
    "02_SDD.md",
    "08_implementation_blueprint.md",
    "10_execution_and_state.md",
    "11_ui_implementation.md",
    "12_implementation_sequence.md",
]

REF_RE = re.compile(r"\[REF:\s*[^\]]+\]")
MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n(.*?)```", re.S)
MERMAID_FORBIDDEN_RE = re.compile(r"(?:^|\s)(?:style\s+\S+\s+[^\n]*fill:|classDef\s+\S+\s+[^\n]*(?:fill:|stroke:|color:)|stroke:#|fill:#|color:#)", re.I)


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_schema(schema_dir: pathlib.Path, name: str):
    return json.loads((schema_dir / name).read_text(encoding="utf-8"))


def validate_bundle(bundle_dir: pathlib.Path, schema_dir: pathlib.Path, tier: str, max_macro_ratio: float, min_refs: int, verify_checksums: bool) -> dict:
    checks = []

    def record(gate: str, group: str, passed: bool, detail: str):
        checks.append({"gate": gate, "group": group, "passed": passed, "detail": detail})

    # --- STATIC GATE 1: Exact 01..12 deliverables, no 13+ ---
    missing = [fn for _, fn in DELIVERABLES if not (bundle_dir / fn).exists()]
    illegal_nums = sorted(p.name for p in bundle_dir.glob("*.md") if re.match(r"^(?:1[3-9]|[2-9][0-9])_", p.name))
    record("S1_fixed_12_deliverables", "static", (not missing and not illegal_nums),
           f"missing={missing}, illegal_extra_numbers={illegal_nums}")

    # --- STATIC GATE 2: Citation density [REF: ...] & ## Sources Read ---
    low_ref_docs = []
    missing_sources_docs = []
    for fn in NARRATIVE_DOCS_NEEDING_SOURCES:
        fp = bundle_dir / fn
        if not fp.exists():
            continue
        txt = fp.read_text(encoding="utf-8")
        refs = REF_RE.findall(txt)
        if len(refs) < min_refs:
            low_ref_docs.append(f"{fn}({len(refs)}<{min_refs})")
        if "## Sources Read" not in txt:
            missing_sources_docs.append(fn)
    record("S2_ref_citations_density", "static", not low_ref_docs, f"min_refs={min_refs}, below_threshold={low_ref_docs}")
    record("S3_sources_read_heading", "static", not missing_sources_docs, f"missing_sources_read={missing_sources_docs}")

    # --- STATIC GATE 4: Structure-only Mermaid contract ---
    mermaid_violations = []
    mermaid_total = 0
    for fp in sorted(bundle_dir.glob("*.md")):
        txt = fp.read_text(encoding="utf-8")
        for idx, blk in enumerate(MERMAID_BLOCK_RE.findall(txt), 1):
            mermaid_total += 1
            if MERMAID_FORBIDDEN_RE.search(blk):
                mermaid_violations.append(f"{fp.name}#mermaid-{idx}")
    record("S4_structure_only_mermaid", "static", (mermaid_total >= 1 and not mermaid_violations),
           f"diagrams={mermaid_total}, color_violations={mermaid_violations}")

    # --- DYNAMIC GATE 5: 03 Feature Matrix schema + anti-handwaving --max-macro-ratio ---
    f_path = bundle_dir / "03_scope" / "features.json"
    feature_ids = set()
    features_data = None
    if f_path.exists():
        features_data = json.loads(f_path.read_text(encoding="utf-8"))
        schema_err = None
        if jsonschema:
            try:
                jsonschema.validate(features_data, load_schema(schema_dir, "feature_matrix.schema.json"))
            except Exception as e:
                schema_err = str(e).splitlines()[0]
        feats = features_data.get("features", [])
        feature_ids = {f["feature_id"] for f in feats}
        macro_cnt = sum(1 for f in feats if f.get("is_macro_group"))
        macro_ratio = (macro_cnt / len(feats)) if feats else 1.0
        record("S5_feature_matrix_schema_and_macro_ratio", "static",
               (schema_err is None and len(feats) >= 10 and macro_ratio <= max_macro_ratio),
               f"features={len(feats)}, macro_ratio={macro_ratio:.3f} (max={max_macro_ratio}), schema_err={schema_err}")
    else:
        record("S5_feature_matrix_schema_and_macro_ratio", "static", False, "03_scope/features.json missing")

    # --- DYNAMIC GATE 6: 06 JSONL schema & FK integrity ---
    ev_path = bundle_dir / "06_evidence" / "ledger.jsonl"
    evidence_ids = set()
    ev_records = []
    ev_errors = []
    if ev_path.exists():
        ev_schema = load_schema(schema_dir, "evidence.schema.json") if jsonschema else None
        for idx, raw in enumerate(ev_path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
                ev_records.append(rec)
                evidence_ids.add(rec["evidence_id"])
                if jsonschema and ev_schema:
                    jsonschema.validate(rec, ev_schema)
                if rec["feature_id"] not in feature_ids:
                    ev_errors.append(f"line {idx}: orphan feature_id {rec['feature_id']}")
            except Exception as e:
                ev_errors.append(f"line {idx}: {str(e).splitlines()[0]}")
        observed_cnt = sum(1 for r in ev_records if r.get("status") == "observed")
        tier_ok = (observed_cnt > 0) if tier in ("T2", "T3") else True
        record("D1_evidence_jsonl_schema_and_fk", "dynamic",
               (len(ev_records) > 0 and not ev_errors and tier_ok),
               f"records={len(ev_records)}, observed={observed_cnt}, errors={ev_errors[:5]}")
    else:
        record("D1_evidence_jsonl_schema_and_fk", "dynamic", False, "06_evidence/ledger.jsonl missing")

    # --- DYNAMIC GATE 7: 05 Screens & 11 UI tokens (T3) ---
    screens_path = bundle_dir / "05_ui" / "screens.json"
    screen_ids = set()
    missing_pngs = []
    if screens_path.exists():
        sdata = json.loads(screens_path.read_text(encoding="utf-8"))
        for sc in sdata.get("screens", []):
            screen_ids.add(sc["screen_id"])
            img = bundle_dir / "05_ui" / sc["file"]
            if not img.exists() or img.stat().st_size == 0:
                missing_pngs.append(sc["file"])
    tokens_path = bundle_dir / "11_ui" / "tokens.json"
    if tier == "T3":
        record("D2_ui_screenshots_and_tokens", "dynamic",
               (len(screen_ids) >= 4 and not missing_pngs and tokens_path.exists()),
               f"screens={len(screen_ids)}, missing_pngs={missing_pngs}, tokens_exists={tokens_path.exists()}")
    else:
        record("D2_ui_screenshots_and_tokens", "dynamic", True, f"optional for {tier} (screens={len(screen_ids)})")

    # --- DYNAMIC GATE 8: Cross-FK check from 03 features -> 05/06 ---
    fk_broken = []
    if features_data:
        for f in features_data["features"]:
            for eid in f.get("evidence_ids", []):
                if eid not in evidence_ids:
                    fk_broken.append(f"{f['feature_id']}->{eid}")
            for sid in f.get("screen_ids", []):
                if screen_ids and sid not in screen_ids:
                    fk_broken.append(f"{f['feature_id']}->{sid}")
    record("D3_feature_cross_fk_integrity", "dynamic", not fk_broken, f"broken_fks={fk_broken[:8]}")

    # --- DYNAMIC GATE 9: 07 Parity Tests read 06 JSONL directly + Baseline PASS ---
    report_path = bundle_dir / "07_tests" / "parity_report.json"
    test_scripts = list((bundle_dir / "07_tests").glob("*.py")) + list((bundle_dir / "07_tests").glob("*.mjs"))
    reads_ledger = any("ledger.jsonl" in p.read_text(encoding="utf-8", errors="replace") for p in test_scripts)
    if report_path.exists():
        rdata = json.loads(report_path.read_text(encoding="utf-8"))
        r_err = None
        if jsonschema:
            try:
                jsonschema.validate(rdata, load_schema(schema_dir, "parity_report.schema.json"))
            except Exception as e:
                r_err = str(e).splitlines()[0]
        summ = rdata.get("summary", {})
        orphan_tc = [c["test_id"] for c in rdata.get("cases", []) if c["evidence_id"] not in evidence_ids or c["feature_id"] not in feature_ids]
        ok = (reads_ledger and r_err is None and summ.get("failed", 1) == 0 and summ.get("passed", 0) > 0 and not orphan_tc)
        record("D4_parity_harness_consumes_06_and_passes", "dynamic", ok,
               f"reads_ledger={reads_ledger}, summary={summ}, orphan_cases={orphan_tc}, schema_err={r_err}")
    else:
        record("D4_parity_harness_consumes_06_and_passes", "dynamic", False, "07_tests/parity_report.json missing")

    # --- DYNAMIC GATE 10: 09 Contracts (OpenAPI JSON, JSON Schemas, SQLite DDL execution) ---
    cdir = bundle_dir / "09_contracts"
    contract_errs = []
    openapi_ok = False
    schema_ok = False
    sql_ok = False
    if cdir.exists():
        for jp in sorted(cdir.glob("*.json")):
            try:
                obj = json.loads(jp.read_text(encoding="utf-8"))
                if "openapi" in obj:
                    openapi_ok = True
                if "$schema" in obj or ("type" in obj and "properties" in obj):
                    schema_ok = True
            except Exception as e:
                contract_errs.append(f"{jp.name}: {e}")
        for sp in sorted(cdir.glob("*.sql")):
            try:
                con = sqlite3.connect(":memory:")
                con.executescript(sp.read_text(encoding="utf-8"))
                con.close()
                sql_ok = True
            except Exception as e:
                contract_errs.append(f"{sp.name}: {e}")
    record("D5_machine_contracts_valid", "dynamic", ((openapi_ok or schema_ok) and not contract_errs),
           f"openapi_ok={openapi_ok}, schema_ok={schema_ok}, sql_exec_ok={sql_ok}, errors={contract_errs}")

    # --- DYNAMIC GATE 11: 04 Release REA Audit (T3) ---
    rea_path = bundle_dir / "04_environment" / "release_audit.json"
    if tier == "T3":
        rea_ok = False
        detail = "04_environment/release_audit.json missing"
        if rea_path.exists():
            ra = json.loads(rea_path.read_text(encoding="utf-8"))
            bin_sha = (ra.get("binary") or {}).get("sha256")
            arch_ver = (ra.get("archive") or {}).get("upstream_checksum_verified")
            rea_ok = bool(bin_sha and len(bin_sha) == 64 and arch_ver is not False)
            detail = f"binary_sha256={bool(bin_sha)}, archive_checksum_verified={arch_ver}"
        record("D6_release_rea_audit", "dynamic", rea_ok, detail)
    else:
        record("D6_release_rea_audit", "dynamic", True, f"optional for {tier}")

    # --- SECURITY GATE 12: Secret Guard Clean Pass ---
    secret_hits = scan_secrets(bundle_dir, redact=False)
    record("SEC1_secret_guard_clean", "security", len(secret_hits) == 0, f"hits={len(secret_hits)}")

    # --- INTEGRITY GATE 13: SHA256SUMS.txt ---
    if verify_checksums:
        sums_path = bundle_dir / "SHA256SUMS.txt"
        bad = []
        checked = 0
        if sums_path.exists():
            for ln in sums_path.read_text(encoding="utf-8").splitlines():
                parts = ln.strip().split("  ", 1)
                if len(parts) != 2:
                    continue
                expected, rel = parts
                target = bundle_dir / rel
                checked += 1
                if not target.exists() or sha256_file(target) != expected:
                    bad.append(rel)
            record("INT1_sha256sums_verified", "integrity", (checked > 0 and not bad), f"checked={checked}, mismatches={bad[:5]}")
        else:
            record("INT1_sha256sums_verified", "integrity", False, "SHA256SUMS.txt missing")

    passed_cnt = sum(1 for c in checks if c["passed"])
    return {
        "bundle": str(bundle_dir),
        "tier": tier,
        "all_passed": (passed_cnt == len(checks)),
        "passed": passed_cnt,
        "total": len(checks),
        "checks": checks,
    }


def main():
    ap = argparse.ArgumentParser(description="spec-anything Dual Mechanical Quality Gate Validator")
    ap.add_argument("bundle_dir")
    ap.add_argument("--schemas", default=None, help="Schema directory (defaults to ../schemas relative to script)")
    ap.add_argument("--tier", choices=["T1", "T2", "T3"], default="T3")
    ap.add_argument("--max-macro-ratio", type=float, default=0.15)
    ap.add_argument("--min-refs", type=int, default=3)
    ap.add_argument("--verify-checksums", action="store_true")
    args = ap.parse_args()

    sdir = pathlib.Path(args.schemas) if args.schemas else pathlib.Path(__file__).resolve().parent.parent / "schemas"
    res = validate_bundle(pathlib.Path(args.bundle_dir).resolve(), sdir, args.tier, args.max_macro_ratio, args.min_refs, args.verify_checksums)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if not res["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
