# Bảng kết quả tổng hợp — 12 con số (hồ sơ §18.2)

> **Cấm số phỏng đoán.** Chỉ số đo thật hoặc chữ `chưa đo` + lý do.
>
> Mọi dòng ghi `fixture` nghĩa là đo trên bộ dữ liệu dựng lại theo **ADR-012**,
> **không phải** dữ liệu quán thật. Phân biệt này là bắt buộc khi thuyết trình.

| # | Con số | Giá trị | Lý do nếu chưa đo | Cập nhật |
|---|--------|---------|-------------------|----------|
| 1 | Tỉ lệ không cần sửa theo tuần (W1→W8) | chưa đo | Chưa có tuần dùng hệ thống tại quán | |
| 2 | Chi phí thực tế toàn dự án (0đ?) | chưa đo | Sổ 14 dòng + ảnh hạn mức. Đã loại 1 phụ thuộc CDN (font) — xem ghi chú 2 | 2026-08-23 |
| 3 | Thời gian xếp ca trước / sau | chưa đo | Chưa đo hiện trạng tại quán | |
| 4 | Vi phạm ràng buộc cứng trên lịch công bố | **fixture: 0/0/0/0/0/0 (c01→c06), TOTAL 0** · quán thật: chưa công bố lịch | Kiểm bằng `scripts/verify_hard.py` — script **độc lập với bộ giải** | 2026-08-23 |
| 5 | AG-TKB accuracy + % đẩy lên người | **98,04% (50/51)** · đẩy lên người: **1/51 = 1,96%** | Replay trên golden 51 ảnh, không gọi LLM thật | 2026-08-23 |
| 6 | AG-MSG confusion (6 ý định) | **200/200 = 100%** — ma trận trong `metrics-18-2.md` | Golden text lặp lại từ khoá nên **không phải bằng chứng NLU độc lập** | 2026-08-23 |
| 7 | Tỉ lệ hoàn thành phiếu + thời gian TB | chưa đo | Chưa chạy phiếu thật tại quán | |
| 8 | Việc treo được ca sau nhận / tổng | chưa đo | Chưa bàn giao ca thật | |
| 9 | Sai số sổ tiêu thụ vs đếm tay | chưa đo | Cần ≥2 tuần kiểm kê thật | |
| 10 | Luật: đề xuất / loại / tập sự / duyệt / tự tắt | dựng lại: 1 / 1 / 5 / 1 / 1 · quán thật: **0** | ADR-012; `POST /cam-nang/chay-8-buoc` | 2026-08-22 |
| 11 | Lần cổng VF đẩy lên người (theo cổng) | chưa đo | Chưa có traffic thật | |
| 12 | Gọi model/ngày · p50/p95 latency · token | chưa đo | Router chưa chạy production | |

**Ba dòng ưu tiên nếu thiếu thời gian:** #1 · #2 · #10.

---

## Ghi chú

### 1. Vì sao #5 thấp hơn nghe tưởng, và vì sao vẫn nên nêu

51 ảnh golden, đọc đúng 50. Ảnh còn lại là ảnh **cố tình làm mờ**; VF-CONF thấy độ tin
cậy dưới ngưỡng nên **đẩy lên người thay vì đọc sai vào lịch**. Đây đúng là hành vi
mong muốn: hồ sơ §18.2 ghi rõ con số này *"mạnh kể cả khi thấp, miễn là tỉ lệ đẩy lên
người cao tương ứng"*.

Giới hạn phải nói ra: đây là **replay trên ảnh rõ**, nên độ chính xác gần như hoàn hảo
là *do thiết kế bộ mẫu*, không phải bằng chứng về thị giác máy tính khi gặp ảnh thật.

### 2. Một phụ thuộc CDN đã bị loại khỏi đường demo

Trước 2026-08-23, `apps/web` tải font từ `fonts.googleapis.com` bằng `<link>`. Việc
này phá **cổng ra Sprint 8 (§14.9)**, vì cổng đó yêu cầu demo chạy trọn 10 phút khi
**đã rút mạng** — không có font thì chữ rơi về Georgia/system-ui giữa buổi bảo vệ.

Đã chuyển sang `next/font` (self-host lúc build, xem `apps/web/src/ui/fonts.ts`).
Kiểm chứng sau khi build:

| Kiểm | Kết quả |
|---|---|
| File font tự host trong `.next/static/media` | **20 file `.woff2`** |
| Tham chiếu `fonts.googleapis` / `fonts.gstatic` trong HTML đã render | **0** |
| Subset `vietnamese` | Có, cho `Fraunces` và `Source Sans 3` |

Đây vừa là sửa lỗi thẩm mỹ vừa là sửa lỗi tuân thủ cổng ra. Nó **không** làm #2 thành
số đo được — #2 vẫn cần sổ 14 dòng và ảnh trang hạn mức.

### 3. Chất lượng công trình — không thuộc 12 số, nhưng kiểm được ngay

Không phải chỉ số §18.2, nêu ở đây vì đây là bằng chứng máy kiểm được mỗi lần commit:

| Hạng mục | Giá trị | Lệnh kiểm |
|---|---|---|
| Test tự động | **252 PASS** (mốc hồ sơ §11.4: 215) | `python -m pytest -q` |
| Coverage `packages` + `apps/api/src` | **94%** | `python -m pytest --cov=packages --cov=apps/api/src` |
| Lint | sạch | `python -m ruff check packages apps` |
| Type (`mypy --strict`) | **0 lỗi / 96 file** | `python -m mypy packages apps` |
| Thời gian giải lịch fixture (25 người · 21 ca) | **0,07 s**, status `OPTIMAL` (cổng S2: <60 s) | `python scripts\solve_tuan.py` |
| Agent Lô 1 có `PHAM_VI.md` đủ 9 thuộc tính | **9/9 thư mục `ag_*`** | `python -m pytest packages/agents/tests/test_architecture.py` |

### 4. ⚠️ Hồ sơ tự mâu thuẫn về số agent Lô 1 — phải sửa trước khi nộp

Hồ sơ v3.0 nói **"Lô 1: 10 agent · Lô 2: 3 agent"** (§1.2 và §5.2). Đếm lại từ chính
bảng §5.2 thì không khớp:

| Nhóm | Agent Lô 1 | Agent Lô 2 |
|---|---|---|
| 1 — Thu ràng buộc | AG-TKB, AG-MSG, AG-HANDOVER | — |
| 2 — Vận hành & tri thức | AG-SOP, AG-RULE | — |
| 3 — Kho vận | AG-WASTE | AG-FORECAST, AG-INVOICE, AG-SHELF |
| 4 — Diễn giải | AG-EXPLAIN, AG-BRIEF | — |
| 5 — Tiếng nói khách | AG-VOC | AG-MENUOPS |
| **Tổng** | **9** | **4** |

Con số đúng là **Lô 1 = 9 · Lô 2 = 4** (tổng vẫn 13). Hai chỗ khác trong hồ sơ đã dùng
đúng số 9: bảng số lần gọi mô hình §10.1 liệt kê đúng 9 agent, và §13.6 liệt kê đúng 4
agent Lô 2.

Mã nguồn khớp với con số **đúng**:

```
packages/agents/src/ca_agents/  →  9 thư mục ag_*, cả 9 đều có PHAM_VI.md
ag_brief · ag_explain · ag_handover · ag_msg · ag_rule
ag_sop   · ag_tkb     · ag_voc      · ag_waste
```

**Vì sao phải sửa hồ sơ, không sửa mã:** câu phản biện §17.2 hỏi thẳng *"mười ba agent,
có phải để hồ sơ trông dày không"*. Nếu đội trả lời "ship 10 con" mà repo chỉ có 9 thư
mục, đó là mất điểm tin cậy ở đúng câu hỏi mình đã chuẩn bị trước. Sửa §1.2 và §5.2
thành 9/4 là xong.
