"""Dùng user token mới để lấy Page token + subscribe app vào Page (webhook fields)."""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

USER_TOKEN = sys.argv[1].strip()
PAGE_ID = "1367177249801969"
FIELDS = "messages,messaging_postbacks,message_deliveries,message_reads,message_echoes"


def get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def post(url: str) -> dict:
    data = urllib.parse.urlencode({}).encode()
    try:
        with urllib.request.urlopen(url, data=data, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print(f"SUBSCRIBE_ERR: HTTP {e.code} {e.read().decode()[:400]}")
        return {}


def main() -> None:
    # 1. Đổi user token -> page token (long-lived theo app)
    accounts = get(
        "https://graph.facebook.com/v21.0/me/accounts?access_token="
        + urllib.parse.quote(USER_TOKEN)
    )
    pages = accounts.get("data", [])
    if not pages:
        print("ERR: token khong quan ly page nao")
        sys.exit(1)

    page = next((p for p in pages if p["id"] == PAGE_ID), pages[0])
    page_token = page["access_token"]
    print(f"PAGE: {page['name']} ({page['id']})")
    print(f"PAGE_TOKEN_PREFIX: {page_token[:16]}...")
    print(f"PAGE_TOKEN_FULL_FOR_ENV: {page_token}")

    # 2. Subscribe app vào Page cho các field Messenger
    sub = post(
        f"https://graph.facebook.com/v21.0/{PAGE_ID}/subscribed_apps"
        f"?subscribed_fields={FIELDS}&access_token={urllib.parse.quote(page_token)}"
    )
    print(f"SUBSCRIBE: {json.dumps(sub, ensure_ascii=False)}")
    # 3. Xác nhận
    check = get(
        f"https://graph.facebook.com/v21.0/{PAGE_ID}/subscribed_apps"
        f"?access_token={urllib.parse.quote(page_token)}"
    )
    print(f"SUBSCRIBED_APPS_NOW: {json.dumps(check, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
