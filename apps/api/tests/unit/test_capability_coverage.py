"""PR13 coverage gate — mọi route user-facing phải có capability hoặc exclusion.

Kế hoạch §PR13: "CI fail khi thêm chức năng user-facing mà không khai báo
capability hoặc explicit exclusion". Gate này quét các router FastAPI, trích
route path, và đối chiếu với CAPABILITY_REGISTRY + EXCLUDED_ROUTES.
"""

from __future__ import annotations

import re
from pathlib import Path

from ca_contracts import CAPABILITY_REGISTRY

API_SRC = Path(__file__).resolve().parents[2] / "src" / "ca_api" / "interfaces" / "http"

# Route không điều phối qua chat theo thiết kế (kế hoạch §1.2 — R4_MANUAL_ONLY
# hoặc hạ tầng kỹ thuật). Mỗi exclusion phải có lý do.
EXCLUDED_ROUTES: dict[str, str] = {
    # Auth — thao tác bảo mật bắt buộc
    "/api/v1/auth/login": "R4: đăng nhập là thao tác bảo mật",
    "/api/v1/auth/register": "R4: đăng ký là thao tác bảo mật",
    # Webhook / ingestion — hạ tầng kỹ thuật, không phải chức năng user-facing
    "/api/v1/channels/telegram/webhook": "webhook hạ tầng Meta/Telegram",
    "/api/v1/channels/zalo/webhook": "webhook hạ tầng Zalo",
    "/api/v1/channels/facebook/webhook": "webhook hạ tầng Meta",
    "/api/v1/channels/replay": "R4: replay ingestion chỉ chạy từ công cụ vận hành",
    # Copilot tự tham chiếu — chính là lớp điều phối
    "/message": "copilot core",
    "/message/stream": "copilot core",
    "/execute-action": "copilot core",
    "/action/{action_id}/amend": "copilot core",
    "/action/{action_id}": "copilot core",
    "/audit": "copilot core",
    "/permissions": "copilot core",
    "/capabilities": "copilot core",
    "/navigate": "copilot core",
    # Upload tệp nhị phân — trình duyệt xử lý trực tiếp
    "/api/v1/chat/upload": "upload tệp qua trình duyệt",
    "/api/v1/chat/uploads/{filename}": "tệp tĩnh",
    "/api/v1/menu/{mon_id}/anh": "upload ảnh qua trình duyệt",
    # Health/metrics nội bộ
    "/api/v1/ops/pickers": "chẩn đoán nội bộ",
    "/api/v1/ab": "báo cáo A/B nội bộ",
    "/api/v1/vf/conflict": "chẩn đoán VF nội bộ",
    "/api/v1/vf/conflict-demo": "demo VF nội bộ",
    "/api/v1/ai/retention/dry-run": "chẩn đoán retention nội bộ",
    "/api/v1/reservations-metrics": "metrics nội bộ",
    # ── AI-learning / governance (PR13 scope, deep-link /ai-learning) ──
    "/api/v1/ai/rules/proposals": "AI governance — duyệt qua UI /ai-learning",
    "/api/v1/ai/generations": "AI governance — đọc qua UI /ai-learning",
    "/api/v1/ai/feedback": "AI governance — feedback qua UI /ai-learning",
    "/api/v1/ai/evaluations/summary": "AI governance — đọc qua UI /ai-learning",
    "/api/v1/ai/operations/status": "AI governance — trạng thái qua UI",
    "/api/v1/ai/operations/circuit-breaker": "R3: circuit breaker qua UI dual approval",
    "/api/v1/ai/reflection/gmail/run": "AI governance — reflection qua UI",
    "/api/v1/ai/reflection/facebook/run": "AI governance — reflection qua UI",
    "/api/v1/ai/rules/proposals/{proposal_id}/approve": "R3: dual approval qua UI",
    "/api/v1/ai/rules/proposals/{proposal_id}/activate": "R3: dual approval qua UI",
    "/api/v1/ai/rules/proposals/{proposal_id}/reject": "R3: dual approval qua UI",
    "/api/v1/ai/rules/{proposal_id}/pause": "R3: dual approval qua UI",
    "/api/v1/ai/rules/{proposal_id}/rollback": "R3: dual approval qua UI",
    # ── Chat nội bộ — realtime channel, không phải tác vụ điều phối ──
    "/api/v1/chat/conversations": "chat realtime — kênh giao tiếp",
    "/api/v1/chat/conversations/{conv_id}": "chat realtime — kênh giao tiếp",
    "/api/v1/chat/conversations/{conv_id}/messages": "chat realtime — kênh giao tiếp",
    "/api/v1/chat/conversations/{conv_id}/mute": "chat realtime — kênh giao tiếp",
    "/api/v1/chat/conversations/{conv_id}/read": "chat realtime — kênh giao tiếp",
    "/api/v1/chat/messages/{message_id}": "chat realtime — kênh giao tiếp",
    "/api/v1/chat/messages/{message_id}/pin": "chat realtime — kênh giao tiếp",
    "/api/v1/chat/messages/{message_id}/reactions": "chat realtime — kênh giao tiếp",
    "/api/v1/chat/online": "chat realtime — kênh giao tiếp",
    "/api/v1/chat/search": "chat realtime — kênh giao tiếp",
    # ── Facebook Page chi tiết — deep-link /page-quan đã phủ miền ──
    "/api/v1/page/threads": "FB Page — deep-link /page-quan/fb-inbox",
    "/api/v1/page/threads/{thread_id}/reply": "FB Page — deep-link /page-quan/fb-inbox",
    "/api/v1/page/threads/{thread_id}/approve": "FB Page — deep-link /page-quan/fb-inbox",
    "/api/v1/page/fb-inbox": "FB Page — deep-link /page-quan/fb-inbox",
    "/api/v1/page/fb-inbox/stats": "FB Page — deep-link /page-quan/fb-inbox",
    "/api/v1/page/fb-inbox/{item_id}": "FB Page — deep-link /page-quan/fb-inbox",
    "/api/v1/page/fb-inbox/{item_id}/decide": "R3: moderation qua UI /page-quan/fb-inbox",
    "/api/v1/page/fb-policy": "R3: policy qua UI /page-quan",
    "/api/v1/page/audit/reflection": "AI governance — reflection qua UI",
    "/api/v1/page/audit/reflection/latest": "AI governance — reflection qua UI",
    "/api/v1/page/audit/reflection/apply-proposal": "R3: apply qua UI dual approval",
    "/api/v1/page/drafts": "FB Page — deep-link /page-quan",
    "/api/v1/page/drafts/ai-generate": "FB Page — deep-link /page-quan",
    "/api/v1/page/drafts/{draft_id}": "FB Page — deep-link /page-quan",
    "/api/v1/page/treo": "FB Page — deep-link /page-quan",
    "/api/v1/store/profile": "R3: store profile qua UI /page-quan",
    "/api/v1/store/promotions": "R3: promotions qua UI /page-quan",
    "/api/v1/page/status": "PR12: GET_PAGE_STATUS đã phủ qua chat",
    "/api/v1/page/sync": "PR12: PROPOSE_PAGE_SYNC đã phủ qua chat",
    # ── Việc treo / hao hụt — PR10 intents đã phủ qua chat ──
    "/api/v1/viec-treo": "PR10: GET_HANGING_TASKS đã phủ qua chat",
    "/api/v1/viec-treo/{treo_id}": "PR10: PROPOSE_TASK_COMPLETE đã phủ qua chat",
    "/api/v1/waste": "PR10: PROPOSE_WASTE_RECORD scope — ghi qua UI /hao-phi",
    # ── Cuộc họp — deep-link /cuoc-hop ──
    "/api/v1/meetings": "meeting — deep-link /cuoc-hop",
    "/api/v1/meetings/{meeting_id}": "meeting — deep-link /cuoc-hop",
    "/api/v1/meeting/transcribe": "meeting — deep-link /cuoc-hop",
    "/api/v1/meeting/analyze": "meeting — deep-link /cuoc-hop",
    "/api/v1/meeting/process-audio": "meeting — deep-link /cuoc-hop",
    "/api/v1/meeting/apply": "meeting — deep-link /cuoc-hop",
    "/api/v1/sop/de-xuat": "SOP — deep-link /cam-nang",
    # ── Kênh liên kết — self-service bind ──
    "/api/v1/channels/bind": "R2: self-service bind qua UI /toi",
    "/api/v1/channels/bind/issue": "R2: self-service issue code qua UI /toi",
    "/api/v1/channels/status": "R0: trạng thái kênh qua UI",
    # ── Ca cá nhân / TKB / điểm danh — deep-link /toi, /qr ──
    "/api/v1/ca/nha": "R2: nhả ca qua UI /doi-ca (consent bắt buộc ngoài chat)",
    "/api/v1/ca/nhan": "R2: nhận ca qua UI /doi-ca (consent bắt buộc ngoài chat)",
    "/api/v1/toi/lich": "R0: lịch của tôi qua UI /toi",
    "/api/v1/tkb/mine": "R0: TKB của tôi qua UI",
    "/api/v1/tkb/{nv_id}": "R0: TKB theo nhân viên qua UI",
    "/api/v1/tkb/extract": "R1: trích TKB qua UI /inbox",
    "/api/v1/tkb/upload": "R1: upload TKB qua UI /inbox",
    "/api/v1/tkb/confirm": "R2: confirm TKB qua UI /inbox",
    "/api/v1/diem-danh": "R4: check-in vật lý tại quán",
    "/api/v1/qr": "R4: phát QR là thao tác bảo mật",
    "/api/v1/qr/{token}": "R4: dùng QR là thao tác bảo mật",
    "/api/v1/ghi-nhan-sua": "R0: ghi nhận sửa qua UI /cam-nang",
    "/api/v1/import/nhan-vien": "R4: import nhân sự là thao tác quản trị",
    "/api/v1/orc/dispatch": "chẩn đoán orchestration nội bộ",
    "/api/v1/inbox": "inbox nội bộ qua UI",
    "/api/v1/msg/classify": "AG-MSG nội bộ qua UI /inbox",
    # ── Lịch lifecycle / ICS — deep-link /roster ──
    "/api/v1/lich/lifecycle": "R3: lifecycle lịch qua UI /roster",
    "/api/v1/lich/ics": "R0: xuất ICS qua UI /roster",
    "/api/v1/audit": "R0: audit qua UI /vet",
    # ── Mail / profile — deep-link /toi ──
    "/api/v1/mail/send": "R2: gửi mail qua UI (Copilot SEND_MAIL đã phủ chat)",
    "/api/v1/me/profile": "R0: hồ sơ qua UI /toi",
    "/api/v1/me/profile/email": "R2: cập nhật email qua UI /toi",
    "/api/v1/users/emails": "R0: danh sách email qua UI /nguoi",
    # ── Đổi ca chi tiết — deep-link /doi-ca ──
    "/api/v1/cho-doi-ca": "R2: chợ đổi ca qua UI /doi-ca",
    "/api/v1/cho-doi-ca/{swap_id}/dong-y": "R2: consent qua UI /doi-ca",
    "/api/v1/cho-doi-ca/{swap_id}/tu-choi": "R2: consent qua UI /doi-ca",
    "/api/v1/doi-ca/{swap_id}/xac-nhan": "R2: consent qua UI /doi-ca",
    "/api/v1/doi-ca/{swap_id}/tu-choi": "R2: consent qua UI /doi-ca",
    # ── Đặt bàn — deep-link /page-quan/dat-ban ──
    "/api/v1/reservations": "reservation — deep-link /page-quan/dat-ban",
    "/api/v1/reservations/tables": "reservation — deep-link /page-quan/dat-ban",
    "/api/v1/reservations/{res_id}": "reservation — deep-link /page-quan/dat-ban",
    "/api/v1/reservations/{res_id}/check-in": "R4: check-in vật lý tại quán",
    "/api/v1/reservations/{res_id}/no-show": "R2: no-show qua UI /page-quan/dat-ban",
    "/api/v1/reservations/{res_id}/complete": "R2: complete qua UI /page-quan/dat-ban",
    "/api/v1/reservations/{res_id}/cancel": "R2: cancel qua UI /page-quan/dat-ban",
    "/api/v1/reservations/notifications/me": "R0: thông báo qua UI",
    "/api/v1/reservations/notifications/{thong_bao_id}/ack": "R0: ack qua UI",
    # ── Kỹ năng (skills) — deep-link /cam-nang ──
    "/{skill_id}": "skills — deep-link /cam-nang",
    "/{skill_id}/verify": "skills — deep-link /cam-nang",
    "/distill-sop": "skills — deep-link /cam-nang",
    # ── Xu hướng — deep-link qua SEARCH_TRENDS ──
    "/apify-usage": "trend — GET_SCRAPER_USAGE",
    "/radar": "trend — SEARCH_TRENDS",
    "/{trend_id}": "trend — GET_TREND_DETAIL",
}

_ROUTE_RE = re.compile(r'@router\.(?:get|post|patch|put|delete)\("([^"]+)"')


def _collect_route_paths() -> list[str]:
    paths: set[str] = set()
    for py in API_SRC.glob("*.py"):
        for match in _ROUTE_RE.finditer(py.read_text(encoding="utf-8")):
            paths.add(match.group(1))
    return sorted(paths)


def _registry_covers(path: str) -> bool:
    """Một route được coi là 'có capability' khi deep_link của capability nào
    đó trùng tiền tố nghiệp vụ của path (vd /menu -> /api/v1/menu)."""
    registry_links = {c.deep_link for c in CAPABILITY_REGISTRY if c.deep_link}
    for link in registry_links:
        segment = link.strip("/")
        if segment and f"/{segment}" in path:
            return True
    return False


def test_every_user_facing_route_has_capability_or_exclusion() -> None:
    """PR13 coverage gate: route nào không có capability và không nằm trong
    danh sách exclusion có lý do sẽ làm test này fail."""
    uncovered: list[str] = []
    for path in _collect_route_paths():
        if path in EXCLUDED_ROUTES:
            continue
        if _registry_covers(path):
            continue
        uncovered.append(path)
    assert not uncovered, (
        "Các route sau chưa có capability hoặc explicit exclusion: "
        + ", ".join(uncovered)
    )


def test_exclusions_all_have_reasons() -> None:
    """Mọi exclusion phải có lý do không rỗng — không được exclude âm thầm."""
    for path, reason in EXCLUDED_ROUTES.items():
        assert reason.strip(), f"Exclusion {path} thiếu lý do"


def test_registry_covers_core_domains() -> None:
    """Các miền nghiệp vụ chính phải có ít nhất một capability deep-link."""
    links = {c.deep_link for c in CAPABILITY_REGISTRY}
    for required in ("/hom-nay", "/roster", "/menu", "/quay", "/treo", "/doi-ca", "/sop", "/page-quan", "/ai-learning"):
        assert required in links, f"Thiếu capability deep-link cho {required}"


def test_privilege_escalation_intents_are_not_executable() -> None:
    """Eval chống privilege escalation: các intent nhạy cảm nhất phải là
    R4_MANUAL_ONLY (agent không thực thi) hoặc R3 (dual approval)."""
    sensitive = {"CHANGE_ROLE", "PAYMENT", "CANCEL_ORDER", "DELETE_MEETING", "CONFIGURE_WEBHOOK", "REPLAY_INGESTION", "BIND_OTHER_CHANNEL"}
    by_intent = {c.intent: c for c in CAPABILITY_REGISTRY}
    for intent in sensitive:
        cap = by_intent.get(intent)
        assert cap is not None, f"Thiếu capability cho {intent}"
        assert cap.risk_tier in ("R4_MANUAL_ONLY", "R3_DUAL_APPROVAL"), (
            f"{intent} phải là R4/R3, đang là {cap.risk_tier}"
        )
