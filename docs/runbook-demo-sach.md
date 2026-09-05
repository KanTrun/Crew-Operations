# Runbook — Demo từ trạng thái sạch (< 10 phút)

> **Khi nào dùng runbook này:** cần demo NHỊP QUÁN từ con số 0 — không rác test,
> không mục inbox "Ràng buộc #N — chờ duyệt", không 480 vết eval trong `/vet`.
> Muốn demo "có sẵn dữ liệu mẫu để thấy nhanh" thì chỉ cần bước 1–2.

## 0. Điều kiện

- Python ≥ 3.12 · Node ≥ 20 (web) · file `.env` ở root (copy từ `.env.example`)
- Không cần key LLM: mọi agent chạy chế độ `replay` (mặc định) — nhanh, tất định, 0 đồng.
- Muốn AI live (Gemini đọc ảnh TKB thật, LLM trả lời tự nhiên): điền key vào `.env`
  và đặt `CA_AGENT_MODE=live`. Không có key thì dùng nút **Thử ảnh mẫu** ở `/tkb`.

## 1. Wipe + seed lại (local, không Docker)

```bash
# Backup DB hiện tại (tự tạo bởi script) → data/backups/
python scripts/seed_professional_fixture.py --reset
# Khởi API
python scripts/demo_api.py        # terminal 1 — giữ nguyên
# Web
cd apps/web && npm install && npm run dev   # terminal 2
```

Mở http://localhost:3000 · API http://localhost:8000/docs

Kiểm tra sạch (chạy khi API đã dừng hoặc từ python khác):

```bash
python -c "import sqlite3; cx=sqlite3.connect('data/quan.db'); \
print('e2e users:', cx.execute(\"SELECT COUNT(*) FROM users WHERE username LIKE 'e2e_%'\").fetchone()[0]); \
print('eval rows:', cx.execute(\"SELECT COUNT(*) FROM fb_review_queue WHERE external_thread_id LIKE 'fb_eval%'\").fetchone()[0])"
# Kỳ vọng: e2e users: 0 · eval rows: 0
```

Docker: `make docker-reset && make docker-up && make docker-seed-ops` (seed-ops
nạp 6 bề mặt vận hành vào **container**, vì volume tách khỏi máy host).

## 2. Hai chế độ demo

| Chế độ | Cách bật | Khi nào dùng |
|---|---|---|
| **Có dữ liệu mẫu** (mặc định sau `--reset`) | Không làm gì thêm | Demo nhanh cho người xem mới — mọi trang có sẵn việc treo, inbox, lịch sử để thấy hình dạng dữ liệu |
| **Sạch trọn vẹn** | Set `NHIPQUAN_INBOX_SEED_FIXTURE=0` trong `.env` **trước khi khởi API**, và KHÔNG chạy `make seed-ops` / `--reset` | Chứng minh mọi dữ liệu sinh từ workflow thật: trang empty-state trung thực, tự tay tạo từng bước |

Sau khi đã seed một lần, muốn chuyển sang sạch trọn vẹn: chạy lại
`--reset` rồi đặt env trên rồi khởi API (inbox sẽ không tự sinh 10 mục placeholder).

## 3. Tài khoản

| Tài khoản | Vai trò | Mật khẩu |
|---|---|---|
| `lan` | Quản lý ca | `nhipquan` |
| `hung` | Chủ quán | `nhipquan` |
| `minh` | Nhân viên | `nhipquan` |
| `an` `bao` `chi` `dung` `thao` `quan` `yen` | Nhân viên (fixture) | `nhipquan` |

Đăng ký thêm nhân viên mới tại `/dang-ky` (vai nhân viên).

## 4. Kịch bản 10 phút — từng bước và "sẽ thấy gì"

### Phần A — Nhân viên `minh` (≈ 3 phút)

1. Đăng nhập `minh` / `nhipquan` → vào **Hôm nay**: thấy KPI việc treo/tồn kho,
   dòng "Lịch nháp · 18 việc treo" nếu đang ở chế độ có dữ liệu mẫu (nhãn
   "Dữ liệu mẫu" chỉ rõ nguồn fixture).
2. **Phiếu** → chọn **MỞ QUÁN**: hệ thống tự điểm danh → checklist từng bước:
   gõ nhiệt độ tủ lạnh (ngoài 2–8°C sẽ sinh việc treo), chụp ảnh minh chứng
   quầy pha, xác nhận. Làm 2–3 bước rồi bấm **Treo** → thấy trang xác nhận
   việc treo đã ghi.
3. **Ca của tôi** → thấy 2 ca "Pha chế 17:00–22:00 · Ca tối" với nút NHẢ/NHẬN.

### Phần B — Quản lý `lan` (≈ 4 phút)

1. Đăng nhập `lan` → **Hôm nay**: KPI "6 MỤC CHỜ DUYỆT" (chế độ mẫu) hoặc
   danh sách trống (chế độ sạch).
2. **Hộp thư** → duyệt 1 mục (DUYỆT RÀNG BUỘC) → mục chuyển "Đã duyệt".
   Duyệt xin nghỉ/TKB → ràng buộc được nạp vào lần xếp lịch kế tiếp.
3. **Điểm danh QR** → chọn `minh` + ca → **PHÁT MÃ** → copy mã → dán vào ô
   phía dưới → thấy xác nhận điểm danh một lần (dùng lại mã → "đã dùng").
4. **Trợ lý vận hành** (`/copilot` hoặc khung nổi Ctrl+K) → gõ
   *"Xếp lịch tuần sau, ưu tiên Lan ca sáng"* → thấy solver chạy (vài giây)
   → thẻ **Đề xuất** hiện: "49 lượt phân công · OPTIMAL · không trùng giờ học"
   kèm đếm ngược 30 phút → bấm **Duyệt & Áp dụng** → trạng thái "ĐÃ DUYỆT"
   → sang **Lịch tuần** tuần sau: thấy phân công mới đã áp dụng.

### Phần C — Chủ quán `hung` (≈ 2 phút)

1. Đăng nhập `hung` → **Cẩm nang**: thấy pipeline 8 bước và các luật
   "MẪU MINH HỌA" (fixture). Chạy "8 bước xét luật" cần ≥3 lần sửa lịch thật —
   ở chế độ sạch sẽ thấy thông báo này thay vì luật tự sinh.
2. **Người dùng** → đội hình 10 tài khoản, donut vai trò, nút nâng/hạ vai.
3. **Vết hệ thống** → nhật ký chỉ ghi thêm: mọi duyệt/điểm danh vừa làm ở trên
   đều có vết ở đây (không còn 480 dòng "Thao tác trong quán" từ eval).

### Ghi chú trung thực khi demo

- Luật có chip **MẪU MINH HỌA** là fixture sinh ra; luật thật chỉ xuất hiện sau
  ≥3 lần quản lý sửa lịch cùng kiểu (nhả/nhận ca, ghim, đổi) — hệ thống ghi nhận
  tự động, không ai phải nhập tay.
- Chế độ mặc định của AI là **replay**: trả lời từ bộ mẫu/đường tất định — nhanh
  và lặp lại được. Câu trả lời AI đều có thể truy vết nguồn (SOP kèm trích dẫn).
- AI không tự ghi gì: mọi hành động (xếp lịch, duyệt đổi ca, luật, mail) dừng ở
  "Đề xuất chờ duyệt" cho đến khi quản lý/chủ quán bấm nút.

## 5. Sau demo

- Dừng: Ctrl+C 2 terminal (hoặc `make docker-down`).
- Muốn về lại trạng thái sạch ban đầu: chạy lại bước 1 (`--reset`).
- DB backup trước wipe nằm ở `data/backups/quan-pre-phase0.db` (lần chạy đầu).
