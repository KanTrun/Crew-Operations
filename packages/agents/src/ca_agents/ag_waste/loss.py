"""Động cơ hao hụt — toán tất định, không I/O, không LLM (ADR-002).

Đây là phần **tính** của AG-WASTE. Nó trả lời được câu hỏi mà `extract.cluster`
không trả lời được: nguyên liệu nào hao, bao nhiêu, tỷ lệ bao nhiêu, do nguyên
nhân nào.

Ranh giới module
----------------
Mọi hàm ở đây là **hàm thuần**: nhận dict/list đã đọc sẵn, trả `LossLine` /
`LossCauseRank`. Không đọc DB, không gọi mạng, không gọi agent khác. Tầng API đọc
`kv kiem_ke` / `menu_mon.bom` / `waste_notes` rồi truyền vào (xem `PHAM_VI.md`).

Quy ước số
----------
`None` = chưa có dữ liệu, `0.0` = có dữ liệu và bằng không. Một mặt hàng chỉ xuất
hiện ở **một** vế thì vế kia là `None` và mức độ là `thieu_du_lieu` — không được
suy ra "đạt" từ chỗ trống (fail-closed, xem `ca_contracts.loss`).

Công thức
---------
Lấy đúng công thức đã kiểm chứng trong repo
(`skills/repositories/repo-skills/barista-waste-audit/scripts/audit_recipe_waste.py`):

    lý thuyết = Σ (định mức nguyên liệu × số phần đã bán)
    thực tế   = Σ (đầu ca + nhập trong ca − cuối ca − hao hụt đã ghi)
    lệch      = thực tế − lý thuyết
    tỷ lệ %   = lệch / lý thuyết × 100
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from ca_contracts.loss import (
    LossBasis,
    LossCauseRank,
    LossCauseSource,
    LossLevel,
    LossLine,
    LossSummary,
    LossThreshold,
)

# ── Bí danh tên mặt hàng ──────────────────────────────────────────────────────
#
# Ba nguồn gọi tên nguyên liệu khác nhau và không nguồn nào sai:
#   - công thức BOM (`menu_mon.bom`) dùng `sua_ml`, `cafe_g` — theo đơn vị đo
#   - phiếu kiểm kê (`kiem_ke`) dùng `sua_tuoi`, `ca_phe_hat` — theo mặt hàng kho
#   - ghi chú hao hụt (`waste_notes`) dùng `sua_tuoi`, `ca_phe` — theo cách gọi
#
# Nếu không quy về một mã, mọi dòng đều ra `thieu_du_lieu` dù dữ liệu có thật.
# Bảng này là ánh xạ **tường minh**: cố tình không fuzzy-match, vì ghép gần đúng
# sẽ nối sai hai mặt hàng khác nhau trong im lặng — sai kiểu đó khó phát hiện hơn
# nhiều so với một dòng "chưa đủ dữ liệu" hiện ra trước mắt.
BI_DANH: dict[str, str] = {
    # BOM (theo đơn vị đo) → mã mặt hàng kho
    "cafe_g": "ca_phe_hat",
    "sua_ml": "sua_tuoi",
    "nuoc_ml": "nuoc_loc",
    "tra_g": "tra",
    "dao_lat": "dao",
    # Cách gọi khác trong ghi chú ca → mã mặt hàng kho
    "ca_phe": "ca_phe_hat",
    "suatuoi": "sua_tuoi",
    "sua": "sua_tuoi",
    "tra_da": "tra",
    "ly_nhua": "ly",
    "banh_kem": "banh",
    "da_vien": "da",
}

# Mặt hàng tính bằng số nguyên (chai/lon/cái) — hiển thị không cần số thập phân.
DON_VI_NGUYEN: frozenset[str] = frozenset(
    {"ly", "ong_hut", "banh", "chai", "lon", "nuoc_dong_chai", "hop", "goi"}
)

# Ghi chú ca không nêu nguyên nhân thì gom vào mã này thay vì bỏ đi. Bỏ đi sẽ làm
# tổng số lần ghi hụt so với thực tế và tỷ lệ phần trăm bị thổi lên.
NGUYEN_NHAN_KHONG_RO = "khong_ro"


def chuan_hoa_mat_hang(ma: str) -> str:
    """Quy một tên mặt hàng bất kỳ về mã chuẩn dùng chung cho cả ba nguồn.

    Mã lạ được giữ nguyên (đã hạ chữ, bỏ khoảng trắng) chứ không bị nuốt — quán
    có nguyên liệu riêng thì vẫn phải thấy dòng hao hụt của nguyên liệu đó.
    """
    raw = str(ma or "").strip().lower().replace(" ", "_").replace("-", "_")
    return BI_DANH.get(raw, raw)


def don_vi_mac_dinh(mat_hang: str) -> str:
    """Đơn vị hiển thị suy từ mã mặt hàng; chỉ là nhãn, không ảnh hưởng phép tính."""
    if mat_hang in DON_VI_NGUYEN:
        return "cái"
    if mat_hang.endswith("_ml") or mat_hang in {"sua_tuoi", "nuoc_loc"}:
        return "ml"
    if mat_hang.endswith("_g") or mat_hang in {"ca_phe_hat", "tra", "matcha", "dao"}:
        return "g"
    return "đơn vị"


def gom_theo_mat_hang(rows: Iterable[Mapping[str, Any]], truong_so: str) -> dict[str, float]:
    """Cộng dồn một trường số theo mặt hàng đã chuẩn hoá.

    Nhiều dòng cùng mặt hàng (nhiều ca, nhiều đơn) phải gộp thành một con số —
    nếu không thì bảng hao hụt hiện trùng mặt hàng và tổng bị đếm nhiều lần.
    Dòng thiếu số, số không đọc được, hoặc ≤ 0 bị bỏ qua.
    """
    ra: dict[str, float] = defaultdict(float)
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        ma = chuan_hoa_mat_hang(str(row.get("mat_hang") or row.get("hang") or ""))
        if not ma:
            continue
        try:
            so = float(row.get(truong_so))
        except (TypeError, ValueError):
            continue
        if so <= 0:
            continue
        ra[ma] += so
    return dict(ra)


def tinh_ly_thuyet(
    ban_theo_mon: Mapping[str, float],
    bom_theo_mon: Mapping[str, Mapping[str, float]],
) -> dict[str, float]:
    """Lượng nguyên liệu lẽ ra phải dùng: định mức công thức × số phần đã bán.

    `ban_theo_mon` là số phần đã bán theo `mon_id`; `bom_theo_mon` là định mức
    nguyên liệu cho một phần của món đó. Món không có công thức bị bỏ qua —
    không có định mức thì không có gì để so.
    """
    ra: dict[str, float] = defaultdict(float)
    for mon_id, so_phan in ban_theo_mon.items():
        try:
            n = float(so_phan)
        except (TypeError, ValueError):
            continue
        if n <= 0:
            continue
        bom = bom_theo_mon.get(mon_id)
        if not isinstance(bom, Mapping):
            continue
        for nguyen_lieu, dinh_muc in bom.items():
            ma = chuan_hoa_mat_hang(str(nguyen_lieu))
            if not ma:
                continue
            try:
                moi_phan = float(dinh_muc)
            except (TypeError, ValueError):
                continue
            if moi_phan <= 0:
                continue
            ra[ma] += moi_phan * n
    return dict(ra)


def _xep_muc_do(
    *, ly_thuyet: float | None, thuc_te: float | None, ty_le: float | None, nguong: LossThreshold, mat_hang: str
) -> tuple[LossLevel, list[str]]:
    """Chọn mức độ và ghi lại vế còn thiếu.

    Chỉ khi **cả hai** vế đều có số mới được kết luận đạt / cảnh báo / nghiêm
    trọng. Một vế trống ⇒ `thieu_du_lieu`, kèm tên vế thiếu.
    """
    thieu: list[str] = []
    if ly_thuyet is None:
        thieu.append("ly_thuyet")
    if thuc_te is None:
        thieu.append("thuc_te")
    if thieu:
        return LossLevel.THIEU_DU_LIEU, thieu

    # Có đủ hai vế. Lý thuyết bằng 0 nên không chia được tỷ lệ — phải xét hai
    # trường hợp khác hẳn nhau:
    #   - thực tế > 0: đã dùng nguyên liệu mà công thức không hề dự kiến ⇒ nghiêm
    #     trọng, vì không có cơ sở nào biện minh cho lượng đã dùng.
    #   - thực tế = 0: không bán, không dùng, không hụt ⇒ đạt. Đây là "có đo và
    #     bằng không", khác hẳn "chưa đo" (đã chặn ở nhánh `thieu` phía trên).
    if ty_le is None:
        return (LossLevel.NGHIEM_TRONG if (thuc_te or 0.0) > 0 else LossLevel.DAT), []

    nguong_rieng = nguong.nguong_cho(mat_hang)
    # Chỉ hao **dương** mới là mất mát. Lệch âm (dùng ít hơn lý thuyết) không phải
    # hao hụt — đó là đếm dư hoặc công thức chưa khớp, hạ xuống mức đạt để không
    # báo động sai và để người đọc tự thấy con số âm.
    if ty_le <= nguong_rieng:
        return LossLevel.DAT, []
    if ty_le >= nguong.nghiem_trong_phan_tram:
        return LossLevel.NGHIEM_TRONG, []
    return LossLevel.CANH_BAO, []


def _lam_tron(mat_hang: str, value: float) -> float:
    """Mặt hàng đếm bằng cái thì làm tròn về số nguyên; còn lại giữ hai chữ số."""
    if mat_hang in DON_VI_NGUYEN:
        return float(round(value))
    return round(value, 2)


def so_hao_hut(
    ly_thuyet: Mapping[str, float] | None,
    thuc_te: Mapping[str, float] | None,
    *,
    nguong: LossThreshold | None = None,
    ten_theo_mat_hang: Mapping[str, str] | None = None,
    ghi_chu_theo_mat_hang: Mapping[str, str] | None = None,
) -> list[LossLine]:
    """So hai vế và sinh một dòng cho mỗi mặt hàng xuất hiện ở **một trong hai**.

    Mặt hàng chỉ có ở một vế vẫn phải hiện — đó thường là chỗ đáng xem nhất
    (kiểm kê có mà không bán được, hoặc bán mà chưa kiểm kê). Dòng đó mang
    `thieu_du_lieu` để người đọc biết ngay là chưa kết luận được gì.

    Trả danh sách đã sắp theo mức độ nặng trước, rồi theo số tuyệt đối của lệch —
    dòng đáng chú ý nhất nằm trên cùng.
    """
    nguong = nguong or LossThreshold()
    ten_map = ten_theo_mat_hang or {}
    ghi_map = ghi_chu_theo_mat_hang or {}
    ly = dict(ly_thuyet or {})
    thuc = dict(thuc_te or {})

    dong: list[LossLine] = []
    for ma in sorted(set(ly) | set(thuc)):
        ly_v = ly.get(ma)
        thuc_v = thuc.get(ma)

        lech: float | None = None
        ty_le: float | None = None
        if ly_v is not None and thuc_v is not None:
            lech = thuc_v - ly_v
            if ly_v > 0:
                ty_le = round(lech / ly_v * 100.0, 2)
            # ly_v == 0 and thuc_v > 0: tỷ lệ không xác định (chia cho 0) — để None,
            # và `_xep_muc_do` coi đây là nghiêm trọng vì dùng thật mà không có cơ sở.

        muc_do, thieu = _xep_muc_do(
            ly_thuyet=ly_v, thuc_te=thuc_v, ty_le=ty_le, nguong=nguong, mat_hang=ma
        )

        dong.append(
            LossLine(
                mat_hang=ma,
                ten=ten_map.get(ma) or ma.replace("_", " "),
                don_vi=don_vi_mac_dinh(ma),
                ly_thuyet=None if ly_v is None else _lam_tron(ma, ly_v),
                thuc_te=None if thuc_v is None else _lam_tron(ma, thuc_v),
                lech=None if lech is None else _lam_tron(ma, lech),
                ty_le_phan_tram=ty_le,
                muc_do=muc_do,
                nguong_phan_tram=nguong.nguong_cho(ma),
                co_so=(
                    LossBasis.KE_HOACH_KIEM_KE
                    if ly_v is None or thuc_v is None
                    else LossBasis.HON_HOP
                ),
                thieu_ve=thieu,
                ghi_chu=ghi_map.get(ma, ""),
            )
        )

    _THU_TU = {
        LossLevel.NGHIEM_TRONG: 0,
        LossLevel.CANH_BAO: 1,
        LossLevel.THIEU_DU_LIEU: 2,
        LossLevel.DAT: 3,
    }
    dong.sort(key=lambda d: (_THU_TU[d.muc_do], -abs(d.lech or 0.0), d.mat_hang))
    return dong


def xep_hang_nguyen_nhan(
    notes: Iterable[Mapping[str, Any]],
) -> list[LossCauseRank]:
    """Xếp hạng nguyên nhân hao hụt từ ghi chú trong ca.

    Đọc hai trường: `nguyen_nhan` (mã, có trong bản ghi thật và trong seed) và
    `ly_do` (mã tự do của đường ghi cũ). Bản ghi không nêu nguyên nhân vẫn được
    đếm vào `khong_ro` — bỏ đi sẽ làm tổng số lần hụt và tỷ lệ phần trăm sai.
    """
    dem: Counter[str] = Counter()
    mat_hang_theo_nn: dict[str, Counter[str]] = defaultdict(Counter)

    for note in notes:
        if not isinstance(note, Mapping):
            continue
        ma_nn = str(note.get("nguyen_nhan") or note.get("ly_do") or "").strip().lower()
        ma_nn = ma_nn.replace(" ", "_") or NGUYEN_NHAN_KHONG_RO
        dem[ma_nn] += 1

        ma_hang = chuan_hoa_mat_hang(str(note.get("mat_hang") or note.get("mon_id") or ""))
        if ma_hang:
            mat_hang_theo_nn[ma_nn][ma_hang] += 1

    tong = sum(dem.values())
    if tong == 0:
        return []

    ra: list[LossCauseRank] = []
    for ma_nn, so_lan in dem.most_common():
        lien_quan = [mh for mh, _ in mat_hang_theo_nn[ma_nn].most_common(5)]
        ra.append(
            LossCauseRank(
                nguyen_nhan=ma_nn,
                ten=ma_nn.replace("_", " "),
                so_lan=so_lan,
                mat_hang_lien_quan=lien_quan,
                ty_le_tong=round(so_lan / tong * 100.0, 2),
                nguon=(
                    LossCauseSource.NGUYEN_NHAN_GHI
                    if ma_nn != NGUYEN_NHAN_KHONG_RO
                    else LossCauseSource.HON_HOP
                ),
            )
        )
    return ra


def tong_hop(
    dong: list[LossLine],
    nguyen_nhan: list[LossCauseRank] | None = None,
    *,
    ky: str = "hom_nay",
    co_du_lieu_mau: bool = False,
) -> LossSummary:
    """Gói các dòng hao hụt thành một tóm tắt đọc được.

    `ty_le_trung_binh` chỉ tính trên các dòng **đủ hai vế**. Nếu lấy trung bình cả
    dòng thiếu dữ liệu thì con số trung bình bị kéo lệch bởi những chỗ chưa đo
    được — đúng kiểu bịa số mà hợp đồng cấm.
    """
    du_hai_ve = [d for d in dong if d.ty_le_phan_tram is not None]
    trung_binh = (
        round(sum(d.ty_le_phan_tram or 0.0 for d in du_hai_ve) / len(du_hai_ve), 2)
        if du_hai_ve
        else None
    )
    return LossSummary(
        ky=ky,
        tong_dong=len(dong),
        so_nghiem_trong=sum(1 for d in dong if d.muc_do is LossLevel.NGHIEM_TRONG),
        so_canh_bao=sum(1 for d in dong if d.muc_do is LossLevel.CANH_BAO),
        so_thieu_du_lieu=sum(1 for d in dong if d.muc_do is LossLevel.THIEU_DU_LIEU),
        ty_le_trung_binh=trung_binh,
        dong=dong,
        nguyen_nhan_hang_dau=list(nguyen_nhan or []),
        co_du_lieu_mau=co_du_lieu_mau,
    )


def doc_bom_theo_mon(menu_items: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, float]]:
    """Dựng `mon_id -> định mức nguyên liệu` từ danh mục món (`menu_mon`)."""
    ra: dict[str, Mapping[str, float]] = {}
    for mon in menu_items:
        if not isinstance(mon, Mapping):
            continue
        ma = str(mon.get("id") or "").strip()
        bom = mon.get("bom")
        if ma and isinstance(bom, Mapping):
            ra[ma] = bom
    return ra


def doc_ban_theo_mon(don_rows: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Đếm số phần đã bán theo món từ các đơn quầy.

    Chỉ tính đơn **đã xong**: đơn đang pha hoặc đã hủy thì nguyên liệu chưa ra
    khỏi kho (hoặc chưa từng ra), tính vào sẽ đẩy lý thuyết lên sai.
    """
    ra: dict[str, float] = defaultdict(float)
    for don in don_rows:
        if not isinstance(don, Mapping):
            continue
        if str(don.get("trang_thai") or "") != "xong":
            continue
        for dong in don.get("dong") or []:
            if not isinstance(dong, Mapping):
                continue
            ma = str(dong.get("mon_id") or "").strip()
            try:
                n = float(dong.get("so_luong"))
            except (TypeError, ValueError):
                continue
            if ma and n > 0:
                ra[ma] += n
    return dict(ra)


def tinh_tu_kiem_ke(muc: Iterable[Mapping[str, Any]]) -> dict[str, float]:
    """Lượng thực tế đã dùng của một phiếu kiểm kê.

    Công thức §4.3 của hồ sơ tổng thể:

        tiêu thụ = đầu ca + nhập trong ca − cuối ca − hao hụt đã ghi

    Trừ `hao_hut_ghi` là chủ ý: phần đã ghi hao hụt không tính là tiêu thụ, nếu
    không thì nó bị đếm hai lần (một lần ở đây, một lần ở dòng hao hụt).
    """
    ra: dict[str, float] = defaultdict(float)
    for row in muc:
        if not isinstance(row, Mapping):
            continue
        ma = chuan_hoa_mat_hang(str(row.get("mat_hang") or ""))
        if not ma:
            continue
        try:
            dau = float(row.get("dau_ca") or 0.0)
            nhap = float(row.get("nhap_trong_ca") or 0.0)
            cuoi = float(row.get("cuoi_ca") or 0.0)
            hao = float(row.get("hao_hut_ghi") or 0.0)
        except (TypeError, ValueError):
            continue
        da_dung = dau + nhap - cuoi - hao
        # Có thể âm khi số liệu nhập sai (cuối ca lớn hơn đầu ca + nhập). Ghi nhận
        # ở mức 0 thay vì để số âm lan vào tổng, và không im lặng bỏ dòng.
        ra[ma] += max(0.0, da_dung)
    return dict(ra)
