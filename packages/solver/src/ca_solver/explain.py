"""Sinh mã lý do cho từng phân công — TẤT ĐỊNH, không có LLM.

Hồ sơ §13.1 (A · 1,5 ngày) và §7.2: lõi quyết định không có agent nào.
AG-EXPLAIN chỉ *dịch* mã lý do ở đây thành câu tiếng Việt; nó không được
tự tính ra con số nào. Vì thế mỗi mã lý do mang kèm `so_lieu` — tập số
được phép xuất hiện trong câu diễn giải, để cổng VF-NUM kiểm được.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ca_solver.model import LichInput

# ── Từ điển mã lý do ──────────────────────────────────────────────────────
# Mỗi mã là một sự thật kiểm được từ LichInput. Không mã nào nói về
# thái độ hay năng lực của một con người (§9.1 cấm tuyệt đối).
MA_LY_DO: dict[str, str] = {
    "KY_NANG_KHOP": "có kỹ năng vị trí ca này cần",
    "KHONG_TRUNG_TKB": "không trùng giờ học",
    "KHONG_NGHI_PHEP": "không nằm trong ngày đã duyệt nghỉ phép",
    "CON_TRAN_GIO": "còn quỹ giờ trong tuần",
    "DU_KHOANG_NGHI": "đủ khoảng nghỉ so với ca liền trước",
    "NO_CONG_BANG_CAO": "đang có nợ công bằng cao nên được ưu tiên ca nhẹ",
    "NO_CONG_BANG_THAP": "đang có nợ công bằng thấp nên nhận ca này",
    "CA_CAN_THEM_NGUOI": "ca này cần thêm người cho đủ định mức",
}

# Mã lý do vô nghiệm — dùng khi không phủ được ca (§16.2 R9)
MA_VO_NGHIEM: dict[str, str] = {
    "THIEU_NGUOI_KY_NANG": "không đủ người có kỹ năng vị trí này",
    "THIEU_NGUOI_RANH": "không đủ người rảnh trong khung giờ này",
}


@dataclass
class LyDo:
    """Một mã lý do đã gắn với dữ liệu cụ thể."""

    ma: str
    so_lieu: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.ma not in MA_LY_DO and self.ma not in MA_VO_NGHIEM:
            raise ValueError(f"ma_ly_do_khong_ton_tai:{self.ma}")


@dataclass
class LyDoPhanCong:
    """Toàn bộ lý do cho một cặp (ca, nhân viên)."""

    ca_id: str
    nhan_vien_id: str
    ly_do: list[LyDo] = field(default_factory=list)

    def ma_list(self) -> list[str]:
        return [d.ma for d in self.ly_do]

    def so_lieu_cho_phep(self) -> set[str]:
        """Tập số VF-NUM được phép thấy trong câu diễn giải."""
        pool: set[str] = set()
        for d in self.ly_do:
            pool.update(d.so_lieu)
        return pool


def _fmt(x: float) -> str:
    """Số nguyên in không thập phân, để VF-NUM so khớp được chuỗi."""
    return str(int(x)) if float(x).is_integer() else str(x)


def _tong_no(data: LichInput, nv: str) -> float:
    return sum((data.debt.get(nv) or {}).values())


def sinh_ly_do(data: LichInput, ca_id: str, nhan_vien_id: str) -> LyDoPhanCong:
    """Sinh mã lý do cho một phân công đã có trong `data.phan_cong`.

    Chỉ phát mã khi dữ liệu chứng minh được. Không suy đoán.
    """
    out = LyDoPhanCong(ca_id=ca_id, nhan_vien_id=nhan_vien_id)

    # KY_NANG_KHOP — cần vị trí và nhân viên có kỹ năng đó
    vi_tri = data.vi_tri_can.get(ca_id)
    if vi_tri and vi_tri in (data.ky_nang.get(nhan_vien_id) or set()):
        out.ly_do.append(LyDo("KY_NANG_KHOP"))

    # KHONG_TRUNG_TKB — chỉ phát khi nhân viên thật sự có khai TKB
    if data.tkb.get(nhan_vien_id):
        out.ly_do.append(LyDo("KHONG_TRUNG_TKB"))

    # KHONG_NGHI_PHEP — chỉ phát khi ca có gắn ngày
    ngay = (data.ca_meta.get(ca_id) or {}).get("ngay")
    if ngay and (nhan_vien_id, ngay) not in data.nghi_phep:
        out.ly_do.append(LyDo("KHONG_NGHI_PHEP"))

    # CON_TRAN_GIO — mang theo 2 số: đã làm và trần tuần
    da_lam = data.gio_da_lam.get(nhan_vien_id)
    if da_lam is not None and data.tran_gio_tuan > 0 and da_lam < data.tran_gio_tuan:
        out.ly_do.append(
            LyDo("CON_TRAN_GIO", so_lieu=[_fmt(da_lam), _fmt(data.tran_gio_tuan)])
        )

    # DU_KHOANG_NGHI — mang theo số giờ nghỉ tối thiểu đang cấu hình
    if data.khoang_nghi_gio > 0:
        out.ly_do.append(
            LyDo("DU_KHOANG_NGHI", so_lieu=[_fmt(data.khoang_nghi_gio)])
        )

    # Nợ công bằng — so với trung vị nhóm, mang theo tổng nợ của người này
    if data.debt:
        moi_nguoi = sorted(_tong_no(data, nv) for nv in data.debt)
        giua = moi_nguoi[len(moi_nguoi) // 2]
        cua_toi = _tong_no(data, nhan_vien_id)
        ma = "NO_CONG_BANG_CAO" if cua_toi > giua else "NO_CONG_BANG_THAP"
        out.ly_do.append(LyDo(ma, so_lieu=[_fmt(cua_toi)]))

    # CA_CAN_THEM_NGUOI — mang theo định mức của ca
    can = data.so_nguoi_toi_thieu.get(ca_id)
    if can:
        out.ly_do.append(LyDo("CA_CAN_THEM_NGUOI", so_lieu=[_fmt(can)]))

    return out


def sinh_ly_do_toan_lich(data: LichInput) -> list[LyDoPhanCong]:
    """Sinh mã lý do cho mọi phân công trong lịch."""
    out: list[LyDoPhanCong] = []
    for ca_id, nhan_viens in data.phan_cong.items():
        for nv in nhan_viens:
            out.append(sinh_ly_do(data, ca_id, nv))
    return out
