# Runbook demo — dưới 5 phút từ máy trắng

## Cách khuyến nghị: Docker toàn tuyến

```bash
make docker-up     # postgres · redis · api · worker · web
make docker-smoke  # kiểm toàn tuyến backend, in nguyên trạng thái trả về
```

Web tại http://localhost:3000, API tại http://localhost:8000/docs.
Dừng bằng `make docker-down`; xoá luôn dữ liệu bằng
`docker compose -f infra/docker/compose.yml down -v`.

Dữ liệu ghi được nằm trong volume `nhipquan_var` (`/app/var`): `quan.db`,
sổ lần sửa, cẩm nang. Seed và template YAML nướng sẵn trong image ở `/app/data`
và `/app/infra/templates`, nên xoá volume không mất dữ liệu gốc.

> **Windows:** BuildKit không build được khi đường dẫn kho có dấu tiếng Việt
> (`x-docker-expose-session-sharedkey` non-ASCII). Tạo lối tắt ASCII rồi build từ đó:
> `mklink /J C:\nhipquan "D:\CA-CÔNG-BẰNG"`.

## Cách thủ công (không Docker)

1. Cài: `python -m pip install -e ./packages/contracts -e ./packages/solver -e ./packages/agents -e ./packages/gates -e ./packages/opsengine -e ./packages/playbook -e ./apps/api uvicorn`
2. API: `python scripts/demo_api.py`
3. Web: `cd apps/web && npm install && npm run dev`
4. Mở http://localhost:3000/login

## Tài khoản thật trên instance NHỊP QUÁN

| Tài khoản | Vai trò | Mật khẩu |
|-----------|---------|----------|
| lan | Quản lý | nhipquan |
| hung | Chủ quán | nhipquan |
| minh | Nhân viên | nhipquan |

Không có tài khoản “demo”. Dữ liệu nằm trong `data/quan.db` sau khi đăng nhập.

## Kịch bản 3 phút

1. **minh** → Hôm nay → Phiếu → làm 2–3 bước → Treo nếu kẹt
2. **lan** → Hôm nay thấy số treo → Việc treo → Lịch tuần → chuyển Nháp → Đang giải (chạy solver)
3. **lan** → Hộp thư duyệt / từ chối · Cẩm nang xem luật (số luật quán thật = 0 cho đến khi gắn quán)

## Cổng hồ sơ chưa đóng bằng demo này

- §14.4 walkthrough điện thoại thật: `docs/walkthrough-s3-dien-thoai.md`
- §14.5 ≥5 phiếu NV quán: `docs/gan-du-lieu-that.md`
- §14.6 luật quán thật
- §14.7 tag + video + bản nộp bán kết chính thức — chưa đóng
