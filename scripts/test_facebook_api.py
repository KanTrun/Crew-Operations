#!/usr/bin/env python3
"""
Facebook Graph API Test Script
Safely test Facebook API endpoints using tokens from .env file
"""

import os
import requests
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

class FacebookAPITester:
    """Test Facebook Graph API endpoints safely"""
    
    BASE_URL = "https://graph.facebook.com/v26.0"
    
    def __init__(self):
        """Initialize with token from environment"""
        self.token = os.getenv("FACEBOOK_ACCESS_TOKEN")
        self.app_id = os.getenv("FACEBOOK_APP_ID")
        self.app_secret = os.getenv("FACEBOOK_APP_SECRET")
        
        if not self.token:
            raise ValueError(
                "❌ FACEBOOK_ACCESS_TOKEN không được set trong .env\n"
                "Hãy:\n"
                "  1. Revoke token cũ tại Facebook App Dashboard\n"
                "  2. Sinh token mới\n"
                "  3. Copy vào .env: FACEBOOK_ACCESS_TOKEN=your_token"
            )
    
    def _make_request(
        self, 
        endpoint: str, 
        method: str = "GET", 
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make API request with proper error handling"""
        url = f"{self.BASE_URL}/{endpoint}"
        
        if params is None:
            params = {}
        
        # Add token to params
        params["access_token"] = self.token
        
        try:
            print(f"\n📤 {method} {endpoint}")
            response = requests.request(
                method=method,
                url=url,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {response.status_code}")
                return data
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"Error: {response.text}")
                return {"error": response.text}
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {str(e)}")
            return {"error": str(e)}
    
    def test_me_accounts(self) -> Dict[str, Any]:
        """Test: Get all pages/accounts managed by this token"""
        print("\n" + "="*60)
        print("TEST 1: Get My Accounts & Pages")
        print("="*60)
        
        data = self._make_request("me/accounts")
        
        if "data" in data:
            print(f"\n📋 Tổng số accounts: {len(data.get('data', []))}")
            for account in data.get("data", []):
                print(f"\n  - {account.get('name', 'Unknown')}")
                print(f"    ID: {account.get('id')}")
                print(f"    Type: {account.get('category', 'N/A')}")
                if "access_token" in account:
                    print(f"    ✓ Có page access token")
        
        return data
    
    def test_me_info(self) -> Dict[str, Any]:
        """Test: Get current user info"""
        print("\n" + "="*60)
        print("TEST 2: Get My Info")
        print("="*60)
        
        data = self._make_request("me", params={"fields": "id,name,email"})
        
        if "error" not in data:
            print(f"\n👤 User: {data.get('name', 'Unknown')}")
            print(f"   ID: {data.get('id')}")
            print(f"   Email: {data.get('email', 'N/A')}")
        
        return data
    
    def test_page_info(self, page_id: str) -> Dict[str, Any]:
        """Test: Get page info"""
        print("\n" + "="*60)
        print(f"TEST 3: Get Page Info ({page_id})")
        print("="*60)
        
        fields = "id,name,category,followers_count,fan_count,about"
        data = self._make_request(f"{page_id}", params={"fields": fields})
        
        if "error" not in data:
            print(f"\n📄 Page: {data.get('name', 'Unknown')}")
            print(f"   ID: {data.get('id')}")
            print(f"   Category: {data.get('category', 'N/A')}")
            print(f"   Followers: {data.get('followers_count', 0):,}")
            print(f"   Fans: {data.get('fan_count', 0):,}")
        
        return data
    
    def test_page_feeds(self, page_id: str, limit: int = 5) -> Dict[str, Any]:
        """Test: Get page feed posts"""
        print("\n" + "="*60)
        print(f"TEST 4: Get Page Feeds ({page_id})")
        print("="*60)
        
        fields = "id,message,story,created_time,type,permalink_url"
        data = self._make_request(
            f"{page_id}/feed",
            params={
                "fields": fields,
                "limit": limit
            }
        )
        
        if "data" in data:
            print(f"\n📝 Tổng posts: {len(data.get('data', []))}")
            for i, post in enumerate(data.get("data", [])[:5], 1):
                print(f"\n  Post {i}:")
                print(f"    ID: {post.get('id')}")
                print(f"    Type: {post.get('type')}")
                print(f"    Created: {post.get('created_time', 'N/A')}")
                msg = post.get('message') or post.get('story') or '[No text]'
                print(f"    Text: {msg[:80]}...")
        
        return data
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "🚀 " * 20)
        print("FACEBOOK API TEST SUITE")
        print("🚀 " * 20)
        
        results = {}
        
        # Test 1: Get accounts
        results["me_accounts"] = self.test_me_accounts()
        
        # Test 2: Get user info
        results["me_info"] = self.test_me_info()
        
        # Test 3 & 4: If we have accounts, test page info and feeds
        if "data" in results["me_accounts"] and results["me_accounts"]["data"]:
            page_id = results["me_accounts"]["data"][0]["id"]
            results["page_info"] = self.test_page_info(page_id)
            results["page_feeds"] = self.test_page_feeds(page_id)
        
        print("\n" + "✅ " * 20)
        print("Test suite completed!")
        print("✅ " * 20)
        
        return results


def main():
    """Main entry point"""
    try:
        tester = FacebookAPITester()
        tester.run_all_tests()
    
    except ValueError as e:
        print(f"\n❌ {str(e)}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
