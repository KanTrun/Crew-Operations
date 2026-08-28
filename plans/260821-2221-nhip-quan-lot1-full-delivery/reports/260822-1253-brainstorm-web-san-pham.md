---
title: Brainstorm — web sản phẩm + đóng phase còn lại
date: 2026-08-22
---

# Hợp đồng

**Outcome:** Web là OS vận hành (hub Hôm nay, nav theo vai ≤5, tiếng Việt sạch), nối API thật, sổ tiêu thụ + các mặt hồ sơ D. Plan 04–07 ghi software-complete; 08–09 vẫn pending vì cổng người/cuộc thi.

**Constraints:** ADR-012 không bịa quán; design-guidelines dials 3/2/6; không mock copy; không viết/chạy test lần này.

**Non-goals:** Fake §14.4–14.9; tag semifinal/final; AG-VOC/EXPLAIN/BRIEF giả; 165–215 tests; merge/ship.

**Acceptance:** Login → Hôm nay; NV thấy phiếu/ca/treo; QL thấy lịch/hộp thư/cẩm nang; không dump link; empty state trung thực; plan không đánh dấu 08–09 xong.

# Hướng đã chọn

Làm sâu IA + nối API có sẵn, thêm sổ tiêu thụ (không agent) và runbook — không bịa agent còn thiếu.

# Câu hỏi còn mở

- Ship/merge PR khi nào?
- Ai chạy walkthrough điện thoại và gắn quán?
