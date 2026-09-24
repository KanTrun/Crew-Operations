# ADR-019 — Ảnh sản phẩm sinh tại máy, không gọi API ảnh đám mây

## Status
Accepted (plan 260923-1736, Phase 06)

## Context

Menu cần một ảnh cho mỗi món; lưới menu rơi về chữ cái đầu khi món chưa có ảnh,
và `data/menu_images/` bắt đầu rỗng. Có hai đường để có ảnh:

1. Gọi API sinh ảnh đám mây (Gemini và tương tự) khi chủ quán lưu món.
2. Sinh ảnh ngay tại máy chủ của quán.

Ba ràng buộc cứng của dự án loại đường (1):

- **Demo phải chạy trọn khi rút mạng** (§14.9 của hồ sơ tổng thể). Phụ thuộc API
  ảnh nghĩa là mất hình giữa buổi bảo vệ khi mạng chập — đúng lúc không sửa được.
- `docs/THIRD_PARTY.md` ghi free tier cloud là **"dễ thu hồi"**, và ngân sách của
  quán là **0 đồng**. Ảnh là thứ trang trí; nó không được là thứ có thể hết hạn.
- `data/menu_images/` bị `.gitignore` bỏ qua, nên ảnh không đi theo repo. Máy nào
  chạy cũng phải tự dựng được ảnh, không thể phụ thuộc một lần sinh sẵn.

Đã kiểm: `Pillow 12.3.0` có sẵn trong venv và trong CI (kéo theo bởi `reportlab`),
nên **không thêm phụ thuộc mới**.

## Decision

- **Sinh ảnh tại máy bằng Pillow**, trong `ca_api/services/menu_image.py`. Không
  gọi mạng ở bất kỳ đâu trong đường sinh ảnh.
- **Tất định**: mọi tham số hình (màu nền, độ nghiêng ống hút, hình đại diện) suy
  từ `id` bằng SHA-256. Không dùng `random`. Cùng `id` ⇒ **cùng byte**, đã kiểm
  trên cả 49 ảnh của danh mục chuẩn.
- **Ba bậc phục vụ** ở `GET /api/v1/menu/{id}/anh`: ảnh quán tự tải lên → ảnh đã
  sinh trong `data/menu_images/` → **sinh tại chỗ**. Bậc ba là chỗ chốt ràng buộc
  offline: máy chưa chạy script vẫn phải trả ảnh thật.
- **Hình học, không emoji**: emoji render khác nhau theo hệ điều hành (mất tính
  tất định) và vi phạm quy ước icon của dự án (`docs/design-guidelines.md`).
- Ảnh là **thẻ sản phẩm**: nền gradient tối theo hệ màu quán (`--nq-*`), khối hình
  đại diện nhóm (ly / chai / đĩa bánh / gói), tên món, đơn giá.
- Font dùng font hệ thống, **không nhúng font vào repo**. Thiếu font có dấu thì
  chữ ra ô vuông nhưng ảnh vẫn dùng được — không đáng thêm vài trăm KB nhị phân
  cho một tấm ảnh thẻ.

## Alternatives considered

| Cách | Vì sao không chọn |
|---|---|
| API sinh ảnh đám mây | Buộc demo phụ thuộc mạng; tốn quota có thể bị thu hồi; ảnh không tất định nên test không so byte được |
| Commit sẵn ảnh vào repo | `data/menu_images/` bị gitignore; và ảnh nhị phân trong repo là thứ trôi khỏi mã |
| Bỏ ảnh, dùng chữ cái đầu | Giữ nguyên vấn đề: mọi món trông như "chưa có ảnh" |

## Consequences

- Demo và CI dựng được ảnh mà không cần mạng, không cần khoá API.
- Ảnh ở bậc 2 và bậc 3 **giống hệt nhau** vì cùng một hàm vẽ — không có hai bản
  để lệch nhau.
- Muốn ảnh thật thì chủ quán tự tải lên; ảnh tải lên luôn thắng ảnh tự sinh.
- Nhận giá: ảnh là hình thẻ chứ không phải ảnh chụp món. Chấp nhận được — ảnh chụp
  thật là việc của chủ quán, và hệ đã có đường tải lên cho việc đó.

## Links

- `apps/api/src/ca_api/services/menu_image.py`
- `apps/api/src/ca_api/interfaces/http/pos.py` (`menu_anh_get`)
- `scripts/sinh_anh_mon.py`, `scripts/seed_danh_muc.py`
- `data/seed/danh-muc.json`
- `docs/THIRD_PARTY.md` (Pillow), `docs/design-guidelines.md` (hệ màu, cấm emoji)
