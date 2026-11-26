#!/usr/bin/env python3
"""Dual static + dynamic quality gate validator for spec-anything bundles.

Combines:
- cc-rsg coverage-check.py static discipline (required files, [REF:] density,
  source-map coverage, Question Bank integrity, state machine consistency)
- Reverse_Spec_and_PRD secret_guard zero-leak enforcement
- spec-anything / REA dynamic contract & parity checks (03 Feature ID foreign-key
  integrity across 01-12, 05 screenshot existence & SHA-256, 06 JSONL schema
  validation, 07 parity test direct 06 consumption + PASS report, 09 OpenAPI JSON
  and SQLite DDL execution test, SHA256SUMS verification).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

from secret_guard import scan_bundle

REQUIRED_12_PREFIXES = [f"{i:02d}_" for i in range(1, 13)]
FEATURE_ID_RE = re.compile(r"\bF-\d{3}\b")
REF_RE = re.compile(r"\[REF:\s*[^:\]]+:\d+(?:-\d+)?\]")
VALID_EPISTEMIC = {"observed", "code-verified", "inferred", "assumed", "unverified"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_all(bundle_dir: Path, verify_checksums: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(cid: str, name: str, passed: bool, detail: Any) -> None:
        checks.append({"check_id": cid, "name": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    # G-01: Fixed 01..12 markdown files present and non-empty
    md_files: dict[str, Path] = {}
    missing_12: list[str] = []
    for pref in REQUIRED_12_PREFIXES:
        matches = sorted(p for p in bundle_dir.glob(f"{pref}*.md") if p.is_file())
        if matches and matches[0].stat().st_size > 200:
            md_files[pref] = matches[0]
        else:
            missing_12.append(pref)
    add("G-01", "fixed_12_artifacts_present", len(missing_12) == 0, {"found": len(md_files), "missing": missing_12})

    # G-02: .spec-anything state machine & source-map presence (cc-rsg discipline)
    state_p = bundle_dir / ".spec-anything/state.json"
    goal_p = bundle_dir / ".spec-anything/goal.json"
    smap_p = bundle_dir / ".spec-anything/source-map.json"
    qbank_p = bundle_dir / ".spec-anything/questions.json"
    state_ok = all(p.is_file() for p in (state_p, goal_p, smap_p, qbank_p))
    smap_units = 0
    if smap_p.is_file():
        smap = json.loads(smap_p.read_text(encoding="utf-8"))
        smap_units = smap.get("stats", {}).get("total_units", 0)
    add("G-02", "state_machine_and_source_map", state_ok and smap_units >= 50, {"files_ok": state_ok, "source_map_units": smap_units})

    # G-03: 03 Feature ID master table foreign-key integrity across 01-12 and 06/07
    master_ids: set[str] = set()
    if "03_" in md_files:
        master_ids = set(FEATURE_ID_RE.findall(md_files["03_"].read_text(encoding="utf-8")))
    orphan_refs: dict[str, list[str]] = {}
    for pref, mpath in sorted(md_files.items()):
        if pref == "03_":
            continue
        ids = set(FEATURE_ID_RE.findall(mpath.read_text(encoding="utf-8")))
        orphans = sorted(ids - master_ids)
        if orphans:
            orphan_refs[mpath.name] = orphans
    add("G-03", "feature_id_foreign_key_integrity", len(master_ids) >= 10 and not orphan_refs, {"master_feature_ids": sorted(master_ids), "orphans": orphan_refs})

    # G-04: Static [REF: path:line] citation density across core spec docs (cc-rsg discipline)
    ref_counts: dict[str, int] = {}
    for pref in ("01_", "02_", "03_", "08_", "10_"):
        if pref in md_files:
            ref_counts[md_files[pref].name] = len(REF_RE.findall(md_files[pref].read_text(encoding="utf-8")))
    total_refs = sum(ref_counts.values())
    add("G-04", "source_ref_citation_density", total_refs >= 25 and all(v >= 3 for v in ref_counts.values()), {"total_refs": total_refs, "by_doc": ref_counts})

    # G-05: 05 screenshots exist and match ui_measurements SHA-256
    ui_meta_p = bundle_dir / "06_evidence/ui_measurements_v1.0.0.json"
    ui_bad: list[str] = []
    ui_count = 0
    if ui_meta_p.is_file():
        ui_recs = json.loads(ui_meta_p.read_text(encoding="utf-8"))
        ui_count = len(ui_recs)
        for r in ui_recs:
            sp = bundle_dir / "05_screenshots" / r["filename"]
            if not sp.is_file() or sha256_file(sp) != r["sha256"]:
                ui_bad.append(r["filename"])
    else:
        ui_bad.append("missing_ui_measurements_json")
    add("G-05", "ui_screenshots_integrity", ui_count >= 6 and not ui_bad, {"screenshots_verified": ui_count, "mismatches": ui_bad})

    # G-06: 06 JSONL machine-readable evidence schema + epistemic status + REA summary
    ev_p = bundle_dir / "06_evidence/evidence_v1.0.0.jsonl"
    rea_p = bundle_dir / "06_evidence/rea_distribution_summary_v1.0.0.json"
    ev_errors: list[str] = []
    ev_count = 0
    required_ev_keys = {
        "evidence_id", "feature_id", "source_ref", "pinned_commit", "artifact_sha256",
        "tool_and_env", "input_and_precondition", "observed_output", "status", "limitations", "linked_artifacts",
    }
    if ev_p.is_file():
        for idx, ln in enumerate(ev_p.read_text(encoding="utf-8").splitlines(), 1):
            if not ln.strip():
                continue
            ev_count += 1
            obj = json.loads(ln)
            missing_k = required_ev_keys - set(obj.keys())
            if missing_k:
                ev_errors.append(f"line_{idx}_missing_{sorted(missing_k)}")
            if obj.get("status") not in VALID_EPISTEMIC:
                ev_errors.append(f"line_{idx}_invalid_status_{obj.get('status')}")
            if master_ids and obj.get("feature_id") not in master_ids:
                ev_errors.append(f"line_{idx}_orphan_feature_{obj.get('feature_id')}")
    else:
        ev_errors.append("missing_evidence_jsonl")
    rea_ok = False
    if rea_p.is_file():
        rea = json.loads(rea_p.read_text(encoding="utf-8"))
        rea_ok = bool(rea.get("artifacts", {}).get("release_archive", {}).get("checksums_match"))
    add("G-06", "evidence_jsonl_and_rea_summary", ev_count >= 10 and not ev_errors and rea_ok, {"records": ev_count, "rea_checksums_match": rea_ok, "errors": ev_errors})

    # G-07: 07 parity harness directly consumes 06 JSONL and latest verification result is PASS
    test_p = bundle_dir / "07_tests/test_memos_parity.py"
    res_p = bundle_dir / "07_tests/verification_results_v1.0.0.json"
    reads_06 = False
    if test_p.is_file():
        tsrc = test_p.read_text(encoding="utf-8")
        reads_06 = ("load_evidence" in tsrc) and ("evidence_v1.0.0.jsonl" in tsrc or "--evidence" in tsrc)
    res_pass = False
    res_summary: dict[str, Any] = {}
    if res_p.is_file():
        res = json.loads(res_p.read_text(encoding="utf-8"))
        res_pass = res.get("overall_status") == "PASS" and res.get("failed") == 0 and res.get("passed", 0) >= 10
        res_summary = {"overall_status": res.get("overall_status"), "passed": res.get("passed"), "failed": res.get("failed")}
    add("G-07", "parity_harness_consumes_06_and_passes", reads_06 and res_pass, {"reads_06_directly": reads_06, "verification_report": res_summary})

    # G-08: 09 contracts valid JSON + SQLite DDL executes cleanly in memory
    oa_p = bundle_dir / "09_contracts/openapi_v1.0.0.json"
    sql_p = bundle_dir / "09_contracts/schema_v1.0.0.sql"
    ev_sch_p = bundle_dir / "09_contracts/evidence.schema.json"
    err_sch_p = bundle_dir / "09_contracts/events_and_errors.schema.json"
    contracts_ok = True
    sql_tables = 0
    contract_err = ""
    try:
        oa = json.loads(oa_p.read_text(encoding="utf-8"))
        assert oa.get("openapi", "").startswith("3.") and len(oa.get("paths", {})) >= 8
        json.loads(ev_sch_p.read_text(encoding="utf-8"))
        json.loads(err_sch_p.read_text(encoding="utf-8"))
        conn = sqlite3.connect(":memory:")
        conn.executescript(sql_p.read_text(encoding="utf-8"))
        sql_tables = len(conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall())
        conn.close()
        assert sql_tables >= 10
    except Exception as exc:
        contracts_ok = False
        contract_err = str(exc)
    add("G-08", "contracts_openapi_json_and_sqlite_ddl", contracts_ok, {"sqlite_tables_created_in_memory": sql_tables, "error": contract_err})

    # G-09: Secret guard zero findings (Reverse_Spec_and_PRD discipline)
    sec = scan_bundle(bundle_dir)
    add("G-09", "secret_guard_zero_leaks", sec["status"] == "PASS", {"scanned_files": sec["scanned_files"], "findings_count": sec["findings_count"]})

    # G-10: SHA256SUMS manifest integrity (when enabled)
    if verify_checksums:
        cs_p = bundle_dir / "SHA256SUMS_v1.0.0.txt"
        bad_cs: list[str] = []
        checked_cs = 0
        if cs_p.is_file():
            for ln in cs_p.read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                expected_h, rel = ln.split("  ", 1)
                fp = bundle_dir / rel.strip()
                checked_cs += 1
                if not fp.is_file() or sha256_file(fp) != expected_h:
                    bad_cs.append(rel.strip())
        else:
            bad_cs.append("missing_SHA256SUMS_v1.0.0.txt")
        add("G-10", "sha256sums_manifest_integrity", checked_cs >= 20 and not bad_cs, {"checked_files": checked_cs, "mismatches": bad_cs})

    failed = sum(1 for c in checks if c["status"] == "FAIL")
    return {
        "schema_version": "1.0.0",
        "bundle_dir": str(bundle_dir),
        "total_gates": len(checks),
        "passed": len(checks) - failed,
        "failed": failed,
        "overall_status": "PASS" if failed == 0 else "FAIL",
        "gates": checks,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate spec-anything bundle across static, secret, contract, and parity gates")
    ap.add_argument("--bundle-dir", required=True)
    ap.add_argument("--verify-checksums", action="store_true")
    ap.add_argument("--report-out", default="")
    args = ap.parse_args()

    res = check_all(Path(args.bundle_dir).resolve(), args.verify_checksums)
    if args.report_out:
        out = Path(args.report_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
