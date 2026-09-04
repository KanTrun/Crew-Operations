"""Kiểm tra trạng thái webhook Messenger của Page qua Graph API."""
import json
import os
import sys
import urllib.error
import urllib.request

PAGE_ID = "1367177249801969"
TOKEN = os.environ.get("NHIPQUAN_FB_PAGE_TOKEN", "")


def call(path: str) -> None:
    url = f"https://graph.facebook.com/v21.0/{path}?access_token={TOKEN}"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            print(f"OK  {path}: {json.dumps(json.load(r), ensure_ascii=False)[:600]}")
    except urllib.error.HTTPError as e:
        print(f"ERR {path}: HTTP {e.code} {e.read().decode()[:400]}")


if __name__ == "__main__":
    call(f"{PAGE_ID}/subscribed_apps")
    call(f"{PAGE_ID}?fields=name,messages")
