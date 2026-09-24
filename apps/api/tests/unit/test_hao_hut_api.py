"""HTTP hao hụt — /api/v1/hao-hut (plan 260923-1736).

Khẳng định:

1. Đọc từ dữ liệu thật, số khớp công thức §4.3.
2. KV rỗng ⇒ tóm tắt rỗng, không raise, không bịa số.
3. Thiếu một vế ⇒ `thieu_du_lieu` kèm `thieu_ve`, không nói "đạt".
4. Ghi hao hụt để lại vết audit (lỗ trước đây ở đường ghi cũ).
5. Cùng một nguồn với agent mẹ — không thể lệch số.
"""

from __future__ import annotations

from typing import Any

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get, kv_mutate
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def _nap_kiem_ke(ngay: str, muc: list[dict[str, Any]], *, nguon: str = "quan") -> None:
    def mut(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows.append({"id": f"kk_test_{len(rows)}", "ngay": ngay, "muc": muc, "nguon": nguon})
        return rows

    kv_mutate("kiem_ke", mut, [])


def _nap_menu(mon: dict[str, Any]) -> None:
    from ca_api.persist import menu_upsert

    menu_upsert(mon)


def test_hao_hut_rong_khong_bia_so() -> None:
    """Chưa có dữ liệu ⇒ tóm tắt rỗng với `ty_le_trung_binh` là None, không phải 0.0."""
    r = client.get("/api/v1/hao-hut", headers=headers(client))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tong_dong"] == 0
    assert body["ty_le_trung_binh"] is None
    assert body["dong"] == []


def test_hao_hut_doi_token() -> None:
    r = client.get("/api/v1/hao-hut")
    assert r.status_code == 401


def test_hao_hut_tinh_tu_kiem_ke_va_cong_thuc() -> None:
    """Số thực tế khớp §4.3: đầu ca + nhập − cuối ca − hao hụt đã ghi."""
    from datetime import datetime

    hom_nay = datetime.now().date().isoformat()
    _nap_kiem_ke(hom_nay, [
        {"mat_hang": "sua_tuoi", "dau_ca": 25, "nhap_trong_ca": 8, "cuoi_ca": 26, "hao_hut_ghi": 0},
    ])
    r = client.get("/api/v1/hao-hut?ky=hom_nay", headers=headers(client))
    assert r.status_code == 200, r.text
    dong = r.json()["dong"]
    sua = next(d for d in dong if d["mat_hang"] == "sua_tuoi")
    assert sua["thuc_te"] == 7.0          # 25 + 8 − 26 − 0
    assert sua["muc_do"] == "thieu_du_lieu"  # chưa có đơn ⇒ chưa có vế lý thuyết
    assert sua["thieu_ve"] == ["ly_thuyet"]


def test_hao_hut_khong_ket_luan_dat_khi_thieu_ve() -> None:
    """Có kiểm kê mà chưa có đơn ⇒ không được nói 'đạt' (fail-closed)."""
    from datetime import datetime

    hom_nay = datetime.now().date().isoformat()
    _nap_kiem_ke(hom_nay, [
        {"mat_hang": "tra", "dau_ca": 100, "nhap_trong_ca": 0, "cuoi_ca": 40, "hao_hut_ghi": 0},
    ])
    body = client.get("/api/v1/hao-hut?ky=hom_nay", headers=headers(client)).json()
    tra = next(d for d in body["dong"] if d["mat_hang"] == "tra")
    assert tra["muc_do"] == "thieu_du_lieu"
    assert tra["ly_thuyet"] is None
    assert body["so_thieu_du_lieu"] >= 1


def test_hao_hut_danh_dau_du_lieu_mau() -> None:
    """Nhãn mẫu theo lên tận cùng để UI gắn chip và người đọc không nhầm số thật."""
    from datetime import datetime

    hom_nay = datetime.now().date().isoformat()
    _nap_kiem_ke(
        hom_nay,
        [{"mat_hang": "da", "dau_ca": 10, "nhap_trong_ca": 0, "cuoi_ca": 4, "hao_hut_ghi": 0}],
        nguon="mo_phong_fixture",
    )
    body = client.get("/api/v1/hao-hut?ky=hom_nay", headers=headers(client)).json()
    assert body["co_du_lieu_mau"] is True


def test_hao_hut_loc_theo_ky() -> None:
    """Kỳ hôm nay không tính phiếu của ngày khác."""
    from datetime import datetime

    hom_nay = datetime.now().date().isoformat()
    _nap_kiem_ke("2020-01-01", [
        {"mat_hang": "banh", "dau_ca": 999, "nhap_trong_ca": 0, "cuoi_ca": 0, "hao_hut_ghi": 0},
    ])
    _nap_kiem_ke(hom_nay, [
        {"mat_hang": "banh", "dau_ca": 10, "nhap_trong_ca": 0, "cuoi_ca": 7, "hao_hut_ghi": 0},
    ])
    body = client.get("/api/v1/hao-hut?ky=hom_nay", headers=headers(client)).json()
    banh = next(d for d in body["dong"] if d["mat_hang"] == "banh")
    assert banh["thuc_te"] == 3.0


def test_hao_hut_ky_la_ve_hom_nay() -> None:
    """Kỳ không hợp lệ không được lọc ra danh sách rỗng im lặng."""
    r = client.get("/api/v1/hao-hut?ky=linh-tinh", headers=headers(client))
    assert r.status_code == 200
    assert r.json()["ky"] == "hom_nay"


def test_nguong_tra_ve_gia_tri_dang_ap_dung() -> None:
    """Ngưỡng đọc từ config, có ngưỡng riêng theo mặt hàng."""
    r = client.get("/api/v1/hao-hut/nguong", headers=headers(client))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mac_dinh_phan_tram"] > 0
    assert body["nghiem_trong_phan_tram"] >= body["mac_dinh_phan_tram"]
    assert isinstance(body["theo_mat_hang"], dict)


def test_nguong_it_quyen_van_doc_duoc() -> None:
    """Nhân viên đọc ngưỡng được — chỉ đọc, không side effect."""
    r = client.get("/api/v1/hao-hut/nguong", headers=headers(client, "minh"))
    assert r.status_code == 200


# ── Ghi hao hụt ───────────────────────────────────────────────────────────────


def test_ghi_hao_hut_luu_du_truong() -> None:
    r = client.post(
        "/api/v1/hao-hut",
        json={
            "mat_hang": "sua_tuoi",
            "so_luong": 2,
            "don_vi": "hộp",
            "nguyen_nhan": "het_han",
            "ghi_chu": "Hộp mở quá lâu",
            "thu": "T3",
        },
        headers=headers(client),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["mat_hang"] == "sua_tuoi"
    assert body["so_luong"] == 2
    assert body["nguyen_nhan"] == "het_han"

    luu = [x for x in kv_get("waste_notes", []) if isinstance(x, dict) and x.get("id") == body["id"]]
    assert len(luu) == 1


def test_ghi_hao_hut_co_ghi_vet_audit() -> None:
    """Lỗ đã sửa: đường ghi cũ không để lại vết nào trong sổ vết (ADR-008)."""
    r = client.post(
        "/api/v1/hao-hut",
        json={"mat_hang": "da", "so_luong": 1, "nguyen_nhan": "roi_do"},
        headers=headers(client),
    )
    assert r.status_code == 200, r.text
    ma = r.json()["id"]

    # Sổ vết là mặt quản lý — đọc bằng tài khoản quản lý.
    vet = client.get("/api/v1/audit?limit=200", headers=headers(client, "lan")).json()["items"]
    assert any(
        x.get("hanh") == "hao_hut" and str((x.get("payload") or {}).get("entity_id")) == ma
        for x in vet
    ), "ghi hao hụt phải có vết audit"


def test_ghi_hao_hut_tu_choi_so_am() -> None:
    r = client.post(
        "/api/v1/hao-hut",
        json={"mat_hang": "da", "so_luong": -1},
        headers=headers(client),
    )
    assert r.status_code == 422


def test_ghi_hao_hut_tu_choi_mat_hang_rong() -> None:
    r = client.post(
        "/api/v1/hao-hut",
        json={"mat_hang": "   ", "so_luong": 1},
        headers=headers(client),
    )
    assert r.status_code == 422


def test_ghi_hao_hut_roi_vao_tong_hao_hut() -> None:
    """Ghi xong thì dòng mới phải xuất hiện trong xếp hạng nguyên nhân ngay."""
    client.post(
        "/api/v1/hao-hut",
        json={"mat_hang": "tra", "so_luong": 5, "nguyen_nhan": "pha_sai"},
        headers=headers(client),
    )
    body = client.get("/api/v1/hao-hut?ky=all", headers=headers(client)).json()
    nn = {x["nguyen_nhan"]: x for x in body["nguyen_nhan_hang_dau"]}
    assert nn.get("pha_sai", {}).get("so_lan", 0) >= 1


# ── Danh mục gợi ý ────────────────────────────────────────────────────────────


def test_danh_muc_gop_tu_ba_nguon() -> None:
    _nap_menu({"id": "mon_test_hh", "ten": "Món thử", "gia": 20000, "an": False, "bom": {"matcha": 5, "da": 100}})
    r = client.get("/api/v1/hao-hut/danh-muc", headers=headers(client, "lan"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert "matcha" in body["items"]
    assert "matcha" in body["tu_cong_thuc"]


def test_danh_muc_can_quyen_quan_ly() -> None:
    """Danh mục là thông tin vận hành chi tiết — nhân viên không cần."""
    r = client.get("/api/v1/hao-hut/danh-muc", headers=headers(client, "minh"))
    assert r.status_code == 403


# ── Không đổi hành vi cũ ──────────────────────────────────────────────────────


def test_duong_waste_cu_van_chay() -> None:
    """`/api/v1/waste` là bề mặt cũ mà UI và e2e đang dùng — không được vỡ."""
    r = client.post(
        "/api/v1/waste",
        json={"thu": "T2", "ghi_chu": "Kiểm tra đường cũ"},
        headers=headers(client),
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    g = client.get("/api/v1/waste", headers=headers(client))
    assert g.status_code == 200
    assert "items" in g.json()


def test_duong_waste_cu_gio_co_ghi_vet() -> None:
    """Vá lỗ: `POST /api/v1/waste` trước đây ghi dữ liệu mà không có vết."""
    client.post(
        "/api/v1/waste",
        json={"thu": "T4", "ghi_chu": "Hao hụt có vết"},
        headers=headers(client),
    )
    vet = client.get("/api/v1/audit?limit=200", headers=headers(client, "lan")).json()["items"]
    assert any(x.get("hanh") == "hao_hut" for x in vet)
