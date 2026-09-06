---
name: vf-gates-audit
description: "Kỹ năng thẩm định đề xuất của AI Agent qua hệ thống cổng kiểm duyệt an toàn Fail-Closed (VF-SCHEMA, VF-TRACE, VF-CONF)."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/gates
---

# VF Gates Audit Skill

Kỹ năng kiểm tra an toàn theo nguyên tắc **Fail-Closed**: ngăn chặn toàn bộ các đề xuất đổi ca, sửa lịch hoặc trả lời sai lệch mà không có bằng chứng rõ ràng.

## 1. Kiểm tra nhanh (Smoke Check)

Chạy script thẩm định với dữ liệu kiểm thử:

```bash
python skills/repositories/repo-skills/vf-gates-audit/scripts/run_fail_closed_audit.py
```

## 2. Các cổng kiểm tra

Xem chi tiết tại [references/vf_rules.md](references/vf_rules.md):
- **VF-SCHEMA:** Bắt buộc có đủ các khóa đầu ra theo hợp đồng JSON Schema.
- **VF-TRACE:** Mọi dữ liệu (tên nhân viên, giờ, lý do) phải trích xuất được từ câu chat gốc (grounded).
- **VF-CONF:** Điểm tin cậy phải đạt $\ge 0.70$.

## 3. Quy trình thực thi cho Agent

1. Sau khi trích xuất thông tin từ tin nhắn hoặc yêu cầu người dùng, đóng gói thành đối tượng `{extraction, evidence, schema_keys}`.
2. Thực thi script `scripts/run_fail_closed_audit.py`.
3. **Phân nhánh kết quả:**
   - `passed = True`: Tiến hành tạo phiếu đề xuất gửi người quản lý phê duyệt.
   - `retry_once = True`: Agent tự động suy luận lại 1 lần duy nhất để hoàn thiện schema.
   - `escalate = True`: Từ chối tự động xử lý, cảnh báo rõ lý do vi phạm cho người quản lý.
