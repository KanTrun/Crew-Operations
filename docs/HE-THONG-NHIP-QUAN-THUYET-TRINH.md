# NHỊP QUÁN — Hệ thống Doanh nghiệp do AI COPILOT Điều hành

**Tài liệu dùng để tạo slide thuyết trình**

---

## 1. NHỊP QUÁN là gì?

NHỊP QUÁN là **hệ thống doanh nghiệp được điều hành bởi AI COPILOT** — một trí tuệ nhân tạo đứng đầu, chỉ huy toàn bộ hoạt động vận hành quán cà phê, từ xếp ca, kiểm kê, bàn giao, đến dự báo nhu cầu và tự hoàn thiện quy trình.

AI COPILOT không phải một chatbot hay trợ lý đơn lẻ. Nó là **bộ não điều hành** — phối hợp 11 agent chuyên biệt, 8 cổng kiểm chứng, bộ giải tối ưu và cẩm nang tự học thành một hệ thống vận hành khép kín, thay thế toàn bộ Excel, sổ giấy và nhóm chat rời rạc mà một quán cà phê 15–40 nhân viên đang dùng mỗi ngày.

**Ba trụ cột:**

- **AI COPILOT điều hành** — Copilot chỉ huy toàn bộ luồng nghiệp vụ: thu thập dữ liệu, điều phối agent, kiểm chứng kết quả, vận hành quy trình, và tự học từ mỗi quyết định của con người
- **Hệ sinh thái Agent khai thác tối đa** — 11 agent chuyên biệt phủ kín mọi khía cạnh vận hành: đọc ảnh, đọc tin nhắn, đọc bàn giao, đọc hao hụt, đọc phản hồi khách, trực Fanpage, đề xuất luật, giải thích, tóm tắt, hỏi đáp quy trình
- **Con người kiểm soát cuối cùng** — AI chạy toàn bộ, nhưng mọi quyết định quan trọng (duyệt lịch, duyệt luật, chốt đơn hàng, kết luận gian dối) đều do con người bấm nút

---

## 2. Kiến trúc tổng thể — AI COPILOT ở trung tâm

```
┌─────────────────────────────────────────────────────────────┐
│                    NGƯỜI PHÊ DUYỆT                           │
│   Duyệt ràng buộc · Chốt lịch · Duyệt luật · Duyệt đơn hàng  │
│   Xử lý mọi thứ bị cổng kiểm chứng đẩy lên                   │
│              CON NGƯỜI GIỮ QUYỀN PHỦ QUYẾT                   │
└──────────────────────────▲──────────────────┬───────────────┘
                           │                  │ mỗi lần sửa
┌──────────────────────────┼──────────────────┼───────────────┐
│                                                                  │
│              AI COPILOT — BỘ NÃO ĐIỀU HÀNH                      │
│                                                                  │
│   Điều phối agent · Chạy máy trạng thái · Phát nhiệm vụ         │
│   Retry · Timeout · Idempotency · Trần ngân sách               │
│   Ghi vết · Phát lại phiên · NGƯỜI GHI DUY NHẤT               │
│                                                                  │
│   Copilot quyết định: gọi agent nào, khi nào, kiểm tra gì,     │
│   nạp kết quả vào đâu, escalate khi nào                        │
│                                                                  │
└──┬──────────────┬──────────────┬───────────────────┬────────────┘
   ▼              ▼              ▼                   ▼
┌─ LÀN ĐỌC ────┐ ┌─ LÀN DIỄN ─┐ ┌─ LÀN HỌC ──────┐ ┌─ LÕI ─────────┐
│ AG-TKB       │ │ AG-EXPLAIN │ │ AG-RULE ⭐     │ │ CP-SAT        │
│ AG-MSG       │ │ AG-BRIEF   │ │                │ │ RULE ENGINE   │
│ AG-HANDOVER  │ │ AG-SOP     │ │                │ │ MÁY QUY TRÌNH │
│ AG-WASTE     │ │            │ │                │ │ SỔ TIÊU THỤ   │
│ AG-VOC       │ │            │ │                │ │               │
└──────┬───────┘ └─────┬──────┘ └───────┬────────┘ └───────▲───────┘
       └───────────────┴────────────────┘                  │
                       ▼                                   │
        ┌─ 8 CỔNG KIỂM CHỨNG (TẤT ĐỊNH) ─┐                │
        │ SCHEMA · TRACE · CONF ·         │────────────────┘
        │ CONFLICT · NUM · RULE ·          │
        │ SCOPE · STALE                    │
        │  không đạt → ĐẨY LÊN NGƯỜI       │
        └──────────────────┬──────────────┘
                           ▼
                  ┌─ CẨM NANG QUÁN ─┐
                  │ luật đọc được,   │──── trở thành tham số lõi
                  │ bật tắt được     │
                  └──────────────────┘
```

**AI COPILOT điều hành như thế nào:**

Copilot là tầng chỉ huy — nó quyết định khi nào cần gọi agent, gọi agent nào, kiểm tra kết quả bằng cổng nào, nạp dữ liệu vào lõi nào, và khi nào phải đẩy lên người. Mỗi tác vụ trong hệ thống đều đi qua Copilot.

**Nguyên tắc bất biến:**

1. **Agent không gọi agent** — Copilot điều phối tất cả, chuỗi agent dài tối đa một bước
2. **Agent không ghi cơ sở dữ liệu** — Copilot (bộ điều phối) là người ghi duy nhất
3. **Agent không quyết định luồng** — Copilot chuyển trạng thái theo điều kiện viết bằng mã
4. **Con người giữ quyền phủ quyết** — mọi quyết định quan trọng đều chờ người bấm duyệt

---

## 3. Hệ sinh thái Agent — 11 Agent do Copilot điều phối

Copilot khai thác tối đa tiềm năng của AI bằng cách triển khai 11 agent chuyên biệt, mỗi agent phụ trách một khía cạnh vận hành. Copilot quyết định khi nào gọi agent nào và kiểm tra kết quả trước khi nạp vào hệ thống.

### Nhóm 1 — Thu ràng buộc và nhân sự

| Mã Agent | Tên | Chức năng | Đầu vào | Đầu ra |
|---|---|---|---|---|
| **AG-TKB** | Đọc thời khoá biểu | Đọc ảnh thời khoá biểu của sinh viên, trích xuất khoảng giờ học thành ràng buộc cứng | Một ảnh chụp | Danh sách khoảng giờ học không được xếp ca |
| **AG-MSG** | Đọc tin nhắn | Phân loại ý định từ tin nhắn tự do của nhân viên (xin nghỉ, đổi ca, báo trễ...) | Một tin nhắn | Một trong 6 ý định, kèm ràng buộc trích xuất |
| **AG-HANDOVER** | Đọc bàn giao ca | Đọc nội dung bàn giao giữa hai ca thành cấu trúc SBAR | Một phiếu bàn giao | Bốn ô SBAR và danh sách việc treo |

### Nhóm 2 — Vận hành và tri thức nội bộ

| Mã Agent | Tên | Chức năng |
|---|---|---|
| **AG-SOP** | Trợ lý quy trình | Hỏi đáp quy trình cho nhân viên mới. **Chỉ trả lời từ mẫu phiếu và cẩm nang của chính quán**, kèm trích dẫn. Không có căn cứ thì nói "chưa có trong cẩm nang" |
| **AG-RULE** ⭐ | Đề xuất luật | Từ một lần con người sửa lịch, đề xuất **một** luật vận hành bằng tiếng Việt kèm bằng chứng. Là agent quan trọng nhất — nguồn gốc của Cẩm nang sống |

### Nhóm 3 — Kho vận và chất lượng

| Mã Agent | Tên | Chức năng |
|---|---|---|
| **AG-WASTE** | Đọc hao hụt | Đọc ghi chú hao hụt viết tự do thành số lượng và nguyên nhân có cấu trúc. Ví dụ: "làm sai 2 ly, bánh hết ngày 3 cái" → hai dòng có mặt hàng, số lượng, nguyên nhân |

### Nhóm 4 — Diễn giải cho con người

| Mã Agent | Tên | Chức năng |
|---|---|---|
| **AG-EXPLAIN** | Dịch mã lý do | Dịch mã lý do của bộ giải tối ưu thành câu tiếng Việt mà quản lý hiểu được |
| **AG-BRIEF** | Bản tin sáng | Viết bản tin sáng cho chủ quán, tối đa 5 câu, tóm tắt tình hình ngày hôm nay |

### Nhóm 5 — Tiếng nói khách hàng

| Mã Agent | Tên | Chức năng |
|---|---|---|
| **AG-VOC** | Phản hồi khách | Đọc phản hồi khách **do quán tự cung cấp**, phân loại thành sự cố vận hành và nối vào việc treo. Không tự trả lời khách |

### Nhóm 6 — Tương tác khách hàng qua Facebook

| Mã Agent | Tên | Chức năng |
|---|---|---|
| **AG-FBPAGE** | Trực Fanpage | Điều phối 4 sub-agent (FRONTDESK/BARISTA/CONCIERGE/SUPERVISOR) trả lời khách trên Facebook. **5 lớp kiểm duyệt** trước khi gửi: Input Guardrail → Rate Limit → Intent Classifier → Policy Engine → Supervisor. Chỉ tin nhắn an toàn (chào hỏi, hỏi giờ/địa chỉ) với độ tin cậy ≥0.9 mới tự gửi; tất cả còn lại chờ người duyệt |

---

## 4. Tám cổng kiểm chứng — Copilot tự kiểm tra trước khi trình người

Copilot không tin mù vào kết quả của agent. Mỗi đầu ra đều đi qua 8 cổng kiểm chứng tất định (**không có AI**) trước khi nạp vào hệ thống hoặc trình lên người phê duyệt.

| Cổng | Kiểm tra gì | Không đạt thì làm gì |
|---|---|---|
| **VF-SCHEMA** | Đầu ra khớp lược đồ dữ liệu | Thử lại 1 lần, vẫn sai → đẩy lên người |
| **VF-TRACE** | Mọi thứ trích xuất trỏ về vùng ảnh/đoạn văn thật tồn tại | Loại phần không có nguồn |
| **VF-CONF** | Độ tin cậy đạt ngưỡng | Dưới ngưỡng → **luôn** đẩy lên người, không thử lại |
| **VF-CONFLICT** | Hai agent nói trái nhau về cùng một người, cùng khung giờ | **Không tự hoà giải.** Hiện cả hai, đẩy lên người |
| **VF-NUM** | Mọi con số trong câu diễn giải tồn tại trong dữ liệu đầu vào | Loại cả câu, ghi vào bảng câu bị loại |
| **VF-RULE** | Luật có ≥3 bằng chứng, điều kiện chỉ dùng trường tồn tại, không xung đột luật đã có | Loại, ghi lý do |
| **VF-SCOPE** | Agent không vượt phạm vi cho phép | Loại kết quả |
| **VF-STALE** | Dữ liệu đầu vào không quá cũ so với thời điểm hiện tại | Cảnh báo hoặc đẩy lên người |

**Nguyên tắc thất bại đóng (fail-closed):** khi không chắc chắn, hệ thống **luôn** chuyển sang chờ người quyết định, không bao giờ chọn phương án "có vẻ hợp lý".

---

## 5. Bảy luồng nghiệp vụ do Copilot vận hành

Mỗi luồng nghiệp vụ đều do AI COPILOT điều phối từ đầu đến cuối — thu thập dữ liệu, gọi agent, kiểm chứng, nạp vào lõi, và trình người duyệt khi cần.

### 5.1. Xếp ca tuần

```
Nhân viên gửi ràng buộc (tin nhắn / ảnh TKB)
        │
        ▼
AG-MSG / AG-TKB trích xuất ràng buộc
        │
        ▼
8 cổng kiểm chứng kiểm tra
        │
   ┌────┴────┐
   │ Đạt     │ Không đạt
   ▼         ▼
Hộp thư     Đẩy lên người
ràng buộc    xử lý thủ công
   │
   ▼
Quản lý duyệt ràng buộc
   │
   ▼
Ràng buộc nạp vào bộ giải CP-SAT
   │
   ▼
CP-SAT xếp lịch tuần:
  • 6 ràng buộc cứng (C01–C06):
    - C01: Không trùng giờ học
    - C02: Đủ người và đủ vị trí kỹ năng mỗi ca
    - C03: Một người không ở hai ca cùng lúc
    - C04: Khoảng nghỉ tối thiểu giữa hai ca
    - C05: Trần giờ tuần và ngày liên tiếp
    - C06: Ngày đã duyệt nghỉ phép
  • 5 ràng buộc mềm có trọng số (S01–S05):
    - S01: Nguyện vọng ca
    - S02: Chia đều ca cuối tuần và ca đêm
    - S03: Ca liền mạch tránh lịch vụn
    - S04: Ổn định so với tuần trước
    - S05: Ghép người mới với người có kinh nghiệm
  • Sổ nợ công bằng 4 chiều:
    tối thiểu hoá nợ LỚN NHẤT (bảo vệ người bị đối xử tệ nhất)
   │
   ▼
AG-EXPLAIN dịch mã lý do → câu tiếng Việt
   │
   ▼
Quản lý duyệt lịch → Công bố → Gửi tin cho từng người
```

**Vòng đời lịch:** `nháp → đang giải → chờ duyệt → đã duyệt → đã công bố → đã đóng`

---

### 5.2. Chợ đổi ca — Ba nhánh

```
A đăng nhả ca
  │
  ▼
Hệ thống tìm người đủ điều kiện, kiểm 5 điều:
  • Không trùng giờ học
  • Không trùng ca khác
  • Đủ giờ nghỉ giữa ca
  • Chưa vượt trần giờ tuần
  • Có kỹ năng vị trí đó cần
  │
  ▼
Gửi lời mời CHỈ cho những người đủ điều kiện
  │
  ▼
B nhận ca:
  ┌─────────────────────────────────────────────────┐
  │ Thoả HẾT ràng buộc → TỰ DUYỆT                   │
  │   quản lý nhận báo cáo sau                       │
  ├─────────────────────────────────────────────────┤
  │ Vi phạm ràng buộc MỀM → chuyển quản lý duyệt     │
  │   NÊU RÕ vi phạm gì                              │
  ├─────────────────────────────────────────────────┤
  │ Vi phạm ràng buộc CỨNG → CHẶN                   │
  │   không cho nhận                                 │
  └─────────────────────────────────────────────────┘
```

**Lưu ý quan trọng:** khi B nhận ca của A, hệ thống kiểm lại ràng buộc **theo trạng thái lịch tại thời điểm nhận**, không phải lúc A đăng.

---

### 5.3. Mở quán và Đóng quán (Phiếu vận hành)

```
Nhân viên điểm danh QR
  │
  ▼
Hệ thống mở phiếu (không điểm danh → không mở được phiếu)
  │
  ▼
Nhân viên chạy từng bước trên điện thoại:
  • Bật máy pha và chờ đủ nhiệt
  • Ghi nhiệt độ tủ lạnh (ngoài ngưỡng → sinh việc treo)
  • Vệ sinh quầy (bắt buộc ảnh chụp mới)
  • Kiểm kê 8 mặt hàng chính (số này đi vào SỔ TIÊU THỤ)
  • Đọc việc treo từ ca trước
  • ... (20+ bước)
  │
  ▼
Mỗi bước có ba kết quả:
  ┌──────────────┬──────────────────────────────────┐
  │ Đã làm       │ Bước hoàn thành bình thường       │
  ├──────────────┼──────────────────────────────────┤
  │ Không áp dụng│ Bước không cần làm ca này         │
  ├──────────────┼──────────────────────────────────┤
  │ Có vấn đề    │ Sinh VIỆC TREO có người nhận     │
  │              │ và hạn hoàn thành                 │
  └──────────────┴──────────────────────────────────┘
```

**Cơ chế chống tích khống:**

| Cơ chế | Cách hoạt động |
|---|---|
| Ảnh phải chụp mới | Chỉ nhận ảnh từ camera trong phiên, phát hiện ảnh dùng lại bằng băm nội dung |
| Dấu thời gian máy chủ | Không tin dấu thời gian của điện thoại |
| Gắn với ca và người | Người ca sáng không làm được phiếu của ca chiều |
| Phát hiện mẫu bất thường | Phiếu 20 bước xong dưới 90 giây; nhiều ngày điền cùng một phút; ảnh trùng băm |
| Bảng dấu hiệu cho chủ | **Không tự kết luận ai gian.** Chỉ hiện dấu hiệu kèm dữ liệu |

**Mẫu phiếu là dữ liệu (YAML), không phải mã nguồn.** Thêm quy trình mới mất 60 giây, không cần lập trình.

---

### 5.4. Bàn giao ca (SBAR)

```
Ca sắp hết → Hệ thống mở phiếu bàn giao
  │
  ▼
Nhân viên CA TRƯỚC điền:
  ┌──────────────────┬──────────────────────────────────┐
  │ Đang thế nào     │ Tình trạng quán lúc giao ca       │
  │ (Situation)      │                                   │
  ├──────────────────┼──────────────────────────────────┤
  │ Chuyện đã xảy ra │ Việc gì đã diễn ra trong ca       │
  │ (Background)     │                                   │
  ├──────────────────┼──────────────────────────────────┤
  │ Cần để ý        │ Máy có tiếng lạ, sữa gần hết...   │
  │ (Assessment)     │                                   │
  ├──────────────────┼──────────────────────────────────┤
  │ Việc treo lại    │ Danh sách việc cụ thể,            │
  │ (Recommendation) │ có người nhận và hạn              │
  └──────────────────┴──────────────────────────────────┘
  │
  ▼
AG-HANDOVER đọc thành cấu trúc SBAR
  │
  ▼
Nhân viên CA SAU xác nhận danh sách việc treo
  (người NHẬN xác nhận, không phải người GIAO)
  │
  ▼
Việc treo chưa xong → chuyển tiếp sang ca sau
Quá 3 ca chưa xong → escalate lên chủ quán
```

---

### 5.5. Kiểm kê → Sổ tiêu thụ → Dự báo

```
Phiếu mở quán: kiểm kê đầu ca (số đếm A)
        │
Phiếu đóng quán: kiểm kê cuối ca (số đếm B)
        │
        ▼
SỔ TIÊU THỤ (tất định, không có AI):

  tiêu thụ = đếm đầu ca + nhập trong ca − đếm cuối ca − hao hụt đã ghi

        │
        ▼
Từ đó suy ra được:
  ┌─────────────────────────────────────────────────────────────┐
  │ Lượng tiêu thụ từng mặt hàng theo ca và theo thứ trong tuần │
  │ → Dự báo nhu cầu, đặt ngưỡng tồn                            │
  ├─────────────────────────────────────────────────────────────┤
  │ Mức độ đông của ca (tính bằng nguyên liệu chính đã dùng)    │
  │ → Đề xuất số người cần cho ca tương tự tuần sau             │
  ├─────────────────────────────────────────────────────────────┤
  │ Sai lệch giữa tiêu thụ dự kiến và thực tế                   │
  │ → Dấu hiệu hao hụt bất thường cần người xem                 │
  └─────────────────────────────────────────────────────────────┘
```

**Đây là ý tưởng mạnh nhất:** một tính năng xây vì tuân thủ (bước kiểm kê trong checklist) trở thành **mạng cảm biến** cho toàn bộ phần dự báo — không cần tích hợp hệ thống bán hàng.

---

### 5.6. Bù ca khẩn

```
Quá 15 phút không điểm danh
  │
  ▼
Nhắc riêng nhân viên đó
  │
Quá 25 phút
  │
  ▼
Mở BÙ CA KHẨN:
  • Tìm người đủ 5 điều kiện (như chợ đổi ca)
  • Xếp theo: đang rảnh → nợ công bằng thấp → ở gần
  • Gửi lời mời cho tối đa 5 người cùng lúc
  • Ai nhận trước thì được
  │
Quá 40 phút
  │
  ▼
Báo chủ quán kèm danh sách đã mời và ai đã từ chối
```

**Khoá tranh chấp ở tầng cơ sở dữ liệu:** khi nhiều người bấm nhận cùng lúc, đúng một người được.

---

### 5.7. Hao hụt

```
Nhân viên ghi chú hao hụt trong ca (viết tự do)
  │
  ▼
AG-WASTE đọc thành cấu trúc:
  "làm sai 2 ly, bánh hết ngày 3 cái"
  → Dòng 1: mặt hàng=ly, số lượng=2, nguyên nhân=làm sai
  → Dòng 2: mặt hàng=bánh, số lượng=3, nguyên nhân=hết hạn
  │
  ▼
Ghi vào sổ hao hụt → nối vào sổ tiêu thụ
  │
  ▼
Dữ liệu hao hụt theo thời gian → AG-RULE tìm mẫu lặp lại
  → đề xuất luật (ví dụ: "bánh hết ngày thường dư vào tối thứ Ba")
```

---

## 6. Cẩm nang sống — Copilot tự học từ con người

Đây là tính năng cốt lõi tạo nên sự khác biệt của NHỊP QUÁN: **Copilot quan sát mỗi lần con người sửa, tìm mẫu lặp lại, đề xuất luật, tự kiểm chứng, tự tập sự, rồi trình người duyệt.**

```
Bước 1: GHI NHẬN
  Mỗi lần người sửa lịch, lưu cặp (trước, sau) kèm bối cảnh
      │
Bước 2: TÌM MẪU
  Đủ 3 lần sửa cùng mẫu → đưa vào hàng đợi AG-RULE
  Dưới 3 lần → không làm gì
      │
Bước 3: ĐỀ XUẤT
  AG-RULE viết MỘT câu luật tiếng Việt
  + điều kiện có cấu trúc
  + danh sách bằng chứng là các lần sửa cụ thể
      │
Bước 4: KIỂM CHỨNG (VF-RULE)
  • Đủ 3 bằng chứng?
  • Điều kiện dùng trường tồn tại?
  • Không xung đột luật đã có?
  → Không đạt: LOẠI, ghi lý do
      │
Bước 5: TẬP SỰ
  Luật chạy IM LẶNG 5 lần:
  hệ thống ghi "nếu áp dụng thì tôi sẽ làm X"
  rồi đối chiếu quyết định thật của người
  Đúng ≥ 4/5 → đủ điều kiện lên chính thức
      │
Bước 6: NGƯỜI DUYỆT
  Chủ hoặc quản lý xem câu luật, bằng chứng, kết quả tập sự
  Bấm duyệt → luật có hiệu lực
  Không duyệt → luật không bao giờ chạm vào quyết định thật
      │
Bước 7: CÓ HIỆU LỰC
  Luật trở thành tham số của lõi quyết định:
  • Ràng buộc bộ giải (thêm người cho ca thứ Bảy)
  • Bước phiếu mới (xả nước máy pha 2 lần sáng thứ Hai)
  • Ngưỡng tồn mới (sữa tươi cần 8 hộp, không phải 5)
      │
Bước 8: THEO DÕI
  Đếm số lần áp dụng và số lần bị người ghi đè
  Tỉ lệ đúng tụt dưới 80% → TỰ ĐỘNG TẮT và báo người xem lại
```

**Năm loại luật hệ thống được phép học:**

| Loại | Ví dụ |
|---|---|
| Nhu cầu người theo ca | "Thứ Bảy ca chiều cần 3 người pha chế, không phải 2" |
| Ngưỡng tồn của mặt hàng | "Sữa tươi cần ngưỡng 8 hộp, không phải 5" |
| Bước phiếu cần thêm/bỏ | "Ca sáng thứ Hai cần thêm bước xả nước máy pha hai lần" |
| Ghép người theo kỹ năng | "Ca cuối tuần nên có ít nhất một người đã làm trên 3 tháng" |
| Nguyên nhân hao hụt lặp lại | "Bánh hết ngày thường dư vào tối thứ Ba, nên giảm nhập thứ Ba" |

**Cấm tuyệt đối:** luật về năng lực hoặc thái độ của một con người cụ thể.

---

## 7. AG-SOP — Copilot biến cẩm nang thành người hướng dẫn

Nhân viên mới hỏi bằng tiếng Việt tự nhiên:
- *"Nhiệt độ tủ lạnh bao nhiêu là được?"*
- *"Sáng thứ Hai có gì khác không?"*
- *"Máy pha có tiếng lạ thì làm gì?"*

Copilot điều phối AG-SOP trả lời **chỉ dựa trên hai nguồn:**
1. Mẫu phiếu YAML (quy trình vận hành)
2. Các luật đã duyệt trong Cẩm nang sống

Mỗi câu trả lời **kèm trích dẫn** là bước phiếu nào hoặc luật nào.

Không có căn cứ trong hai nguồn trên → trả lời *"chưa có trong cẩm nang của quán, hãy hỏi quản lý"*.

**Vòng lặp đóng lại:** tri thức mà Copilot học được từ chị quản lý **quay lại dạy nhân viên mới thay chị** — tự động, không cần chị viết tài liệu.

---

## 8. Kênh tương tác

### 8.1. Chat nội bộ `/chat`

Toàn bộ giao tiếp giữa nhân viên và hệ thống diễn ra qua **chat nội bộ `/chat`** ngay trong ứng dụng web.

Nhân viên gửi ràng buộc, xin nghỉ, đổi ca, hỏi quy trình — tất cả trong cùng một khung chat, không cần cài thêm ứng dụng bên ngoài.

### 8.2. Facebook Fanpage — AG-FBPAGE

Hệ thống tích hợp Facebook Fanpage để tương tác với khách hàng qua tin nhắn Messenger và bình luận bài đăng.

**Kiến trúc 4 sub-agent:**

| Sub-agent | Vai trò |
|---|---|
| **FRONTDESK** | Chào hỏi, hỏi giờ mở cửa, địa chỉ |
| **BARISTA** | Hỏi menu, giá, khuyến mãi |
| **CONCIERGE** | Đặt bàn, yêu cầu đặc biệt |
| **SUPERVISOR** | Khiếu nại, góp ý, xử lý sự cố |

**5 lớp kiểm duyệt tin nhắn (pre-flight gate):**

```
Lớp 1: INPUT GUARDRAIL
  • Chặn spam, injection, toxic
  • Phát hiện prompt injection attempt
      │
Lớp 2: RATE LIMIT
  • Giới hạn số tin nhắn mỗi giờ
  • Chống flood từ cùng một PSID
      │
Lớp 3: INTENT CLASSIFIER
  • Phân loại 9 ý định:
    chao_hoi, hoi_gio_dia_chi, hoi_menu_gia, hoi_khuyen_mai,
    dat_ban, khieu_nai_gop_y, yeu_cau_dac_biet,
    spam/injection/toxic, ngoai_pham_vi
      │
Lớp 4: POLICY ENGINE
  • Ma trận ý định → hành động:
    AUTO_SEND: chỉ chao_hoi, hoi_gio_dia_chi (confidence ≥0.9)
    QUEUE_REVIEW: hoi_menu_gia, hoi_khuyen_mai, dat_ban
    ESCALATE_OWNER: khieu_nai_gop_y, yeu_cau_dac_biet
    BLOCK: spam/injection/toxic
      │
Lớp 5: SUPERVISOR
  • Kiểm tra lần cuối trước khi gửi
  • Ghi log toàn bộ quyết định
```

**Nguyên tắc bất biến:** chỉ tin nhắn an toàn với độ tin cậy cao mới tự động gửi. Tất cả còn lại **chờ người duyệt** trước khi trả lời khách.

### 8.3. Đặt bàn (Table Reservation)

Khách nhắn tin đặt bàn qua Facebook → hệ thống xử lý với cơ chế chống lạm dụng:

**Cơ chế atomic booking:**

```
Khách gửi yêu cầu đặt bàn (ngày giờ, số người)
      │
      ▼
Kiểm tra chống lạm dụng:
  • Tối đa 1 booking đang hoạt động mỗi khách
  • Danh sách đen: 2 lần no-show → chặn đặt mới
      │
      ▼
BEGIN IMMEDIATE (SQLite)
  • Khoá ở tầng cơ sở dữ liệu
  • Chống TOCTOU: nhiều người đặt cùng lúc → đúng một người được
      │
      ▼
Idempotency: sha256(store_id:psid:booking_time:party_size)
  • Cùng một khách đặt cùng thời điểm → không tạo trùng
      │
      ▼
Ghép bàn (table combinability matrix)
  • Tự động ghép bàn nhỏ thành bàn lớn khi cần
      │
      ▼
Xác nhận booking → gửi tin nhắn cho khách
```

**Múi giờ:** tất cả thời gian dùng `Asia/Ho_Chi_Minh`, không tin múi giờ từ client.

### 8.4. Radar giá vùng (Catchment Price Radar)

Hệ thống khảo sát giá thị trường xung quanh quán để hỗ trợ quyết định giá bán:

**Luồng bất đồng bộ:**

```
Quản lý gửi yêu cầu khảo sát (bán kính, từ khoá)
      │
      ▼
POST /catchment-survey → trả về job_id (HTTP 202)
      │
      ▼
Hệ thống chạy ngầm:
  • SerpApi tìm kiếm quán cà phê trong vùng
  • Thu thập giá từ menu công khai
  • Giới hạn: 10 job/giờ mỗi IP+account
      │
      ▼
GET /catchment-survey/{job_id} → kiểm tra tiến độ
      │
      ▼
POST /catchment-survey/{job_id}/review → duyệt kết quả
```

**Phân loại lỗi:**

| Mã HTTP | Ý nghĩa |
|---|---|
| 400 | Yêu cầu không hợp lệ |
| 409 | Job đã tồn tại (idempotency) |
| 422 | Dữ liệu không hợp lệ |
| 429 | Vượt rate limit |
| 502 | SerpApi lỗi |
| 503 | Hệ thống quá tải |

### 8.5. Tin nhắn tự động với người duyệt

AG-FBPAGE không tự do gửi tin nhắn. Mọi tin nhắn đều đi qua quy trình kiểm duyệt:

**Luồng tin nhắn:**

```
Khách gửi tin nhắn / bình luận
      │
      ▼
Webhook nhận → phân loại (Messenger hay comment)
      │
      ▼
AG-FBPAGE phân tích ý định
      │
      ▼
5 lớp kiểm duyệt (xem mục 8.2)
      │
   ┌──┴──────────────────────────────────┐
   │                                     │
AUTO_SEND                          QUEUE_REVIEW
(chào hỏi, giờ/địa chỉ)            (menu, giá, đặt bàn, khuyến mãi)
   │                                     │
   ▼                                     ▼
Tự động gửi                      Chờ người duyệt
   │                                     │
   │                              ┌──────┴──────┐
   │                              │             │
   │                           Duyệt         Từ chối
   │                              │             │
   │                              ▼             ▼
   │                           Gửi tin      Không gửi
   │                              │
   └──────────────────────────────┴──────────────┘
                                  │
                                  ▼
                           Ghi log quyết định
```

**Giao thức HEAR cho khiếu nại:**

Khi khách khiếu nại (ý định `khieu_nai_gop_y`), hệ thống áp dụng giao thức HEAR:

1. **H**ỏi — Xin lỗi chân thành
2. **E**mpathize — Đồng cảm với trải nghiệm
3. **A**sk — Hỏi số điện thoại để liên hệ
4. **R**esolve — Cam kết xử lý và chuyển cho chủ quán

**Lưu ý:** AG-FBPAGE **không tự trả lời khiếu nại**. Luôn chuyển cho chủ quán sau khi thu thập thông tin.

---

## 9. Các màn hình chính trên ứng dụng web

| Màn hình | Dành cho | Chức năng |
|---|---|---|
| **Lưới lịch tuần** | Quản lý | Kéo thả xếp ca, ghim ô, chặn vi phạm kèm giải thích tại chỗ |
| **Hộp thư ràng buộc** | Quản lý | Duyệt/từ chối đầu ra của agent trước khi nạp vào bộ giải |
| **Bảng công bằng** | Quản lý + NV | Số dư 4 chiều (ca cuối tuần, ca đêm, tổng giờ, ca vụn), so với trung bình nhóm |
| **Phiếu vận hành** | Nhân viên | Chạy checklist mở quán/đóng quán/bàn giao trên điện thoại |
| **Cẩm nang quán** | Quản lý | Xem, bật/tắt, sửa câu luật; mỗi luật có nguồn gốc và kết quả tập sự |
| **Bản tin sáng** | Chủ quán | Tóm tắt 5 câu tình hình hôm nay |
| **Vết agent** | Quản lý | Đồ thị nhiệm vụ, kết quả từng cổng, nhà cung cấp mỗi lần gọi |
| **Hỏi đáp SOP** | Nhân viên | Chat hỏi quy trình, nhận câu trả lời kèm trích dẫn |
| **Tình trạng quán** | Chủ quán | Bảng tổng hợp: việc treo, hao hụt, cảnh báo hết hàng |
| **Chợ đổi ca** | Nhân viên | Đăng nhả ca, nhận ca, xem điều kiện ràng buộc |
| **Sổ tiêu thụ** | Quản lý | Lượng tiêu thụ theo ca, theo thứ, xu hướng |
| **Đăng ký / Đăng nhập** | Tất cả | Xác thực ba vai trò: chủ quán, quản lý, nhân viên |

---

## 10. Mười lăm việc Copilot KHÔNG BAO GIỜ tự quyết — luôn trình người

Dù Copilot điều hành toàn bộ hệ thống, có 15 quyết định **luôn** do con người bấm nút. Đây là nguyên tắc thiết kế cốt lõi: AI chạy, người duyệt.

1. Xếp ca (do CP-SAT)
2. Quyết định tự duyệt hay chặn một yêu cầu đổi ca
3. Tính sổ nợ công bằng
4. Quyết định escalate
5. Ghi vào cơ sở dữ liệu
6. Quyết định chuyển trạng thái phiên
7. Quyết định một bước phiếu là đã làm hay chưa
8. Quyết định một dấu hiệu tích khống có phải gian dối hay không
9. Quyết định mở chế độ bù ca khẩn
10. Quyết định một mặt hàng đã dưới ngưỡng tồn
11. **Quyết định một luật có hiệu lực hay không**
12. **Quyết định xoá một luật đã có**
13. **Tính lượng tiêu thụ từ số kiểm kê**
14. **Gửi đơn đặt hàng cho nhà cung cấp**
15. **Trả lời khách hàng thay quán**

---

## 11. Luồng dữ liệu tổng thể — Từ đầu vào đến đầu ra

```
┌─ ĐẦU VÀO ──────────────────────────────────────────────────────────┐
│                                                                     │
│  Ảnh TKB     Tin nhắn NV    Phiếu giao ca   Ghi chú hao hụt       │
│  Phản hồi khách   Ảnh chụp minh chứng   Số kiểm kê                │
│  Tin nhắn Facebook (Messenger + bình luận bài đăng)                │
│  Yêu cầu đặt bàn   Yêu cầu khảo sát giá                           │
│                                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─ TẦNG AGENT (đọc + trích xuất + đề xuất) ─────────────────────────┐
│                                                                     │
│  AG-TKB → ràng buộc giờ học                                        │
│  AG-MSG → 6 loại ý định + ràng buộc                                │
│  AG-HANDOVER → SBAR + việc treo                                    │
│  AG-WASTE → hao hụt có cấu trúc                                    │
│  AG-VOC → sự cố vận hành từ phản hồi khách                         │
│  AG-RULE → đề xuất luật từ lần sửa                                 │
│  AG-EXPLAIN → câu tiếng Việt từ mã lý do                           │
│  AG-BRIEF → bản tin sáng 5 câu                                     │
│  AG-SOP → câu trả lời quy trình kèm trích dẫn                      │
│  AG-FBPAGE → phân loại 9 ý định khách, soạn tin trả lời           │
│                                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─ TẦNG CỔNG KIỂM CHỨNG (tất định) ──────────────────────────────────┐
│                                                                     │
│  VF-SCHEMA → VF-TRACE → VF-CONF → VF-CONFLICT → VF-NUM            │
│  VF-RULE → VF-SCOPE → VF-STALE                                     │
│  + 5 lớp kiểm duyệt FB: Guardrail → Rate → Intent → Policy → Super│
│                                                                     │
│  Đạt → nạp vào hệ thống / tự gửi tin                               │
│  Không đạt → đẩy lên người                                         │
│                                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─ TẦNG LÕI (tất định, chứng minh được) ─────────────────────────────┐
│                                                                     │
│  CP-SAT xếp ca (6 cứng + 5 mềm + công bằng 4 trục)                │
│  Máy quy trình chạy phiếu (YAML → bước → minh chứng → việc treo)  │
│  Sổ tiêu thụ (kiểm kê đầu − kiểm kê cuối − hao hụt)               │
│  Cẩm nang sống (8 bước: ghi nhận → tìm mẫu → ... → theo dõi)     │
│  Chợ đổi ca (3 nhánh: tự duyệt / duyệt có điều kiện / chặn)       │
│  Bù ca khẩn (15' nhắc → 25' mở bù → 40' báo chủ)                  │
│  Đặt bàn (atomic booking + chống lạm dụng + ghép bàn)              │
│  Radar giá (async job + rate limit + idempotency)                  │
│                                                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─ ĐẦU RA ───────────────────────────────────────────────────────────┐
│                                                                     │
│  Lịch tuần cho 25+ người (không vi phạm ràng buộc cứng)           │
│  Phiếu vận hành đã chạy (mở quán / đóng quán / bàn giao)          │
│  Việc treo có người nhận và hạn                                    │
│  Sổ tiêu thụ theo ca và theo tuần                                  │
│  Cẩm nang quán (luật đọc được, bật tắt được)                       │
│  Bản tin sáng cho chủ                                              │
│  Báo cáo công bằng 4 chiều                                          │
│  Cảnh báo hết hàng, hao hụt bất thường                             │
│  Tin nhắn trả lời khách trên Facebook (tự động hoặc người duyệt)   │
│  Xác nhận đặt bàn                                                  │
│  Báo cáo khảo sát giá vùng                                         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 12. Tóm tắt các con số chính

| Hạng mục | Con số |
|---|---|
| Agent đang hoạt động | **11** (chia thành 6 nhóm nghiệp vụ, bao gồm AG-FBPAGE) |
| Sub-agent Facebook | **4** (FRONTDESK, BARISTA, CONCIERGE, SUPERVISOR) |
| Lớp kiểm duyệt tin nhắn FB | **5** (Guardrail → Rate → Intent → Policy → Supervisor) |
| Ý định khách hàng FB | **9** (chào hỏi, giờ/địa chỉ, menu/giá, khuyến mãi, đặt bàn, khiếu nại, yêu cầu đặc biệt, spam, ngoài phạm vi) |
| Cổng kiểm chứng tất định | **8** (VF-SCHEMA, TRACE, CONF, CONFLICT, NUM, RULE, SCOPE, STALE) |
| Ràng buộc cứng xếp ca | **6** (C01–C06) |
| Ràng buộc mềm xếp ca | **5** (S01–S05) |
| Chiều công bằng | **4** (ca cuối tuần, ca đêm, tổng giờ, ca vụn) |
| Bước vòng đời luật | **8** (ghi nhận → tìm mẫu → đề xuất → kiểm chứng → tập sự → duyệt → hiệu lực → theo dõi) |
| Quy trình vận hành (mẫu phiếu) | **3** (mở quán, đóng quán, bàn giao ca) |
| Kênh tương tác | **2** (chat nội bộ `/chat` + Facebook Fanpage) |
| Vai trò người dùng | **3** (chủ quán, quản lý, nhân viên) |
| Việc cấm AI làm | **15** |
| Màn hình chính trên web | **12+** |
| Luồng nghiệp vụ chính | **9** (xếp ca, đổi ca, phiếu, bàn giao, kiểm kê, bù ca, hao hụt, đặt bàn, radar giá) |

---

## 13. Thông điệp cốt lõi cho slide

> **NHỊP QUÁN là hệ thống doanh nghiệp do AI COPILOT điều hành.**
> **Copilot khai thác toàn bộ tiềm năng của 11 agent,**
> **phủ kín mọi khía cạnh vận hành — từ đọc ảnh, đọc tin nhắn,**
> **trực Fanpage, đặt bàn, khảo sát giá thị trường,**
> **đến dự báo nhu cầu và tự hoàn thiện quy trình.**
>
> **Nhưng con người luôn giữ quyền kiểm soát cuối cùng.**
> **Copilot chạy, người duyệt. Copilot đề xuất, người quyết định.**
> **Tin nhắn Facebook chỉ gửi khi an toàn — còn lại chờ người duyệt.**
>
> **Mỗi lần chị quản lý sửa lịch, Copilot học một điều.**
> **Sau tám tuần, quán có một cẩm nang vận hành mà không ai phải ngồi viết.**
> **Đó là tài sản của quán, không phải của người sắp nghỉ.**
