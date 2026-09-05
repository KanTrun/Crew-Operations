# Runbook — Chatbot Fanpage có kiểm duyệt (AG-FBPAGE Moderation)

> Áp dụng cho luồng tin nhắn Messenger Fanpage Nhịp Quán. Thiết kế chi tiết:
> `plans/260903-2230-chatbot-fbpage-moderation-chuyen-nghiep/KE-HOACH-Chatbot-FBPage-KiemDuyet-DAYDU.md`.
> Chuẩn ADR: ADR-002 (tất định) · ADR-008 (người quyết, có dấu vết).

## 1. Pipeline tóm tắt (5 lớp cổng)

```
Webhook Meta
  → L0  lọc is_echo (bot không tự trả lời chính mình) · idempotency mid (Meta retry)
        · lọc entry.id = NHIPQUAN_FB_PAGE_ID
  → L1  guardrail (prompt injection, control chars)
  → L2  rate limit 5 tin/phút, 30 tin/giờ · sổ đen PSID (3 vi phạm → chặn 24h)
  → L3  phân loại intent (từ khóa tất định)
  → L4  fb_policy.decide() — bảng ma trận §3.2, không LLM
  → L5  supervisor (cấm hứa KM/tài chính, lộ nội bộ, câu robot) — hạ AUTO → QUEUE nếu flag
Kết quả: AUTO_SEND (flag ON + supervisor pass) | QUEUE (QL duyệt) |
         PRIORITY (QL, SLA 5′) | ESCALATE (Chủ quán, SLA 15′) | BLOCK_* (không trả lời)
```

## 2. Bật / tắt auto-send

**Bật (Chủ quán):**
- API: `PUT /api/v1/page/fb-policy` body `{"auto_send_enabled": true}` (chỉ role `chu_quan`)
- Hoặc env: `NHIPQUAN_FB_AUTO_SEND=1` rồi restart API

**Tắt (khẩn cấp — trong vài giây):**
- API: `PUT /api/v1/page/fb-policy` body `{"auto_send_enabled": false}`
- Mọi tin auto-able tiếp theo chuyển sang **pending** cho QL duyệt tay; không ghi `auto_sent`

**Rollback sự cố:** tắt flag là đủ. Không cần rollback DB (schema additive).

## 3. Duyệt tin hàng ngày (UI)

1. Vào **More → Hộp thư Fanpage (duyệt)** (`/page-quan/fb-inbox`) — role Quản lý trở lên.
2. Card đỏ viền = quá SLA. Chip "Báo chủ quán" = chỉ Chủ quán duyệt được.
3. Ba hành động: **Duyệt & gửi** (gửi đúng nháp) · **Sửa rồi gửi** · **Từ chối**.
4. Mọi quyết định ghi audit (`fb_inbox_decide`) — ai duyệt, nội dung cuối gửi gì.

## 4. Leo thang escalation

- Tin chứa từ khóa an toàn (ngộ độc, trẻ em, thai sản, hóa đơn đỏ, hoàn tiền, gặp chủ…)
  → `escalate_owner`, đẩy vào `fb_escalation_log` (chưa ack).
- QL **không** duyệt được tin gán `chu_quan` (403). Chủ ack bằng cách duyệt trong inbox.
- Kiểm tra escalation chưa xử lý: `GET /api/v1/page/fb-inbox/stats` → `escalation_unacked`.

## 5. Chẩn đoán sự cố

| Hiện tượng | Nguyên nhân | Xử lý |
|---|---|---|
| Webhook trả `page_chua_live` | Thiếu `NHIPQUAN_FB_PAGE_TOKEN` / mode không live | Đặt token + `NHIPQUAN_PAGE_MODE=live` |
| `invalid_signature` (403) | `NHIPQUAN_FB_APP_SECRET` lệch hoặc Meta đổi secret | So lại App Secret trong Meta App Dashboard |
| Tin không vào pipeline | Meta retry trùng `mid` (bình thường) hoặc entry sai Page ID | Xem bảng `fb_processed_events` |
| Khách phàn nàn bot trả lời ngáo | Nháp auto sai | Tắt flag ngay (mục 2) → tra `fb_review_queue` theo PSID → thêm keyword escalate + PR golden case |
| Bị flood | Spam PSID | Kiểm tra `fb_psid_blacklist`; chỉnh limit qua `fb_rate_limiter.py` (đổi phải PR) |
| Auto rate lệch (`/stats`) | < 30%: policy chặt · > 75%: whitelist rộng | Rà confusion matrix của eval (mục 6) |

## 6. Eval & CI

```bash
# Chạy golden eval (ít nhất 60 case, cần GREEN với 0 hard-fail):
set PYTHONIOENCODING=utf-8 && python scripts/eval_fb_moderation.py
```

- Fixtures: `data/fixtures/fb_moderation_golden.jsonl` — **thêm case mới kèm PR** khi gặp tình huống thật.
- RED build nếu: ít hơn 60 case, 1 case escalate/block sai, hoặc pass rate < 95%.
- Unit tests: `apps/api/tests/unit/test_fb_moderation.py`, `test_fb_policy_api.py`, `packages/agents/tests/test_fb_policy.py`, `test_fb_rate_limiter.py`.

## 7. Chỉnh chính sách

| Muốn đổi | Làm ở đâu | Ai |
|---|---|---|
| Bật/tắt auto | `PUT /api/v1/page/fb-policy` hoặc env | Chủ quán |
| Trần giá auto | `{"auto_price_cap_vnd": N}` cùng endpoint | Chủ quán |
| Ngưỡng conf từng intent / SLA / danh sách keyword escalate | `packages/agents/src/ca_agents/fb_policy.py` | PR mới (quyết định kinh doanh — có golden case kèm theo) |
| Thêm case test | `data/fixtures/fb_moderation_golden.jsonl` | PR kèm mô tả tình huống thật |

## 8. Trách nhiệm

| Vai | Việc |
|---|---|
| Quản lý | Duyệt inbox ≥ 2 lần/ngày giờ cao điểm; xử lý priority ≤ 5 phút |
| Chủ quán | Duyệt escalation ≤ 15 phút; giữ flag auto-send tắt khi vắng người trực |
| Dev trực | Theo `/stats` daily; phản hồi alert; PR keyword mới khi có sự cố văn bản |
