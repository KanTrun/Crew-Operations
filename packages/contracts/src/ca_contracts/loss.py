"""Hợp đồng dữ liệu — Hao hụt tiêu thụ theo nguyên liệu (plan 260923-1736).

ADR-003 (contracts-first): module này tồn tại và có unit test validate TRƯỚC khi
bất kỳ logic hao hụt nào của `ag_waste` được viết.

ADR-002 (tất định): contract chỉ mô tả **hình dạng** dữ liệu. Mọi con số (lượng lý
thuyết, lượng thực tế, độ lệch, tỷ lệ phần trăm, xếp hạng nguyên nhân) do tầng toán
thuần ở `ca_agents.ag_waste` sinh ra. LLM không được tự sinh số.

ADR-008 (người quyết định): đây là kênh **đọc và gợi ý**. Không model nào trong
module này mang nghĩa "thay đổi đã được áp dụng lên hệ thống thật".

Quy ước `None` khác `0.0`
-------------------------
Trường số của một dòng hao hụt là `float | None`:

- `None` — **chưa có dữ liệu** cho vế đó. Ví dụ quán chưa gõ phiếu kiểm kê, hoặc
  chưa có đơn quầy nào để đối chiếu công thức.
- `0.0` — **có dữ liệu và số bằng không**. Ví dụ đã kiểm kê và ghi đúng bằng dự kiến.

Trộn hai thứ này là bịa số. Vì vậy enum `LossLevel` có nhánh `thieu_du_lieu` riêng,
và `LossLine` bắt buộc nêu `thieu_ve` để UI nói được đang thiếu vế nào.
"""

from __future__ import annotations

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover - Python < 3.11
    from enum import Enum

    class StrEnum(str, Enum):
        pass


from pydantic import BaseModel, Field

# ── Enum nghiệp vụ ────────────────────────────────────────────────────────────


class LossLevel(StrEnum):
    """Mức độ hao hụt của một nguyên liệu, so với ngưỡng đang áp dụng.

    `THIEU_DU_LIEU` là nhánh **bắt buộc**: thiếu một vế thì không được suy ra
    "đạt" (không có bằng chứng không phải là bằng chứng đạt — fail-closed).
    """

    DAT = "dat"
    CANH_BAO = "canh_bao"
    NGHIEM_TRONG = "nghiem_trong"
    THIEU_DU_LIEU = "thieu_du_lieu"


class LossBasis(StrEnum):
    """Dòng hao hụt này tính từ nguồn nào.

    Nói rõ nguồn để người đọc biết độ tin của con số; đơn quầy là số **ước lượng**
    (`nguon="uoc_luong_tu_quay"`), không phải số bán thật từ Grab/ShopeeFood.
    """

    KE_HOACH_KIEM_KE = "ke_hoach_kiem_ke"
    DON_QUAY_THUC_TE = "don_quay_thuc_te"
    HON_HOP = "hon_hop"


class LossCauseSource(StrEnum):
    """Nguồn của một hạng mục nguyên nhân hao hụt."""

    GHI_CHU_CA = "ghi_chu_ca"
    NGUYEN_NHAN_GHI = "nguyen_nhan_ghi"
    HON_HOP = "hon_hop"


# ── Model ─────────────────────────────────────────────────────────────────────


class LossLine(BaseModel):
    """Một dòng hao hụt cho **một mặt hàng**, so lý thuyết với thực tế.

    `ly_thuyet` = Σ(BOM nguyên liệu × số phần đã bán); `thuc_te` = lượng đã dùng
    suy ra từ phiếu kiểm kê.

    `lech` được phép **âm**: lệch âm nghĩa là thực tế dùng **ít hơn** lý thuyết —
    dấu hiệu đếm dư hoặc công thức chưa khớp, không phải lỗi dữ liệu.
    """

    mat_hang: str = Field(min_length=1, max_length=64, description="Mã mặt hàng, vd sua_tuoi")
    ten: str = Field(default="", max_length=120, description="Tên người đọc, vd Sữa tươi")
    don_vi: str = Field(default="đơn vị", max_length=16, description="Đơn vị tính, vd ml, g, hộp")

    ly_thuyet: float | None = Field(
        default=None, ge=0.0, description="Lượng theo công thức; None = chưa có đơn để đối chiếu"
    )
    thuc_te: float | None = Field(
        default=None, ge=0.0, description="Lượng theo kiểm kê; None = chưa gõ phiếu kiểm kê"
    )
    lech: float | None = Field(
        default=None, description="thuc_te - ly_thuyet; âm = dùng ít hơn lý thuyết"
    )
    ty_le_phan_tram: float | None = Field(
        default=None, description="lech / ly_thuyet * 100; None khi không có vế lý thuyết"
    )

    muc_do: LossLevel = LossLevel.THIEU_DU_LIEU
    nguong_phan_tram: float = Field(
        default=5.0, ge=0.0, description="Ngưỡng đang áp dụng cho mặt hàng này"
    )
    co_so: LossBasis = LossBasis.KE_HOACH_KIEM_KE

    thieu_ve: list[str] = Field(
        default_factory=list,
        description="Vế còn thiếu: 'ly_thuyet' | 'thuc_te'. Rỗng khi đủ hai vế.",
    )
    ghi_chu: str = Field(default="", max_length=300)


class LossCauseRank(BaseModel):
    """Một nguyên nhân hao hụt đã xếp hạng, kèm mặt hàng nó hay đi cùng."""

    nguyen_nhan: str = Field(min_length=1, max_length=64, description="Mã nguyên nhân, vd het_han")
    ten: str = Field(default="", max_length=120, description="Tên người đọc, vd Hết hạn dùng")
    so_lan: int = Field(ge=0, description="Số lần nguyên nhân này được ghi")
    mat_hang_lien_quan: list[str] = Field(
        default_factory=list, description="Mã mặt hàng hay đi cùng nguyên nhân này"
    )
    ty_le_tong: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Phần trăm trên tổng số lần ghi hao hụt có nêu nguyên nhân",
    )
    nguon: LossCauseSource = LossCauseSource.NGUYEN_NHAN_GHI


class LossSummary(BaseModel):
    """Toàn cảnh hao hụt của quán trong kỳ đang xét.

    `co_du_lieu_mau` giữ đúng quy ước có sẵn của repo: `True` khi ít nhất một bản
    ghi là dữ liệu mẫu (`nguon="mo_phong_fixture"` hoặc id `fx_*`), để UI gắn nhãn
    và người đọc không nhầm số mẫu với số thật của quán.
    """

    ky: str = Field(default="hom_nay", max_length=32, description="Kỳ đang xét: hom_nay | tuan | thang")

    tong_dong: int = Field(default=0, ge=0)
    so_nghiem_trong: int = Field(default=0, ge=0)
    so_canh_bao: int = Field(default=0, ge=0)
    so_thieu_du_lieu: int = Field(default=0, ge=0)

    ty_le_trung_binh: float | None = Field(
        default=None,
        description="Trung bình tỷ lệ hao hụt các dòng đủ hai vế; None khi chưa dòng nào đủ",
    )

    dong: list[LossLine] = Field(default_factory=list)
    nguyen_nhan_hang_dau: list[LossCauseRank] = Field(default_factory=list)

    nguon: str = Field(default="quan", max_length=32)
    co_du_lieu_mau: bool = False
    ghi: str = Field(default="", max_length=300)


class LossThreshold(BaseModel):
    """Ngưỡng hao hụt đang áp dụng — đọc từ `config/nguong-hao-hut.yaml`.

    Ngưỡng **không** hard-code trong mã nghiệp vụ: đổi quy định của quán thì sửa
    file cấu hình, không sửa mã (cùng nguyên tắc với `config/tham-so-lao-dong.yaml`).
    """

    mac_dinh_phan_tram: float = Field(default=5.0, ge=0.0)
    nghiem_trong_phan_tram: float = Field(default=15.0, ge=0.0)
    theo_mat_hang: dict[str, float] = Field(
        default_factory=dict, description="mat_hang -> ngưỡng riêng, thắng ngưỡng mặc định"
    )
    phien_ban: str = Field(default="", max_length=32)
    ngay_kiem: str = Field(default="", max_length=32)

    def nguong_cho(self, mat_hang: str) -> float:
        """Ngưỡng áp cho một mặt hàng; mặt hàng lạ dùng ngưỡng mặc định."""
        return self.theo_mat_hang.get(mat_hang, self.mac_dinh_phan_tram)
