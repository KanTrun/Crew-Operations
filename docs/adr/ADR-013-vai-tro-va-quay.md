# ADR-013 — Ba vai nội bộ và quầy bán nước

## Bối cảnh

PWA NHỊP QUÁN gộp `quan_ly` và `chu_quan` thành một cửa quản lý. Hồ sơ Lô 1 cấm luồng đơn khách / POS thứ hai thay Grab hoặc ShopeeFood. Cần web nội bộ cho nhân viên, quản lý, và chủ quán (admin quán) plus ghi đơn tại quầy.

## Quyết định

1. **Ba vai, không invent superuser hệ thống.** `nhan_vien` · `quan_ly` · `chu_quan`. Nhãn UI “Admin” = chủ quán. Tự đăng ký chỉ ra `nhan_vien`. Nâng vai `nhan_vien` → `quan_ly` chỉ do `chu_quan`.
2. **`_require_manager`** giữ cho lịch, inbox, pin, QR phát mã. **`_require_chu_quan`** cho nâng vai, gỡ luật hiệu lực, CRUD menu, vết audit đầy đủ, đóng tuần (`da_dong`).
3. **Quầy là ghi đơn nội bộ** do nhân viên đã điểm danh. Thanh toán chỉ `tien_mat` | `da_ck` | `chua_thu`. Khi đơn `xong`, ghi tiêu thụ **ước lượng từ quầy** (BOM), không phải số Grab. Agent không ghi DB.
4. **Cấm** storefront khách, cổng thanh toán, định danh khách, agent nhận đơn.

## Hệ quả

Nav và `RoleGate` lọc theo vai. Hợp đồng `MonNuoc` / `DonQuay` / `DongDon` nằm cạnh năm hợp đồng Sprint 1, không nhét vào `NhanVien`/`Ca`.

## Phương án loại

App khách đặt mang đi — loại vì hai luồng đơn. Vai `admin` kỹ thuật tách khỏi `chu_quan` — loại vì không có người vận hành thứ tư tại quán.
