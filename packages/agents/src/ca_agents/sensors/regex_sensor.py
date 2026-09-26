"""RegexSensor — bọc lại mã regex/quy tắc cũ thành một SignalSensor.

Nguyên tắc đơn điệu (kế hoạch JEV v2 §3.2): regex là lưới an toàn rẻ, tất định,
độ chính xác cao. Jev chỉ được *thêm* leo thang, không bao giờ *gỡ* leo thang
do regex. RegexSensor luôn `ok=True` (không I/O, không lỗi mạng).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ca_agents.fb_policy import (
    ASK_HUMAN_KEYWORDS,
    HEALTH_KEYWORDS,
    HOSTILE_KEYWORDS,
    LEGAL_KEYWORDS,
    _has_any,
)
from ca_agents.guardrails import normalize_text
from ca_agents.sensors.port import SensorResult, Signal

# Phiên bản bộ câu hỏi của RegexSensor (tất định, không đổi trừ khi sửa keyword).
REGEX_SCHEMA_VERSION = "regex-1.0.0"
REGEX_MODEL_VERSION = "regex-deterministic"


@dataclass(frozen=True)
class RegexSensor:
    """Cảm biến tất định dựa trên từ khóa của fb_policy.

    Trả về các tín hiệu `noul` (xác suất 0/1) cho các trục an toàn:
    nguy_co_suc_khoe, de_doa_phap_ly_truyen_thong, muc_gay_gat (score 0/1),
    doi_gap_nguoi_that, de_doa_thu_dich.
    """

    def evaluate(
        self,
        state: Mapping[str, object],
        schema_id: str,
        questions: Mapping[str, object] | None = None,
    ) -> SensorResult:
        text = str(state.get("noi_dung_khach", ""))
        norm = normalize_text(text)

        health = 1.0 if _has_any(norm, HEALTH_KEYWORDS) else 0.0
        legal = 1.0 if _has_any(norm, LEGAL_KEYWORDS) else 0.0
        ask_human = 1.0 if _has_any(norm, ASK_HUMAN_KEYWORDS) else 0.0
        hostile = 1.0 if _has_any(norm, HOSTILE_KEYWORDS) else 0.0
        # score 0-based: 0 = bình thường, 1 = gay gắt (có từ khóa thù địch)
        hostility_score = 1.0 if hostile else 0.0

        signals: dict[str, Signal] = {
            "nguy_co_suc_khoe": Signal(kind="noul", value=health),
            "de_doa_phap_ly_truyen_thong": Signal(kind="noul", value=legal),
            "doi_gap_nguoi_that": Signal(kind="noul", value=ask_human),
            "muc_gay_gat": Signal(kind="score", value=hostility_score),
            "de_doa_thu_dich": Signal(kind="noul", value=hostile),
        }
        return SensorResult(
            signals=signals,
            model_version=REGEX_MODEL_VERSION,
            schema_version=REGEX_SCHEMA_VERSION,
            latency_ms=0,
            ok=True,
        )