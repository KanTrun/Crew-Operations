#!/usr/bin/env python3
"""Bộ đo 12 con số §18.2 trên fixture ADR-012 — tất định, không random.

Chạy:   python scripts/do_metrics.py
Ghi ra: data/out/metrics.json  (+ bảng ra stdout)

Luật của bộ đo (hồ sơ §18.2 "Cấm số phỏng đoán"):

1. Mỗi bản ghi bắt buộc có `nguon` ∈ {`mo_phong_fixture`, `quan_that`}.
   Fixture luôn là `mo_phong_fixture` và KHÔNG được trình bày như số quán thật.
2. Mỗi bản ghi bắt buộc có `cach_do`: nói rõ công thức và dữ liệu nguồn.
3. Số nào không tính được từ fixture → `gia_tri: null` + `trang_thai: "chua_do"`
   + `ly_do` cụ thể. Thà để trống có lý do hơn là bịa.
4. Không dùng `random`, không lấy giờ hệ thống làm đầu vào của số đo. Cùng
   fixture → cùng kết quả. Trường nào buộc phải bấm đồng hồ thật thì được kê
   trong `khong_tat_dinh` để `make replay` và bộ kiểm tất định bỏ qua nó.
5. Khi quán thật vào: đổi `NGUON_FIXTURE` sang nguồn thật + đổi hàm nạp dữ
   liệu. Công thức, bảng, và schema bản ghi không đổi.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("solver", "playbook", "gates", "opsengine", "agents", "contracts"):
    sys.path.insert(0, str(ROOT / "packages" / _pkg / "src"))

from ca_agents.ag_explain import dien_giai  # noqa: E402
from ca_agents.ag_tkb.extract import extract_tkb  # noqa: E402
from ca_agents.router import FreeTierRouter  # noqa: E402
from ca_agents.runtime import AgentRuntime  # noqa: E402
from ca_gates import (  # noqa: E402
    present_conflict,
    run_vf_pipeline,
    validate_num,
    validate_rule,
)
from ca_ops import PhieuRun, add_treo, complete_buoc, run_to_dict, start_phieu  # noqa: E402
from ca_solver import (  # noqa: E402
    MA_LY_DO,
    LichInput,
    build_lich_input,
    sinh_ly_do,
    solve_cpsat,
    solve_hard_only,
)
from ca_solver.load_fixture import load_labor_params, load_seed  # noqa: E402

# ── Nhãn nguồn — chỉ hai giá trị hợp lệ ───────────────────────────────────
NGUON_FIXTURE = "mo_phong_fixture"
NGUON_QUAN = "quan_that"

SEED_PATH = ROOT / "data" / "seed" / "sample.json"
GOLDEN_TKB = ROOT / "data" / "golden" / "tkb"
OUT_PATH = ROOT / "data" / "out" / "metrics.json"

_THU = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}
_KHUNG_ORD = {"sang": 0, "chieu": 1, "toi": 2}

# Nhịp đồng hồ ảo của máy quy trình: cố định 5 giây/bước. Chọn cố định để bộ
# đo tất định — đây KHÔNG phải thời gian thao tác của nhân viên thật.
NHIP_MS = 5_000
# Ảnh minh chứng giả lập: fixture không có ảnh quán thật.
ANH_FIXTURE = "data:image/png;base64,QUJDREVGR0g="


def ghi(
    so: int,
    ten: str,
    *,
    gia_tri: Any,
    trang_thai: str,
    cach_do: str,
    nguon: str = NGUON_FIXTURE,
    ly_do: str | None = None,
    canh_bao: str | None = None,
    khong_tat_dinh: list[str] | None = None,
) -> dict[str, Any]:
    """Tạo một bản ghi số đo đúng schema (nguon + cach_do là bắt buộc)."""
    if nguon not in (NGUON_FIXTURE, NGUON_QUAN):
        raise ValueError(f"nguon_khong_hop_le:{nguon}")
    if trang_thai not in ("do_duoc", "mot_phan", "chua_do"):
        raise ValueError(f"trang_thai_khong_hop_le:{trang_thai}")
    if trang_thai != "do_duoc" and not ly_do:
        raise ValueError(f"thieu_ly_do:{so}")
    rec: dict[str, Any] = {
        "so": so,
        "ten": ten,
        "gia_tri": gia_tri,
        "trang_thai": trang_thai,
        "nguon": nguon,
        "cach_do": cach_do,
    }
    if ly_do:
        rec["ly_do"] = ly_do
    if canh_bao:
        rec["canh_bao"] = canh_bao
    if khong_tat_dinh:
        rec["khong_tat_dinh"] = khong_tat_dinh
    return rec


# ── Dựng lịch một tuần lịch sử thành LichInput ────────────────────────────
def lich_tuan(seed: dict[str, Any], tuan: dict[str, Any]) -> LichInput:
    """Nạp một tuần trong `lich_su_8_tuan` thành LichInput đã có phân công.

    Cùng quy ước TKB/nghỉ phép với `ca_solver.build_lich_input` để hai đường
    đo so được với nhau.
    """
    params = load_labor_params()
    nvs = seed["nhan_vien"]
    cas = tuan["ca"]
    nv_ids = [x["id"] for x in nvs]
    ca_meta: dict[str, dict[str, str]] = {}
    so_nguoi: dict[str, int] = {}
    vi_tri: dict[str, str] = {}
    for c in cas:
        ca_meta[c["id"]] = {
            "thu": _THU[int(c["ngay_offset"])],
            "bat_dau": c["bat_dau"],
            "ket_thuc": c["ket_thuc"],
            "khung": c.get("khung", ""),
        }
        so_nguoi[c["id"]] = int(c.get("so_nguoi_toi_thieu", 1))
        vi_tri[c["id"]] = c["vi_tri"]
    tkb: dict[str, list[tuple[str, str, str]]] = {
        x["id"]: [("T2", "07:00", "10:00")]
        for x in nvs
        if x.get("la_sinh_vien") and str(x["id"]).endswith(("1", "3", "5", "7", "9"))
    }
    return LichInput(
        nhan_vien_ids=nv_ids,
        ca_ids=[c["id"] for c in cas],
        phan_cong={c["id"]: list(tuan["phan_cong"].get(c["id"], [])) for c in cas},
        tkb=tkb,
        ca_meta=ca_meta,
        ky_nang={x["id"]: set(x.get("ky_nang", [])) for x in nvs},
        vi_tri_can=vi_tri,
        so_nguoi_toi_thieu=so_nguoi,
        nghi_phep={("nv_25", "CN")} if "nv_25" in nv_ids else set(),
        gio_da_lam={},
        tran_gio_tuan=float(params["tran_gio_tuan"]),
        khoang_nghi_gio=float(params["khoang_nghi_toi_thieu_gio"]),
        debt={n: {"cuoi_tuan": 0.0, "dem": 0.0, "gio": 0.0, "vun": 0.0} for n in nv_ids},
    )


def cap_phai_sua(data: LichInput, vi_pham: list[str]) -> set[tuple[str, str]]:
    """Quy mỗi vi phạm cứng về tập cặp (ca, nhân viên) buộc phải sửa.

    - c01/c06 `c0x:ca:nv:...`      → đúng cặp đó
    - c02 `c02:ca:nv:thieu_ky_nang`→ đúng cặp đó
    - c02 `c02:ca:thieu_nguoi`     → mọi cặp đang có của ca đó (ca phải sửa)
    - c03/c04 `c0x:nv:ca_a:ca_b`   → hai cặp (ca_a,nv) và (ca_b,nv)
    - c05 `c05:nv:vuot_tran_tuan`  → mọi cặp của nv đó trong tuần
    """
    ca_set = set(data.ca_ids)
    ca_theo_nv: dict[str, list[str]] = {}
    for ca, nvs in data.phan_cong.items():
        for nv in nvs:
            ca_theo_nv.setdefault(nv, []).append(ca)
    out: set[tuple[str, str]] = set()
    for v in vi_pham:
        p = v.split(":")
        ma = p[0]
        if ma in {"c01", "c06"}:
            out.add((p[1], p[2]))
        elif ma == "c02":
            if p[2] == "thieu_nguoi":
                for nv in data.phan_cong.get(p[1], []):
                    out.add((p[1], nv))
            else:
                out.add((p[1], p[2]))
        elif ma in {"c03", "c04"}:
            for ca in (p[2], p[3]):
                if ca in ca_set:
                    out.add((ca, p[1]))
        elif ma == "c05":
            for ca in ca_theo_nv.get(p[1], []):
                out.add((ca, p[1]))
    return out


def timeline(seed: dict[str, Any]) -> list[tuple[dict[str, Any], list[str]]]:
    """Trọn 8 tuần × 21 ca xếp theo thứ tự thời gian (tuần, ngày, khung)."""
    rows: list[tuple[int, int, int, dict[str, Any], list[str]]] = []
    for tuan in seed["lich_su_8_tuan"]:
        for c in tuan["ca"]:
            rows.append(
                (
                    int(tuan["tuan"]),
                    int(c["ngay_offset"]),
                    _KHUNG_ORD.get(str(c.get("khung", "")), 9),
                    c,
                    list(tuan["phan_cong"].get(c["id"], [])),
                )
            )
    rows.sort(key=lambda r: (r[0], r[1], r[2]))
    return [(r[3], r[4]) for r in rows]


# ── Máy quy trình: chạy trọn một phiếu bằng đồng hồ ảo ────────────────────
def gia_tri_buoc(minh_chung: str, *, co_anh: bool) -> Any:
    """Giá trị fixture cho một bước. `None` = không cung cấp được minh chứng."""
    if minh_chung == "anh":
        return ANH_FIXTURE if co_anh else None
    if minh_chung in {"so", "kiem_ke"}:
        return "4"
    if minh_chung in {"van_ban", "danh_sach"}:
        return "fixture"
    return True


def chay_phieu(
    mau: str,
    *,
    run_id: str,
    nv_id: str,
    ca_id: str,
    co_anh: bool = True,
    treo: str | None = None,
) -> PhieuRun:
    """Chạy phiếu tới khi hết bước hoặc tới bước không có minh chứng."""
    run = start_phieu(
        run_id=run_id, mau=mau, nv_id=nv_id, ca_id=ca_id, now_ms=0, diem_danh=True
    )
    if treo:
        add_treo(run, treo)
    now = 0
    while True:
        cur = run.current()
        if cur is None:
            break
        val = gia_tri_buoc(cur.minh_chung, co_anh=co_anh)
        if val is None:
            break
        now += NHIP_MS
        complete_buoc(run, cur.ma, val, now)
    return run


def da_xac_nhan_treo(run: PhieuRun) -> bool:
    return any(b.ma == "nguoi_nhan_xac_nhan" and b.done for b in run.buoc)


# ── #1 Tỉ lệ không cần sửa theo tuần ──────────────────────────────────────
def so_1(seed: dict[str, Any]) -> dict[str, Any]:
    tuan_rows: list[dict[str, Any]] = []
    for tuan in seed["lich_su_8_tuan"]:
        data = lich_tuan(seed, tuan)
        kq = solve_hard_only(data)
        tong = sum(len(v) for v in data.phan_cong.values())
        sua = len(cap_phai_sua(data, kq.violations))
        tuan_rows.append(
            {
                "tuan_iso": tuan["tuan_iso"],
                "tong_phan_cong": tong,
                "phai_sua": sua,
                "khong_can_sua": tong - sua,
                "ti_le": round((tong - sua) / tong, 4) if tong else None,
            }
        )
    tong_all = sum(r["tong_phan_cong"] for r in tuan_rows)
    sua_all = sum(r["phai_sua"] for r in tuan_rows)
    return ghi(
        1,
        "Tỉ lệ không cần sửa theo tuần (W1→W8)",
        gia_tri={
            "theo_tuan": tuan_rows,
            "ti_le_8_tuan": round((tong_all - sua_all) / tong_all, 4) if tong_all else None,
            "tong_phan_cong_8_tuan": tong_all,
        },
        trang_thai="do_duoc",
        cach_do=(
            "Với mỗi tuần W1→W8 của `lich_su_8_tuan`: tổng phân công = "
            "Σ|phan_cong[ca]|. 'Phải sửa' = số cặp (ca, nhân viên) bị ít nhất một "
            "ràng buộc cứng c01–c06 chỉ tên khi chạy `ca_solver.solve_hard_only` "
            "trên đúng tuần đó (quy vi phạm về cặp theo `cap_phai_sua`). "
            "Tỉ lệ = (tổng − phải sửa)/tổng. Ở quán thật, tử số đổi sang số cặp bị "
            "quản lý sửa sau công bố, lấy từ `ca_playbook.list_sua`; công thức và "
            "bảng không đổi, chỉ đổi nguồn."
        ),
        canh_bao=(
            "Lịch sử 8 tuần của fixture do bộ sinh dữ liệu bốc ngẫu nhiên tạo ra "
            "(`scripts/generate_fixture_data.py`), KHÔNG do bộ giải sinh. Vì thế con "
            "số này đo mức hợp lệ của lịch sử fixture, không đo hiệu quả hệ thống. "
            "Nó chỉ thành chỉ số §18.2 khi tử số lấy từ sổ sửa của quán thật."
        ),
    )


# ── #3 Thời gian xếp ca trước / sau ───────────────────────────────────────
def so_3() -> dict[str, Any]:
    data = build_lich_input()
    kq = solve_cpsat(data, time_limit_s=60.0)
    return ghi(
        3,
        "Thời gian xếp ca trước / sau",
        gia_tri={
            "truoc_gio": None,
            "truoc_trang_thai": "chua_do",
            "sau_giay": round(kq.elapsed_s, 3),
            "sau_status": kq.status,
            "sau_vi_pham_cung": len(kq.violations),
            "quy_mo": f"{len(data.nhan_vien_ids)} người · {len(data.ca_ids)} ca",
        },
        trang_thai="mot_phan",
        cach_do=(
            "Nửa 'sau' = `ca_solver.solve_cpsat(build_lich_input(), time_limit_s=60)` "
            "trên fixture 25 người · 21 ca, lấy `elapsed_s` do chính bộ giải bấm. "
            "Nửa 'trước' phải bấm đồng hồ khi quản lý quán xếp lịch bằng Excel."
        ),
        ly_do=(
            "Nửa 'trước' chưa đo: cần bấm đồng hồ tại quán khi quản lý xếp lịch tay. "
            "Hồ sơ có nêu khoảng 2,5–4 giờ nhưng đó là con số nghe kể, chưa đo, nên "
            "bộ đo không ghi nó vào đây."
        ),
        khong_tat_dinh=["sau_giay"],
    )


# ── #7 Tỉ lệ hoàn thành phiếu + thời gian TB ───────────────────────────────
def so_7(seed: dict[str, Any]) -> dict[str, Any]:
    kich_ban: dict[str, dict[str, Any]] = {}
    for ten, co_anh in (("du_minh_chung", True), ("thieu_anh", False)):
        tong_buoc = 0
        tong_xong = 0
        so_phieu = 0
        dau_hieu = 0
        for ca, nvs in timeline(seed):
            khung = str(ca.get("khung", ""))
            mau = "mo_quan" if khung == "sang" else ("dong_quan" if khung == "toi" else "")
            if not mau or not nvs:
                continue
            run = chay_phieu(
                mau,
                run_id=f"{mau}:{ca['id']}:{ten}",
                nv_id=nvs[0],
                ca_id=str(ca["id"]),
                co_anh=co_anh,
            )
            d = run_to_dict(run)
            tong_buoc += int(d["so_buoc"])
            tong_xong += int(d["so_xong"])
            so_phieu += 1
            dau_hieu += len(run.anti_fake)
        kich_ban[ten] = {
            "so_phieu": so_phieu,
            "buoc_tong": tong_buoc,
            "buoc_xong": tong_xong,
            "ti_le": round(tong_xong / tong_buoc, 4) if tong_buoc else None,
            "dau_hieu_chong_tich_khong": dau_hieu,
        }
    return ghi(
        7,
        "Tỉ lệ hoàn thành phiếu + thời gian TB",
        gia_tri={
            "du_minh_chung": kich_ban["du_minh_chung"],
            "thieu_anh": kich_ban["thieu_anh"],
            "thoi_gian_tb_phut": None,
            "thoi_gian_trang_thai": "chua_do",
        },
        trang_thai="mot_phan",
        cach_do=(
            "Chạy `ca_ops` qua trọn mẫu `mo_quan` (ca khung 'sang') và `dong_quan` "
            "(ca khung 'toi') cho cả 8 tuần × 7 ngày của fixture, mỗi phiếu do người "
            "đầu tiên trong `phan_cong` giữ. Tỉ lệ = Σ`so_xong`/Σ`so_buoc` do chính "
            "`run_to_dict` đếm. Kịch bản `thieu_anh` không cung cấp ảnh minh chứng "
            "để xem máy dừng ở đâu. Đồng hồ là ảo, nhịp cố định 5 giây/bước."
        ),
        ly_do=(
            "Thời gian TB chưa đo: nhịp 5 giây/bước là đồng hồ ảo do bộ đo đặt để tất "
            "định, không phải thời gian thao tác của người. Muốn có số thật cần dấu "
            "thời gian từ điện thoại nhân viên tại quán."
        ),
        canh_bao=(
            "Tỉ lệ 100% ở kịch bản `du_minh_chung` là kết quả cấu trúc: kịch bản "
            "fixture cung cấp đủ minh chứng cho mọi bước. Nó chứng minh máy quy trình "
            "đi đúng thứ tự và đóng được phiếu, KHÔNG chứng minh nhân viên làm đủ bước."
        ),
    )


# ── #8 Việc treo được ca sau nhận / tổng ──────────────────────────────────
def so_8(seed: dict[str, Any]) -> dict[str, Any]:
    ds = timeline(seed)
    runs: list[PhieuRun | None] = []
    for ca, nvs in ds:
        if not nvs:
            runs.append(None)
            continue
        runs.append(
            chay_phieu(
                "ban_giao_ca",
                run_id=f"bg:{ca['id']}",
                nv_id=nvs[0],
                ca_id=str(ca["id"]),
                treo=f"viec_treo:{ca['id']}",
            )
        )
    tong_treo = 0
    duoc_nhan = 0
    khong_co_ca_sau = 0
    ca_sau_khong_xac_nhan = 0
    for i, run in enumerate(runs):
        if run is None:
            continue
        tong_treo += len(run.treo)
        ke_tiep = runs[i + 1] if i + 1 < len(runs) else None
        if ke_tiep is None:
            khong_co_ca_sau += len(run.treo)
        elif da_xac_nhan_treo(ke_tiep):
            duoc_nhan += len(run.treo)
        else:
            ca_sau_khong_xac_nhan += len(run.treo)
    return ghi(
        8,
        "Việc treo được ca sau nhận / tổng",
        gia_tri={
            "tong_treo": tong_treo,
            "duoc_ca_sau_nhan": duoc_nhan,
            "khong_co_ca_sau": khong_co_ca_sau,
            "ca_sau_khong_xac_nhan": ca_sau_khong_xac_nhan,
            "ti_le": round(duoc_nhan / tong_treo, 4) if tong_treo else None,
        },
        trang_thai="do_duoc",
        cach_do=(
            "Xếp 8 tuần × 21 ca theo thứ tự thời gian, mỗi ca chạy một phiếu "
            "`ban_giao_ca` bằng `ca_ops` và treo lại một việc. Việc treo tính là "
            "'được nhận' khi phiếu bàn giao của ca liền sau hoàn thành bước "
            "`nguoi_nhan_xac_nhan`. Ca cuối chuỗi không có ca sau nên đếm riêng."
        ),
        canh_bao=(
            "Tỉ lệ cao là kết quả cấu trúc: máy quy trình không cho đóng phiếu bàn "
            "giao nếu chưa qua bước người nhận xác nhận, và kịch bản fixture luôn "
            "chạy hết phiếu. Con số này chứng minh chuỗi bàn giao không rơi việc "
            "trong mã, KHÔNG chứng minh nhân viên thật có đọc việc treo."
        ),
    )


# ── #9 Sai số sổ tiêu thụ vs đếm tay ──────────────────────────────────────
def so_9() -> dict[str, Any]:
    return ghi(
        9,
        "Sai số sổ tiêu thụ vs đếm tay",
        gia_tri=None,
        trang_thai="chua_do",
        cach_do=(
            "Công thức §4.3: tiêu thụ trong ca = đếm đầu ca + nhập trong ca − đếm "
            "cuối ca − hao hụt đã ghi. Sai số = |tiêu thụ suy ra − đếm tay| / đếm "
            "tay, tính theo từng mặt hàng trong `danh_muc` 8 mặt hàng của mẫu phiếu. "
            "Cần bốn cột dữ liệu: `kiem_ke_dau_ca`, `nhap_trong_ca`, "
            "`kiem_ke_cuoi_ca`, `ghi_hao_hut`, cộng một cột đếm tay độc lập."
        ),
        ly_do=(
            "Fixture ADR-012 (`data/seed/sample.json`) giờ CÓ khoá `kiem_ke`: 112 ca "
            "sáng/tối × 8 mặt hàng, đủ bốn cột §4.3 cộng cột đếm tay độc lập cho 5 mặt "
            "hàng tuần 1 — nên công thức chạy được về mặt cấu trúc. Nhưng cả bốn cột "
            "và cột đếm tay đều do bộ sinh viết ra, nên sai số tính được chỉ là độ "
            "lệch mà bộ sinh vừa nhét vào: số vòng tròn, không phải số đo. Vẫn cần ≥2 "
            "tuần kiểm kê thật tại quán mới điền được ô này."
        ),
    )


# ── #11 Lần cổng VF đẩy lên người, theo từng cổng ──────────────────────────
def _golden_items() -> list[dict[str, Any]]:
    idx = json.loads((GOLDEN_TKB / "index.json").read_text(encoding="utf-8"))
    return list(idx.get("items", []))


def _chung_cu(item: dict[str, Any]) -> str:
    """Chứng cứ thô của một ảnh TKB = nội dung tệp SVG golden (nếu có)."""
    svg = GOLDEN_TKB / str(item.get("file") or "")
    return svg.read_text(encoding="utf-8") if svg.exists() else ""


def _cong_vf_anh() -> dict[str, dict[str, int]]:
    """VF-SCHEMA / VF-TRACE / VF-CONF trên trọn golden set ảnh TKB."""
    dem = {
        "VF-SCHEMA": {"chay": 0, "day_len_nguoi": 0, "yeu_cau_lam_lai": 0},
        "VF-TRACE": {"chay": 0, "day_len_nguoi": 0, "yeu_cau_lam_lai": 0},
        "VF-CONF": {"chay": 0, "day_len_nguoi": 0, "yeu_cau_lam_lai": 0},
    }
    for item in _golden_items():
        out = extract_tkb(str(item["id"]), mode="replay")
        chung_cu = _chung_cu(item)
        trich: dict[str, Any] = {
            "nhan_vien_id": out["nhan_vien_id"],
            "spans": out["spans"],
            "confidence": out["confidence"],
        }
        # source_span là vị trí thật của nhãn khoảng bận trong tệp SVG chứng cứ.
        if out["spans"] and chung_cu:
            s = out["spans"][0]
            nhan = f"{s['day']} {s['start']}-{s['end']}"
            off = chung_cu.find(nhan)
            if off >= 0:
                trich["source_span"] = {"text_offset": off}
        kq = run_vf_pipeline(
            trich, chung_cu, ["nhan_vien_id", "spans", "confidence"]
        )
        for ten, r in (
            ("VF-SCHEMA", kq.schema),
            ("VF-TRACE", kq.trace),
            ("VF-CONF", kq.conf),
        ):
            dem[ten]["chay"] += 1
            if getattr(r, "escalate", False):
                dem[ten]["day_len_nguoi"] += 1
            if getattr(r, "retry_once", False):
                dem[ten]["yeu_cau_lam_lai"] += 1
    return dem


def _cong_vf_num(seed: dict[str, Any]) -> dict[str, int]:
    """VF-NUM trên câu diễn giải của mọi phân công tuần W1 fixture."""
    data = lich_tuan(seed, seed["lich_su_8_tuan"][0])
    chay = 0
    day = 0
    for ca_id, nvs in data.phan_cong.items():
        for nv in nvs:
            ld = sinh_ly_do(data, ca_id, nv)
            cho_phep = ld.so_lieu_cho_phep()
            kq = dien_giai(
                ld.ma_list(),
                MA_LY_DO,
                {d.ma: d.so_lieu for d in ld.ly_do},
                so_lieu_cho_phep=cho_phep,
            )
            chay += 1
            if not validate_num(kq.cau, cho_phep).passed:
                day += 1
    return {"chay": chay, "day_len_nguoi": day, "yeu_cau_lam_lai": 0}


def _cong_vf_rule(seed: dict[str, Any]) -> dict[str, int]:
    """VF-RULE trên luật ứng viên dựng từ 8 tuần: nhóm theo (thứ, khung)."""
    nhom: dict[tuple[str, str], list[tuple[str, int]]] = {}
    for tuan in seed["lich_su_8_tuan"]:
        for c in tuan["ca"]:
            khoa = (_THU[int(c["ngay_offset"])], str(c.get("khung", "")))
            n = len(tuan["phan_cong"].get(c["id"], []))
            nhom.setdefault(khoa, []).append((str(tuan["tuan_iso"]), n))
    chay = 0
    day = 0
    for (thu, khung), quan_sat in sorted(nhom.items()):
        can = max(n for _, n in quan_sat)
        luat = {
            "loai": "nhu_cau_ca",
            "cau": f"{thu} khung {khung} cần {can} người",
            "dieu_kien": {"thu": thu, "khung": khung, "so_nguoi": can},
            "bang_chung": [t for t, _ in quan_sat],
        }
        chay += 1
        if not validate_rule(luat).passed:
            day += 1
    return {"chay": chay, "day_len_nguoi": day, "yeu_cau_lam_lai": 0}


def _cong_vf_conflict() -> dict[str, int]:
    """VF-CONFLICT: TKB do AG-TKB đọc từ ảnh vs TKB khai trong seed."""
    base = build_lich_input()
    chay = 0
    day = 0
    for item in _golden_items():
        out = extract_tkb(str(item["id"]), mode="replay")
        nv = str(out["nhan_vien_id"])
        doc_anh = sorted((s["day"], s["start"], s["end"]) for s in out["spans"])
        khai_seed = sorted(base.tkb.get(nv, []))
        kq = present_conflict(
            {"nguoi": nv, "khung": "tkb_tuan", "claim": str(doc_anh), "tu": "ag_tkb"},
            {"nguoi": nv, "khung": "tkb_tuan", "claim": str(khai_seed), "tu": "seed"},
        )
        chay += 1
        if kq.conflict:
            day += 1
    return {"chay": chay, "day_len_nguoi": day, "yeu_cau_lam_lai": 0}


def so_11(seed: dict[str, Any]) -> dict[str, Any]:
    theo_cong = _cong_vf_anh()
    theo_cong["VF-NUM"] = _cong_vf_num(seed)
    theo_cong["VF-RULE"] = _cong_vf_rule(seed)
    theo_cong["VF-CONFLICT"] = _cong_vf_conflict()
    return ghi(
        11,
        "Lần cổng VF đẩy lên người (theo cổng)",
        gia_tri={
            "theo_cong": theo_cong,
            "tong_day_len_nguoi": sum(v["day_len_nguoi"] for v in theo_cong.values()),
            "tong_lan_chay_cong": sum(v["chay"] for v in theo_cong.values()),
        },
        trang_thai="do_duoc",
        cach_do=(
            "Sáu cổng, mỗi cổng một bộ golden dựng từ fixture: "
            "VF-SCHEMA/VF-TRACE/VF-CONF chạy `ca_gates.run_vf_pipeline` trên 51 ảnh "
            "`data/golden/tkb` (chứng cứ = nội dung tệp SVG, `source_span` là vị trí "
            "thật của nhãn khoảng bận trong tệp đó); VF-NUM chạy `validate_num` trên "
            "câu AG-EXPLAIN soạn cho từng phân công tuần W1, tập số cho phép lấy từ "
            "`sinh_ly_do(...).so_lieu_cho_phep()`; VF-RULE chạy `validate_rule` trên "
            "21 luật ứng viên `nhu_cau_ca` dựng từ 8 tuần (nhóm theo thứ × khung, "
            "bằng chứng = các tuần quan sát); VF-CONFLICT so TKB do AG-TKB đọc từ ảnh "
            "với TKB khai trong seed cho cùng một người. "
            "'Đẩy lên người' = `escalate` (hoặc `conflict` với VF-CONFLICT)."
        ),
        canh_bao=(
            "Số của VF-CONFLICT cao vì hai nguồn TKB trong fixture được sinh độc lập "
            "(seed khai 1 khối bận, ảnh golden vẽ 3–4 khối), nên đây là tính chất của "
            "fixture chứ không phải mức lệch dữ liệu tại quán."
        ),
    )


# ── #12 Gọi model/ngày · p50/p95 · token ──────────────────────────────────
def so_12() -> dict[str, Any]:
    rt = AgentRuntime()
    router = FreeTierRouter(mode="replay")
    items = _golden_items()
    goi_replay = 0
    prompt_chars = 0
    provider_khac_replay = 0
    for item in items:
        quyet = router.choose("vision:tkb")
        if quyet.provider != "replay":
            provider_khac_replay += 1
        out = rt.run_replay("ag_tkb", "0.1.0", {"id": str(item["id"])})
        goi_replay += 1
        prompt_chars += int(out["prompt_chars"])
    return ghi(
        12,
        "Gọi model/ngày · p50/p95 latency · token",
        gia_tri={
            "che_do": "replay",
            "so_lan_goi_mang_that": 0,
            "so_lan_goi_replay_mot_ngay": goi_replay,
            "provider_khac_replay": provider_khac_replay,
            "tong_prompt_chars": prompt_chars,
            "p50_ms": None,
            "p95_ms": None,
            "token_ngay": None,
            "latency_token_trang_thai": "chua_do",
        },
        trang_thai="mot_phan",
        cach_do=(
            "Một ngày demo = quản lý nạp trọn 51 ảnh golden. Với mỗi ảnh, "
            "`ca_agents.router.FreeTierRouter(mode='replay').choose()` chọn provider "
            "và `AgentRuntime.run_replay('ag_tkb','0.1.0', ...)` chạy một lần; bộ đo "
            "đếm số lần gọi và tổng `prompt_chars` do runtime trả về."
        ),
        ly_do=(
            "p50/p95 và token chưa đo: đây là REPLAY, 0 lần gọi mạng thật (router trả "
            "`provider='replay'`, xem `packages/agents/tests/test_no_network.py`). Mọi "
            "latency đo được ở đây là latency đọc tệp cục bộ, không phải latency LLM; "
            "token cũng không sinh ra vì không có lời gọi mô hình nào. Muốn có số thật "
            "phải bật chế độ live và đọc hoá đơn provider."
        ),
    )


# ── Năm số đã đo ở nơi khác — bộ đo này KHÔNG tính lại, không sửa ─────────
DO_O_NOI_KHAC: list[dict[str, str]] = [
    {"so": "2", "ten": "Chi phí thực tế toàn dự án", "do_boi": "sổ 14 dòng + ảnh hạn mức"},
    {"so": "4", "ten": "Vi phạm ràng buộc cứng", "do_boi": "scripts/verify_hard.py"},
    {"so": "5", "ten": "AG-TKB accuracy + % đẩy người", "do_boi": "scripts/eval_ag_tkb.py"},
    {"so": "6", "ten": "AG-MSG confusion 6 ý định", "do_boi": "scripts/eval_ag_msg.py"},
    {"so": "10", "ten": "Vòng đời luật 8 bước", "do_boi": "POST /cam-nang/chay-8-buoc"},
]


def do_tat_ca() -> dict[str, Any]:
    """Đo 7 con số cần quán thật, trên fixture. Tất định."""
    seed = load_seed(SEED_PATH)
    return {
        "phien_ban_bo_do": 1,
        "nguon_du_lieu": "data/seed/sample.json — Quán Fixture NHỊP QUÁN (ADR-012)",
        "che_do_agent": "replay",
        "nhan_nguon_cho_phep": [NGUON_FIXTURE, NGUON_QUAN],
        "ghi_chu": (
            "Bộ đo này chỉ đo 7 số cần quán thật (#1 #3 #7 #8 #9 #11 #12). "
            "Năm số còn lại đã đo ở nơi khác và không bị tính lại ở đây."
        ),
        "so_do": [so_1(seed), so_3(), so_7(seed), so_8(seed), so_9(), so_11(seed), so_12()],
        "khong_do_o_day": DO_O_NOI_KHAC,
    }


def tom_tat(rec: dict[str, Any]) -> str:
    """Một dòng ngắn cho bảng stdout."""
    g = rec["gia_tri"]
    if g is None:
        return "chưa đo"
    so = rec["so"]
    if so == 1:
        return (
            f"8 tuần: {g['ti_le_8_tuan']:.1%} không cần sửa "
            f"({g['tong_phan_cong_8_tuan']} phân công)"
        )
    if so == 3:
        return f"trước: chưa đo · sau: {g['sau_giay']} s ({g['sau_status']})"
    if so == 7:
        a = g["du_minh_chung"]
        b = g["thieu_anh"]
        return (
            f"đủ minh chứng {a['buoc_xong']}/{a['buoc_tong']} = {a['ti_le']:.1%} · "
            f"thiếu ảnh {b['buoc_xong']}/{b['buoc_tong']} = {b['ti_le']:.1%} · "
            "thời gian TB: chưa đo"
        )
    if so == 8:
        return f"{g['duoc_ca_sau_nhan']}/{g['tong_treo']} = {g['ti_le']:.1%}"
    if so == 11:
        phan = " · ".join(
            f"{k} {v['day_len_nguoi']}/{v['chay']}" for k, v in g["theo_cong"].items()
        )
        return phan
    if so == 12:
        return (
            f"replay {g['so_lan_goi_replay_mot_ngay']} lượt/ngày · mạng thật "
            f"{g['so_lan_goi_mang_that']} · p50/p95 + token: chưa đo"
        )
    return json.dumps(g, ensure_ascii=False)


def in_bang(payload: dict[str, Any]) -> None:
    print("=== BỘ ĐO 12 SỐ §18.2 — 7 số đo trên fixture ADR-012 ===")
    print(f"nguồn dữ liệu: {payload['nguon_du_lieu']}")
    print(f"chế độ agent: {payload['che_do_agent']}")
    print("")
    print(f"{'#':>3} | {'nhãn nguồn':<18} | {'trạng thái':<9} | số")
    print("-" * 96)
    for rec in payload["so_do"]:
        nhan = "mô phỏng fixture" if rec["nguon"] == NGUON_FIXTURE else "quán thật"
        print(f"{rec['so']:>3} | {nhan:<18} | {rec['trang_thai']:<9} | {tom_tat(rec)}")
    print("-" * 96)
    for rec in payload["so_do"]:
        if rec.get("ly_do"):
            print(f"  #{rec['so']} chưa đo phần nào: {rec['ly_do']}")
    print("")
    print("Năm số đã đo ở nơi khác (bộ đo này không tính lại):")
    for row in payload["khong_do_o_day"]:
        print(f"  #{row['so']:<2} {row['ten']} — {row['do_boi']}")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    payload = do_tat_ca()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    in_bang(payload)
    print("")
    print(f"đã ghi {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
