"""Nhánh biên của bảng ghi nhận lần sửa: path truyền tay, cờ synthetic, lọc synthetic."""

from __future__ import annotations

from pathlib import Path

from ca_playbook.sua import list_sua, record_sua


def test_record_sua_ghi_vao_path_truyen_vao(tmp_path: Path) -> None:
    """Truyền path tường minh thì _store dùng luôn path đó, không đọc biến môi trường."""
    p = tmp_path / "nested" / "so_lan_sua.jsonl"
    row = record_sua(
        loai="nhan_ca",
        truoc=2,
        sau=3,
        ai="nv_01",
        now_iso="2025-01-01T08:00:00",
        path=p,
    )
    assert p.exists()
    assert row["loai"] == "nhan_ca"
    assert list_sua(p) == [row]


def test_record_sua_synthetic_gan_co_synthetic(tmp_path: Path) -> None:
    p = tmp_path / "so_lan_sua.jsonl"
    row = record_sua(
        loai="nha_ca",
        truoc=3,
        sau=2,
        ai="nv_02",
        now_iso="2025-01-02T08:00:00",
        path=p,
        synthetic=True,
    )
    assert row["synthetic"] is True
    assert list_sua(p)[0]["synthetic"] is True


def test_record_sua_mac_dinh_khong_co_co_synthetic(tmp_path: Path) -> None:
    p = tmp_path / "so_lan_sua.jsonl"
    row = record_sua(
        loai="nha_ca", truoc=3, sau=2, ai="nv_02", now_iso="2025-01-02T08:00:00", path=p
    )
    assert "synthetic" not in row


def test_list_sua_loc_bo_dong_synthetic(tmp_path: Path) -> None:
    """include_synthetic=False phải bỏ qua các dòng dựng lại, chỉ giữ ghi trực tiếp."""
    p = tmp_path / "so_lan_sua.jsonl"
    record_sua(
        loai="nhan_ca",
        truoc=2,
        sau=3,
        ai="nv_01",
        now_iso="2025-01-01T08:00:00",
        path=p,
        synthetic=True,
    )
    record_sua(loai="nhan_ca", truoc=2, sau=3, ai="nv_01", now_iso="2025-01-03T08:00:00", path=p)
    assert len(list_sua(p)) == 2
    thuc = list_sua(p, include_synthetic=False)
    assert len(thuc) == 1
    assert thuc[0]["at"] == "2025-01-03T08:00:00"


def test_list_sua_file_chua_ton_tai_tra_ve_rong(tmp_path: Path) -> None:
    assert list_sua(tmp_path / "chua_co.jsonl") == []
