# NHỊP QUÁN — Design Guidelines

**Authority for all `apps/web` work.** Cook chạm UI phải đọc file này trước, rồi chạy `/ak:ui-ux-pro-max` → `/ak:frontend-design`.

## Product

Cafe ops PWA: xếp ca, phiếu mở/đóng quán một tay, chợ đổi ca, cẩm nang, fairness — không marketing landing làm surface chính.

## Register

| Surface | Register | Bar |
|---------|----------|-----|
| App quản lý / nhân viên | **Product** | Tin cậy kiểu Linear/Figma-fluent; mật độ thông tin |
| Slide / video demo sân khấu | Brand (hẹp) | Chỉ khi D dựng landing demo — không lẫn tokens app |

## Dials (Product)

| Dial | Value | Notes |
|------|------:|-------|
| DESIGN_VARIANCE | 3 | Lưới đều, không masonry art |
| MOTION_INTENSITY | 2 | 150–250ms state; tôn trọng `prefers-reduced-motion` |
| VISUAL_DENSITY | 6 | Hairline, mono cho số giờ/nợ; tránh card-stack |

## Color tokens (CSS variables)

Atmosphere: đêm quán / gỗ cháy nhẹ — **không** purple SaaS, **không** cream+terracotta cliché.

```css
:root {
  --nq-bg: #12100e;
  --nq-bg-elevated: #1c1814;
  --nq-surface: #241f1a;
  --nq-ink: #f3e6d4;
  --nq-ink-muted: rgba(243, 230, 212, 0.72);
  --nq-line: rgba(243, 230, 212, 0.18);
  --nq-accent: #c4a574;      /* primary action only */
  --nq-accent-ink: #1a140e;
  --nq-danger: #d45d4a;
  --nq-ok: #6f9b7a;
  --nq-warn: #d4a017;
  --nq-focus: #e8d5b5;
}
```

Accent chỉ cho primary CTA + selection + state — không tô cả hero.

## Typography

- Display / brand wordmark: serif biểu cảm (vd. `"Source Serif 4"`, `"Fraunces"`) — **không** Inter/Roboto/Arial làm mặt
- UI body: humanist sans hẹp (vd. `"Source Sans 3"`, `"IBM Plex Sans"`)
- Số lịch / nợ / giờ: `"IBM Plex Mono"` hoặc `"JetBrains Mono"`
- Base ≥ 16px; line-height body 1.5; ratio product 1.125–1.2

## Layout & interaction

- Mobile-first; phiếu chạy **một tay**: target ≥ 44×44px, thumb-zone CTA đáy màn
- Lưới lịch quản lý: desktop-first nhưng không vỡ < 1024
- Không card trong hero/demo shell; trong app: chỉ card khi là đơn vị tương tác thật
- Focus ring 2–4px `--nq-focus`; không `outline: none` trần
- Ảnh minh chứng phiếu: full-bleed trong bước, không collage

## Motion

- State change 150–250ms ease-out
- Không page-load stagger trên product screens
- `@media (prefers-reduced-motion: reduce)` → tắt transition không cần thiết

## AgentKit cook command (copy)

```text
/ak:ui-ux-pro-max "NHIP QUAN cafe shift PWA — roster, one-hand run-form, playbook, fairness"
/ak:frontend-design
/ak:frontend-development
/ak:web-testing
```

## Surfaces map (D sở hữu)

| Feature folder | Priority UX |
|----------------|-------------|
| `roster-grid` | Kéo-thả + chặn vi phạm tại chỗ |
| `run-form` | Một tay, camera 1 bấm |
| `swap-market` | 3 nhánh rõ ràng |
| `fairness` | Số dư 4 chiều — không xếp hạng tên |
| `playbook` / `sop-chat` | Citation bắt buộc |
| `today` | Tình trạng quán hôm nay |
| `agent-trace` | Đọc được cho giám khảo |

## Changelog

- 2026-08-21 — Seed từ brainstorm UI pipeline (phase-01); refine khi D ngồi ca thật.
