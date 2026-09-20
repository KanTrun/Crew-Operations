# ADR-018 — Progressive 3D fallback

## Status
Accepted (plan 260920-1442, Phase 06)

## Context
QUÁNVERSE/HỒN QUÁN muốn bản đồ sống. WebGL/3D có thể không khả dụng (thiết bị
cũ, reduced-motion, lỗi driver, e2e). Không được bắt buộc công nghệ để trải
nghiệm chính hoạt động.

## Decision
- **2D/isometric là canonical**: mọi acceptance phải pass ở 2D. WebGL/3D/AR là
  progressive enhancement.
- `SpatialMap`/`LivingMap`: phát hiện WebGL; thiếu → render `*2dFallback`
  với cùng anchor id + hành động. Không core acceptance nào yêu cầu WebGL,
  camera, mic hay live network.
- Camera motion chỉ T1/T2, tắt dưới `prefers-reduced-motion`.
- 3D budget: ≤50 objects, không allocate per-frame, p95 ≤200ms; vượt → tắt
  WebGL mặc định, 2D là demo tin cậy.

## Consequences
- Replay demo 5 phút chạy 100% 2D/text.
- AR-lite gated capability: lỗi camera/WebXR → fallback QR/manual anchor.

## Links
- `apps/web/src/ui/experience/spatial/SpatialMap.tsx`
- `apps/web/src/ui/experience/quanverse/LivingMap.tsx`
- `docs/design-guidelines.md` (reduced motion, typography)