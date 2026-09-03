"""Facebook Page Graph helpers — token chỉ đọc từ env, không log."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
from typing import Any

GRAPH = "https://graph.facebook.com/v26.0"

_ENV_LOADED = False


def _ensure_env() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    candidates = [
        pathlib.Path.cwd() / ".env",
        pathlib.Path(__file__).resolve().parents[4] / ".env",
    ]
    for c in candidates:
        if c.exists():
            for line in c.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                k, _, v = stripped.partition("=")
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k and k not in os.environ:
                    os.environ[k] = v
            break
    _ENV_LOADED = True


_RESOLVED_FB_TOKEN: str | None = None
_RESOLVED_FB_PID: str | None = None


def _token() -> str:
    global _RESOLVED_FB_TOKEN, _RESOLVED_FB_PID
    if _RESOLVED_FB_TOKEN:
        return _RESOLVED_FB_TOKEN
    _ensure_env()
    raw = (
        os.environ.get("NHIPQUAN_FB_PAGE_TOKEN")
        or os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
        or ""
    ).strip()
    if not raw:
        return ""
    try:
        import json
        import urllib.request
        url = f"https://graph.facebook.com/v26.0/me/accounts?access_token={raw}"
        req = urllib.request.Request(url, headers={"User-Agent": "ca-crew/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            accounts = data.get("data", [])
            for p in accounts:
                if "nhịp quán" in p.get("name", "").lower():
                    _RESOLVED_FB_TOKEN = p["access_token"]
                    _RESOLVED_FB_PID = str(p.get("id") or "")
                    return _RESOLVED_FB_TOKEN
            if accounts and accounts[0].get("access_token"):
                _RESOLVED_FB_TOKEN = accounts[0]["access_token"]
                _RESOLVED_FB_PID = str(accounts[0].get("id") or "")
                return _RESOLVED_FB_TOKEN
    except Exception:
        pass
    _RESOLVED_FB_TOKEN = raw
    return raw


def _page_id() -> str:
    _ensure_env()
    pid = (
        os.environ.get("NHIPQUAN_FB_PAGE_ID") or os.environ.get("FACEBOOK_PAGE_ID") or ""
    ).strip()
    if pid and pid != "me":
        return pid
    if _RESOLVED_FB_PID:
        return _RESOLVED_FB_PID
    return "1367177249801969"


def _app_secret() -> str:
    _ensure_env()
    return os.environ.get("NHIPQUAN_FB_APP_SECRET", "").strip()


def verify_fb_webhook_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """
    Verify X-Hub-Signature-256 header sent by Meta Webhook.
    Format: sha256=<hex_digest>
    """
    secret = _app_secret()
    if not secret:
        # If secret is not configured in dev/test, return True if signature header is missing/dev
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_hash = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    provided_hash = signature_header.split("sha256=", 1)[1]
    return hmac.compare_digest(expected_hash, provided_hash)


def is_within_24h_window(last_message_timestamp: float | str | None) -> bool:
    """Check if the last customer message was sent within 24 hours."""
    if not last_message_timestamp:
        return True
    try:
        if isinstance(last_message_timestamp, (int, float)):
            ts = float(last_message_timestamp)
            # if ms timestamp
            if ts > 1e11:
                ts = ts / 1000.0
            return (time.time() - ts) <= 86400.0
        # parse ISO string
        from datetime import datetime

        dt = datetime.fromisoformat(str(last_message_timestamp).replace("Z", "+00:00"))
        return (datetime.now(UTC) - dt).total_seconds() <= 86400.0
    except Exception:
        return True


def graph_get(path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
    token = _token()
    if not token:
        raise RuntimeError("thieu_fb_token")
    q = dict(params or {})
    q["access_token"] = token
    url = f"{GRAPH}/{path.lstrip('/')}?{urllib.parse.urlencode(q)}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"graph_http_{e.code}:{body}") from e


def graph_post(path: str, data: dict[str, str]) -> dict[str, Any]:
    token = _token()
    if not token:
        raise RuntimeError("thieu_fb_token")
    payload = dict(data)
    payload["access_token"] = token
    body = urllib.parse.urlencode(payload).encode("utf-8")
    url = f"{GRAPH}/{path.lstrip('/')}"
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"graph_http_{e.code}:{err}") from e


def page_health() -> dict[str, Any]:
    """GET /{page-id}?fields=id,name — xác nhận token + Page ID."""
    pid = _page_id()
    if not pid:
        return {"ok": False, "detail": "thieu_page_id"}
    if not _token():
        return {"ok": False, "detail": "thieu_fb_token"}
    try:
        data = graph_get(pid, {"fields": "id,name"})
        return {
            "ok": True,
            "page_id": str(data.get("id") or pid),
            "page_name": str(data.get("name") or ""),
        }
    except RuntimeError as e:
        return {"ok": False, "detail": str(e)[:200]}


def fetch_conversations(limit: int = 15) -> list[dict[str, Any]]:
    """Đọc hội thoại Messenger của Page → thread nội bộ."""
    pid = _page_id()
    if not pid or not _token():
        return []
    fields = "id,updated_time,participants{name,id},messages.limit(5){message,from,created_time}"
    data = graph_get(f"{pid}/conversations", {"fields": fields, "limit": str(limit)})
    out: list[dict[str, Any]] = []
    for c in data.get("data") or []:
        parts = ((c.get("participants") or {}).get("data")) or []
        other = next((p for p in parts if str(p.get("id")) != pid), parts[0] if parts else {})
        msgs = ((c.get("messages") or {}).get("data")) or []
        latest = msgs[0] if msgs else {}
        replies = []
        for m in reversed(msgs):
            replies.append(
                {
                    "id": m.get("id") or "",
                    "text": m.get("message") or "",
                    "by": (m.get("from") or {}).get("name") or (m.get("from") or {}).get("id"),
                    "at": m.get("created_time") or "",
                    "mock": False,
                }
            )
        out.append(
            {
                "id": str(c.get("id") or ""),
                "psid": str(other.get("id") or ""),
                "from": str(other.get("name") or other.get("id") or "Khách"),
                "tom_tat": (latest.get("message") or "(không có chữ)")[:160],
                "updated_at": c.get("updated_time") or "",
                "replies": replies,
                "nguon": "facebook",
            }
        )
    return out


def send_messenger_text(psid: str, text: str, *, tag: str | None = None) -> dict[str, Any]:
    """
    Gửi tin Messenger tới PSID.
    Hỗ trợ message_tag khi gửi ngoài cửa sổ 24h (vd: CONFIRMED_EVENT_UPDATE).
    """
    data: dict[str, str] = {
        "recipient": json.dumps({"id": psid}),
        "message": json.dumps({"text": text}),
    }
    if tag:
        data["messaging_type"] = "MESSAGE_TAG"
        data["tag"] = tag
    else:
        data["messaging_type"] = "RESPONSE"

    return graph_post("me/messages", data)


def publish_page_post(message: str) -> dict[str, Any]:
    pid = _page_id()
    if not pid:
        raise RuntimeError("thieu_page_id")
    return graph_post(f"{pid}/feed", {"message": message})


def upsert_thread_from_messaging(sender_id: str, text: str, mid: str = "") -> dict[str, Any]:
    """Chuẩn hoá 1 tin webhook Messenger → thread dict."""
    return {
        "id": f"fb_{sender_id}",
        "psid": sender_id,
        "from": sender_id,
        "tom_tat": (text or "")[:160],
        "replies": [
            {
                "id": mid or "",
                "text": text,
                "by": sender_id,
                "at": "",
                "mock": False,
            }
        ],
        "nguon": "facebook",
    }
