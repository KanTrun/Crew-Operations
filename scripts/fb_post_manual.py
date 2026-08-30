"""Đăng bài thủ công lên page Nhịp Quán.

Usage:
    python scripts/fb_post_manual.py
    python scripts/fb_post_manual.py --text "Noi dung can dang"
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from facebook_page_poster import FacebookPagePoster


def main() -> int:
    ap = argparse.ArgumentParser(description="Dang bai thu cong len page Nhip Quan")
    ap.add_argument("--text", help="Noi dung bai (neu khong truyen se nhap tu stdin)")
    args = ap.parse_args()

    text = args.text or input("Nhap noi dung bai dang:\n> ").strip()
    if not text:
        print("Khong co noi dung -> thoat")
        return 1

    poster = FacebookPagePoster()
    if not poster.verify_token():
        print("Token loi -> khong dang")
        return 2

    result = poster.post_text(text)
    if not result.get("success"):
        print(f"LOI: {result.get('error')}")
        return 3

    print(f"\n=== POSTED ===\nID: {result.get('post_id')}")
    print(
        f"Permalink: https://facebook.com/{poster.page_id}_{result.get('post_id').split('_')[-1]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
