from __future__ import annotations

from pathlib import Path

from ca_ops import evaluate_phieu_access, load_phieu_catalog, load_phieu_policy


def test_access_is_inclusive_and_fail_closed() -> None:
    args = dict(
        nv_id="nv_1",
        expected_nv_id="nv_1",
        checked_in=True,
        requires_checkin=True,
        opens_at_ms=100,
        closes_at_ms=200,
    )
    assert evaluate_phieu_access(now_ms=100, **args).allowed
    assert evaluate_phieu_access(now_ms=200, **args).allowed
    assert evaluate_phieu_access(now_ms=99, **args).reason == "chua_den_cua_so"
    assert evaluate_phieu_access(now_ms=201, **args).reason == "da_qua_cua_so"


def test_access_checks_responsibility_and_shift_attendance() -> None:
    args = dict(now_ms=150, opens_at_ms=100, closes_at_ms=200)
    assert evaluate_phieu_access(
        nv_id="nv_2", expected_nv_id="nv_1", checked_in=True, requires_checkin=True, **args
    ).reason == "khong_phai_nguoi_phu_trach"
    assert evaluate_phieu_access(
        nv_id="nv_1", expected_nv_id="nv_1", checked_in=False, requires_checkin=True, **args
    ).reason == "chua_diem_danh_ca"


def test_store_policy_override_and_legacy_catalog(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        """
mac_dinh: [{ma: mo_quan, bat: true}]
chinh_sach:
  phien_ban: 1
  mui_gio: Asia/Ho_Chi_Minh
  cua_so:
    ca_dau_ngay: {mo_truoc_moc_phut: 60, dong_sau_moc_phut: 30}
    giao_ca: {mo_truoc_moc_phut: 30, dong_sau_moc_phut: 15}
    ca_cuoi_ngay: {mo_truoc_moc_phut: 30, dong_sau_moc_phut: 60}
quan:
  quan_02:
    phieu: [{ma: dong_quan, bat: true}]
    chinh_sach:
      cua_so:
        ca_cuoi_ngay: {mo_truoc_moc_phut: 45, dong_sau_moc_phut: 90}
""",
        encoding="utf-8",
    )
    assert load_phieu_policy("quan_02", cfg)["cua_so"]["ca_cuoi_ngay"]["dong_sau_moc_phut"] == 90
    assert [x["ma"] for x in load_phieu_catalog("quan_02", cfg)] == ["dong_quan"]
