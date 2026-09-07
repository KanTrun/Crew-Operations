# Plan — UX demo-ready 4 trang lõi (Phiếu · Lịch tuần · Việc treo · Tiêu thụ)

**Ngày:** 2026-09-07 · **Nhánh:** `feat/ux-demo-ready` (từ main 060fb80) · **Mục tiêu thi:** demo 10 phút §15.2 chạy mượt, người chủ quán hiểu ngay màn hình

## Outcome

4 trang sau khi sửa thì chính chủ quán (không đọc code) mở vào biết làm gì tiếp; hết mock trong Lịch tuần; demo theo kịch bản §15.2 không vấp. Mọi thứ làm trên nhánh này, test xanh, verify bằng browser thật, rồi mới merge main.

## Non-goals

- Không thêm module/agent mới. Không sửa kiến trúc solver. Không đụng kênh tin live.
- Không dọn 2 kv lifecycle song song (sprint45 `lifecycle` vs main `lich_tuan_lifecycle`) — ghi flag, làm riêng sau.

## Nguồn bằng chứng

- Audit Phieu (scout): 12 vấn đề file:dòng; gốc "tạo phiếu liên tục" = state không persist + fallback hard-code + nút primary "Tạo phiếu mới" + `ca_id='w1_c01'` (sprint3.py:152-153).
- Audit Roster (scout): 15 vấn đề; gốc "mock trong lịch" = nhánh `_build_lich_tuan_from_seed` active khi chưa chạy solver (main.py:343-370) + pin API validate theo seed (main.py:478-482) từ chối users thật → 404 vô hình sau modal.
- Hồ sơ §15.2: phút 0:40 phiếu điện thoại một tay; 4:00 solver ra lịch; 5:00 ghim ô + giải lại; §15.3 điểm 25/20/20/15/10/10.

---

## Phase 1 — Sửa backend 2 bug chặn demo (làm trước để UI dựa được)

### 1.1 Pin nhận users thật (`main.py` ~478)
- `_pin_map`/`_set_pin` hợp lệ; lỗi nằm ở **route validate**: pin so `nv_id` với `seed["nhan_vien"]`. Sửa: xác thực theo `list_nhan_vien_ops()` (đã import sẵn) thay vì seed thô. Test: pin nv_26 (users) → 200; pin id không tồn tại → 422.

### 1.2 Hết mock trong Lịch tuần (`main.py` `_build_lich_tuan_from_seed` 343-370)
- Khi chưa chạy solver: nhánh fallback sinh phan_cong **giả từ pattern seed**. Sửa: nhánh này trả `phan_cong: {}` + `nguon_lich: "chua_xep"` (mới) — lưới hiển thị trống sạch + thông điệp "Chưa xếp — bấm chạy máy xếp" (kèm nút lifecycle dang_giai). Solver chạy rồi → dữ liệu thật như cũ.
- `get_lich_tuan` thêm `nguon_lich: "solver" | "chua_xep"` + truyền `solver` (đã có) cho UI dòng nguồn gốc.
- Test: xóa file lich_tuan.json → GET trả phan_cong rỗng + nguon_lich=chua_xep; có file → solver.

## Phase 2 — Trang Phiếu dễ hiểu (giữ kit sẵn)

2.1 **Persist + khôi phục:** lưu `phieu.id` vào sessionStorage khi start; mount → `GET /phieu/{id}` (đã có, sprint3.py:301) khôi phục phiếu dở. Màn xong: primary = "Về Hôm nay" (BtnLink), "Tạo phiếu mới" hạ ghost.
2.2 **Xóa 2 fallback hard-code** (page.tsx:78 + 233-236) → Empty + "Thử lại".
2.3 **Card mẫu giàu info:** dùng `so_buoc`/`mo_khi`/`han_hoan_thanh_phut` từ payload có sẵn — mỗi mẫu 1 OpsCard nhỏ "Mở quán · 20 bước · đầu ca · hạn 30 phút".
2.4 **Điểm danh tách bước rõ:** trước chọn mẫu hiện khối "Xác nhận có mặt hôm nay" (nút gọi /diem-danh, đã xong thì badge ✓). Bỏ điểm danh ẩn trong startPhieu.
2.5 **"Tiếp theo" + feedback treo:** OpsCard Tiến độ thêm "còn N bước" + 3 bước kế dạng mờ; sau treo → Alert ok "Quản lý sẽ thấy" + card "Việc đã treo lần này" từ `phieu.treo` payload; nút "Treo" → "Để lại việc khó".
2.6 **Ảnh:** nén client (canvas ≤1024px JPEG 0.7) + preview trước gửi + nút "Chụp lại"; map lỗi `anh_qua_lon` ra lời.
2.7 **Nhập số có ngữ cảnh:** Field label theo bước + Hint ngưỡng 2–8°C (từ payload); disable "Xong bước này" khi text rỗng; Alert warn khi payload trả anti_fake.

## Phase 3 — Panel chi tiết Lịch tuần mới (theo phác scout)

3.1 Modal thân mới: **mỗi ca 1 hàng** — giờ → trạng thái lời ("Đủ 2/2", "Thiếu 1 (cần 2)", "Không có ca này") → pill NV **kèm nút ×** (gọi `handlePin(..., false)`) → nút "＋ Thêm người". Highlight hàng ca gốc khi vào từ ô.
3.2 Alert lỗi/thành công **trong modal**; sau pin chỉ cập nhật state, không skeleton toàn trang.
3.3 Trạng thái lịch **1 chỗ** + dùng `lifeLabelPublic`; nút hành động duy nhất "Bước tiếp theo: …" theo lifecycle.
3.4 Dòng nguồn gốc: "Máy xếp xong · OPTIMAL" hoặc "Chưa xếp — bấm chạy máy xếp" (dữ liệu `solver` + `nguon_lich` Phase 1.2).
3.5 Badge thiếu người theo `so_nguoi_toi_thieu` ("2/3 · thiếu 1") thay vì hardcode <2.
3.6 Tuần hiển thị "07/09 – 13/09" chính, W37 phụ; **ẩn chu kỳ 2-4 tuần** (giả — cùng 21 ca).
3.7 Dọn mock: bỏ fallback `nv_03` (empty-state "chưa liên kết"), bỏ "×5 giờ".

## Phase 4 — Việc treo + Tiêu thụ rõ nghĩa

4.1 Treo: đổi 2 tab thành tab chính "Việc cần xử lý" (chỉ chưa xong, mở đầu) / "Đã xong" / "Lần sửa lịch" (đổi tên từ "Ghi nhận sửa"); mỗi thẻ: nội dung + ai để + bao giờ + chip trạng thái + hạn (nếu có); NV thấy nút "Tôi đã làm xong việc này" (PATCH của mình) còn QL nút đầy đủ (hiện đã đúng — chỉ đổi nhãn + copy giải thích 1 câu mỗi khu).
4.2 Tiêu thụ: đổi title "Sổ kiểm kê nguyên liệu" + giải thích "Đếm đầu ca & cuối ca — hệ thống suy ra tiêu thụ"; form thêm Hint "ví dụ: Sữa tươi · 8 · hộp"; danh sách hiển thị "kiểm kê lúc HH:MM · Sữa tươi 8 hộp"; giữ cảnh báo ngưỡng.

## Phase 5 — Verify kiểu demo thật + merge

- Khởi API+web, kịch bản §15.2 thu hẹp: minh điểm danh→phiếu 3 bước→treo (thấy Alert) ; lan /roster → trống sạch → "Chạy máy xếp" (dang_giai) → lịch 21 ca → ghim/nhỏ người (thêm+gỡ) → trạng thái "Gửi duyệt".
- `tsc --noEmit` + pytest vùng đụng (test_copilot_api, test_http_demo, test_nhan_vien) + ruff.
- Screenshot từng trang trước/sau cho bạn xem trong báo cáo.
- Test xanh hết → merge main → push → CI/deploy xanh → verify nhipquan.duckdns.org 1 vòng.
- Ghi flag 2 việc chừa lại (lifecycle đôi, browser e2e optional).

## Risk ledger

- **Preserves:** API contracts (chỉ thêm field), kit components, quyền role, solver logic.
- **Breaks:** nhánh seed-fallback trả phan_cong rỗng — ảnh hưởng e2e cũ nào kỳ lịch có sẵn? Chạy suite để bắt.
- **Risks:** pin users thật cần ca hợp lệ `_known_ca` (sprint3) — pin theo ca_id từ lịch (w1_*) nên ổn; theo dõi test đỏ liên quan lịch.
