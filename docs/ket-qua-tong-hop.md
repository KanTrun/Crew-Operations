# Bảng kết quả tổng hợp — 12 con số (hồ sơ §18.2)

> **Cấm số phỏng đoán.** Chỉ số đo thật hoặc chữ `chưa đo` + lý do.
>
> Mọi dòng ghi `fixture` nghĩa là đo trên bộ dữ liệu dựng lại theo **ADR-012**,
> **không phải** dữ liệu quán thật. Phân biệt này là bắt buộc khi thuyết trình.

| # | Con số | Giá trị | Lý do nếu chưa đo | Cập nhật |
|---|--------|---------|-------------------|----------|
| 1 | Tỉ lệ không cần sửa theo tuần (W1→W8) | **mô phỏng fixture:** 32,7 / 36,7 / 32,7 / 34,7 / 34,7 / 30,6 / 42,9 / 32,7 % · gộp 8 tuần **34,7% (136/392)** · quán thật: **chưa đo** | Nửa quán thật cần sổ sửa của quán — xem ghi chú 5 | 2026-08-24 |
| 2 | Chi phí thực tế toàn dự án (0đ?) | chưa đo | Sổ 14 dòng + ảnh hạn mức. Đã loại 1 phụ thuộc CDN (font) — xem ghi chú 2 | 2026-08-23 |
| 3 | Thời gian xếp ca trước / sau | trước: **chưa đo** · sau — **mô phỏng fixture: 0,088 s** (`OPTIMAL`, 25 người · 21 ca, 0 vi phạm cứng) | Nửa "trước" phải bấm đồng hồ tại quán khi quản lý xếp lịch tay. Hồ sơ có nêu 2,5–4 giờ nhưng đó là số nghe kể, bộ đo không ghi | 2026-08-24 |
| 4 | Vi phạm ràng buộc cứng trên lịch công bố | **fixture: 0/0/0/0/0/0 (c01→c06), TOTAL 0** · quán thật: chưa công bố lịch | Kiểm bằng `scripts/verify_hard.py` — script **độc lập với bộ giải** | 2026-08-23 |
| 5 | AG-TKB accuracy + % đẩy lên người | **98,04% (50/51)** · đẩy lên người: **1/51 = 1,96%** | Replay trên golden 51 ảnh, không gọi LLM thật | 2026-08-23 |
| 6 | AG-MSG confusion (6 ý định) | **200/200 = 100%** — ma trận trong `metrics-18-2.md` | Golden text lặp lại từ khoá nên **không phải bằng chứng NLU độc lập** | 2026-08-23 |
| 7 | Tỉ lệ hoàn thành phiếu + thời gian TB | **mô phỏng fixture:** đủ minh chứng **1344/1344 bước = 100%** · thiếu ảnh **560/1344 = 41,7%** (112 phiếu: 56 `mo_quan` + 56 `dong_quan`) · thời gian TB: **chưa đo** | 100% là kết quả cấu trúc — xem ghi chú 5. Thời gian TB cần dấu thời gian từ điện thoại nhân viên thật, đồng hồ trong bộ đo là ảo (5 s/bước, cố định để tất định) | 2026-08-24 |
| 8 | Việc treo được ca sau nhận / tổng | **mô phỏng fixture: 167/168 = 99,4%** (1 việc treo của ca cuối chuỗi không có ca sau) · quán thật: **chưa đo** | Máy quy trình không cho đóng phiếu bàn giao khi chưa qua bước người nhận xác nhận, nên tỉ lệ này là cấu trúc — xem ghi chú 5 | 2026-08-24 |
| 9 | Sai số sổ tiêu thụ vs đếm tay | **chưa đo** | Fixture ADR-012 nay CÓ khoá `kiem_ke` (nguồn `mo_phong_fixture`): 112 ca sáng/tối × 8 mặt hàng, đủ bốn cột §4.3 + cột đếm tay độc lập cho 5 mặt hàng tuần 1 — nên công thức chạy được về cấu trúc. Nhưng cả bốn cột và cột đếm tay đều do bộ sinh viết ra, nên sai số tính được chỉ là độ lệch bộ sinh vừa nhét vào — số vòng tròn. Cần ≥2 tuần kiểm kê thật | 2026-08-24 |
| 10 | Luật: đề xuất / loại / tập sự / duyệt / tự tắt | dựng lại: 1 / 1 / 5 / 1 / 1 · quán thật: **0** | ADR-012; `POST /cam-nang/chay-8-buoc` | 2026-08-22 |
| 11 | Lần cổng VF đẩy lên người (theo cổng) | **mô phỏng fixture:** VF-SCHEMA **0/51** · VF-TRACE **1/51** · VF-CONF **1/51** · VF-NUM **0/49** · VF-RULE **0/21** · VF-CONFLICT **50/51** · quán thật: **chưa đo** | Con số VF-CONFLICT cao là tính chất của fixture — xem ghi chú 5 | 2026-08-24 |
| 12 | Gọi model/ngày · p50/p95 latency · token | **mô phỏng fixture:** gọi mạng thật **0** · replay **51 lượt/ngày demo** (nạp trọn golden 51 ảnh) · p50/p95 và token: **chưa đo** | Đây là **replay, 0 lần gọi mạng thật** (router trả `provider='replay'`); mọi latency đo được là latency đọc tệp cục bộ, không phải latency LLM, và không có token nào sinh ra. Muốn số thật phải bật chế độ live và đọc hoá đơn provider | 2026-08-24 |

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

### 5. Bảy số vừa có giá trị đến từ đâu, và chỗ nào vẫn phải trống

Bộ đo: `python scripts/do_metrics.py` (hoặc `make metrics`) → in bảng và ghi
`data/out/metrics.json`. Bộ đo **tất định**: cùng fixture cho cùng kết quả, nên
người khác phát lại và kiểm chứng được. `apps/api/tests/unit/test_do_metrics.py`
chạy bộ đo hai lần và so kết quả, đồng thời chặn mọi bản ghi thiếu `nguon` hoặc
`cach_do`. Trường duy nhất được phép lệch giữa hai lần chạy là thời gian bấm
đồng hồ của bộ giải, và nó được **tự khai** trong `khong_tat_dinh`.

Nguồn dữ liệu: `data/seed/sample.json` — Quán Fixture NHỊP QUÁN (ADR-012). Khi
quán thật vào thì đổi hàm nạp dữ liệu; công thức, bảng và schema bản ghi không
đổi.

**Ba con số cần đọc kèm cảnh báo, vì cao không phải nhờ hệ thống:**

| Số | Con số | Vì sao không được kể như thành tích |
|---|---|---|
| 7 | 1344/1344 bước = 100% | Kịch bản fixture cấp đủ minh chứng cho **mọi** bước, nên 100% chứng minh máy quy trình đi đúng thứ tự và đóng được phiếu, **không** chứng minh nhân viên làm đủ bước. Cột đối chứng `thiếu ảnh` 41,7% mới là chỗ cho thấy cổng minh chứng ảnh thật sự chặn |
| 8 | 167/168 = 99,4% | Máy quy trình **không cho** đóng phiếu bàn giao nếu chưa qua bước người nhận xác nhận. Con số này chứng minh chuỗi bàn giao không rơi việc **trong mã**, không chứng minh nhân viên thật có đọc việc treo |
| 11 | VF-CONFLICT 50/51 | Hai nguồn TKB trong fixture được sinh **độc lập** (seed khai 1 khối bận, ảnh golden vẽ 3–4 khối), nên đây là mức lệch của fixture, không phải mức lệch dữ liệu tại quán |

**Số #1 đo cái gì, nói cho đúng.** Công thức là (tổng phân công − số phân công
phải sửa)/tổng, theo từng tuần. Trên fixture, "phải sửa" = số cặp (ca, nhân
viên) bị ràng buộc cứng c01–c06 chỉ tên khi chạy `solve_hard_only` trên đúng
tuần đó. Lịch sử 8 tuần của fixture do bộ sinh **bốc ngẫu nhiên**
(`scripts/generate_fixture_data.py`), không do bộ giải sinh — vì thế đường
W1→W8 đi ngang (32,7 → 42,9%) chứ không dốc lên, và nó **đo mức hợp lệ của lịch
sử fixture, không đo hiệu quả hệ thống**. Nó chỉ thành chỉ số §18.2 khi tử số
lấy từ sổ sửa của quán thật (`ca_playbook.list_sua`).

**Bốn chỗ vẫn trống, và vì sao thà trống:**

| Chỗ trống | Lý do |
|---|---|
| #3 nửa "trước" | Phải bấm đồng hồ khi quản lý quán xếp lịch bằng Excel. Hồ sơ có nêu 2,5–4 giờ, đó là số nghe kể — bộ đo không ghi nó vào bảng |
| #7 thời gian TB | Nhịp 5 giây/bước là **đồng hồ ảo** do bộ đo đặt để tất định. Số thật cần dấu thời gian từ điện thoại nhân viên |
| #9 toàn bộ | Fixture không có một số kiểm kê nào. Nếu tự sinh số synthetic thì sai số đo được chỉ là sai số bộ sinh vừa nhét vào — **số vòng tròn**, không phải số đo |
| #12 p50/p95 và token | Replay: **0 lần gọi mạng thật**. Latency đo được là latency đọc tệp cục bộ, không phải latency LLM; không lời gọi mô hình nào nên không có token |

### 6. Vì sao KHÔNG nối API bên ngoài nào cho Lô 1

Có yêu cầu "tự tìm và nối API bên ngoài nếu có". Đã xem xét và **quyết định không
nối**, vì cả ba lý do dưới đây đều là ràng buộc của chính đề tài:

**1. Luận điểm trung tâm của đề tài là không cần tích hợp.** §2.2 định vị NHỊP
QUÁN khác các sản phẩm thương mại ở chỗ nó *"đọc đúng những gì quán vốn đã tạo
ra"* thay vì cần tích hợp hệ thống bán hàng. §4.3 còn xây cả mạng cảm biến từ
chênh lệch hai lần kiểm kê để **khỏi phải** tích hợp. Nối thêm API bên ngoài
làm loãng đúng cái lập luận mạnh nhất của hồ sơ.

**2. API duy nhất hồ sơ dự tính là thời tiết, và nó thuộc Lô 2.** §10.3 dòng 6
xếp API thời tiết cho **AG-FORECAST**, mà AG-FORECAST nằm ở Lô 2 (§5.2). Plan
ghi rõ Lô 2 *"không cook trong plan này"*. Xây một client API chưa có ai tiêu
thụ là thêm mã chết, và nó rơi đúng vào lỗi mà §6.3 đã dùng để loại bốn đề
xuất agent: *"một tính năng demo trên dữ liệu giả sẽ bị hội đồng phát hiện
ngay"*.

**3. Nó phá cổng ra Sprint 8.** §14.9 buộc demo chạy trọn 10 phút khi **đã rút
mạng**. Mỗi lời gọi ra ngoài là một điểm chết khi hội trường mất mạng. Đây cũng
chính là lý do đã bỏ font CDN ở ghi chú 2 — thêm API mới lại là đi ngược việc
vừa sửa.

**Điều kiện mở lại:** khi Lô 2 khởi động và có ≥3 tuần sổ tiêu thụ thật (§13.6),
lúc đó AG-FORECAST mới có đầu vào và API thời tiết mới có người tiêu thụ. Khi
đó phải kiểm điều khoản sử dụng trước (§18.3 việc 4) và đặt sau một cổng có
đường lùi offline.

**Không phải là không làm được** — mà là làm thì hỏng ba thứ đang đúng.
