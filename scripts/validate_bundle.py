#!/usr/bin/env python3
"""
Dual Mechanical Quality Gate & Governance Validator for spec-anything (v4.1.0).
Enforces:
  - Static gates (S1..S5): 12 fixed deliverables, [REF:] citations, ## Sources Read,
    structure-only Mermaid, 03 Feature Matrix schema + --max-macro-ratio
  - Dynamic/contract/parity gates (D1..D6): 06 JSONL schema & FK, 05/11 UI & tokens,
    03 cross-FK, 07 direct consumption of 06 + baseline PASS, 09 OpenAPI/Schema/SQLite
    execution, 04 Release REA audit
  - Security & Governance gates (SEC1, GOV1, GOV2):
      * SEC1: 3-tier secret confidence guard (blocks high-confidence leaks only)
      * GOV1: Deterministic Machine Ceiling + AI Downgrade-Only enforcement + Anti-Slop
              placeholder rejection (N/A, TODO, TBD, none, -, null, empty payloads)
      * GOV2: 3-Axis Bijective Tool Coverage validation (when 04_environment/tool_coverage.json
              exists) + non-blocking [AI-Safety] 4-category prompt-injection advisory scan
  - Integrity gate (INT1): SHA256SUMS.txt verification
  - Semantic exit code 42 (with --strict-ceiling) when all hard gates pass but machine
    ceiling forbids claiming full coverage.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sqlite3
import sys
import tempfile

try:
    import jsonschema
except ImportError:
    jsonschema = None

from secret_guard import scan_dir as scan_secrets, scan_prompt_injections

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
MERMAID_FORBIDDEN_RE = re.compile(
    r"(?:^|\s)(?:style\s+\S+\s+[^\n]*fill:|classDef\s+\S+\s+[^\n]*(?:fill:|stroke:|color:)|stroke:#|fill:#|color:#)",
    re.I,
)

SLOP_STRINGS = {"", "-", "--", "n/a", "na", "none", "null", "todo", "tbd", "placeholder", "unknown", "fixme"}
GRADE_ORDER = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_schema(schema_dir: pathlib.Path, name: str):
    return json.loads((schema_dir / name).read_text(encoding="utf-8"))


def is_slop_value(val) -> bool:
    if val is None:
        return True
    if isinstance(val, str):
        return val.strip().lower() in SLOP_STRINGS
    if isinstance(val, (list, dict)):
        return len(val) == 0
    return False


def compute_machine_ceiling(
    observed_ratio: float,
    failed_cases: int,
    degraded_tools: int,
    missing_tools: int,
    did_real_work: bool,
    tier: str,
) -> dict:
    """Deterministic upper bound on allowed grade and full-coverage claims (AI may only hold or downgrade)."""
    reasons = []
    if not did_real_work:
        reasons.append("no_verified_runtime_or_parity_work")
        grade = "F"
    elif failed_cases > 0:
        reasons.append(f"parity_failures={failed_cases}")
        grade = "D"
    elif degraded_tools > 0:
        reasons.append(f"degraded_tools={degraded_tools}")
        grade = "B"
    elif tier in ("T2", "T3") and observed_ratio < 0.5:
        reasons.append(f"low_observed_ratio={observed_ratio:.2f}")
        grade = "B"
    elif missing_tools > 0:
        reasons.append(f"optional_or_missing_tools={missing_tools}")
        grade = "A"
    else:
        grade = "A"

    can_claim_full = (
        did_real_work
        and failed_cases == 0
        and degraded_tools == 0
        and missing_tools == 0
        and (observed_ratio >= 0.5 if tier in ("T2", "T3") else True)
    )
    return {
        "grade_ceiling": grade,
        "can_claim_full_coverage": can_claim_full,
        "did_real_work": did_real_work,
        "observed_ratio": round(observed_ratio, 4),
        "degraded_tools": degraded_tools,
        "missing_tools": missing_tools,
        "reasons": reasons,
    }


def validate_tool_coverage_manifest(cov_path: pathlib.Path, schema_dir: pathlib.Path) -> tuple[bool, dict]:
    """Validate 3-axis tool_coverage.json and bijective missing_tools / must_rerun_tools partitioning."""
    cov = json.loads(cov_path.read_text(encoding="utf-8"))
    errors = []
    schema_path = schema_dir / "tool_coverage.schema.json"
    if jsonschema and schema_path.exists():
        try:
            jsonschema.validate(cov, load_schema(schema_dir, "tool_coverage.schema.json"))
        except Exception as e:
            errors.append(f"schema: {str(e).splitlines()[0]}")

    missing_set = set(cov.get("missing_tools", []))
    rerun_set = set(cov.get("must_rerun_tools", []))
    overlap = sorted(missing_set & rerun_set)
    if overlap:
        errors.append(f"non_bijective_overlap={overlap}")

    expected_accounted = set()
    degraded_cnt = 0
    for t in cov.get("tools", []):
        if t.get("applicability") != "applicable":
            continue
        if t.get("evidence_quality") == "degraded":
            degraded_cnt += 1
        if t.get("execution") != "executed_primary":
            expected_accounted.add(t["tool"])

    union_set = missing_set | rerun_set
    unaccounted = sorted(expected_accounted - union_set)
    extra = sorted(union_set - expected_accounted)
    if unaccounted:
        errors.append(f"unaccounted_non_primary_tools={unaccounted}")
    if extra:
        errors.append(f"primary_or_unknown_tools_in_sets={extra}")

    metrics = cov.get("metrics", {})
    if "terminal_state_completion_rate" not in metrics or "primary_tool_success_rate" not in metrics:
        errors.append("missing_separate_completion_and_primary_rates")

    return (len(errors) == 0), {
        "present": True,
        "errors": errors,
        "degraded_tools": degraded_cnt,
        "missing_tools_count": len(missing_set),
        "must_rerun_count": len(rerun_set),
        "metrics": metrics,
    }


def validate_bundle(
    bundle_dir: pathlib.Path,
    schema_dir: pathlib.Path,
    tier: str,
    max_macro_ratio: float,
    min_refs: int,
    verify_checksums: bool,
) -> dict:
    checks = []

    def record(gate: str, group: str, passed: bool, detail: str):
        checks.append({"gate": gate, "group": group, "passed": passed, "detail": detail})

    # --- STATIC GATE S1: Exact 01..12 deliverables, no 13+ ---
    missing = [fn for _, fn in DELIVERABLES if not (bundle_dir / fn).exists()]
    illegal_nums = sorted(p.name for p in bundle_dir.glob("*.md") if re.match(r"^(?:1[3-9]|[2-9][0-9])_", p.name))
    record("S1_fixed_12_deliverables", "static", (not missing and not illegal_nums),
           f"missing={missing}, illegal_extra_numbers={illegal_nums}")

    # --- STATIC GATES S2 & S3: Citation density [REF: ...] & ## Sources Read ---
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

    # --- STATIC GATE S4: Structure-only Mermaid contract ---
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

    # --- STATIC GATE S5: 03 Feature Matrix schema + anti-handwaving --max-macro-ratio ---
    f_path = bundle_dir / "03_scope" / "features.json"
    feature_ids = set()
    features_data = None
    slop_hits = []
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
        for f in feats:
            fid = f.get("feature_id", "?")
            if is_slop_value(f.get("name")):
                slop_hits.append(f"{fid}.name")
            if is_slop_value(f.get("entrypoint")):
                slop_hits.append(f"{fid}.entrypoint")
            if is_slop_value(f.get("source_refs")) or any(is_slop_value(r) for r in f.get("source_refs", [])):
                slop_hits.append(f"{fid}.source_refs")
        macro_cnt = sum(1 for f in feats if f.get("is_macro_group"))
        macro_ratio = (macro_cnt / len(feats)) if feats else 1.0
        record("S5_feature_matrix_schema_and_macro_ratio", "static",
               (schema_err is None and len(feats) >= 10 and macro_ratio <= max_macro_ratio),
               f"features={len(feats)}, macro_ratio={macro_ratio:.3f} (max={max_macro_ratio}), schema_err={schema_err}")
    else:
        record("S5_feature_matrix_schema_and_macro_ratio", "static", False, "03_scope/features.json missing")

    # --- DYNAMIC GATE D1: 06 JSONL schema & FK integrity ---
    ev_path = bundle_dir / "06_evidence" / "ledger.jsonl"
    evidence_ids = set()
    ev_records = []
    ev_errors = []
    observed_cnt = 0
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
                for fld in ("source_location", "observation_tool", "observed_output"):
                    if is_slop_value(rec.get(fld)):
                        slop_hits.append(f"{rec.get('evidence_id', f'line-{idx}')}.{fld}")
            except Exception as e:
                ev_errors.append(f"line {idx}: {str(e).splitlines()[0]}")
        observed_cnt = sum(1 for r in ev_records if r.get("status") == "observed")
        tier_ok = (observed_cnt > 0) if tier in ("T2", "T3") else True
        record("D1_evidence_jsonl_schema_and_fk", "dynamic",
               (len(ev_records) > 0 and not ev_errors and tier_ok),
               f"records={len(ev_records)}, observed={observed_cnt}, errors={ev_errors[:5]}")
    else:
        record("D1_evidence_jsonl_schema_and_fk", "dynamic", False, "06_evidence/ledger.jsonl missing")

    # --- DYNAMIC GATE D2: 05 Screens & 11 UI tokens (T3) ---
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

    # --- DYNAMIC GATE D3: Cross-FK check from 03 features -> 05/06 ---
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

    # --- DYNAMIC GATE D4: 07 Parity Tests read 06 JSONL directly + Baseline PASS ---
    report_path = bundle_dir / "07_tests" / "parity_report.json"
    test_scripts = list((bundle_dir / "07_tests").glob("*.py")) + list((bundle_dir / "07_tests").glob("*.mjs"))
    reads_ledger = any("ledger.jsonl" in p.read_text(encoding="utf-8", errors="replace") for p in test_scripts)
    rdata = None
    parity_passed = 0
    parity_failed = 1
    if report_path.exists():
        rdata = json.loads(report_path.read_text(encoding="utf-8"))
        r_err = None
        if jsonschema:
            try:
                jsonschema.validate(rdata, load_schema(schema_dir, "parity_report.schema.json"))
            except Exception as e:
                r_err = str(e).splitlines()[0]
        summ = rdata.get("summary", {})
        parity_passed = int(summ.get("passed", 0))
        parity_failed = int(summ.get("failed", 1))
        orphan_tc = [
            c["test_id"] for c in rdata.get("cases", [])
            if c["evidence_id"] not in evidence_ids or c["feature_id"] not in feature_ids
        ]
        ok = (reads_ledger and r_err is None and parity_failed == 0 and parity_passed > 0 and not orphan_tc)
        record("D4_parity_harness_consumes_06_and_passes", "dynamic", ok,
               f"reads_ledger={reads_ledger}, summary={summ}, orphan_cases={orphan_tc}, schema_err={r_err}")
    else:
        record("D4_parity_harness_consumes_06_and_passes", "dynamic", False, "07_tests/parity_report.json missing")

    # --- DYNAMIC GATE D5: 09 Contracts (OpenAPI JSON, JSON Schemas, SQLite DDL execution) ---
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

    # --- DYNAMIC GATE D6: 04 Release REA Audit (T3) ---
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

    # --- SECURITY GATE SEC1: 3-tier Secret Guard (blocks high-confidence leaks) ---
    secret_hits = scan_secrets(bundle_dir, redact=False, min_confidence="high")
    record("SEC1_secret_guard_clean", "security", len(secret_hits) == 0, f"high_confidence_hits={len(secret_hits)}")

    # --- GOVERNANCE GATE GOV2 (evaluated before ceiling): 3-Axis Bijective Coverage + [AI-Safety] ---
    cov_path = bundle_dir / "04_environment" / "tool_coverage.json"
    cov_info = {"present": False, "errors": [], "degraded_tools": 0, "missing_tools_count": 0}
    cov_ok = True
    if cov_path.exists():
        cov_ok, cov_info = validate_tool_coverage_manifest(cov_path, schema_dir)
    injection_advisories = scan_prompt_injections(bundle_dir)
    record(
        "GOV2_bijective_coverage_and_ai_safety",
        "governance",
        cov_ok,
        f"tool_coverage_present={cov_info['present']}, errors={cov_info['errors']}, ai_safety_advisories={len(injection_advisories)}",
    )

    # --- GOVERNANCE GATE GOV1: Deterministic Machine Ceiling + Downgrade-Only + Anti-Slop ---
    observed_ratio = (observed_cnt / len(ev_records)) if ev_records else 0.0
    did_real_work = (len(ev_records) > 0 and parity_passed > 0)
    ceiling = compute_machine_ceiling(
        observed_ratio=observed_ratio,
        failed_cases=parity_failed,
        degraded_tools=cov_info["degraded_tools"],
        missing_tools=cov_info["missing_tools_count"],
        did_real_work=did_real_work,
        tier=tier,
    )
    ceiling_violations = []
    if rdata and isinstance(rdata.get("governance"), dict):
        gov = rdata["governance"]
        claimed_grade = gov.get("claimed_grade")
        if claimed_grade in GRADE_ORDER and GRADE_ORDER[claimed_grade] > GRADE_ORDER[ceiling["grade_ceiling"]]:
            ceiling_violations.append(f"claimed_grade({claimed_grade})>ceiling({ceiling['grade_ceiling']})")
        if gov.get("claimed_full_coverage") is True and not ceiling["can_claim_full_coverage"]:
            ceiling_violations.append("claimed_full_coverage=true_blocked_by_machine_ceiling")
    record(
        "GOV1_anti_slop_and_machine_ceiling",
        "governance",
        (not slop_hits and not ceiling_violations),
        f"ceiling={ceiling['grade_ceiling']}, can_claim_full={ceiling['can_claim_full_coverage']}, "
        f"slop_hits={slop_hits[:5]}, ceiling_violations={ceiling_violations}",
    )

    # --- INTEGRITY GATE INT1: SHA256SUMS.txt ---
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
        "machine_ceiling": ceiling,
        "ai_safety_advisories": injection_advisories[:20],
        "checks": checks,
    }


def run_governance_self_test(schema_dir: pathlib.Path) -> dict:
    """Offline self-test verifying Downgrade-Only ceiling rejection, Anti-Slop, and Bijective coverage."""
    # 1. Ceiling blocks over-claiming A when degraded_tools > 0
    ceil = compute_machine_ceiling(observed_ratio=0.9, failed_cases=0, degraded_tools=1, missing_tools=0, did_real_work=True, tier="T3")
    assert ceil["grade_ceiling"] == "B" and not ceil["can_claim_full_coverage"]

    # 2. Anti-slop catches placeholder tokens
    for tok in ("N/A", "TODO", "none", "-", "", [], {}):
        assert is_slop_value(tok), f"Expected slop for {tok!r}"
    assert not is_slop_value("Valid handler")

    # 3. Bijective tool coverage rejects overlap & unaccounted non-primary tools
    with tempfile.TemporaryDirectory() as td:
        cov_bad = pathlib.Path(td) / "bad_cov.json"
        cov_bad.write_text(json.dumps({
            "schema_version": "1.0.0",
            "generated_at": "2026-11-26T00:00:00Z",
            "host_os": "Darwin",
            "host_arch": "arm64",
            "target_stack": "desktop-tauri",
            "mode": "deep",
            "tools": [
                {"tool": "ghidra", "applicability": "applicable", "installation": "not_installed", "execution": "skipped_uninstalled", "evidence_quality": "none"}
            ],
            "missing_tools": ["ghidra"],
            "must_rerun_tools": ["ghidra"],
            "metrics": {
                "applicable_tools": 1, "terminal_state_tools": 1, "primary_success_tools": 0,
                "degraded_tools": 0, "terminal_state_completion_rate": 1.0, "primary_tool_success_rate": 0.0
            },
        }), encoding="utf-8")
        ok_bad, info_bad = validate_tool_coverage_manifest(cov_bad, schema_dir)
        assert not ok_bad and any("non_bijective_overlap" in e for e in info_bad["errors"])

        cov_good = pathlib.Path(td) / "good_cov.json"
        cov_good.write_text(json.dumps({
            "schema_version": "1.0.0",
            "generated_at": "2026-11-26T00:00:00Z",
            "host_os": "Darwin",
            "host_arch": "arm64",
            "target_stack": "desktop-tauri",
            "mode": "deep",
            "tools": [
                {"tool": "os_binary_rea", "applicability": "applicable", "installation": "installed", "execution": "executed_primary", "evidence_quality": "primary"},
                {"tool": "ghidra", "applicability": "applicable", "installation": "not_installed", "execution": "skipped_uninstalled", "evidence_quality": "none"},
            ],
            "missing_tools": ["ghidra"],
            "must_rerun_tools": [],
            "metrics": {
                "applicable_tools": 2, "terminal_state_tools": 2, "primary_success_tools": 1,
                "degraded_tools": 0, "terminal_state_completion_rate": 1.0, "primary_tool_success_rate": 0.5
            },
        }), encoding="utf-8")
        ok_good, _ = validate_tool_coverage_manifest(cov_good, schema_dir)
        assert ok_good

    return {
        "self_test": "PASS",
        "downgrade_only_ceiling_verified": True,
        "anti_slop_verified": True,
        "bijective_coverage_verified": True,
    }


def main():
    ap = argparse.ArgumentParser(description="spec-anything Dual Mechanical Quality Gate & Governance Validator")
    ap.add_argument("bundle_dir", nargs="?", default=None)
    ap.add_argument("--schemas", default=None, help="Schema directory (defaults to ../schemas relative to script)")
    ap.add_argument("--tier", choices=["T1", "T2", "T3"], default="T3")
    ap.add_argument("--max-macro-ratio", type=float, default=0.15)
    ap.add_argument("--min-refs", type=int, default=3)
    ap.add_argument("--verify-checksums", action="store_true")
    ap.add_argument("--strict-ceiling", action="store_true", help="Exit 42 (honest incomplete) if hard gates pass but full coverage cannot be claimed")
    ap.add_argument("--self-test", action="store_true", help="Run offline governance self-test")
    args = ap.parse_args()

    sdir = pathlib.Path(args.schemas) if args.schemas else pathlib.Path(__file__).resolve().parent.parent / "schemas"
    if args.self_test:
        print(json.dumps(run_governance_self_test(sdir), indent=2))
        return
    if not args.bundle_dir:
        ap.error("bundle_dir is required unless --self-test is passed")

    res = validate_bundle(
        pathlib.Path(args.bundle_dir).resolve(), sdir, args.tier, args.max_macro_ratio, args.min_refs, args.verify_checksums
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))
    if not res["all_passed"]:
        sys.exit(1)
    if args.strict_ceiling and not res["machine_ceiling"]["can_claim_full_coverage"]:
        sys.exit(42)


if __name__ == "__main__":
    main()
