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

> **Windows:** BuildKit không build được khi đường dẫn kho có ký tự non-ASCII
> (`x-docker-expose-session-sharedkey`). Clone hoặc junction sang đường dẫn ASCII:
> `mklink /J C:\nhipquan C:\path\to\Crew-Operations`

## Cách thủ công (không Docker)

```bash
make setup                        # Cài Python editable + npm web
python scripts/seed_19_staff.py  # Seed 19 nhân viên demo
cd apps/web && npm run dev        # Web dev server
python scripts/demo_api.py        # Hoặc: uvicorn ca_api.interfaces.http.main:app
```

Mở http://localhost:3000/login

---

## Tài khoản demo — 19 nhân viên (mật khẩu đều: `nhipquan`)

### Nhóm 1 — Ban quản lý

| Tài khoản | Tên | Vai trò | Kịch bản demo |
|-----------|-----|---------|---------------|
| `lan` | Lan Nguyễn | Quản lý | Người phê duyệt chính — xem tất cả inbox, duyệt đổi ca |
| `hung` | Hùng Trần | Chủ quán | Nâng/hạ vai nhân viên, xem báo cáo tổng |

### Nhóm 2 — Nhân viên lõi

| Tài khoản | Tên | Kỹ năng | Ghi chú |
|-----------|-----|---------|---------|
| `minh` | Minh Phạm | pha_che, phuc_vu | Ca sáng cố định · Bind **Telegram** demo |
| `an` | An Lê | pha_che, thu_ngan, kho | Đa năng — hay được điều động |
| `bao` | Bảo Hoàng | pha_che, kho | Có đơn xin đổi ca đang chờ duyệt |

### Nhóm 3 — Sinh viên năng động (TKB xung đột — solver bài toán)

| Tài khoản | Tên | Kỹ năng | Ngày bận | Bind kênh |
|-----------|-----|---------|----------|-----------|
| `chi` | Chi Vũ | thu_ngan | T2 sáng+chiều | **Zalo** demo |
| `dung` | Dũng Đặng | kho, phuc_vu | T3, T5 chiều | — |
| `thao` | Thảo Dương | thu_ngan, phuc_vu | T2, T6 tối | **Telegram** demo |
| `quan` | Quân Lương | pha_che, phuc_vu | T4, CN sáng | **VẮNG hôm nay** — demo kịch bản D |
| `yen` | Yến Kiều | thu_ngan, kho | T3, T5 sáng | — |
| `linh` | Linh Ngô | phuc_vu, pha_che | T2, T4, T6 sáng | — |
| `nam` | Nam Lý | pha_che, thu_ngan | T3, T5, CN sáng | — |
| `my` | Mỹ Tạ | kho, phuc_vu | T2, T4 chiều | — |

### Nhóm 4 — Sinh viên ít giờ (cuối tuần — demo sổ công bằng)

| Tài khoản | Tên | Kỹ năng | Điểm bất công tích lũy |
|-----------|-----|---------|------------------------|
| `khoa` | Khoa Đỗ | kho | **-3** (bị dồn ca cuối tuần nhiều nhất) |
| `oanh` | Oanh Phan | phuc_vu | **-2** |
| `phuc` | Phúc Trịnh | pha_che, phuc_vu | **-4** (bị dồn nhiều nhất cả kho lẫn tối) |
| `son` | Sơn Hà | pha_che | **-2** (chỉ làm sáng CN) |

### Nhóm 5 — Nhân viên mới / thử việc (demo onboarding)

| Tài khoản | Tên | Kỹ năng | Kịch bản |
|-----------|-----|---------|----------|
| `rosa` | Rosa Võ | phuc_vu | Vừa đăng ký — **hung** nâng vai và thêm kỹ năng |
| `uyen` | Uyên Cao | phuc_vu, kho | **Bù ca Quân** hôm nay — demo xử lý vắng đột xuất |

---

## 6 Kịch bản demo (A–F) — mỗi kịch bản < 3 phút

### Kịch bản A — Xếp ca tự động (Solver CP-SAT)

```
lan đăng nhập → Lịch tuần → "Giải lại" → chọn tuần 2026-W37 → Đang giải
```

- Solver bỏ qua chi (T2 bận), dung (T3 chiều bận), thao (T6 tối bận)
- Kết quả: 21 ca, không ai bị xếp đè giờ học
- **Nói với hội đồng:** "Trước đây quản lý mất 2–4 giờ làm việc này trên Excel"

### Kịch bản B — Đổi ca / Chợ ca

```
bao đăng nhập → Lịch của tôi → Ca T5 tối → "Xin đổi" → chọn yen nhận
lan đăng nhập → Inbox → Phê duyệt yêu cầu đổi ca của bao ↔ yen
```

- Hệ thống validate kỹ năng và xung đột TKB tự động
- **Thể hiện:** agent đề xuất, người duyệt

### Kịch bản C — Sổ công bằng

```
lan đăng nhập → Báo cáo → Sổ công bằng
```

- Biểu đồ: khoa (-3), oanh (-2), phuc (-4), son (-2) vs minh (+1), an (0)
- **Nói với hội đồng:** "Đây là lý do số 1 nhân viên nghỉ việc — chúng em đo được"

### Kịch bản D — Vắng không báo trước

```
lan đăng nhập → Hôm nay → Xem điểm danh → quan "vắng mặt"
→ Việc treo: "CA sáng hôm nay Quân vắng — nhờ Uyên bù"
→ Chấp nhận → uyen nhận ca → Xác nhận
```

- **Thể hiện:** hệ thống gợi ý người phù hợp (uyen có kỹ năng và sẵn sàng)

### Kịch bản E — Kênh tin (Telegram/Zalo)

```
lan đăng nhập → Kênh tin → Broadcast "Lịch tuần W37 đã phát hành"
→ minh nhận qua Telegram, chi nhận qua Zalo (nếu demo live)
→ Console log cho phần còn lại
```

- **Thể hiện:** đa kênh, idempotent, không gửi trùng

### Kịch bản F — Onboarding nhân viên mới

```
rosa tự đăng ký → vào với vai nhan_vien (không có quyền phê duyệt)
hung đăng nhập → Quản lý NV → rosa → "Nâng vai quản lý"
→ rosa refresh → menu thay đổi
```

- **Thể hiện:** phân quyền rõ ràng, không ai tự leo thang quyền

---

## Cổng hồ sơ chưa đóng bằng demo này

- §14.4 walkthrough điện thoại thật: `docs/walkthrough-s3-dien-thoai.md`
- §14.5 ≥5 phiếu NV quán: `docs/gan-du-lieu-that.md`
- §14.6 luật quán thật
- §14.7 tag + video + 165 tests — chưa nộp bán kết

---

## Seed & reset dữ liệu demo

```bash
# Seed 19 nhân viên (giữ dữ liệu hiện có)
python scripts/seed_19_staff.py

# Wipe sạch rồi seed lại
python scripts/seed_19_staff.py --reset

# Seed professional fixture đầy đủ (POS, checklist, Facebook Page)
python scripts/seed_professional_fixture.py
```
