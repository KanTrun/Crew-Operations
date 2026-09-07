# HƯỚNG DẪN DEMO THI — NHỊP QUÁN

> Tài liệu này cho **chính bạn** — chủ quán đi thi. Đọc 10 phút, demo được 10 phút.
> Mọi dữ liệu dưới đây đã được kiểm chứng chạy thật trên máy ngày 07/09.

---

## 0. TRẢ LỜI NHANH CÁC CÂU HỎI CỦA BẠN

| Câu hỏi của bạn | Trả lời ngắn |
|---|---|
| Lịch tuần tương tác thế nào, ai có quyền? | **Chỉ quản lý (lan) và chủ quán (hung)** được xem/xếp/sửa. Nhân viên chỉ xem "Lịch của tôi" ở trang **/toi**. Bấm ô ngày → panel chi tiết → nút "＋ Thêm người" hoặc "×" gỡ người → nút "Xếp lịch tự động" chạy AI xếp ca (CP-SAT). Khi có người khác pin, sửa hoặc đổi trạng thái, màn hình tự cập nhật qua realtime |
| Lịch đã đóng thì điều chỉnh ở đâu? | Trong **/roster**, chủ quán bấm **"Mở lại để điều chỉnh"**, nhập lý do bắt buộc rồi mới sửa lịch. Việc mở lại được giới hạn cho chủ quán và ghi audit; xong việc có thể xếp, duyệt, công bố và đóng lại theo chu trình |
| Up ảnh ở trang nào? | Trang **/tkb** (Tải ảnh lịch bận) — nhân viên chụp ảnh thời khóa biểu → AI đọc khung giờ → xác nhận → lần xếp lịch sau sẽ tránh giờ học |
| Phiếu làm cái gì? | **Đây là "checklist ca"** — giống danh mục mở quán dán tường: vào ca (đã điểm danh) → mở phiếu "Mở quán" → đi 20 bước (nhiệt độ tủ, chụp ảnh quầy, kiểm kê sữa...) → bước nào kẹt thì bấm "Để lại việc khó" (treo) → quản lý nhận việc đó. **Không có phiếu nào "tự sinh"** — phiếu cũ được lưu, reload không mất |
| AI Agent ở đâu, làm sao thấy? | Bấm nút **"Hỏi trợ lý vận hành"** trên mọi trang (hoặc Ctrl+K) — hoặc trang **/copilot**. Mỗi câu trả lời có nhãn "🤖 AI · live/replay". AI chỉ **đề xuất** — bạn bấm "Duyệt" nó mới ghi |
| Công bằng là gì? | Sổ nợ 4 trục (ca cuối tuần, ca đêm, giờ, ca vụn) của **chính bạn** so trung bình. Bộ xếp ca đọc số này để người gánh nhiều được bù trước |
| Tiêu thụ là gì? | **Sổ kiểm kê nguyên liệu**: đếm hàng đầu ca + cuối ca (vd sữa còn 8 hộp), hệ thống tự suy ra tiêu thụ. Dưới ngưỡng 2 → cảnh báo hiện trên Hôm nay |
| Cẩm nang là gì? | **Bộ luật quán tự học**: mỗi lần quản lý sửa lịch cùng kiểu ≥3 lần → AI đề xuất 1 câu luật → tập sự → chủ quán chốt → luật áp vào lần xếp sau |
| SOP là gì? | **Trợ lý hỏi-đáp**: nhân viên gõ "nhiệt độ tủ lạnh bao nhiêu?" → AI trả lời **kèm trích dẫn** đúng bước phiếu nào, luật nào — không bịa |
| Họp ca kiểm tra AI tổng hợp? | ✅ **ĐÃ KIỂM CHỨNG LIVE**: transcript 4 việc (máy rỉ nước, khách quên áo, sữa sắp hết, đón đoàn 25 người) → AI sinh biên bản có tiêu đề, tóm tắt, action items đúng đủ |
| Chat chung liên kết gì? | Chat nội bộ có "@agent_lich" để xin việc + nút "Treo thành việc" — tin nhắn thành việc có người chịu trách nhiệm |
| QR làm gì? | Quản lý phát mã 1 lần dùng → nhân viên dán mã = điểm danh. **Điểm danh xong mới mở được phiếu** (đã có link dẫn sang Phiếu) |
| Test key LLM có hoạt động? | ✅ **Groq hoạt động** (trả lời "Chủ"), ✅ **OpenRouter hoạt động** ("lễ tân"), ⚠️ Gemini key hợp lệ nhưng model cần cấu hình lại. **CA_AGENT_MODE đang =replay trên .env** → đổi thành `live` là AI thật 100% |
| AI có hiểu lịch vừa generate? | ✅ Hỏi "ca của tôi tuần này" → AI liệt kê đúng 5 ca từ lịch solver; "bản tin sáng" → "49 lượt trong 21 ca" |

---

## 1. AI ĐÃ ĐƯỢC KIỂM CHỨNG LIVE (07/09) — nói được trước giám khảo

| Tính năng | Kết quả test | Chi tiết |
|---|---|---|
| Router LLM Groq→Gemini→OpenRouter | ✅ | Groq trả "Chủ" — đúng tiếng Việt |
| AG-MSG đọc tin nhắn tự do | ✅ | "tôi bận thứ 5 vì thi" → `xin_nghi`, độ tin cậy 0.95 |
| AG-TKB đọc ảnh thời khóa biểu | ✅ | 3 khung giờ đúng T2/T4 sáng + T6 chiều, conf 0.82 |
| AG-Meeting tổng hợp họp | ✅ | 4 việc → biên bản + action items, bắt được cả "nhờ Lan sắp xếp" |
| Copilot đọc lịch thật | ✅ | "Ca của tôi?" → 5 ca đúng; "Bản tin sáng" → 49 lượt/21 ca |
| 2 pha duyệt | ✅ | AI đề xuất → người bấm Duyệt → mới ghi (audit đầy đủ) |

**Cách nói với giám khảo:** "Toàn bộ AI chạy qua router miễn phí fail-closed: hết hạn mức nhà này tự chuyển nhà kia, chết sạch thì đẩy lên người — không bao giờ bịa số."

---

## 2. LUỒNG DEMO 10 PHÚT (kịch bản đã chạy được)

### Chuẩn bị trước khi lên (5 phút)
```bash
# Trên EC2: bật AI live (hiện đang replay)
# Sửa .env: CA_AGENT_MODE=live  rồi: make docker-up
```

### Phút 0-2: Nhân viên (minh) — vòng ca
1. **/qr**: quản lý lan phát mã → minh dán → "Đã điểm danh" → bấm link **"Mở phiếu ca →"**
2. **/phieu**: "Tôi đã có mặt" → chọn "Mở quán · 20 bước" → làm 2-3 bước (nhiệt độ tủ 4.5, chụp ảnh quầy có preview) → bấm "Để lại việc khó": "Hết ống hút cỡ lớn" → thấy xác nhận + link sang Việc treo
3. **/tkb**: chụp ảnh TKB → AI live đọc giờ → bấm "Xác nhận"

### Phút 2-4: Quản lý (lan) — AI xếp lịch
4. **/roster**: thấy "Chưa xếp" → bấm **"Xếp lịch tự động"** → solver chạy (~1-2s) → 21 ca có người
5. Bấm ô Thứ 2 → panel chi tiết: "Đủ 2/2 người" → gỡ 1 người ("Thiếu 1 (cần 2)") → thêm lại → "Đủ 2/2"
6. Nút "Gửi duyệt" → "Duyệt lịch" → "Công bố cho nhân viên"

### Phút 4-6: Hỏi AI (lan giữ màn hình)
7. **Copilot (Ctrl+K)**: gõ "Bản tin sáng hôm nay" → AI trả "49 lượt trong 21 ca, 3 việc treo"
8. Gõ "Tôi bận thứ 6, có việc gia đình" → thẻ đề xuất xin nghỉ → bấm Duyệt → **/inbox** thấy "bận T6, y_dinh: xin_nghi" chờ duyệt
9. Lan bấm **Duyệt** trong Hộp thư → giải thích: "lần xếp lịch sau solver sẽ tránh"

### Phút 6-8: Họp ca — AI tổng hợp
10. **/cuoc-hop**: dán transcript (dùng sẵn transcript máy pha/áo khoác/sữa/đoàn 25 người) → bấm phân tích → **biên bản + action items hiện ra** → bấm "Lưu" (Apply) → việc xuất hiện trong **/treo**

### Phút 8-10: Cẩm nang — AI học quán
11. **/cam-nang**: giải thích vòng 8 bước (đủ 3 lần sửa → đề xuất → tập sự → chủ chốt)
12. **/sop**: minh gõ "nhiệt độ tủ lạnh bao nhiêu là được?" → trả lời **kèm trích dẫn** bước phiếu
13. Kết: quay về **/hom-nay** — hàng đợi "Việc của bạn" + bản tin sáng + 3 việc treo đều có link

---

## 3. AI ĐANG Ở CHẾ ĐỘ NÀO? (quan trọng)

```
.env hiện tại:  CA_AGENT_MODE=replay   ← AI trả lời từ mẫu (nhanh, ổn định, 0 phí)
Để thi:        CA_AGENT_MODE=live     ← AI thật qua Groq/OpenRouter (key đã test ✅)
```

**Sự thật đã kiểm chứng:** cả Groq lẫn OpenRouter đều trả lời thật. Replay chỉ là "hàng mẫu" cho CI — lên thi thì bật live. Nếu lo mạng hội trường: quay trước 1 lần làm video dự phòng.

---

## 4. SƠ ĐỒ TƯ DUYY 3 VÒNG (trả lời "trang nào nối trang nào")

```
VÒNG 1 — CA LÀM VIỆC (mỗi ngày)
  /hom-nay ──xem tổng──► /qr ──điểm danh──► /phieu ──kẹt?──► /treo
                ▲                                  │
                └───── viêc treo ca sau ◄─/handover┘
  /tkb (ảnh giờ học) ──► /roster (solver tránh giờ) ──► /toi (xem ca mình)
  /doi-ca ◄──3 nhánh──► /inbox (AI tách tin → QL duyệt) ──► /cong-bang (sổ nợ)

VÒNG 2 — HỌC (quán nhớ)
  /cuoc-hop (AI bóc họp) ──► /treo (action items)
  3 lần sửa lịch cùng kiểu ──► /cam-nang (luật đề xuất) ──chủ chốt──► /sop (NV hỏi, AI trích dẫn)

VÒNG 3 — QUẦY & KHÁCH (phụ)
  /quay ──► /pha ──► /tieu-thu (kiểm kê) ──► /hom-nay (cảnh báo tồn)
  /chat (nội bộ, treo tin thành việc) · /page-quan (FB khi nối Meta)
```

---

## 5. 3 ĐIỂM CHẮN CHẸO NÊU GIÁM KHẢO HỎI

1. **"AI tự ghi dữ liệu được không?"** → Không. Mọi hành động ghi đều qua 2 pha: AI đề xuất → người bấm Duyệt. Có audit log từng bước (`/vet`).
2. **"AI bịa số thì sao?"** → Sáu cổng kiểm chứng tất định (VF-*) chặn trước khi tới người; AI không được ghi; fail-closed: không chắc thì đẩy người, không đoán.
3. **"Sao không dùng luôn LLM xếp ca?"** → Xếp ca là CP-SAT (toán), LLM chỉ hiểu tiếng nói + diễn giải. Cùng input luôn ra cùng output — replay được, kiểm thử được.

## 6. RỦI RO CÒN MỞ (nói thật)
- .env trên EC2 đang `replay` — phải đổi `live` trước giờ thi
- Gemini key OK nhưng model cũ 404 — router tự bỏ qua, không sao
- 3 tài khoản "verify*" còn trong DB prod (lệnh xóa đã có trong lịch sử chat)
