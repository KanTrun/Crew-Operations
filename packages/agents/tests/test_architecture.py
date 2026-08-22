"""Architecture rules — agents must not import DB/API/gates or other agents."""

from __future__ import annotations

import ast
import pathlib

CAM = ("sqlalchemy", "psycopg", "redis", "fastapi", "ca_api", "ca_gates", "ca_playbook")
ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "ca_agents"


def test_moi_agent_co_pham_vi_khi_co_thu_muc() -> None:
    if not ROOT.exists():
        return
    for d in ROOT.iterdir():
        if d.is_dir() and d.name.startswith("ag_"):
            assert (d / "PHAM_VI.md").exists(), f"{d.name} thiếu PHAM_VI.md"


def test_agent_khong_goi_agent_va_khong_ghi_db() -> None:
    if not ROOT.exists():
        return
    ten_agent = {d.name for d in ROOT.iterdir() if d.is_dir() and d.name.startswith("ag_")}
    for tep in ROOT.rglob("*.py"):
        hien_tai = next((p for p in tep.parts if p.startswith("ag_")), None)
        tree = ast.parse(tep.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            ten = ""
            if isinstance(node, ast.Import):
                ten = " ".join(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                ten = node.module or ""
            for x in CAM:
                assert x not in ten, f"{tep} không được import {x}"
            for khac in ten_agent - {hien_tai}:
                assert khac not in ten, f"{tep} không được gọi agent khác: {khac}"
