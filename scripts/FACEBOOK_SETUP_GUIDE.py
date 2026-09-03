#!/usr/bin/env python3
"""
Facebook Setup Guide - Comprehensive Setup Instructions
Step-by-step guide to properly configure Facebook Page Access Token
"""


def print_header(title):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num, title):
    """Print formatted step"""
    print(f"\n📌 STEP {step_num}: {title}")
    print("-" * 70)


def main():
    """Display comprehensive setup guide"""
    print("\n" + "🚀 " * 25)
    print("FACEBOOK PAGE POST SETUP GUIDE")
    print("🚀 " * 25)

    print_header("⚠️  CURRENT ERROR")
    print("""
Token is INVALID: "Cannot parse access token"

This means:
  ❌ Token was copied incorrectly
  ❌ Token is truncated/incomplete
  ❌ Token contains spaces or extra characters
    """)

    print_header("✅ SOLUTION: Generate Token Correctly")

    print_step(1, "Open Facebook App Dashboard")
    print("""
URL: https://developers.facebook.com/apps/

OR direct link:
https://developers.facebook.com/apps/YOUR_APP_ID/settings/basic/
    """)

    print_step(2, "Navigate to Tools → Token Debugger")
    print("""
Path:
  Dashboard (top-left) 
  → Tools & Support 
  → More Tools 
  → Token Debugger

OR simpler:
Go to: https://developers.facebook.com/tools/debug/token
    """)

    print_step(3, "Generate New Token")
    print("""
Option A - From Token Debugger:
  1. Click blue "Generate Access Token" button
  2. Select your page from dropdown
  3. Copy the long token string

Option B - From App Settings:
  1. Go to Settings → Basic
  2. Scroll to "Page Access Token"
  3. Click "Generate new"
  4. Select page
  5. Confirm permissions:
     ✓ pages_manage_posts
     ✓ pages_read_engagement
  6. Copy token
    """)

    print_step(4, "Copy Token Correctly")
    print("""
⚠️  IMPORTANT - Avoid Common Mistakes:

  ❌ WRONG: Copy-pasting includes extra spaces
  ❌ WRONG: Truncating token (must be ~150 chars)
  ❌ WRONG: Including quotes in token
  
  ✅ RIGHT: Copy entire token without any extra chars
  
How to verify token format:
  • Should be ~150-200 characters
  • Only letters, numbers, no spaces
  • Starts with: EA... or similar
  
Example: EAAjJgqhGVncBSU...{150 chars total}...ZD
    """)

    print_step(5, "Add to .env File")
    print("""
Open .env file and set:

  FACEBOOK_PAGE_ACCESS_TOKEN=<YOUR_COMPLETE_TOKEN_HERE>
  FACEBOOK_PAGE_ID=1367177249801969

❌ Wrong:
  FACEBOOK_PAGE_ACCESS_TOKEN=EA Ajj... (has space)
  FACEBOOK_PAGE_ACCESS_TOKEN=EAAjJg... (truncated)
  FACEBOOK_PAGE_ACCESS_TOKEN="EAAjJg..." (has quotes)

✅ Correct:
  FACEBOOK_PAGE_ACCESS_TOKEN=EAAB...<YOUR_COMPLETE_TOKEN_HERE>
    """)

    print_step(6, "Verify Setup")
    print("""
Run this to verify token is correct:

  python scripts/facebook_token_checker.py

Expected output:
  ✅ Token valid
  ✅ Page access confirmed
  ✅ All permissions present
    """)

    print_step(7, "Test Posting")
    print("""
If token verification passes:

  python scripts/facebook_page_poster.py

This will:
  1. Verify token
  2. Post test message
  3. Post test link
  4. Display post stats
    """)

    print_header("🆘 STILL NOT WORKING?")
    print("""
If token is valid but posting still fails:

1. Check App Status
   • Settings → Basic
   • Verify App Status is "Live"
   
2. Check Permissions
   • Settings → Basic → App Roles
   • Make sure you're Developer or Tester

3. Check Page Permissions
   • Make sure you're Admin of the page
   • Reassign yourself as Admin if needed

4. Check Rate Limits
   • You might be posting too frequently
   • Wait 60 seconds between posts

5. Regenerate App Secret
   • Settings → Basic
   • Generate New Secret
   • Update any configs using it

6. Use Browser Token Generator
   • Go to: https://developers.facebook.com/tools/explorer/
   • Select your app
   • Click "Get Token"
   • Select page
   • Confirm permissions
    """)

    print_header("📚 USEFUL LINKS")
    print("""
Token Debugger:
  https://developers.facebook.com/tools/debug/token

Facebook Graph API Docs:
  https://developers.facebook.com/docs/graph-api

Publishing to Pages:
  https://developers.facebook.com/docs/graph-api/reference/page/feed

Page Access Tokens:
  https://developers.facebook.com/docs/facebook-login/access-tokens/
    """)

    print_header("✅ QUICK CHECKLIST")
    print("""
Before running tests:
  
  [ ] Token is copied without spaces
  [ ] Token is full length (~150-200 chars)
  [ ] Token is in .env file
  [ ] FACEBOOK_PAGE_ID is correct (1367177249801969)
  [ ] You are admin of the Facebook page
  [ ] App is in "Live" mode
  [ ] You have both pages_manage_posts and pages_read_engagement
  [ ] Token generated in last hour (tokens can expire)
    """)

    print("\n" + "✅ " * 25)
    print("END OF SETUP GUIDE")
    print("✅ " * 25 + "\n")


if __name__ == "__main__":
    main()
