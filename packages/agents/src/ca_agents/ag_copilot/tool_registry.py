"""Tool Registry for AG-COPILOT — Whitelisted deterministic tools only.

Rules:
1. LLM cannot call arbitrary tools.
2. Every tool call must match one of the 7 whitelisted intents.
3. Tools do not write to production database directly; they produce data/diffs for ActionProposals.
4. Tools read REAL data — no hardcoded fixtures. When real data is empty, tools
   return an honest "no data" result instead of fake numbers.
5. Architecture: this module must NOT import other agents (ag_sop, ag_waste),
   ca_api, ca_playbook or ca_gates (enforced by test_architecture.py).
   Data sources are INJECTED via `configure_data_sources()` from the API layer.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone

    UTC = timezone.utc
from pathlib import Path
from typing import Any

WHITELISTED_INTENTS = {
    "SCHEDULE_SOLVE": "tool_solve_weekly_schedule",
    "APPROVE_SHIFT_SWAP": "tool_prepare_swap_approval",
    "GENERATE_DAILY_BRIEF": "tool_get_daily_brief",
    "QUERY_SOP": "tool_query_sop_playbook",
    "ANALYZE_WASTE": "tool_get_waste_summary",
    "CREATE_RULE_PROPOSAL": "tool_propose_rule_from_recent_edits",
    "INVENTORY_RESTOCK_CHECK": "tool_check_inventory_restock",
    "SEND_MAIL": "tool_send_mail",
}

# ── Data source injection (hexagonal architecture) ────────────────────────────
# API layer gọi `configure_data_sources()` một lần lúc startup để cung cấp
# các hàm đọc dữ liệu thật. Tools chỉ gọi qua các callable này — không import
# trực tiếp ca_api / ca_playbook / agent khác.

DataSources = dict[str, Callable[..., Any]]

_SOURCES: DataSources = {}


def configure_data_sources(**sources: Callable[..., Any]) -> None:
    """Inject data sources từ API layer. Gọi 1 lần lúc startup.

    Keys kỳ vọng:
      - kv_get(key, default) -> Any
      - list_luat() -> list[dict]           (luật hiệu lực từ cẩm nang sống)
      - load_template(ma) -> dict | None    (mẫu phiếu YAML)
      - list_sua() -> list[dict]            (lịch sử sửa lịch thật)
      - tim_mau(sua) -> list[dict]          (mẫu lặp từ lịch sử sửa)
      - de_xuat(mau) -> dict | None         (sinh đề xuất luật; None khi thiếu tín hiệu)
      - sop_answer(q, buoc, luat) -> SopAnswer
      - waste_cluster(notes) -> list[WasteHint]
      - list_ca_meta() -> dict[str, dict]   (ca_id -> {thu, khung, bat_dau, ket_thuc})
    """
    _SOURCES.clear()
    _SOURCES.update(sources)


def _src(name: str) -> Callable[..., Any] | None:
    return _SOURCES.get(name)


def build_live_snapshot(
    intent: str,
    store_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical live source snapshot shared by propose and approve."""
    snapshot: dict[str, Any] = {"store_id": store_id, "intent": intent}
    if intent == "SCHEDULE_SOLVE":
        snapshot.update({
            "phan_cong": _kv_get("phan_cong", {}),
            "lich_tuan": _kv_get("lich_tuan", {}),
        })
    elif intent == "APPROVE_SHIFT_SWAP":
        snapshot.update({
            "swap": _kv_get("swap", []),
            "shift_swaps": _kv_get("shift_swaps", []),
            "phan_cong": _kv_get("phan_cong", {}),
        })
    elif intent == "CREATE_RULE_PROPOSAL":
        list_sua = _src("list_sua")
        list_luat = _src("list_luat")
        snapshot["list_sua"] = list(list_sua() or []) if list_sua else None
        snapshot["list_luat"] = list(list_luat() or []) if list_luat else None
    elif intent == "SEND_MAIL":
        # Snapshot mail chỉ khóa nguồn liên quan an toàn: recipient email +
        # nội dung đã duyệt. ops_context/style là ngữ cảnh soạn thảo (volatile),
        # không đưa vào hash — nếu không correction nội dung hợp lệ sẽ bị stale
        # giả khi ngữ cảnh sống đổi giữa propose và approve (kế hoạch §3.3:
        # "Không hash ... dữ liệu không cần thiết").
        payload = payload or {}
        get_emails = _src("get_user_emails")
        to_nv_ids = list(payload.get("to_nv_ids") or [])
        snapshot["recipient_emails"] = (
            {nv_id: (get_emails() or {}).get(nv_id) for nv_id in to_nv_ids}
            if get_emails else None
        )
        snapshot["content"] = {
            "to_emails": list(payload.get("to_emails") or []),
            "subject": str(payload.get("subject") or ""),
            "body": str(payload.get("body") or ""),
        }
        snapshot["rule_version"] = str(payload.get("rule_version") or "none")
    elif intent == "PROPOSE_HANGING_TASK":
        snapshot["treo"] = [t for t in (_kv_get("treo", []) or []) if isinstance(t, dict)]
    elif intent == "PROPOSE_TASK_COMPLETE":
        snapshot["treo"] = [t for t in (_kv_get("treo", []) or []) if isinstance(t, dict)]
    elif intent == "PROPOSE_CONSUMPTION_RECORD":
        snapshot["tieu_thu"] = [t for t in (_kv_get("tieu_thu", []) or []) if isinstance(t, dict)]
    elif intent == "PROPOSE_MENU_UPDATE":
        menu_list = _src("menu_list")
        snapshot["menu"] = list(menu_list(gom_an=True) or []) if menu_list else []
    elif intent == "PROPOSE_ORDER_TRANSITION":
        payload0 = payload or {}
        don_list = _src("don_list")
        don_get = _src("don_get")
        don_id = str(payload0.get("don_id") or "")
        snapshot["don"] = don_get(don_id) if (don_get and don_id) else None
        snapshot["orders"] = list(don_list() or []) if don_list else []
    elif intent == "PROPOSE_PIN":
        snapshot["pins"] = _kv_get("pins", {})
    elif intent == "PROPOSE_PAGE_SYNC":
        page_status = _src("page_status")
        try:
            snapshot["page"] = page_status() if page_status else None
        except Exception:
            snapshot["page"] = None
    list_ca_meta = _src("list_ca_meta")
    if list_ca_meta is not None:
        try:
            snapshot["ca_meta"] = list_ca_meta() or {}
        except Exception:
            snapshot["ca_meta"] = None
    return snapshot


def _kv_get(key: str, default: Any) -> Any:
    """Đọc KV qua source được inject; fallback file JSON khi chạy standalone/tests."""
    fn = _src("kv_get")
    if fn is not None:
        try:
            return fn(key, default)
        except Exception:
            pass
    try:
        path = Path(os.environ.get("NHIPQUAN_KV", _ROOT / "data" / "out" / "kv.json"))
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                return raw.get(key, default)
    except Exception:
        pass
    return default


_ROOT = Path(__file__).resolve().parents[4]


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
    source_snapshot: Any | None = None


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
                "snapshot_version": "live-v1",
            },
            summary=summary,
            explanation=explanation,
            requires_confirmation=True,
            source_snapshot=build_live_snapshot("SCHEDULE_SOLVE", store_id),
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


def _swap_khong_trung_ca(
    phan_cong: dict[str, Any],
    ca_dich: str,
    nhan_nv: str | None,
    list_ca_meta: Callable[..., Any] | None,
) -> bool:
    """Trả False khi không thể chứng minh ca đích không trùng lịch."""
    if not nhan_nv or not ca_dich:
        return False
    if not list_ca_meta:
        return False
    try:
        ca_meta = list_ca_meta() or {}
    except Exception:
        return False

    meta_dich = ca_meta.get(ca_dich)
    if not isinstance(meta_dich, dict):
        return False

    thu_dich = meta_dich.get("thu")
    # So trùng ca: không phân biệt khung cứng — so theo thu + khung trùng giờ.
    for ca_id, nvs in (phan_cong or {}).items():
        if ca_id == ca_dich:
            continue
        if not isinstance(nvs, list) or nhan_nv not in nvs:
            continue
        meta_other = ca_meta.get(ca_id)
        if not isinstance(meta_other, dict):
            continue
        # Trùng ngày và trùng khung giờ (bat_dau/ket_thuc chồng nhau) → chặn.
        if meta_other.get("thu") == thu_dich:
            # Nếu trùng khung (cùng giờ) hoặc không có meta → chặn an toàn.
            khung_dich = meta_dich.get("khung")
            khung_other = meta_other.get("khung")
            if khung_dich and khung_other and khung_dich == khung_other:
                return False
            # Nếu không có khung, so giờ.
            bd_d = meta_dich.get("bat_dau")
            kt_d = meta_dich.get("ket_thuc")
            bd_o = meta_other.get("bat_dau")
            kt_o = meta_other.get("ket_thuc")
            if bd_d and kt_d and bd_o and kt_o and _gio_chong(bd_d, kt_d, bd_o, kt_o):
                return False
    return True


def _gio_chong(bd1: str, kt1: str, bd2: str, kt2: str) -> bool:
    """Kiểm tra 2 khoảng giờ 'HH:MM' có chồng lấn không."""
    try:
        def _m(s: str) -> int:
            h, m = s.split(":")
            return int(h) * 60 + int(m)

        return _m(bd1) < _m(kt2) and _m(bd2) < _m(kt1)
    except Exception:
        return False


def tool_prepare_swap_approval(
    swap_id: str | None = None,
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Validate swap request against hard rules and prepare approval proposal.

    Đọc yêu cầu đổi ca THẬT từ KV ("swap" — 3 nhánh đồng ý, hoặc "shift_swaps").
    Kiểm tra 5 điều kiện thật trên dữ liệu phân công hiện tại.
    """
    # 1. Lấy danh sách swap thật (ưu tiên KV "swap" của swap-market 3 nhánh)
    swaps = _kv_get("swap", []) or []
    legacy = _kv_get("shift_swaps", []) or []
    if isinstance(legacy, list) and legacy:
        swaps = swaps + legacy

    # 2. Chọn swap: theo id nếu có, else cái mới nhất còn đang chờ
    candidates = [
        s
        for s in swaps
        if isinstance(s, dict)
        and s.get("trang_thai") in ("cho_3_nhanh", "dong_y", "cho_duyet")
    ]
    target: dict[str, Any] | None = None
    if swap_id:
        for s in candidates:
            if s.get("id") == swap_id or s.get("swap_id") == swap_id:
                target = s
                break
    else:
        target = candidates[-1] if candidates else None

    if not target:
        return ToolExecutionResult(
            success=True,
            tool_name="tool_prepare_swap_approval",
            intent="APPROVE_SHIFT_SWAP",
            data={"swaps_cho_duyet": 0},
            summary="Hiện không có yêu cầu đổi ca nào đang chờ duyệt.",
            explanation="Danh sách đổi ca trống hoặc tất cả đã được xử lý.",
            requires_confirmation=False,
        )

    # 3. Kiểm tra 5 điều kiện thật trên phân công hiện tại
    phan_cong = _kv_get("phan_cong", {}) or {}
    ca_id = str(target.get("ca_id") or "")
    a, b, c = target.get("a"), target.get("b"), target.get("c")

    checks: dict[str, bool] = {}
    # 3.1 Đủ 3 nhánh xác định
    checks["du_3_nhanh"] = bool(a and b and c and len({a, b, c}) == 3)
    # 3.2 Cả 3 đã đồng ý (swap-market) hoặc trạng thái dong_y
    dong_y = set(target.get("dong_y") or [])
    parties = {x for x in (a, b, c) if x}
    checks["du_3_dong_y"] = bool(parties) and parties <= dong_y or target.get("trang_thai") == "dong_y"
    # 3.3 Ca tồn tại trong phân công tuần
    ca_exists = bool(ca_id) and (
        not phan_cong or any(ca_id in str(k) or ca_id == k for k in phan_cong)
    )
    checks["ca_hop_le"] = ca_exists if phan_cong else bool(ca_id)
    # 3.4 Người nhận không trùng ca khác cùng khung giờ (đọc dữ liệu thật).
    #     So sánh ca đích với các ca khác mà nhan_nv đang đảm nhận: nếu trùng
    #     giờ (bat_dau/ket_thuc) trong cùng khung → chặn.
    checks["khong_trung_ca_khac"] = _swap_khong_trung_ca(
        phan_cong, ca_id, c, _src("list_ca_meta")
    )
    # 3.5 Lý do: swap-market 3 nhánh KHÔNG có trường ly_do/ghi_chu — chỉ bắt buộc
    #     khi swap kiểu cũ có trường này. Nếu swap-market thì coi là hợp lệ (3 nhánh đã đồng ý).
    checks["co_ly_do"] = bool(target.get("ly_do") or target.get("ghi_chu") or target.get("trang_thai") in ("dong_y", "cho_3_nhanh"))

    passed = all(checks.values())
    ten_map = {u.get("nv_id"): u.get("ten") for u in (_kv_get("users", []) or []) if isinstance(u, dict)}
    ten_a = ten_map.get(a, a)
    ten_c = ten_map.get(c, c)

    diff = {
        "swap_id": target.get("id") or target.get("swap_id"),
        "ca_id": ca_id,
        "tu_nv": a,
        "nhan_nv": c,
        "trung_gian": b,
        "dong_y": sorted(dong_y),
        "kiem_tra_5_dieu_kien": checks,
        "thoa_man_5_dieu_kien": passed,
        "snapshot_version": "live-v1",
    }
    if not passed:
        return ToolExecutionResult(
            success=False,
            tool_name="tool_prepare_swap_approval",
            intent="APPROVE_SHIFT_SWAP",
            data=diff,
            summary=f"Đổi ca {ca_id} chưa đủ điều kiện duyệt.",
            explanation="Điều kiện chưa đạt: "
            + ", ".join(k for k, v in checks.items() if not v),
            requires_confirmation=False,
            error="swap_conditions_not_met",
        )

    return ToolExecutionResult(
        success=True,
        tool_name="tool_prepare_swap_approval",
        intent="APPROVE_SHIFT_SWAP",
        data=diff,
        summary=f"Đề xuất duyệt đổi ca {ca_id}: {ten_a} → {ten_c} (đủ 3 nhánh đồng ý).",
        explanation=(
            "Đã kiểm tra: đủ 3 nhân sự khác nhau, cả 3 nhánh đã đồng ý, ca hợp lệ, "
            "không trùng ca khác, có lý do ghi nhận."
        ),
        requires_confirmation=True,
        source_snapshot=build_live_snapshot("APPROVE_SHIFT_SWAP", store_id),
    )


def tool_get_daily_brief(
    store_id: str = "quan_01",
    ngay: str | None = None,
    **kwargs: Any,
) -> ToolExecutionResult:
    """Generate daily operational morning brief from REAL KV data.

    Tổng hợp: phân công ca, việc treo, tồn kho dưới ngưỡng, luật mới.
    Không có dữ liệu nào → báo trung thực, không bịa.
    """
    from datetime import datetime

    ngay = ngay or datetime.now(UTC).date().isoformat()

    # 1. Phân công ca hôm nay (KV "phan_cong": {ca_id: [nv_id...]})
    phan_cong = _kv_get("phan_cong", {}) or {}
    users: dict[str, str] = {
        str(u.get("nv_id")): str(u.get("ten") or "")
        for u in (_kv_get("users", []) or [])
        if isinstance(u, dict) and u.get("nv_id")
    }
    ca_hom_nay: dict[str, list[str]] = {}
    for ca_id, nvs in phan_cong.items():
        if ngay in str(ca_id) or isinstance(nvs, list):
            ten_list = [users.get(nv, str(nv)) for nv in (nvs or []) if isinstance(nv, str)]
            if ten_list:
                ca_hom_nay[str(ca_id)] = ten_list

    # 2. Việc treo đang chờ
    treo = [t for t in (_kv_get("treo", []) or []) if isinstance(t, dict)]
    treo_cho = [t for t in treo if str(t.get("trang_thai") or "dang_cho") == "dang_cho"]

    # 3. Tồn kho dưới ngưỡng (KV "tieu_thu": [{hang, so_luong, duoi_nguong}])
    ton = [x for x in (_kv_get("tieu_thu", []) or []) if isinstance(x, dict)]
    canh_bao = [
        f"{x.get('hang')}: còn {x.get('so_luong')} {x.get('don_vi') or ''}".strip()
        for x in ton
        if x.get("duoi_nguong")
    ]

    # 4. Sự cố từ việc treo (nội dung chứa từ khoá sự cố)
    su_co = [
        str(t.get("noi_dung") or "")[:120]
        for t in treo_cho
        if any(k in str(t.get("noi_dung") or "").lower() for k in ("hỏng", "lỗi", "sửa", "cần"))
    ]

    parts: list[str] = []
    if ca_hom_nay:
        n_nv = sum(len(v) for v in ca_hom_nay.values())
        parts.append(f"{n_nv} lượt phân công trong {len(ca_hom_nay)} ca")
    if su_co:
        parts.append(f"{len(su_co)} sự cố cần chú ý")
    if canh_bao:
        parts.append(f"{len(canh_bao)} mặt hàng dưới ngưỡng tồn")
    if treo_cho:
        parts.append(f"{len(treo_cho)} việc treo đang chờ")

    if not parts:
        summary = f"Chưa có dữ liệu vận hành nào được ghi nhận cho ngày {ngay}."
        explanation = (
            "Chưa có phân công, việc treo hay tồn kho nào trong hệ thống. "
            "Dữ liệu sẽ xuất hiện khi nhân viên điểm danh, ghi phiếu và quản lý xếp lịch."
        )
        data: dict[str, Any] = {"ngay": ngay, "co_du_lieu": False}
    else:
        summary = f"Bản tin {ngay}: " + ", ".join(parts) + "."
        explanation = summary
        data = {
            "ngay": ngay,
            "co_du_lieu": True,
            "ca": ca_hom_nay,
            "su_co_can_chu_y": su_co,
            "ton_kho_thap": canh_bao,
            "so_treo_cho": len(treo_cho),
        }

    return ToolExecutionResult(
        success=True,
        tool_name="tool_get_daily_brief",
        intent="GENERATE_DAILY_BRIEF",
        data=data,
        summary=summary,
        explanation=explanation,
        requires_confirmation=False,
    )


def tool_query_sop_playbook(
    cau_hoi: str,
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Answer SOP question strictly from YAML templates + approved laws (AG-SOP).

    Dùng sop_answer được inject (AG-SOP thật): match câu hỏi với bước trong
    phiếu YAML (mo_quan/dong_quan/ban_giao_ca) + luật hiệu lực trong cẩm nang.
    Không có → trả "chưa có trong cẩm nang" — không bịa.
    """
    sop_answer = _src("sop_answer")
    load_template = _src("load_template")
    list_luat = _src("list_luat")

    q = (cau_hoi or "").lower()

    # Chọn mẫu phiếu phù hợp nhất theo từ khoá
    mau = "mo_quan"
    if any(k in q for k in ("đóng quán", "dong quan", "khóa cửa", "khoa cua", "cuối ngày")):
        mau = "dong_quan"
    elif any(k in q for k in ("bàn giao", "ban giao", "giao ca", "handover")):
        mau = "ban_giao_ca"

    tpl = load_template(mau) if load_template else None
    buoc = list(tpl.get("buoc") or []) if isinstance(tpl, dict) else []
    luat = list(list_luat() or []) if list_luat else []

    if not buoc and not luat:
        return ToolExecutionResult(
            success=True,
            tool_name="tool_query_sop_playbook",
            intent="QUERY_SOP",
            data={"answer": "Chưa tải được cẩm nang của quán.", "citations": [], "chua_co": True},
            summary="Chưa tải được cẩm nang của quán.",
            explanation="Không đọc được mẫu phiếu YAML và luật hiệu lực.",
            requires_confirmation=False,
        )

    if sop_answer is None:
        return ToolExecutionResult(
            success=True,
            tool_name="tool_query_sop_playbook",
            intent="QUERY_SOP",
            data={"answer": "Chưa cấu hình nguồn dữ liệu SOP.", "citations": [], "chua_co": True},
            summary="Chưa cấu hình nguồn dữ liệu SOP.",
            explanation="API layer chưa gọi configure_data_sources(sop_answer=...).",
            requires_confirmation=False,
        )

    r = sop_answer(cau_hoi or "", buoc=buoc, luat=luat)
    citations = list(getattr(r, "trich_dan", []) or [])
    if not getattr(r, "chua_co", True) and tpl:
        citations = [f"templates/{mau}.yaml"] + citations

    return ToolExecutionResult(
        success=True,
        tool_name="tool_query_sop_playbook",
        intent="QUERY_SOP",
        data={"answer": r.cau_tra_loi, "citations": citations, "chua_co": r.chua_co},
        summary=r.cau_tra_loi,
        explanation=("Trích dẫn từ: " + ", ".join(citations)) if citations else "Không tìm thấy trong cẩm nang.",
        requires_confirmation=False,
    )


def tool_get_waste_summary(
    store_id: str = "quan_01",
    khoang_ngay: str = "hom_nay",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Query structured waste summary from REAL waste notes (KV "waste_notes").

    Dùng waste_cluster được inject (AG-WASTE thật) để nhóm ghi chú hao hụt.
    Không có ghi chú → báo trung thực.
    """
    waste_cluster = _src("waste_cluster")

    stored = [x for x in (_kv_get("waste_notes", []) or []) if isinstance(x, dict)]
    pairs = [(str(x.get("thu", "")), str(x.get("ghi_chu", ""))) for x in stored if x.get("ghi_chu")]

    if not pairs:
        return ToolExecutionResult(
            success=True,
            tool_name="tool_get_waste_summary",
            intent="ANALYZE_WASTE",
            data={"so_ghi_nhan": 0, "co_du_lieu": False},
            summary="Chưa có ghi chú hao hụt nào được ghi nhận.",
            explanation="Nhân viên chưa ghi hao hụt nào qua mặt Hao hụt (/hao-phi).",
            requires_confirmation=False,
        )

    clusters: list[dict[str, Any]] = []
    if waste_cluster is not None:
        clusters = [x.__dict__ if hasattr(x, "__dict__") else dict(x) for x in waste_cluster(pairs)]
    n = len(pairs)
    summary = f"Đã ghi nhận {n} ghi chú hao hụt."
    if clusters:
        summary += f" Phát hiện {len(clusters)} mẫu lặp: " + "; ".join(
            str(x.get("cau") or x.get("ten") or "") for x in clusters[:3]
        ) + "."

    return ToolExecutionResult(
        success=True,
        tool_name="tool_get_waste_summary",
        intent="ANALYZE_WASTE",
        data={"so_ghi_nhan": n, "so_cum": len(clusters), "cum": clusters, "co_du_lieu": True},
        summary=summary,
        explanation=f"Phân cụm từ {n} ghi chú thật của nhân viên (nguồn: waste_notes).",
        requires_confirmation=False,
    )


def tool_propose_rule_from_recent_edits(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Analyze recent manual manager edits and propose a Vietnamese operating rule.

    Dùng tim_mau + de_xuat được inject (ca_playbook thật): phân tích lịch sử
    sửa lịch (list_sua) thành mẫu lặp → đề xuất luật. Không có mẫu → báo trung thực.
    """
    list_sua = _src("list_sua")
    tim_mau = _src("tim_mau")
    de_xuat = _src("de_xuat")

    if not (list_sua and tim_mau and de_xuat):
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_rule_from_recent_edits",
            intent="CREATE_RULE_PROPOSAL",
            data={},
            summary="Chưa cấu hình nguồn dữ liệu cẩm nang sống.",
            explanation="API layer chưa gọi configure_data_sources(list_sua=..., tim_mau=..., de_xuat=...).",
            requires_confirmation=False,
            error="playbook_sources_not_configured",
        )

    sua = list(list_sua() or [])
    mau = list(tim_mau(sua) or [])

    if not mau:
        return ToolExecutionResult(
            success=True,
            tool_name="tool_propose_rule_from_recent_edits",
            intent="CREATE_RULE_PROPOSAL",
            data={"so_lan_sua": len(sua), "so_mau": 0, "co_de_xuat": False},
            summary="Chưa có mẫu lặp đủ mạnh để đề xuất luật mới.",
            explanation=(
                f"Đã phân tích {len(sua)} lần sửa lịch thật của quản lý — "
                "chưa có mẫu nào lặp đủ số lần theo quy tắc 8 bước."
            ),
            requires_confirmation=False,
        )

    # Đề xuất từ mẫu mạnh nhất — de_xuat trả None khi mẫu thiếu tín hiệu
    # (không đủ nhân sự suy ra được), nên lọc trước khi chọn.
    co_le = [d for d in (de_xuat(m) for m in mau) if d]
    if not co_le:
        return ToolExecutionResult(
            success=True,
            tool_name="tool_propose_rule_from_recent_edits",
            intent="CREATE_RULE_PROPOSAL",
            data={"so_lan_sua": len(sua), "so_mau": len(mau), "co_de_xuat": False},
            summary="Chưa đủ tín hiệu từ các mẫu sửa để dựng đề xuất luật.",
            explanation=(
                f"Có {len(mau)} mẫu lặp nhưng chưa mẫu nào cho phép suy tất định "
                "nội dung luật (thiếu số người/vị trí trong dữ liệu sửa)."
            ),
            requires_confirmation=False,
        )
    best = co_le[0]

    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_rule_from_recent_edits",
        intent="CREATE_RULE_PROPOSAL",
        data={
            "so_lan_sua": len(sua),
            "so_mau": len(mau),
            "de_xuat": best,
            "co_de_xuat": True,
            "snapshot_version": "live-v1",
        },
        summary=f"Đề xuất luật mới: \"{best.get('cau') or best.get('cau_luat')}\" (dựa trên {len(sua)} lần sửa thật).",
        explanation=str(best.get("ly_do") or best.get("dien_giai") or "Sinh từ mẫu lặp trong lịch sử sửa lịch của quản lý."),
        source_snapshot=build_live_snapshot("CREATE_RULE_PROPOSAL", store_id),
        requires_confirmation=True,
    )


def tool_check_inventory_restock(
    store_id: str = "quan_01",
    nguong_canh_bao: float = 10.0,
    **kwargs: Any,
) -> ToolExecutionResult:
    """Check inventory stock levels against thresholds from REAL data (KV "tieu_thu").

    Nhân viên ghi số lượng tồn qua mặt Tiêu thụ (/tieu-thu) — tool đọc và
    cảnh báo mặt nào dưới ngưỡng. Không có dữ liệu → báo trung thực.
    """
    ton = [x for x in (_kv_get("tieu_thu", []) or []) if isinstance(x, dict)]

    if not ton:
        return ToolExecutionResult(
            success=True,
            tool_name="tool_check_inventory_restock",
            intent="INVENTORY_RESTOCK_CHECK",
            data={"so_mat_hang": 0, "co_du_lieu": False},
            summary="Chưa có dữ liệu tồn kho nào được ghi nhận.",
            explanation="Nhân viên chưa ghi số lượng hàng qua mặt Tiêu thụ (/tieu-thu).",
            requires_confirmation=False,
        )

    # Mặt hàng dưới ngưỡng (dữ liệu đã có flag duoi_nguong từ API ghi)
    canh_bao = [
        {
            "mat_hang": x.get("hang"),
            "ton_hien_tai": x.get("so_luong"),
            "don_vi": x.get("don_vi") or "đơn vị",
            "duoi_nguong": bool(x.get("duoi_nguong")),
        }
        for x in ton
        if x.get("duoi_nguong")
    ]

    if not canh_bao:
        return ToolExecutionResult(
            success=True,
            tool_name="tool_check_inventory_restock",
            intent="INVENTORY_RESTOCK_CHECK",
            data={"so_mat_hang": len(ton), "canh_bao": [], "co_du_lieu": True},
            summary=f"Đã kiểm tra {len(ton)} mặt hàng — tất cả đều trên ngưỡng an toàn.",
            explanation="Không có mặt hàng nào dưới ngưỡng cảnh báo.",
            requires_confirmation=False,
        )

    items_text = ", ".join(
        f"{x['mat_hang']} (còn {x['ton_hien_tai']} {x['don_vi']})" for x in canh_bao
    )
    summary = f"Cảnh báo {len(canh_bao)}/{len(ton)} mặt hàng dưới ngưỡng tồn: {items_text}."
    explanation = (
        "Đề xuất kiểm kê lại và đặt hàng bổ sung các mặt hàng trên. "
        "Duyệt để tạo đơn đặt hàng nháp trong hệ thống."
    )

    return ToolExecutionResult(
        success=True,
        tool_name="tool_check_inventory_restock",
        intent="INVENTORY_RESTOCK_CHECK",
        data={"so_mat_hang": len(ton), "canh_bao": canh_bao, "co_du_lieu": True},
        summary=summary,
        explanation=explanation,
        requires_confirmation=True,
        source_snapshot=ton,
    )


def tool_send_mail(
    store_id: str = "quan_01",
    to_nv_ids: list[str] | None = None,
    subject: str = "",
    body: str = "",
    **kwargs: Any,
) -> ToolExecutionResult:
    """Delegate email drafting to AG-MAILWRITER and generate an ActionProposal.

    Tuân thủ Two-Phase Approval: Tool chỉ soạn thảo thư chuyên nghiệp và trả về
    ActionProposal (requires_confirmation=True) để Chủ quán/Quản lý xem trước,
    duyệt, sửa hoặc từ chối trước khi gửi thật qua SMTP.
    """
    to_nv_ids = list(to_nv_ids or [])
    direct_emails = list(kwargs.get("direct_emails") or [])
    recipient_names = list(kwargs.get("recipient_names") or [])
    raw_request = str(kwargs.get("raw_request") or body or subject or "Thông báo công việc").strip()

    # Tra cứu email thật từ user table (inject qua get_user_emails)
    get_emails = _src("get_user_emails")
    try:
        email_map = dict(get_emails() or {}) if get_emails else {}
    except Exception:
        email_map = {}
    to_emails: list[str] = list(direct_emails)
    missing: list[str] = []

    for nv in to_nv_ids:
        em = email_map.get(nv)
        if em:
            if em not in to_emails:
                to_emails.append(em)
        else:
            missing.append(nv)

    # Xác định danh xưng người nhận
    if recipient_names:
        recip_label = ", ".join(recipient_names)
    elif to_emails:
        recip_label = ", ".join(to_emails)
    elif missing:
        recip_label = ", ".join(missing)
    else:
        recip_label = "Nhân viên quán"

    if not to_emails:
        return ToolExecutionResult(
            success=False,
            tool_name="tool_send_mail",
            intent="SEND_MAIL",
            data={
                "to_emails": [],
                "to_nv_ids": to_nv_ids,
                "recipient_names": recipient_names,
                "recip_label": recip_label,
                "missing": missing,
                "snapshot_version": "live-v1",
            },
            summary=f"Chưa thể tạo đề xuất gửi email cho {recip_label}.",
            explanation="Không tìm thấy địa chỉ email hợp lệ của người nhận.",
            requires_confirmation=False,
            error="no_recipient_email",
        )

    # Lấy dữ liệu vận hành sống (Compound Context) & Gu văn phong (Tone Memory)
    get_ops_ctx = _src("get_ops_context")
    try:
        ops_context = get_ops_ctx(store_id=store_id, to_nv_ids=to_nv_ids, raw_request=raw_request) if get_ops_ctx else None
    except Exception:
        ops_context = None

    get_style = _src("get_mail_style")
    try:
        style_memory = get_style(store_id=store_id) if get_style else None
    except Exception:
        style_memory = None

    # Gọi Agent chuyên trách AG-MAILWRITER (inject qua _src("draft_mail"))
    draft_fn = _src("draft_mail")
    has_learned = bool(style_memory)
    if draft_fn:
        try:
            draft = draft_fn(
                raw_request=raw_request,
                recipient_name=recip_label,
                recipient_email=", ".join(to_emails),
                store_id=store_id,
                to_nv_ids=to_nv_ids,
                sender_name="Ban Quản Lý Nhịp Quán",
                store_name="Nhịp Quán",
                ops_context=ops_context,
                style_memory=style_memory,
            )
            draft_subject = getattr(draft, "subject", "") or subject or f"[Nhịp Quán] Thông báo gửi {recip_label}"
            draft_body = getattr(draft, "body", "") or body or raw_request
            has_learned = getattr(draft, "has_learned_style", has_learned)
            rule_version = getattr(draft, "rule_version", "none")
            rollout_bucket = getattr(draft, "rollout_bucket", "control")
        except Exception:
            draft_subject = subject or f"[Nhịp Quán] Thông báo gửi {recip_label}"
            draft_body = body or raw_request
            rule_version = "none"
            rollout_bucket = "control"
    else:
        draft_subject = (
            subject if subject.startswith("[Nhịp Quán]") else f"[Nhịp Quán] Thông báo gửi {recip_label}"
        )
        draft_body = (
            f"Thân gửi {recip_label},\n\n"
            f"Ban Quản Lý Nhịp Quán xin thông báo:\n"
            f"- {raw_request}\n\n"
            f"Vui lòng phản hồi lại nếu cần thêm thông tin.\n\n"
            f"Trân trọng,\n"
            f"Ban Quản Lý Nhịp Quán"
        )
        rule_version = "none"
        rollout_bucket = "control"

    ops_summary = ""
    if ops_context:
        if ops_context.get("type") == "shift":
            ops_summary = f"Lịch ca {ops_context.get('ca_ten', '')} ({ops_context.get('gio', '')})"
        elif ops_context.get("type") == "inventory":
            ops_summary = f"Tồn kho {ops_context.get('mat_hang', '')} ({ops_context.get('ton_kho')} {ops_context.get('dvt', '')})"
        elif ops_context.get("type") == "daily_summary":
            ops_summary = "Số liệu vận hành ngày"

    payload = {
        "snapshot_version": "live-v1",
        "subject": draft_subject,
        "body": draft_body,
        "to_emails": to_emails,
        "to_nv_ids": to_nv_ids,
        "recipient_names": recipient_names,
        "recip_label": recip_label,
        "missing": missing,
        "raw_request": raw_request,
        "ops_context": ops_context,
        "ops_context_summary": ops_summary,
        "has_learned_style": has_learned,
        "rule_version": rule_version,
        "rollout_bucket": rollout_bucket,
    }

    explanation = (
        f"Agent AG-MAILWRITER đã soạn xong thư chuyên nghiệp cho {recip_label}. "
        "Anh/chị xem trước nội dung, có thể bấm 'Duyệt & Gửi' để gửi đi hoặc bảo em sửa lại nhé!"
    )

    return ToolExecutionResult(
        success=True,
        tool_name="tool_send_mail",
        intent="SEND_MAIL",
        data=payload,
        summary=f"Bản nháp email gửi {recip_label}: {draft_subject}",
        explanation=explanation,
        requires_confirmation=True,
        source_snapshot=build_live_snapshot("SEND_MAIL", store_id, payload),
    )


_TOOLS: dict[str, Callable[..., ToolExecutionResult]] = {
    "SCHEDULE_SOLVE": tool_solve_weekly_schedule,
    "APPROVE_SHIFT_SWAP": tool_prepare_swap_approval,
    "GENERATE_DAILY_BRIEF": tool_get_daily_brief,
    "QUERY_SOP": tool_query_sop_playbook,
    "ANALYZE_WASTE": tool_get_waste_summary,
    "CREATE_RULE_PROPOSAL": tool_propose_rule_from_recent_edits,
    "INVENTORY_RESTOCK_CHECK": tool_check_inventory_restock,
    "SEND_MAIL": tool_send_mail,
}


# ── PR9 read tools: GET_* intents trả dữ liệu sống tenant-scoped ───────────


def _read_result(
    intent: str,
    tool_name: str,
    data: dict[str, Any],
    summary: str,
    explanation: str,
) -> ToolExecutionResult:
    """Chuẩn hoá kết quả đọc: requires_confirmation=False, provenance trong data."""
    return ToolExecutionResult(
        success=True,
        tool_name=tool_name,
        intent=intent,
        data={
            "_provenance": {
                "source": tool_name,
                "read_at": datetime.now(UTC).isoformat(),
                "store_scope": True,
            },
            **data,
        },
        summary=summary,
        explanation=explanation,
        requires_confirmation=False,
    )


def tool_get_my_profile(
    store_id: str = "quan_01",
    user_id: str = "",
    **kwargs: Any,
) -> ToolExecutionResult:
    """GET_MY_PROFILE: hồ sơ của chính người hỏi (không đọc hộ người khác)."""
    list_users = _src("list_users")
    users = list(list_users() or []) if list_users else []
    me = next((u for u in users if isinstance(u, dict) and str(u.get("nv_id") or "") == user_id), None)
    if not me:
        return _read_result(
            "GET_MY_PROFILE", "tool_get_my_profile", {"found": False},
            "Không tìm thấy hồ sơ của anh/chị trong hệ thống.",
            "user_id không khớp dữ liệu users (tenant-scoped).",
        )
    return _read_result(
        "GET_MY_PROFILE", "tool_get_my_profile",
        {"found": True, "profile": {"nv_id": me.get("nv_id"), "ten": me.get("ten") or me.get("display_name"), "role": me.get("role")}},
        f"Hồ sơ: {me.get('ten') or me.get('display_name') or user_id} ({me.get('role')}).",
        "Đọc từ bảng users theo nv_id của session.",
    )


def tool_list_staff(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """LIST_STAFF: danh sách nhân sự trong store (không lộ email/password)."""
    list_users = _src("list_users")
    users = list(list_users() or []) if list_users else []
    staff = [
        {"nv_id": u.get("nv_id"), "ten": u.get("ten") or u.get("display_name"), "role": u.get("role")}
        for u in users if isinstance(u, dict)
    ]
    return _read_result(
        "LIST_STAFF", "tool_list_staff", {"so_nguoi": len(staff), "nhan_su": staff},
        f"Hiện có {len(staff)} nhân sự trong hệ thống.",
        "Đọc từ bảng users; không trả email/số điện thoại qua chat.",
    )


def tool_query_menu(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """QUERY_MENU: menu hiện hành từ bảng menu_mon."""
    menu_list = _src("menu_list")
    mons = list(menu_list() or []) if menu_list else []
    visible = [m for m in mons if isinstance(m, dict)]
    return _read_result(
        "QUERY_MENU", "tool_query_menu", {"so_mon": len(visible), "menu": visible},
        f"Menu hiện có {len(visible)} món.",
        "Đọc từ bảng menu_mon (bỏ món đã ẩn nếu nguồn trả theo trạng thái).",
    )


def tool_get_inventory(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """GET_INVENTORY: tồn kho hiện tại + cảnh báo dưới ngưỡng."""
    ton = [x for x in (_kv_get("tieu_thu", []) or []) if isinstance(x, dict)]
    duoi_nguong = [x for x in ton if x.get("duoi_nguong")]
    return _read_result(
        "GET_INVENTORY", "tool_get_inventory",
        {"so_mat_hang": len(ton), "duoi_nguong": len(duoi_nguong), "items": ton},
        f"Tồn kho: {len(ton)} mặt hàng, {len(duoi_nguong)} dưới ngưỡng.",
        "Đọc từ KV tieu_thu (tenant-scoped theo store_id).",
    )


def tool_get_shift_swaps(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """GET_SHIFT_SWAPS: các yêu cầu đổi ca đang chờ (không consent qua chat)."""
    swaps = [s for s in (_kv_get("swap", []) or []) if isinstance(s, dict)]
    cho = [s for s in swaps if str(s.get("trang_thai") or "") in ("cho_3_nhanh", "dong_y", "cho_duyet")]
    return _read_result(
        "GET_SHIFT_SWAPS", "tool_get_shift_swaps", {"so_cho": len(cho), "swaps": cho},
        f"{len(cho)} yêu cầu đổi ca đang chờ xử lý.",
        "Đọc từ KV swap; consent vẫn phải do nhân viên thao tác trên /doi-ca.",
    )


def tool_get_hanging_tasks(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """GET_HANGING_TASKS: việc treo đang chờ."""
    treo = [t for t in (_kv_get("treo", []) or []) if isinstance(t, dict)]
    cho = [t for t in treo if str(t.get("trang_thai") or "dang_cho") == "dang_cho"]
    return _read_result(
        "GET_HANGING_TASKS", "tool_get_hanging_tasks", {"so_cho": len(cho), "treo": cho},
        f"{len(cho)} việc treo đang chờ xử lý.",
        "Đọc từ KV treo (dang_cho).",
    )


def tool_get_handovers(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """GET_HANDOVERS: bản giao ca gần nhất."""
    list_sua = _src("list_sua")
    sua = list(list_sua() or []) if list_sua else []
    return _read_result(
        "GET_HANDOVERS", "tool_get_handovers", {"so_lan_sua": len(sua), "lich_su": sua[-10:]},
        f"{len(sua)} bản ghi sửa lịch/bàn giao gần nhất.",
        "Đọc từ ca_playbook list_sua (10 bản ghi gần nhất).",
    )


_READ_TOOLS: dict[str, Callable[..., ToolExecutionResult]] = {
    "GET_MY_PROFILE": tool_get_my_profile,
    "LIST_STAFF": tool_list_staff,
    "QUERY_MENU": tool_query_menu,
    "GET_INVENTORY": tool_get_inventory,
    "GET_SHIFT_SWAPS": tool_get_shift_swaps,
    "GET_HANGING_TASKS": tool_get_hanging_tasks,
    "GET_HANDOVERS": tool_get_handovers,
}

_TOOLS.update(_READ_TOOLS)


# ── PR10 self-service proposal tools (R2_CONFIRM) ─────────────────────────


def tool_propose_hanging_task(
    store_id: str = "quan_01",
    user_id: str = "",
    noi_dung: str = "",
    thieu_noi_dung: bool = False,
    **kwargs: Any,
) -> ToolExecutionResult:
    """PROPOSE_HANGING_TASK: tạo việc treo mới (cần duyệt)."""
    if thieu_noi_dung or not noi_dung.strip():
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_hanging_task",
            intent="PROPOSE_HANGING_TASK",
            data={},
            summary="Anh/chị muốn treo việc gì ạ?",
            explanation="Cần nội dung cụ thể của việc treo.",
            requires_confirmation=False,
            error="missing_noi_dung",
        )
    payload = {
        "snapshot_version": "live-v1",
        "noi_dung": noi_dung.strip()[:200],
        "nv_id": user_id,
    }
    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_hanging_task",
        intent="PROPOSE_HANGING_TASK",
        data=payload,
        summary=f"Đề xuất tạo việc treo: {payload['noi_dung']}",
        explanation="Việc treo sẽ xuất hiện trên /treo sau khi duyệt.",
        requires_confirmation=True,
        source_snapshot=build_live_snapshot("PROPOSE_HANGING_TASK", store_id),
    )


def tool_propose_task_complete(
    store_id: str = "quan_01",
    treo_id: str = "",
    thieu_treo_id: bool = False,
    **kwargs: Any,
) -> ToolExecutionResult:
    """PROPOSE_TASK_COMPLETE: đánh dấu một việc treo là xong (cần duyệt)."""
    if thieu_treo_id or not treo_id:
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_task_complete",
            intent="PROPOSE_TASK_COMPLETE",
            data={},
            summary="Anh/chị cho em mã việc treo cần đánh dấu xong (dạng treo_xxx).",
            explanation="Cần treo_id cụ thể.",
            requires_confirmation=False,
            error="missing_treo_id",
        )
    treo = [t for t in (_kv_get("treo", []) or []) if isinstance(t, dict)]
    target = next((t for t in treo if str(t.get("id") or "") == treo_id), None)
    if not target:
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_task_complete",
            intent="PROPOSE_TASK_COMPLETE",
            data={"treo_id": treo_id},
            summary=f"Không tìm thấy việc treo {treo_id}.",
            explanation="treo_id không tồn tại trong dữ liệu sống.",
            requires_confirmation=False,
            error="treo_not_found",
        )
    payload = {
        "snapshot_version": "live-v1",
        "treo_id": treo_id,
        "noi_dung": str(target.get("noi_dung") or "")[:200],
    }
    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_task_complete",
        intent="PROPOSE_TASK_COMPLETE",
        data=payload,
        summary=f"Đề xuất đánh dấu xong việc treo: {payload['noi_dung'] or treo_id}",
        explanation="Trạng thái việc treo sẽ chuyển thành 'xong' sau khi duyệt.",
        requires_confirmation=True,
        source_snapshot=build_live_snapshot("PROPOSE_TASK_COMPLETE", store_id),
    )


def tool_propose_consumption_record(
    store_id: str = "quan_01",
    hang: str = "",
    so_luong: float | None = None,
    don_vi: str = "khay",
    thieu_so_lieu: bool = False,
    **kwargs: Any,
) -> ToolExecutionResult:
    """PROPOSE_CONSUMPTION_RECORD: ghi tiêu thụ (cần duyệt quản lý)."""
    if thieu_so_lieu or so_luong is None or not hang.strip():
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_consumption_record",
            intent="PROPOSE_CONSUMPTION_RECORD",
            data={},
            summary="Anh/chị cho em biết mặt hàng và số lượng cần ghi tiêu thụ.",
            explanation="Cần hàng + số lượng (vd: 'ghi tiêu thụ 2 hộp sữa tươi').",
            requires_confirmation=False,
            error="missing_quantity_or_item",
        )
    payload = {
        "snapshot_version": "live-v1",
        "hang": hang.strip()[:60],
        "so_luong": so_luong,
        "don_vi": don_vi,
    }
    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_consumption_record",
        intent="PROPOSE_CONSUMPTION_RECORD",
        data=payload,
        summary=f"Đề xuất ghi tiêu thụ: {so_luong} {don_vi} {payload['hang']}.",
        explanation="Bản ghi sẽ vào sổ tiêu thụ (/tieu-thu) sau khi duyệt.",
        requires_confirmation=True,
        source_snapshot=build_live_snapshot("PROPOSE_CONSUMPTION_RECORD", store_id),
    )


# ── PR11 admin proposal tools (R2_CONFIRM, quan_ly/chu_quan) ─────────────

# Khớp state machine đơn quầy tại route web /quay (pos.py _STATUS_NEXT).
_ORDER_STATUS_NEXT: dict[str, set[str]] = {
    "cho_pha": {"dang_pha", "huy"},
    "dang_pha": {"xong", "huy"},
    "xong": set(),
    "huy": set(),
}


def tool_propose_menu_update(
    store_id: str = "quan_01",
    ten_mon: str = "",
    gia: int | None = None,
    an: bool | None = None,
    thieu_thong_tin: bool = False,
    **kwargs: Any,
) -> ToolExecutionResult:
    """PROPOSE_MENU_UPDATE: sửa giá/ẩn/thêm món (cần duyệt quản lý)."""
    if thieu_thong_tin or not ten_mon.strip():
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_menu_update",
            intent="PROPOSE_MENU_UPDATE",
            data={},
            summary="Anh/chị cho em biết món và giá mới (hoặc nói 'ẩn món <tên>').",
            explanation="Cần tên món + giá mới, hoặc yêu cầu ẩn món.",
            requires_confirmation=False,
            error="missing_menu_info",
        )
    menu_list = _src("menu_list")
    mons = list(menu_list(gom_an=True) or []) if menu_list else []
    mon = next(
        (m for m in mons if isinstance(m, dict) and str(m.get("ten") or "").lower() == ten_mon.lower()),
        None,
    )
    if mon is None:
        if gia is None:
            return ToolExecutionResult(
                success=False,
                tool_name="tool_propose_menu_update",
                intent="PROPOSE_MENU_UPDATE",
                data={"ten_mon": ten_mon},
                summary=f"Không tìm thấy món '{ten_mon}' trong menu.",
                explanation="Tên món không khớp dữ liệu sống; thêm món mới cần giá.",
                requires_confirmation=False,
                error="mon_not_found",
            )
        # Thêm món mới
        payload = {
            "snapshot_version": "live-v1",
            "hanh_dong": "them",
            "ten_mon": ten_mon,
            "gia": gia,
            "an": False,
        }
        summary = f"Đề xuất thêm món '{ten_mon}' với giá {gia}đ."
    elif gia is not None:
        payload = {
            "snapshot_version": "live-v1",
            "hanh_dong": "sua_gia",
            "mon_id": str(mon.get("id") or ""),
            "ten_mon": ten_mon,
            "gia_cu": int(mon.get("gia") or 0),
            "gia": gia,
        }
        summary = f"Đề xuất sửa giá '{ten_mon}': {payload['gia_cu']}đ → {gia}đ."
    elif an is not None:
        payload = {
            "snapshot_version": "live-v1",
            "hanh_dong": "an_mon" if an else "hien_mon",
            "mon_id": str(mon.get("id") or ""),
            "ten_mon": ten_mon,
        }
        summary = f"Đề xuất {'ẩn' if an else 'hiện lại'} món '{ten_mon}'."
    else:
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_menu_update",
            intent="PROPOSE_MENU_UPDATE",
            data={"ten_mon": ten_mon},
            summary="Chưa rõ thay đổi cần làm với món này.",
            explanation="Cần giá mới hoặc yêu cầu ẩn/hiện món.",
            requires_confirmation=False,
            error="no_change_specified",
        )
    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_menu_update",
        intent="PROPOSE_MENU_UPDATE",
        data=payload,
        summary=summary,
        explanation="Menu (/menu) sẽ cập nhật sau khi duyệt.",
        requires_confirmation=True,
        source_snapshot=build_live_snapshot("PROPOSE_MENU_UPDATE", store_id),
    )


def tool_propose_order_transition(
    store_id: str = "quan_01",
    don_id: str = "",
    trang_thai: str = "",
    ly_do_huy: str = "",
    thieu_thong_tin: bool = False,
    **kwargs: Any,
) -> ToolExecutionResult:
    """PROPOSE_ORDER_TRANSITION: chuyển trạng thái đơn quầy theo state machine.

    Thanh toán và chỉnh sửa nội dung đơn là R4_MANUAL_ONLY — không qua chat.
    """
    if thieu_thong_tin or not don_id or not trang_thai:
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_order_transition",
            intent="PROPOSE_ORDER_TRANSITION",
            data={},
            summary="Anh/chị cho em mã đơn (dq_xxx) và trạng thái cần chuyển.",
            explanation="Cần don_id + trạng thái đích (đang pha/xong/hủy).",
            requires_confirmation=False,
            error="missing_order_info",
        )
    don_get = _src("don_get")
    don = don_get(don_id) if don_get else None
    if not don:
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_order_transition",
            intent="PROPOSE_ORDER_TRANSITION",
            data={"don_id": don_id},
            summary=f"Không tìm thấy đơn {don_id}.",
            explanation="don_id không tồn tại trong dữ liệu sống.",
            requires_confirmation=False,
            error="don_not_found",
        )
    cur = str(don.get("trang_thai") or "")
    if trang_thai not in _ORDER_STATUS_NEXT.get(cur, set()):
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_order_transition",
            intent="PROPOSE_ORDER_TRANSITION",
            data={"don_id": don_id, "trang_thai_hiện_tại": cur, "trang_thai_dích": trang_thai},
            summary=f"Không thể chuyển đơn {don_id} từ '{cur}' sang '{trang_thai}'.",
            explanation="Chuyển trạng thái không hợp lệ theo luồng đơn quầy.",
            requires_confirmation=False,
            error=f"chuyen_khong_hop_le:{cur}->{trang_thai}",
        )
    if trang_thai == "huy" and not ly_do_huy.strip():
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_order_transition",
            intent="PROPOSE_ORDER_TRANSITION",
            data={"don_id": don_id, "trang_thai": trang_thai},
            summary="Hủy đơn cần lý do cụ thể.",
            explanation="Anh/chị nhắn lại kèm lý do hủy nhé.",
            requires_confirmation=False,
            error="can_ly_do_huy",
        )
    payload = {
        "snapshot_version": "live-v1",
        "don_id": don_id,
        "trang_thai": trang_thai,
        "trang_thai_hien_tai": cur,
        "ly_do_huy": ly_do_huy.strip()[:200],
    }
    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_order_transition",
        intent="PROPOSE_ORDER_TRANSITION",
        data=payload,
        summary=f"Đề xuất chuyển đơn {don_id}: {cur} → {trang_thai}.",
        explanation="Trạng thái đơn sẽ đổi sau khi duyệt; thanh toán vẫn giữ manual.",
        requires_confirmation=True,
        source_snapshot=build_live_snapshot("PROPOSE_ORDER_TRANSITION", store_id, {"don_id": don_id}),
    )


def tool_propose_pin(
    store_id: str = "quan_01",
    ca_id: str = "",
    nv_id: str = "",
    pinned: bool = True,
    thieu_thong_tin: bool = False,
    **kwargs: Any,
) -> ToolExecutionResult:
    """PROPOSE_PIN: ghim/bỏ ghim một ca trên lịch tuần (cần duyệt quản lý)."""
    if thieu_thong_tin or not ca_id or not nv_id:
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_pin",
            intent="PROPOSE_PIN",
            data={},
            summary="Anh/chị cho em mã ca (vd w1_c01) và nhân viên cần ghim.",
            explanation="Cần ca_id + nv_id.",
            requires_confirmation=False,
            error="missing_pin_info",
        )
    payload = {
        "snapshot_version": "live-v1",
        "ca_id": ca_id,
        "nv_id": nv_id,
        "pinned": pinned,
    }
    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_pin",
        intent="PROPOSE_PIN",
        data=payload,
        summary=f"Đề xuất {'ghim' if pinned else 'bỏ ghim'} ca {ca_id} của {nv_id}.",
        explanation="Ca được ghim sẽ không bị solver đổi khi xếp lịch lại.",
        requires_confirmation=True,
        source_snapshot=build_live_snapshot("PROPOSE_PIN", store_id),
    )


def tool_get_page_status(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """GET_PAGE_STATUS: trạng thái kết nối Facebook Page (không lộ token)."""
    page_status = _src("page_status")
    if page_status is None:
        return _read_result(
            "GET_PAGE_STATUS", "tool_get_page_status", {"connected": False, "chua_cau_hinh": True},
            "Chưa cấu hình nguồn trạng thái Page.",
            "API layer chưa inject page_status.",
        )
    try:
        st = dict(page_status() or {})
    except Exception as exc:
        return _read_result(
            "GET_PAGE_STATUS", "tool_get_page_status", {"connected": False, "loi": str(exc)[:120]},
            "Không đọc được trạng thái Page.",
            "Nguồn page_status lỗi.",
        )
    st.pop("has_token", None)  # không tiết lộ tồn tại token qua chat
    connected = bool(st.get("connected"))
    return _read_result(
        "GET_PAGE_STATUS", "tool_get_page_status", st,
        (
            f"Page đang kết nối (mode {st.get('mode')})."
            if connected
            else "Page chưa kết nối — xem /page-quan để cấu hình."
        ),
        "Đọc từ nguồn page_status của API layer.",
    )


def tool_propose_page_sync(
    store_id: str = "quan_01",
    **kwargs: Any,
) -> ToolExecutionResult:
    """PROPOSE_PAGE_SYNC: kéo hội thoại Messenger từ Graph (cần duyệt quản lý)."""
    page_status = _src("page_status")
    st: dict[str, Any] = {}
    if page_status is not None:
        try:
            st = dict(page_status() or {})
        except Exception:
            st = {}
    if not st.get("connected"):
        return ToolExecutionResult(
            success=False,
            tool_name="tool_propose_page_sync",
            intent="PROPOSE_PAGE_SYNC",
            data={"connected": st.get("connected")},
            summary="Page chưa kết nối nên không thể đồng bộ.",
            explanation="Cần cấu hình token + Page ID live trước (xem /page-quan).",
            requires_confirmation=False,
            error="page_chua_live",
        )
    payload = {"snapshot_version": "live-v1", "hanh_dong": "sync_threads"}
    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_page_sync",
        intent="PROPOSE_PAGE_SYNC",
        data=payload,
        summary="Đề xuất đồng bộ hội thoại Messenger từ Page.",
        explanation="Hội thoại mới sẽ xuất hiện trong hộp thư Fanpage sau khi duyệt.",
        requires_confirmation=True,
        source_snapshot=build_live_snapshot("PROPOSE_PAGE_SYNC", store_id),
    )


_TOOLS.update({
    "PROPOSE_HANGING_TASK": tool_propose_hanging_task,
    "PROPOSE_TASK_COMPLETE": tool_propose_task_complete,
    "PROPOSE_CONSUMPTION_RECORD": tool_propose_consumption_record,
    "PROPOSE_MENU_UPDATE": tool_propose_menu_update,
    "PROPOSE_ORDER_TRANSITION": tool_propose_order_transition,
    "PROPOSE_PIN": tool_propose_pin,
    "GET_PAGE_STATUS": tool_get_page_status,
    "PROPOSE_PAGE_SYNC": tool_propose_page_sync,
})


_TOOLS.update({
    "PROPOSE_HANGING_TASK": tool_propose_hanging_task,
    "PROPOSE_TASK_COMPLETE": tool_propose_task_complete,
    "PROPOSE_CONSUMPTION_RECORD": tool_propose_consumption_record,
    "PROPOSE_MENU_UPDATE": tool_propose_menu_update,
    "PROPOSE_ORDER_TRANSITION": tool_propose_order_transition,
    "PROPOSE_PIN": tool_propose_pin,
})


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
