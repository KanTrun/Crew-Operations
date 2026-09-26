"""Danh mục sản phẩm & ảnh thẻ — plan 260923-1736 phase 6.

Khẳng định:

1. Danh mục phủ đủ nhóm sản phẩm, mã nguyên liệu khớp giữa ba nguồn.
2. Nạp danh mục là idempotent và không đụng món ngoài danh mục.
3. Ảnh sinh tại máy, tất định (cùng id ⇒ cùng byte), không cần mạng.
4. `GET /api/v1/menu/{id}/anh` trả ảnh cho **mọi** món kể cả chưa chạy script sinh.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ca_api.interfaces.http.main import app
from ca_api.persist import menu_get, menu_list, menu_upsert
from ca_api.services.menu_image import KICH_THUOC, bam_anh, bytes_anh, ve_anh
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)

ROOT = Path(__file__).resolve().parents[4]
DANH_MUC = ROOT / "data" / "seed" / "danh-muc.json"


def _doc() -> dict[str, Any]:
    return json.loads(DANH_MUC.read_text(encoding="utf-8"))


def _mon() -> list[dict[str, Any]]:
    return list(_doc()["mon"])


# ── Danh mục ──────────────────────────────────────────────────────────────────


def test_danh_muc_du_nhom_san_pham() -> None:
    """Phải có cà phê, trà, nước đóng chai, sinh tố, bánh và nguyên liệu."""
    nhom = {m["nhom"] for m in _mon()}
    for bat_buoc in ("ca_phe", "tra", "nuoc_dong_chai", "sinh_to", "banh", "nguyen_lieu"):
        assert bat_buoc in nhom, f"danh mục thiếu nhóm {bat_buoc}"


def test_danh_muc_du_lon() -> None:
    """Ít nhất 45 món — quán thật có menu dài hơn bốn món mặc định."""
    assert len(_mon()) >= 45


def test_moi_mon_co_cong_thuc() -> None:
    """Không có định mức thì không tính được vế lý thuyết của hao hụt."""
    for m in _mon():
        assert m.get("bom"), f"{m['id']} thiếu công thức"
        for nl, dm in m["bom"].items():
            assert dm > 0, f"{m['id']}/{nl} định mức phải > 0"


def test_ma_mon_khong_trung() -> None:
    ids = [m["id"] for m in _mon()]
    assert len(ids) == len(set(ids)), "có mã món trùng"


def test_ma_nguyen_lieu_khop_voi_bom_editor() -> None:
    """Mã nguyên liệu phải khớp danh sách chọn ở `bom-editor.tsx`.

    Lệch mã thì công thức lưu từ UI và công thức nạp từ danh mục là hai hệ khác
    nhau, và phép tính hao hụt sẽ không ghép được hai vế.
    """
    hop_le = {
        "ca_phe_hat", "cafe_g", "sua_tuoi", "sua_dac", "tra", "matcha", "dao",
        "da", "banh", "ly", "nuoc_dong_chai", "duong", "syrup", "kem",
        "ong_hut", "trai_cay",
    }
    for m in _mon():
        la = set(m["bom"]) - hop_le
        assert not la, f"{m['id']} dùng mã nguyên liệu lạ: {la}"


def test_co_nuoc_dong_chai_trong_danh_muc() -> None:
    """Nhóm nước đóng chai là thứ trước đây hoàn toàn thiếu."""
    nuoc = [m for m in _mon() if m["nhom"] == "nuoc_dong_chai"]
    assert len(nuoc) >= 5


def test_danh_muc_qua_kiem_tra_cua_script() -> None:
    """`kiem_tra()` của script nạp phải nói danh mục hợp lệ."""
    import importlib.util
    import sys

    path = ROOT / "scripts" / "seed_danh_muc.py"
    spec = importlib.util.spec_from_file_location("seed_danh_muc", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    assert mod.kiem_tra(_doc()) == []


# ── Nạp idempotent ────────────────────────────────────────────────────────────


def test_nap_danh_muc_idempotent() -> None:
    """Nạp hai lần không nhân bản, và món ngoài danh mục còn nguyên."""
    import importlib.util
    import sys

    path = ROOT / "scripts" / "seed_danh_muc.py"
    spec = importlib.util.spec_from_file_location("seed_danh_muc", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    menu_upsert({"id": "mon_quan_tu_them", "ten": "Món quán tự thêm", "gia": 99000, "bom": {"da": 50}})

    mod.nap(_doc())
    lan1 = {m["id"] for m in menu_list(gom_an=True)}
    mod.nap(_doc())
    lan2 = {m["id"] for m in menu_list(gom_an=True)}

    assert lan1 == lan2, "nạp lần hai làm đổi danh mục"
    assert "mon_quan_tu_them" in lan2, "món ngoài danh mục bị xoá"
    assert len([m for m in _mon() if m["id"] in lan2]) == len(_mon())


# ── Ảnh sinh tại máy ──────────────────────────────────────────────────────────


def test_anh_tat_dinh_cung_id_cung_byte() -> None:
    """Cùng món ⇒ cùng byte. Không có `random` thì ảnh mới không nhảy loạn."""
    m = {"id": "latte", "ten": "Latte", "gia": 42000, "nhom": "ca_phe"}
    assert bytes_anh(m) == bytes_anh(m)
    assert bam_anh(m) == bam_anh(m)


def test_anh_khac_mon_thi_khac_byte() -> None:
    a = bytes_anh({"id": "latte", "ten": "Latte", "gia": 42000, "nhom": "ca_phe"})
    b = bytes_anh({"id": "tra_dao", "ten": "Trà đào", "gia": 35000, "nhom": "tra"})
    assert a != b


def test_anh_dung_kich_thuoc() -> None:
    img = ve_anh({"id": "da", "ten": "Đá", "nhom": "nguyen_lieu"})
    assert img.size == (KICH_THUOC, KICH_THUOC)


def test_anh_thieu_id_thi_bao_loi() -> None:
    import pytest

    with pytest.raises(ValueError):
        ve_anh({"ten": "Không có id"})


def test_anh_la_png_hop_le() -> None:
    """Chữ ký PNG — để `<img>` render được, không trả bytes rác."""
    raw = bytes_anh({"id": "bac_xiu", "ten": "Bạc xỉu", "gia": 32000, "nhom": "ca_phe"})
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_moi_mon_trong_danh_muc_sinh_duoc_anh() -> None:
    """Không món nào được vỡ khi sinh ảnh — kể cả tên dài, giá 0, nhóm lạ."""
    for m in _mon():
        raw = bytes_anh({"id": m["id"], "ten": m["ten"], "gia": m["gia"], "nhom": m["nhom"]})
        assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"{m['id']} không ra PNG"


# ── Bề mặt HTTP ảnh ───────────────────────────────────────────────────────────


def test_anh_mon_chua_tai_len_van_tra_anh() -> None:
    """Bậc 3: máy chưa chạy script sinh ảnh thì endpoint tự sinh tại chỗ.

    Đây là chỗ chốt ràng buộc demo offline (§14.9) — lưới menu không được rơi về
    chữ cái đầu chỉ vì thiếu file.
    """
    menu_upsert({"id": "mon_anh_tu_sinh", "ten": "Món ảnh tự sinh", "gia": 30000, "bom": {"ca_phe_hat": 18}})
    r = client.get("/api/v1/menu/mon_anh_tu_sinh/anh")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/png")
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_anh_mon_khong_ton_tai_tra_404() -> None:
    r = client.get("/api/v1/menu/khong_co_mon_nay/anh")
    assert r.status_code == 404


def test_anh_mon_id_khong_hop_le_tra_404() -> None:
    """Mã món sai định dạng không được đi vào đường sinh ảnh."""
    r = client.get("/api/v1/menu/AB!!/anh")
    assert r.status_code == 404


def test_anh_mon_tu_tai_len_thang_anh_tu_sinh() -> None:
    """Ảnh do quán tải lên phải thắng ảnh tự sinh — không được ghi đè ảnh thật."""
    from ca_api.interfaces.http.pos import _menu_image_dir

    menu_upsert({"id": "mon_co_anh_that", "ten": "Món có ảnh thật", "gia": 30000, "bom": {"da": 100}})
    # PNG 1×1 hợp lệ, nhỏ nhất có thể
    that = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )
    (_menu_image_dir() / "mon_co_anh_that.png").write_bytes(that)

    r = client.get("/api/v1/menu/mon_co_anh_that/anh")
    assert r.status_code == 200
    assert r.content == that, "ảnh tự sinh đã ghi đè ảnh quán tải lên"


def test_anh_tra_cho_moi_mon_da_nap() -> None:
    """Nạp danh mục rồi mọi món phải trả ảnh — không món nào 404."""
    for m in _mon()[:12]:
        menu_upsert({
            "id": m["id"],
            "ten": m["ten"],
            "gia": m["gia"],
            "bom": {str(k): float(v) for k, v in m["bom"].items()},
        })
        r = client.get(f"/api/v1/menu/{m['id']}/anh")
        assert r.status_code == 200, f"{m['id']} không trả ảnh"
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_anh_public_khong_can_token() -> None:
    """`<img>` không gửi được Bearer — endpoint ảnh phải public."""
    menu_upsert({"id": "mon_anh_public", "ten": "Món ảnh public", "gia": 30000, "bom": {"da": 100}})
    r = client.get("/api/v1/menu/mon_anh_public/anh")
    assert r.status_code == 200


def test_menu_quan_tri_thay_du_mon_sau_khi_nap() -> None:
    """Nạp danh mục rồi chủ quán phải thấy đủ món trong trang quản trị."""
    import importlib.util
    import sys

    path = ROOT / "scripts" / "seed_danh_muc.py"
    spec = importlib.util.spec_from_file_location("seed_danh_muc", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.nap(_doc())

    r = client.get("/api/v1/menu/quan-tri", headers=headers(client, "hung"))
    assert r.status_code == 200, r.text
    ids = {m["id"] for m in r.json()["items"]}
    for m in _mon():
        assert m["id"] in ids, f"{m['id']} không có trong menu quản trị"


def test_nuoc_dong_chai_co_trong_menu_mac_dinh() -> None:
    """Danh mục mặc định của persist phải có nước đóng chai và bánh kèm."""
    from ca_api.persist import _MENU_MAC_DINH

    nguyen_lieu = {k for _, _, _, bom, _ in _MENU_MAC_DINH for k in bom}
    assert "nuoc_dong_chai" in nguyen_lieu, "menu mặc định thiếu nước đóng chai"
    assert "banh" in nguyen_lieu, "menu mặc định thiếu bánh kèm"


def test_menu_get_tra_dung_mon_vua_upsert() -> None:
    menu_upsert({"id": "mon_kiem_get", "ten": "Món kiểm get", "gia": 12345, "bom": {"tra": 8}})
    mon = menu_get("mon_kiem_get")
    assert mon is not None
    assert mon["gia"] == 12345
    assert mon["bom"] == {"tra": 8}
