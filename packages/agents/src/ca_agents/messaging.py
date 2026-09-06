"""Messaging ports — send + inbound (replay / telegram / zalo / console)."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_FIXTURE = ROOT / "data" / "golden" / "msg" / "inbound_01.jsonl"
OUTBOX = ROOT / "data" / "out" / "msg_sent.jsonl"


@dataclass
class SendResult:
    ok: bool
    backend: str
    detail: str


@dataclass
class InboundMessage:
    text: str
    channel: str
    external_user_id: str
    ts: str = ""
    raw_id: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


class MessagePort:
    name = "base"

    def send(self, to: str, text: str) -> SendResult:
        raise NotImplementedError

    def receive_iter(self) -> Iterator[InboundMessage]:
        return iter(())


def _append_outbox(backend: str, to: str, text: str) -> None:
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {"backend": backend, "to": to, "text": text},
                ensure_ascii=False,
            )
            + "\n"
        )


class ConsolePort(MessagePort):
    name = "console"

    def send(self, to: str, text: str) -> SendResult:
        print(f"[console->{to}] {text}")
        _append_outbox("console", to, text)
        return SendResult(ok=True, backend="console", detail="printed")


class ReplayPort(MessagePort):
    """Đọc tin fixture — không mạng. Dùng cho CI và demo trước khi có bot."""

    name = "replay"

    def __init__(self, fixture: Path | None = None) -> None:
        self.fixture = fixture or Path(os.environ.get("NHIPQUAN_MSG_FIXTURE", str(DEFAULT_FIXTURE)))

    def send(self, to: str, text: str) -> SendResult:
        _append_outbox("replay", to, text)
        return SendResult(ok=True, backend="replay", detail="logged_outbox")

    def receive_iter(self) -> Iterator[InboundMessage]:
        if not self.fixture.exists():
            return
        for line in self.fixture.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            yield InboundMessage(
                text=str(raw.get("text") or ""),
                channel=str(raw.get("channel") or "telegram"),
                external_user_id=str(raw.get("external_user_id") or ""),
                ts=str(raw.get("ts") or ""),
                raw_id=str(raw.get("raw_id") or raw.get("id") or ""),
                raw=raw if isinstance(raw, dict) else {},
            )


class TelegramPort(MessagePort):
    name = "telegram"

    def send(self, to: str, text: str) -> SendResult:
        token = os.environ.get("NHIPQUAN_TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            _append_outbox("telegram", to, text)
            return SendResult(
                ok=False,
                backend="telegram",
                detail="stub_no_token_logged_outbox",
            )
        # Live send chỉ khi có token — tránh gọi mạng trong CI.
        try:
            import urllib.parse
            import urllib.request

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": to, "text": text}).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
                body = resp.read().decode()
            _append_outbox("telegram", to, text)
            return SendResult(ok=True, backend="telegram", detail=body[:120])
        except Exception as exc:  # noqa: BLE001 — port không được ném lên API
            _append_outbox("telegram", to, text)
            return SendResult(ok=False, backend="telegram", detail=f"send_fail:{exc}")


class ZaloPort(MessagePort):
    name = "zalo"

    def send(self, to: str, text: str) -> SendResult:
        enabled = os.environ.get("NHIPQUAN_ZALO_ENABLED", "").strip() in {"1", "true", "yes"}
        token = os.environ.get("NHIPQUAN_ZALO_OA_ACCESS_TOKEN", "").strip()
        if not enabled:
            return SendResult(
                ok=False,
                backend="zalo",
                detail="chua_bat_zalo",
            )
        if not token:
            _append_outbox("zalo", to, text)
            return SendResult(ok=False, backend="zalo", detail="thieu_token_logged_outbox")
        try:
            import json as _json
            import urllib.request

            url = "https://openapi.zalo.me/v3.0/oa/message/cs"
            body = _json.dumps(
                {
                    "recipient": {"user_id": str(to)},
                    "message": {"text": text},
                }
            ).encode()
            req = urllib.request.Request(
                url,
                data=body,
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "access_token": token,
                },
            )
            with urllib.request.urlopen(req, timeout=8) as resp:  # noqa: S310
                raw = resp.read().decode()
            _append_outbox("zalo", to, text)
            return SendResult(ok=True, backend="zalo", detail=raw[:160])
        except Exception as exc:  # noqa: BLE001
            _append_outbox("zalo", to, text)
            return SendResult(ok=False, backend="zalo", detail=f"send_fail:{exc}")


def get_port(name: str | None) -> MessagePort:
    key = (name or os.environ.get("NHIPQUAN_MSG_BACKEND") or "console").lower()
    if key == "telegram":
        return TelegramPort()
    if key == "zalo":
        return ZaloPort()
    if key == "replay":
        return ReplayPort()
    return ConsolePort()


def parse_zalo_webhook(payload: dict[str, Any]) -> InboundMessage | None:
    """Nhận event OA phổ biến (message text). Shape Zalo có thể đổi — giữ parser lỏng."""
    event = str(payload.get("event_name") or payload.get("event") or "")
    message_raw = payload.get("message")
    message: dict[str, Any] = message_raw if isinstance(message_raw, dict) else {}
    text = message.get("text") or payload.get("text")
    sender_raw = payload.get("sender")
    sender = (
        sender_raw.get("id")
        if isinstance(sender_raw, dict)
        else payload.get("user_id_by_app") or payload.get("sender_id")
    )
    if not text or not sender:
        data_raw = payload.get("data")
        data: dict[str, Any] = data_raw if isinstance(data_raw, dict) else {}
        nested = data.get("message")
        if isinstance(nested, dict):
            text = text or nested.get("text")
        elif isinstance(nested, str):
            text = text or nested
        sender = sender or data.get("sender_id") or data.get("user_id")
    if not text or not sender:
        return None
    if event and "message" not in event.lower() and event not in {"", "user_send_text"}:
        if not str(text).strip():
            return None
    return InboundMessage(
        text=str(text),
        channel="zalo",
        external_user_id=str(sender),
        ts=str(payload.get("timestamp") or ""),
        raw_id=str(payload.get("message_id") or message.get("msg_id") or ""),
        raw=payload,
    )


def parse_telegram_update(payload: dict[str, Any]) -> InboundMessage | None:
    msg = payload.get("message") or payload.get("edited_message")
    if not isinstance(msg, dict):
        return None
    text = msg.get("text")
    chat = msg.get("chat") or {}
    if not text or not isinstance(chat, dict):
        return None
    chat_id = chat.get("id")
    if chat_id is None:
        return None
    return InboundMessage(
        text=str(text),
        channel="telegram",
        external_user_id=str(chat_id),
        ts=str(msg.get("date") or ""),
        raw_id=str(msg.get("message_id") or ""),
        raw=payload,
    )


_XEM_LICH_KEYS = (
    "lịch của tôi",
    "lich cua toi",
    "ca của tôi",
    "ca cua toi",
    "xem lịch",
    "xem lich",
    "hôm nay làm gì",
    "hom nay lam gi",
    "tuần này ca",
    "tuan nay ca",
)


def is_xem_lich(text: str) -> bool:
    t = text.lower().strip()
    return any(k in t for k in _XEM_LICH_KEYS)


def should_enqueue_constraint(text: str, intent: str, do_tin_cay: float) -> bool:
    """Xác định tin nhắn có phải ràng buộc cần đưa vào inbox duyệt hay không."""
    if intent in {"doi_ca", "nhan_ca", "bao_tre", "cap_nhat_tkb", "xin_nghi"}:
        return do_tin_cay >= 0.5
    return False
