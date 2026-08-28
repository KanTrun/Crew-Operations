#!/usr/bin/env python3
"""Đồng bộ README và docs Crew-Operations từ main sang mọi nhánh remote."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC_FILES = [
    "README.md",
    "docs/team.md",
    "docs/github-operating-model.md",
    "docs/phan-cong-nhanh.md",
    "docs/runbook-demo.md",
    "packages/agents/src/ca_agents/llm.py",
    "Makefile",
    "scripts/docker_stack.py",
]
COMMIT_MSG = "docs: dong bo README va link Crew-Operations tu main"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True, check=check)


def main() -> int:
    run("git", "fetch", "origin")
    branches_raw = run("git", "branch", "-r").stdout
    branches: list[str] = []
    for line in branches_raw.splitlines():
        line = line.strip()
        if not line or "->" in line or line.endswith("/HEAD"):
            continue
        name = line.removeprefix("origin/").strip()
        if name:
            branches.append(name)

    if not branches:
        print("Không có nhánh remote.", file=sys.stderr)
        return 1

    original = run("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    stash = run("git", "stash", "push", "-u", "-m", "sync-docs-temp", check=False)
    had_stash = stash.returncode == 0 and "No local changes" not in (stash.stdout or "")

    failed: list[str] = []
    skipped: list[str] = []
    updated: list[str] = []

    for branch in sorted(set(branches)):
        co = run("git", "checkout", branch, check=False)
        if co.returncode != 0:
            failed.append(f"{branch}: checkout — {co.stderr.strip()}")
            continue
        for rel in SYNC_FILES:
            run("git", "checkout", "main", "--", rel, check=False)
        diff = run("git", "diff", "--cached", "--quiet", check=False)
        if diff.returncode == 0:
            skipped.append(branch)
            continue
        commit = run("git", "commit", "-m", COMMIT_MSG, check=False)
        if commit.returncode != 0:
            failed.append(f"{branch}: commit — {commit.stderr.strip()}")
            continue
        push = run("git", "push", "origin", branch, check=False)
        if push.returncode != 0:
            failed.append(f"{branch}: push — {push.stderr.strip()}")
            continue
        updated.append(branch)

    run("git", "checkout", original, check=False)
    if had_stash:
        run("git", "stash", "pop", check=False)

    print("\n== sync docs Crew-Operations ==")
    print(f"  updated ({len(updated)}): {', '.join(updated) or '—'}")
    print(f"  skipped ({len(skipped)}): {', '.join(skipped) or '—'}")
    if failed:
        print(f"  failed ({len(failed)}):")
        for f in failed:
            print(f"    - {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
