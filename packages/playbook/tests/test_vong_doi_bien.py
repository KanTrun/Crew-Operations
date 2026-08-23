"""Nhánh biên của cẩm nang sống: path tường minh, từ chối duyệt, dạng lưu {items}."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ca_playbook.vong_doi import de_xuat, duyet, list_luat, save_luat, tim_mau


def _luat_de_xuat() -> dict[str, Any]:
    mau: dict[str, Any] = {
        "mau": "nhan_ca",
        "loai_luat": "nhu_cau_ca",
        "n": 3,
        "bang_chung": ["0", "1", "2"],
        "nguon": "ghi_truc_tiep",
    }
    luat: dict[str, Any] = de_xuat(mau)
    return luat


def test_luu_va_doc_cam_nang_theo_path_truyen_vao(tmp_path: Path) -> None:
    """Truyền path tường minh thì _path dùng luôn path đó thay vì STORE mặc định."""
    p = tmp_path / "sau" / "cam_nang.json"
    items = [_luat_de_xuat()]
    save_luat(items, p)
    assert p.exists()
    assert list_luat(p) == items


def test_list_luat_file_chua_ton_tai_tra_ve_rong(tmp_path: Path) -> None:
    assert list_luat(tmp_path / "chua_co.json") == []


def test_list_luat_doc_duoc_dang_boc_items(tmp_path: Path) -> None:
    """File lưu dạng {"items": [...]} vẫn phải đọc ra danh sách luật."""
    p = tmp_path / "cam_nang.json"
    p.write_text(json.dumps({"items": [{"id": "luat_x"}]}), encoding="utf-8")
    assert list_luat(p) == [{"id": "luat_x"}]


def test_duyet_tu_choi_dat_trang_thai_tu_choi() -> None:
    """Quản lý không duyệt thì luật dừng ở 'tu_choi', không được lên bước 7."""
    luat = _luat_de_xuat()
    out = duyet(luat, ok=False, ai="ql_01")
    assert out["trang_thai"] == "tu_choi"
    assert out["nguoi_duyet"] == "ql_01"
    assert out["buoc"] == 3
    assert "tham_so_loi" not in out


def test_duyet_khong_sua_luat_goc() -> None:
    """duyet phải trả bản sao, luật đầu vào giữ nguyên trạng thái."""
    luat = _luat_de_xuat()
    duyet(luat, ok=True, ai="ql_01")
    assert luat["trang_thai"] == "de_xuat"


def test_tim_mau_duoi_ba_lan_sua_khong_ra_mau() -> None:
    """Ngưỡng gom mẫu là >=3 lần sửa, 2 lần thì chưa đủ."""
    rows: list[dict[str, Any]] = [{"loai": "nhan_ca"}, {"loai": "nhan_ca"}]
    assert tim_mau(rows) == []


def test_tim_mau_toan_bo_synthetic_thi_nguon_la_dung_lai() -> None:
    """Mọi lần sửa đều là dựng lại thì nguồn phải ghi 'dung_lai_8_tuan'."""
    rows: list[dict[str, Any]] = [{"loai": "pin_ca", "synthetic": True} for _ in range(3)]
    out = tim_mau(rows)
    assert len(out) == 1
    assert out[0]["nguon"] == "dung_lai_8_tuan"
    assert out[0]["loai_luat"] == "ghep_ky_nang"


def test_tim_mau_loai_la_khac_khi_thieu_truong_loai() -> None:
    """Dòng sửa không có 'loai' phải gom vào nhóm 'khac' và map về nhu_cau_ca."""
    rows: list[dict[str, Any]] = [{} for _ in range(3)]
    out = tim_mau(rows)
    assert out[0]["mau"] == "khac"
    assert out[0]["loai_luat"] == "nhu_cau_ca"
