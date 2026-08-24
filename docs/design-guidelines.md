# NHỊP QUÁN — Design Guidelines v4 (Awwwards / Digital Art)

**Authority for all `apps/web` work. Phiên bản này thay thế v3 (Premium Ops) để hướng tới trải nghiệm nghệ thuật số (Digital Art) và Awwwards.**

## Product

Cafe ops PWA — **Digital Art Experience**: Biến hệ thống quản lý khô khan thành một tác phẩm nghệ thuật tương tác.
- **Hub/Login**: Scrollytelling, 3D/WebGL, Neo-Brutalism, Kinetic Typography.
- **Ops (phiếu, roster)**: Vẫn giữ tính utility nhưng nâng cấp với vi-tương-tác (micro-interactions) siêu mượt và page transitions.

## Dials

| Dial | Hub/Login | Ops (phiếu, roster) |
|------|-----------|---------------------|
| DESIGN_VARIANCE | 10 — Phá vỡ lưới (Broken Grids), Neo-brutalism | 6 — Lưới linh hoạt, overlapping |
| MOTION_INTENSITY | T3 — Cinematic, Scroll-driven, Physics-based | T1 — Fluid, Easing chuẩn |
| VISUAL_DENSITY | 9 — 3D, Shaders, Particles, Noise | 5 — Sạch, tập trung dữ liệu nhưng có điểm nhấn |

## Color & motif

Atmosphere: **Avant-Garde / Cyber-Physical**
- Màu sắc: Tương phản mạnh (High contrast), có thể dùng các màu neon hoặc pastel nổi bật trên nền tối/sáng gắt (Brutalism).
- Motif: Hạt (particles), nhiễu (grain/noise shader), biến dạng (distortion/glitch effect).
- Typography: Oversized, Kinetic (chuyển động liên tục).

## 1. Kỹ thuật cuộn và điều hướng đặc trưng

- **Scrollytelling & Parallax đa tầng**: Cuộn trang điều khiển timeline. Các layer chuyển động với tốc độ khác nhau, đối tượng zoom-in, xoay, lắp ghép theo pixel cuộn (dùng GSAP ScrollTrigger).
- **Smooth Scrolling**: Sử dụng Lenis để khử giật cục, tạo độ êm (inertia) cho mọi animation.
- **Horizontal / Split Scrolling**: Cuộn dọc nhưng nội dung trượt ngang hoặc hai nửa màn hình di chuyển ngược chiều.

## 2. Visual & Tương tác chuyên sâu

- **3D & WebGL Integration**: Tích hợp mô hình 3D tương tác realtime (React Three Fiber, Three.js). Xoay theo chuột, biến dạng vật lý.
- **Custom Cursor & Magnetic Effects**: Con trỏ chuột có độ trễ (lerp). Hiệu ứng "hút" (magnetic) khi gần nút/ảnh.
- **Kinetic Typography**: Chữ chạy vô tận (marquee), biến dạng theo tốc độ cuộn, vỡ hạt khi hover.
- **Shader & Distortion Effects**: WebGL shaders tạo hiệu ứng mặt nước, kính lúp khúc xạ, noise/grain retro khi hover ảnh.

## 3. Tư duy bố cục và nghệ thuật thị giác

- **Brutalism / Neo-Brutalism & Broken Grids**: Phá vỡ lưới truyền thống, khối hình đè lên nhau (overlapping), typography khổ lớn (oversized text), bất đối xứng.
- **Micro-interactions siêu mượt**: Mọi click/hover dùng easing tinh chỉnh (cubic-bezier nảy nhẹ hoặc quán tính cao).
- **Page Transitions liền mạch**: Không load trắng màn hình. Dùng hiệu ứng curtain swipe, morphing shape hoặc fade-scale (Framer Motion).

## Tech Stack Cốt Lõi

| Mảng | Công nghệ / Thư viện |
|---|---|
| Animation Engine | GSAP + ScrollTrigger, Framer Motion |
| 3D & Render Engine | Three.js, React Three Fiber (R3F) |
| Smooth Scroll | Lenis (`@studio-freight/react-lenis`) |
| Creative Coding | WebGL / GLSL Shaders, Canvas API |
| Styling | Tailwind CSS, clsx, tailwind-merge |

## Changelog

- 2026-08-24 — v4: Đại tu toàn diện sang hướng Awwwards / Digital Art (GSAP, Three.js, Lenis, Neo-brutalism).
