#!/usr/bin/env python3
"""Strip git conflict markers, keeping the lower (incoming) side."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAT = re.compile(
    r"<<<<<<<[^\n]*\n.*?=======\n(.*?)>>>>>>>[^\n]*\n",
    re.DOTALL,
)


def clean(text: str) -> str:
    prev = None
    while prev != text:
        prev = text
        text = PAT.sub(r"\1", text)
    return text


def main() -> int:
    touched = 0
    for path in ROOT.rglob("*"):
        if path.suffix not in {".py", ".ts", ".tsx", ".md", ".json", ".css"}:
            continue
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        raw = path.read_text(encoding="utf-8")
        if "<<<<<<<" not in raw:
            continue
        fixed = clean(raw)
        if fixed != raw:
            path.write_text(fixed, encoding="utf-8")
            print(f"fixed {path.relative_to(ROOT)}")
            touched += 1
    print(f"done: {touched} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
