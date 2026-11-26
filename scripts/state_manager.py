#!/usr/bin/env python3
"""
Resumable 7-phase state machine manager for spec-anything.
Manages .spec-anything/state.json, goal.json, and questions.json (Question Bank)
so large repository runs can pause, resume, rewind, or re-validate cleanly.
"""
import argparse
import datetime
import json
import pathlib
import sys

PHASES = {
    "0": "Goal, Scope & Profile Lock",
    "1": "Deterministic Static Recon & Release Artifact Analysis (REA)",
    "2": "Feature Matrix (03) & Reproduction Environment (04)",
    "3": "Parallel Slice Investigation & Isolated Runtime Observation (05, 06, 09, 10, 11)",
    "4": "Executable Parity Tests (07) & Dual Quality Gate",
    "5": "Conflict Resolution & Question Bank Closure",
    "6": "Final Synthesis (01, 02, 08, 12), Sealing & Review Rendering",
}


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def meta_dir(workdir: pathlib.Path) -> pathlib.Path:
    d = workdir / ".spec-anything"
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: pathlib.Path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cmd_init(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
    state_path = mdir / "state.json"
    if state_path.exists() and not args.force:
        state = load_json(state_path)
        print(json.dumps({"action": "resume_available", "current_phase": state["current_phase"], "state_file": str(state_path)}, indent=2))
        return
    now = utc_now()
    phases = {
        k: {"name": v, "status": "completed" if k == "0" else "pending", "artifacts": [], "updated_at": now if k == "0" else None, "notes": None}
        for k, v in PHASES.items()
    }
    state = {
        "schema_version": "1.0.0",
        "target_repo": args.repo,
        "commit_sha": args.commit,
        "release_tag": args.tag,
        "release_sha256": args.release_sha256,
        "tier": args.tier,
        "mode": args.mode,
        "depth": args.depth,
        "output_language": args.lang,
        "current_phase": 1,
        "phases": phases,
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
    save_json(state_path, state)
    save_json(mdir / "goal.json", goal)
    save_json(mdir / "questions.json", questions)
    print(json.dumps({"action": "initialized", "state_file": str(state_path), "tier": args.tier, "depth": args.depth}, indent=2))


def cmd_advance(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
    state_path = mdir / "state.json"
    state = load_json(state_path)
    p = str(args.phase)
    if p not in state["phases"]:
        sys.exit(f"Invalid phase: {p}")
    now = utc_now()
    state["phases"][p]["status"] = args.status
    state["phases"][p]["updated_at"] = now
    if args.artifacts:
        state["phases"][p]["artifacts"] = sorted(set(state["phases"][p]["artifacts"] + args.artifacts))
    if args.notes:
        state["phases"][p]["notes"] = args.notes
    if args.status == "completed":
        state["current_phase"] = min(6, int(p) + 1)
    state["updated_at"] = now
    save_json(state_path, state)
    print(json.dumps({"action": "updated", "phase": int(p), "status": args.status, "current_phase": state["current_phase"]}, indent=2))


def cmd_rewind(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
    state_path = mdir / "state.json"
    state = load_json(state_path)
    target = int(args.phase)
    now = utc_now()
    for k in sorted(state["phases"].keys(), key=int):
        if int(k) >= target:
            state["phases"][k]["status"] = "rewound" if int(k) == target else "pending"
            state["phases"][k]["updated_at"] = now
    state["current_phase"] = target
    state["updated_at"] = now
    save_json(state_path, state)
    print(json.dumps({"action": "rewound", "current_phase": target}, indent=2))


def cmd_question(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
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
    save_json(q_path, data)
    print(json.dumps({"action": "question_saved", "id": qid, "total": len(data["questions"])}, indent=2))


def cmd_status(args):
    mdir = meta_dir(pathlib.Path(args.workdir))
    state = load_json(mdir / "state.json")
    questions = load_json(mdir / "questions.json")["questions"]
    open_q = sum(1 for q in questions if q["status"] == "open")
    print(json.dumps({
        "target_repo": state["target_repo"],
        "tier": state["tier"],
        "depth": state["depth"],
        "output_language": state["output_language"],
        "current_phase": state["current_phase"],
        "phases": {k: v["status"] for k, v in state["phases"].items()},
        "questions_total": len(questions),
        "questions_open": open_q,
    }, indent=2))


def main():
    ap = argparse.ArgumentParser(description="spec-anything resumable phase state manager")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--workdir", required=True)
    p_init.add_argument("--repo", required=True)
    p_init.add_argument("--tag", default=None)
    p_init.add_argument("--commit", default=None)
    p_init.add_argument("--release-sha256", default=None)
    p_init.add_argument("--tier", choices=["T1", "T2", "T3"], default="T3")
    p_init.add_argument("--mode", choices=["clean-room", "deep"], default="deep")
    p_init.add_argument("--depth", choices=["outline", "comprehensive", "interactive"], default="comprehensive")
    p_init.add_argument("--lang", choices=["en", "ko", "ja"], default="en")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_adv = sub.add_parser("advance")
    p_adv.add_argument("--workdir", required=True)
    p_adv.add_argument("--phase", type=int, required=True)
    p_adv.add_argument("--status", choices=["in_progress", "completed", "failed"], default="completed")
    p_adv.add_argument("--artifacts", nargs="*", default=[])
    p_adv.add_argument("--notes", default=None)
    p_adv.set_defaults(func=cmd_advance)

    p_rew = sub.add_parser("rewind")
    p_rew.add_argument("--workdir", required=True)
    p_rew.add_argument("--phase", type=int, required=True)
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
