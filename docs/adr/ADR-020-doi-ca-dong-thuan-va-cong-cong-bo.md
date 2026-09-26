# ADR-020 — Đổi ca phải có đồng thuận và cổng công bố

- Status: accepted
- Date: 2026-09-26
- Liên quan: ADR-009 (vòng đời lịch), ADR-004 (CP-SAT), ADR-008 (người quyết)

## Bối cảnh

Bốn bề mặt cùng thay đổi phân công ca: xếp lịch tự động (solver), xác nhận
thời khoá biểu bận, chợ đổi ca, và nút nhả/nhận ca ở trang "Ca của tôi". Trước
ADR này, ba trong bốn bề mặt ghi thẳng vào `phan_cong` mà **không hỏi ai**:

- `/api/v1/ca/nhan`: ghi thẳng cho bất kỳ ai đăng nhập — kể cả ca của người
  khác, kể cả tuần còn nháp.
- `/api/v1/ca/nha`: ghi thẳng, không kiểm tuần đã công bố hay chưa.
- `POST /cho-doi-ca/{id}/dong-y`: hai bên bấm đồng ý là phân công đổi ngay,
  không có lượt quản lý nào.

Hệ quả người dùng gặp thật: họ không biết phiếu đổi ca thuộc **tuần nào**, không
biết người nhận **có bị kẹt ca khác** hay không, và lịch tự đổi mà không có gì
giải thích ai đã đổi với ai. Nguyên tắc "người quyết" của ADR-008 bị vi phạm ở
đúng chỗ cần nó nhất: lịch mà nhân viên khác đang chạy theo.

## Quyết định

**1. Cổng công bố (`_guard_swap_cong_bo`, `_tuan_trang_thai`).** Mọi thao tác
đổi phân công do người dùng khởi xướng phải kiểm trạng thái tuần:

| Trạng thái tuần | Nhả ca | Nhận ca | Đổi ca |
|---|---|---|---|
| `nhap` / `may_sinh` / `dang_giai` | chặn `409 lich_chua_cong_bo` | chặn | chặn |
| `cho_duyet` | chặn | chặn | chặn |
| `da_cong_bo` / `da_dong` | cho phép | cần quản lý duyệt | cần quản lý duyệt |

Lý do: tuần còn nháp là bản đang được xếp — sửa nó sau lưng người xếp là hỏng
việc của họ. Tuần đã công bố là lịch đã chốt và có người khác đang chạy theo —
sửa được, nhưng phải có người chịu trách nhiệm.

**2. "Đồng ý" tách khỏi "duyệt".** `POST /cho-doi-ca/{id}/dong-y` chỉ ghi nhận
đồng ý của một bên. Việc áp vào phân công do `POST /cho-doi-ca/{id}/duyet` làm,
và chỉ `quan_ly`/`chu_quan` gọi được. Gộp hai việc vào một endpoint là lẫn quyền
đồng ý với quyền quyết định, và mất khả năng trả lời "ai đã duyệt phiếu này"
(`da_duyet_boi`).

**3. Nhận ca của nhân viên bắt buộc qua chợ đổi ca.** `/api/v1/ca/nhan` trả
`409 nhan_ca_phai_qua_cho_doi_ca` kèm chỉ dẫn. Đường gán ca trực tiếp cho quản
lý nằm ở endpoint riêng `/api/v1/ca/nhan-truc-tiep` — có `nv_id` và kiểm quyền,
để hành vi "quản lý lấp ca thiếu người" không lẫn với "nhân viên tự nhận ca".

**4. Mọi thay đổi phân công phải để lại vết đọc được.** Diff trước/sau được ghi
tại **một điểm chốt duy nhất** (`solver_adapter.run_solver` → `_ghi_nhat_ky_thay_doi`)
vì mọi đường xếp lịch đều đi qua đó, và được phơi qua
`GET /api/v1/lich-tuan/thay-doi`. Mô-đun phân loại diff
(`services/schedule_diff.py`) là **thuần** và dùng chung, nên ba bề mặt không thể
kể ba câu chuyện khác nhau về cùng một sự kiện.

**5. Đo rủi ro, không khuyên suông.** `_rui_ro_doi_ca` trả dữ liệu thô
(`nguoi_nhuong_dang_trong_ca`, `nguoi_nhan_dang_trung`, `ly_do_chan`) để UI nói
được *vì sao* một phiếu không thực hiện được, thay vì chỉ từ chối.

## Hệ quả

- Đổi hành vi có chủ đích, đã cập nhật: `test_sprint3.py::test_ghi_nhan_after_nha`,
  `test_schedule_consistency.py::test_ca_nha_and_nhan_sync_to_phan_cong_by_week`,
  `test_schedule_consistency.py::test_swap_only_touches_its_own_week`,
  `test_sprint45.py::test_swap_consent_by_any_recipient`.
- `GET /cho-doi-ca` **lọc theo server**: trước đây trả `kv_get("swap", [])` cho
  mọi vai, tức một nhân viên đọc được toàn bộ phiếu của quán. Lọc ở client không
  phải là bảo vệ.

## Bổ sung: hợp nhất ma trận hai đường vòng đời

Hai cửa vào cùng state machine (`PATCH /api/v1/lich-tuan/lifecycle` trong
`main.py` và `POST /api/v1/lich/lifecycle` trong `sprint45.py`) trước đây **mỗi
bên khai một bản ma trận riêng**, và đã lệch thật ở đúng một ô:

| | `da_cong_bo →` |
|---|---|
| `main.py` (PATCH) | `da_dong` |
| `sprint45.py` (POST) | `da_dong`, **`nhap`** |

Hệ quả: "mở lại lịch đã công bố" chạy được qua POST nhưng trả
`409 illegal:da_cong_bo->nhap` qua PATCH. UI hiện gọi đúng đường (POST khi cần lý
do) nên người dùng chưa gặp — nhưng client API, test hay agent chọn nhầm đường sẽ
nhận lỗi cho một thao tác mà đường kia cho phép.

**Quyết định:** ma trận về **một nguồn duy nhất** — khai trong `sprint45.py` dưới
tên `_SHARED_ALLOWED`, `main.py` import và alias thành `_LIFECYCLE_ALLOWED`. Ô
`da_cong_bo → nhap` **được phép** (mở lại lịch công bố là nghiệp vụ thật).

**Kèm theo:** `PATCH` nay cũng bắt buộc có lý do khi mở lại lịch đã chốt, như
`POST` đã bắt từ trước. Trước kia lỗ hổng này bị ma trận hẹp che — nay ma trận mở
`da_cong_bo → nhap` thì cổng lý do phải chặn, không thì mở lại một quyết định đã
ban hành sẽ đi qua im lặng.

**Chốt chống tái phát:** `apps/api/tests/unit/test_lifecycle_matrix.py` kiểm hai
tên ma trận là **cùng một object** (`is`), không phải hai bản bằng giá trị — hai
dict bằng nhau hôm nay vẫn có thể bị sửa lệch ở lần sau.

- `/api/v1/ca/nhan-truc-tiep` không có UI riêng trong phạm vi này; nó là đường
  API cho quản lý, đã khai trong `EXCLUDED_ROUTES` (R3).
