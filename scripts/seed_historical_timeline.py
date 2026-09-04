"""Seed dữ liệu dòng thời gian lịch sử quán từ tháng 7/2026 đến 05/09/2026.

Mô hình hóa dòng thời gian 10 tuần thực tế:
- Tuần 1-4 (01/07 - 31/07/2026): Quán khai trương với 10 nhân sự cốt lõi,
  sau đó tuyển thêm Khoa & Phúc (15/07). Vận hành thủ công, phát sinh dồn ca cuối tuần.
- Tuần 5-8 (01/08 - 31/08/2026): Tuyển sinh viên part-time (Quân, Linh, Mỹ, Oanh, Sơn).
  Đưa NHỊP QUÁN vào chạy: giải ca CP-SAT, tích lũy lần sửa và học ra 3 luật Cẩm nang sống.
- Tuần 9-10 (01/09 - 05/09/2026 - Hiện tại): Tuyển 2 nhân viên mới (Rosa, Uyên).
  Áp dụng AG-SOP đào tạo nhân viên mới, điều động Uyên bù ca cho Quân vắng hôm nay.

Chạy:
    python scripts/seed_historical_timeline.py
    python scripts/seed_historical_timeline.py --reset
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc

for path in (
    ROOT,
    ROOT / "scripts",
    ROOT / "apps" / "api" / "src",
    ROOT / "packages" / "playbook" / "src",
    ROOT / "packages" / "gates" / "src",
    ROOT / "packages" / "opsengine" / "src",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


from ca_api.persist import (
    _conn,
    audit_add,
    don_insert,
    hash_password,
    init_db,
    kenh_bind_set,
    kv_set,
)

# ── 1. Danh sách 19 nhân viên & Mốc tuyển dụng thực tế từ tháng 7 ─────────────
NHAN_SU_TIMELINE = [
    # Đợt 1: Khai trương quán ngày 01/07/2026 (10 nhân sự cốt lõi)
    ("nv_01", "lan",  "Lan Nguyễn — Cửa hàng trưởng (SM)",            "quan_ly",   "2026-07-01", ["pha_che", "kho", "thu_ngan"]),
    ("nv_02", "hung", "Hùng Trần — Chủ quán (Owner)",                 "chu_quan",  "2026-07-01", ["thu_ngan", "kho"]),
    ("nv_12", "nam",  "Nam Lý — Cửa hàng phó kiêm HR (ASM)",          "quan_ly",   "2026-07-01", ["pha_che", "thu_ngan"]),
    ("nv_03", "minh", "Minh Phạm — Trưởng pha chế (Head Bar)",        "nhan_vien", "2026-07-01", ["pha_che", "phuc_vu"]),
    ("nv_06", "chi",  "Chi Vũ — Tổ trưởng Thu ngân",                  "nhan_vien", "2026-07-01", ["thu_ngan"]),
    ("nv_04", "an",   "An Lê — Nhân viên đa năng / Chi viện",         "nhan_vien", "2026-07-01", ["pha_che", "thu_ngan", "phuc_vu"]),
    ("nv_05", "bao",  "Bảo Hoàng — Barista chính",                    "nhan_vien", "2026-07-01", ["pha_che", "kho"]),
    ("nv_07", "dung", "Dũng Đặng — Trưởng kho & Tiếp liệu",           "nhan_vien", "2026-07-01", ["kho", "phuc_vu"]),
    ("nv_08", "thao", "Thảo Dương — Thu ngân ca tối",                 "nhan_vien", "2026-07-01", ["thu_ngan", "phuc_vu"]),
    ("nv_10", "yen",  "Yến Kiều — Thu ngân ca chiều",                 "nhan_vien", "2026-07-01", ["thu_ngan", "kho"]),

    # Đợt 2: Tăng cường cao điểm cuối tuần ngày 15/07/2026
    ("nv_14", "khoa", "Khoa Đỗ — Kho ca cuối tuần",                   "nhan_vien", "2026-07-15", ["kho", "phuc_vu"]),
    ("nv_15", "phuc", "Phúc Trịnh — Barista ca cuối tuần",            "nhan_vien", "2026-07-15", ["pha_che", "phuc_vu"]),

    # Đợt 3: Bổ sung sinh viên part-time chuẩn bị năm học mới ngày 01/08/2026
    ("nv_09", "quan", "Quân Lương — Barista part-time",               "nhan_vien", "2026-08-01", ["pha_che", "phuc_vu"]),
    ("nv_11", "linh", "Linh Ngô — Phục vụ chính",                     "nhan_vien", "2026-08-01", ["phuc_vu", "pha_che"]),
    ("nv_13", "my",   "Mỹ Tạ — Phụ kho & Sảnh",                       "nhan_vien", "2026-08-01", ["kho", "phuc_vu"]),
    ("nv_16", "oanh", "Oanh Phan — Phục vụ ca tối",                   "nhan_vien", "2026-08-01", ["phuc_vu"]),

    # Đợt 4: Tăng cường sáng Chủ Nhật ngày 15/08/2026
    ("nv_17", "son",  "Sơn Hà — Barista sáng CN",                     "nhan_vien", "2026-08-15", ["pha_che"]),

    # Đợt 5: Tuyển dụng thử việc tháng 9 (01/09 & 03/09/2026)
    ("nv_18", "rosa", "Rosa Võ — Thử việc (Phục vụ)",                 "nhan_vien", "2026-09-01", ["phuc_vu"]),
    ("nv_19", "uyen", "Uyên Cao — Thử việc (Phụ bar/Kho)",            "nhan_vien", "2026-09-03", ["phuc_vu", "kho"]),
]


def seed_users_timeline() -> int:
    init_db()
    with _conn() as cx:
        for nv_id, username, display_name, role, ngay_vao, _ in NHAN_SU_TIMELINE:
            cx.execute(
                """
                INSERT INTO users(username, password_sha, role, nv_id, display_name, store_id)
                VALUES (?, ?, ?, ?, ?, 'quan_01')
                ON CONFLICT(username) DO UPDATE SET
                    role=excluded.role,
                    nv_id=excluded.nv_id,
                    display_name=excluded.display_name
                """,
                (username, hash_password("nhipquan"), role, nv_id, display_name),
            )
    return len(NHAN_SU_TIMELINE)


# ── 2. Lịch sử hóa đơn POS (Tháng 7, Tháng 8, Đầu tháng 9) ──────────────────
def seed_historical_orders() -> int:
    orders = [
        # --- Tháng 7/2026: Quán mới mở ---
        {"id": "don_260701_001", "nv_id": "nv_06", "trang_thai": "xong", "thanh_toan": "tien_mat", "luc": "2026-07-01T08:15:00Z",
         "dong": [{"mon_id": "mon_den", "ten": "Cà phê đen", "so_luong": 2, "gia": 25000}, {"mon_id": "mon_sua", "ten": "Cà phê sữa", "so_luong": 1, "gia": 30000}]},
        {"id": "don_260705_002", "nv_id": "nv_10", "trang_thai": "xong", "thanh_toan": "da_ck", "luc": "2026-07-05T13:40:00Z",
         "dong": [{"mon_id": "mon_tra", "ten": "Trà đào", "so_luong": 3, "gia": 35000}]},
        {"id": "don_260712_003", "nv_id": "nv_08", "trang_thai": "xong", "thanh_toan": "da_ck", "luc": "2026-07-12T19:20:00Z",
         "dong": [{"mon_id": "mon_da", "ten": "Bạc xỉu", "so_luong": 2, "gia": 32000}, {"mon_id": "mon_den", "ten": "Cà phê đen", "so_luong": 1, "gia": 25000}]},
        {"id": "don_260716_004", "nv_id": "nv_06", "trang_thai": "huy", "thanh_toan": "chua_thu", "ly_do_huy": "Khách đổi ý sang trà sữa", "luc": "2026-07-16T09:10:00Z",
         "dong": [{"mon_id": "mon_sua", "ten": "Cà phê sữa", "so_luong": 1, "gia": 30000}]},
        {"id": "don_260720_005", "nv_id": "nv_04", "trang_thai": "xong", "thanh_toan": "tien_mat", "luc": "2026-07-20T10:05:00Z",
         "dong": [{"mon_id": "mon_da", "ten": "Bạc xỉu", "so_luong": 4, "gia": 32000}]},
        {"id": "don_260728_006", "nv_id": "nv_10", "trang_thai": "xong", "thanh_toan": "da_ck", "luc": "2026-07-28T15:30:00Z",
         "dong": [{"mon_id": "mon_tra", "ten": "Trà đào", "so_luong": 2, "gia": 35000}, {"mon_id": "mon_sua", "ten": "Cà phê sữa", "so_luong": 2, "gia": 30000}]},

        # --- Tháng 8/2026: Triển khai NHỊP QUÁN & sinh viên vào làm ---
        {"id": "don_260802_007", "nv_id": "nv_06", "trang_thai": "xong", "thanh_toan": "da_ck", "luc": "2026-08-02T08:45:00Z",
         "dong": [{"mon_id": "mon_den", "ten": "Cà phê đen", "so_luong": 3, "gia": 25000}]},
        {"id": "don_260808_008", "nv_id": "nv_08", "trang_thai": "xong", "thanh_toan": "tien_mat", "luc": "2026-08-08T18:50:00Z",
         "dong": [{"mon_id": "mon_da", "ten": "Bạc xỉu", "so_luong": 3, "gia": 32000}, {"mon_id": "mon_tra", "ten": "Trà đào", "so_luong": 1, "gia": 35000}]},
        {"id": "don_260815_009", "nv_id": "nv_04", "trang_thai": "xong", "thanh_toan": "da_ck", "luc": "2026-08-15T09:30:00Z",
         "dong": [{"mon_id": "mon_sua", "ten": "Cà phê sữa", "so_luong": 4, "gia": 30000}]},
        {"id": "don_260822_010", "nv_id": "nv_10", "trang_thai": "xong", "thanh_toan": "tien_mat", "luc": "2026-08-22T14:15:00Z",
         "dong": [{"mon_id": "mon_tra", "ten": "Trà đào", "so_luong": 2, "gia": 35000}]},
        {"id": "don_260829_011", "nv_id": "nv_08", "trang_thai": "xong", "thanh_toan": "da_ck", "luc": "2026-08-29T20:10:00Z",
         "dong": [{"mon_id": "mon_da", "ten": "Bạc xỉu", "so_luong": 2, "gia": 32000}, {"mon_id": "mon_den", "ten": "Cà phê đen", "so_luong": 2, "gia": 25000}]},

        # --- Tháng 9/2026 (Tuần này): Hiện tại ---
        {"id": "don_260904_012", "nv_id": "nv_06", "trang_thai": "xong", "thanh_toan": "da_ck", "luc": "2026-09-04T07:45:00Z",
         "dong": [{"mon_id": "mon_den", "ten": "Cà phê đen", "so_luong": 2, "gia": 25000}, {"mon_id": "mon_sua", "ten": "Cà phê sữa", "so_luong": 1, "gia": 30000}]},
        {"id": "don_260904_013", "nv_id": "nv_10", "trang_thai": "xong", "thanh_toan": "tien_mat", "luc": "2026-09-04T13:20:00Z",
         "dong": [{"mon_id": "mon_tra", "ten": "Trà đào", "so_luong": 3, "gia": 35000}]},
        {"id": "don_260905_014", "nv_id": "nv_06", "trang_thai": "dang_pha", "thanh_toan": "da_ck", "luc": "2026-09-05T07:35:00Z",
         "dong": [{"mon_id": "mon_da", "ten": "Bạc xỉu", "so_luong": 2, "gia": 32000}]},
        {"id": "don_260905_015", "nv_id": "nv_04", "trang_thai": "cho_pha", "thanh_toan": "chua_thu", "luc": "2026-09-05T07:48:00Z",
         "dong": [{"mon_id": "mon_sua", "ten": "Cà phê sữa", "so_luong": 2, "gia": 30000}, {"mon_id": "mon_tra", "ten": "Trà đào", "so_luong": 1, "gia": 35000}]},
    ]
    with _conn() as cx:
        for od in orders:
            cx.execute("DELETE FROM don_quay WHERE id=?", (od["id"],))
    for od in orders:
        don_insert(od)
    return len(orders)


# ── 3. Nhật ký Audit Log (Từ 01/07/2026 đến 05/09/2026) ─────────────────────
def seed_historical_audit() -> int:
    logs = [
        ("2026-07-01T06:00:00Z", "hung", "khoi_tao_quan", {"ghi_chu": "Khai trương quán NHỊP QUÁN, khởi tạo 10 nhân sự đầu tiên"}),
        ("2026-07-01T06:30:00Z", "lan", "mo_quan_ngay_dau", {"ca": "sang", "so_du_ket": 2000000}),
        ("2026-07-15T09:00:00Z", "hung", "tuyen_dung_nhan_su", {"nhan_vien": ["nv_14", "nv_15"], "ghi_chu": "Bổ sung Khoa và Phúc làm ca cuối tuần"}),
        ("2026-07-31T22:30:00Z", "lan", "chot_so_thang_7", {"tong_doanh_thu_uoc_tinh": 65000000, "danh_gia": "Khách cuối tuần đông, cần thêm nhân sự bar"}),
        ("2026-08-01T08:00:00Z", "nam", "tuyen_dung_sinh_vien", {"nhan_vien": ["nv_09", "nv_11", "nv_13", "nv_16"], "ghi_chu": "Tiếp nhận 4 sinh viên part-time"}),
        ("2026-08-03T10:00:00Z", "nam", "thu_thap_tkb_ag_tkb", {"agent": "AG-TKB", "so_anh_quet": 4, "ket_qua": "Trích xuất thành công 4 TKB sinh viên"}),
        ("2026-08-05T15:00:00Z", "lan", "chay_solver_tuan_dau", {"tuan_iso": "2026-W32", "status": "OPTIMAL", "so_ca": 21}),
        ("2026-08-08T11:00:00Z", "lan", "duyet_luat_cam_nang_01", {"ma_luat": "LUAT-BAR-WKND", "noi_dung": "Ca sáng T7/CN cần tối thiểu 2 Barista"}),
        ("2026-08-15T08:30:00Z", "hung", "tuyen_dung_nhan_su", {"nhan_vien": ["nv_17"], "ghi_chu": "Sơn Hà làm tăng cường sáng CN"}),
        ("2026-08-20T16:00:00Z", "lan", "duyet_doi_ca", {"tu": "nv_07", "sang": "nv_13", "ca": "fx_ca_08", "ly_do": "Dũng bận lịch học thêm"}),
        ("2026-08-31T22:00:00Z", "lan", "chot_so_thang_8", {"tong_doanh_thu_uoc_tinh": 92000000, "ty_le_tuan_thu_lich": "98%"}),
        ("2026-09-01T08:00:00Z", "nam", "onboarding_nhan_vien_moi", {"nhan_vien": "nv_18", "ten": "Rosa Võ", "huong_dan": "AG-SOP tra cứu quy trình phục vụ"}),
        ("2026-09-03T08:00:00Z", "nam", "onboarding_nhan_vien_moi", {"nhan_vien": "nv_19", "ten": "Uyên Cao", "huong_dan": "AG-SOP tra cứu quy trình phụ bar/kho"}),
        ("2026-09-04T17:00:00Z", "bao", "gui_don_doi_ca", {"ca": "fx_ca_15", "nhan": "nv_10", "ly_do": "Bảo bận việc gia đình tối T5"}),
        ("2026-09-05T06:55:00Z", "lan", "tao_viec_treo_bu_ca", {"noi_dung": "Quân vắng ca sáng 05/09, điều động Uyên bù ca"}),
        ("2026-09-05T07:02:00Z", "minh", "diem_danh_ca_sang", {"trang_thai": "minh, an, bao có mặt; quan vắng"}),
    ]
    with _conn() as cx:
        for at, ai, hanh, payload in logs:
            audit_add(at, ai, hanh, payload)
    return len(logs)


# ── 4. Cẩm nang sống & Lần sửa (Học từ tháng 7 và tháng 8) ───────────────────
def seed_playbook_history() -> tuple[int, int]:
    p_sua = ROOT / "data" / "out" / "so_lan_sua.jsonl"
    p_cam_nang = ROOT / "data" / "out" / "cam_nang.json"
    p_sua.parent.mkdir(parents=True, exist_ok=True)

    # 12 lần quản lý sửa tay trong tháng 7 và tháng 8
    sua_rows = [
        {"loai": "nhan_ca", "truoc": "1 barista", "sau": "2 barista", "ai": "lan", "at": "2026-07-04T08:00:00Z", "synthetic": True},
        {"loai": "nhan_ca", "truoc": "1 barista", "sau": "2 barista", "ai": "lan", "at": "2026-07-11T08:00:00Z", "synthetic": True},
        {"loai": "nhan_ca", "truoc": "1 barista", "sau": "2 barista", "ai": "lan", "at": "2026-07-18T08:00:00Z", "synthetic": True},
        {"loai": "nhan_ca", "truoc": "1 barista", "sau": "2 barista", "ai": "lan", "at": "2026-07-25T08:00:00Z", "synthetic": True},
        {"loai": "pin_ca", "truoc": "khong thu ngan", "sau": "co thu ngan giu ket", "ai": "lan", "at": "2026-07-07T12:00:00Z", "synthetic": True},
        {"loai": "pin_ca", "truoc": "khong thu ngan", "sau": "co thu ngan giu ket", "ai": "lan", "at": "2026-07-14T12:00:00Z", "synthetic": True},
        {"loai": "pin_ca", "truoc": "khong thu ngan", "sau": "co thu ngan giu ket", "ai": "lan", "at": "2026-07-21T12:00:00Z", "synthetic": True},
        {"loai": "nha_ca", "truoc": "xep ca lien tiep dem-sang", "sau": "nghi it nhat 9h", "ai": "nam", "at": "2026-08-04T22:00:00Z", "synthetic": True},
        {"loai": "nha_ca", "truoc": "xep ca lien tiep dem-sang", "sau": "nghi it nhat 9h", "ai": "nam", "at": "2026-08-11T22:00:00Z", "synthetic": True},
        {"loai": "nha_ca", "truoc": "xep ca lien tiep dem-sang", "sau": "nghi it nhat 9h", "ai": "nam", "at": "2026-08-18T22:00:00Z", "synthetic": True},
        {"loai": "nhan_ca", "truoc": "1 nguoi don dep", "sau": "2 nguoi ca toi T7", "ai": "nam", "at": "2026-08-22T21:30:00Z", "synthetic": True},
        {"loai": "nhan_ca", "truoc": "1 nguoi don dep", "sau": "2 nguoi ca toi CN", "ai": "nam", "at": "2026-08-23T21:30:00Z", "synthetic": True},
    ]
    with p_sua.open("w", encoding="utf-8") as f:
        for r in sua_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 3 luật đã được học và phê duyệt trong Cẩm nang sống
    cam_nang_items = [
        {
            "id": "luat_260808_01",
            "ma": "LUAT-BAR-WKND",
            "loai": "nhu_cau_ca",
            "tieu_de": "Tăng cường Barista ca sáng cuối tuần",
            "cau_luat": "Ca sáng thứ Bảy và Chủ Nhật bắt buộc có tối thiểu 2 Barista để tránh nghẽn quầy pha chế giờ cao điểm.",
            "dieu_kien": {"thu": ["T7", "CN"], "khung": "sang", "vi_tri": "pha_che", "toi_thieu": 2},
            "bang_chung": ["sua_0", "sua_1", "sua_2", "sua_3"],
            "trang_thai": "da_duyet",
            "duyet_boi": "lan",
            "duyet_luc": "2026-08-08T11:00:00Z",
            "synthetic": True,
        },
        {
            "id": "luat_260812_02",
            "ma": "LUAT-THU-NGAN-KET",
            "loai": "ghep_ky_nang",
            "tieu_de": "Mọi ca đều phải có nhân sự kỹ năng Thu ngân",
            "cau_luat": "Bất kỳ ca làm việc nào cũng phải có ít nhất 1 nhân viên đạt kỹ năng Thu ngân để quản lý két và chốt doanh thu POS.",
            "dieu_kien": {"ky_nang_bat_buoc": "thu_ngan", "toi_thieu": 1},
            "bang_chung": ["sua_4", "sua_5", "sua_6"],
            "trang_thai": "da_duyet",
            "duyet_boi": "lan",
            "duyet_luc": "2026-08-12T14:30:00Z",
            "synthetic": True,
        },
        {
            "id": "luat_260819_03",
            "ma": "LUAT-NGHI-CHUYEN-CA",
            "loai": "nghi_chuyen_ca",
            "tieu_de": "Bảo vệ giấc ngủ: Giãn cách tối thiểu ca đêm và ca sáng",
            "cau_luat": "Nhân viên vừa hoàn thành ca tối (kết thúc 22h00) không được xếp ca sáng hôm sau (bắt đầu 07h00) để đảm bảo nghỉ ngơi.",
            "dieu_kien": {"khoang_nghi_gio": 10},
            "bang_chung": ["sua_7", "sua_8", "sua_9"],
            "trang_thai": "da_duyet",
            "duyet_boi": "nam",
            "duyet_luc": "2026-08-19T10:15:00Z",
            "synthetic": True,
        },
    ]
    p_cam_nang.write_text(json.dumps(cam_nang_items, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(sua_rows), len(cam_nang_items)


# ── 5. Nạp KV Store Toàn Diện (Sổ công bằng, Đổi ca, Việc treo, Lịch tuần) ──
def seed_kv_historical() -> dict[str, Any]:
    # Lịch sử tuần đã qua (Tuần W27 đến W36)
    history_weeks = [
        {"tuan_iso": f"2026-W{w:02d}", "trang_thai": "da_dong", "so_ca": 21, "tong_cong": 42}
        for w in range(27, 36)
    ]
    history_weeks.append({"tuan_iso": "2026-W36", "trang_thai": "da_cong_bo", "so_ca": 21, "tong_cong": 43})
    kv_set("lich_su_tuan", history_weeks)

    # Lịch tuần hiện tại (2026-W37) với đầy đủ 21 ca và 43 phân công
    from scripts.seed_19_staff import DEMO_PHAN_CONG, read_fixture
    base = read_fixture("base.json")
    lich_tuan = {
        "tuan_iso": "2026-W37",
        "trang_thai": "da_xep",
        "solver_run_id": "solver_20260905_tuan37",
        "ca_lam": [
            {**shift, "nhan_vien": DEMO_PHAN_CONG.get(shift["id"], [])}
            for shift in base["shifts"]
        ],
        "nguon": "seed_timeline",
        "cap_nhat_luc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    kv_set("lich_tuan", lich_tuan)
    kv_set("phan_cong", DEMO_PHAN_CONG)

    # Sổ nợ công bằng: Tích lũy thực tế từ tháng 7
    fairness = {
        "nv_15": {"ca_toi_tich_luy": 9, "ca_cuoi_tuan_tich_luy": 11, "diem_bap_cong_bang": -4, "ghi_chu": "Phúc Trịnh — Gánh ca đêm T7/CN liên tục từ 15/07"},
        "nv_14": {"ca_toi_tich_luy": 8, "ca_cuoi_tuan_tich_luy": 12, "diem_bap_cong_bang": -3, "ghi_chu": "Khoa Đỗ — Làm kho cuối tuần từ 15/07"},
        "nv_16": {"ca_toi_tich_luy": 6, "ca_cuoi_tuan_tich_luy": 10, "diem_bap_cong_bang": -2, "ghi_chu": "Oanh Phan — Làm phục vụ ca tối từ 01/08"},
        "nv_17": {"ca_toi_tich_luy": 4, "ca_cuoi_tuan_tich_luy": 8,  "diem_bap_cong_bang": -2, "ghi_chu": "Sơn Hà — Tăng cường ca sáng CN từ 15/08"},
        "nv_03": {"ca_toi_tich_luy": 2, "ca_cuoi_tuan_tich_luy": 3,  "diem_bap_cong_bang": 1,  "ghi_chu": "Minh Phạm — Bar trưởng cố định ca sáng"},
        "nv_01": {"ca_toi_tich_luy": 1, "ca_cuoi_tuan_tich_luy": 2,  "diem_bap_cong_bang": 2,  "ghi_chu": "Lan Nguyễn — Cửa hàng trưởng ca sáng"},
        "nv_04": {"ca_toi_tich_luy": 3, "ca_cuoi_tuan_tich_luy": 4,  "diem_bap_cong_bang": 0,  "ghi_chu": "An Lê — Đa năng cân bằng tốt"},
    }
    kv_set("ngan_sach_cong_bang", fairness)

    # Đề xuất đổi ca (Bao gồm lịch sử tháng 8 và đơn mới tháng 9)
    doi_ca = [
        {"id": "doi_ca_260814_01", "staff_id_xin": "nv_07", "shift_id": "fx_ca_08", "nhan_xin": "nv_13",
         "ly_do": "Dũng bận lịch học chiều T4", "status": "approved", "created_at": "2026-08-14T10:00:00Z", "approved_by": "nv_01", "approved_at": "2026-08-14T14:30:00Z"},
        {"id": "doi_ca_260821_02", "staff_id_xin": "nv_09", "shift_id": "fx_ca_04", "nhan_xin": "nv_05",
         "ly_do": "Quân thi giữa kỳ sáng T3", "status": "approved", "created_at": "2026-08-21T09:00:00Z", "approved_by": "nv_01", "approved_at": "2026-08-21T11:00:00Z"},
        {"id": "doi_ca_260904_03", "staff_id_xin": "nv_05", "shift_id": "fx_ca_15", "nhan_xin": "nv_10",
         "ly_do": "Bảo bận việc gia đình tối T5, Yến đồng ý nhận ca", "status": "cho_duyet", "created_at": "2026-09-04T17:00:00Z"},
    ]
    kv_set("de_xuat_doi_ca", doi_ca)

    # Việc treo (Gồm 4 việc thực tế ngày 05/09/2026)
    treo = [
        {"id": "treo_001", "mo_ta": "Máy pha espresso có tiếng lạ khi đánh sữa — Minh cần kỹ thuật kiểm tra", "ca_tao": "fx_ca_01", "nguoi_tao": "nv_03", "nguoi_nhan": "nv_01", "do_uu_tien": "cao", "trang_thai": "dang_xu_ly", "tao_luc": "2026-09-05T07:10:00Z"},
        {"id": "treo_002", "mo_ta": "Khách đặt bánh sinh nhật chiều T7 qua Zalo (chị Hoa 0912345678) — Quầy bánh giữ phần", "ca_tao": "fx_ca_01", "nguoi_tao": "nv_06", "nguoi_nhan": "nv_10", "do_uu_tien": "trung_binh", "trang_thai": "chua_xu_ly", "tao_luc": "2026-09-05T07:25:00Z"},
        {"id": "treo_003", "mo_ta": "Kiểm tra hạn sử dụng lô sữa tươi nhập hôm 03/09 trước khi giao ca trưa", "ca_tao": "fx_ca_01", "nguoi_tao": "nv_01", "nguoi_nhan": "nv_07", "do_uu_tien": "cao", "trang_thai": "dang_xu_ly", "tao_luc": "2026-09-05T07:30:00Z"},
        {"id": "treo_004", "mo_ta": "Quân vắng ca sáng 05/09 do lịch học đột xuất — Điều động Uyên phụ bar thay thế", "ca_tao": "fx_ca_01", "nguoi_tao": "nv_01", "nguoi_nhan": "nv_19", "do_uu_tien": "cao", "trang_thai": "dang_xu_ly", "tao_luc": "2026-09-05T06:55:00Z"},
    ]
    kv_set("treo", treo)

    # Điểm danh hôm nay (05/09/2026)
    diem_danh = {
        "ngay": "2026-09-05",
        "ca": "sang",
        "xac_nhan": [
            {"nv_id": "nv_01", "gio": "06:45", "trang_thai": "du_mat", "ghi_chu": "Mở cửa & kiểm két"},
            {"nv_id": "nv_03", "gio": "06:50", "trang_thai": "du_mat", "ghi_chu": "Khởi động máy pha"},
            {"nv_id": "nv_06", "gio": "06:55", "trang_thai": "du_mat", "ghi_chu": "Đăng nhập POS"},
            {"nv_id": "nv_04", "gio": "07:00", "trang_thai": "du_mat", "ghi_chu": "Chuẩn bị đá & sảnh"},
            {"nv_id": "nv_09", "gio": None,    "trang_thai": "vang_mat", "ghi_chu": "Báo bận học đột xuất lúc 06:40"},
            {"nv_id": "nv_19", "gio": "07:05", "trang_thai": "du_mat", "ghi_chu": "Nhận điều động bù ca cho Quân"},
        ],
        "cap_nhat_luc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    kv_set("diem_danh_hom_nay", diem_danh)

    # Liên kết kênh tin
    kenh_bind_set("telegram", "tg_demo_minh_9999", "nv_03")
    kenh_bind_set("telegram", "tg_demo_thao_8888", "nv_08")
    kenh_bind_set("zalo",     "za_demo_chi_7777",  "nv_06")

    return {
        "history_weeks": len(history_weeks),
        "fairness_entries": len(fairness),
        "swap_requests": len(doi_ca),
        "pending_tasks": len(treo),
        "attendance_count": len(diem_danh["xac_nhan"]),
    }


def main() -> int:
    print("=" * 65)
    print("NHỊP QUÁN — Seed Dòng Thời Gian Lịch Sử Quán (Tháng 7 -> 05/09/2026)")
    print("=" * 65)

    n_users = seed_users_timeline()
    print(f"[1] Nhân sự: Đã nạp 19 nhân viên theo các đợt tuyển dụng ({n_users} NV)")

    n_orders = seed_historical_orders()
    print(f"[2] Đơn hàng POS: Đã nạp {n_orders} đơn hàng mẫu trải từ T7 đến nay")

    n_audit = seed_historical_audit()
    print(f"[3] Nhật ký Audit Log: Đã nạp {n_audit} sự kiện vận hành lịch sử")

    n_sua, n_luat = seed_playbook_history()
    print(f"[4] Cẩm nang sống: Đã nạp {n_sua} lần sửa -> Học ra {n_luat} luật vận hành")

    kv_stats = seed_kv_historical()
    print(f"[5] KV Store đồng bộ:")
    for k, v in kv_stats.items():
        print(f"    • {k}: {v}")

    print("=" * 65)
    print("HOÀN THÀNH: Dữ liệu nhất quán, logic và xuyên suốt 10 tuần!")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
