# Facebook Page Posting - Complete Setup & Usage Guide

## 🎯 Current Status

✅ **Token is valid** - Connection established to "Nhịp Quán" page
❌ **Missing Permission** - Token lacks `pages_manage_posts` permission

## ⚠️ What's the Issue?

The current token can only **read** page data, but cannot **post** new content.

## ✅ How to Fix

### Step 1: Generate New Token with Correct Permissions

Go to: **https://developers.facebook.com/tools/debug/token**

1. Click blue **"Generate New Token"** button
2. Select **"Nhịp Quán"** page from dropdown
3. A popup will show required permissions:
   - ✅ `pages_manage_posts`
   - ✅ `pages_read_engagement`
   - ✅ `pages_read_user_content`
4. Confirm all permissions
5. **Copy the entire token** (long string ~150+ chars)

⚠️ **Important**: Copy the COMPLETE token without:
- Extra spaces
- Quotes around it
- Truncating it

### Step 2: Update .env File

Edit `.env` and update:

```bash
FACEBOOK_PAGE_ACCESS_TOKEN=<paste_your_complete_token_here>
FACEBOOK_PAGE_ID=1367177249801969
```

Example:
```bash
FACEBOOK_PAGE_ACCESS_TOKEN=EAAjJgqhGVncBSUuWqgd55rLZAgUEfZArdZCeWZApqz7V5SNXCkZA7UMQIJimF71zXlTwvDVGf3mzyR8PmK6zPWUZBThavVZC6xV7QQz6zfmzgXCd9gT9VZB0XoI17m8velZBZBBdgaVREhn6XvZAojmKzHhmIV4iZBTjt81pRIg1RLmXNZBzxfo4sel7RuAoSJzCd5NsOu0Ex7kRLWgiUUJ6LgLKgK7ewOeop9L5DwZAympL0ZD
FACEBOOK_PAGE_ID=1367177249801969
```

### Step 3: Verify Configuration

```bash
python scripts/facebook_quickstart.py
```

Should show:
```
✅ Configuration found
✅ Token verified
✅ Post successful!
```

## 📝 Available Scripts

### 1. Quick Start (Recommended)
```bash
python scripts/facebook_quickstart.py
```
- Checks configuration
- Verifies token
- Tests posting
- Shows results

### 2. Setup Guide
```bash
python scripts/FACEBOOK_SETUP_GUIDE.py
```
- Detailed step-by-step instructions
- Common mistakes to avoid
- Troubleshooting tips

### 3. Page Posting
```bash
python scripts/facebook_page_poster.py
```
- Full test suite with multiple post types
- Text posts
- Links
- Photos
- Analytics for posts

### 4. Token Checker (Advanced)
```bash
python scripts/facebook_token_checker.py
```
- Check token permissions
- Verify admin status
- Diagnose permission issues

## 🚀 Usage Examples

### Post Text Message

```python
from scripts.facebook_page_poster import FacebookPagePoster

poster = FacebookPagePoster()
result = poster.post_text("Hello from Nhịp Quán Bot! 🤖")

if result.get("success"):
    print(f"Posted! ID: {result.get('post_id')}")
```

### Post Link

```python
result = poster.post_link(url="https://example.com", message="Check this out!")
```

### Get Post Stats

```python
info = poster.get_post_info(post_id)
print(f"Likes: {info['data']['likes']['summary']['total_count']}")
print(f"Comments: {info['data']['comments']['summary']['total_count']}")
```

## 📊 Test Suite Results

The `facebook_page_poster.py` script runs comprehensive tests:

1. ✅ Token Verification
2. ✅ Text Post
3. ✅ Post Info Retrieval
4. ✅ Link Post

## 🔒 Security Best Practices

✅ **DO:**
- Store token in `.env` (gitignore)
- Use environment variables in code
- Rotate tokens periodically
- Use separate tokens for dev/prod

❌ **DON'T:**
- Share token in chat/email
- Commit token to Git
- Hardcode token in scripts
- Expose token in logs

## 📚 Facebook API Resources

- [Graph API Reference](https://developers.facebook.com/docs/graph-api)
- [Page Publishing Guide](https://developers.facebook.com/docs/graph-api/reference/page/feed)
- [Access Token Types](https://developers.facebook.com/docs/facebook-login/access-tokens)
- [Token Debugger](https://developers.facebook.com/tools/debug/token)

## 🆘 Troubleshooting

### Error: "Cannot parse access token"
- Token was copied incorrectly
- Solution: Copy complete token without spaces/quotes
- Run: `python scripts/FACEBOOK_SETUP_GUIDE.py`

### Error: "Missing pages_manage_posts permission"
- Token doesn't have publishing permission
- Solution: Regenerate token with full permissions
- Must confirm `pages_manage_posts` in permission dialog

### Error: "Not admin of page"
- You need admin/editor role on page
- Solution: Check Facebook Page Roles
- Add yourself as Admin if needed

### Error: "Rate limit exceeded"
- Posting too frequently
- Solution: Wait 60+ seconds between posts
- Check Facebook rate limiting docs

## 🎯 Make Commands

```bash
# Test Facebook API (read-only)
make test-fb

# Test posting to page
make test-fb-post
```

## ✅ Checklist Before Running

- [ ] Token has `pages_manage_posts` permission
- [ ] Token has `pages_read_engagement` permission
- [ ] You are admin/editor of the page
- [ ] Token is complete (150+ chars)
- [ ] No spaces or quotes in token
- [ ] Token is in `.env` file
- [ ] `.env` is in `.gitignore`
- [ ] App is in "Live" mode (not sandbox)

## 💡 Pro Tips

1. **Always regenerate token** if it fails - tokens can expire
2. **Use Token Debugger** to verify token has correct permissions
3. **Test in sandbox first** before production
4. **Keep backup tokens** for testing
5. **Monitor rate limits** when posting frequently

---

**Last Updated:** 2026-08-30
**Status:** Setup Guide Complete - Ready for Production
