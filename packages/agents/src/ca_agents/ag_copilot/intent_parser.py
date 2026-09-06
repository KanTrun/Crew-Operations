"""Intent Parser & Prompt Injection Guard for AG-COPILOT.

Classifies natural language input into 7 whitelisted intents with confidence scoring.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Intent enum string constants
SCHEDULE_SOLVE = "SCHEDULE_SOLVE"
APPROVE_SHIFT_SWAP = "APPROVE_SHIFT_SWAP"
GENERATE_DAILY_BRIEF = "GENERATE_DAILY_BRIEF"
QUERY_SOP = "QUERY_SOP"
ANALYZE_WASTE = "ANALYZE_WASTE"
CREATE_RULE_PROPOSAL = "CREATE_RULE_PROPOSAL"
INVENTORY_RESTOCK_CHECK = "INVENTORY_RESTOCK_CHECK"
SEND_MAIL = "SEND_MAIL"
# PR9 read intents — chỉ đọc, không side effect
GET_MY_PROFILE = "GET_MY_PROFILE"
LIST_STAFF = "LIST_STAFF"
QUERY_MENU = "QUERY_MENU"
GET_INVENTORY = "GET_INVENTORY"
GET_SHIFT_SWAPS = "GET_SHIFT_SWAPS"
GET_HANGING_TASKS = "GET_HANGING_TASKS"
GET_HANDOVERS = "GET_HANDOVERS"
# PR10 self-service mutating intents — R2_CONFIRM
PROPOSE_HANGING_TASK = "PROPOSE_HANGING_TASK"
PROPOSE_TASK_COMPLETE = "PROPOSE_TASK_COMPLETE"
PROPOSE_CONSUMPTION_RECORD = "PROPOSE_CONSUMPTION_RECORD"
# PR11 admin mutating intents — R2_CONFIRM (quan_ly/chu_quan)
PROPOSE_MENU_UPDATE = "PROPOSE_MENU_UPDATE"
PROPOSE_ORDER_TRANSITION = "PROPOSE_ORDER_TRANSITION"
PROPOSE_PIN = "PROPOSE_PIN"
# PR12 external channel intents
GET_PAGE_STATUS = "GET_PAGE_STATUS"
PROPOSE_PAGE_SYNC = "PROPOSE_PAGE_SYNC"
# PR13 read intents bổ sung — lịch tuần / ca cá nhân / ràng buộc chờ duyệt
GET_SCHEDULE = "GET_SCHEDULE"
GET_MY_SHIFTS = "GET_MY_SHIFTS"
GET_CONSTRAINT_CANDIDATES = "GET_CONSTRAINT_CANDIDATES"
# PR10 còn lại (R2_CONFIRM): xác nhận TKB, đồng ý đổi ca, ghi bàn giao ca
PROPOSE_TKB_CONFIRM = "PROPOSE_TKB_CONFIRM"
PROPOSE_SWAP_CONSENT = "PROPOSE_SWAP_CONSENT"
PROPOSE_HANDOVER = "PROPOSE_HANDOVER"
OUT_OF_SCOPE = "OUT_OF_SCOPE"
# Patterns detecting attempts to bypass two-phase approval
_BYPASS_PATTERNS = [
    r"bỏ\s*qua\s*(bước\s*)?duyệt",
    r"ghi\s*luôn\s*(không\s*cần\s*(hỏi|duyệt|xác\s*nhận))?",
    r"tự\s*động\s*duyệt\s*hộ",
    r"xóa\s*hết\s*lịch.*ghi\s*đè\s*luôn",
    r"override\s*(auth|permission|approval|security)",
    r"ignore\s*(all\s*)?(previous\s*)?(instructions|rules)",
    r"từ\s*giờ\s*bạn\s*là\s*(admin|root|system|developer)",
]
_BYPASS_REGEX = re.compile("|".join(_BYPASS_PATTERNS), re.IGNORECASE)

# Intent matching keywords
# PR9 read intents đặt ĐẦU danh sách: cụm hỏi đọc cụ thể ("đổi ca nào",
# "việc treo") phải thắng từ chung của mutating intents ("đổi ca").
_INTENT_KEYWORDS: list[tuple[str, list[str], float]] = [
    # PR10 còn lại — đặt ĐẦU danh sách: cụm hành động cụ thể ("đồng ý đổi ca
    # sw_xxx") phải thắng từ chung của GET_SHIFT_SWAPS/APPROVE_SHIFT_SWAP
    # ("đổi ca"), và "bàn giao ca" phải thắng GET_HANDOVERS ("bàn giao").
    (
        PROPOSE_SWAP_CONSENT,
        ["đồng ý đổi ca", "dong y doi ca", "đồng ý nhận ca", "dong y nhan ca", "xác nhận nhận ca", "xac nhan nhan ca", "em đồng ý", "em dong y", "tôi đồng ý", "toi dong y"],
        0.9,
    ),
    (
        PROPOSE_TKB_CONFIRM,
        ["xác nhận tkb", "xac nhan tkb", "xác nhận lịch bận", "xac nhan lich ban", "tkb bận", "tkb ban", "gán tkb", "gan tkb", "chốt tkb", "chot tkb"],
        0.9,
    ),
    (
        PROPOSE_HANDOVER,
        ["bàn giao ca", "ban giao ca", "ghi bàn giao", "ghi ban giao", "soạn bàn giao", "soan ban giao", "gửi bàn giao", "gui ban giao"],
        0.9,
    ),
    (
        GET_SHIFT_SWAPS,
        ["đổi ca nào", "doi ca nao", "yêu cầu đổi ca nào", "yeu cau doi ca nao", "chợ đổi ca", "cho doi ca", "danh sách đổi ca", "danh sach doi ca"],
        0.9,
    ),
    (
        GET_MY_PROFILE,
        ["hồ sơ của tôi", "ho so cua toi", "tôi là ai", "toi la ai", "thông tin của tôi", "thong tin cua toi"],
        0.9,
    ),
    (
        LIST_STAFF,
        ["danh sách nhân", "danh sach nhan", "nhân sự", "nhan su", "ai làm", "ai lam", "ai đang làm", "ai dang lam"],
        0.9,
    ),
    # PR11 admin mutating — đặt TRƯỚC QUERY_MENU: "sửa giá món X" (hành động)
    # phải thắng "menu"/"giá món" (đọc).
    (
        PROPOSE_MENU_UPDATE,
        ["sửa giá", "sua gia", "đổi giá", "doi gia", "cập nhật giá", "cap nhat gia", "ẩn món", "an mon", "bỏ món", "bo mon", "thêm món", "them mon", "thêm món mới", "them mon moi"],
        0.9,
    ),
    (
        PROPOSE_ORDER_TRANSITION,
        ["chuyển đơn", "chuyen don", "đơn đang pha", "don dang pha", "hủy đơn", "huy don", "xác nhận đơn", "xac nhan don", "đơn xong", "don xong"],
        0.9,
    ),
    (
        PROPOSE_PIN,
        ["ghim ca", "ghim ca", "pin ca", "ghim lịch", "ghim lich"],
        0.9,
    ),    # PR12 external channels
    (
        PROPOSE_PAGE_SYNC,
        ["đồng bộ page", "dong bo page", "sync page", "đồng bộ fanpage", "dong bo fanpage", "kéo tin nhắn page", "keo tin nhan page"],
        0.9,
    ),
    (
        GET_PAGE_STATUS,
        ["trạng thái page", "trang thai page", "page có sống", "page co song", "fanpage còn nối", "fanpage con noi", "kết nối page", "ket noi page"],
        0.9,
    ),    (
        QUERY_MENU,
        ["menu", "món gì", "mon gi", "có bán", "co ban", "giá món", "gia mon", "bảng giá", "bang gia"],
        0.9,
    ),
    # PR10 self-service mutating — đặt TRƯỚC GET_HANGING_TASKS: cụm hành động
    # ("đánh dấu xong việc treo", "treo việc X") phải thắng cụm đọc ("việc treo").
    (
        PROPOSE_TASK_COMPLETE,
        ["đánh dấu xong việc treo", "danh dau xong viec treo", "xong việc treo", "xong viec treo", "hoàn thành việc treo", "hoan thanh viec treo"],
        0.9,
    ),
    (
        PROPOSE_HANGING_TASK,
        ["treo việc", "treo viec", "treoviệc", "treoviec", "tạo việc treo", "tao viec treo", "ghi việc treo", "ghi viec treo"],
        0.9,
    ),
    (
        PROPOSE_CONSUMPTION_RECORD,
        ["ghi tiêu thụ", "ghi tieu thu", "ghi tồn kho", "ghi ton kho", "nhập tiêu thụ", "nhap tieu thu"],
        0.9,
    ),
    (
        GET_HANGING_TASKS,
        ["việc treo", "viec treo", "treo việc nào", "treo viec nao", "công việc đang treo", "cong viec dang treo"],
        0.9,
    ),
    (
        GET_HANDOVERS,
        ["bàn giao", "ban giao", "lịch sử sửa", "lich su sua", "bản ghi sửa", "ban ghi sua"],
        0.9,
    ),
    # PR13 read — ràng buộc chờ duyệt / lịch cá nhân phải thắng từ chung của
    # mutating intents ("đổi ca"), nhưng SCHEDULE_SOLVE ("xếp lịch") phải thắng
    # GET_SCHEDULE nên GET_SCHEDULE được đặt SAU SCHEDULE_SOLVE.
    (
        GET_MY_SHIFTS,
        ["lịch của tôi", "lich cua toi", "ca của tôi", "ca cua toi", "lịch làm việc của tôi", "lich lam viec cua toi", "ca của mình", "ca cua minh", "lịch tôi", "lich toi", "lịch của em", "lich cua em", "ca tôi làm", "ca toi lam"],
        0.9,
    ),
    (
        GET_CONSTRAINT_CANDIDATES,
        ["ràng buộc chờ duyệt", "rang buoc cho duyet", "ràng buộc nào", "rang buoc nao", "xin nghỉ chờ", "xin nghi cho", "inbox ràng buộc", "inbox rang buoc", "danh sách ràng buộc", "danh sach rang buoc", "ràng buộc chưa duyệt", "rang buoc chua duyet"],
        0.9,
    ),
    (
        SCHEDULE_SOLVE,
        ["xếp lịch", "xep lich", "chia ca", "xếp ca", "lên lịch", "chạy solver", "phân công ca", "tạo lịch"],
        0.92,
    ),
    (
        GET_SCHEDULE,
        ["xem lịch tuần", "xem lich tuan", "lịch tuần này", "lich tuan nay", "lịch làm việc", "lich lam viec", "xem lịch", "xem lich", "lịch ca", "lich ca", "roster"],
        0.9,
    ),
    (
        APPROVE_SHIFT_SWAP,
        ["đổi ca", "doi ca", "nhường ca", "nhận ca", "chuyển ca", "duyệt đổi ca", "yêu cầu đổi ca"],
        0.90,
    ),
    (
        GENERATE_DAILY_BRIEF,
        ["bản tin", "ban tin", "tin sáng", "tóm tắt đầu ngày", "tình hình hôm nay", "tình hình ca sáng"],
        0.95,
    ),
    (
        QUERY_SOP,
        ["quy trình", "quy trinh", "cẩm nang", "hướng dẫn", "mở quán", "đóng quán", "vệ sinh", "cách làm", "sop"],
        0.90,
    ),
    (
        ANALYZE_WASTE,
        ["hao hụt", "hao hut", "hàng hủy", "lãng phí", "sữa hỏng", "đổ bọt", "báo cáo hủy"],
        0.91,
    ),
    (
        CREATE_RULE_PROPOSAL,
        ["đề xuất luật", "luật mới", "cẩm nang sống", "tạo luật", "học luật", "thêm quy tắc"],
        0.90,
    ),
    (
        INVENTORY_RESTOCK_CHECK,
        ["kiểm kho", "tồn kho", "sắp hết hàng", "hết sữa", "đặt hàng", "nhập hàng", "ngưỡng tồn", "restock"],
        0.90,
    ),
    (
        SEND_MAIL,
        [
            "gửi mail",
            "gui mail",
            "gửi email",
            "gửi gmail",
            "email cho",
            "mail cho",
            "nhắn qua email",
            "gửi thông báo qua email",
            "soạn mail",
            "soan mail",
            "soạn email",
            "soan email",
            "soạn gmail",
            "soan gmail",
            "viết mail",
            "viet mail",
            "viết email",
            "viet email",
            "viết gmail",
            "viet gmail",
            "nhờ soạn mail",
            "nhờ viết mail",
        ],
        0.92,
    ),
]


@dataclass
class IntentParseResult:
    intent: str
    confidence: float
    params: dict[str, Any]
    clarification_needed: bool = False
    clarification_question: str | None = None
    security_flag: str | None = None


def _iso_week(d: Any) -> str:
    """Trả về ISO week dạng 'YYYY-Wnn'. Không hardcode."""
    from datetime import date

    if not isinstance(d, date):
        d = date.today()
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _add_week(d: Any, n: int = 1) -> Any:
    """Cộng n tuần (giữ nguyên kiểu date)."""
    from datetime import date, timedelta

    if not isinstance(d, date):
        d = date.today()
    return d + timedelta(weeks=n)


def _active_date(context: dict[str, Any]) -> Any:
    from datetime import date

    raw = str(context.get("active_date") or "").strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.today()


def parse_intent(message: str, context: dict[str, Any] | None = None) -> IntentParseResult:
    """Parse intent from user message with confidence rules and injection checks."""
    text = (message or "").strip()
    if not text:
        return IntentParseResult(
            intent=OUT_OF_SCOPE,
            confidence=0.0,
            params={},
            clarification_needed=False,
            security_flag="empty_message",
        )

    # 1. Security Check: Prompt Injection / Bypass Approval
    if _BYPASS_REGEX.search(text):
        return IntentParseResult(
            intent=OUT_OF_SCOPE,
            confidence=0.99,
            params={},
            clarification_needed=False,
            security_flag="bypass_approval_rejected",
        )

    context = context or {}
    recent_messages = [
        str(item).strip() for item in context.get("recent_messages", [])[-3:]
        if str(item).strip()
    ]
    recent_text = " ".join(recent_messages).lower()

    # 2. Check for vague / ambiguous input unless recent context supplies intent.
    lower = text.lower()
    if lower in ("xếp lịch", "xep lich", "xếp lịch đi", "lên lịch đi") and not any(
        keyword in recent_text for _, keywords, _ in _INTENT_KEYWORDS for keyword in keywords
    ):
        return IntentParseResult(
            intent=SCHEDULE_SOLVE,
            confidence=0.60,
            params={},
            clarification_needed=True,
            clarification_question="Dạ anh/chị muốn em xếp lịch cho tuần này hay tuần sau ạ?",
        )

    # 3. Match against Whitelisted Intents
    matched_intent = OUT_OF_SCOPE
    matched_conf = 0.3
    params: dict[str, Any] = {}

    for intent_name, keywords, base_conf in _INTENT_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                matched_intent = intent_name
                matched_conf = base_conf
                break
        if matched_intent != OUT_OF_SCOPE:
            break

    inferred_from_context = matched_intent == OUT_OF_SCOPE and bool(recent_messages)
    if inferred_from_context:
        for intent_name, keywords, base_conf in _INTENT_KEYWORDS:
            if any(kw in recent_text for kw in keywords):
                matched_intent = intent_name
                matched_conf = base_conf
                break

    # Extract common parameters
    if matched_intent == SCHEDULE_SOLVE:
        # Week detection (ISO week thực tế — không hardcode).
        active_date = _active_date(context)
        combined_lower = f"{recent_text} {lower}"
        tuan = _iso_week(active_date)
        if "tuần sau" in combined_lower or "tuan sau" in combined_lower:
            params["tuan"] = _iso_week(_add_week(active_date, 1))
        elif "tuần này" in combined_lower or "tuan nay" in combined_lower:
            params["tuan"] = tuan
        else:
            # Mặc định tuần sau (nhu cầu lập lịch phổ biến).
            params["tuan"] = _iso_week(_add_week(active_date, 1))
        # Preference detection
        lan_match = re.search(r"ưu\s*tiên\s*(\w+)\s*ca\s*(\w+)", lower)
        if lan_match:
            params["uu_tien_nhan_su"] = {lan_match.group(1).title(): f"ca_{lan_match.group(2)}"}

    elif matched_intent == QUERY_SOP:
        params["cau_hoi"] = text

    elif matched_intent == GENERATE_DAILY_BRIEF:
        params["ngay"] = _active_date(context).isoformat()

    elif matched_intent == ANALYZE_WASTE:
        params["khoang_ngay"] = "hom_nay"

    elif matched_intent == INVENTORY_RESTOCK_CHECK:
        params["nguong_canh_bao"] = 10.0

    elif matched_intent == SEND_MAIL:
        param_text = " ".join((*recent_messages, text)) if inferred_from_context else text
        current_lower = text.lower()
        current_has_recipient = bool(
            re.search(r"(?:@|\bnv_\d+\b|\b(?:minh|lan|hùng|hung)\b)", current_lower)
        )
        recipient_text = text if current_has_recipient else param_text
        recipient_lower = recipient_text.lower()
        # Direct email extraction
        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        found_emails = email_pattern.findall(recipient_text)

        # Trích xuất tên nhân viên thường gặp
        staff_map = {
            "minh": "nv_03",
            "lan": "nv_01",
            "hùng": "nv_02",
            "hung": "nv_02",
        }
        to_nv_ids: list[str] = []
        recip_names: list[str] = []
        for name, nv_id in staff_map.items():
            if re.search(r"\b" + re.escape(name) + r"\b", recipient_lower):
                if nv_id not in to_nv_ids:
                    to_nv_ids.append(nv_id)
                    recip_names.append(name.capitalize())

        # Trích xuất mã nv_XX nếu có
        for m in re.findall(r"\bnv_\d+\b", recipient_lower):
            if m not in to_nv_ids:
                to_nv_ids.append(m)
                recip_names.append(m.upper())

        params["raw_request"] = param_text
        params["to_nv_ids"] = to_nv_ids
        params["direct_emails"] = found_emails
        params["recipient_names"] = recip_names
        params["subject"] = param_text if len(param_text) <= 120 else param_text[:120]
        params["body"] = param_text

    elif matched_intent == PROPOSE_HANGING_TASK:
        # Trích nội dung việc treo: phần sau "treo việc"/"tạo việc treo".
        m = re.search(
            r"(?:treo\s*việc|treo\s*viec|tạo\s*việc\s*treo|tao\s*viec\s*treo|ghi\s*việc\s*treo|ghi\s*viec\s*treo)\s*(?:là|la|:|—|-)?\s*(.+)",
            text,
            re.IGNORECASE,
        )
        noi_dung = (m.group(1).strip() if m else "").strip()
        params["noi_dung"] = noi_dung[:200]
        params["thieu_noi_dung"] = not noi_dung

    elif matched_intent == PROPOSE_TASK_COMPLETE:
        # Trích treo_id: dạng treo_<alnum> (hex từ route web hoặc test ID).
        m = re.search(r"\b(treo_[a-z0-9]{4,20})\b", text, re.IGNORECASE)
        params["treo_id"] = m.group(1).lower() if m else ""
        params["thieu_treo_id"] = not params["treo_id"]

    elif matched_intent == PROPOSE_CONSUMPTION_RECORD:
        # Trích: "<số lượng> <đơn vị?> <hàng>" hoặc "hàng <hàng> còn <số>".
        so_luong: float | None = None
        don_vi = "khay"
        hang = ""
        m = re.search(
            r"(\d+(?:[.,]\d+)?)\s*(hộp|hop|khay|gói|goi|chai|lon|túi|tui|kg|gram|g)?\s*(?:của\s*)?(.+)",
            text,
            re.IGNORECASE,
        )
        if m:
            so_luong = float(m.group(1).replace(",", "."))
            if m.group(2):
                don_vi = m.group(2).lower()
            hang = m.group(3).strip()[:60]
        params["so_luong"] = so_luong
        params["don_vi"] = don_vi
        params["hang"] = hang
        params["thieu_so_lieu"] = so_luong is None or not hang

    elif matched_intent == PROPOSE_MENU_UPDATE:
        # Trích: "sửa giá <món> thành <số>" | "ẩn món <món>" | "thêm món <món> giá <số>".
        gia: int | None = None
        an: bool | None = None
        ten_mon = ""
        m_gia = re.search(
            r"(?:sửa|sua|đổi|doi|cập\s*nhật|cap\s*nhat)\s*giá\s*(?:món\s*)?(.+?)\s*(?:thành|thanh|lên|len|:)\s*(\d+(?:[.,]\d+)?)",
            text,
            re.IGNORECASE,
        )
        m_an = re.search(r"(?:ẩn|an|bỏ|bo)\s*món\s*(.+)", text, re.IGNORECASE)
        m_them = re.search(
            r"(?:thêm|them)\s*món\s*(?:mới\s*|moi\s*)?(.+?)(?:\s*giá\s*|\s*gia\s*)(\d+(?:[.,]\d+)?)",
            text,
            re.IGNORECASE,
        )
        if m_gia:
            ten_mon = m_gia.group(1).strip()[:60]
            gia = int(float(m_gia.group(2).replace(",", ".")))
            an = False
        elif m_an:
            ten_mon = m_an.group(1).strip()[:60]
            an = True
        elif m_them:
            ten_mon = m_them.group(1).strip()[:60]
            gia = int(float(m_them.group(2).replace(",", ".")))
            an = False
        params["ten_mon"] = ten_mon
        params["gia"] = gia
        params["an"] = an
        params["thieu_thong_tin"] = not ten_mon or (gia is None and an is None)

    elif matched_intent == PROPOSE_ORDER_TRANSITION:
        # Trích don_id (dq_xxx) và trạng thái đích từ động từ.
        m_id = re.search(r"\b(dq_[a-z0-9]{4,20})\b", text, re.IGNORECASE)
        lower = text.lower()
        trang_thai = ""
        if re.search(r"(hủy|huy)\s*đơn|đơn.*(hủy|huy)", lower):
            trang_thai = "huy"
        elif re.search(r"(xong|hoàn\s*thành|hoan\s*thanh)", lower):
            trang_thai = "xong"
        elif re.search(r"(đang\s*pha|dang\s*pha|bắt\s*đầu\s*pha|bat\s*dau\s*pha)", lower):
            trang_thai = "dang_pha"
        params["don_id"] = m_id.group(1).lower() if m_id else ""
        params["trang_thai"] = trang_thai
        params["ly_do_huy"] = ""
        params["thieu_thong_tin"] = not params["don_id"] or not trang_thai

    elif matched_intent == PROPOSE_PIN:
        # Trích ca_id (w1_c01...), nv_id (nv_XX hoặc tên nhân viên), pinned.
        m_ca = re.search(r"\b([a-z]\d+_[a-z]\d{1,3})\b", text, re.IGNORECASE)
        lower = text.lower()
        pinned = not bool(re.search(r"(bỏ\s*ghim|bo\s*ghim|un\s*pin|gỡ\s*ghim|go\s*ghim)", lower))
        m_nv = re.search(r"\b(nv_\d+)\b", text, re.IGNORECASE)
        nv_id = m_nv.group(1).lower() if m_nv else ""
        if not nv_id:
            staff_map = {"minh": "nv_03", "lan": "nv_01", "hùng": "nv_02", "hung": "nv_02"}
            for name, nv in staff_map.items():
                if re.search(r"\b" + re.escape(name) + r"\b", lower):
                    nv_id = nv
                    break
        params["ca_id"] = m_ca.group(1).lower() if m_ca else ""
        params["nv_id"] = nv_id
        params["pinned"] = pinned
        params["thieu_thong_tin"] = not params["ca_id"] or not nv_id

    elif matched_intent == PROPOSE_TKB_CONFIRM:
        # Trích khoảng bận: "T2 07:00-12:00, T4 18:00-22:00" (thứ T2..T8/CN).
        khoang_ban: list[tuple[str, str, str]] = []
        for m in re.finditer(
            r"\b(T[2-8]|CN)\s+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})",
            text,
            re.IGNORECASE,
        ):
            thu = m.group(1).upper()
            khoang_ban.append((thu, m.group(2), m.group(3)))
        # nv_id: mặc định người nói (executor sẽ chốt ownership); cho phép
        # nv_XX hoặc tên nhân viên nếu quản lý xác nhận hộ.
        m_nv = re.search(r"\b(nv_\d+)\b", text, re.IGNORECASE)
        nv_id = m_nv.group(1).lower() if m_nv else ""
        if not nv_id:
            staff_map = {"minh": "nv_03", "lan": "nv_01", "hùng": "nv_02", "hung": "nv_02"}
            for name, nv in staff_map.items():
                if re.search(r"\b" + re.escape(name) + r"\b", lower):
                    nv_id = nv
                    break
        params["khoang_ban"] = khoang_ban
        params["nv_id"] = nv_id
        params["thieu_khoang_ban"] = not khoang_ban

    elif matched_intent == PROPOSE_SWAP_CONSENT:
        # Trích swap_id (sw_xxx) — thiếu ID thì tool fail-closed.
        m = re.search(r"\b(sw_[a-z0-9]{4,24})\b", text, re.IGNORECASE)
        params["swap_id"] = m.group(1).lower() if m else ""
        params["thieu_swap_id"] = not params["swap_id"]

    elif matched_intent == PROPOSE_HANDOVER:
        # Toàn bộ text là nội dung bàn giao (SBAR) — tool yêu cầu không rỗng.
        params["text"] = text[:2000]
        params["thieu_noi_dung"] = not text.strip()

    # 4. Confidence thresholds:
    # >= 0.75: regular
    # 0.5 <= conf < 0.75: clarification
    # < 0.5: OUT_OF_SCOPE
    if matched_conf >= 0.75:
        return IntentParseResult(
            intent=matched_intent,
            confidence=matched_conf,
            params=params,
            clarification_needed=False,
        )
    elif 0.5 <= matched_conf < 0.75:
        return IntentParseResult(
            intent=matched_intent,
            confidence=matched_conf,
            params=params,
            clarification_needed=True,
            clarification_question="Dạ anh/chị có thể nói rõ hơn thao tác cần hỗ trợ không ạ?",
        )
    else:
        return IntentParseResult(
            intent=OUT_OF_SCOPE,
            confidence=matched_conf,
            params={},
            clarification_needed=False,
        )
