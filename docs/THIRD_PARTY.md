# Third-party & free-tier — ngày kiểm 2026-08-21

| Thành phần | Giấy phép / hạng | Hạn mức (theo trang công bố lúc kiểm) | Ngày kiểm | Ghi chú vận hành |
|------------|-----------------|----------------------------------------|-----------|------------------|
| FastAPI | MIT | n/a | 2026-08-21 | API |
| Next.js | MIT | n/a | 2026-08-21 | Web |
| Pydantic | MIT | n/a | 2026-08-21 | Contracts |
| PostgreSQL image | PostgreSQL License | n/a | 2026-08-21 | Docker |
| Redis image | RSALv2 / SSPLv1 (image) / client BSD | n/a | 2026-08-21 | Chỉ dùng local/dev |
| OR-Tools | Apache-2.0 | n/a | 2026-08-21 | Xác nhận lại file LICENSE trong release dùng |
| Google AI Studio / Gemini free | ToS Google | Có hạn mức ngày/phút — **không** cam kết “vĩnh viễn” | 2026-08-21 | Router phải có fallback Ollama |
| Groq free tier | ToS Groq | Rate limit thay đổi theo thời điểm | 2026-08-21 | Không phụ thuộc một nhà cung cấp |
| OpenRouter free models | ToS OpenRouter | Hạn mức credit free thay đổi | 2026-08-21 | Ghi `make budget` tuần |
| Ollama local | MIT (phần mềm) | Phụ thuộc máy đội | 2026-08-21 | Phương án B khi hết hạn mức cloud |
| Telegram Bot API | Telegram ToS | Free cho bot thông thường | 2026-08-21 | Backend tin nhắn chính |
| Zalo OA | Zalo OA ToS / bảng giá | **Gói miễn phí có thể không đủ / đổi** | 2026-08-21 | Port messaging: console+Telegram bắt buộc; Zalo optional |
| Thu thập Google Maps / ShopeeFood / Grab | ToS từng nền tảng | Thu thập tự động **không** giả định được phép | 2026-08-21 | AG-VOC chỉ nhận phản hồi quán tự chuyển |

## Kết luận vận hành (không phải lời hứa marketing)

- Ngân sách **0 đồng** = không trả phí cloud bắt buộc; phụ thuộc free tier **dễ thu hồi** → thiết kế router đa nhà cung cấp + Ollama.
- Trước bảo vệ: C chụp lại trang giá/ToS và cập nhật cột Ngày kiểm.
