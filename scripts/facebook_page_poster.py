#!/usr/bin/env python3
"""
Facebook Page Post Manager
Safely post content to Facebook page with validation and error handling
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class FacebookPagePoster:
    """Manage Facebook page posts"""

    BASE_URL = "https://graph.facebook.com/v26.0"

    def __init__(self):
        """Initialize with config from environment"""
        self.page_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") or os.getenv(
            "NHIPQUAN_FB_PAGE_TOKEN"
        )
        self.page_id = os.getenv("FACEBOOK_PAGE_ID") or os.getenv("NHIPQUAN_FB_PAGE_ID")
        self.page_name = os.getenv("FACEBOOK_PAGE_NAME", "Unknown Page")

        if not self.page_token:
            raise ValueError(
                "❌ FACEBOOK_PAGE_ACCESS_TOKEN không được set trong .env\n"
                "Hãy chạy: python scripts/test_facebook_api.py\n"
                "Copy page access token từ output vào .env"
            )

        if not self.page_id:
            raise ValueError("❌ FACEBOOK_PAGE_ID không được set trong .env")

    def verify_token(self) -> bool:
        """Verify token is valid"""
        print("\n🔐 Verifying token...")
        try:
            response = requests.get(
                f"{self.BASE_URL}/me", params={"access_token": self.page_token}, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                print("✅ Token valid")
                print(f"   Page: {data.get('name', 'Unknown')}")
                return True
            else:
                print(f"❌ Token invalid: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Verification failed: {str(e)}")
            return False

    def post_text(self, message: str) -> dict[str, Any]:
        """Post text message to page"""
        print("\n📝 Posting text message...")
        print(f"   Content: {message[:80]}...")

        try:
            response = requests.post(
                f"{self.BASE_URL}/{self.page_id}/feed",
                data={"message": message, "access_token": self.page_token},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                post_id = data.get("id")
                print("✅ Post successful!")
                print(f"   Post ID: {post_id}")
                return {"success": True, "post_id": post_id}
            else:
                error = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else response.text
                )
                print(f"❌ Post failed: {error}")
                return {"success": False, "error": str(error)}

        except Exception as e:
            print(f"❌ Request error: {str(e)}")
            return {"success": False, "error": str(e)}

    def post_link(self, url: str, message: str = "") -> dict[str, Any]:
        """Post link with optional message"""
        print("\n🔗 Posting link...")
        print(f"   URL: {url}")
        if message:
            print(f"   Caption: {message[:60]}...")

        try:
            data = {"link": url, "access_token": self.page_token}

            if message:
                data["message"] = message

            response = requests.post(f"{self.BASE_URL}/{self.page_id}/feed", data=data, timeout=10)

            if response.status_code == 200:
                result = response.json()
                post_id = result.get("id")
                print("✅ Link posted!")
                print(f"   Post ID: {post_id}")
                return {"success": True, "post_id": post_id}
            else:
                error = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else response.text
                )
                print(f"❌ Post failed: {error}")
                return {"success": False, "error": str(error)}

        except Exception as e:
            print(f"❌ Request error: {str(e)}")
            return {"success": False, "error": str(e)}

    def post_photo(self, image_url: str, caption: str = "") -> dict[str, Any]:
        """Post photo from URL"""
        print("\n📸 Posting photo...")
        print(f"   Image URL: {image_url}")
        if caption:
            print(f"   Caption: {caption[:60]}...")

        try:
            data = {"url": image_url, "access_token": self.page_token}

            if caption:
                data["caption"] = caption

            response = requests.post(
                f"{self.BASE_URL}/{self.page_id}/photos", data=data, timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                post_id = result.get("id")
                print("✅ Photo posted!")
                print(f"   Photo ID: {post_id}")
                return {"success": True, "photo_id": post_id}
            else:
                error = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else response.text
                )
                print(f"❌ Post failed: {error}")
                return {"success": False, "error": str(error)}

        except Exception as e:
            print(f"❌ Request error: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_post_info(self, post_id: str) -> dict[str, Any]:
        """Get information about a posted post"""
        print(f"\n📊 Getting post info: {post_id}")

        try:
            response = requests.get(
                f"{self.BASE_URL}/{post_id}",
                params={
                    "fields": (
                        "id,message,story,created_time,likes.summary(true),"
                        "comments.summary(true),shares"
                    ),
                    "access_token": self.page_token,
                },
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                print("✅ Post info retrieved")
                print(f"   Created: {data.get('created_time', 'N/A')}")
                likes_c = data.get("likes", {}).get("summary", {}).get("total_count", 0)
                cmts_c = data.get("comments", {}).get("summary", {}).get("total_count", 0)
                print(f"   Likes: {likes_c}")
                print(f"   Comments: {cmts_c}")
                return {"success": True, "data": data}
            else:
                error = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else response.text
                )
                print(f"❌ Failed to get info: {error}")
                return {"success": False, "error": str(error)}

        except Exception as e:
            print(f"❌ Request error: {e!s}")
            return {"success": False, "error": str(e)}


def test_suite():
    """Run comprehensive test suite"""
    print("\n" + "🚀 " * 20)
    print("FACEBOOK PAGE POST TEST SUITE")
    print("🚀 " * 20)

    try:
        poster = FacebookPagePoster()
    except ValueError as e:
        print(f"\n❌ {e!s}")
        return False

    # Test 1: Verify token
    print("\n" + "=" * 60)
    print("TEST 1: Token Verification")
    print("=" * 60)

    if not poster.verify_token():
        print("\n❌ Token verification failed. Stop testing.")
        return False

    # Test 2: Post simple text
    print("\n" + "=" * 60)
    print("TEST 2: Post Simple Text")
    print("=" * 60)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    text_content = (
        f"🤖 Bài test tự động từ Nhịp Quán Bot\n\nThời gian: {now_str}\n\n✅ Test post thành công!"
    )
    result_text = poster.post_text(text_content)

    if result_text.get("success"):
        post_id = result_text.get("post_id")

        # Test 3: Get post info
        print("\n" + "=" * 60)
        print("TEST 3: Get Post Info")
        print("=" * 60)

        info_result = poster.get_post_info(post_id)

    # Test 4: Post link
    print("\n" + "=" * 60)
    print("TEST 4: Post Link")
    print("=" * 60)

    link_result = poster.post_link(
        url="https://github.com/nhipquan", message="GitHub Repository - Nhịp Quán Project"
    )

    # Summary
    print("\n" + "✅ " * 20)
    print("TEST SUITE COMPLETED")
    print("✅ " * 20)

    print("\n📊 SUMMARY:")
    print("  ✓ Token verification: PASSED")
    print(f"  ✓ Text post: {'PASSED' if result_text.get('success') else 'FAILED'}")
    if result_text.get("success"):
        print(f"  ✓ Get post info: {'PASSED' if info_result.get('success') else 'FAILED'}")
    print(f"  ✓ Link post: {'PASSED' if link_result.get('success') else 'FAILED'}")

    return True


if __name__ == "__main__":
    try:
        test_suite()
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        exit(1)
