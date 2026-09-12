# Camoufox audit — các chức năng khác trong dự án

**Date:** 2026-09-12
**Câu hỏi:** Còn chức năng nào khác trong dự án áp dụng Camoufox được không?
**Kết luận:** **KHÔNG.** Camoufox đã phủ hết mọi bề mặt cào cần browser-thật. Mọi điểm HTTP ra ngoài còn lại đều dùng API chính thức hoặc bị cấm bởi PHAM_VI.md.

## Bảng audit toàn bộ điểm HTTP ra ngoài

| Module | Điểm đến | Loại | Áp dụng Camoufox? |
|---|---|---|---|
| `ag_trend.py` — TikTok | Google Bridge → TikWM → Camoufox → Apify → RSS | Cào web | ✅ Đã có (PR #42) |
| `ag_trend.py` — Threads | Official API → Google Bridge → Direct Jina → Camoufox → Apify → RSS | Cào web | ✅ Đã có (PR #42 + #43) |
| `ag_trend.py` — Google Trends VN/Global, Gen Z Media, Showbiz KOLs | RSS công khai | RSS | ❌ Không cần — RSS công khai, live-test OK (10-50 items) |
| `facebook_page.py` | `graph.facebook.com/v26.0` | API chính thức | ❌ Không cần — Graph API cho phép, không bị chặn |
| `messaging.py` | `api.telegram.org`, `openapi.zalo.me` | API chính thức | ❌ Không cần — Bot API chính thức |
| `llm.py` | `api.groq.com`, `openrouter.ai`, `generativelanguage.googleapis.com` | API chính thức | ❌ Không cần |
| `ag_meeting/stt.py` | `api.groq.com` (Whisper), `generativelanguage.googleapis.com` | API chính thức | ❌ Không cần |
| `clients/apify_client.py` | `api.apify.com` | API trả phí | ❌ Không cần — Apify tự lo browser bên phía họ |
| `ag_voc/` | Google Maps, ShopeeFood, Grab (lý thuyết) | Cào nền tảng đánh giá | ⛔ **BỊ CẤM** — PHAM_VI.md §6.2 cấm thu thập tự động (rủi ro ToS chưa xác minh), chỉ chấp nhận nội dung chủ quán dán vào |
| `apps/api/src/` | Không có client HTTP ra ngoài | — | ❌ Không áp dụng |
| `apps/web/src/lib/api.ts` | Chỉ gọi `localhost:8000` (API nội bộ) | Nội bộ | ❌ Không áp dụng |

## Lý do không mở rộng thêm

1. **Ranh giới pháp lý, không phải kỹ thuật:** AG-VOC là ứng viên kỹ thuật duy nhất còn lại, nhưng PHAM_VI.md cấm rõ ràng thu thập tự động từ nền tảng đánh giá. Muốn mở phải đổi PHAM_VI.md trước — quyết định của chủ quán, không phải của agent.
2. **Non-goals §2.2 của plan gốc:** plan `260910-1610-trend-camoufox-integration` chỉ scope AG-TREND. Mở rộng sang agent khác là đổi scope, phải có plan mới.
3. **API chính thức không cần browser:** các module còn lại đều gọi endpoint chính thức có key/token — Camoufox không mang lại giá trị ở đó, chỉ thêm rủi ro.

## Verify

- 396/396 tests pass trên main sau merge PR #45 (`02188ad`)
- Audit bằng grep toàn bộ `https?://` trong `packages/agents/src/ca_agents`, `apps/api/src`, `apps/web/src` — không sót điểm ra ngoài nào
