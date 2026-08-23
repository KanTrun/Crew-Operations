"""Sáu bề mặt vận hành phải CÓ GÌ MÀ XEM, và phải tất định.

Người dùng phàn nàn "web rất nhiều chỗ trống". Nguyên nhân không phải CSS: sáu
bề mặt dữ liệu rỗng ruột vì bộ sinh fixture chỉ sinh nhân viên + ca mẫu + lịch
sử, không sinh bản ghi vận hành nào. Bộ kiểm này giữ ba thứ:

- `scripts/generate_fixture_data.py` sinh đủ 6 tập, và sinh lại cho kết quả y hệt
  (không có seed ngẫu nhiên nào lọt vào);
- `scripts/seed_operational.py` nạp vào đúng khoá store, chạy nhiều lần không
  nhân bản, và sáu endpoint sau đó không còn rỗng;
- luật cẩm nang đủ 5 loại §9.1, có luật bị VF-RULE loại kèm lý do thật, có luật
  tự tắt — hai thứ kịch bản demo phút 6:00 phải chiếu được.

Mọi bản ghi mang `synthetic: True` và `nguon="mo_phong_fixture"`: bộ kiểm cũng
canh việc đó, để không ai lỡ tay gắn nhãn quán thật cho dữ liệu dựng lại.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from ca_api.interfaces.http.main import app
from ca_gates.vf_rule import LOAI_HOP_LE, validate_rule
from fastapi.testclient import TestClient

from unit.auth_util import headers

ROOT = Path(__file__).resolve().parents[4]
BO_SINH = ROOT / "scripts" / "generate_fixture_data.py"
BO_NAP = ROOT / "scripts" / "seed_operational.py"
SAMPLE = ROOT / "data" / "seed" / "sample.json"

TAP_VAN_HANH = (
    "viec_treo",
    "inbox_rang_buoc",
    "luat_cam_nang",
    "hao_phi",
    "kiem_ke",
    "ghi_nhan_sua",
    "tieu_thu",
)

client = TestClient(app)


def _nap_module(path: Path, ten: str) -> Any:
    spec = importlib.util.spec_from_file_location(ten, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ten] = mod
    spec.loader.exec_module(mod)
    return mod


def _sinh_van_hanh(ten: str) -> dict[str, Any]:
    """Chạy lại đúng chuỗi RNG của main() rồi lấy phần vận hành.

    build_tkb không dùng RNG nên bỏ qua được; build_messages thì có, phải gọi.
    """
    mod = _nap_module(BO_SINH, ten)
    staff = mod.build_staff(25)
    history = mod.build_history(staff, 8)
    ca21 = mod.build_shifts_for_week(1)
    mod.build_messages(200)
    out: dict[str, Any] = mod.build_van_hanh(staff, ca21, history)
    return out


@pytest.fixture(scope="module")
def sample() -> dict[str, Any]:
    assert SAMPLE.exists(), "chạy `python scripts/generate_fixture_data.py` trước"
    raw: dict[str, Any] = json.loads(SAMPLE.read_text(encoding="utf-8"))
    return raw


@pytest.fixture
def bo_nap() -> Any:
    return _nap_module(BO_NAP, "seed_operational_test")


# ── Bộ sinh ───────────────────────────────────────────────────────────────
def test_bo_sinh_tat_dinh() -> None:
    lan_1 = _sinh_van_hanh("gen_fixture_lan_1")
    lan_2 = _sinh_van_hanh("gen_fixture_lan_2")
    assert lan_1 == lan_2, "bộ sinh không tất định — có seed ngẫu nhiên lọt vào"


def test_bo_sinh_khop_voi_sample_da_ghi(sample: dict[str, Any]) -> None:
    lai = _sinh_van_hanh("gen_fixture_doi_chieu")
    for khoa in TAP_VAN_HANH:
        assert sample[khoa] == lai[khoa], f"`{khoa}` trong sample.json lệch bộ sinh"


def test_sample_co_du_sau_tap_va_deu_mang_nhan_fixture(sample: dict[str, Any]) -> None:
    for khoa in TAP_VAN_HANH:
        rows = sample[khoa]
        assert rows, f"`{khoa}` rỗng"
        for r in rows:
            assert r["synthetic"] is True, f"{khoa}: mất nhãn synthetic"
            assert r["nguon"] == "mo_phong_fixture", f"{khoa}: nhãn nguồn sai — {r['nguon']}"


def test_viec_treo_du_ba_trang_thai(sample: dict[str, Any]) -> None:
    rows = sample["viec_treo"]
    assert len(rows) >= 18
    assert {r["trang_thai"] for r in rows} == {"xong", "dang_cho", "qua_han"}
    ca_that = {c["id"] for c in sample["ca_mau_21"]}
    for r in rows:
        assert r["ca_id"] in ca_that, "việc treo gắn vào ca không tồn tại"
        assert r["noi_dung"].strip() and r["han"] and r["nguoi_nhan"]
    qua_han = [r for r in rows if r["trang_thai"] == "qua_han"]
    assert qua_han
    for r in qua_han:
        assert r["han"] < r["moc_tinh_han"], "gọi là quá hạn mà hạn lại ở tương lai"
        assert not r["ca_sau_da_nhan"], "quá hạn mà ca sau đã nhận thì không còn là quá hạn"


def test_viec_treo_co_ca_viec_ca_sau_da_nhan_va_viec_con_mo(sample: dict[str, Any]) -> None:
    """Số #8 đọc đúng ba nhóm: ca sau đã nhận · còn mở · quá hạn."""
    rows = sample["viec_treo"]
    da_nhan = [r for r in rows if r["ca_sau_da_nhan"]]
    con_mo = [r for r in rows if r["trang_thai"] == "dang_cho" and not r["ca_sau_da_nhan"]]
    assert da_nhan, "không có việc nào được ca sau nhận"
    assert con_mo, "không có việc nào còn mở — trang /treo mất một nhóm"
    for r in da_nhan:
        assert r["ca_sau_nhan_luc"] and r["ca_sau_nhan_luc"] <= (r["xong_luc"] or r["han"]), (
            f"{r['id']}: nhận sau khi xong / sau hạn thì vô nghĩa"
        )
    for r in rows:
        if r["trang_thai"] == "xong":
            assert r["ca_sau_da_nhan"] and r["xong_luc"], "xong mà không ai nhận"
    # Trải trên nhiều ca và nhiều thứ, không dồn hết vào một ca.
    assert len({r["ca_id"] for r in rows}) >= 10
    assert len({r["thu"] for r in rows}) >= 5


def test_inbox_co_it_nhat_hai_muc_cho_duyet(sample: dict[str, Any]) -> None:
    rows = sample["inbox_rang_buoc"]
    assert len(rows) >= 14
    assert sum(1 for r in rows if r["trang_thai"] == "cho_duyet") >= 2
    assert {r["trang_thai"] for r in rows} <= {"cho_duyet", "duyet", "tu_choi"}
    assert {r["agent"] for r in rows} == {"ag_msg", "ag_handover", "ag_tkb", "ag_waste"}
    for r in rows:
        assert 0.0 <= r["do_tin_cay"] <= 1.0
        assert r["tom_tat"].strip()


def test_inbox_du_sau_y_dinh_ag_msg(sample: dict[str, Any]) -> None:
    """Nhãn `y_dinh` do bộ sinh ghi phải khớp AG-MSG thật, và đủ cả 6 ý định.

    Không tự chấm điểm mình: gọi `ca_agents.ag_msg.classify` phân loại lại câu
    tóm tắt. Dán nhãn cho đẹp mà câu chữ không có từ khoá thì test đỏ.
    """
    from ca_agents.ag_msg import INTENTS, classify

    thay = set()
    for r in sample["inbox_rang_buoc"]:
        that = classify(r["tom_tat"]).intent
        assert r["y_dinh"] == that, f"{r['id']}: nhãn {r['y_dinh']} nhưng AG-MSG đọc ra {that}"
        thay.add(that)
    assert thay == set(INTENTS), f"thiếu ý định: {set(INTENTS) - thay}"


def test_luat_du_nam_loai_co_luat_bi_loai_va_luat_tu_tat(sample: dict[str, Any]) -> None:
    rows = sample["luat_cam_nang"]
    assert len(rows) >= 12
    assert {r["loai"] for r in rows} == set(LOAI_HOP_LE), "thiếu loại luật §9.1"
    assert {r["loai_ho_so"] for r in rows} >= {"nguyen_nhan_hao_hut"}

    bi_loai = [r for r in rows if r["trang_thai"] == "loai"]
    assert bi_loai, "không có luật nào bị VF-RULE loại — demo phút 6:00 không có gì chiếu"
    for r in bi_loai:
        assert r["vf_rule"] not in {"", "dat"}, "bị loại mà không ghi lý do"

    tu_tat = [r for r in rows if r["trang_thai"] == "tu_tat"]
    assert tu_tat, "không có luật nào tự tắt"
    for r in tu_tat:
        assert r["ti_le_dung"] < 0.8, "tự tắt phải vì tỉ lệ dùng dưới 80%"

    assert {r["trang_thai"] for r in rows} >= {
        "de_xuat",
        "qua_vf_rule",
        "hieu_luc",
        "tu_choi",
        "tu_tat",
        "loai",
    }
    for r in rows:
        assert len(r["bang_chung"]) >= 3, f"{r['id']}: dưới 3 bằng chứng"
        assert isinstance(r["dieu_kien"], dict) and r["dieu_kien"]
        assert r["cau"].strip()
        assert r["tap_su_dung"] <= r["tap_su_tong"]
        assert r["da_ap_dung"] >= 0 and r["bi_ghi_de"] >= 0


def test_nhan_vf_rule_cua_tung_luat_dung_voi_cong_that(sample: dict[str, Any]) -> None:
    """Không tự nhận "bị loại": cho VF-RULE thật chấm lại từng luật."""
    for r in sample["luat_cam_nang"]:
        kq = validate_rule(r)
        if r["trang_thai"] == "loai":
            assert not kq.passed, f"{r['id']}: dán nhãn bị loại nhưng cổng cho qua"
            assert kq.reason == r["vf_rule"], f"{r['id']}: lý do loại không khớp cổng"
        else:
            assert kq.passed, f"{r['id']}: cổng loại ({kq.reason}) mà dữ liệu ghi là đạt"


def test_hao_phi_gom_duoc_cum(sample: dict[str, Any]) -> None:
    """Ghi chú hao phí phải để AG-WASTE thật gom được cụm theo thứ."""
    from ca_agents.ag_waste import cluster

    rows = sample["hao_phi"]
    assert len(rows) >= 16
    for r in rows:
        assert r["ghi_chu"].strip() and r["nguyen_nhan"] and r["mat_hang"]
        assert r["so_luong"] >= 1
        assert r["thu"] in {"T2", "T3", "T4", "T5", "T6", "T7", "CN"}

    # Nguyên nhân lặp lại theo thứ: mỗi thứ chỉ một nguyên nhân, và ≥1 thứ lặp ≥3 lần.
    theo_thu: dict[str, set[str]] = {}
    for r in rows:
        theo_thu.setdefault(r["thu"], set()).add(r["nguyen_nhan"])
    assert all(len(v) == 1 for v in theo_thu.values()), "cùng một thứ mà nguyên nhân lung tung"
    dem = Counter(r["thu"] for r in rows)
    assert max(dem.values()) >= 3, "không thứ nào lặp đủ 3 lần"

    cum = cluster([(r["thu"], r["ghi_chu"]) for r in rows])
    assert len(cum) >= 5, f"AG-WASTE chỉ gom được {len(cum)} cụm"


def test_kiem_ke_du_de_tinh_so_9(sample: dict[str, Any]) -> None:
    """Bốn cột §4.3 phải khớp công thức, và tuần 1 phải có cột đếm tay."""
    rows = sample["kiem_ke"]
    assert len(rows) == 112, "8 tuần × 7 ngày × (ca sáng + ca tối)"
    assert {r["khung"] for r in rows} == {"sang", "toi"}
    co_dem_tay = 0
    for r in rows:
        assert len(r["muc"]) == 8, "phải kiểm kê đủ 8 mặt hàng trong danh_muc"
        for m in r["muc"]:
            suy_ra = m["dau_ca"] + m["nhap_trong_ca"] - m["cuoi_ca"] - m["hao_hut_ghi"]
            assert suy_ra == m["tieu_thu_suy_ra"], f"{r['id']}/{m['mat_hang']}: lệch §4.3"
            assert m["cuoi_ca"] >= 0
            if m["dem_tay_doc_lap"] is not None:
                co_dem_tay += 1
    assert co_dem_tay == 14 * 5, "cột đếm tay: 5 mặt hàng × 14 ca của tuần 1"


def test_ghi_nhan_sua_co_mau_lap_lai(sample: dict[str, Any]) -> None:
    rows = sample["ghi_nhan_sua"]
    assert len(rows) >= 30
    assert {r["loai"] for r in rows} == {"pin_ca", "nha_ca", "nhan_ca", "sua_lich"}
    lap = [r for r in rows if r.get("mau_lap") == "them_1_pha_che_t7_chieu"]
    assert len(lap) >= 3, "§9.2 cần ≥3 lần cùng mẫu mới coi là mẫu"
    for r in rows:
        assert r["truoc"] != r["sau"], "lần sửa mà trước == sau thì không phải sửa"
        assert r["ai"] and r["at"]


# ── Bộ nạp ────────────────────────────────────────────────────────────────
NGUONG_BE_MAT = {
    "/api/v1/viec-treo": 18,
    "/api/v1/inbox": 14,
    "/api/v1/inbox/rang-buoc": 14,
    "/api/v1/cam-nang": 12,
    "/api/v1/ghi-nhan-sua": 30,
    "/api/v1/waste": 1,
    "/api/v1/tieu-thu": 8,
}


def test_sau_be_mat_khong_con_rong_sau_khi_nap(bo_nap: Any) -> None:
    truoc = {}
    ql = headers(client, "lan")
    for ep in NGUONG_BE_MAT:
        truoc[ep] = len(client.get(ep, headers=ql).json()["items"])
    bo_nap.nap_tat_ca()
    for ep, toi_thieu in NGUONG_BE_MAT.items():
        r = client.get(ep, headers=ql)
        assert r.status_code == 200, r.text
        n = len(r.json()["items"])
        assert n >= toi_thieu, f"{ep}: {n} bản ghi, cần ≥{toi_thieu}"
        assert n > truoc[ep] or truoc[ep] >= toi_thieu, f"{ep}: nạp mà không thêm gì"


def test_nap_hai_lan_khong_nhan_ban(bo_nap: Any) -> None:
    ql = headers(client, "lan")
    bo_nap.nap_tat_ca()
    lan_1 = {ep: len(client.get(ep, headers=ql).json()["items"]) for ep in NGUONG_BE_MAT}
    bo_nap.nap_tat_ca()
    bo_nap.nap_tat_ca()
    lan_3 = {ep: len(client.get(ep, headers=ql).json()["items"]) for ep in NGUONG_BE_MAT}
    assert lan_1 == lan_3, "bộ nạp không idempotent"


def test_nap_khong_de_ai_nham_fixture_la_quan_that(bo_nap: Any) -> None:
    bo_nap.nap_tat_ca()
    ql = headers(client, "lan")
    treo = client.get("/api/v1/viec-treo", headers=ql).json()["items"]
    assert treo and all(x["nguon"] == "mo_phong_fixture" for x in treo)
    sua = client.get("/api/v1/ghi-nhan-sua", headers=ql).json()
    assert sua["so_dung_lai"] >= 30
    assert all(x["nguon"] == "mo_phong_fixture" for x in sua["items"] if x["dung_lai"])
    # Cổng luật vẫn chỉ tính lần sửa ghi trực tiếp → số #10 không bị fixture đội lên.
    assert client.post("/api/v1/cam-nang/chay-8-buoc", headers=ql).status_code == 409


def test_kiem_ke_vao_store_du_de_tinh_sai_so(bo_nap: Any) -> None:
    """Có đủ 4 cột + đếm tay thì tính được sai số #9 trên tuần 1."""
    from ca_api.persist import kv_get

    bo_nap.nap_tat_ca()
    rows = kv_get("kiem_ke", [])
    assert len(rows) == 112
    cap = [
        (m["tieu_thu_suy_ra"], m["dem_tay_doc_lap"])
        for r in rows
        for m in r["muc"]
        if m["dem_tay_doc_lap"] is not None
    ]
    assert len(cap) == 70
    sai_so = [abs(a - b) / b for a, b in cap if b]
    assert sai_so, "không tính được sai số nào"
    assert max(sai_so) < 0.25, "sai số fixture phi lý — xem lại bộ sinh kiểm kê"
    assert any(x > 0 for x in sai_so), "sai số toàn 0 thì không có gì để đo"
