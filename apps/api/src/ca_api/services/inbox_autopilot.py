"""Tự động duyệt Hộp thư ràng buộc — AI quyết định thay quản lý.

Trước đây `/inbox` yêu cầu quản lý bấm "Duyệt"/"Từ chối" cho từng yêu cầu
(xin nghỉ, báo trễ, đổi ca…). Theo yêu cầu vận hành mới: AI tự động duyệt và
tự động chạy lại lịch — trang Hộp thư ràng buộc chỉ còn để XEM (yêu cầu → AI
quyết định → kết quả xếp lịch), không còn nút duyệt tay.

Chính sách quyết định (tất định, không LLM — an toàn để tự động hoá):
  - `xin_nghi` / `bao_tre` / `cap_nhat_tkb`  → luôn DUYỆT, tự động xếp lại lịch
    (ràng buộc áp ngay vào lượt giải tiếp theo).
  - `doi_ca` / `nhan_ca` → DUYỆT nếu tìm được ứng viên phù hợp (điểm > 0) từ
    cùng thuật toán xếp hạng đang hiển thị trên trang (`find_swap_candidates`);
    áp dụng ngay (`ap_dat=True`) vì AI đã chọn người, không cần đợi đối tác xác
    nhận thủ công. Không tìm được ứng viên nào → TỪ CHỐI, ghi rõ lý do.
  - Còn lại (loại chưa biết) → DUYỆT, chỉ ghi nhận (không đổi lịch).
  - Lịch tuần đã khoá (`da_duyet`/`da_cong_bo`/`da_dong`) → vẫn duyệt yêu cầu,
    nhưng việc xếp lại lịch bị `_decide_inbox_item` tự bỏ qua và ghi rõ
    "chờ lượt xếp lịch sau" (không sửa lịch đã công bố).

Được gọi từ hai nơi (`main.py`/`channels.py` gọi `auto_process`):
  1. Ngay khi một yêu cầu mới được ghi vào hộp thư (kênh nhắn tin, copilot,
     cuộc họp) — quyết định gần như lập tức.
  2. Mỗi lần `GET /api/v1/inbox/rang-buoc` được tải — quét lại phần còn sót
     (an toàn cho các luồng ghi không gọi autopilot trực tiếp).
"""

from __future__ import annotations

from typing import Any

from ca_api.persist import kv_get

AUTOPILOT_ACTOR = "ag_scheduler"


def _pick_swap_candidate(item: dict[str, Any]) -> str | None:
    """Ứng viên tốt nhất cho một yêu cầu đổi/nhận ca — cùng thuật toán đang
    hiển thị ở trang Hộp thư (`goi_y_doi_tac`), không suy diễn thêm."""
    # Import muộn để tránh vòng import (sprint45 định nghĩa router HTTP, còn
    # phụ thuộc vào các hàm nội bộ này để tính ứng viên).
    from ca_api.interfaces.http.sprint45 import _get_swap_candidates_for_item

    try:
        candidates = _get_swap_candidates_for_item(item)
    except Exception:
        return None
    top = next((c for c in candidates if (c.get("score") or 0) > 0), None)
    return str(top["nv_id"]) if top else None


def auto_process(store_id: str = "quan_01") -> list[dict[str, Any]]:
    """Quét mọi mục `cho_duyet` trong hộp thư và để AI quyết định ngay.

    Trả về danh sách các quyết định đã đưa ra trong lượt gọi này (rỗng nếu
    không còn gì chờ) — dùng để log/kiểm thử, không bắt buộc phía gọi phải
    đọc giá trị trả về."""
    from ca_api.interfaces.http.sprint45 import _decide_inbox_item

    items = kv_get("inbox_rang_buoc", [])
    if not isinstance(items, list):
        return []
    pending = [it for it in items if isinstance(it, dict) and it.get("trang_thai") == "cho_duyet"]
    decisions: list[dict[str, Any]] = []

    for item in pending:
        item_id = str(item.get("id") or "")
        if not item_id:
            continue
        y_dinh = str(item.get("y_dinh") or "")
        try:
            if y_dinh in {"doi_ca", "nhan_ca"}:
                rb = item.get("rang_buoc") or {}
                ca_id = str(rb.get("ca_id") or "").strip()
                candidate = _pick_swap_candidate(item)
                if ca_id and candidate:
                    result = _decide_inbox_item(
                        item_id,
                        quyet_dinh="duyet",
                        role=AUTOPILOT_ACTOR,
                        store_id=store_id,
                        actor_id=AUTOPILOT_ACTOR,
                        ca_id=ca_id,
                        doi_tac_nv_id=candidate,
                        ap_dat=True,
                        ly_do="AI tự động chọn người phù hợp nhất và duyệt ngay.",
                    )
                else:
                    result = _decide_inbox_item(
                        item_id,
                        quyet_dinh="tu_choi",
                        role=AUTOPILOT_ACTOR,
                        store_id=store_id,
                        actor_id=AUTOPILOT_ACTOR,
                        ly_do="Không tìm được người phù hợp để tự động đổi ca — cần quản lý can thiệp thủ công.",
                    )
            elif y_dinh in {"xin_nghi", "bao_tre", "cap_nhat_tkb"}:
                result = _decide_inbox_item(
                    item_id,
                    quyet_dinh="duyet",
                    role=AUTOPILOT_ACTOR,
                    store_id=store_id,
                    actor_id=AUTOPILOT_ACTOR,
                    tu_dong_xep_lich=True,
                    ly_do="AI tự động duyệt và áp vào lượt xếp lịch tiếp theo.",
                )
            else:
                result = _decide_inbox_item(
                    item_id,
                    quyet_dinh="duyet",
                    role=AUTOPILOT_ACTOR,
                    store_id=store_id,
                    actor_id=AUTOPILOT_ACTOR,
                    ly_do="AI tự động ghi nhận.",
                )
            decisions.append({"id": item_id, "y_dinh": y_dinh, "ok": True, "result": result})
        except Exception as exc:  # Một mục lỗi không được chặn các mục khác.
            decisions.append({"id": item_id, "y_dinh": y_dinh, "ok": False, "error": str(exc)})

    return decisions
