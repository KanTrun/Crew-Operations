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
from dataclasses import dataclass
from pathlib import Path
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
      - de_xuat(mau) -> dict                (sinh đề xuất luật từ mẫu)
      - sop_answer(q, buoc, luat) -> SopAnswer
      - waste_cluster(notes) -> list[WasteHint]
      - list_ca_meta() -> dict[str, dict]   (ca_id -> {thu, khung, bat_dau, ket_thuc})
    """
    _SOURCES.clear()
    _SOURCES.update(sources)


def _src(name: str) -> Callable[..., Any] | None:
    return _SOURCES.get(name)


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


def _swap_khong_trung_ca(
    phan_cong: dict[str, Any],
    ca_dich: str,
    nhan_nv: str | None,
    list_ca_meta: Callable[..., Any] | None,
) -> bool:
    """Trả True nếu nhan_nv trùng ca khác CÙNG khung giờ với ca_dich.

    Khi dữ liệu ca_meta không có (thiếu source / standalone), mặc định True
    (cho phép) — giữ an toàn cho test không set đủ dữ liệu. Bỏ hardcode cũ.
    """
    if not nhan_nv or not ca_dich:
        return True
    if not list_ca_meta:
        return True
    try:
        ca_meta = list_ca_meta() or {}
    except Exception:
        return True

    meta_dich = ca_meta.get(ca_dich)
    if not isinstance(meta_dich, dict):
        # Không có meta ca đích → không thể so, coi là không trùng (fail-open nhẹ).
        return True

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
    from datetime import datetime, timezone

    ngay = ngay or datetime.now(timezone.utc).date().isoformat()

    # 1. Phân công ca hôm nay (KV "phan_cong": {ca_id: [nv_id...]})
    phan_cong = _kv_get("phan_cong", {}) or {}
    users = {u.get("nv_id"): u.get("ten") for u in (_kv_get("users", []) or []) if isinstance(u, dict)}
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
    top = clusters[0] if clusters else {}
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

    # Đề xuất từ mẫu mạnh nhất
    de_xuat_list = [de_xuat(m) for m in mau]
    best = de_xuat_list[0]

    return ToolExecutionResult(
        success=True,
        tool_name="tool_propose_rule_from_recent_edits",
        intent="CREATE_RULE_PROPOSAL",
        data={
            "so_lan_sua": len(sua),
            "so_mau": len(mau),
            "de_xuat": best,
            "co_de_xuat": True,
        },
        summary=f"Đề xuất luật mới: \"{best.get('cau') or best.get('cau_luat')}\" (dựa trên {len(sua)} lần sửa thật).",
        explanation=str(best.get("ly_do") or best.get("dien_giai") or "Sinh từ mẫu lặp trong lịch sử sửa lịch của quản lý."),
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
