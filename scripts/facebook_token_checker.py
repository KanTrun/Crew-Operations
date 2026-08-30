#!/usr/bin/env python3
"""
Facebook Token Permission Checker
Diagnose and fix token permission issues
"""

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class FacebookTokenChecker:
    """Check and diagnose token permissions"""

    BASE_URL = "https://graph.facebook.com/v26.0"

    # Required permissions for posting
    REQUIRED_PERMISSIONS = ["pages_manage_posts", "pages_read_engagement"]

    def __init__(self):
        """Initialize with token from environment"""
        self.page_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") or os.getenv(
            "NHIPQUAN_FB_PAGE_TOKEN"
        )
        self.page_id = os.getenv("FACEBOOK_PAGE_ID") or os.getenv("NHIPQUAN_FB_PAGE_ID")

        if not self.page_token:
            raise ValueError("❌ FACEBOOK_PAGE_ACCESS_TOKEN not set in .env")
        if not self.page_id:
            raise ValueError("❌ FACEBOOK_PAGE_ID not set in .env")

    def check_token_permissions(self) -> dict[str, Any]:
        """Check what permissions the token has"""
        print("\n🔐 Checking token permissions...")

        try:
            # Debug token to see permissions
            response = requests.get(
                "https://graph.instagram.com/debug_token",
                params={"input_token": self.page_token, "access_token": self.page_token},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json().get("data", {})

                scopes = data.get("scopes", [])
                is_valid = data.get("is_valid", False)
                expires_at = data.get("expires_at", 0)

                print("\n📊 Token Status:")
                print(f"  Valid: {'✅ Yes' if is_valid else '❌ No'}")
                print(f"  Expires at: {expires_at}")

                print(f"\n📋 Current Permissions ({len(scopes)}):")
                for scope in scopes:
                    print(f"  - {scope}")

                return {"valid": is_valid, "scopes": scopes, "expires_at": expires_at}
            else:
                print(f"❌ Failed to debug token: {response.text}")
                return {"error": response.text}

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return {"error": str(e)}

    def check_page_admin_status(self) -> bool:
        """Check if token has admin access to page"""
        print("\n👤 Checking page admin status...")

        try:
            # Try to get page info with the token
            response = requests.get(
                f"{self.BASE_URL}/{self.page_id}",
                params={"fields": "id,name,access_token", "access_token": self.page_token},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ You have access to page: {data.get('name', 'Unknown')}")

                # Check if we got page access token (means we're admin)
                if "access_token" in data:
                    print("✅ Page access token obtained (you're admin/editor)")
                    return True
                else:
                    print("❌ No page access token (insufficient permissions)")
                    return False
            else:
                error = (
                    response.json()
                    if response.headers.get("content-type") == "application/json"
                    else response.text
                )
                print(f"❌ Cannot access page: {error}")
                return False

        except Exception as e:
            print(f"❌ Error: {str(e)}")
            return False

    def diagnose(self) -> bool:
        """Run full diagnostic"""
        print("\n" + "=" * 60)
        print("FACEBOOK TOKEN PERMISSION DIAGNOSTIC")
        print("=" * 60)

        # Check token permissions
        token_info = self.check_token_permissions()

        if "error" in token_info:
            print("\n❌ Could not retrieve token info")
            return False

        # Check for required permissions
        scopes = token_info.get("scopes", [])
        missing_permissions = [p for p in self.REQUIRED_PERMISSIONS if p not in scopes]

        print("\n🔍 Required Permissions Check:")
        for perm in self.REQUIRED_PERMISSIONS:
            status = "✅" if perm in scopes else "❌"
            print(f"  {status} {perm}")

        if missing_permissions:
            print(f"\n⚠️  Missing permissions: {', '.join(missing_permissions)}")

        # Check admin status
        is_admin = self.check_page_admin_status()

        print("\n" + "=" * 60)
        print("DIAGNOSIS SUMMARY")
        print("=" * 60)

        if token_info.get("valid") and not missing_permissions and is_admin:
            print("\n✅ Token is properly configured!")
            print("\n💡 Possible reasons posting still fails:")
            print("  1. Page settings restrict who can post")
            print("  2. App not yet approved by Meta for publishing")
            print("  3. Try regenerating token from Facebook Developer")
            return True
        else:
            print("\n❌ Token has permission issues:")
            if not token_info.get("valid"):
                print("  • Token is expired or invalid")
            if missing_permissions:
                print(f"  • Missing: {', '.join(missing_permissions)}")
            if not is_admin:
                print("  • Not admin/editor of the page")

            print("\n🔧 HOW TO FIX:")
            print("\n1. Go to Facebook App Dashboard:")
            print("   https://developers.facebook.com/apps/")
            print("\n2. Select your app → Settings → Basic")
            print("\n3. Go to App Roles → Test Users")
            print("   Make sure you're listed as Developer or Tester")
            print("\n4. Regenerate Page Access Token:")
            print("   Settings → Basic → Generate token")
            print("   Select your page")
            print("   Select all permissions:")
            print("     • pages_manage_posts")
            print("     • pages_read_engagement")
            print("     • pages_read_user_content")
            print("\n5. Copy the new token to .env:")
            print("   FACEBOOK_PAGE_ACCESS_TOKEN=<new_token>")
            print("   FACEBOOK_PAGE_ID=1367177249801969")
            print("\n6. Run again: python scripts/facebook_token_checker.py")

            return False


def main():
    """Main entry point"""
    try:
        checker = FacebookTokenChecker()
        success = checker.diagnose()
        exit(0 if success else 1)

    except ValueError as e:
        print(f"\n❌ {str(e)}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback

        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
