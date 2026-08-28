"""Facebook Page Graph helpers — token chỉ đọc từ env, không log."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

GRAPH = "https://graph.facebook.com/v21.0"


def _token() -> str:
    return os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "").strip()


def _page_id() -> str:
    return os.environ.get("NHIPQUAN_FB_PAGE_ID", "").strip()


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
    fields = (
        "id,updated_time,participants{name,id},"
        "messages.limit(5){message,from,created_time}"
    )
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


def send_messenger_text(psid: str, text: str) -> dict[str, Any]:
    """Gửi tin Messenger tới PSID (người dùng đã nhắn Page)."""
    return graph_post(
        "me/messages",
        {
            "recipient": json.dumps({"id": psid}),
            "messaging_type": "RESPONSE",
            "message": json.dumps({"text": text}),
        },
    )


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
