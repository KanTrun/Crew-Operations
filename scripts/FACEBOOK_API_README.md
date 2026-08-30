# Facebook API Test Guide

## ⚠️ Bảo Mật Token

**Token của bạn đã bị expose!** Thực hiện ngay:

### 1. Revoke Token Cũ
- Đi đến: [Facebook App Dashboard](https://developers.facebook.com/apps)
- Chọn App của bạn → Settings → Basic
- Hoặc: Người dùng → Settings → Apps and Websites
- Revoke/remove app access

### 2. Sinh Token Mới
```
Facebook App Dashboard
  → Your App
  → Tools & Support → Token Debugger
  → hoặc: Settings → Basic → Generate new token
```

### 3. Lưu Token An Toàn
```bash
# .env file (gitignore)
FACEBOOK_ACCESS_TOKEN=YOUR_NEW_TOKEN_HERE
FACEBOOK_APP_ID=YOUR_APP_ID
FACEBOOK_APP_SECRET=YOUR_APP_SECRET
```

## 🚀 Cách Sử Dụng Script Test

### Cài đặt dependencies
```bash
pip install python-dotenv requests
```

### Chạy test suite
```bash
python scripts/test_facebook_api.py
```

### Output sẽ bao gồm:
1. ✅ Get My Accounts & Pages
2. ✅ Get User Info  
3. ✅ Get Page Info
4. ✅ Get Page Feed Posts

## 📋 API Endpoints Được Test

| Endpoint | Mô tả |
|----------|-------|
| `me/accounts` | Lấy tất cả pages/accounts bạn quản lý |
| `me` | Thông tin user hiện tại |
| `{page_id}` | Thông tin chi tiết page |
| `{page_id}/feed` | Posts trên page |

## 🔒 Best Practices

❌ **Không bao giờ:**
- Share token trong code, chat, hay công khai
- Commit token vào git
- Hardcode token trong app

✅ **Luôn:**
- Lưu token trong `.env` (gitignore)
- Reference qua `os.getenv("FACEBOOK_ACCESS_TOKEN")`
- Rotate token định kỳ
- Use separate tokens cho dev/prod

## 📚 Useful Links
- [Facebook Graph API Docs](https://developers.facebook.com/docs/graph-api)
- [Access Token Types](https://developers.facebook.com/docs/facebook-login/access-tokens)
- [Token Debugger](https://developers.facebook.com/tools/debug/token)
