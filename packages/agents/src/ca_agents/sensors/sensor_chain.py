"""SensorChain — chuỗi cảm biến JEV + RegexSensor fallback (kế hoạch §5 mở rộng).

Luồng:
  1. Gọi JevSensor (nếu đã bật + có API key).
  2. Nếu JEV ok=True → dùng signals của JEV.
  3. Nếu JEV ok=False vì lỗi transient (timeout/5xx/429/schema) → gọi RegexSensor
     làm fallback. Đánh dấu `fallback_used=True` để audit phân biệt.
  4. Nếu JEV tắt hẳn (chưa cấu hình) → gọi RegexSensor bình thường (source="regex").

Khi cả JEV lẫn Regex đều không thể chạy (điều cực hiếm) → trả `both_failed=True`;
tầng gọi chịu trách nhiệm fail-closed.

Nguyên tắc đơn điệu (kế hoạch JEV v2 §3.2):
  - Với mỗi tên signal chung, lấy `max(jev_value, regex_value)`.
  - Không bao giờ giảm signal vì fallback.
  - Regex luôn ok=True (không I/O) → đảm bảo ít nhất một lưới an toàn.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ca_agents.sensors.port import SensorResult, Signal
from ca_agents.sensors.regex_sensor import RegexSensor


@dataclass(frozen=True)
class CombinedResult:
    """Kết quả đã ghép từ JEV và/hoặc RegexSensor.

    `source` cho biết cảm biến nào được dùng:
    - "jev"             : JEV thành công, Regex không chạy thêm.
    - "regex"           : JEV tắt hẳn (chưa bật), chỉ Regex chạy.
    - "regex_fallback"  : JEV bật nhưng lỗi → Regex thay thế.
    - "both"            : Cả hai chạy; signal là max() theo từng axis.
    - "none"            : Cả hai thất bại (cực hiếm).
    """

    signals: dict[str, Signal]
    source: str
    jev_ok: bool
    jev_failed: bool        # JEV đã bật nhưng bị lỗi transient
    fallback_used: bool     # Regex được dùng thay JEV do JEV lỗi
    both_failed: bool = False  # Cả hai đều không chạy được


def _float_value(sig: Signal) -> float:
    """Lấy giá trị float của Signal để so sánh max (đơn điệu)."""
    v = sig.value
    if isinstance(v, float):
        return v
    if isinstance(v, int):
        return float(v)
    # kind="choice": không thể max bằng số → giữ nguyên, không merge
    return -1.0


def _merge_signals(
    primary: Mapping[str, Signal],
    secondary: Mapping[str, Signal],
) -> dict[str, Signal]:
    """Ghép hai tập signal theo nguyên tắc đơn điệu (max).

    - Signal có trong cả hai → lấy cái có value cao hơn (float).
    - Signal chỉ có ở một bên → giữ nguyên.
    - Signal kiểu "choice" → ưu tiên primary (không thể max bằng số).
    """
    merged: dict[str, Signal] = dict(secondary)
    for name, sig in primary.items():
        if name not in merged:
            merged[name] = sig
        else:
            existing = merged[name]
            if sig.kind == "choice" or existing.kind == "choice":
                # choice: giữ primary (JEV hoặc cái được gọi trước)
                merged[name] = sig
            else:
                merged[name] = sig if _float_value(sig) >= _float_value(existing) else existing
    return merged


@dataclass
class SensorChain:
    """Chuỗi cảm biến: JEV → fallback RegexSensor.

    Dùng chung cho fb_moderation, ag_supervisor, ag_voc, ag_msg.

    Khởi tạo:
        chain = SensorChain(jev_sensor=jev)          # RegexSensor tự động tạo
        chain = SensorChain(jev_sensor=jev, regex_sensor=custom_regex)
        chain = SensorChain()                         # chỉ Regex (JEV chưa bật)
    """

    jev_sensor: Any | None = None   # JevSensor | None
    regex_sensor: RegexSensor = field(default_factory=RegexSensor)

    def evaluate(
        self,
        text: str,
        schema_id: str,
        questions: Mapping[str, Any] | None = None,
    ) -> CombinedResult:
        """Đánh giá text qua JEV rồi ghép với Regex fallback.

        `questions` được truyền thẳng cho JevSensor (bắt buộc nếu JEV bật).
        RegexSensor bỏ qua `questions` (tất định theo keyword).
        """
        state = {"noi_dung_khach": text}

        # ── Regex luôn chạy sẵn (tất định, không I/O, luôn ok=True) ──────────
        regex_result: SensorResult = self.regex_sensor.evaluate(state, schema_id, questions)

        # ── JEV ──────────────────────────────────────────────────────────────
        if self.jev_sensor is None:
            # JEV chưa được cấu hình → chỉ Regex
            return CombinedResult(
                signals=dict(regex_result.signals),
                source="regex",
                jev_ok=False,
                jev_failed=False,
                fallback_used=False,
            )

        jev_result: SensorResult = self.jev_sensor.evaluate(state, schema_id, questions)

        if jev_result.ok:
            # JEV thành công → ghép JEV + Regex (đơn điệu: max)
            merged = _merge_signals(
                primary=dict(jev_result.signals),
                secondary=dict(regex_result.signals),
            )
            return CombinedResult(
                signals=merged,
                source="both",
                jev_ok=True,
                jev_failed=False,
                fallback_used=False,
            )

        # JEV bật nhưng lỗi → Regex làm fallback
        # Phân biệt: JEV lỗi transient (jev_failed=True) vs JEV tắt (ok=False không lỗi)
        # JevSensor trả ok=False khi: disabled, no key, circuit open, hoặc lỗi thật.
        # Ta không có `jev_failed` trực tiếp từ SensorResult — dựa vào sensor state:
        # nếu sensor tồn tại (không None) mà ok=False → coi là lỗi transient.
        jev_failed = True  # sensor đã bật nhưng gọi không thành công

        if not regex_result.ok:
            # Regex cũng không chạy (không xảy ra trong thực tế vì Regex luôn ok)
            return CombinedResult(
                signals={},
                source="none",
                jev_ok=False,
                jev_failed=jev_failed,
                fallback_used=True,
                both_failed=True,
            )

        return CombinedResult(
            signals=dict(regex_result.signals),
            source="regex_fallback",
            jev_ok=False,
            jev_failed=jev_failed,
            fallback_used=True,
        )
