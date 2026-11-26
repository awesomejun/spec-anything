"""Enumerate a commit's file paths and check a reviewed copy of that inventory."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess


def inventory(repo, revision):
    def git(*args):
        return subprocess.check_output(["git", "-C", repo, *args])

    commit = git("rev-parse", "--verify", "--end-of-options", revision + "^{commit}").decode().strip()
    paths = git("ls-tree", "-rz", "--name-only", commit).decode("utf-8", "surrogateescape")
    return commit, paths.split("\0")[:-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo")
    parser.add_argument("revision")
    parser.add_argument("review", nargs="?", type=Path)
    args = parser.parse_args()
    commit, paths = inventory(args.repo, args.revision)
    if args.review is None:
        rows = [{"path": path, "status": "pending", "features": [], "reason": ""} for path in paths]
        print(json.dumps({"commit": commit, "files": rows}, indent=2))
        return
    review = json.loads(args.review.read_text())
    rows = review["files"]
    if review["commit"] != commit or sorted(row["path"] for row in rows) != sorted(paths):
        raise SystemExit("Commit or file list differs from the pinned Git tree.")
    for row in rows:
        status = row["status"]
        features = row["features"]
        if status == "mapped" and isinstance(features, list) and features and all(isinstance(f, str) and f.strip() for f in features):
            continue
        if status in ("excluded", "unverified") and isinstance(row["reason"], str) and row["reason"].strip():
            continue
        raise SystemExit("Incomplete disposition: " + row["path"])
    print(json.dumps(dict(Counter(row["status"] for row in rows)), sort_keys=True))


if __name__ == "__main__":
    main()
