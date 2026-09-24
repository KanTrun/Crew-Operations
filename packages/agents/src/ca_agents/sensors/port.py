"""SignalSensor port — Jev là cảm biến xác suất, không phải bộ điều phối (ADR-002).

Nguyên tắc (kế hoạch JEV v2 §3):
- Đầu ra của Jev là **dữ liệu đầu vào không tin cậy** cho code tất định.
- Máy trạng thái vẫn là bảng chuyển trạng thái viết bằng code:
  `(tín hiệu, ngưỡng) → chuyển trạng thái`.
- Jev **không bao giờ** chọn "trạng thái kế tiếp", "agent kế tiếp" hay "công cụ kế tiếp".
- Nguyên tắc đơn điệu: `leo_thang = regex_hit OR jev_flag` — Jev chỉ được *thêm*
  leo thang, không bao giờ *gỡ* leo thang do regex/quy tắc cũ.

Cổng này tách biệt khỏi `FreeTierRouter` (chọn nhà cung cấp sinh văn bản).
`SignalSensor` là một bước **trước** tầng sinh văn bản.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

# Kiểu primitive của Jev (System One). `noul` không có `confidence`.
SignalKind = Literal["choice", "score", "noul"]


@dataclass(frozen=True)
class Signal:
    """Một tín hiệu từ cảm biến.

    - `choice`: `value` là nhãn (str), `confidence` có thể có.
    - `score`: `value` là vị trí 0-based (float), `confidence` có thể có.
    - `noul`: `value` là xác suất 0–1 (float), `confidence` luôn None.
    """

    kind: SignalKind
    value: str | float
    confidence: float | None = None
    probabilities: Mapping[str, float] | None = None


@dataclass(frozen=True)
class SensorResult:
    """Kết quả đánh giá của một cảm biến trên một state.

    `ok=False` khi timeout / 5xx / 429 / schema lỗi / bị kill-switch tắt.
    Khi `ok=False`, `signals` rỗng và code tất định phải thoái lui về phía con người.
    """

    signals: Mapping[str, Signal]
    model_version: str
    schema_version: str
    latency_ms: int
    ok: bool


class SignalSensor(Protocol):
    """Hợp đồng cổng cảm biến. Triển khai: JevSensor, RegexSensor.

    `questions` là bản đồ câu hỏi System One (type/instructions/criteria) dùng
    cho lần đánh giá này. Cảm biến tất định (RegexSensor) có thể bỏ qua; cảm
    biến Jev gửi thẳng lên API. Mặc định `None` → dùng bộ câu hỏi của schema.
    """

    def evaluate(
        self,
        state: Mapping[str, object],
        schema_id: str,
        questions: Mapping[str, object] | None = None,
    ) -> SensorResult: ...