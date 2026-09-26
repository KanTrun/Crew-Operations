# Runbook — Grand AI Experience Portfolio (replay 5 phút)

Mục tiêu: demo 5 ý tưởng AI hoạt động **offline trong replay** — không cần
live LLM, microphone, camera, WebGL hay mạng ngoài. Mọi số hiển thị đều là
`Mô phỏng/ước tính` kèm chip `Fixture replay`.

## Thời lượng: 90 giây → 5 phút (tuỳ nhịp)

## Chuẩn bị

```powershell
# 1) Contracts + fixture (một lần):
make contracts

# 2) Chạy API demo (replay, seed demo, bật role-switch demo):
$env:CA_AGENT_MODE='replay'
$env:NHIPQUAN_SEED_DEMO='true'
$env:NHIPQUAN_INBOX_SEED_FIXTURE='1'
$env:NHIPQUAN_EXPERIENCE_REPLAY_ROLE='1'
python scripts/demo_api.py

# 3) Web:
Push-Location apps/web
npm run build
npm run start -p 3001
Pop-Location
```

## Script demo 6 bước (theo Phase 07 integration contract)

| # | Diễn viên | Hành động | Trang | Kết quả |
|---|---|---|---|---|
| 1 | Khách | “Tôi thích ít ngọt, thơm trà, không sữa” | `/quanverse` → Flavor Universe | Gợi ý kèm lý do; allergy chỉ khi khách khai |
| 2 | Khách | Bấm “Đề xuất” sở thích bàn cửa sổ | `/quanverse` → PreferenceConsent | Draft chờ consent, có delete path |
| 3 | Nhân viên | Bấm “Báo vắng (fixture)” | `/quanverse/shift-rescue` | Danh sách an toàn + bị chặn kèm lý do |
| 4 | Quản lý | Chọn 2 preset → “Chạy mô phỏng” | `/quanverse/war-room` | Baseline + ≥2 option, “Đề xuất” → draft |
| 5 | Quản lý | “Tìm quyết định lặp lại” → shadow → xác nhận | `/quanverse/rules` | Candidate → playbook, KHÔNG tự kích hoạt |
| 6 | Bất kỳ | Hỏi “khách thích gì ở quầy?” | `/quanverse/spatial-memory` | Trả lời grounded kèm citation `mem_*` |
| 7 | Quản lý | Mở panel “Trợ lý Quánverse” ở CẢ 5 trang, đọc tab *Tóm tắt trang*, rồi hỏi 1 câu | bất kỳ trang `/quanverse*` | Tóm tắt bằng số THẬT của trang; câu trả lời kèm “Dựa trên N bản ghi”; trang trống thì nói rõ “không suy đoán” |

Cách chạy tự động (không UI):

```powershell
make contracts
$env:CA_AGENT_MODE='replay'; python scripts/demo_grand_experience.py
```

## Kiểm tra nhanh bằng e2e (Playwright, replay)

```powershell
Push-Location apps/web
npx playwright test e2e/grand-experience-replay.spec.ts
Pop-Location
```

## Fallback khi live bị lỗi

| Thành phần lỗi | Hành vi đã chuẩn |
|---|---|
| Live LLM | Replay/deterministic text response; không giả badge live |
| Microphone | Text composer + browser audio/replay |
| WebGL | 2D/isometric map hoàn chỉnh (cùng anchor id) |
| Camera | QR/manual anchor path (AR-lite) |
| API timeout | Lỗi tiếng Việt an toàn + retry; không duplicate action |
| Stale snapshot | Yêu cầu recompute; không confirm |

## Các endpoint chính

- `GET  /api/v1/experience/capabilities` — capability theo role (fail-closed)
- `GET  /api/v1/experience/map` — anchors read-only
- `POST /api/v1/experience/war-room/simulate|.../propose|.../confirm`
- `POST /api/v1/experience/shift-rescue/{intake,candidates,invite,respond,confirm}`
- `POST /api/v1/experience/rules/{discover,shadow-test,confirm,reject}`
- `POST /api/v1/experience/voice/turn` — grounded, không mutate
- `GET /api/v1/experience/quanverse/brief/{page}` — tóm tắt TẤT ĐỊNH của một trang
  (`living_map|war_room|shift_rescue|rules|spatial_memory`), không gọi LLM
- `POST /api/v1/experience/quanverse/ask` — hỏi đáp có căn cứ; replay trả lời tất
  định, live thì LLM chỉ diễn đạt brief và phải qua cổng grounding (ADR-021)
- `GET  /api/v1/experience/quanverse/snapshot` — bản chiếu theo role

## Rollback

Tắt flag (mặc định off khi chưa cần demo):
`QUANVERSE_ENABLED=0`, `QUANVERSE_WEBGL_ENABLED=0`, `QUANVERSE_AR_ENABLED=0`,
`NHIPQUAN_EXPERIENCE_READ_ADAPTER` không trỏ production. Các route cũ
(`/api/v1/ops/twin/*`, `/api/v1/cho-doi-ca`) không bị ảnh hưởng.