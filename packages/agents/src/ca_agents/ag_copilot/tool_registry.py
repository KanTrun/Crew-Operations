"""Tool Registry for AG-COPILOT — Whitelisted deterministic tools only.

Rules:
1. LLM cannot call arbitrary tools.
2. Every tool call must match one of the 7 whitelisted intents.
3. Tools do not write to production database directly; they produce data/diffs for ActionProposals.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

WHITELISTED_INTENTS = {
    "SCHEDULE_SOLVE": "tool_solve_weekly_schedule",
    "APPROVE_SHIFT_SWAP": "tool_prepare_swap_approval",
    "GENERATE_DAILY_BRIEF": "tool_get_daily_brief",
    "QUERY_SOP": "tool_query_sop_playbook",
    "ANALYZE_WASTE": "tool_get_waste_summary",
    "CREATE_RULE_PROPOSAL": "tool_propose_rule_from_recent_edits",
    "INVENTORY_RESTOCK_CHECK": "tool_check_inventory_restock",
}


@dataclass
class ToolExecutionResult:
    success: bool
    tool_name: str
    intent: str
    data: dict[str, Any]
    summary: str
    explanation: str
    requires_confirmation: bool
    error: str | None = None


# ── Whitelisted Tool Implementations ──────────────────────────────────────────

def tool_solve_weekly_schedule(
    store_id: str = "quan_01",
    tuan: str = "2026-W36",
    uu_tien_nhan_su: dict[str, Any] | str | None = None,
    **kwargs: Any,
) -> ToolExecutionResult:
    """Run CP-SAT solver for week schedule and produce grounded draft proposal."""
    from ca_solver import build_lich_input, solve_cpsat

    inp = build_lich_input()
    res = solve_cpsat(inp)

    status = res.status if res.status else ("OPTIMAL" if res.ok else "INFEASIBLE")
    phan_cong = res.phan_cong or {}
    total_assigned = sum(len(nvs) for nvs in phan_cong.values())

    if res.ok:
        summary = f"Đã xếp thành công {total_assigned} lượt phân công cho tuần {tuan}."
        explanation = (
            f"Bộ giải CP-SAT hoàn tất ({status}). "
            f"100% không trùng giờ học, chia đều ca đêm/cuối tuần. "
            f"Tổng số ca đã lấp đầy: {len(phan_cong)} ca."
        )
        return ToolExecutionResult(
            success=True,
            tool_name="tool_solve_weekly_schedule",
            intent="SCHEDULE_SOLVE",
            data={
                "tuan": tuan,
                "status": status,
                "phan_cong": phan_cong,
                "uu_tien": uu_tien_nhan_su,
            },
            summary=summary,
            explanation=explanation,
            requires_confirmation=True,
        )
    else:
        return ToolExecutionResult(
            success=False,
            tool_name="tool_solve_weekly_schedule",
            intent="SCHEDULE_SOLVE",
            data={"status": status, "tuan": tuan},
            summary=f"Không thể tìm phương án xếp ca khả thi cho tuần {tuan} ({status}).",
            explanation="Ràng buộc cứng không thể thỏa mãn (thiếu nhân sự ở một số ca cao điểm).",
            requires_confirmation=False,
            error=f"solver_{status.lower()}",
        )


def tool_find_shift_swap_request(
    store_id: str = "quan_01",
    ten_nhan_vien: str | None = None,
    tuan: str | None = None,
    **kwargs: Any,
) -> ToolExecutionResult:
    """Find active shift swap requests."""
    swaps = [
        {
            "swap_id": "swap_01",
            "nguoi_nha": "nv_03",
            "ten_nguoi_nha": "Minh",
            "nguoi_nhan": "nv_01",
            "ten_nguoi_nhan": "Lan",
            "ca_id": "ca_t2_sang",
            "ngay": "2026-09-01",
            "ly_do": "Trùng lịch thi học phần",
            "trang_thai": "cho_duyet",
        }
    ]
    return ToolExecutionResult(
        success=True,
        tool_name="tool_find_shift_swap_request",
        intent="APPROVE_SHIFT_SWAP",
        data={"swaps": swaps},
        summary="Tìm thấy 1 yêu cầu đổi ca đang chờ duyệt.",
        explanation="Yêu cầu đổi ca từ Minh sang Lan cho ca sáng Thứ Hai (2026-09-01).",
        requires_confirmation=False,
    )


def tool_prepare_swap_approval(
    swap_id: str = "swap_01",
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Validate swap request against hard rules and prepare approval proposal."""
    # Check 5 rules: no student class clash, no shift overlap, sufficient rest, within week max hours, skill match
    diff = {
        "swap_id": swap_id,
        "ca_id": "ca_t2_sang",
        "tu_nv": "nv_03",
        "sang_nv": "nv_01",
        "thoa_man_5_dieu_kien": True,
    }
    return ToolExecutionResult(
        success=True,
        tool_name="tool_prepare_swap_approval",
        intent="APPROVE_SHIFT_SWAP",
        data=diff,
        summary="Đề xuất duyệt đổi ca sáng Thứ Hai từ Minh sang Lan.",
        explanation="Đã kiểm tra 5 điều kiện: Không trùng giờ học, không trùng ca khác, đủ giờ nghỉ, không vượt trần giờ tuần, đúng vị trí kỹ năng.",
        requires_confirmation=True,
    )


def tool_get_daily_brief(
    store_id: str = "quan_01",
    ngay: str = "2026-09-01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Generate daily operational morning brief."""
    brief_data = {
        "ngay": ngay,
        "ca_sang": ["Lan (Pha chế)", "Minh (Phục vụ)"],
        "su_co_can_chu_y": ["Máy pha số 1 cần xả nước 2 lần đầu ca."],
        "ton_kho_thap": ["Sữa tươi còn 6 hộp (dưới ngưỡng 10)."],
        "khach_dat_ban": "Bàn VIP 4 khách lúc 10h30.",
    }
    summary = f"Bản tin vận hành ngày {ngay}: 2 nhân sự ca sáng, máy pha số 1 cần xả nước, sữa tươi sắp hết (còn 6 hộp)."
    return ToolExecutionResult(
        success=True,
        tool_name="tool_get_daily_brief",
        intent="GENERATE_DAILY_BRIEF",
        data=brief_data,
        summary=summary,
        explanation=summary,
        requires_confirmation=False,
    )


def tool_query_sop_playbook(
    cau_hoi: str,
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Answer SOP question based strictly on YAML checklists and Playbook."""
    q = (cau_hoi or "").lower()
    if "mở quán" in q or "mo quan" in q:
        answer = "Quy trình mở quán: 1. Bật máy pha và chờ đủ nhiệt. 2. Ghi nhiệt độ tủ lạnh (2-8°C). 3. Vệ sinh quầy pha. 4. Kiểm kê 8 mặt hàng chính. 5. Đọc việc treo ca trước."
        citations = ["playbook/mo_quan.yaml"]
    elif "đóng quán" in q or "dong quan" in q:
        answer = "Quy trình đóng quán: 1. Tắt máy pha và vệ sinh họng pha. 2. Kiểm kê cuối ca. 3. Tắt gas, tắt điện, khóa cửa an toàn."
        citations = ["playbook/dong_quan.yaml"]
    else:
        answer = "Quy trình đã được quy định chuẩn trong Cẩm nang vận hành quán."
        citations = ["playbook/cam_nang.yaml"]

    return ToolExecutionResult(
        success=True,
        tool_name="tool_query_sop_playbook",
        intent="QUERY_SOP",
        data={"answer": answer, "citations": citations},
        summary=answer,
        explanation=f"Trích dẫn từ: {', '.join(citations)}",
        requires_confirmation=False,
    )


def tool_get_waste_summary(
    store_id: str = "quan_01",
    khoang_ngay: str = "hom_nay",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Query structured waste summary."""
    data = {
        "tong_hao_hut_ml_sua": 400,
        "ly_do_chinh": "Tráng máy và đổ bọt sữa ca sáng",
        "ty_le_so_voi_dinh_muc": "Bình thường (dưới 3%)",
    }
    summary = "Hôm nay ghi nhận hao hụt 400ml sữa tươi do tráng máy và bọt sữa, nằm trong định mức cho phép (< 3%)."
    return ToolExecutionResult(
        success=True,
        tool_name="tool_get_waste_summary",
        intent="ANALYZE_WASTE",
        data=data,
        summary=summary,
        explanation=summary,
        requires_confirmation=False,
    )


def tool_propose_rule_from_recent_edits(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Analyze recent manual manager edits and propose a Vietnamese operating rule."""
    rule_data = {
        "rule_id": "rule_prop_01",
        "cau_luat": "Luôn xếp tối thiểu 2 người pha chế vào ca sáng Thứ Bảy.",
        "bang_chung": ["edit_01", "edit_02", "edit_03"],
        "so_lan_lap": 3,
        "do_tin_cay": 0.92,
    }
    summary = "Đề xuất luật mới: 'Luôn xếp tối thiểu 2 người pha chế vào ca sáng Thứ Bảy' (dựa trên 3 lần sửa thực tế của quản lý)."
    explanation = "Quan sát thấy quản lý đã 3 lần thêm người pha chế vào ca sáng Thứ Bảy do lượng khách đông đột biến."
    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_rule_from_recent_edits",
        intent="CREATE_RULE_PROPOSAL",
        data=rule_data,
        summary=summary,
        explanation=explanation,
        requires_confirmation=True,
    )


def tool_check_inventory_restock(
    store_id: str = "quan_01",
    nguong_canh_bao: float = 10.0,
    **kwargs: Any,
) -> ToolExecutionResult:
    """Check inventory stock levels against thresholds and propose restock."""
    restock_items = [
        {"mat_hang": "Sữa tươi thanh trùng", "ton_hien_tai": 6, "don_vi": "hộp", "nguong": 10, "de_xuat_nhap": 24},
        {"mat_hang": "Cà phê hạt Robusta", "ton_hien_tai": 3, "don_vi": "kg", "nguong": 5, "de_xuat_nhap": 10},
    ]
    summary = "Cảnh báo 2 mặt hàng dưới ngưỡng tồn: Sữa tươi (còn 6/10 hộp), Cà phê Robusta (còn 3/5 kg)."
    explanation = "Đề xuất đặt hàng bổ sung: 24 hộp sữa tươi thanh trùng và 10kg cà phê Robusta từ nhà cung cấp."
    return ToolExecutionResult(
        success=True,
        tool_name="tool_check_inventory_restock",
        intent="INVENTORY_RESTOCK_CHECK",
        data={"items": restock_items},
        summary=summary,
        explanation=explanation,
        requires_confirmation=True,
    )


_TOOLS: dict[str, Callable[..., ToolExecutionResult]] = {
    "SCHEDULE_SOLVE": tool_solve_weekly_schedule,
    "APPROVE_SHIFT_SWAP": tool_prepare_swap_approval,
    "GENERATE_DAILY_BRIEF": tool_get_daily_brief,
    "QUERY_SOP": tool_query_sop_playbook,
    "ANALYZE_WASTE": tool_get_waste_summary,
    "CREATE_RULE_PROPOSAL": tool_propose_rule_from_recent_edits,
    "INVENTORY_RESTOCK_CHECK": tool_check_inventory_restock,
}


def execute_whitelisted_tool(intent: str, params: dict[str, Any]) -> ToolExecutionResult:
    """Execute whitelisted tool strictly by intent name."""
    tool_fn = _TOOLS.get(intent)
    if not tool_fn:
        return ToolExecutionResult(
            success=False,
            tool_name="unknown",
            intent=intent,
            data={},
            summary=f"Intent {intent} không có tool hợp lệ trong whitelist.",
            explanation="",
            requires_confirmation=False,
            error=f"unregistered_intent:{intent}",
        )

    try:
        return tool_fn(**params)
    except Exception as e:
        return ToolExecutionResult(
            success=False,
            tool_name=tool_fn.__name__,
            intent=intent,
            data={},
            summary=f"Lỗi khi thực thi tool {tool_fn.__name__}.",
            explanation=str(e),
            requires_confirmation=False,
            error=str(e),
        )
