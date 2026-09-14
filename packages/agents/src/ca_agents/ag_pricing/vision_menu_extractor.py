"""Trích xuất bảng giá từ ảnh chụp menu bằng Vision AI (Qwen VL / Gemini).

Phase 2: rewrite để dùng v2 contracts (MenuItemPrice, MenuSnapshotV2).
- Ưu tiên Qwen VL qua OpenRouter (free tier), fallback Gemini.
- Structured output: response_schema = list[MenuItemPrice].
- Retry tối đa 2 lần khi schema validation fail.
- NEEDS_REVIEW queue: món OCR không đọc được giá → confidence="low", đẩy sang review.

ADR-002: tầng parse không chứa suy luận nghiệp vụ — chỉ OCR + chuẩn hoá.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ca_contracts.catchment_survey_v2 import (
    ChannelMode,
    ConfidenceLevel,
    MenuItemPrice,
    MenuSnapshotV2,
)

from ca_agents.ag_pricing.dish_name_normalizer import normalize_dish_name
from ca_agents.llm import complete, parse_json_object

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_MIN_PRICE_VND = 5_000
_MAX_PRICE_VND = 5_000_000

# Bảng confidence hợp lệ theo contract. Vision có thể trả bất kỳ chuỗi nào
# ("HIGH", "chắc chắn", ""), nên phải tra bảng để thu hẹp về Literal thay vì
# để mypy thấy một `str` trần — và để giá trị lạ rơi về "medium" một chỗ duy nhất.
_CONFIDENCE_HOP_LE: dict[str, ConfidenceLevel] = {
    "low": "low",
    "medium": "medium",
    "high": "high",
}

_VISION_SYSTEM_PROMPT = """Bạn là chuyên gia OCR thực đơn F&B tại Việt Nam.
Đọc ảnh chụp menu/bảng giá và trích xuất DANH SÁCH món cùng giá.

QUY TẮC CHỐNG ẢO GIÁC:
1. CHỈ trích xuất món + giá nhìn RÕ trên ảnh. Không suy diễn, không bịa.
2. Quy đổi giá về số nguyên VNĐ: "35k"→35000, "42.000đ"→42000, "120k"→120000.
3. Nếu món có nhiều size (S/M/L): lấy size nhỏ nhất làm original_price_vnd.
4. Nếu thấy giá gạch ngang + giá sale: tách RIÊNG original_price_vnd (giá gốc) và effective_price_vnd (giá sale), is_promotional=true.
5. Nếu ảnh mờ KHÔNG ĐỌC ĐƯỢC GIÁ: trả original_price_vnd=null, effective_price_vnd=0, confidence="low".
6. Nếu ảnh KHÔNG PHẢI menu (không gian, món ăn, logo): trả {"dishes":[], "is_valid_menu":false}.

Trả về JSON:
{
  "dishes": [
    {
      "name": "Cơm tấm sườn bì chả",
      "original_price_vnd": 45000,
      "effective_price_vnd": 36000,
      "is_promotional": true,
      "is_combo": false,
      "portion_note": null,
      "confidence": "high",
      "raw_text": "Cơm tấm sườn bì chả 45.000 → 36.000"
    }
  ],
  "is_valid_menu": true,
  "overall_confidence": 0.92
}
"""


@dataclass(frozen=True)
class VisionExtractionResult:
    """Kết quả OCR menu ảnh — bao gồm cả items cần review."""

    snapshot: MenuSnapshotV2 | None
    needs_review: list[dict[str, str]] = field(default_factory=list)
    error: str = ""
    retries_used: int = 0

    @property
    def ok(self) -> bool:
        return self.snapshot is not None and not self.error


def _validate_price(price_val: object) -> int | None:
    """Validate và chuẩn hoá giá về int VNĐ. None nếu không hợp lệ.

    Vision trả JSON nên `price_val` có thể là int, float hoặc chuỗi "42000".
    `isinstance(x, bool)` bị loại riêng vì `True` là `int` hợp lệ với Python —
    nếu không chặn thì một field boolean lệch tên sẽ thành giá 1đ rồi bị khoảng
    hợp lệ loại, và ta mất dấu vết rằng nguồn đã trả sai kiểu.
    """
    if isinstance(price_val, bool) or price_val is None:
        return None
    try:
        p: int = int(price_val) if isinstance(price_val, (int, float)) else int(str(price_val))
    except (TypeError, ValueError):
        return None
    if p < _MIN_PRICE_VND or p > _MAX_PRICE_VND:
        return None
    return p


def _parse_vision_response(
    text: str,
    *,
    source_channel: ChannelMode,
) -> tuple[list[MenuItemPrice], list[dict[str, str]], bool]:
    """Parse JSON response từ Vision AI thành MenuItemPrice list.

    Returns:
        (valid_items, needs_review_items, is_valid_menu)
    """
    parsed = parse_json_object(text)
    if not parsed or not isinstance(parsed, dict):
        return [], [], False

    if not parsed.get("is_valid_menu", False):
        return [], [], False

    raw_dishes = parsed.get("dishes") or []
    valid: list[MenuItemPrice] = []
    review: list[dict[str, str]] = []

    for d in raw_dishes:
        if not isinstance(d, dict):
            continue

        name = str(d.get("name") or "").strip()
        if not name:
            continue

        original = _validate_price(d.get("original_price_vnd"))
        effective = _validate_price(d.get("effective_price_vnd"))
        raw_confidence = str(d.get("confidence") or "medium").strip().lower()
        # Tra bảng chứ không so sánh chuỗi: mypy không thu hẹp `str` thành
        # ConfidenceLevel qua phép `in`, còn contract thì yêu cầu đúng Literal.
        # Bảng tra cũng khiến "giá trị lạ" và "thiếu giá trị" cùng về `medium`
        # một cách tường minh thay vì phụ thuộc thứ tự nhánh if.
        confidence: ConfidenceLevel = _CONFIDENCE_HOP_LE.get(raw_confidence, "medium")

        # OCR không đọc được giá → đẩy vào NEEDS_REVIEW
        if original is None and effective is None:
            review.append({
                "name": name,
                "raw_text": str(d.get("raw_text") or name),
                "reason": "price_unreadable",
            })
            continue

        # Fallback: nếu chỉ có 1 giá
        if original is None and effective is not None:
            original = effective
        if effective is None and original is not None:
            effective = original

        is_promotional = bool(d.get("is_promotional", False))
        if original != effective:
            is_promotional = True

        is_combo = bool(d.get("is_combo", False)) or "combo" in name.lower()

        portion_note = d.get("portion_note")
        if portion_note is not None:
            portion_note = str(portion_note).strip() or None

        is_fallback = bool(d.get("is_fallback_derived", False))

        valid.append(
            MenuItemPrice(
                item_name_raw=name,
                item_name_normalized=normalize_dish_name(name),
                original_price_vnd=original,
                effective_price_vnd=effective,  # type: ignore[arg-type]
                is_promotional=is_promotional,
                is_combo=is_combo,
                portion_note=portion_note,
                source_channel=source_channel,
                confidence=confidence,
                is_fallback_derived=is_fallback,
            )
        )

    return valid, review, True


def extract_menu_from_image(
    image_bytes: bytes,
    *,
    store_id: str,
    image_url: str = "",
    core_keyword: str = "",
    image_mime: str = "image/jpeg",
    source_channel: ChannelMode = ChannelMode.DINE_IN_VISION,
    photo_source: str = "menu_tab",
    photo_taken_recency_days: int | None = None,
) -> VisionExtractionResult:
    """OCR ảnh menu → MenuSnapshotV2 với retry + NEEDS_REVIEW queue.

    Args:
        image_bytes: bytes ảnh menu
        store_id: ID quán (bắt buộc cho MenuSnapshotV2)
        image_url: URL gốc của ảnh (lưu trace)
        core_keyword: danh mục cốt lõi đang khảo sát
        image_mime: MIME type ảnh
        source_channel: kênh nguồn
        photo_source: "menu_tab" hoặc "all_photos_filtered"
        photo_taken_recency_days: số ngày từ lúc chụp

    Returns:
        VisionExtractionResult với snapshot + needs_review list
    """
    if not image_bytes or len(image_bytes) < 100:
        return VisionExtractionResult(
            snapshot=None, error="image_too_small_or_empty"
        )

    user_prompt = (
        f"Đọc bảng giá trên ảnh menu này và trích xuất món ăn cùng giá bán (VNĐ). "
        f"Ngành hàng: '{core_keyword or 'ẩm thực'}'. "
        f"Trả JSON đúng định dạng."
    )

    all_needs_review: list[dict[str, str]] = []
    last_error = ""

    for attempt in range(_MAX_RETRIES + 1):
        try:
            res = complete(
                system=_VISION_SYSTEM_PROMPT,
                user=user_prompt,
                image_bytes=image_bytes,
                image_mime=image_mime,
                json_mode=True,
                timeout_s=30.0,
            )
        except Exception as exc:
            last_error = f"llm_call_error:{exc}"
            logger.warning("Vision OCR attempt %d failed: %s", attempt + 1, exc)
            continue

        if not res.ok or not res.text:
            last_error = f"llm_not_ok:{res.reason}"
            logger.warning(
                "Vision OCR attempt %d: provider=%s reason=%s",
                attempt + 1, res.provider, res.reason,
            )
            continue

        items, review, is_valid = _parse_vision_response(
            res.text, source_channel=source_channel
        )
        all_needs_review.extend(review)

        if not is_valid:
            # Invalid JSON or not_a_menu → retry (model may have hallucinated format)
            last_error = "parse_failed_or_not_menu"
            logger.info(
                "Vision OCR attempt %d: parse failed or not a menu, retrying",
                attempt + 1,
            )
            continue

        if items:
            snapshot = MenuSnapshotV2(
                store_id=store_id,
                image_url=image_url,
                ocr_model=f"{res.provider}:vision",
                extracted_items=items,
                captured_at=datetime.now(timezone.utc).isoformat(),
                photo_source=photo_source,  # type: ignore[arg-type]
                photo_taken_recency_days=photo_taken_recency_days,
            )
            return VisionExtractionResult(
                snapshot=snapshot,
                needs_review=all_needs_review,
                retries_used=attempt,
            )

        # Parse OK nhưng không có item nào hợp lệ → retry
        last_error = "no_valid_items_after_parse"
        logger.info(
            "Vision OCR attempt %d: parsed OK but 0 valid items (review=%d)",
            attempt + 1, len(review),
        )

    # Hết retry — trả về result với needs_review items
    return VisionExtractionResult(
        snapshot=None,
        needs_review=all_needs_review,
        error=last_error or "max_retries_exhausted",
        retries_used=_MAX_RETRIES,
    )


def extract_dishes_from_menu_image(
    image_bytes: bytes,
    core_keyword: str = "",
    image_mime: str = "image/jpeg",
) -> list[MenuItemPrice]:
    """Backward-compat wrapper — trả list[MenuItemPrice] thay vì DishItem.

    Dùng cho code cũ chưa migrate sang VisionExtractionResult.
    """
    result = extract_menu_from_image(
        image_bytes,
        store_id="_legacy_",
        core_keyword=core_keyword,
        image_mime=image_mime,
    )
    if result.snapshot is None:
        return []
    return result.snapshot.extracted_items
