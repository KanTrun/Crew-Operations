# NHỊP QUÁN — Design Guidelines v3 (Premium Ops)

**Authority for all `apps/web` work.**

## Product

Cafe ops PWA — register **Product Premium**: studio-grade trên shell/hub/login; utilitarian trên phiếu/roster.

## Dials

| Dial | Hub/Login | Ops (phiếu, roster) |
|------|-----------|---------------------|
| DESIGN_VARIANCE | 5 — bento, motif | 3 — lưới đều |
| MOTION_INTENSITY | T2 editorial / T1 ambient | T0 functional |
| VISUAL_DENSITY | 7 — glass, glow | 6 — hairline |

## Color & motif

Atmosphere: **đêm quán / đồng / gỗ cháy** — grain overlay 4%, steam-line pattern, accent copper `#c4a574` with OKLCH hover drift.

## Layout

- `--nq-max`: `min(1200px, 100%)` desktop hub; mobile 1 cột
- Bento grid 12-col trên `/hom-nay`
- Progressive disclosure: hero = human line; technical (solver, raw state) = drawer

## Shape & depth (bubble register)

| Token | Giá trị | Dùng ở đâu |
|---|---|---|
| `--nq-radius` | 6px | **chỉ** input, select, ô bảng roster — bo lớn ở bảng số liệu làm mắt mất hàng |
| `--nq-radius-bubble` | 18px | card, tile, item, ops-card, alert, notice, empty, drawer |
| `--nq-radius-pill` | 999px | button, tab, chip, nav item, thanh nổi |
| `--nq-radius-sheet` | 24px | sheet lớn (banner trong thẻ login) |
| `--nq-shadow-bubble` / `-hover` | 2 lớp | bóng gần + bóng xa, không dùng bóng đơn |
| `--nq-inner-hi` | `inset 0 1px 0 rgba(255,255,255,.06)` | viền sáng 1px trên cùng mọi bề mặt nổi |
| `--nq-blur-glass` | `blur(20px) saturate(1.3)` | thanh trên, thanh dưới, panel nổi |
| `--nq-press` / `--nq-dur-press` | 0.97 / 180ms | lún khi bấm, `--nq-ease-spring`; khối `prefers-reduced-motion` đặt `--nq-press: 1` |
| `--nq-safe-b/l/r` | `env(safe-area-inset-*)` | thanh nổi tách khỏi đáy và lề máy |

Thanh dưới là **pill nổi** tách khỏi đáy (không dán mép): mép dưới màn hình là
vùng gesture bar của máy, dán vào đó là mời người dùng bấm trượt. Trên máy nhỏ
thanh hành động của phiếu nâng lên trên thanh điều hướng, không đè nhau.

## Disclosure rules

- Login: **không** in credential trên UI prod — runbook `docs/runbook-demo.md`
- Hub: một dòng hero; meta có `nguồn quán` (e2e) — in **một lần**, không lặp ở
  cả banner và meta-strip; solver trong drawer
- Mã dùng-một-lần (điểm danh QR): hiện dạng che `•••• •••• 1234`, nội dung thật
  chỉ đi qua clipboard
- JSON hợp đồng, mã cổng VF, mã lần chạy phiếu: trong `TechnicalDrawer`, mặc định đóng
- `/cong-bang`: mỗi người **chỉ** thấy số dư của mình so với trung bình nhóm.
  Máy chủ trả số dư cả nhóm cho vai quản lý — UI chủ động bỏ, không xếp hạng tên (§13.4)
- Lỗi: mọi lỗi đi qua `viError()` trong `src/lib/present.ts` — câu tiếng Việt +
  hành động kế tiếp, phân nhánh mất mạng/401/403/404/409/422/5xx. Không mã HTTP,
  không tên biến, không JSON lỗi trên UI
- Mã trạng thái nội bộ (`cho_duyet`, `ag_msg`, `pin_ca`, `hieu_luc`…) phải qua
  bảng nhãn trong `present.ts`; `null`/`undefined`/object đi qua `safeText()` nên
  không có đường ra cho `[object Object]`

## Motion tiers

T0 160ms · T1 220ms · T2 480ms · `prefers-reduced-motion` tắt animation

## Kit (`src/ui/kit.tsx`)

`EditorialBanner`, `BentoTile`, `TechnicalDrawer`, `PageHeader`, `Btn`, `TabBar`, `OpsCard`, `FixedBottomBar`, `StatusChip`, `Loading`/skeleton, `BtnLink`, `PageActions`

## Two-register sweep (v3.1)

| Register | Routes | Motion |
|----------|--------|--------|
| **Premium hub** | `/`, `/login`, `/hom-nay` | T1–T2 editorial |
| **Ops utilitarian** | all other authenticated routes | T0 functional, shared kit |

## Typography — self-host, không CDN

Font nạp qua `next/font` trong `apps/web/src/ui/fonts.ts`, **không** dùng
`<link>` tới `fonts.googleapis.com`.

| Vai trò | Font | Subset |
|---|---|---|
| Display | Fraunces 400/600 | latin, latin-ext, **vietnamese** |
| Body | Source Sans 3 400/600 | latin, latin-ext, **vietnamese** |
| Mono | IBM Plex Mono 400/500 | latin, latin-ext |

Hai lý do, cả hai đều là ràng buộc cứng:

1. **Cổng ra Sprint 8 (§14.9)** yêu cầu demo chạy trọn 10 phút khi đã rút mạng.
   Font CDN làm chữ rơi về Georgia/system-ui ngay giữa buổi bảo vệ.
2. **Phải có subset `vietnamese`.** Thiếu nó thì chữ có dấu render bằng font
   fallback, và cả trang trông chắp vá dù token màu/khoảng cách vẫn đúng.

Kiểm lại sau mỗi lần đổi font:

```
cd apps/web ; npx next build
# .next/static/media phải có file .woff2
# HTML đã render phải có 0 tham chiếu fonts.googleapis / fonts.gstatic
```

## Icon

`apps/web/src/ui/icons.tsx` — SVG inline, 24×24, `currentColor`, stroke 1.5.
Không thêm dependency icon, không dùng emoji (xem mục cấm). Icon mang
`aria-hidden` vì nhãn chữ luôn đi kèm; `iconForHref()` suy icon từ route.

## Changelog

- 2026-08-23 — Register bubble/glass kiểu iOS (token radius/shadow/blur/press, thanh dưới pill nổi + safe-area); kiểm duyệt hiển thị toàn 19 route: lớp `src/lib/present.ts` (lỗi tiếng Việt + nhãn trạng thái + `safeText`), `ApiError` mang mã HTTP, mã QR che, JSON `/contracts` vào drawer, `/cong-bang` chỉ còn số dư của chính người xem
- 2026-08-23 — Font self-host qua `next/font` (+ subset vietnamese) sửa cổng demo offline; bộ icon SVG inline cho nav + thanh dưới; skip-link; `<main id="nq-content">`; `viewport.maximumScale=5` để không chặn zoom
- 2026-08-23 — v3.1 full-site sweep: PageHeader/Btn/TabBar on all 19 routes; phieu run-form + roster table CSS
- 2026-08-23 — v3 Premium Ops (international studio bar, bento, disclosure, motif)
