"""Bảng quyết định tất định cho Fanpage Facebook (kế hoạch JEV v2 §4.2).

Nguyên tắc:
- `leo_thang = regex_hit OR jev_flag` (đơn điệu, §3.2). Regex luôn thắng.
- Jev lỗi (`not r.ok`) → thoái lui về phía con người (fail-closed, ADR-008),
  không thoái lui về "regex không thấy gì = an toàn".
- Tín hiệu mâu thuẫn (vd: `y_dinh = khen` nhưng `nguy_co_suc_khoe` cao) → leo thang.
- Ngưỡng theo từng hành động, chọn từ dữ liệu (§3.3). Giá trị khởi điểm.

Các hằng số ngưỡng là giá trị khởi điểm, phải hiệu chỉnh trên tập dữ liệu vàng (§7).
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum

from ca_agents.sensors.port import SensorResult, Signal

# Ngưỡng khởi điểm (kế hoạch §4.2). Hiệu chỉnh theo tập vàng.
HEALTH_RISK_THRESHOLD = 0.30
LEGAL_THREAT_THRESHOLD = 0.30
HOSTILITY_SCORE_THRESHOLD = 1.5
ASK_HUMAN_THRESHOLD = 0.50
SARCASM_THRESHOLD = 0.50
AUTO_REPLY_CONFIDENCE = 0.70
# Vùng xám cho noul (B2 review): tránh nhạy cảm với nhiễu quanh ngưỡng.
NOUL_GRAY_LOW = 0.25
NOUL_GRAY_HIGH = 0.35

# Intent được phép tự trả lời (whitelist). Chỉ tăng leo thang, không tự ý mở rộng.
AUTO_REPLY_WHITELIST = frozenset({"khen", "hoi_thong_tin", "dat_ban"})


class Route(Enum):
    ESCALATE_OWNER = "escalate_owner"
    ESCALATE_MANAGER = "escalate_manager"
    AUTO_REPLY_DRAFT = "auto_reply_draft"
    HUMAN_QUEUE = "human_queue"
    HUMAN_QUEUE_HOLDING_MSG = "human_queue_holding_msg"


def _noul(signals: Mapping[str, Signal], name: str) -> float:
    """Lấy giá trị xác suất của tín hiệu noul; thiếu → 0.0 (không leo thang)."""
    s = signals.get(name)
    if s is None or s.kind != "noul":
        return 0.0
    return float(s.value)


def _score(signals: Mapping[str, Signal], name: str) -> float:
    """Lấy giá trị score 0-based; thiếu → 0.0."""
    s = signals.get(name)
    if s is None or s.kind != "score":
        return 0.0
    return float(s.value)


def _choice(signals: Mapping[str, Signal], name: str) -> str:
    """Lấy nhãn choice; thiếu → ""."""
    s = signals.get(name)
    if s is None or s.kind != "choice":
        return ""
    return str(s.value)


def _choice_conf(signals: Mapping[str, Signal], name: str) -> float:
    """Lấy confidence của choice; thiếu → 0.0."""
    s = signals.get(name)
    if s is None or s.confidence is None:
        return 0.0
    return float(s.confidence)


def route_fb(regex_hit: bool, r: SensorResult) -> Route:
    """Bảng quyết định tất định cho Fanpage (kế hoạch §4.2)."""
    # Regex luôn thắng: chỉ thêm, không bớt (đơn điệu).
    if regex_hit:
        return Route.ESCALATE_OWNER

    # Jev lỗi → về phía con người (fail-closed).
    if not r.ok:
        return Route.HUMAN_QUEUE_HOLDING_MSG

    signals = r.signals

    # Sức khỏe / pháp lý: ngưỡng thấp (thà báo nhầm còn hơn bỏ sót).
    health = _noul(signals, "nguy_co_suc_khoe")
    legal = _noul(signals, "de_doa_phap_ly_truyen_thong")
    if health >= HEALTH_RISK_THRESHOLD or legal >= LEGAL_THREAT_THRESHOLD:
        return Route.ESCALATE_OWNER

    # Vùng xám cho noul (B2): không quyết định cứng, chuyển hàng đợi.
    if NOUL_GRAY_LOW <= health < NOUL_GRAY_HIGH or NOUL_GRAY_LOW <= legal < NOUL_GRAY_HIGH:
        return Route.HUMAN_QUEUE

    hostility = _score(signals, "muc_gay_gat")
    ask_human = _noul(signals, "doi_gap_nguoi_that")
    intent = _choice(signals, "y_dinh")
    sarcasm = _noul(signals, "co_ve_mia_mai")

    if (
        hostility >= HOSTILITY_SCORE_THRESHOLD
        or ask_human >= ASK_HUMAN_THRESHOLD
        or intent == "khieu_nai"
        or sarcasm >= SARCASM_THRESHOLD
    ):
        return Route.ESCALATE_MANAGER

    # Tự trả lời chỉ cho intent trong whitelist + confidence đủ cao + không nguy hại.
    if (
        intent in AUTO_REPLY_WHITELIST
        and _choice_conf(signals, "y_dinh") >= AUTO_REPLY_CONFIDENCE
        and health < 0.10
        and legal < 0.10
        and hostility < 0.75
    ):
        return Route.AUTO_REPLY_DRAFT

    return Route.HUMAN_QUEUE