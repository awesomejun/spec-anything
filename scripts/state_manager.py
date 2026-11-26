#!/usr/bin/env python3
"""
Tamper- and Race-Safe Resumable 7-Phase State Machine Manager for spec-anything (v4.1.0).
Features:
  - Atomic JSON commits (write temp file + fsync + os.replace)
  - POSIX fcntl.flock exclusive session lock (returns structured session_busy on contention)
  - Target SHA-256 Epoch isolation (lineage_base_revision) preventing silent reuse of stale evidence
  - Deterministic cache key (schema_version + target + commit + release_sha256 + mode + tier + tool_manifest)
  - Per-phase retry budget (default max 3) and explicit reopen_events audit trail
  - Append-only execution ledger (.spec-anything/RUN_MANIFEST.jsonl)
"""
import argparse
import contextlib
import datetime
import hashlib
import json
import os
import pathlib
import sys
import tempfile

try:
    import fcntl
except ImportError:
    fcntl = None

PHASES = {
    "0": "Goal, Scope & Profile Lock",
    "1": "Deterministic Static Recon & Release Artifact Analysis (RAA)",
    "2": "Feature Matrix (03) & Reproduction Environment (04)",
    "3": "Parallel Slice Investigation & Isolated Runtime Observation (05, 06, 09, 10, 11)",
    "4": "Executable Parity Tests (07) & Dual Quality Gate",
    "5": "Conflict Resolution & Question Bank Closure",
    "6": "Final Synthesis (01, 02, 08, 12), Sealing & Review Rendering",
}

DEFAULT_MAX_RETRIES = 3


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def meta_dir(workdir: pathlib.Path) -> pathlib.Path:
    d = workdir / ".spec-anything"
    d.mkdir(parents=True, exist_ok=True)
    return d


@contextlib.contextmanager
def session_lock(mdir: pathlib.Path):
    """Acquire non-blocking exclusive POSIX flock on .spec-anything/.session.lock."""
    lock_path = mdir / ".session.lock"
    fh = lock_path.open("a+", encoding="utf-8")
    try:
        if fcntl is not None:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(json.dumps({"error": "session_busy", "lock_file": str(lock_path)}, indent=2))
                sys.exit(75)
        yield
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        fh.close()


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_save_json(path: pathlib.Path, data) -> None:
    """Write JSON atomically via same-directory temporary file + fsync + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def append_manifest(mdir: pathlib.Path, event: str, details: dict) -> None:
    """Append an immutable line to .spec-anything/RUN_MANIFEST.jsonl."""
    mpath = mdir / "RUN_MANIFEST.jsonl"
    rec = {"ts": utc_now(), "event": event, **details}
    with mpath.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def compute_cache_key(
    schema_version: str,
    repo: str,
    commit_sha: str | None,
    release_sha256: str | None,
    mode: str,
    tier: str,
    tool_manifest_sha256: str | None = None,
) -> str:
    raw = "|".join([
        schema_version,
        repo,
        commit_sha or "",
        release_sha256 or "",
        mode,
        tier,
        tool_manifest_sha256 or "",
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _fresh_phases(now: str) -> dict:
    return {
        k: {
            "name": v,
            "status": "completed" if k == "0" else "pending",
            "attempts": 1 if k == "0" else 0,
            "artifacts": [],
            "updated_at": now if k == "0" else None,
            "notes": None,
        }
        for k, v in PHASES.items()
    }


def cmd_init(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
    with session_lock(mdir):
        state_path = mdir / "state.json"
        now = utc_now()
        new_cache_key = compute_cache_key(
            "1.0.0", args.repo, args.commit, args.release_sha256, args.mode, args.tier, args.tool_manifest_sha256
        )

        if state_path.exists() and not args.force:
            prev = load_json(state_path)
            target_changed = (
                (args.commit and prev.get("commit_sha") and args.commit != prev.get("commit_sha"))
                or (args.release_sha256 and prev.get("release_sha256") and args.release_sha256 != prev.get("release_sha256"))
            )
            if not target_changed:
                print(json.dumps({
                    "action": "resume_available",
                    "epoch": prev.get("epoch", 1),
                    "current_phase": prev["current_phase"],
                    "cache_key": prev.get("cache_key"),
                    "state_file": str(state_path),
                }, indent=2))
                return

            # Target commit or release SHA-256 changed -> open new Epoch to prevent silent stale-evidence reuse
            new_epoch = int(prev.get("epoch", 1)) + 1
            lineage = {
                "previous_epoch": prev.get("epoch", 1),
                "previous_commit_sha": prev.get("commit_sha"),
                "previous_release_sha256": prev.get("release_sha256"),
                "reset_at": now,
                "reason": "target_digest_changed",
            }
            state = {
                "schema_version": "1.0.0",
                "epoch": new_epoch,
                "lineage_base_revision": lineage,
                "cache_key": new_cache_key,
                "target_repo": args.repo,
                "commit_sha": args.commit,
                "release_tag": args.tag,
                "release_sha256": args.release_sha256,
                "tier": args.tier,
                "mode": args.mode,
                "depth": args.depth,
                "output_language": args.lang,
                "max_retries_per_phase": args.max_retries,
                "current_phase": 1,
                "phases": _fresh_phases(now),
                "reopen_events": prev.get("reopen_events", []) + [{
                    "ts": now,
                    "type": "epoch_reset",
                    "from_epoch": prev.get("epoch", 1),
                    "to_epoch": new_epoch,
                    "reason": "target_digest_changed",
                }],
                "updated_at": now,
            }
            atomic_save_json(state_path, state)
            append_manifest(mdir, "epoch_reset", {
                "epoch": new_epoch,
                "commit_sha": args.commit,
                "release_sha256": args.release_sha256,
                "cache_key": new_cache_key,
            })
            print(json.dumps({
                "action": "epoch_reset",
                "epoch": new_epoch,
                "lineage_base_revision": lineage,
                "cache_key": new_cache_key,
                "state_file": str(state_path),
            }, indent=2))
            return

        state = {
            "schema_version": "1.0.0",
            "epoch": 1,
            "lineage_base_revision": None,
            "cache_key": new_cache_key,
            "target_repo": args.repo,
            "commit_sha": args.commit,
            "release_tag": args.tag,
            "release_sha256": args.release_sha256,
            "tier": args.tier,
            "mode": args.mode,
            "depth": args.depth,
            "output_language": args.lang,
            "max_retries_per_phase": args.max_retries,
            "current_phase": 1,
            "phases": _fresh_phases(now),
            "reopen_events": [],
            "updated_at": now,
        }
        goal = {
            "schema_version": "1.0.0",
            "target_repo": args.repo,
            "commit_sha": args.commit,
            "release_tag": args.tag,
            "tier": args.tier,
            "mode": args.mode,
            "depth": args.depth,
            "output_language": args.lang,
            "primary_readers": ["reimplementation_engineer", "qa_verifier", "pm_designer"],
            "non_goals": [
                "vulnerability_exploitation",
                "access_control_or_drm_bypass",
                "unauthorized_asset_or_trademark_redistribution",
            ],
            "created_at": now,
        }
        questions = {"schema_version": "1.0.0", "questions": []}
        atomic_save_json(state_path, state)
        atomic_save_json(mdir / "goal.json", goal)
        atomic_save_json(mdir / "questions.json", questions)
        append_manifest(mdir, "init", {
            "epoch": 1,
            "repo": args.repo,
            "tier": args.tier,
            "mode": args.mode,
            "cache_key": new_cache_key,
        })
        print(json.dumps({
            "action": "initialized",
            "epoch": 1,
            "cache_key": new_cache_key,
            "state_file": str(state_path),
            "tier": args.tier,
            "mode": args.mode,
            "depth": args.depth,
        }, indent=2))


def cmd_advance(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
    with session_lock(mdir):
        state_path = mdir / "state.json"
        state = load_json(state_path)
        p = str(args.phase)
        if p not in state["phases"]:
            sys.exit(f"Invalid phase: {p}")

        max_retries = int(state.get("max_retries_per_phase", DEFAULT_MAX_RETRIES))
        attempts = int(state["phases"][p].get("attempts", 0)) + 1
        if attempts > max_retries and not args.override_budget:
            print(json.dumps({
                "error": "retry_budget_exceeded",
                "phase": int(p),
                "attempts": attempts,
                "max_retries_per_phase": max_retries,
            }, indent=2))
            sys.exit(42)

        now = utc_now()
        state["phases"][p]["status"] = args.status
        state["phases"][p]["attempts"] = attempts
        state["phases"][p]["updated_at"] = now
        if args.artifacts:
            state["phases"][p]["artifacts"] = sorted(set(state["phases"][p]["artifacts"] + args.artifacts))
        if args.notes:
            state["phases"][p]["notes"] = args.notes
        if args.status == "completed":
            state["current_phase"] = min(6, int(p) + 1)
        state["updated_at"] = now
        atomic_save_json(state_path, state)
        append_manifest(mdir, "advance", {
            "epoch": state.get("epoch", 1),
            "phase": int(p),
            "status": args.status,
            "attempts": attempts,
        })
        print(json.dumps({
            "action": "updated",
            "epoch": state.get("epoch", 1),
            "phase": int(p),
            "status": args.status,
            "attempts": attempts,
            "current_phase": state["current_phase"],
        }, indent=2))


def cmd_rewind(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
    with session_lock(mdir):
        state_path = mdir / "state.json"
        state = load_json(state_path)
        target = int(args.phase)
        now = utc_now()
        for k in sorted(state["phases"].keys(), key=int):
            if int(k) >= target:
                state["phases"][k]["status"] = "rewound" if int(k) == target else "pending"
                state["phases"][k]["updated_at"] = now
        state["current_phase"] = target
        state.setdefault("reopen_events", []).append({
            "ts": now,
            "type": "manual_rewind",
            "phase": target,
            "reason": args.reason or "unspecified",
        })
        state["updated_at"] = now
        atomic_save_json(state_path, state)
        append_manifest(mdir, "rewind", {
            "epoch": state.get("epoch", 1),
            "phase": target,
            "reason": args.reason or "unspecified",
        })
        print(json.dumps({"action": "rewound", "epoch": state.get("epoch", 1), "current_phase": target}, indent=2))


def cmd_question(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
    with session_lock(mdir):
        q_path = mdir / "questions.json"
        data = load_json(q_path)
        qid = args.id or f"Q-{len(data['questions']) + 1:03d}"
        existing = next((q for q in data["questions"] if q["id"] == qid), None)
        now = utc_now()
        if existing:
            if args.status:
                existing["status"] = args.status
            if args.answer:
                existing["answer"] = args.answer
            existing["updated_at"] = now
        else:
            data["questions"].append({
                "id": qid,
                "feature_id": args.feature_id,
                "category": args.category,
                "severity": args.severity,
                "question": args.text,
                "status": args.status or "open",
                "answer": args.answer,
                "updated_at": now,
            })
        atomic_save_json(q_path, data)
        append_manifest(mdir, "question", {"id": qid, "status": args.status or "open"})
        print(json.dumps({"action": "question_saved", "id": qid, "total": len(data["questions"])}, indent=2))


def cmd_status(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
    state = load_json(mdir / "state.json")
    questions = load_json(mdir / "questions.json")["questions"]
    open_q = sum(1 for q in questions if q["status"] == "open")
    manifest_lines = 0
    mpath = mdir / "RUN_MANIFEST.jsonl"
    if mpath.exists():
        manifest_lines = sum(1 for ln in mpath.read_text(encoding="utf-8").splitlines() if ln.strip())
    print(json.dumps({
        "target_repo": state["target_repo"],
        "epoch": state.get("epoch", 1),
        "cache_key": state.get("cache_key"),
        "tier": state["tier"],
        "mode": state.get("mode", "deep"),
        "depth": state["depth"],
        "output_language": state["output_language"],
        "current_phase": state["current_phase"],
        "phases": {k: {"status": v["status"], "attempts": v.get("attempts", 0)} for k, v in state["phases"].items()},
        "reopen_events_count": len(state.get("reopen_events", [])),
        "manifest_events": manifest_lines,
        "questions_total": len(questions),
        "questions_open": open_q,
    }, indent=2))


def main():
    ap = argparse.ArgumentParser(description="spec-anything tamper- and race-safe resumable phase state manager")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--workdir", required=True)
    p_init.add_argument("--repo", required=True)
    p_init.add_argument("--tag", default=None)
    p_init.add_argument("--commit", default=None)
    p_init.add_argument("--release-sha256", default=None)
    p_init.add_argument("--tool-manifest-sha256", default=None)
    p_init.add_argument("--tier", choices=["T1", "T2", "T3"], default="T3")
    p_init.add_argument("--mode", choices=["clean-room", "deep"], default="deep")
    p_init.add_argument("--depth", choices=["outline", "comprehensive", "interactive"], default="comprehensive")
    p_init.add_argument("--lang", choices=["en", "ko", "ja"], default="en")
    p_init.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_adv = sub.add_parser("advance")
    p_adv.add_argument("--workdir", required=True)
    p_adv.add_argument("--phase", type=int, required=True)
    p_adv.add_argument("--status", choices=["in_progress", "completed", "failed"], default="completed")
    p_adv.add_argument("--artifacts", nargs="*", default=[])
    p_adv.add_argument("--notes", default=None)
    p_adv.add_argument("--override-budget", action="store_true")
    p_adv.set_defaults(func=cmd_advance)

    p_rew = sub.add_parser("rewind")
    p_rew.add_argument("--workdir", required=True)
    p_rew.add_argument("--phase", type=int, required=True)
    p_rew.add_argument("--reason", default=None)
    p_rew.set_defaults(func=cmd_rewind)

    p_q = sub.add_parser("question")
    p_q.add_argument("--workdir", required=True)
    p_q.add_argument("--id", default=None)
    p_q.add_argument("--feature-id", default=None)
    p_q.add_argument("--category", default="behavior")
    p_q.add_argument("--severity", choices=["critical", "important", "nice_to_have"], default="important")
    p_q.add_argument("--text", default="")
    p_q.add_argument("--status", choices=["open", "resolved", "abandoned"], default=None)
    p_q.add_argument("--answer", default=None)
    p_q.set_defaults(func=cmd_question)

    p_st = sub.add_parser("status")
    p_st.add_argument("--workdir", required=True)
    p_st.set_defaults(func=cmd_status)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
