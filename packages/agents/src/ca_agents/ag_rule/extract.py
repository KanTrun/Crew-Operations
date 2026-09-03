"""AG-RULE — one Vietnamese law sentence from a mined pattern.

Agent thuần: chỉ trích xuất và đề xuất. Không chạm DB, không gọi cổng VF,
không gọi package điều phối. Cổng VF-RULE và bước suy luật tất định là việc
của lớp điều phối; agent nhận gợi ý tất định qua tham số ``goi_y``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ca_agents.llm import agent_mode, complete, parse_json_object

# Hợp đồng đầu ra của agent — trùng danh sách khóa nêu trong prompt bên dưới.
# Cổng VF-RULE ở lớp điều phối vẫn là nơi phán quyết cuối cùng; bộ lọc này chỉ
# để agent không đẩy khóa lạ do LLM bịa ra xuống dưới.
_TRUONG_DIEU_KIEN = frozenset(
    {
        "thu",
        "khung",
        "vi_tri",
        "so_nguoi",
        "nguong",
        "ma_buoc",
        "thang_kinh_nghiem",
    }
)

_RULE_SYSTEM = """Bạn là AG-RULE của NHỊP QUÁN.
Từ các lần sửa lịch/ca của quán, đề xuất ĐÚNG MỘT câu luật tiếng Việt ngắn gọn.
Trả JSON: {"cau": "...", "loai": "nhu_cau_ca|nguong_ton|buoc_phieu|ghep_ky_nang|hao_hut", "dieu_kien": {...}, "do_tin_cay": 0.0-1.0}
dieu_kien chỉ dùng các khóa: thu, khung, vi_tri, so_nguoi, nguong, ma_buoc, thang_kinh_nghiem.
CẤM luật về thái độ hay chỉ trích một người cụ thể (nv_XX, tên riêng).
Chỉ dựa trên bằng chứng được cung cấp."""


@dataclass
class RuleDraft:
    cau: str
    loai: str
    dieu_kien: dict[str, Any]
    bang_chung: list[str]
    do_tin_cay: float


def _loc_dieu_kien(raw: Any) -> dict[str, Any]:
    """Chỉ giữ các khóa nằm trong hợp đồng. LLM hay bịa khóa mới."""
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if k in _TRUONG_DIEU_KIEN}


def _from_goi_y(mau: dict[str, Any], goi_y: dict[str, Any]) -> RuleDraft | None:
    """Dựng bản nháp từ gợi ý tất định do lớp điều phối suy ra."""
    cau = str(goi_y.get("cau") or "").strip()
    if not cau:
        return None
    return RuleDraft(
        cau=cau,
        loai=str(goi_y.get("loai") or mau.get("loai_luat") or "nhu_cau_ca"),
        dieu_kien=_loc_dieu_kien(goi_y.get("dieu_kien")),
        bang_chung=list(goi_y.get("bang_chung") or mau.get("bang_chung") or [])[:4],
        do_tin_cay=0.75,
    )


def _propose_live(mau: dict[str, Any], sua_rows: list[dict[str, Any]]) -> RuleDraft | None:
    user = json.dumps(
        {
            "mau": mau,
            "lan_sua": sua_rows[:10],
            "yeu_cau": "Một luật duy nhất, tiếng Việt, có dieu_kien máy đọc được.",
        },
        ensure_ascii=False,
    )
    res = complete(system=_RULE_SYSTEM, user=user, task="ag_rule", json_mode=True)
    if not res.ok:
        return None
    data = parse_json_object(res.text)
    if not data:
        return None
    cau = str(data.get("cau") or "").strip()
    dieu_kien = _loc_dieu_kien(data.get("dieu_kien"))
    bang_chung = list(mau.get("bang_chung") or [])[:4]
    # Fail closed: không có câu, không có điều kiện máy đọc được, hoặc thiếu
    # bằng chứng thì coi như LLM không trả lời được — để lớp điều phối dùng
    # gợi ý tất định thay vì đẩy rác xuống cổng VF.
    if not cau or not dieu_kien or len(bang_chung) < 3:
        return None
    try:
        do_tin_cay = float(data.get("do_tin_cay") or 0.7)
    except (TypeError, ValueError):
        do_tin_cay = 0.7
    return RuleDraft(
        cau=cau,
        loai=str(data.get("loai") or mau.get("loai_luat") or "nhu_cau_ca"),
        dieu_kien=dieu_kien,
        bang_chung=bang_chung,
        do_tin_cay=max(0.0, min(1.0, do_tin_cay)),
    )


def propose(
    mau: dict[str, Any],
    *,
    sua_mau: list[dict[str, Any]] | None = None,
    goi_y: dict[str, Any] | None = None,
    mode: str | None = None,
) -> RuleDraft | None:
    """Đề xuất một luật từ mẫu đã gom.

    ``goi_y`` là bản nháp tất định do lớp điều phối suy ra từ lần sửa thật
    (``ca_playbook.derive``). Agent không tự suy — nó chỉ diễn đạt lại bằng LLM
    khi ở chế độ live, và trả về gợi ý tất định khi LLM không dùng được.
    Không có tín hiệu nào thì trả ``None`` — tuyệt đối không bịa luật.
    """
    if int(mau.get("n") or 0) < 3:
        return None

    resolved = (mode or agent_mode() or "replay").strip().lower()
    rows = sua_mau or []

    if resolved == "live" and rows:
        live = _propose_live(mau, rows)
        if live:
            return live

    if goi_y:
        return _from_goi_y(mau, goi_y)

    return None
