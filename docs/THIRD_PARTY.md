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
| Zalo OA | Zalo OA ToS / bảng giá | **Gói miễn phí có thể không đủ / đổi** | 2026-08-27 | **Kênh tin ưu tiên (VN)** — runbook `docs/runbooks/zalo-oa-connect.md`; cần OA + token do quán tạo |
| Telegram Bot API | Telegram ToS | Free cho bot thông thường | 2026-08-27 | Kênh phụ cùng MessagePort; runbook `telegram-bot-connect.md` |
| Facebook Page / Graph | Meta Platform ToS | App Review + quyền Page | 2026-08-27 | Surface `/page-quan` riêng; trống tới khi có token — `facebook-page-connect.md` |
| Thu thập Google Maps / ShopeeFood / Grab | ToS từng nền tảng | Thu thập tự động **không** giả định được phép | 2026-08-21 | AG-VOC chỉ nhận phản hồi quán tự chuyển |
| Camoufox (Firefox chống-detect) | MPL-2.0 | Binary ~300MB sau `camoufox fetch`; không có API hạn mức | 2026-09-10 | Optional — tier cào browser-thật AG-TREND; Linux cần system deps (libgtk-3-0, libasound2, libdbus-glib-1-2, libx11-xcb1, fonts) — runbook `docs/runbooks/camoufox-scraping.md` |
| Pillow | MIT-CMU (HPND) | n/a | 2026-09-23 | Ảnh sản phẩm sinh **tại máy** — ADR-019. Đã có sẵn trong venv/CI qua `reportlab`; không gọi mạng nên không có hạn mức nào bị thu hồi |
| google-api-python-client | Apache-2.0 | Gmail API free tier: 1 tỷ quota units/ngày/project; 250 quota units/user/giây | 2026-09-19 | Quản lý Gmail (`ag_gmail`): đọc/gửi/labels/filters; cần OAuth client `NHIPQUAN_GMAIL_CLIENT_ID` |
| google-auth / google-auth-oauthlib | Apache-2.0 | n/a | 2026-09-19 | OAuth 2.0 flow cho Gmail; refresh token tự động |
| cryptography (Fernet) | Apache-2.0 / BSD-3-Clause | n/a | 2026-09-19 | Mã hoá OAuth token trong DB; key qua `NHIPQUAN_ENCRYPTION_KEY` |
| Space Grotesk (font) | SIL OFL 1.1 | n/a — file **commit trong repo** | 2026-09-25 | Tiêu đề. `apps/web/src/fonts/`; xem `README.md` cùng thư mục |
| IBM Plex Sans (font) | SIL OFL 1.1 | n/a — file **commit trong repo** | 2026-09-25 | Chữ đọc chính |
| IBM Plex Mono (font) | SIL OFL 1.1 | n/a — file **commit trong repo** | 2026-09-25 | Số liệu / mã / mono |

**Vì sao font được commit vào repo (khác các mục trên):** ba họ này tải từ Google
Fonts một lần rồi commit dưới dạng `.woff2`. Lý do: `next/font/google` tải font
**lúc build**, và trong Docker build của CI lời gọi đó vỡ
(`TypeError: Cannot read properties of null` ở `loader.js`) trong khi build ở máy
local vẫn xanh — lỗi ẩn tới tận bước deploy. Guideline
(`docs/design-guidelines.md` §Typography) cũng đã yêu cầu self-host để cổng §14.9
(demo chạy khi rút mạng) không vỡ. OFL 1.1 cho phép phân phối kèm sản phẩm, chỉ
cấm bán font riêng lẻ. Kích thước: 27 file, ~324 KB.

## Kết luận vận hành (không phải lời hứa marketing)

- Ngân sách **0 đồng** = không trả phí cloud bắt buộc; phụ thuộc free tier **dễ thu hồi** → thiết kế router đa nhà cung cấp + Ollama.
- Trước bảo vệ: C chụp lại trang giá/ToS và cập nhật cột Ngày kiểm.
