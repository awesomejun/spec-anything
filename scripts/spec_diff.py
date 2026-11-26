#!/usr/bin/env python3
"""
Deterministic Spec-vs-Code Impact & Sync Analyzer for spec-anything.
Maps changed upstream repository files (from --changed-file or git diff base..head)
against 03_scope/features.json source_refs to compute impacted Feature IDs (F-XXX),
Evidence IDs (EV-XXX), Screen IDs (SCR-XXX), and Parity Test IDs (TC-XXX) that must
be re-verified when upstream releases a new commit or tag.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys
import tempfile


def strip_line_range(ref: str) -> str:
    """Normalize '[REF: src/app.ts:10-40]' or 'src/app.ts:10-40' to 'src/app.ts'."""
    s = ref.strip()
    m = re.match(r"^\[REF:\s*([^\]]+)\]$", s)
    if m:
        s = m.group(1).strip()
    # Strip trailing :line or :start-end
    s = re.sub(r":\d+(?:-\d+)?$", "", s)
    return s.lstrip("./")


def git_changed_files(repo_dir: pathlib.Path, base_rev: str, head_rev: str) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_dir), "diff", "--name-only", f"{base_rev}..{head_rev}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [ln.strip().lstrip("./") for ln in proc.stdout.splitlines() if ln.strip()]


def analyze_impact(features_path: pathlib.Path, changed_files: list[str]) -> dict:
    data = json.loads(features_path.read_text(encoding="utf-8"))
    norm_changed = sorted({f.strip().lstrip("./") for f in changed_files if f.strip()})
    changed_set = set(norm_changed)

    impacted_features = []
    impacted_evidence = set()
    impacted_screens = set()
    impacted_tests = set()
    matched_files = set()

    for feat in data.get("features", []):
        refs = [strip_line_range(r) for r in feat.get("source_refs", [])]
        hits = sorted({c for c in changed_set if any(c == r or c.endswith("/" + r) or r.endswith("/" + c) for r in refs)})
        if hits:
            matched_files.update(hits)
            impacted_features.append({
                "feature_id": feat["feature_id"],
                "name": feat["name"],
                "requirement_level": feat.get("requirement_level", "must"),
                "matched_files": hits,
                "evidence_ids": feat.get("evidence_ids", []),
                "screen_ids": feat.get("screen_ids", []),
                "test_ids": feat.get("test_ids", []),
            })
            impacted_evidence.update(feat.get("evidence_ids", []))
            impacted_screens.update(feat.get("screen_ids", []))
            impacted_tests.update(feat.get("test_ids", []))

    unmapped_files = sorted(changed_set - matched_files)
    return {
        "schema_version": "1.0.0",
        "features_file": features_path.name,
        "changed_files_count": len(norm_changed),
        "impacted_feature_count": len(impacted_features),
        "impacted_features": impacted_features,
        "rerun_evidence_ids": sorted(impacted_evidence),
        "rerun_screen_ids": sorted(impacted_screens),
        "rerun_test_ids": sorted(impacted_tests),
        "unmapped_changed_files": unmapped_files,
        "sync_status": "in_sync" if (not impacted_features and not unmapped_files) else "drift_detected",
    }


def run_self_test() -> dict:
    with tempfile.TemporaryDirectory() as td:
        fp = pathlib.Path(td) / "features.json"
        fp.write_text(json.dumps({
            "schema_version": "1.0.0",
            "target": {"repo": "example/app", "tag": "v1.0.0", "commit_sha": "abcdef1"},
            "generated_at": "2026-11-26T00:00:00Z",
            "features": [
                {
                    "feature_id": "F-001",
                    "domain": "timer",
                    "name": "Start countdown",
                    "kind": "ui_screen",
                    "is_macro_group": False,
                    "requirement_level": "must",
                    "entrypoint": "Timer.start",
                    "source_refs": ["src/timer.ts:12-48"],
                    "status": "observed",
                    "evidence_ids": ["EV-001"],
                    "screen_ids": ["SCR-001"],
                    "contract_refs": ["09_contracts/state.schema.json"],
                    "test_ids": ["TC-001"],
                },
                {
                    "feature_id": "F-002",
                    "domain": "settings",
                    "name": "Toggle theme",
                    "kind": "setting",
                    "is_macro_group": False,
                    "requirement_level": "should",
                    "entrypoint": "Theme.toggle",
                    "source_refs": ["src/theme.ts:1-30"],
                    "status": "observed",
                    "evidence_ids": ["EV-002"],
                    "screen_ids": ["SCR-002"],
                    "contract_refs": [],
                    "test_ids": ["TC-002"],
                },
            ],
        }), encoding="utf-8")
        rep = analyze_impact(fp, ["src/timer.ts", "src/new_untracked.ts"])
        assert rep["sync_status"] == "drift_detected"
        assert rep["impacted_feature_count"] == 1
        assert rep["rerun_evidence_ids"] == ["EV-001"]
        assert rep["rerun_screen_ids"] == ["SCR-001"]
        assert rep["rerun_test_ids"] == ["TC-001"]
        assert rep["unmapped_changed_files"] == ["src/new_untracked.ts"]
        return {
            "self_test": "PASS",
            "impacted_feature_count": rep["impacted_feature_count"],
            "rerun_test_ids": rep["rerun_test_ids"],
            "unmapped_changed_files": rep["unmapped_changed_files"],
        }


def main() -> None:
    ap = argparse.ArgumentParser(description="spec-anything deterministic spec-vs-code impact and sync analyzer")
    ap.add_argument("--features", help="Path to 03_scope/features.json")
    ap.add_argument("--changed-file", action="append", default=[], help="Changed relative source path (repeatable)")
    ap.add_argument("--repo", help="Local git repo path for git diff range")
    ap.add_argument("--base", help="Base commit/tag for git diff")
    ap.add_argument("--head", default="HEAD", help="Head commit/tag for git diff (default: HEAD)")
    ap.add_argument("--self-test", action="store_true", help="Run offline impact-analysis self-test")
    args = ap.parse_args()

    if args.self_test:
        print(json.dumps(run_self_test(), indent=2))
        return
    if not args.features:
        ap.error("--features is required unless --self-test is passed")

    changed = list(args.changed_file)
    if args.repo and args.base:
        changed.extend(git_changed_files(pathlib.Path(args.repo), args.base, args.head))

    report = analyze_impact(pathlib.Path(args.features), changed)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
