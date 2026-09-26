# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""TKB upload → confirm → store."""

from __future__ import annotations

from ca_api.interfaces.http.main import app
from ca_api.persist import kv_get
from fastapi.testclient import TestClient

from unit.auth_util import headers

client = TestClient(app)


def test_tkb_upload_fixture_and_confirm() -> None:
    nv = headers(client, "minh")
    r = client.post(
        "/api/v1/tkb/upload",
        data={"fixture_id": "tkb_01"},
        headers=nv,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rows"] or body["spans"]
    assert body["upload_id"].startswith("fixture:")

    khoang = body.get("rows") or [
        {"thu": s["day"], "start": s["start"], "end": s["end"]} for s in body.get("spans", [])
    ]
    conf = client.post(
        "/api/v1/tkb/confirm",
        json={
            "tuan_iso": "2026-W39",
            "khoang_ban": khoang,
            "source_id": body.get("source_id", "tkb_01"),
        },
        headers=nv,
    )
    assert conf.status_code == 200, conf.text
    assert conf.json()["n"] >= 1
    assert conf.json()["tuan_iso"] == "2026-W39"

    mine = client.get("/api/v1/tkb/mine?tuan_iso=2026-W39", headers=nv)
    assert mine.status_code == 200
    assert mine.json()["item"]["khoang_ban"]
    assert mine.json()["item"]["tuan_iso"] == "2026-W39"

    stored = kv_get("tkb_nv_by_week", {})
    assert mine.json()["nv_id"] in stored["2026-W39"]


def test_tkb_confirm_keeps_multiple_weeks_independent() -> None:
    nv = headers(client, "minh")
    w39 = [{"thu": "T2", "start": "07:00", "end": "12:00"}]
    w40 = [{"thu": "T4", "start": "12:00", "end": "17:00"}]

    for week, blocks in [("2026-W39", w39), ("2026-W40", w40)]:
        response = client.post(
            "/api/v1/tkb/confirm",
            json={"tuan_iso": week, "khoang_ban": blocks},
            headers=nv,
        )
        assert response.status_code == 200, response.text

    mine_w39 = client.get("/api/v1/tkb/mine?tuan_iso=2026-W39", headers=nv)
    mine_w40 = client.get("/api/v1/tkb/mine?tuan_iso=2026-W40", headers=nv)
    assert mine_w39.json()["item"]["khoang_ban"] == w39
    assert mine_w40.json()["item"]["khoang_ban"] == w40


def test_tkb_confirm_empty_rejected() -> None:
    nv = headers(client, "minh")
    r = client.post("/api/v1/tkb/confirm", json={"khoang_ban": []}, headers=nv)
    assert r.status_code == 400


def test_tkb_confirm_invalid_week_rejected() -> None:
    nv = headers(client, "minh")
    r = client.post(
        "/api/v1/tkb/confirm",
        json={
            "tuan_iso": "2026-W00",
            "khoang_ban": [{"thu": "T2", "start": "07:00", "end": "12:00"}],
        },
        headers=nv,
    )
    assert r.status_code == 422


def test_tkb_confirm_rejects_invalid_or_reversed_time_ranges() -> None:
    nv = headers(client, "minh")
    for block in (
        {"thu": "T2", "start": "25:00", "end": "26:00"},
        {"thu": "T2", "start": "12:00", "end": "07:00"},
        {"thu": "T2", "start": "08:99", "end": "12:00"},
    ):
        response = client.post(
            "/api/v1/tkb/confirm",
            json={"tuan_iso": "2026-W39", "khoang_ban": [block]},
            headers=nv,
        )
        assert response.status_code == 400, response.text


def test_tkb_upload_svg_rejected() -> None:
    nv = headers(client, "minh")
    svg_content = b"<svg xmlns='http://www.w3.org/2000/svg'><text>test</text></svg>"
    r = client.post(
        "/api/v1/tkb/upload",
        files={"file": ("test.svg", svg_content, "image/svg+xml")},
        headers=nv,
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "dinh_dang"


# ─────────────────────────────────────────────────────────────────────────────
# Tác động lên lịch tuần: "up TKB xong mà lịch không tự đổi"
#
# Lỗi cũ: `tkb_confirm` ghi khung bận rồi kết thúc, không cho biết lịch tuần
# đang có ca nào vi phạm khung mới. Người dùng up ảnh, thấy "Đã gắn", nhưng
# lịch vẫn giữ ca cũ — không có gì nói cho họ biết phải xếp lại.
# ─────────────────────────────────────────────────────────────────────────────


def test_tkb_confirm_tra_khung_cu_va_tac_dong() -> None:
    """Lần confirm thứ hai phải trả khung CŨ để UI hiện được trước/sau."""
    nv = headers(client, "minh")
    week = "2026-W41"
    cu = [{"thu": "T3", "start": "08:00", "end": "11:00"}]
    moi = [{"thu": "T3", "start": "09:00", "end": "13:00"}]

    first = client.post(
        "/api/v1/tkb/confirm", json={"tuan_iso": week, "khoang_ban": cu}, headers=nv
    )
    assert first.status_code == 200, first.text
    assert first.json()["khoang_cu"] == []

    second = client.post(
        "/api/v1/tkb/confirm", json={"tuan_iso": week, "khoang_ban": moi}, headers=nv
    )
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["khoang_cu"] == cu
    assert body["khoang_ban"] == moi
    assert body["tac_dong"]["tuan_iso"] == week
    assert "can_chay_lai" in body["tac_dong"]
    assert "trang_thai" in body["tac_dong"]


def test_tkb_tac_dong_bao_ca_bi_dung_khung_ban() -> None:
    """Khung bận mới trùng ca đã xếp → `can_chay_lai=True` + nêu đúng ca.

    Dựng lịch tuần thật bằng cách ghi thẳng kv `phan_cong_by_week` (đó là store
    mà solver đọc), rồi mới confirm khung bận đè lên chính ca đó.
    """
    from ca_api.persist import kv_set

    nv = headers(client, "minh")
    week = "2026-W42"
    # T2-sáng của seed là 07:00–12:00; đặt chính "minh" vào ca đó.
    ca_id = _ca_id_cua_seed(thu="T2", khung="sang")
    assert ca_id, "seed ca_mau_21 phải có ca T2-sáng"

    nv_id = client.get("/api/v1/tkb/mine?tuan_iso=" + week, headers=nv).json()["nv_id"]
    kv_set("phan_cong_by_week", {week: {ca_id: [nv_id]}})
    try:
        r = client.post(
            "/api/v1/tkb/confirm",
            json={"tuan_iso": week, "khoang_ban": [{"thu": "T2", "start": "08:00", "end": "10:00"}]},
            headers=nv,
        )
        assert r.status_code == 200, r.text
        tac_dong = r.json()["tac_dong"]
        assert tac_dong["can_chay_lai"] is True
        assert tac_dong["so_ca_bi_dung"] == 1
        assert tac_dong["ca_bi_dung"][0]["ca_id"] == ca_id
        assert tac_dong["ca_bi_dung"][0]["khoang_ban"] == "08:00-10:00"
    finally:
        kv_set("phan_cong_by_week", {})


def test_tkb_tac_dong_khong_bao_dong_khi_khung_ban_nam_ngoai_ca() -> None:
    """Khung bận mới KHÔNG trùng ca nào → không được hù người dùng."""
    from ca_api.persist import kv_set

    nv = headers(client, "minh")
    week = "2026-W43"
    ca_id = _ca_id_cua_seed(thu="T2", khung="sang")
    assert ca_id
    nv_id = client.get("/api/v1/tkb/mine?tuan_iso=" + week, headers=nv).json()["nv_id"]
    kv_set("phan_cong_by_week", {week: {ca_id: [nv_id]}})
    try:
        r = client.post(
            "/api/v1/tkb/confirm",
            # Ca T2-sáng là 07:00–12:00; khung 17:00–20:00 không giao nhau.
            json={"tuan_iso": week, "khoang_ban": [{"thu": "T2", "start": "17:00", "end": "20:00"}]},
            headers=nv,
        )
        assert r.status_code == 200, r.text
        tac_dong = r.json()["tac_dong"]
        assert tac_dong["can_chay_lai"] is False
        assert tac_dong["so_ca_bi_dung"] == 0
    finally:
        kv_set("phan_cong_by_week", {})


def test_tkb_xep_lai_chi_quan_ly() -> None:
    """Nhân viên không được tự chạy lại lịch của cả tuần."""
    nv = headers(client, "minh")
    r = client.post("/api/v1/tkb/xep-lai", json={"tuan_iso": "2026-W40"}, headers=nv)
    assert r.status_code == 403
    assert r.json()["detail"] == "chi_quan_ly_xep_lai"


def test_tkb_xep_lai_chuyen_tuan_sang_cho_duyet_va_tra_diff() -> None:
    """Chạy lại xếp lịch → tuần về `cho_duyet`, trả diff có cấu trúc.

    KHÔNG tự công bố: đây là điểm cốt lõi để "up TKB xong không update" không bị
    thay bằng "up TKB xong tự công bố đè lên lịch đang chạy".
    """
    ql = headers(client, "lan")
    week = "2026-W44"
    r = client.post("/api/v1/tkb/xep-lai", json={"tuan_iso": week}, headers=ql)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tuan_iso"] == week
    if body["ok"]:
        assert body["trang_thai"] == "cho_duyet"
        assert body["trang_thai"] != "da_cong_bo"
        diff = body["diff"]
        for key in ("them", "bot", "hoan_doi", "doi_giua_hai_ca", "giu_nguyen", "khong_so_sanh_duoc"):
            assert key in diff
        assert isinstance(body["tom_tat"], str)
    else:
        # Không đủ người khả dụng: phải nói RÕ vì sao, không im lặng.
        assert body["ly_do"] == "khong_xep_duoc"
        assert isinstance(body["danh_sach_xung_dot"], list)


def test_tkb_khung_ban_9h_va_12h_khong_bi_loc() -> None:
    """Hồi quy: khung có số 0 đầu (09:00) và khung 12:00–23:00 phải LƯU được.

    Đây là bản sao ở tầng API của lỗi ô nhập giờ: nếu UI gửi lên "9:00" (mất số
    0) thì `_clean_khoang_api` lọc sạch → `khoang_rong`. Chốt rằng server CHẤP
    NHẬN đúng "09:00" để lỗi nằm ở tầng hiển thị, không phải tầng validate.
    """
    nv = headers(client, "minh")
    r = client.post(
        "/api/v1/tkb/confirm",
        json={"tuan_iso": "2026-W45", "khoang_ban": [{"thu": "CN", "start": "09:00", "end": "12:00"}]},
        headers=nv,
    )
    assert r.status_code == 200, r.text
    assert r.json()["khoang_ban"] == [{"thu": "CN", "start": "09:00", "end": "12:00"}]

    r2 = client.post(
        "/api/v1/tkb/confirm",
        json={"tuan_iso": "2026-W45", "khoang_ban": [{"thu": "CN", "start": "12:00", "end": "23:00"}]},
        headers=nv,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["khoang_ban"] == [{"thu": "CN", "start": "12:00", "end": "23:00"}]


def _ca_id_cua_seed(*, thu: str, khung: str) -> str | None:
    """Tra ca_id trong seed `ca_mau_21` theo thứ + khung (dùng cho test tác động)."""
    import json as _json

    from ca_api.interfaces.http.sprint3 import SEED

    if not SEED.exists():
        return None
    thu_map = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}
    doc = _json.loads(SEED.read_text(encoding="utf-8"))
    for c in doc.get("ca_mau_21", []):
        if thu_map.get(int(c.get("ngay_offset", 1))) == thu and str(c.get("khung")) == khung:
            return str(c["id"])
    return None


