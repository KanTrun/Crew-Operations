# 2026-08-23 — Sprint 7: làm cứng, hoàn tất Lô 1, và sửa một lỗi chặn cổng demo

## Bối cảnh

Plan ghi phase 1–7 `Completed`, phase 8–9 `Pending`. Rà lại thì phase 7 chưa
xong thật: ba agent nó khai là "Create" chỉ còn `__pycache__`, không có source.

## Việc đã làm

### 1. Hoàn tất Lô 1 — ba agent còn thiếu

`ag_explain`, `ag_brief`, `ag_voc` chưa từng được viết. Đã viết cả ba kèm
`PHAM_VI.md` đủ 9 thuộc tính.

Phát hiện kéo theo: **AG-EXPLAIN không có gì để dịch** vì từ điển mã lý do của
bộ giải (§13.1, A · 1,5 ngày) cũng chưa tồn tại. Đã viết
`packages/solver/src/ca_solver/explain.py` — 8 mã lý do + 2 mã vô nghiệm.

Quyết định thiết kế: từ điển nằm ở **lõi solver**, không ở agent.

- Nếu agent giữ bản sao, hai bản sẽ lệch và VF-NUM mất ý nghĩa.
- Cụm từ trong `MA_LY_DO` **không chứa chữ số**; số chỉ vào câu qua bảng
  `DUOI_SO` và chỉ khi nằm trong `so_lieu_cho_phep`. Nhờ vậy tập số trong câu
  luôn là tập con của dữ liệu đầu vào, nên VF-NUM luôn kiểm được.

AG-VOC giữ đúng phạm vi đã thu hẹp ở §6.2: chỉ nhận nội dung quán tự chuyển
vào, và phản hồi về giá/khuyến mãi bị nhận ra **để loại**, không nối vào việc
treo. Sự cố vận hành xét trước marketing, vì một phản hồi vừa nói giá vừa báo
chờ lâu thì phần vận hành mới là phần có người phải xử lý.

### 2. Lỗi chặn cổng ra Sprint 8 — font tải từ CDN

`apps/web/src/app/layout.tsx` tải font bằng `<link>` tới
`fonts.googleapis.com`. Cổng ra §14.9 yêu cầu demo chạy trọn 10 phút khi **đã
rút mạng** — không có font thì chữ rơi về Georgia/system-ui giữa buổi bảo vệ.
Thêm nữa, nếu font thiếu subset `vietnamese` thì chữ có dấu render bằng
fallback và cả trang trông chắp vá dù token màu/khoảng cách đều đúng.

Đã chuyển sang `next/font` (`apps/web/src/ui/fonts.ts`), subset `vietnamese`
cho Fraunces và Source Sans 3. Kiểm sau build: **20 file `.woff2`** tự host,
**0** tham chiếu `fonts.googleapis`/`fonts.gstatic` trong HTML đã render.

Kèm theo: bộ icon SVG inline (`src/ui/icons.tsx`, không thêm dependency, không
emoji theo design guidelines), skip-link, `<main id="nq-content">`,
`aria-current="page"` cho nav, và `viewport.maximumScale=5` để không chặn zoom.

### 3. Làm cứng

| Hạng mục | Trước | Sau |
|---|---|---|
| Test Python | 100 (1 đỏ) | **252 PASS** |
| Test e2e Playwright | chưa chạy | **8/8 PASS** |
| Coverage | 92% | **94%** |
| `mypy --strict` | 130 lỗi | **0 / 96 file** |
| ruff | sạch | sạch |

Nguyên nhân đáng ghi của nhóm lỗi mypy trong `cpsat.py`: biến `b0`, `b1`,
`need` bị **shadow** giữa vòng lặp miền giá trị (kiểu `str`) và khối tính
khoảng nghỉ (kiểu `int`). Đã tách logic c04 ra `_vi_pham_khoang_nghi()` để mốc
thời gian có scope riêng — sửa cả lỗi kiểu lẫn cái bẫy dễ gây bug thật. Ngoài
ra `CpModel` chỉ khai snake_case trong stubs nên đã đổi `model.Add` →
`model.add`, v.v.

## Phát hiện phải sửa hồ sơ

Hồ sơ §1.2 và §5.2 ghi **"Lô 1: 10 agent · Lô 2: 3 agent"**. Đếm lại từ chính
bảng §5.2 thì đúng là **9 và 4** (tổng vẫn 13). Hai chỗ khác trong hồ sơ đã
dùng đúng số 9: bảng gọi mô hình §10.1 liệt kê 9 agent, §13.6 liệt kê 4 agent
Lô 2. Mã nguồn khớp con số đúng: 9 thư mục `ag_*`, cả 9 có `PHAM_VI.md`.

Đây là chỗ mất điểm ở đúng câu phản biện §17.2 mà đội đã chuẩn bị trước. Sửa
hồ sơ, **không** sửa mã. Chi tiết ở `docs/ket-qua-tong-hop.md` ghi chú 4.

## Số đo được thêm (§18.2)

| # | Trước | Sau |
|---|---|---|
| 4 — vi phạm ràng buộc cứng | chưa đo | fixture **TOTAL 0** (c01→c06), kiểm bằng `scripts/verify_hard.py` độc lập với bộ giải |
| 5 — AG-TKB | chưa đo | **98,04% (50/51)**, đẩy lên người **1,96%** |
| 6 — AG-MSG | chưa đo | **200/200**, ma trận trong `metrics-18-2.md` |

## Còn lại, và vì sao tôi không tự lấp

Bảy số vẫn `chưa đo`: #1 #3 #7 #8 #9 #11 #12. Cả bảy đều cần **quán thật dùng
hệ thống** — tỉ lệ không-cần-sửa theo tuần, thời gian xếp ca của quản lý, tỉ lệ
hoàn thành phiếu, việc treo được ca sau nhận, sai số sổ tiêu thụ, traffic qua
cổng VF, và số lần gọi mô hình mỗi ngày.

Không có cách nào sinh ra chúng từ máy. Hồ sơ đã tự đặt luật ở §18.2 — *"cấm số
phỏng đoán"* — và ở lời cuối: *"một hồ sơ có sẵn con số đẹp ở tuần 0 là một hồ
sơ đã bịa"*. Nên chúng được để nguyên `chưa đo` kèm lý do.

Sprint 8 (tag `v1.0.0-final`, diễn tập demo ×5 có ≥2 lần offline, chạy trên 3
máy) cũng cần người thật thực hiện.

## Lệnh xác minh

```
python -m pytest -q                      # 252 passed
python -m ruff check packages apps scripts
python -m mypy packages apps             # 0 lỗi / 96 file
python scripts\validate_templates.py     # ok: 3 templates
python scripts\solve_tuan.py             # OPTIMAL, 0,07s, violations=0
python scripts\verify_hard.py            # TOTAL 0
cd apps\web ; npx tsc --noEmit ; npx next build ; npx playwright test   # 8 passed
```
