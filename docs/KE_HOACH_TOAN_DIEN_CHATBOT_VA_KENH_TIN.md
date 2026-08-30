# KẾ HOẠCH TOÀN DIỆN & NÂNG CAO: HỆ THỐNG CHATBOT FACEBOOK & KÊNH TIN VẬN HÀNH NHÂN VIÊN
**Dự án:** NHỊP QUÁN (Crew-Operations)  
**Phiên bản:** v2.0 (Đã hoàn thiện Bảo mật, Guardrails, 2-Phase Confirmation & Audit)  
**Ngày cập nhật:** 30/08/2026  
**Trạng thái:** Sẵn sàng triển khai (Production-Ready)  

---

## 📌 1. TỔNG QUAN VÀ TẦM NHÌN KIẾN TRÚC

Hệ thống tin nhắn của **Nhịp Quán** vận hành theo mô hình phân tách độc lập giữa Khách hàng (Đối ngoại) và Nhân sự (Nội bộ), với lõi điều phối tất định (deterministic) và có sự tham gia của con người (Human-in-the-loop):

```
                              ┌────────────────────────────────────────────────────────┐
                              │                 NGƯỜI DÙNG TƯƠNG TÁC                   │
                              └───────────┬────────────────────────────────┬───────────┘
                                          │                                │
                       [Khách hàng vãng lai / Đặt món]             [Nhân viên quán đã bind ID]
                                          │                                │
                                          ▼                                ▼
                              ┌──────────────────────┐         ┌──────────────────────┐
                              │  FACEBOOK MESSENGER  │         │   ZALO OA / TELEGRAM │
                              └───────────┬──────────┘         └───────────┬──────────┘
                                          │ (Input Guardrail)              │
                                          ▼                                ▼
                              ┌──────────────────────┐         ┌──────────────────────┐
                              │ AG-FBPAGE (CSKH Bot) │         │ AG-MSG (Vận hành ca) │
                              │ + Whitelist Tools    │         │ + 2-Phase Confirm    │
                              └───────────┬──────────┘         └───────────┬──────────┘
                                          │                                │
             ┌────────────────────────────┴─────────────┐                  │
             │                                          │                  │
    (Confidence >= 0.82)                       (Nhạy cảm / Đặt bàn)        │
             ▼                                          ▼                  ▼
┌───────────────────────────┐                ┌────────────────────────────────────────┐
│  Trả lời tự động tức thì  │                │     HỘP THƯ DUYỆT CỦA QUẢN LÝ (WEB)    │
│  (Menu, Giá, Giờ mở cửa)  │                │   • /page-quan (Duyệt tin nhắn khách)  │
└───────────────────────────┘                │   • /inbox (Duyệt xin nghỉ, đổi ca NV) │
                                             └────────────────────┬───────────────────┘
                                                                  │
                                                                  ▼
                                                     ┌────────────────────────┐
                                                     │  PREVIEW DIFF TRƯỚC   │
                                                     │  LÕI SOLVER (CP-SAT)   │
                                                     │  Cập nhật lịch phân ca │
                                                     └────────────────────────┘
```

---

## 🔒 2. BẢO MẬT & MÔ HÌNH PHÂN VÙNG DỮ LIỆU NÂNG CAO

### 2.1. Phòng chống Prompt Injection & Data Exfiltration
- **Input Guardrails:** Bộ lọc tiền xử lý phát hiện các mẫu tấn công ép AI bỏ qua luật (`ignore previous instructions`, `system prompt`, `dump database`).
- **Tool Whitelist Bất biến:** AI chỉ được quyền gọi 3 hàm Read-only công khai:
  1. `get_public_menu()`: Tên món, Giá bán, Mô tả (Đã lược bỏ hoàn toàn BOM nguyên liệu & Giá vốn).
  2. `get_store_profile()`: Giờ mở/đóng cửa, Địa chỉ, Hotline, Wifi.
  3. `get_active_promotions()`: Danh sách ưu đãi và điều kiện áp dụng.

### 2.2. Cơ chế Định danh Nhân viên `/bind` Chống Brute-force
- **Mã OTP 6 số:** Thời gian sống ngắn (**5 phút**), tự hủy sau **1 lần sử dụng thành công**.
- **Rate-limit & Khóa an toàn:** Cho phép tối đa **5 lần thử sai** cho mỗi tài khoản chat. Vượt quá ngưỡng sẽ khóa xác thực 15 phút.
- **Audit định danh:** Ghi nhật ký chi tiết: `(external_user_id, nv_id, created_at, expire_at, bind_status)`.

---

## 👥 3. NGHIỆP VỤ & QUY TRÌNH XỬ LÝ ĐẶC THÙ

### 3.1. Luồng Đổi ca (`doi_ca`) Xác nhận 2 Chiều (2-Phase Confirmation)
Nhân viên A không thể đơn phương đổi ca của bạn B mà không có sự đồng thuận.
1. **Bước 1 (Đề xuất):** Nhân viên A nhắn: *"Em muốn đổi ca chiều thứ 3 cho bạn Minh"*.
2. **Bước 2 (Xác nhận từ người nhận):** Hệ thống tự động gửi tin nhắn đến nick Zalo/Telegram của Minh: *"Bạn Lan muốn đổi ca Chiều T3 với bạn. Nhắn `/dong_y` hoặc `/tu_choi`"*.
3. **Bước 3 (Đẩy lên Quản lý):** Chỉ khi bạn Minh xác nhận `/dong_y`, phiếu yêu cầu mới được đưa vào `/inbox` để Quản lý duyệt cuối cùng.

### 3.2. Xử lý Chính sách Cửa sổ 24 Giờ của Meta (24-Hour Policy)
Khi Quản lý duyệt tin nhắn đặt bàn/yêu cầu của khách sau 24h:
- **Trong 24h:** Gửi tin nhắn thông thường qua Facebook Send API.
- **Ngoài 24h (Đặt bàn):** Tự động đính kèm Message Tag: `CONFIRMED_EVENT_UPDATE` (hợp lệ theo chuẩn chính sách Meta).
- **Trường hợp ngoài danh mục Tag:** Giao diện `/page-quan` hiển thị cảnh báo đỏ: *"Hội thoại đã quá hạn 24h - Vui lòng gọi điện trực tiếp cho khách theo số [SĐT]"*.

### 3.3. Cơ chế Fallback khi LLM / Dịch vụ AI gặp sự cố
- **Timeout ngắn:** Đặt ngưỡng phản hồi tối đa **3.0 giây** cho API LLM.
- **Graceful Degradation:**
  - Nếu LLM quá 3s hoặc sập mạng $\rightarrow$ Chuyển ngay sang **Rule-based Keyword Matching**.
  - Nếu không khớp từ khóa $\rightarrow$ Gửi câu trả lời giữ chân khách hàng lịch sự (*"Quán đã nhận được tin nhắn và quản lý sẽ phản hồi bạn ngay nhé!"*) đồng thời đưa cuộc trò chuyện vào tab **Chờ xử lý** trên `/page-quan`.

---

## ⚙️ 4. KIỂM THỬ ĐỊNH LƯỢNG & ĐIỀU PHỐI LỊCH (SOLVER)

### 4.1. Cơ sở Thiết lập Ngưỡng Tin cậy (Confidence Threshold)
- Xây dựng bộ dữ liệu đánh giá chuẩn (**Golden Benchmark Dataset** gồm 150+ mẫu tin nhắn tiếng Việt có gán nhãn).
- Đo lường ma trận phân loại (Confusion Matrix) với các chỉ số **Precision, Recall, F1-Score**.
- **Ngưỡng vận hành:**
  - $\ge 0.82$ kèm Intent Precision $\ge 95\%$: Tự động trả lời (Auto-reply).
  - $0.50 \le \text{score} < 0.82$: Chuyển về chế độ gợi ý câu trả lời để Quản lý duyệt 1-click.
  - $< 0.50$: Đánh dấu "Cần nhân viên hỗ trợ trực tiếp".

### 4.2. Duyệt Lịch Ca & Xem trước So sánh (Diff Preview)
- Khi Quản lý duyệt yêu cầu xin nghỉ/đổi ca, Lõi Solver (CP-SAT) chạy bất đồng bộ để tính phương án thay thế.
- **Không tự động commit:** Hệ thống hiển thị bảng so sánh (Diff Preview):
  - *Lịch hiện tại vs Lịch đề xuất mới*.
  - *Danh sách nhân viên bị ảnh hưởng (nếu có)*.
- Quản lý kiểm tra và nhấn **"Xác nhận áp dụng lịch mới"** mới chính thức ghi đè vào DB và gửi thông báo cập nhật cho các nhân viên liên quan.

### 4.3. Audit Trail Chi tiết & Minh bạch
Mọi hành động đều được lưu vào bảng `audit` với đầy đủ thông tin:
```json
{
  "at": "2026-08-30T14:30:00Z",
  "ai": "quan_ly_lan",
  "hanh": "duyet_tin_nhan_cskh",
  "payload": {
    "thread_id": "t_fb_98234",
    "customer_msg": "Bàn 10 người tối nay có phụ thu không?",
    "ai_suggested_reply": "Dạ quán không phụ thu bàn đông người ạ...",
    "manager_final_reply": "Dạ quán không phụ thu ạ, quán đã chuẩn bị bàn tầng 2 cho anh/chị nhé!",
    "diff_detected": true
  }
}
```

---

## 🛠️ 5. DANH SÁCH FILE VÀ LỘ TRÌNH TRIỂN KHAI

| STT | File cần tạo / chỉnh sửa | Nhiệm vụ kỹ thuật |
| :---: | :--- | :--- |
| 1 | `apps/api/src/ca_api/services/store_public_context.py` *(Mới)* | Provider dữ liệu công khai sạch: menu, giờ mở cửa, khuyến mãi (kèm cache in-memory). |
| 2 | `packages/agents/src/ca_agents/guardrails.py` *(Mới)* | Bộ lọc tiền xử lý chống Prompt Injection và whitelist tools. |
| 3 | `packages/agents/src/ca_agents/ag_fbpage.py` | Agent xử lý tin nhắn khách, tích hợp confidence threshold và fallback rule. |
| 4 | `packages/agents/src/ca_agents/facebook_page.py` | Xử lý Webhook signature HMAC-SHA256, Message Tag `CONFIRMED_EVENT_UPDATE`, và kiểm soát 24h. |
| 5 | `apps/api/src/ca_api/interfaces/http/channels.py` | API Webhook, cơ chế `/bind` OTP 5 phút kèm rate-limit, luồng xác nhận đổi ca 2 bên. |
| 6 | `apps/web/src/app/page-quan/page.tsx` | UI Hộp thư Fanpage, Duyệt tin nhắn, Cảnh báo 24h và Chat trực tiếp. |
| 7 | `apps/web/src/app/inbox/page.tsx` | Bổ sung Preview Diff Lịch ca trước khi áp dụng kết quả từ Solver. |