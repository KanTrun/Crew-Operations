# Walkthrough Sprint 3 — phiếu trên điện thoại thật

Checklist **15 phút** để chứng minh cổng §14.4 (phần phone). Chạy khi API + web local hoặc sau deploy staging.

## Chuẩn bị

1. Máy chủ: `python scripts/demo_api.py` và `cd apps/web && npm run dev`
2. Điện thoại cùng Wi‑Fi với máy dev; mở `http://<IP-máy>:3000/login`
3. Tài khoản NV: `minh` / `nhipquan` (hoặc `lan` nếu cần quyền quản lý)

## Luồng (đánh dấu khi xong)

| # | Bước | Pass? |
|---|------|-------|
| 1 | Đăng nhập một tay, redirect `/hom-nay` | ☐ |
| 2 | Vào **Phiếu** → bắt đầu phiếu mở quán | ☐ |
| 3 | Hoàn thành ≥3 bước có minh chứng (chụp ảnh hoặc tick) | ☐ |
| 4 | Để việc **treo** → thấy trên `/treo` (manager: `lan`) | ☐ |
| 5 | **Lịch của tôi** → nhả/nhận ca (nếu có ca trong tuần) | ☐ |
| 6 | Kiểm tra ghi nhận sửa: API `GET /api/v1/ghi-nhan-sua` có bản ghi mới | ☐ |

## Ghi chú trung thực

- Emulator-only **không** thay walkthrough phone thật cho hội đồng.
- Nếu chưa có quán đối tác: ghi “software-complete, walkthrough NV nội bộ” trên slide ADR-012.

## Bằng chứng đính kèm (tùy chọn)

- 1 screenshot màn phiếu trên phone
- 1 screenshot việc treo trên máy quản lý
