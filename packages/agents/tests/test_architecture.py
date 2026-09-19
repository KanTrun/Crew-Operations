# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Architecture rules — agents must not import DB/API/gates or other agents."""

from __future__ import annotations

import ast
import pathlib

CAM = ("sqlalchemy", "psycopg", "redis", "fastapi", "ca_api", "ca_gates", "ca_playbook")
ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "ca_agents"

# ── ADR-002: Math Layer phải là hàm thuần ───────────────────────────────────
#
# Plan `260913-1455` mục 7 liệt kê "Architecture compliance" là một tầng QA riêng.
# Quy tắc ở `math_layer.py` chỉ là docstring — docstring không chặn được ai đó
# thêm một lời gọi network "cho tiện". Test này biến nó thành gate thật.
#
# Danh sách cấm chia hai nhóm vì lý do khác nhau:
#  - I/O (network, DB, file): làm con số phụ thuộc thế giới bên ngoài.
#  - Bất định (`random`, `time`, `datetime`): cùng input phải ra cùng output,
#    nếu không thì không test lại được và không audit được con số đã báo chủ quán.
MATH_LAYER = ROOT / "ag_pricing" / "math_layer.py"
MATH_CAM_IO = (
    "urllib",
    "http",
    "httpx",
    "requests",
    "aiohttp",
    "socket",
    "camoufox",
    "playwright",
    "sqlalchemy",
    "psycopg",
    "redis",
    "ca_api",
    "openai",
    "anthropic",
    "gemini",
    "google",
    "llm",
    "pathlib",
    "os",
)
MATH_CAM_BAT_DINH = ("random", "time", "datetime", "uuid", "secrets")


def _ten_import(node: ast.AST) -> str:
    """Tên module của một node import; chuỗi rỗng nếu node không phải import."""
    if isinstance(node, ast.Import):
        return " ".join(a.name for a in node.names)
    if isinstance(node, ast.ImportFrom):
        return node.module or ""
    return ""


def test_math_layer_khong_io_khong_bat_dinh() -> None:
    """ADR-002: `math_layer.py` không được chạm I/O hay nguồn bất định nào."""
    # Assert cứng chứ không `return`: nếu file bị đổi tên/đổi chỗ thì gate phải
    # ĐỎ để người sửa cập nhật đường dẫn, thay vì âm thầm pass và bỏ trống quy tắc.
    assert MATH_LAYER.exists(), f"không tìm thấy Math Layer tại {MATH_LAYER}"
    tree = ast.parse(MATH_LAYER.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        ten = _ten_import(node)
        if not ten:
            continue
        goc = ten.split(".")[0]
        for cam in MATH_CAM_IO:
            assert goc != cam, (
                f"math_layer.py không được import {cam} — ADR-002 yêu cầu hàm thuần, "
                "mọi I/O phải nằm ở orchestrator"
            )
        for cam in MATH_CAM_BAT_DINH:
            assert goc != cam, (
                f"math_layer.py không được import {cam} — cùng input phải ra cùng output "
                "(ADR-002), giá trị thời gian/ngẫu nhiên phải do tầng ngoài truyền vào"
            )


def test_math_layer_khong_goi_ham_bat_dinh_truc_tiep() -> None:
    """Chặn `random.random()` / `datetime.now()` viết inline mà không qua import gốc.

    Bắt import thôi là chưa đủ: `from random import random` vẫn hiện tên module,
    nhưng `__import__` hoặc thuộc tính truy cập động thì không. Test này quét
    thêm các lời gọi dạng `<module>.<hàm>` với những tên bất định phổ biến.
    """
    assert MATH_LAYER.exists(), f"không tìm thấy Math Layer tại {MATH_LAYER}"
    tree = ast.parse(MATH_LAYER.read_text(encoding="utf-8"))
    cam_goi = {"now", "utcnow", "today", "time", "random", "urlopen", "urandom"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr in cam_goi and isinstance(func.value, ast.Name):
            assert func.value.id not in MATH_CAM_BAT_DINH + MATH_CAM_IO, (
                f"math_layer.py không được gọi {func.value.id}.{func.attr}() — ADR-002"
            )


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
    # Ngoại lệ: `ag_twin` dùng `ag_predict.math_layer` — math_layer là module toán
    # thuần (ADR-002), không phải agent. Cho phép import module con này.
    CHO_PHEP = {
        "ag_twin": {"ag_predict.math_layer"},
    }
    for tep in ROOT.rglob("*.py"):
        hien_tai = next((p for p in tep.parts if p.startswith("ag_")), None)
        if hien_tai is None:
            continue
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
                # Bỏ qua nếu import này là module con được phép (vd ag_predict.math_layer)
                cho_phep = CHO_PHEP.get(hien_tai, set())
                if any(cho in ten for cho in cho_phep):
                    continue
                assert khac not in ten, f"{tep} không được gọi agent khác: {khac}"
