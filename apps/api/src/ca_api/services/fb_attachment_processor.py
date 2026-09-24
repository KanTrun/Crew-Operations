"""Facebook Messenger attachment processor.

Xử lý các loại đính kèm từ Messenger: image, audio, video, file.
Tích hợp với OCR hiện có cho ảnh menu, và có thể mở rộng cho audio/video.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx
from ca_agents.ag_pricing.vision_menu_extractor import (
    VisionExtractionResult,
    extract_menu_from_image,
)
from ca_contracts.catchment_survey_v2 import ChannelMode

logger = logging.getLogger(__name__)

# Maximum file size to download (10MB)
MAX_DOWNLOAD_SIZE = 10 * 1024 * 1024

# Supported image MIME types for OCR
IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}

# Supported audio MIME types
AUDIO_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/ogg",
    "audio/mp4",
    "audio/aac",
}

# Supported video MIME types
VIDEO_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
}


@dataclass(frozen=True)
class AttachmentInfo:
    """Thông tin đính kèm đã xử lý."""

    attachment_type: str  # "image", "audio", "video", "file"
    mime_type: str | None
    url: str | None
    filename: str | None
    size_bytes: int | None
    # Processed content
    ocr_result: VisionExtractionResult | None = None
    transcript: str | None = None
    summary: str | None = None
    error: str | None = None


async def download_attachment(url: str, max_size: int = MAX_DOWNLOAD_SIZE) -> bytes | None:
    """Tải file đính kèm từ URL của Facebook.

    Facebook attachment URLs thường cần access token. Trong production,
    cần truyền page access token qua header Authorization.
    """
    try:
        # Get page access token from environment
        page_token = os.environ.get("NHIPQUAN_FB_PAGE_TOKEN")
        headers = {}
        if page_token:
            headers["Authorization"] = f"Bearer {page_token}"

        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            # First, HEAD request to check size
            head_resp = await client.head(url)
            content_length = head_resp.headers.get("content-length")
            if content_length and int(content_length) > max_size:
                logger.warning("Attachment too large: %s bytes", content_length)
                return None

            # Download with streaming to enforce size limit
            content = bytearray()
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                async for chunk in resp.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > max_size:
                        logger.warning("Attachment exceeded max size during download")
                        return None
            return bytes(content)
    except Exception as e:
        logger.error("Failed to download attachment from %s: %s", url, e)
        return None


async def process_image_attachment(
    url: str,
    mime_type: str | None = None,
) -> AttachmentInfo:
    """Xử lý ảnh: OCR menu nếu là ảnh thực đơn."""
    # Check if it's an image we can process
    if mime_type and mime_type not in IMAGE_MIME_TYPES:
        return AttachmentInfo(
            attachment_type="image",
            mime_type=mime_type,
            url=url,
            filename=None,
            size_bytes=None,
            error=f"Unsupported image type: {mime_type}",
        )

    image_bytes = await download_attachment(url)
    if image_bytes is None:
        return AttachmentInfo(
            attachment_type="image",
            mime_type=mime_type,
            url=url,
            filename=None,
            size_bytes=None,
            error="Attachment download failed or exceeded size limit",
        )

    # Try OCR for menu extraction
    try:
        ocr_result = extract_menu_from_image(
            image_bytes,
            store_id=os.environ.get("NHIPQUAN_DEFAULT_STORE_ID", "quan_01"),
            image_url=url,
            image_mime=mime_type or "image/jpeg",
            source_channel=ChannelMode.DINE_IN_VISION,
            photo_source="all_photos_filtered",
        )
        summary = None
        if ocr_result.ok and ocr_result.snapshot:
            dishes = ocr_result.snapshot.extracted_items
            if dishes:
                dish_names = [d.item_name_raw for d in dishes[:5]]
                summary = f"Menu OCR: {len(dishes)} món ({', '.join(dish_names)}{'...' if len(dishes) > 5 else ''})"
            else:
                summary = "Ảnh menu nhưng OCR không đọc được món nào"
        elif ocr_result.error:
            summary = f"OCR lỗi: {ocr_result.error}"
        else:
            summary = "Không phải menu hoặc ảnh không hợp lệ"

        return AttachmentInfo(
            attachment_type="image",
            mime_type=mime_type,
            url=url,
            filename=None,
            size_bytes=None,
            ocr_result=ocr_result,
            summary=summary,
        )
    except Exception as e:
        logger.error("Image processing failed for %s: %s", url, e)
        return AttachmentInfo(
            attachment_type="image",
            mime_type=mime_type,
            url=url,
            filename=None,
            size_bytes=None,
            error=str(e),
        )


async def process_audio_attachment(
    url: str,
    mime_type: str | None = None,
) -> AttachmentInfo:
    """Xử lý âm thanh: placeholder cho speech-to-text.

    TODO: Integrate with Whisper/ASR service when available.
    """
    return AttachmentInfo(
        attachment_type="audio",
        mime_type=mime_type,
        url=url,
        filename=None,
        size_bytes=None,
        summary="[Âm thanh] Chưa hỗ trợ chuyển văn bản tự động",
        error="Speech-to-text not implemented",
    )


async def process_video_attachment(
    url: str,
    mime_type: str | None = None,
) -> AttachmentInfo:
    """Xử lý video: placeholder cho video analysis.

    TODO: Integrate with video analysis service when available.
    """
    return AttachmentInfo(
        attachment_type="video",
        mime_type=mime_type,
        url=url,
        filename=None,
        size_bytes=None,
        summary="[Video] Chưa hỗ trợ phân tích tự động",
        error="Video analysis not implemented",
    )


async def process_file_attachment(
    url: str,
    mime_type: str | None = None,
    filename: str | None = None,
) -> AttachmentInfo:
    """Xử lý file chung: placeholder cho document parsing.

    TODO: Integrate with document parsing (PDF, DOCX, etc.) when available.
    """
    return AttachmentInfo(
        attachment_type="file",
        mime_type=mime_type,
        url=url,
        filename=filename,
        size_bytes=None,
        summary=f"[Tệp: {filename or 'không tên'}] Chưa hỗ trợ đọc nội dung tự động",
        error="Document parsing not implemented",
    )


async def process_attachment(
    attachment: dict[str, Any],
    page_token: str | None = None,
) -> AttachmentInfo:
    """Xử lý một attachment từ Messenger webhook.

    Args:
        attachment: Dict từ webhook payload với keys: type, payload{url, mime_type, ...}
        page_token: Page access token để download private attachments

    Returns:
        AttachmentInfo với kết quả xử lý
    """
    att_type = str(attachment.get("type") or "unknown")
    payload = attachment.get("payload") or {}
    url = str(payload.get("url") or "")
    mime_type = str(payload.get("mime_type") or "") or None
    filename = str(payload.get("filename") or "") or None
    size_bytes = payload.get("size")

    if not url:
        return AttachmentInfo(
            attachment_type=att_type,
            mime_type=mime_type,
            url=None,
            filename=filename,
            size_bytes=size_bytes if isinstance(size_bytes, int) else None,
            error="No URL in attachment payload",
        )

    # Route to appropriate processor
    if att_type == "image" or (mime_type and mime_type in IMAGE_MIME_TYPES):
        return await process_image_attachment(url, mime_type)
    elif att_type == "audio" or (mime_type and mime_type in AUDIO_MIME_TYPES):
        return await process_audio_attachment(url, mime_type)
    elif att_type == "video" or (mime_type and mime_type in VIDEO_MIME_TYPES):
        return await process_video_attachment(url, mime_type)
    elif att_type == "file":
        return await process_file_attachment(url, mime_type, filename)
    else:
        return AttachmentInfo(
            attachment_type=att_type,
            mime_type=mime_type,
            url=url,
            filename=filename,
            size_bytes=size_bytes if isinstance(size_bytes, int) else None,
            summary=f"[{att_type}] Loại đính kèm chưa hỗ trợ xử lý",
            error=f"Unsupported attachment type: {att_type}",
        )


def format_attachment_for_review(att_info: AttachmentInfo) -> tuple[str, list[str]]:
    """Format attachment info thành description và flagged_reasons cho review queue.

    Returns:
        (description, flagged_reasons)
    """
    flagged = [f"attachment:{att_info.attachment_type}"]

    if att_info.error:
        flagged.append("processing_error")

    if att_info.attachment_type == "image" and att_info.ocr_result:
        if att_info.ocr_result.ok and att_info.ocr_result.snapshot:
            dishes = att_info.ocr_result.snapshot.extracted_items
            if dishes:
                flagged.append("menu_detected")
                if any(d.original_price_vnd is None for d in dishes):
                    flagged.append("ocr_price_missing")
            else:
                flagged.append("no_menu_items")
        elif att_info.ocr_result.error:
            flagged.append("ocr_failed")

    # Build description
    parts = []
    if att_info.summary:
        parts.append(att_info.summary)
    elif att_info.error:
        parts.append(f"Lỗi xử lý: {att_info.error}")
    else:
        type_labels = {
            "image": "Ảnh",
            "audio": "Âm thanh",
            "video": "Video",
            "file": "Tệp",
        }
        parts.append(f"[{type_labels.get(att_info.attachment_type, 'Đính kèm')}]")

    if att_info.filename:
        parts.append(f"Tên: {att_info.filename}")
    if att_info.url:
        parts.append(f"URL: {att_info.url}")

    description = " | ".join(parts)
    return description, flagged
