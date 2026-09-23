"""AG-WASTE — gom cụm ghi chú hao hụt và tính hao hụt theo nguyên liệu.

Hai năng lực, cùng một phạm vi:

- `extract.cluster` — gom cụm ghi chú theo thứ trong tuần (năng lực gốc).
- `loss.*` — so lượng lý thuyết (công thức × phần đã bán) với lượng thực tế
  (phiếu kiểm kê), ra mức độ và xếp hạng nguyên nhân (plan 260923-1736).

Cả hai đều là hàm thuần, không I/O, không LLM. Tầng API đọc dữ liệu và truyền vào.
"""

from ca_agents.ag_waste.extract import WasteHint, cluster
from ca_agents.ag_waste.loss import (
    BI_DANH,
    chuan_hoa_mat_hang,
    doc_ban_theo_mon,
    doc_bom_theo_mon,
    don_vi_mac_dinh,
    gom_theo_mat_hang,
    so_hao_hut,
    tinh_ly_thuyet,
    tinh_tu_kiem_ke,
    tong_hop,
    xep_hang_nguyen_nhan,
)

__all__ = [
    # Năng lực gốc
    "WasteHint",
    "cluster",
    # Động cơ hao hụt (plan 260923-1736)
    "BI_DANH",
    "chuan_hoa_mat_hang",
    "doc_ban_theo_mon",
    "doc_bom_theo_mon",
    "don_vi_mac_dinh",
    "gom_theo_mat_hang",
    "so_hao_hut",
    "tinh_ly_thuyet",
    "tinh_tu_kiem_ke",
    "tong_hop",
    "xep_hang_nguyen_nhan",
]
