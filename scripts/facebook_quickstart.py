#!/usr/bin/env python3
"""
Facebook Page Posting - Quick Start Script
Combines verification, permission checking, and test posting
"""

import os
import sys
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class FacebookQuickStart:
    """One-command verification and testing"""
    
    BASE_URL = "https://graph.facebook.com/v26.0"
    
    def __init__(self):
        self.page_token = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN") or os.getenv("NHIPQUAN_FB_PAGE_TOKEN")
        self.page_id = os.getenv("FACEBOOK_PAGE_ID") or os.getenv("NHIPQUAN_FB_PAGE_ID")
    
    def print_section(self, title):
        print(f"\n{'='*70}")
        print(f"  {title}")
        print(f"{'='*70}\n")
    
    def run(self):
        self.print_section("🚀 FACEBOOK PAGE POSTING QUICK START")
        
        # Step 1: Check environment
        print("📋 STEP 1: Checking Configuration...")
        
        if not self.page_token:
            print("  ❌ FACEBOOK_PAGE_ACCESS_TOKEN not found in .env")
            self._show_fix_instructions()
            return False
        
        if not self.page_id:
            print("  ❌ FACEBOOK_PAGE_ID not found in .env")
            self._show_fix_instructions()
            return False
        
        print("  ✅ Configuration found")
        print(f"     Page ID: {self.page_id}")
        print(f"     Token: {self.page_token[:20]}...{self.page_token[-10:]}")
        
        # Step 2: Verify token
        print("\n📋 STEP 2: Verifying Token...")
        
        try:
            response = requests.get(
                f"{self.BASE_URL}/me",
                params={"access_token": self.page_token},
                timeout=10
            )
            
            if response.status_code != 200:
                print(f"  ❌ Token verification failed")
                if response.status_code == 400:
                    error = response.json().get("error", {}).get("message", "")
                    if "Cannot parse access token" in error:
                        print("  💡 Tip: Token format is invalid. It may be:")
                        print("     - Truncated (must be ~150+ chars)")
                        print("     - Contains spaces or extra characters")
                        print("     - Includes quotes around it")
                        print("\n  👉 Run: python scripts/FACEBOOK_SETUP_GUIDE.py")
                print(f"  Error: {error}")
                return False
            
            data = response.json()
            print(f"  ✅ Token verified")
            print(f"     Page: {data.get('name', 'Unknown')}")
        
        except Exception as e:
            print(f"  ❌ Connection failed: {str(e)}")
            return False
        
        # Step 3: Test post
        print("\n📋 STEP 3: Testing Post...")
        
        test_message = f"🤖 Nhịp Quán Bot Test\nThời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/{self.page_id}/feed",
                data={
                    "message": test_message,
                    "access_token": self.page_token
                },
                timeout=10
            )
            
            if response.status_code == 200:
                post_id = response.json().get("id")
                print(f"  ✅ Post successful!")
                print(f"     Post ID: {post_id}")
                print(f"     Message: {test_message[:50]}...")
                return True
            else:
                error_data = response.json() if response.headers.get("content-type") == "application/json" else response.text
                error_msg = error_data.get("error", {}).get("message", str(error_data)) if isinstance(error_data, dict) else str(error_data)
                
                print(f"  ❌ Post failed")
                print(f"     Error: {error_msg[:100]}")
                
                if "permission" in error_msg.lower():
                    print("\n  💡 Solution:")
                    print("     1. Make sure you're ADMIN of the page")
                    print("     2. Token needs: pages_manage_posts permission")
                    print("     3. Regenerate token from Facebook Developer")
                
                return False
        
        except Exception as e:
            print(f"  ❌ Request failed: {str(e)}")
            return False
        
        return False
    
    def _show_fix_instructions(self):
        print("\n" + "="*70)
        print("  ❌ CONFIGURATION MISSING")
        print("="*70)
        print("""
To fix this, you need to:

1. Get Page Access Token:
   python scripts/FACEBOOK_SETUP_GUIDE.py
   
   Follow the setup guide to:
   • Go to Facebook App Dashboard
   • Generate new Page Access Token
   • Copy complete token (without spaces)

2. Update .env file:
   FACEBOOK_PAGE_ACCESS_TOKEN=<your_complete_token>
   FACEBOOK_PAGE_ID=1367177249801969

3. Verify setup:
   python scripts/facebook_quickstart.py

For detailed setup help:
   python scripts/FACEBOOK_SETUP_GUIDE.py
""")


def main():
    try:
        starter = FacebookQuickStart()
        success = starter.run()
        
        if success:
            print("\n" + "✅ "*35)
            print("\n🎉 Everything is working! You can now post to Nhịp Quán page\n")
            print("Usage examples in: python scripts/facebook_page_poster.py")
            print("✅ "*35 + "\n")
        else:
            print("\n" + "❌ "*35)
            print("\n⚠️  Setup incomplete. See instructions above.\n")
            print("✅ "*35 + "\n")
        
        exit(0 if success else 1)
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
