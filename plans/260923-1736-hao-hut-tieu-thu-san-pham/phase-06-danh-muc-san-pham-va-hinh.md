---
phase: 6
title: "Danh mục sản phẩm & hình"
status: pending
priority: P1
effort: "1 ngày"
dependencies: [5]
---

# Phase 6: Danh mục sản phẩm & hình

## Overview

Bơm đầy danh mục sản phẩm (cà phê, trà, nước đóng chai, nguyên liệu, bánh) và
**sinh ảnh tại máy** cho mọi món — chạy được khi rút mạng, chi phí 0 đồng.

## Requirements

- Functional: danh mục ≥ 45 mặt hàng, phủ đủ nhóm: cà phê, trà, nước đóng chai,
  nguyên liệu pha chế, bánh, ly/ống hút.
- Functional: mỗi món có `bom` đúng đơn vị theo `BOM_INGREDIENTS`.
- Functional: sinh ảnh cho mọi món trong menu; ảnh tất định (cùng input ⇒ cùng byte).
- Non-functional: **không gọi mạng, không API ảnh** — ràng buộc demo offline §14.9.
- Non-functional: idempotent — chạy lại không nhân bản, không đè ảnh người dùng tự tải.
- Non-functional: ảnh phải theo hệ màu quán (`--nq-*`: copper `#c4a574`, nền tối).

## Architecture

Hai công cụ tách biệt, đều là script vận hành (không phải mã chạy lúc phục vụ):

```text
scripts/seed_danh_muc.py
  - đọc data/seed/danh-muc.json (nguồn duy nhất)
  - upsert menu_mon theo id, gắn nguon="danh_muc_chuan"
  - giữ nguyên món do quán tự thêm

scripts/sinh_anh_mon.py
  - đọc từng món từ menu_mon
  - sinh ảnh PNG/WEBP tất định bằng Pillow (không mạng)
  - ghi data/menu_images/<mon_id>.png
  - BỎ QUA nếu ảnh đã do quán tải lên (đánh dấu trong hinh_url)
```

Vì sao tại máy: `docs/THIRD_PARTY.md` ghi free tier cloud "dễ thu hồi", và §14.9
buộc demo chạy trọn khi rút mạng. API ảnh đám mây vừa tốn quota vừa làm buổi demo
phụ thuộc mạng. Pillow đã có trong venv (`12.3.0`) và trong CI.

Ảnh sinh ra là **ảnh thẻ sản phẩm**: nền gradient tối theo hệ màu quán, khối hình
học đại diện nhóm (ly/trà/chai/bánh), chữ tên món + đơn giá bằng font hệ thống.
Tất định: mọi tham số suy từ `mon_id` bằng hash, không dùng `random`.

## Related Code Files

- Create: `data/seed/danh-muc.json` (nguồn danh mục, được git theo dõi như `sample.json`)
- Create: `scripts/seed_danh_muc.py`
- Create: `scripts/sinh_anh_mon.py`
- Modify: `data/seed/.gitignore` (cho phép `danh-muc.json`)
- Modify: `apps/api/src/ca_api/persist.py` (`_MENU_MAC_DINH` — bổ sung nước đóng chai)
- Modify: `apps/api/src/ca_api/interfaces/http/pos.py` (fallback ảnh sinh tại máy khi chưa upload)
- Modify: `Makefile` (`seed-danh-muc`, `sinh-anh`)
- Modify: `docs/THIRD_PARTY.md` (ghi Pillow nếu chưa có dòng tương ứng)
- Create: `apps/api/tests/unit/test_sinh_anh_mon.py`

## Implementation Steps

1. Soạn `data/seed/danh-muc.json`: id, tên, giá, nhóm, `bom`, `hinh_mo_ta` (mô tả
   hình để sinh ảnh). Đủ ≥ 45 món.
2. Viết `seed_danh_muc.py` idempotent theo `id`; in bảng đếm theo nhóm.
3. Viết `sinh_anh_mon.py` bằng Pillow: tất định, không mạng, có chế độ `--dry-run`.
4. Cho `GET /api/v1/menu/{mon_id}/anh` fallback sang ảnh sinh tại máy khi chưa upload.
5. Thêm target Makefile; cập nhật `THIRD_PARTY.md` nếu Pillow chưa được khai.
6. Test: sinh ảnh hai lần cho ra byte giống nhau; ảnh là PNG/WEBP hợp lệ; số ảnh ≥ số món.

## Success Criteria

- [ ] `python scripts/seed_danh_muc.py` rồi `GET /api/v1/menu/quan-tri` trả ≥ 45 món.
- [ ] Chạy script hai lần: số món **không** tăng; món quán tự thêm còn nguyên.
- [ ] `python scripts/sinh_anh_mon.py` sinh ảnh cho **mọi** món; chạy lại ra cùng byte.
- [ ] `GET /api/v1/menu/{id}/anh` trả 200 ảnh hợp lệ cho mọi món, **khi tắt mạng**.
- [ ] Có nước đóng chai trong danh mục mặc định của `persist.py`.
- [ ] `ruff check scripts` sạch.

## Risk Assessment

Rủi ro 1: ghi thẳng vào `data/menu_images/` (đang gitignore) khiến ảnh không tồn
tại ở máy khác / CI. **Tín hiệu:** CI chạy e2e mà ảnh 404. **Phản ứng:** ảnh sinh
theo yêu cầu tại chỗ phục vụ (fallback ở bước 4), nên CI tự sinh lại; không cần
commit ảnh nhị phân.

Rủi ro 2: Pillow vẽ font tiếng Việt cần font có dấu. **Tín hiệu:** chữ ra ô vuông.
**Phản ứng:** dùng font hệ thống đã dùng cho web nếu tìm thấy; không thấy thì vẽ
khối hình học + chữ không dấu dạng mã, và ghi rõ giới hạn trong docs — không bịa font.

