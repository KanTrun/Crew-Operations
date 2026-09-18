# HỎI – ĐÁP BUỔI THI DEMO — NHỊP QUÁN

> Tài liệu này dành cho **chính bạn** — chủ quán đi thi. Gồm các câu hỏi thầy cô
> hay hỏi nhất, kèm **câu trả lời sẵn** (nói ngắn gọn, tự tin, có số liệu).
> Đọc kỹ phần "3 điểm chốt" trước khi lên.

---

## 0. 3 CÂU CHỐT NẾU CHỈ NHỚ ĐƯỢC 3 ĐIỀU

1. **"AI có tự ghi dữ liệu không?"** → Không. Mọi thay đổi đều qua **2 pha**:
   AI chỉ *đề xuất* → người bấm **Duyệt** mới ghi. Có audit log từng bước (`/vet`).
2. **"AI bịa số thì sao?"** → Có **6 cổng kiểm chứng tất định (VF-\*)** chặn trước
   khi tới người; AI không được ghi; **fail-closed** — không chắc thì đẩy lên người,
   không đoán.
3. **"Sao không dùng luôn LLM để xếp ca?"** → Xếp ca là **CP-SAT (toán học)** —
   cùng input luôn ra cùng output, replay được, kiểm thử được. LLM chỉ dùng để
   *hiểu tiếng nói* và *diễn giải*, không quyết định lịch.

---

## 1. NHÓM CÂU HỎI VỀ SẢN PHẨM / Ý TƯỞNG

### Q1. "Dự án này làm gì? Một câu thôi."
**A:** NHỊP QUÁN là **hệ điều hành vận hành quán cà phê bằng AI agent** — từ xếp lịch
tự động, điểm danh, phiếu checklist ca, đến cẩm nang quán tự học, tất cả chạy trên
một web PWA + kênh tin (Telegram/Zalo/Facebook).

### Q2. "Vì sao lại chọn bài toán quán cà phê?"
**A:** Vì nó **nhỏ nhưng đủ phức tạp** để chứng minh đủ kỹ thuật: xếp lịch là bài toán
tối ưu (CP-SAT), hiểu tin nhắn là LLM, quy trình ca là state machine, lỗi lặp lại là
học máy. Đồng thời có **người dùng thật** (nhân viên, quản lý, chủ quán) nên dễ demo
và dễ đo giá trị.

### Q3. "Điểm khác biệt so với app quản lý quán có sẵn (POS, phần mềm chấm công)?"
**A:** Ba điểm:
- **Lõi tất định + AI đề xuất**: không phải app "AI tự làm hết" mà là AI *trợ lý*,
  người luôn giữ quyền duyệt cuối.
- **Cẩm nang tự học**: hệ thống tự sinh luật từ lỗi lặp lại ≥3 lần, không ai phải nhập tay.
- **Đa kênh**: nhân viên không cần mở app — gửi tin Telegram/Zalo là hệ thống hiểu.

### Q4. "Ai là người dùng chính?"
**A:** 3 vai: **nhân viên** (điểm danh, làm phiếu, xem ca của mình), **quản lý** (duyệt,
xếp lịch, xử lý việc treo), **chủ quán** (chốt luật, nâng/hạ vai, xem báo cáo).

---

## 2. NHÓM CÂU H�ỎI VỀ KỸ THUẬT / KIẾN TRÚC

### Q5. "Kiến trúc tổng thể thế nào?"
**A:** Monorepo gồm: **API FastAPI** (`apps/api`), **web Next.js 15 PWA** (`apps/web`),
và các **package Python** tách rõ trách nhiệm: `solver` (CP-SAT), `gates` (cổng kiểm
chứng), `opsengine` (phiếu/việc treo), `playbook` (cẩm nang), `agents` (10+ agent LLM),
`contracts` (schema dùng chung). Dữ liệu lưu SQLite/Postgres, có worker nền.

### Q6. "Vì sao tách lõi không dùng LLM?"
**A:** Vì **xếp lịch phải tất định** — cùng dữ liệu vào phải ra cùng kết quả để kiểm thử
và tái lập. LLM không đảm bảo điều đó. Nên: **toán (CP-SAT) quyết định lịch, LLM chỉ
hiểu ngôn ngữ và giải thích.**

### Q7. "Solver xếp lịch hoạt động thế nào?"
**A:** Dùng **Google OR-Tools CP-SAT**. Nạp ràng buộc cứng C01–C06 (đủ người, đúng kỹ
năng, không trùng giờ học, trần giờ, khoảng nghỉ…) + ràng buộc mềm + **công bằng 4 trục**
(ca cuối tuần, ca đêm, giờ, ca vụn). Kết quả: 21 ca có người trong ~1–2 giây, không ai
bị xếp đè giờ học.

### Q8. "6 cổng kiểm chứng VF-\* là gì?"
**A:** Là các cổng **tất định** chặn trước khi kết quả AI tới người:
- **VF-SCHEMA**: đúng định dạng dữ liệu
- **VF-TRACE**: có nguồn gốc, truy vết được
- **VF-CONF**: độ tin cậy đủ cao
- **VF-RULE**: không vi phạm luật quán
- **VF-SCOPE**: nằm trong phạm vi cho phép
- **VF-STALE**: dữ liệu không quá cũ
- (thêm **VF-NUM** cho số liệu)
Cổng nào không qua → từ chối, không bịa.

### Q9. "Fail-closed nghĩa là gì?"
**A:** Khi LLM lỗi, hết hạn mức, hoặc không chắc chắn → hệ thống **từ chối trả lời /
đẩy lên người** thay vì đoán bừa. Router LLM cũng fail-closed: hết nhà này tự chuyển
nhà kia, chết sạch thì không bịa.

### Q10. "Cẩm nang 8 bước hoạt động thế nào?"
**A:** Khi quản lý sửa lịch cùng kiểu **≥3 lần** → hệ thống tự đề xuất 1 câu luật →
qua 8 bước: *tìm mẫu → đề xuất → kiểm chứng → tập sự → chốt → hiệu lực → áp dụng →
gỡ*. Chủ quán chốt thì luật mới có hiệu lực và được bơm lại vào solver.

### Q11. "Các agent LLM gồm những gì?"
**A:** 10+ agent, ví dụ: **AG-MSG** (phân loại ý định tin nhắn), **AG-TKB** (đọc ảnh thời
khóa biểu), **AG-Meeting** (tổng hợp họp ca), **AG-COPILOT** (trợ lý vận hành), **AG-RULE**
(sinh luật), **AG-SOP** (hỏi-đáp kèm trích dẫn). Tất cả chạy qua **router LLM** Groq→
Gemini→OpenRouter.

### Q12. "Làm sao đảm bảo AI không bịa khi trả lời SOP?"
**A:** Mọi câu trả lời SOP đều **kèm trích dẫn** — chỉ rõ đúng bước phiếu nào, luật nào.
Không có nguồn thì không trả lời (fail-closed).

---

## 3. NHÓM CÂU HỎI VỀ DEMO / TÍNH NĂNG

### Q13. "Demo nhanh nhất cho tôi xem tính năng nổi bật?"
**A:** (Chạy kịch bản A) Đăng nhập `lan` → **Lịch tuần** → "Xếp lịch tự động" → solver
chạy ~1–2s → 21 ca có người, không trùng giờ học. Đây là việc trước đây quản lý mất
**2–4 giờ trên Excel**.

### Q14. "Điểm danh QR hoạt động thế nào?"
**A:** Quản lý phát mã **1 lần dùng** → nhân viên dán mã = điểm danh. Dùng lại mã →
báo "đã dùng". **Điểm danh xong mới mở được phiếu ca.**

### Q15. "Phiếu ca (checklist) làm gì?"
**A:** Là "danh mục mở quán" dán tường dạng số: vào ca → mở phiếu "Mở quán" → đi 20 bước
(nhiệt độ tủ, chụp ảnh quầy, kiểm kê sữa…). Bước nào kẹt → bấm "Để lại việc khó" (treo)
→ quản lý nhận việc. **Không có phiếu nào tự sinh** — phiếu cũ được lưu, reload không mất.

### Q16. "Việc treo là gì?"
**A:** Là việc chưa xong trong ca, được **treo lại** để ca sau / quản lý xử lý. Có link
sang `/handover` (bàn giao) và `/treo`. Họp ca AI tổng hợp cũng sinh action items thành
việc treo.

### Q17. "Sổ công bằng là gì?"
**A:** Sổ nợ **4 trục** (ca cuối tuần, ca đêm, giờ, ca vụn) của từng người so với trung
bình. Solver đọc số này để **người gánh nhiều được bù trước**. Đây là lý do số 1 nhân
viên nghỉ việc — hệ thống đo được.

### Q18. "Họp ca AI tổng hợp thế nào?"
**A:** Dán transcript → AI sinh **biên bản có tiêu đề, tóm tắt, action items** → bấm
"Lưu" → việc xuất hiện trong `/treo`. Đã kiểm chứng live với 4 việc (máy rỉ nước, khách
quên áo, sữa sắp hết, đón đoàn 25 người).

### Q19. "Chat nội bộ liên kết gì?"
**A:** Có `@agent_lich` để xin việc + nút "Treo thành việc" — tin nhắn thành việc có
người chịu trách nhiệm.

### Q20. "AI có hiểu lịch vừa generate không?"
**A:** Có. Hỏi "ca của tôi tuần này" → AI liệt kê đúng 5 ca từ solver; "bản tin sáng" →
"49 lượt trong 21 ca". Đã kiểm chứng live.

---

## 4. NHÓM CÂU HỎI VỀ AN TOÀN / ĐẠO ĐỨC / RỦI RO

### Q21. "Nếu AI trả lời sai thì ai chịu trách nhiệm?"
**A:** Người duyệt. Vì AI **không tự ghi** — mọi hành động dừng ở "Đề xuất chờ duyệt".
Có audit log từng bước (`/vet`) để truy vết ai duyệt gì lúc nào.

### Q22. "Dữ liệu nhân viên có an toàn không?"
**A:** Có lớp **bảo vệ dữ liệu** trong `ai_learning` (rollout luật AI có kiểm soát),
phân quyền rõ 3 vai, và mọi thay đổi đều có vết. Không có key LLM trong code — nằm
trong `.env`.

### Q23. "Rủi ro còn mở là gì?" (nói thật — tạo thiện cảm)
**A:** Trung thực: (1) `.env` trên EC2 đang ở chế độ `replay` — phải đổi `live` trước
giờ thi; (2) Gemini key hợp lệ nhưng model cũ 404 — router tự bỏ qua, không sao;
(3) vài tài khoản test còn trong DB prod — lệnh xóa đã có.

### Q24. "Vì sao không cho AI tự xếp luôn, phải qua duyệt?"
**A:** Vì lịch ảnh hưởng trực tiếp đời sống nhân viên. **Người phải giữ quyền quyết định
cuối**; AI chỉ là trợ lý đề xuất. Đây cũng là điểm khác biệt đạo đức so với app "AI tự
làm hết".

---

## 5. NHÓM CÂU HỎI VỀ KIỂM THỬ / CHẤT LƯỢNG

### Q25. "Làm sao chứng minh hệ thống chạy đúng?"
**A:** Có **bộ kiểm thử tất định** (fixtures/golden), **pytest** cho backend, **Playwright
e2e** cho web, và **cổng VF-\*** chặn kết quả AI. Chế độ `replay` cho phép tái lập kết
quả 100% trong CI.

### Q26. "Chế độ replay vs live là gì?"
**A:** `replay` = AI trả lời từ bộ mẫu tất định (nhanh, 0 đồng, dùng cho CI/demo ổn định).
`live` = AI thật qua Groq/OpenRouter. Cả hai đã kiểm chứng hoạt động.

### Q27. "Đo lường hiệu quả thế nào?"
**A:** Có script `do_metrics.py` và báo cáo `docs/ket-qua-tong-hop.md` (§18.2) — đo số
lượt phân công, độ công bằng, thời gian xử lý việc treo, v.v.

---

## 6. NHÓM CÂU HỎI "HÓC BÚA" (chuẩn bị tinh thần)

### Q28. "Nếu hết tiền API LLM giữa demo thì sao?"
**A:** Router fail-closed tự chuyển nhà khác; chết sạch thì đẩy lên người, không bịa.
Ngoài ra có thể bật `replay` để demo vẫn chạy ổn định.

### Q29. "Nếu mạng hội trường chậm thì sao?"
**A:** Đã chuẩn bị **video demo quay sẵn** làm dự phòng, và chế độ `replay` không cần
mạng LLM.

### Q30. "Dự án này có thật sự dùng được ngoài đời không?"
**A:** Có — đã chạy thật trên máy, có dữ liệu seed 19 nhân viên, 21 ca, lịch sử 8 tuần.
Kiến trúc tách lõi tất định + AI đề xuất giúp dễ vận hành thật và dễ mở rộng.

### Q31. "Vì sao tên repo là Crew-Operations mà sản phẩm là NHỊP QUÁN?"
**A:** GitHub dùng tên tiếng Anh **Crew-Operations**; phần mềm và UI vẫn là **NHỊP QUÁN**.
Tên thư mục clone không bắt buộc trùng tên repo.

### Q32. "Điểm yếu lớn nhất của dự án?"
**A:** Trung thực: phụ thuộc vào key LLM bên thứ ba (đã giảm bằng router fail-closed),
và chưa nối thật Facebook Page (chỉ có hướng dẫn). Đây là hướng phát triển tiếp theo.

---

## 7. MẸO TRÌNH BÀY

- **Nói ngắn, có số**: "2–4 giờ trên Excel" → "1–2 giây". Số cụ thể tạo ấn tượng.
- **Luôn quy về 3 chốt** ở mục 0 khi bị hỏi về AI.
- **Nói thật về rủi ro** (Q23, Q32) — giám khảo đánh giá cao sự trung thực hơn là
  che giấu.
- **Demo theo kịch bản A–F** trong `docs/runbook-demo.md` — mỗi kịch bản < 3 phút.
- Trước giờ thi: đổi `.env` `CA_AGENT_MODE=live`, chạy `make docker-up`, kiểm tra
  `make docker-smoke`.