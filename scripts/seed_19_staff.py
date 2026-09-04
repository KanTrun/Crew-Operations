"""Seed 19 nhân viên demo vào SQLite và KV store — idempotent.

Chạy:
    python scripts/seed_19_staff.py          # Seed bình thường
    python scripts/seed_19_staff.py --reset  # Xóa DB rồi seed lại sạch

Sau khi chạy:
    - 19 tài khoản trong bảng users (password: nhipquan)
    - KV store: lich_tuan, ngan_sach_cong_bang, de_xuat_doi_ca, viec_treo,
                diem_danh_hom_nay, kenh_bind (telegram/zalo cho 3 NV demo)
    - Lịch tuần 2026-W37 với 21 ca, 43 assignments

Tài khoản đăng nhập demo:
    lan / nhipquan   → quản lý (người phê duyệt)
    hung / nhipquan  → chủ quán
    minh / nhipquan  → nhân viên ca sáng
    chi / nhipquan   → nhân viên (bind Telegram demo)
    thao / nhipquan  → nhân viên (bind Telegram demo)
    (toàn bộ 19 người đều nhipquan)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Fix UTF-8 output trên Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "fixtures" / "professional"
SEED = ROOT / "data" / "seed" / "sample.json"
SOURCE = "seed_19_staff"
UTC = timezone.utc

for path in (
    ROOT / "apps" / "api" / "src",
    ROOT / "packages" / "playbook" / "src",
    ROOT / "packages" / "gates" / "src",
    ROOT / "packages" / "opsengine" / "src",
):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

# Bảng ánh xạ đầy đủ 19 nhân viên chuẩn doanh nghiệp
# (nv_id, username, display_name, role)
ALL_STAFF: list[tuple[str, str, str, str]] = [
    # Khối 1 — Ban Quản Lý (2 Quản lý + 1 Chủ quán)
    ("nv_01", "lan",  "Lan Nguyễn — Cửa hàng trưởng (SM)",            "quan_ly"),
    ("nv_02", "hung", "Hùng Trần — Chủ quán (Owner)",                 "chu_quan"),
    ("nv_12", "nam",  "Nam Lý — Cửa hàng phó kiêm HR (ASM)",          "quan_ly"),
    # Khối 2 — Trưởng Nhóm Chuyên Môn & Nhân Viên Lõi
    ("nv_03", "minh", "Minh Phạm — Trưởng pha chế (Head Bar)",        "nhan_vien"),
    ("nv_06", "chi",  "Chi Vũ — Tổ trưởng Thu ngân",                  "nhan_vien"),
    ("nv_07", "dung", "Dũng Đặng — Trưởng kho & Tiếp liệu",           "nhan_vien"),
    ("nv_04", "an",   "An Lê — Nhân viên đa năng / Chi viện",         "nhan_vien"),
    ("nv_05", "bao",  "Bảo Hoàng — Barista chính",                    "nhan_vien"),
    # Khối 3 — Nhân Viên Vận Hành Ca / Thu Ngân Xoay Tua
    ("nv_10", "yen",  "Yến Kiều — Thu ngân ca chiều",                 "nhan_vien"),
    ("nv_08", "thao", "Thảo Dương — Thu ngân ca tối",                 "nhan_vien"),
    ("nv_09", "quan", "Quân Lương — Barista part-time",               "nhan_vien"),
    ("nv_11", "linh", "Linh Ngô — Phục vụ chính",                     "nhan_vien"),
    ("nv_13", "my",   "Mỹ Tạ — Phụ kho & Sảnh",                       "nhan_vien"),
    # Khối 4 — Nhân Viên Ca Cuối Tuần / Ca Đêm (Demo Sổ Công Bằng)
    ("nv_14", "khoa", "Khoa Đỗ — Kho ca cuối tuần",                   "nhan_vien"),
    ("nv_15", "oanh", "Oanh Phan — Phục vụ ca tối",                   "nhan_vien"),
    ("nv_16", "phuc", "Phúc Trịnh — Barista ca cuối tuần",            "nhan_vien"),
    ("nv_17", "son",  "Sơn Hà — Barista sáng CN",                     "nhan_vien"),
    # Khối 5 — Nhân Viên Thử Việc / Học Việc (Demo Onboarding & Bù Ca)
    ("nv_18", "rosa", "Rosa Võ — Thử việc (Phục vụ)",                 "nhan_vien"),
    ("nv_19", "uyen", "Uyên Cao — Thử việc (Phụ bar/Kho)",            "nhan_vien"),
]


# Kênh tin demo — chỉ 3 người có bind thật (console fallback cho phần còn lại)
KENH_BIND_DEMO = [
    # (channel, external_user_id, nv_id)
    ("telegram", "tg_demo_minh_9999",  "nv_03"),
    ("telegram", "tg_demo_thao_8888",  "nv_08"),
    ("zalo",     "za_demo_chi_7777",   "nv_06"),
    # Console fallback cho các người còn lại được gán lúc đăng ký
]


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURE / name).read_text(encoding="utf-8"))


def seed_users() -> dict[str, int]:
    """Upsert 19 tài khoản. Trả về {'created': n, 'updated': n}."""
    from ca_api.persist import _conn, hash_password, init_db

    init_db()
    created = 0
    updated = 0
    with _conn() as cx:
        for nv_id, username, display_name, role in ALL_STAFF:
            existing = cx.execute(
                "SELECT nv_id FROM users WHERE username=?", (username,)
            ).fetchone()
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
            if existing is None:
                created += 1
            else:
                updated += 1
    return {"created": created, "updated": updated}


def seed_schedule(base: dict[str, Any]) -> dict[str, int]:
    """Seed lịch tuần vào KV store."""
    from ca_api.persist import kv_set

    # Lịch phân công 19 nhân viên (>= 2 người/ca)
    phan_cong: dict[str, list[str]] = dict(DEMO_PHAN_CONG)
    total_assignments = sum(len(nvs) for nvs in phan_cong.values())

    # Lịch tuần đầy đủ (shifts + assignments gộp)
    lich_tuan = {
        "tuan_iso": base["lifecycle"]["tuan_iso"],
        "trang_thai": base["lifecycle"]["trang_thai"],
        "solver_run_id": base["lifecycle"]["solver_run_id"],
        "ca_lam": [
            {
                **shift,
                "nhan_vien": phan_cong.get(shift["id"], []),
            }
            for shift in base["shifts"]
        ],
        "nguon": SOURCE,
        "cap_nhat_luc": now_iso(),
    }
    kv_set("lich_tuan", lich_tuan)
    kv_set("phan_cong", phan_cong)
    return {"shifts": len(base["shifts"]), "assignments": total_assignments}



DEFAULT_FAIRNESS = [
    {"staff_id": "nv_14", "ca_toi_tich_luy": 8, "ca_cuoi_tuan_tich_luy": 12, "diem_bap_cong_bang": -3},
    {"staff_id": "nv_15", "ca_toi_tich_luy": 6, "ca_cuoi_tuan_tich_luy": 10, "diem_bap_cong_bang": -2},
    {"staff_id": "nv_16", "ca_toi_tich_luy": 9, "ca_cuoi_tuan_tich_luy": 11, "diem_bap_cong_bang": -4},
    {"staff_id": "nv_17", "ca_toi_tich_luy": 4, "ca_cuoi_tuan_tich_luy": 8, "diem_bap_cong_bang": -2},
    {"staff_id": "nv_03", "ca_toi_tich_luy": 2, "ca_cuoi_tuan_tich_luy": 3, "diem_bap_cong_bang": 1},
    {"staff_id": "nv_04", "ca_toi_tich_luy": 3, "ca_cuoi_tuan_tich_luy": 4, "diem_bap_cong_bang": 0},
    {"staff_id": "nv_09", "ca_toi_tich_luy": 1, "ca_cuoi_tuan_tich_luy": 2, "diem_bap_cong_bang": 2},
]

DEFAULT_DOI_CA = [
    {
        "id": "fx_doi_ca_01",
        "staff_id_xin": "nv_05",
        "shift_id": "fx_ca_15",
        "nhan_xin": "nv_10",
        "ly_do": "Bảo bận việc gia đình, Yến đồng ý nhận ca T5 tối",
        "status": "cho_duyet",
        "created_at": "2026-09-05T08:30:00Z",
    },
    {
        "id": "fx_doi_ca_02",
        "staff_id_xin": "nv_07",
        "shift_id": "fx_ca_08",
        "nhan_xin": "nv_13",
        "ly_do": "Dũng có lịch học bổ sung chiều T4",
        "status": "approved",
        "created_at": "2026-09-04T14:00:00Z",
        "approved_by": "nv_01",
        "approved_at": "2026-09-04T15:30:00Z",
    },
]

# Phân công 19 nhân viên vào 21 ca mẫu để demo lịch tuần đầy đủ (>= 2 người/ca)
DEMO_PHAN_CONG = {
    "fx_ca_01": ["nv_03", "nv_09"],
    "fx_ca_02": ["nv_01", "nv_06"],
    "fx_ca_03": ["nv_08", "nv_19"],
    "fx_ca_04": ["nv_04", "nv_13"],
    "fx_ca_05": ["nv_05", "nv_12"],
    "fx_ca_06": ["nv_10", "nv_18"],
    "fx_ca_07": ["nv_11", "nv_08"],
    "fx_ca_08": ["nv_04", "nv_07"],
    "fx_ca_09": ["nv_03", "nv_16"],
    "fx_ca_10": ["nv_06", "nv_01"],
    "fx_ca_11": ["nv_11", "nv_19"],
    "fx_ca_12": ["nv_07", "nv_10"],
    "fx_ca_13": ["nv_05", "nv_09"],
    "fx_ca_14": ["nv_12", "nv_08"],
    "fx_ca_15": ["nv_13", "nv_15"],
    "fx_ca_16": ["nv_04", "nv_14"],
    "fx_ca_17": ["nv_03", "nv_16"],
    "fx_ca_18": ["nv_10", "nv_06"],
    "fx_ca_19": ["nv_05", "nv_17", "nv_09"],
    "fx_ca_20": ["nv_11", "nv_15"],
    "fx_ca_21": ["nv_14", "nv_16"],
}


def seed_fairness(base: dict[str, Any]) -> int:
    """Seed sổ công bằng vào KV store."""
    from ca_api.persist import kv_set

    sach = base.get("ngan_sach_cong_bang") or DEFAULT_FAIRNESS
    kv_set("ngan_sach_cong_bang", {
        row["staff_id"]: {
            "ca_toi_tich_luy": row["ca_toi_tich_luy"],
            "ca_cuoi_tuan_tich_luy": row["ca_cuoi_tuan_tich_luy"],
            "diem_bap_cong_bang": row["diem_bap_cong_bang"],
        }
        for row in sach
    })
    return len(sach)


def seed_doi_ca(base: dict[str, Any]) -> int:
    """Seed đề xuất đổi ca đang chờ phê duyệt."""
    from ca_api.persist import kv_set

    doi_ca_list = base.get("doi_ca_requests") or DEFAULT_DOI_CA
    kv_set("de_xuat_doi_ca", doi_ca_list)
    return len(doi_ca_list)



def seed_viec_treo() -> int:
    """Seed 4 việc treo từ ca trước — kịch bản demo vận hành."""
    from ca_api.persist import kv_set

    viec_treo = [
        {
            "id": "treo_001",
            "mo_ta": "Máy pha espresso có tiếng lạ — cần gọi kỹ thuật kiểm tra",
            "ca_tao": "fx_ca_15",
            "nguoi_tao": "nv_08",
            "nguoi_nhan": "nv_01",
            "do_uu_tien": "cao",
            "trang_thai": "chua_xu_ly",
            "tao_luc": "2026-09-11T17:05:00Z",
            "synthetic": True,
            "nguon": SOURCE,
        },
        {
            "id": "treo_002",
            "mo_ta": "Khách đặt bánh sinh nhật chiều T7 — tên Hoa, đặt qua Zalo, số 0912345678",
            "ca_tao": "fx_ca_15",
            "nguoi_tao": "nv_10",
            "nguoi_nhan": "nv_03",
            "do_uu_tien": "trung_binh",
            "trang_thai": "chua_xu_ly",
            "tao_luc": "2026-09-11T16:50:00Z",
            "synthetic": True,
            "nguon": SOURCE,
        },
        {
            "id": "treo_003",
            "mo_ta": "Sữa tươi hết hạn 3 hộp — đã tách riêng, nhắc kho nhập lô mới trước 14h",
            "ca_tao": "fx_ca_14",
            "nguoi_tao": "nv_04",
            "nguoi_nhan": "nv_05",
            "do_uu_tien": "cao",
            "trang_thai": "dang_xu_ly",
            "tao_luc": "2026-09-11T13:40:00Z",
            "synthetic": True,
            "nguon": SOURCE,
        },
        {
            "id": "treo_004",
            "mo_ta": "Ca sáng hôm nay Quân vắng — đã nhờ Uyên bù nhưng chưa xác nhận chính thức",
            "ca_tao": "fx_ca_13",
            "nguoi_tao": "nv_01",
            "nguoi_nhan": "nv_19",
            "do_uu_tien": "cao",
            "trang_thai": "chua_xu_ly",
            "tao_luc": "2026-09-11T06:55:00Z",
            "synthetic": True,
            "nguon": SOURCE,
        },
    ]
    kv_set("treo", viec_treo)
    return len(viec_treo)


def seed_attendance() -> int:
    """Seed điểm danh hôm nay — minh và an đã điểm danh, quan vắng."""
    from ca_api.persist import kv_set

    diem_danh = {
        "ngay": "2026-09-11",
        "ca": "sang",
        "xac_nhan": [
            {"nv_id": "nv_03", "gio": "07:02", "trang_thai": "du_mat"},
            {"nv_id": "nv_04", "gio": "07:00", "trang_thai": "du_mat"},
            {"nv_id": "nv_05", "gio": "07:15", "trang_thai": "tre_5_phut"},
            {"nv_id": "nv_09", "gio": None, "trang_thai": "vang_mat"},
        ],
        "nguon": SOURCE,
        "cap_nhat_luc": now_iso(),
    }
    kv_set("diem_danh_hom_nay", diem_danh)
    return len(diem_danh["xac_nhan"])


def seed_channel_bindings() -> int:
    """Seed kênh tin demo — 3 nhân viên có bind thật."""
    from ca_api.persist import kenh_bind_set

    for channel, external_user_id, nv_id in KENH_BIND_DEMO:
        kenh_bind_set(channel, external_user_id, nv_id)
    return len(KENH_BIND_DEMO)


def seed_availability(base: dict[str, Any]) -> None:
    """Lưu bảng khả dụng (TKB bận) vào KV store."""
    from ca_api.persist import kv_set

    kv_set("kha_dung", base.get("availability", []))


def wipe_db() -> None:
    from ca_api.persist import db_path, reset_init_flag

    p = db_path()
    if p.exists():
        p.unlink()
    for extra in (p.with_name(p.name + "-wal"), p.with_name(p.name + "-shm")):
        if extra.exists():
            extra.unlink()
    reset_init_flag()
    print("✓ database wiped.")


def main() -> int:
    if "--reset" in sys.argv:
        wipe_db()

    print("=" * 60)
    print("seed_19_staff.py — NHỊP QUÁN demo database")
    print("=" * 60)

    base = read_fixture("base.json")

    # 1. Users
    from ca_api.persist import init_db
    init_db()
    result = seed_users()
    print(f"[1] users: created={result['created']} updated={result['updated']}")

    # 2. Lịch tuần
    sched = seed_schedule(base)
    print(f"[2] schedule: shifts={sched['shifts']} assignments={sched['assignments']}")

    # 3. Sổ công bằng
    n_fair = seed_fairness(base)
    print(f"[3] fairness: {n_fair} entries seeded")

    # 4. Đề xuất đổi ca
    n_doi = seed_doi_ca(base)
    print(f"[4] shift-swap requests: {n_doi} (pending approval)")

    # 5. Việc treo
    n_treo = seed_viec_treo()
    print(f"[5] pending tasks (viec_treo): {n_treo}")

    # 6. Điểm danh hôm nay
    n_dd = seed_attendance()
    print(f"[6] attendance today: {n_dd} records")

    # 7. Kênh tin bind
    n_bind = seed_channel_bindings()
    print(f"[7] channel bindings: {n_bind} (minh→telegram, thao→telegram, chi→zalo)")

    # 8. Khả dụng (TKB bận)
    seed_availability(base)
    print("[8] availability / tkb_busy: seeded")

    print()
    print("=" * 60)
    print("DONE — 19 tài khoản sẵn sàng, mật khẩu đều: nhipquan")
    print()
    print("Nhóm 1 — Quản lý:")
    print("  lan   / nhipquan  → quản lý (người phê duyệt)")
    print("  hung  / nhipquan  → chủ quán")
    print()
    print("Nhóm 2 — Nhân viên lõi:")
    print("  minh  / nhipquan  → pha chế, phục vụ  [Telegram demo]")
    print("  an    / nhipquan  → pha chế, thu ngân, kho")
    print("  bao   / nhipquan  → pha chế, kho")
    print()
    print("Nhóm 3 — Sinh viên (có TKB xung đột):")
    print("  chi   / nhipquan  → thu ngân            [Zalo demo]")
    print("  dung  / nhipquan  → kho, phục vụ")
    print("  thao  / nhipquan  → thu ngân, phục vụ   [Telegram demo]")
    print("  quan  / nhipquan  → pha chế, phục vụ    [VẮNG hôm nay — demo kịch bản D]")
    print("  yen   / nhipquan  → thu ngân, kho")
    print("  linh  / nhipquan  → phục vụ, pha chế")
    print("  nam   / nhipquan  → pha chế, thu ngân")
    print("  my    / nhipquan  → kho, phục vụ")
    print()
    print("Nhóm 4 — Sinh viên cuối tuần (sổ bất công tích lũy):")
    print("  khoa  / nhipquan  → kho")
    print("  oanh  / nhipquan  → phục vụ")
    print("  phuc  / nhipquan  → pha chế, phục vụ")
    print("  son   / nhipquan  → pha chế (chỉ sáng CN)")
    print()
    print("Nhóm 5 — Nhân viên mới (demo onboarding):")
    print("  rosa  / nhipquan  → phục vụ [thử việc]")
    print("  uyen  / nhipquan  → phục vụ, kho [thử việc — bù ca Quân hôm nay]")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
