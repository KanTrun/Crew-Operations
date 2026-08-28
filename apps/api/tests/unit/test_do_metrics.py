"""Bộ đo 12 số §18.2 phải TẤT ĐỊNH và luôn khai nguồn.

Hồ sơ §18.2 tự đặt hai luật: "Cấm số phỏng đoán" và mọi con số phải phát lại
được. Bộ kiểm này giữ hai luật đó bằng máy:

- chạy bộ đo hai lần trên cùng fixture → cùng kết quả (trừ trường đã khai là
  phải bấm đồng hồ, kê trong `khong_tat_dinh`);
- mọi bản ghi có `nguon` ∈ {mo_phong_fixture, quan_that} và `cach_do`;
- số nào `chua_do` thì `gia_tri` phải là null và phải có `ly_do`;
- bộ đo không được dùng `random` hay giờ hệ thống làm đầu vào.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "scripts" / "do_metrics.py"

NGUON_HOP_LE = {"mo_phong_fixture", "quan_that"}
TRANG_THAI_HOP_LE = {"do_duoc", "mot_phan", "chua_do"}
BAY_SO_CAN_QUAN_THAT = {1, 3, 7, 8, 9, 11, 12}
NAM_SO_DA_DO = {"2", "4", "5", "6", "10"}


def _nap_bo_do() -> Any:
    spec = importlib.util.spec_from_file_location("do_metrics", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["do_metrics"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bo_do() -> Any:
    return _nap_bo_do()


@pytest.fixture(scope="module")
def payload(bo_do: Any) -> dict[str, Any]:
    ket_qua: dict[str, Any] = bo_do.do_tat_ca()
    return ket_qua


def _bo_truong_bam_dong_ho(payload: dict[str, Any]) -> dict[str, Any]:
    """Gỡ mọi trường đã tự khai là không tất định trước khi so hai lần chạy."""
    out = copy.deepcopy(payload)
    for rec in out["so_do"]:
        gia_tri = rec.get("gia_tri")
        if not isinstance(gia_tri, dict):
            continue
        for khoa in rec.get("khong_tat_dinh", []):
            gia_tri.pop(khoa, None)
    return out


def test_chay_hai_lan_cho_cung_ket_qua(bo_do: Any) -> None:
    lan_1 = _bo_truong_bam_dong_ho(bo_do.do_tat_ca())
    lan_2 = _bo_truong_bam_dong_ho(bo_do.do_tat_ca())
    assert lan_1 == lan_2


def test_moi_ban_ghi_co_nguon_va_cach_do(payload: dict[str, Any]) -> None:
    assert payload["so_do"], "bộ đo không trả bản ghi nào"
    for rec in payload["so_do"]:
        assert rec["nguon"] in NGUON_HOP_LE, rec
        assert rec["trang_thai"] in TRANG_THAI_HOP_LE, rec
        assert isinstance(rec["cach_do"], str)
        assert len(rec["cach_do"]) >= 40, f"cach_do quá mỏng ở #{rec['so']}"


def test_do_dung_bay_so_can_quan_that(payload: dict[str, Any]) -> None:
    assert {rec["so"] for rec in payload["so_do"]} == BAY_SO_CAN_QUAN_THAT
    assert {row["so"] for row in payload["khong_do_o_day"]} == NAM_SO_DA_DO


def test_so_chua_do_de_trong_kem_ly_do(payload: dict[str, Any]) -> None:
    for rec in payload["so_do"]:
        if rec["trang_thai"] == "chua_do":
            assert rec["gia_tri"] is None, rec
        if rec["trang_thai"] != "do_duoc":
            assert rec.get("ly_do"), f"#{rec['so']} thiếu ly_do"


def test_khong_bao_gio_gan_nhan_quan_that_cho_fixture(payload: dict[str, Any]) -> None:
    assert "fixture" in payload["nguon_du_lieu"].lower()
    for rec in payload["so_do"]:
        assert rec["nguon"] == "mo_phong_fixture", (
            f"#{rec['so']} gắn nhãn quán thật trong khi nguồn là fixture"
        )


def test_bo_do_khong_dung_random_hay_gio_he_thong() -> None:
    ma = SCRIPT.read_text(encoding="utf-8")
    for cam in ("import random", "from random", "time.time(", "datetime.now("):
        assert cam not in ma, f"bộ đo dùng {cam} → mất tính tất định"


def test_ghi_tu_choi_nhan_nguon_la_ma_khong_hop_le(bo_do: Any) -> None:
    with pytest.raises(ValueError):
        bo_do.ghi(99, "x", gia_tri=1, trang_thai="do_duoc", cach_do="y", nguon="ban_bia")
    with pytest.raises(ValueError):
        bo_do.ghi(99, "x", gia_tri=None, trang_thai="chua_do", cach_do="y")
