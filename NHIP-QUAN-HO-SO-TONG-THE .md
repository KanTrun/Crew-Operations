# NHỊP QUÁN

**Hệ sinh thái AI agent vận hành quán cà phê, lấy ca làm việc làm hạt nhân và cẩm nang tự viết làm bộ nhớ**

Hồ sơ dự án · **Phiên bản 3.0** · Tài liệu duy nhất, thay cho toàn bộ bản trước
Đội 4 người · 6 tuần xây dựng + 2 tuần hoàn thiện · **Ngân sách 0 đồng**
Cuộc thi "Xây dựng Hệ điều hành Doanh nghiệp số AI" · Khoa CNTT HUTECH · 2026

---

## Cách đọc

| Phần | Mục | Đọc khi nào |
|---|---|---|
| **I — Đề tài** | 1 đến 10 | Viết hồ sơ, chuẩn bị thuyết trình, luyện phản biện |
| **II — Thực thi** | 11 đến 18 | Bắt tay vào code |

**Nguyên tắc của tài liệu này:** mọi con số về kết quả đều là **mục tiêu phải đi đo**, không phải kết quả đã có. Không có câu chuyện nào được bịa ra. Chỗ nào chưa kiểm chứng được thì ghi rõ là chưa kiểm chứng.

**Bốn quy tắc bất biến của dự án:**

1. **Hợp đồng dữ liệu trước, mã nguồn sau.** Chốt trong 2 ngày đầu, sau đó không ai bị chặn bởi ai.
2. **`main` luôn xanh và luôn demo được.** Bất kỳ lúc nào, `git checkout main && make demo` phải chạy ra sản phẩm.
3. **Không mã nguồn nào vào `main` mà không qua pull request được duyệt.** Kể cả của trưởng nhóm.
4. **Không mô hình ngôn ngữ nào ghi vào lịch, và không mô hình ngôn ngữ nào điều phối.** Danh sách 15 việc cấm agent hoá ở mục 7.2.

---
---

# PHẦN I — ĐỀ TÀI

# 1. Tóm tắt điều hành

## 1.1. Một câu

Một quán cà phê có 15 đến 40 nhân viên bán thời gian đang được vận hành bằng Excel, ba cuốn sổ giấy và sáu nhóm Zalo. NHỊP QUÁN thay toàn bộ thứ đó bằng một hệ điều hành lấy **ca làm việc** làm hạt nhân, có **hệ sinh thái agent chuyên trách** đọc dữ liệu thô mà quán vốn đã tạo ra, một **bộ điều phối tất định** giữ cho mọi thứ không sai, và một **cẩm nang vận hành tự viết ra từ chính những lần con người sửa hệ thống**.

## 1.2. Bảng thông tin nhanh

| Hạng mục | Nội dung |
|---|---|
| Doanh nghiệp | Quán cà phê hoặc trà sữa, 1 điểm bán, 15 đến 40 nhân viên bán thời gian phần lớn là sinh viên |
| Hạt nhân | Ca làm việc: xếp ca bằng bộ giải tối ưu, sổ nợ công bằng, chợ đổi ca, điểm danh |
| Tầng vận hành | Máy quy trình với **mẫu phiếu là dữ liệu**: mở quán, đóng quán, bàn giao ca, kiểm kê, hao hụt |
| Bộ nhớ | **Cẩm nang sống**: luật vận hành tự viết ra từ các lần con người sửa hệ thống |
| Kiến trúc mục tiêu | **13 agent, 5 nhóm nghiệp vụ** |
| **Lô 1, ship trong 6 tuần** | **9 agent** |
| Lô 2, đã thiết kế và tính chi phí, chưa xây | 4 agent |
| Đã loại kèm lý do kỹ thuật | 4 đề xuất, mục 6.3 |
| Điều phối | **Máy trạng thái tất định, không phải mô hình ngôn ngữ** |
| Kiểm chứng | **6 cổng tất định**, thất bại đóng, mọi bất định đẩy lên người |
| Lõi quyết định | CP-SAT, rule engine, máy quy trình. **Không mô hình ngôn ngữ nào ghi vào lịch** |
| Chi phí | **0 đồng.** Sổ chi phí 14 dòng ở mục 10 |
| Đội | 4 người, **25,5 ngày mỗi người**, 4 vùng nhánh GitHub, CODEOWNERS |
| Khối lượng | 104,0 ngày người trên sức chứa 108, đệm 4,0 ngày |
| Kiểm thử | Mục tiêu **từ 215 bài** tự động, 11 cổng CI |

## 1.3. Câu mở đầu bài thuyết trình

> Ở một quán cà phê, người biết cách vận hành quán là chị quản lý. Không phải hệ thống nào cả, mà là chị. Chị biết thứ Bảy phải xếp thêm một người pha chế, biết máy pha phải xả nước hai lần vào buổi sáng lạnh, biết nhà cung cấp sữa hay giao trễ thứ Hai. Toàn bộ tri thức đó nằm trong đầu chị, và **ngày chị nghỉ việc, quán mất sạch**.
>
> Chúng em không xây một phần mềm để chị nhập dữ liệu vào. Chúng em xây một hệ thống mà **mỗi lần chị sửa nó, nó học được một điều và ghi lại thành một câu ai cũng đọc được**. Sau tám tuần, quán có một cẩm nang vận hành mà không ai phải ngồi viết. Đó là tài sản của quán, không phải của người sắp nghỉ.

---

# 2. Nghiên cứu hệ sinh thái agent cho ngành F&B, và khoảng trống

## 2.1. Ngành đang đi đúng hướng này

**Hệ điều hành nhà hàng dạng agent đã là một hạng mục sản phẩm thương mại.** [Nory tự định vị là hệ điều hành nhà hàng dùng AI dạng agent](https://www.nory.ai/blog/migrate-to-agentic-ai-restaurant-operating-system), một nền tảng tự động hoá và kiểm soát chi phí chính gồm nhân công và giá vốn, trên nhiều điểm bán.

**Agent đang được dùng cho đúng những việc trong đề tài này.** [Một phân tích ngành](https://digiqt.com/blog/ai-agents-in-restaurant-tech/) mô tả agent nhà hàng kết hợp mô hình ngôn ngữ, logic lập kế hoạch và tích hợp công cụ để làm trọn việc: trả lời khách, nhận và sửa đơn, báo thời gian chờ, chuyển phiếu vào bếp, đối soát tồn kho, **xếp ca nhân viên, và đẩy ngoại lệ lên cho con người khi cần**.

**Giá trị được đo bằng giờ trả lại cho người quản lý.** [Một bài tổng hợp về agent trong ngành nhà hàng 2026](https://growwstacks.com/blog/ai-agents-restaurant-industry-2026/) mô tả chủ nhà hàng đang chìm trong bảng tính và bảng điều khiển, và các agent đang trả lại **10 đến 15 giờ mỗi tuần**.

**Ngành gọi tên đúng bước chuyển này.** [Một phân tích khác](https://mobidev.biz/blog/ai-agents-for-restaurants) diễn đạt rằng agent đưa sản phẩm từ **hệ thống ghi chép** sang **hệ thống cho ra kết quả**. Đây là câu định vị chính xác nhất cho NHỊP QUÁN. [Salesforce cũng viết](https://www.salesforce.com/retail/artificial-intelligence/ai-agents-in-restaurants/) về việc agent hoạt động tự chủ khi điều phối ca làm việc.

*Nội dung từ các nguồn trên đã được diễn giải lại để tuân thủ quy định bản quyền.*

## 2.2. Khoảng trống, và đây là chỗ đề tài đứng

| Sản phẩm thương mại hiện có | NHỊP QUÁN |
|---|---|
| Nhắm **chuỗi nhiều điểm bán** ở phương Tây | Nhắm **một quán nhỏ** ở Việt Nam |
| Cần **tích hợp hệ thống bán hàng** làm nguồn dữ liệu | Đọc **đúng những gì quán vốn đã tạo ra**: ảnh thời khoá biểu, tin nhắn Zalo, sổ giấy, bảng tính, **và số kiểm kê giữa hai ca** |
| Trọng tâm là chi phí nhân công và giá vốn, tức bài toán tiền | Trọng tâm là **điều phối, tuân thủ, công bằng và tri thức vận hành**. Không có module tài chính nào |
| Nhân viên toàn thời gian, lịch ổn định | Nhân viên là **sinh viên, mỗi người một thời khoá biểu, đổi mỗi học kỳ** |
| Tri thức vận hành nằm trong cấu hình do nhà cung cấp thiết lập | **Tri thức vận hành tự sinh ra từ chính quán**, và quán sở hữu nó |
| Trả phí theo điểm bán mỗi tháng | **0 đồng** |

**Câu nói khi phản biện:** ngành đang xây hệ điều hành nhà hàng dạng agent cho chuỗi lớn có sẵn hệ thống bán hàng và có ngân sách. Không ai xây cho một quán 25 nhân viên sinh viên chạy trên Zalo và Excel, và đó là hình dạng của phần lớn quán ở Việt Nam.

---

# 3. Bài toán: một ngày ở quán

## 3.1. Bảy điểm đau, theo thứ tự thời gian

| Giờ | Việc | Điểm đau thật |
|---|---|---|
| 6h30 | Mở quán | Danh sách 20 đến 40 mục dán tường. Nhân viên tích một loạt vào cuối ca trong hai mươi giây. Quản lý biết là tích khống nhưng không có cách nào khác |
| 7h00 | Kiểm kê nhanh | Đếm vài mặt hàng, ghi sổ. **Số đó không đi đâu cả.** Không ai biết còn bao nhiêu sữa cho tới lúc hết sữa giữa giờ cao điểm |
| 10h00 | Hàng về | Phiếu giao hàng viết tay nhét vào ngăn kéo. Không ai đối chiếu, không ai biết hạn dùng của lô nào |
| 14h00 | Giao ca | Hai ca gặp nhau 5 phút. Máy pha có tiếng lạ, một khách đã đặt bánh chiều tới lấy, ca sáng đã hứa đổi món cho khách. **Ba việc đó rơi mất** |
| 14h05 | Một người không tới | Quản lý gọi điện lần lượt từng người trong danh bạ |
| 22h00 | Đóng quán | Tắt gas, tắt điện, khoá cửa. Tích khống lần nữa. **Hàng huỷ trong ngày không ai ghi** |
| Tối thứ Năm | Xếp ca tuần sau | 2,5 đến 4 giờ trên Excel với 25 thời khoá biểu và 60 tin nhắn Zalo |

## 3.2. Bốn hậu quả có thể đo

| Hậu quả | Tần suất cần xác nhận tại quán |
|---|---|
| Xếp ca trùng giờ học của nhân viên | dự kiến 2 đến 5 lần mỗi tuần |
| Ca thiếu người, phát hiện lúc 7h sáng hôm đó | dự kiến 1 đến 3 lần mỗi tuần |
| Việc treo từ ca trước bị bỏ rơi | dự kiến hầu như mỗi ngày |
| Bất công tích luỹ: một người liên tục bị dồn ca cuối tuần và ca đêm | luôn luôn, và là lý do số một khiến nhân viên nghỉ việc |

Các con số này là **giả thuyết phải đi xác nhận ở tuần 0**, không phải kết quả đã đo. Nếu quán thật cho số khác thì dùng số của quán.

## 3.3. Bảy con số phải đo trong tuần 0

1. Quản lý mất bao nhiêu phút xếp lịch một tuần
2. Tuần rồi có bao nhiêu ca bị đổi sau khi đã chốt lịch
3. Bao nhiêu nhân viên, trong đó bao nhiêu người là sinh viên có thời khoá biểu
4. Trong 8 tuần qua, ai làm ca cuối tuần nhiều nhất và ai ít nhất
5. Tuần rồi có bao nhiêu ngày sổ mở quán và đóng quán bị ghi bù
6. Lần gần nhất một việc treo từ ca trước bị bỏ rơi, và hậu quả
7. Bao nhiêu lần hết hàng giữa giờ cao điểm trong tháng

**Cách lấy mẫu phiếu, bắt buộc:** người phụ trách trình bày phải **ngồi xem một ca mở quán và một ca đóng quán thật**, ghi lại đúng thứ tự việc nhân viên làm. Không lấy bằng cách hỏi, vì cái người ta kể và cái người ta làm là hai thứ khác nhau.

---

# 4. Ba ý tưởng trung tâm

## 4.1. Ý tưởng 1: Cẩm nang sống

**Quan sát.** Mọi hệ thống quản lý đều bắt người dùng **cấu hình** trước khi dùng: nhập định mức, nhập quy tắc, nhập ngưỡng. Người dùng không biết trả lời, nên họ nhập bừa hoặc bỏ qua, rồi hệ thống chạy sai, rồi họ bỏ hệ thống.

Nhưng tri thức đó **có tồn tại**. Nó nằm trong hành động sửa của con người. Mỗi lần chị quản lý kéo một ô lịch từ người này sang người khác, chị đang **phát biểu một luật vận hành mà chị không viết ra**.

> **Không hỏi người dùng luật của quán. Quan sát lúc họ sửa, rồi hỏi lại một câu duy nhất: "có phải luật của quán mình là thế này không?"**

Chi tiết đầy đủ ở mục 9.

## 4.2. Ý tưởng 2: Mẫu phiếu là dữ liệu, không phải mã nguồn

Sáu quy trình vận hành của quán không phải sáu module. Chúng là **sáu tệp YAML** chạy trên một máy quy trình duy nhất. Hệ quả: thêm quy trình thứ bảy mất 60 giây, và điều đó **demo được ngay trên sân khấu**.

Đây là thứ chứng minh sản phẩm là một hệ điều hành, không phải một bộ ứng dụng ghép lại.

## 4.3. Ý tưởng 3: Kiểm kê là mạng cảm biến của quán

Đây là ý tưởng giải quyết vấn đề khó nhất của đề tài, và nó là chỗ đội có thể bị đánh sập nếu không có nó.

**Vấn đề.** Muốn dự báo nhu cầu nguyên liệu, muốn biết ca nào đông để xếp thêm người, thì cần **dữ liệu bán hàng**. Quán nhỏ không cho đội truy cập hệ thống bán hàng, và đội cũng không có ngân sách tích hợp. Mọi hệ thống thương mại giải bài này bằng cách tích hợp hệ thống bán hàng. Đội không làm được điều đó.

**Giải pháp.** Phiếu mở quán và phiếu đóng quán **đã có bước kiểm kê**, vì đó là việc quán vốn đã làm để tuân thủ. Hai lần đếm cùng một mặt hàng ở hai đầu ca cho ra **lượng tiêu thụ trong ca đó**:

```
tiêu thụ trong ca = số đếm đầu ca + số nhập trong ca − số đếm cuối ca − hao hụt đã ghi
```

Từ đó suy ra được, **không cần một dòng dữ liệu nào từ hệ thống bán hàng**:

| Suy ra được | Dùng để làm gì |
|---|---|
| Lượng tiêu thụ từng mặt hàng theo ca và theo thứ trong tuần | Dự báo nhu cầu, đặt ngưỡng tồn động |
| Mức độ đông của ca, tính bằng lượng nguyên liệu chính đã dùng | Đề xuất số người cần cho ca tương tự tuần sau |
| Sai lệch giữa tiêu thụ dự kiến và thực tế | Dấu hiệu hao hụt bất thường cần người xem |

**Vì sao đây là ý tưởng mạnh:** một tính năng xây ra vì lý do tuân thủ, tức bước kiểm kê trong danh mục kiểm tra, **trở thành mạng cảm biến** cho toàn bộ phần dự báo. Không tích hợp, không chi phí, không phụ thuộc nhà cung cấp nào.

**Nói rõ giới hạn, vì giám khảo sẽ hỏi:** đây là **ước lượng gián tiếp**, không phải số bán hàng thật. Sai số đến từ ba nguồn: người đếm sai, hao hụt không được ghi, và mặt hàng dùng cho nhiều món khác nhau. Vì thế mọi đầu ra dự báo đều **gắn nhãn ước lượng** và **luôn cần người phê duyệt** trước khi ảnh hưởng tới lịch hay tới đơn đặt hàng. Sai số này sẽ được đo và công bố, xem con số số 9 ở mục 18.2.

---

# 5. Kiến trúc mục tiêu: 13 agent, 5 nhóm nghiệp vụ

## 5.1. Nguyên tắc đặt trước

> **Bộ điều phối là máy trạng thái tất định, không phải mô hình ngôn ngữ. Và lõi quyết định không có agent nào.**

Căn cứ: nghiên cứu **MAST** công bố tại NeurIPS 2025 phân tích 150 vết chạy trên 7 framework đa agent với 6 người gán nhãn chuyên môn, độ đồng thuận κ = 0,88, xác định **14 dạng thất bại thuộc 3 nhóm** là vấn đề đặc tả và thiết kế hệ thống, lệch pha giữa các agent, và xác minh cùng kết thúc nhiệm vụ ([nguồn](https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html)). [Trang dự án MAST](https://sites.google.com/berkeley.edu/mast/) nêu rằng các thất bại này thường bắt nguồn từ **thiết kế và tương tác, cần thiết kế lại cấu trúc chứ không sửa được bằng cách chỉnh prompt**.

Bổ sung hai căn cứ về **khi nào đa agent thắng và khi nào thua**:

- [Anthropic mô tả hệ thống nghiên cứu đa agent của họ](https://www.anthropic.com/engineering/built-multi-agent-research-system): một agent dẫn dắt sinh ra các subagent chạy song song, **mỗi con một cửa sổ ngữ cảnh riêng**, và lợi thế đến chủ yếu từ điều đó. Chi phí khoảng **15 lần token** so với hội thoại thường, theo số được [dẫn lại](https://www.augmentcode.com/guides/multi-agent-cost-compounding).
- [Cognition, đội làm Devin, đã viết rằng phần lớn người ta không nên xây hệ đa agent](https://cognition.ai/blog/dont-build-multi-agents), vì các agent chạy song song tự đưa ra những lựa chọn ngầm xung đột nhau, dẫn tới sản phẩm dễ vỡ.
- [Anthropic cũng viết](https://www.anthropic.com/engineering/building-effective-agents) rằng các hiện thực thành công nhất dùng **khuôn mẫu đơn giản và ghép được, thay vì framework phức tạp**.

**Ba nguyên tắc bất biến rút ra:**

1. **Agent không gọi agent.** Chuỗi agent dài tối đa một bước.
2. **Agent không ghi cơ sở dữ liệu.** Chỉ bộ điều phối được ghi.
3. **Agent không quyết định luồng.** Mọi chuyển trạng thái là điều kiện viết bằng mã.

## 5.2. Mười ba agent, năm nhóm

Cột **Lô** cho biết cái nào ship trong 6 tuần.

### Nhóm 1 — Thu ràng buộc và nhân sự

| Mã | Agent | Đơn vị công việc | Đầu ra | Lô |
|---|---|---|---|---|
| **AG-TKB** | Đọc thời khoá biểu sinh viên | Một ảnh | Khoảng giờ học thành ràng buộc cứng | **1** |
| **AG-MSG** | Đọc tin nhắn tự do | Một tin nhắn | Một trong 6 ý định, kèm ràng buộc trích xuất | **1** |
| **AG-HANDOVER** | Đọc bàn giao ca | Một phiếu | Bốn ô SBAR và danh sách việc treo | **1** |

### Nhóm 2 — Vận hành và tri thức nội bộ

| Mã | Agent | Nhiệm vụ | Lô |
|---|---|---|---|
| **AG-SOP** | Trợ lý hỏi đáp quy trình cho nhân viên mới, **trả lời chỉ dựa trên mẫu phiếu và cẩm nang của chính quán**, kèm trích dẫn | **1** |
| **AG-RULE** ⭐ | Từ một lần con người sửa, đề xuất **một** luật vận hành viết bằng tiếng Việt kèm bằng chứng | **1** |

### Nhóm 3 — Kho vận và chất lượng

| Mã | Agent | Nhiệm vụ | Lô |
|---|---|---|---|
| **AG-WASTE** | Đọc ghi chú hao hụt viết tự do thành số lượng và nguyên nhân có cấu trúc | **1** |
| **AG-FORECAST** | Từ tiêu thụ suy ra ở mục 4.3 cộng thời tiết, **đề xuất** ngưỡng tồn và lượng đặt hàng. Người phê duyệt | 2 |
| **AG-INVOICE** | Đọc ảnh phiếu giao hàng thành lô nhập kèm hạn dùng | 2 |
| **AG-SHELF** | Đọc ảnh kệ hàng, đề xuất mặt hàng trông sắp hết | 2 |

### Nhóm 4 — Diễn giải cho con người

| Mã | Agent | Nhiệm vụ | Lô |
|---|---|---|---|
| **AG-EXPLAIN** | Dịch mã lý do của bộ giải thành câu tiếng Việt | **1** |
| **AG-BRIEF** | Viết bản tin sáng cho chủ quán, tối đa 5 câu | **1** |

### Nhóm 5 — Tiếng nói khách hàng

| Mã | Agent | Nhiệm vụ | Lô |
|---|---|---|---|
| **AG-VOC** | Đọc phản hồi khách **do quán tự cung cấp**, phân loại thành sự cố vận hành và **nối vào việc treo**, không nối vào marketing | **1** |
| **AG-MENUOPS** | Từ tiêu thụ và hao hụt, chỉ ra món **gây hao hụt cao và tốn thời gian pha chế cao**. Không tính lợi nhuận | 2 |

**Lô 1: 9 agent.** Lô 2: 4 agent, đã thiết kế và tính chi phí, xem mục 13.6.

## 5.3. Sơ đồ toàn hệ

```
┌─ NGƯỜI ─────────────────────────────────────────────────────────┐
│ Phê duyệt ràng buộc · Chốt lịch · Duyệt luật · Duyệt đơn đặt hàng│
│ Xử lý mọi thứ bị cổng kiểm chứng đẩy lên                         │
└───────────────────────────▲──────────────────┬──────────────────┘
                            │                  │ mỗi lần sửa
┌─ BỘ ĐIỀU PHỐI (TẤT ĐỊNH, KHÔNG PHẢI LLM) ───┼──────────────────┐
│ Máy trạng thái · phát nhiệm vụ song song · retry · timeout       │
│ idempotency · trần ngân sách · ghi vết · phát lại phiên           │
│                      NGƯỜI GHI DUY NHẤT                          │
└──┬──────────────┬──────────────┬───────────────────┬────────────┘
   ▼              ▼              ▼                   ▼
┌─ LÀN ĐỌC ────┐ ┌─ LÀN DIỄN ─┐ ┌─ LÀN HỌC ──────┐ ┌─ LÕI ─────────┐
│ AG-TKB       │ │ AG-EXPLAIN │ │ AG-RULE ⭐     │ │ CP-SAT        │
│ AG-MSG       │ │ AG-BRIEF   │ │                │ │ RULE ENGINE   │
│ AG-HANDOVER  │ │ AG-SOP     │ │                │ │ MÁY QUY TRÌNH │
│ AG-WASTE     │ │            │ │                │ │ SỔ TIÊU THỤ   │
│ AG-VOC       │ │            │ │                │ │               │
│ (lô 2: 3 con)│ │            │ │                │ │ KHÔNG CÓ AGENT│
└──────┬───────┘ └─────┬──────┘ └───────┬────────┘ └───────▲───────┘
       └───────────────┴────────────────┘                  │
                       ▼                                   │
        ┌─ 6 CỔNG KIỂM CHỨNG (TẤT ĐỊNH) ─┐                │
        │ SCHEMA · TRACE · CONF ·         │────────────────┘
        │ CONFLICT · NUM · RULE            │
        │  không đạt  →  ĐẨY LÊN NGƯỜI     │                │
        └──────────────────┬──────────────┘                 │
                           ▼                                │
                  ┌─ CẨM NANG QUÁN ─┐                       │
                  │ luật đọc được,   │───────────────────────┘
                  │ bật tắt được     │  luật đã duyệt trở thành
                  └──────────────────┘  tham số của lõi
```

Vòng dưới cùng là vòng khép kín của Cẩm nang sống: luật sinh ra từ hành vi con người, qua cổng, được người duyệt, rồi **trở thành tham số của lõi quyết định**.

## 5.4. Chín thuộc tính bắt buộc của mỗi agent

Mỗi agent có một tệp `PHAM_VI.md` ghi đủ chín thuộc tính. Thiếu là vi phạm nhóm thất bại thứ nhất của MAST, và có bài kiểm thử làm đỏ nếu thiếu tệp.

Nhiệm vụ · Phạm vi · Đầu vào · Đầu ra · Mô hình dùng · Có chạy song song không · Điều kiện dừng · **Danh sách cấm** · Cổng phải qua.

Ví dụ đầy đủ cho **AG-RULE**, agent quan trọng nhất:

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Từ **một** cặp trước và sau khi người sửa, đề xuất **đúng một** luật |
| Phạm vi | Một lần sửa. Được xem tối đa 10 lần sửa tương tự trước đó để tìm mẫu lặp lại, không nhiều hơn |
| Đầu vào | `{loai_quyet_dinh, dau_ra_cu, ban_sua, boi_canh_toi_thieu, cac_lan_sua_tuong_tu}` |
| Đầu ra | `{cau_luat_tieng_viet, dieu_kien_ap_dung_co_cau_truc, bang_chung: [id_lan_sua], do_tin_cay}` |
| Mô hình | Nhỏ là đủ. Đây là nhiệm vụ nhận mẫu, không phải suy luận dài |
| Song song | Không. Hàng đợi, mỗi lần một luật |
| Điều kiện dừng | Trả một luật, hoặc trả rỗng nếu chưa đủ bằng chứng |
| **Cấm** | Không đề xuất khi có **dưới 3 lần sửa cùng mẫu** · không viết luật về một con người cụ thể · không tạo điều kiện dựa trên trường dữ liệu không tồn tại · không sửa hoặc xoá luật đã có |
| Cổng | VF-SCHEMA, VF-TRACE, VF-CONF, **VF-RULE** |

## 5.5. Sáu cổng kiểm chứng

Cổng là mã nguồn thường, tất định, không có mô hình ngôn ngữ.

| Cổng | Kiểm gì | Không đạt thì làm gì |
|---|---|---|
| VF-SCHEMA | Đầu ra khớp lược đồ | Thử lại 1 lần, vẫn sai thì đẩy lên người |
| VF-TRACE | Mọi thứ trích xuất trỏ về vùng ảnh hoặc đoạn văn thật tồn tại | Loại phần không có nguồn |
| VF-CONF | Độ tin cậy đạt ngưỡng | Dưới ngưỡng thì **luôn** đẩy lên người, không thử lại |
| VF-CONFLICT | Hai agent nói trái nhau về cùng một người, cùng khung giờ | **Không tự hoà giải.** Hiện cả hai, đẩy lên người |
| VF-NUM | Mọi con số trong câu diễn giải tồn tại trong dữ liệu đầu vào | Loại cả câu, ghi vào bảng câu bị loại |
| **VF-RULE** | Luật có **ít nhất 3 bằng chứng**, điều kiện chỉ dùng trường tồn tại thật, **không xung đột luật đã có** | Loại, ghi lý do vào bảng luật bị loại |

**Nguyên tắc thất bại đóng:** khi không chắc, hệ thống **luôn** chuyển sang chờ người, không bao giờ chọn phương án có vẻ hợp lý.

---

# 6. Sàng lọc mười đề xuất agent: bốn nhận, hai thu hẹp, bốn loại

Mục này là mục quan trọng nhất khi phản biện. Một hội đồng chuyên môn sẽ không hỏi "các em có bao nhiêu agent". Họ sẽ hỏi **"dữ liệu cho agent này lấy ở đâu"**. Bảng dưới đây trả lời trước.

## 6.1. Bốn đề xuất nhận nguyên vẹn

| Đề xuất | Thành agent nào | Vì sao thực thi được |
|---|---|---|
| **Dynamic Staff Rostering** | Hạt nhân đã có, cộng AG-FORECAST ở lô 2 | Đã có bộ giải CP-SAT. Điểm khác: bản của đội tối ưu **công bằng** thay vì chi phí nhân công, vì không có dữ liệu lương |
| **Waste & Quality Monitoring** | **AG-WASTE** lô 1, **AG-INVOICE** lô 2 | Hao hụt ghi ngay trong phiếu vận hành. Hạn dùng đến từ phiếu giao hàng, không cần hệ thống bán hàng |
| **Training & SOP** | **AG-SOP** lô 1 | **Rẻ nhất và giá trị cao nhất.** Nguồn tri thức chính là mẫu phiếu YAML và Cẩm nang sống, hai thứ đã tồn tại. Không cần dữ liệu mới |
| **Inventory Forecasting** | **AG-FORECAST** lô 2 | Chỉ khả thi **nhờ ý tưởng 3 ở mục 4.3**: suy ra tiêu thụ từ chênh lệch hai lần kiểm kê. Không có ý tưởng đó thì đề xuất này không thực thi được |

## 6.2. Hai đề xuất thu hẹp, và nói rõ đã bỏ phần nào

### Customer Support & Feedback → **AG-VOC**

| Phần đề xuất | Quyết định |
|---|---|
| Tự động trả lời khách về menu và chính sách đổi trả | **Bỏ.** Trả lời khách thay quán là hành động đối ngoại có rủi ro, và cần menu cùng chính sách được duyệt. Ngoài phạm vi |
| Quét và phân loại đánh giá trên Google Maps, ShopeeFood, Grab | **Thu hẹp.** ⚠️ Thu thập tự động từ các nền tảng này **có khả năng vi phạm điều khoản sử dụng của họ**, và đội chưa kiểm chứng được điều đó. Nên phiên bản này chỉ nhận phản hồi **do quán tự chuyển vào**: chủ chuyển tiếp tin nhắn, dán nội dung, hoặc chuyển ảnh chụp |
| Cảnh báo sự cố dịch vụ | **Nhận.** Đây là phần có giá trị thật, và nó **nối vào việc treo** của quy trình vận hành, tức phản hồi khách trở thành một việc có người chịu trách nhiệm và có hạn |

**Việc phải tự kiểm chứng:** trước khi làm bất kỳ hình thức thu thập tự động nào, phải đọc điều khoản sử dụng của từng nền tảng. Tài liệu này **không giả định** là được phép.

### Menu Engineering → **AG-MENUOPS**

| Phần đề xuất | Quyết định |
|---|---|
| Phân tích ma trận menu theo biên lợi nhuận | **Bỏ.** Cần giá vốn từng món và số bán từng món, tức cần hệ thống bán hàng và số liệu kế toán. Đội không có, và đề tài đã tuyên bố không làm module tài chính |
| Chỉ ra món cần xem lại | **Thu hẹp sang góc vận hành.** Từ tiêu thụ suy ra và hao hụt, chỉ ra món **gây hao hụt cao** và **tốn thời gian pha chế cao ở giờ cao điểm**. Đây là hai đại lượng đội đo được thật |

## 6.3. Bốn đề xuất loại hoàn toàn, kèm lý do kỹ thuật

Đây là bảng khiến đề tài không có lỗ hổng. Loại có lý do mạnh hơn nhận mà không giải thích được.

| Đề xuất | Lý do loại |
|---|---|
| **Smart Ordering Agent** với Voice AI tại quầy và drive-thru, tự động gợi ý upsell | **Ba lý do độc lập.** Một, nhận đơn cần ghi vào hệ thống bán hàng của quán; đội không có quyền truy cập và cũng không nên tạo một luồng đơn hàng thứ hai song song, vì đó là cách nhanh nhất làm lệch dữ liệu của quán. Hai, quán nhỏ ở Việt Nam **không có drive-thru**, nên nửa đề xuất không có đối tượng. Ba, upsell theo lịch sử mua cần dữ liệu định danh khách hàng, mà **thể lệ cuộc thi cấm dùng dữ liệu cá nhân khi chưa được phép** |
| **Barista Copilot** điều phối đơn xuống quầy bar theo thời gian thực | Cần **luồng đơn hàng trực tiếp** từ hệ thống bán hàng. Không có luồng đó thì mọi thứ chỉ là mô phỏng trên dữ liệu giả, và một tính năng demo trên dữ liệu giả sẽ bị hội đồng phát hiện ngay. Ghi vào lộ trình, điều kiện mở lại là quán đồng ý cho tích hợp hệ thống bán hàng |
| **Personalized Retention Agent** phân khúc khách và cá nhân hoá ưu đãi | Cần định danh khách và lịch sử giao dịch. Hai vấn đề: đội không có dữ liệu đó, và **đây là dữ liệu cá nhân**, thuộc đúng loại mà thể lệ yêu cầu cam kết không sử dụng khi chưa được phép. Không làm là quyết định đúng, không phải hạn chế năng lực |
| **Nhóm agent quản trị chiến lược** | Chưa đủ cụ thể để định nghĩa đầu vào, đầu ra và điều kiện dừng. Một agent không định nghĩa được chín thuộc tính ở mục 5.4 thì không được vào hệ thống. Đây chính là dạng thất bại thứ nhất của MAST |

**Câu nói khi phản biện:** chúng em khảo sát mười ba hướng agent cho quán. Bốn hướng bị loại vì không có nguồn dữ liệu hợp pháp hoặc không có đối tượng thật, và **chúng em nói ra điều đó trước khi hội đồng hỏi**. Một hệ thống mười ba agent trong đó bốn agent chạy trên dữ liệu giả thì tệ hơn một hệ thống mười agent chạy trên dữ liệu thật.

---

# 7. Kiến trúc bốn tầng và mười lăm việc cấm agent hoá

## 7.1. Bốn tầng

| Tầng | Vùng mã nguồn | Tính chất | Được phép | Bị cấm |
|---|---|---|---|---|
| Điều phối | `apps/api/.../orchestration` | Tất định | Ghi trạng thái, phát nhiệm vụ, quyết định luồng | Gọi mô hình để quyết định luồng |
| Agent | `packages/agents` | Xác suất | Đọc, đề xuất, diễn giải | Ghi DB, gọi agent khác, quyết định luồng, tính con số |
| Cổng | `packages/gates` | Tất định | Loại bỏ, đẩy lên người | Có bất kỳ tính xác suất nào |
| Lõi | `packages/solver`, `packages/opsengine`, `packages/playbook`, `domain/policies` | Tất định, chứng minh được | Xếp ca, chạy phiếu, tính tiêu thụ, quyết định tự duyệt | Có mô hình ngôn ngữ |

## 7.2. Mười lăm việc cấm agent hoá

Đưa vào `docs/adr/ADR-008`, nêu nguyên văn khi phản biện.

Xếp ca · quyết định tự duyệt hay chặn một yêu cầu đổi ca · tính sổ nợ công bằng · quyết định escalate · ghi vào cơ sở dữ liệu · quyết định chuyển trạng thái phiên · quyết định một bước phiếu là đã làm hay chưa · quyết định một dấu hiệu tích khống có phải gian dối hay không · quyết định mở chế độ bù ca khẩn · quyết định một mặt hàng đã dưới ngưỡng tồn · **quyết định một luật có hiệu lực hay không** · **quyết định xoá một luật đã có** · **tính lượng tiêu thụ từ số kiểm kê** · **gửi đơn đặt hàng cho nhà cung cấp** · **trả lời khách hàng thay quán**.

Ba việc cuối là ba việc thêm vào ở phiên bản 3.0. Việc gửi đơn đặt hàng có hậu quả tiền thật, nên nó **luôn cần người bấm**, kể cả khi AG-FORECAST rất tự tin.

---

# 8. Nghiệp vụ chi tiết bảy quy trình

## 8.1. Xếp ca tuần

**Sáu ràng buộc cứng:** không trùng giờ học · đủ người và đủ vị trí kỹ năng mỗi ca · một người không ở hai ca cùng lúc · khoảng nghỉ tối thiểu giữa hai ca · trần giờ tuần và ngày liên tiếp · ngày đã duyệt nghỉ phép.

**Năm ràng buộc mềm có trọng số:** nguyện vọng ca · **chia đều ca cuối tuần và ca đêm** · ca liền mạch tránh lịch vụn · ổn định so với tuần trước · ghép người mới với người có kinh nghiệm.

> ⚠️ **Việc phải tự kiểm chứng:** con số về khoảng nghỉ tối thiểu, trần giờ làm việc và giới hạn giờ làm của người đang học **phải tra từ Bộ luật Lao động và văn bản hướng dẫn hiện hành**. Tài liệu này cố tình không nêu con số. Để tất cả là **tham số cấu hình**. Khi phản biện: "chúng em không viết cứng con số nào, vì quy định đổi thì hệ thống không phải sửa mã nguồn."

## 8.2. Sổ nợ công bằng

Mỗi nhân viên có số dư nợ theo **bốn chiều gánh nặng**: ca cuối tuần, ca đêm, tổng giờ, ca vụn. Nợ **tích luỹ qua các tuần**, và bộ giải tối thiểu hoá **nợ lớn nhất**, không phải tổng nợ.

**Vì sao tối thiểu hoá nợ lớn nhất:** vì nó bảo vệ **người bị đối xử tệ nhất**, thay vì tối ưu mức trung bình. Tối thiểu hoá tổng nợ cho phép một người rất bất công miễn là những người khác rất thoải mái. Đây là một quyết định giá trị, và phải ghi vào ADR-006.

## 8.3. Chợ đổi ca, ba nhánh

```
A đăng nhả ca
  → Hệ thống tìm người đủ điều kiện, kiểm 5 điều:
      không trùng giờ học · không trùng ca khác · đủ giờ nghỉ giữa ca
      · chưa vượt trần giờ tuần · có kỹ năng vị trí đó cần
  → Gửi lời mời CHỈ cho những người đó
  → B nhận:
      Thoả HẾT ràng buộc  → TỰ DUYỆT, quản lý nhận báo cáo
      Vi phạm ràng buộc MỀM → chuyển quản lý duyệt, NÊU RÕ vi phạm gì
      Vi phạm ràng buộc CỨNG → CHẶN
```

**Chỗ dễ sai số 1:** khi B nhận ca của A, phải kiểm lại ràng buộc **theo trạng thái lịch tại thời điểm nhận**, không phải lúc A đăng, vì giữa hai thời điểm có thể đã có vụ đổi ca khác. Đây là một bài kiểm thử bắt buộc.

## 8.4. Mở quán và đóng quán

**Mở phiếu:** ngay khi nhân viên điểm danh QR. **Không điểm danh thì không mở được phiếu.**

**Mẫu phiếu là dữ liệu:**

```yaml
ma: mo_quan
ten: Mở quán
gan_voi: ca_dau_ngay
mo_khi: nhan_vien_da_diem_danh
han_hoan_thanh_phut: 30
buoc:
  - ma: bat_may_pha
    ten: Bật máy pha và chờ đủ nhiệt
    minh_chung: khong
  - ma: nhiet_do_tu_lanh
    ten: Ghi nhiệt độ tủ lạnh
    minh_chung: so
    nguong: { min: 2, max: 8 }        # ngoài ngưỡng -> sinh việc treo
  - ma: ve_sinh_quay
    ten: Vệ sinh quầy pha
    minh_chung: anh                    # bắt buộc ảnh chụp mới
  - ma: kiem_ke_dau_ca
    ten: Kiểm kê 8 mặt hàng chính
    minh_chung: kiem_ke                # số này đi vào SỔ TIÊU THỤ
    danh_muc: [sua_tuoi, ca_phe_hat, tra, duong, ly_nhua, ong_hut, banh, da]
  - ma: doc_viec_treo
    ten: Đọc việc treo từ ca trước
    minh_chung: xac_nhan_doc
escalate:
  - dieu_kien: qua_han_phut > 30
    hanh_dong: nhac_nhan_vien
  - dieu_kien: qua_han_phut > 60
    hanh_dong: bao_chu_quan
```

**Ba loại kết quả mỗi bước:** đã làm · không áp dụng · **có vấn đề**. Bước có vấn đề sinh **việc treo** có người nhận và hạn.

**Cơ chế chống tích khống:**

| Cơ chế | Cách làm |
|---|---|
| Ảnh phải chụp mới | Chỉ nhận ảnh từ camera trong phiên. Băm nội dung để phát hiện ảnh dùng lại |
| Dấu thời gian của máy chủ | Không tin dấu thời gian của điện thoại |
| Gắn với ca và người đã điểm danh | Người ca sáng không làm được phiếu của ca chiều |
| Phát hiện mẫu bất thường | Phiếu 20 bước xong dưới 90 giây · nhiều ngày điền cùng một phút · ảnh trùng băm · giờ điền lệch xa giờ ca |
| Bảng dấu hiệu cho chủ | **Không tự kết luận ai gian.** Chỉ hiện dấu hiệu kèm dữ liệu |

**Vì sao không chặn khi thấy dấu hiệu:** chặn sai sẽ làm nhân viên bỏ không dùng nữa, và lúc đó hệ thống mất giá trị hoàn toàn. Hệ thống **để lại vết và hiện cho chủ**. Sổ giấy không làm được điều đó.

**Căn cứ về việc danh mục kiểm tra có tác dụng:** [WHO công bố](https://www.who.int/news/item/11-12-2010-checklist-helps-reduce-surgical-complications-deaths) tỉ lệ biến chứng nặng sau mổ giảm từ 11% xuống 7% và tử vong nội trú giảm hơn 40% khi áp dụng danh mục kiểm tra an toàn phẫu thuật. **Nhưng phải nói cả mặt kia:** [một phân tích tổng hợp](https://pubmed.ncbi.nlm.nih.gov/24469615/) kết luận bằng chứng **rất gợi ý** nhưng **không thể coi là chắc chắn**; [một tổng quan 25 nghiên cứu](https://pmc.ncbi.nlm.nih.gov/articles/PMC4943979/) thấy kết quả **không nhất quán**; và [một đánh giá khác](https://www.ncbi.nlm.nih.gov/books/NBK561963/) nêu rằng hiệu quả **phụ thuộc vào việc nó có được thực hiện thật hay không**.

Chính điều cuối là lý do cơ chế chống tích khống tồn tại. Nếu danh mục kiểm tra chỉ có tác dụng khi được làm thật, thì bài toán kỹ thuật không phải là số hoá cái danh sách.

## 8.5. Bàn giao ca

**Khung SBAR, đổi tên cho người bán cà phê:**

| SBAR | Tên trong sản phẩm | Nội dung |
|---|---|---|
| Situation | **Đang thế nào** | Tình trạng quán lúc giao ca |
| Background | **Chuyện đã xảy ra** | Việc gì đã diễn ra trong ca |
| Assessment | **Cần để ý** | Máy có tiếng lạ, sữa gần hết |
| Recommendation | **Việc treo lại** | Danh sách việc cụ thể, có người nhận và hạn |

**Căn cứ:** trong y tế, bàn giao giữa các ca là điểm mất thông tin đã được nghiên cứu nhiều, và SBAR là công cụ chuẩn hoá được dùng rộng rãi. [Tổng quan hệ thống về ISBAR và SBAR trong bàn giao ca điều dưỡng](https://pmc.ncbi.nlm.nih.gov/articles/PMC13291198/) và [tổng quan về tác động tới an toàn người bệnh](https://pmc.ncbi.nlm.nih.gov/articles/PMC6112409/). Tài liệu cơ quan y tế Anh ghi rằng **WHO khuyến nghị dùng SBAR để chuẩn hoá bàn giao**, và nêu rõ **không hệ thống nào phù hợp mọi bối cảnh, cần điều chỉnh theo địa phương** ([nguồn](https://www.ncbi.nlm.nih.gov/books/NBK564933/)). **Trung thực về độ mạnh:** [một đánh giá chuyên môn](https://www.ncbi.nlm.nih.gov/books/NBK613742/) xếp bằng chứng ở mức **độ tin cậy thấp**.

**Chỗ dễ sai số 2:** **người xác nhận danh sách việc treo là người NHẬN ca, không phải người giao ca.** Vì người nhận là người phải làm, nên việc xác nhận trở thành hành động có lợi cho chính họ, và vì thế nó được làm thật thay vì bấm cho xong.

Việc treo chưa xong thì **chuyển tiếp sang ca sau**, hiện ở bước "đọc việc treo". Quá 3 ca chưa xong thì escalate lên chủ.

## 8.6. Kiểm kê, sổ tiêu thụ, và hao hụt

**Kiểm kê** nằm trong phiếu mở quán và phiếu đóng quán. Mỗi mặt hàng có **ngưỡng tồn tối thiểu**; xuống dưới ngưỡng thì sinh cảnh báo và một việc treo "đặt hàng".

**Sổ tiêu thụ** tính theo công thức ở mục 4.3, bằng mã nguồn tất định, **không có agent nào tham gia**.

**Hao hụt** ghi ngay trong ca: số lượng và nguyên nhân. AG-WASTE đọc ghi chú viết tự do thành cấu trúc, ví dụ *"làm sai 2 ly, bánh hết ngày 3 cái"* thành hai dòng có mặt hàng, số lượng và nguyên nhân.

**Phi mục tiêu quan trọng:** hệ thống ghi **số lượng**, **không làm kế toán**. Nếu chủ nhập đơn giá thì hệ thống chỉ dùng để **xếp thứ tự ưu tiên**, và ghi rõ điều đó trên giao diện. Không sổ sách, không báo cáo doanh thu, không tính lương.

## 8.7. Bù ca khẩn

```
Quá 15 phút không điểm danh → nhắc riêng nhân viên đó
Quá 25 phút → mở BÙ CA KHẨN:
                tìm người đủ 5 điều kiện như chợ đổi ca
                xếp theo: đang rảnh · nợ công bằng thấp · ở gần
                gửi lời mời cho tối đa 5 người cùng lúc
                ai nhận trước thì được
Quá 40 phút → báo chủ quán kèm danh sách đã mời và ai đã từ chối
```

**Chỗ dễ sai số 3:** khi nhiều người bấm nhận cùng lúc, phải có **khoá tranh chấp ở tầng cơ sở dữ liệu**, không phải kiểm ở tầng ứng dụng. Bài kiểm thử bắt buộc: 5 yêu cầu đồng thời, đúng một người được.

---

# 9. Cẩm nang sống

## 9.1. Năm loại luật hệ thống được phép học

Chỉ năm loại. Ngoài ra AG-RULE không được đề xuất gì.

| Loại | Ví dụ luật | Học từ |
|---|---|---|
| **Nhu cầu người theo ca** | "Thứ Bảy ca chiều cần 3 người pha chế, không phải 2" | Các lần quản lý thêm người vào cùng một loại ca |
| **Ngưỡng tồn của một mặt hàng** | "Sữa tươi cần ngưỡng 8 hộp, không phải 5" | Các lần chủ sửa ngưỡng, hoặc các lần hết hàng dù chưa báo động |
| **Bước phiếu cần thêm hoặc bỏ** | "Ca sáng thứ Hai cần thêm bước xả nước máy pha hai lần" | Các lần nhân viên ghi chú cùng nội dung ở ô có vấn đề |
| **Ghép người theo kỹ năng** | "Ca cuối tuần nên có ít nhất một người đã làm trên 3 tháng" | Các lần quản lý đổi phân công theo cùng một mẫu |
| **Nguyên nhân hao hụt lặp lại** | "Bánh hết ngày thường dư vào tối thứ Ba, nên giảm nhập thứ Ba" | AG-WASTE gom nguyên nhân theo thời gian |

**Cấm tuyệt đối:** luật về năng lực hoặc thái độ của một con người. Loại thứ tư là luật về **cách ghép**, không phải luật đánh giá người.

## 9.2. Vòng đời tám bước của một luật

```
1. GHI NHẬN     Mỗi lần người sửa, lưu cặp trước và sau, kèm bối cảnh
                       │
2. TÌM MẪU      Đủ 3 lần sửa cùng mẫu → đưa vào hàng đợi AG-RULE
                       │                 (dưới 3 lần: không làm gì)
3. ĐỀ XUẤT      AG-RULE viết MỘT câu luật tiếng Việt + điều kiện có cấu trúc
                + danh sách bằng chứng là các lần sửa cụ thể
                       │
4. KIỂM CHỨNG   VF-RULE: đủ 3 bằng chứng? điều kiện dùng trường tồn tại?
                không xung đột luật đã có?  →  không đạt: LOẠI, ghi lý do
                       │
5. TẬP SỰ       Luật chạy IM LẶNG 5 lần: hệ thống ghi "nếu áp dụng thì
                tôi sẽ làm X" rồi đối chiếu quyết định thật của người.
                Đúng từ 4 trên 5 → đủ điều kiện lên chính thức
                       │
6. NGƯỜI DUYỆT  Chủ hoặc quản lý xem câu luật, bằng chứng, kết quả tập sự,
                rồi bấm duyệt. KHÔNG duyệt thì luật không có hiệu lực
                       │
7. CÓ HIỆU LỰC  Luật trở thành tham số của lõi quyết định
                       │
8. THEO DÕI     Đếm số lần áp dụng và số lần bị người ghi đè.
                Tỉ lệ đúng tụt dưới 80% → TỰ ĐỘNG TẮT và báo người xem lại
```

**Bước 5 và bước 8 là hai bước quan trọng nhất.** Bước 5 bảo đảm một luật sai không bao giờ chạm vào quyết định thật. Bước 8 bảo đảm một luật từng đúng mà nay đã lạc hậu sẽ tự rút lui.

## 9.3. Giao diện cẩm nang

Một trang, mỗi luật một thẻ, ba thứ bắt buộc phải có:

```
┌────────────────────────────────────────────────────────────┐
│ Thứ Bảy ca chiều cần 3 người pha chế, không phải 2         │
│                                                            │
│ Nguồn gốc: 4 lần chị Lan sửa vào các thứ Bảy    [xem]      │
│ Tập sự:    đúng 5 trên 5 lần                               │
│ Đã áp dụng: 7 lần · người ghi đè: 0 lần · đúng 100%        │
│                                                            │
│ [Đang bật]  [Tắt]  [Sửa câu luật]  [Xoá]                   │
└────────────────────────────────────────────────────────────┘
```

## 9.4. AG-SOP: cẩm nang trở thành người hướng dẫn

Đây là chỗ Cẩm nang sống trả lãi lần thứ hai, và là lý do AG-SOP có tỉ lệ giá trị trên chi phí cao nhất trong toàn bộ hệ.

Nhân viên mới hỏi bằng tiếng Việt tự nhiên: *"nhiệt độ tủ lạnh bao nhiêu là được?"*, *"sáng thứ Hai có gì khác không?"*. AG-SOP trả lời **chỉ dựa trên hai nguồn**: mẫu phiếu YAML và các luật đã duyệt trong Cẩm nang. Mỗi câu trả lời **kèm trích dẫn** là bước phiếu nào hoặc luật nào.

**Cấm:** trả lời từ kiến thức chung của mô hình. Không có căn cứ trong hai nguồn trên thì trả lời *"chưa có trong cẩm nang của quán, hãy hỏi quản lý"*. Cổng VF-TRACE bắt buộc.

**Vì sao đây là tính năng đẹp:** tri thức mà hệ thống học được từ chị quản lý **quay lại dạy nhân viên mới thay chị**. Vòng lặp đóng lại.

## 9.5. Bốn chỉ số của Cẩm nang sống

| Chỉ số | Ý nghĩa | Kỳ vọng, phải đi đo |
|---|---|---|
| **Tỉ lệ không cần sửa** | Phần trăm quyết định hệ thống đưa ra mà người không sửa | Tuần 1 khoảng 40%, tuần 6 khoảng 85% |
| Số luật đang có hiệu lực | Kích thước cẩm nang | Tuần 6 khoảng 12 đến 20 luật |
| Số luật bị VF-RULE loại | Bằng chứng cổng đang hoạt động | Chiếu trong demo |
| Số luật tự tắt vì tỉ lệ đúng tụt | Bằng chứng cơ chế rút lui hoạt động | Ít nhất 1 |

**Đường cong tỉ lệ không cần sửa là slide mạnh nhất của cả bài thuyết trình**, vì nó là bằng chứng hệ thống đang học thật. Nhưng nó chỉ có giá trị nếu **đo thật**: con số 40% và 85% ở trên là **kỳ vọng**, không phải kết quả.

---

# 10. Ngân sách 0 đồng

## 10.1. Bài toán số

Chi phí duy nhất có thể phát sinh là gọi mô hình ngôn ngữ. Ba cơ chế giữ nó rất nhỏ: **bộ nhớ đệm theo nội dung** (thời khoá biểu đổi một lần mỗi học kỳ, nên 25 lần gọi thành gần 0 từ tuần thứ hai, và chạy lại trong lúc phát triển tốn 0 lần gọi) · **mô hình hai bậc** (mô hình nhỏ trước, chỉ lên mô hình lớn khi độ tin cậy thấp) · **gọi theo yêu cầu** (AG-EXPLAIN chỉ chạy khi có người bấm).

**Số lần gọi ở trạng thái bình thường, lô 1:**

| Agent | Lần mỗi tuần |
|---|---|
| AG-TKB | 0 đến 3, đã đệm |
| AG-MSG | 60 |
| AG-HANDOVER | 14, hai ca mỗi ngày |
| AG-WASTE | 14 |
| AG-EXPLAIN | 7, theo yêu cầu |
| AG-RULE | 3 đến 5 |
| AG-SOP | 10 |
| AG-BRIEF | 7 |
| AG-VOC | 5 |
| **Tổng** | **khoảng 125 mỗi tuần, tức khoảng 18 lần mỗi ngày** |

## 10.2. Mười tám lần mỗi ngày so với hạn mức miễn phí

[Groq có hạn mức miễn phí không cần thẻ tín dụng, khoảng 30 yêu cầu mỗi phút](https://www.eesel.ai/blog/groq-pricing), và [một so sánh hạn mức](https://docs.bswen.com/blog/2026-03-23-free-llm-api-rate-limits-compared/) ghi Groq ở mức **14.400 yêu cầu mỗi ngày**. [OpenRouter cho các biến thể mô hình miễn phí](https://pinggy.io/blog/free_ai_model_apis_unlimited_tokens_openrouter/) với 20 yêu cầu mỗi phút và 50 hoặc 1.000 mỗi ngày tuỳ trường hợp. [Một tổng hợp](https://www.edenai.co/post/top-free-generative-ai-apis-and-open-source-models) cho biết có thể **xếp nhiều hạn mức miễn phí lại để đạt hơn 5.000 yêu cầu mỗi ngày**. Google công bố [hạn mức Gemini API](https://ai.google.dev/gemini-api/docs/rate-limits) trong tài liệu chính thức.

> **18 lần gọi mỗi ngày.** Ngay cả hạn mức khắt khe nhất trong các nguồn trên là 50 mỗi ngày cũng còn dư. Với Groq thì đó là khoảng **0,1%** hạn mức ngày.

**Cảnh báo phải tự kiểm chứng:** [một bài phân tích](https://docs.bswen.com/blog/2026-03-23-best-free-llm-api-providers-2026/) nêu rằng nhiều thứ gọi là miễn phí thực chất là **bản dùng thử 30 đến 90 ngày tự chuyển sang trả phí**. Trước khi chốt nhà cung cấp, mở trang giá chính thức xác nhận hạn mức là **vĩnh viễn**, rồi ghi ngày kiểm tra vào `docs/THIRD_PARTY.md`. Số trong tài liệu này là số tại thời điểm tra cứu.

*Nội dung từ các nguồn trên đã được diễn giải lại để tuân thủ quy định bản quyền.*

## 10.3. Sổ chi phí đầy đủ

| # | Thành phần | Phương án 0 đồng | Hạn mức và cảnh báo |
|---|---|---|---|
| 1 | Gọi mô hình ngôn ngữ | **Bộ định tuyến nhiều nhà cung cấp miễn phí**, mục 10.4 | Xác nhận hạn mức vĩnh viễn trước khi chốt |
| 2 | Mô hình dự phòng khi hết hạn mức | **Ollama chạy cục bộ** | Miễn phí tuyệt đối. Bản nhỏ chạy trên laptop |
| 3 | Nhận dạng giọng nói tiếng Việt | **PhoWhisper** của VinAI, cục bộ | Mã nguồn mở, bản `base` chạy trên CPU |
| 4 | Đọc chữ trong ảnh | **PaddleOCR** hoặc **VietOCR**, cục bộ | Mã nguồn mở |
| 5 | Bộ giải tối ưu | **Google OR-Tools CP-SAT** | Mã nguồn mở. **Đọc tệp LICENSE** trước khi công bố |
| 6 | Thời tiết cho AG-FORECAST, lô 2 | API thời tiết mở, không cần khoá | Kiểm tra điều khoản trước khi dùng |
| 7 | Cơ sở dữ liệu | **PostgreSQL** trong Docker, hoặc hạn mức miễn phí của nhà cung cấp | Miễn phí |
| 8 | Hàng đợi | **Redis** trong Docker, hoặc hạn mức miễn phí | Miễn phí |
| 9 | Hosting | **25 hosting do AZDIGI tài trợ, 3 tháng**, theo poster cuộc thi | Đủ cho cả cuộc thi |
| 10 | Kênh tin nhắn chính | **Telegram Bot API** | **Miễn phí hoàn toàn**, duyệt tức thì |
| 11 | Kênh tin nhắn Zalo | Zalo OA nếu hạn mức miễn phí đủ dùng | ⚠️ **Không chắc chắn miễn phí.** Tin ngoài cửa sổ tương tác và tin ZNS có thể tính phí. **Phải tự kiểm tra.** Đây là lý do kênh tin nhắn có ba hiện thực |
| 12 | Kho mã nguồn và CI | **GitHub công khai**, Actions không giới hạn phút cho repo công khai | Miễn phí, và repo công khai phù hợp việc thể lệ ưu tiên mã nguồn mở |
| 13 | Tên miền | Tên miền phụ miễn phí của nền tảng triển khai | Miễn phí |
| 14 | Thiết bị và mã QR | Điện thoại của đội, QR sinh tại chỗ in trên giấy A4 | 0 đồng |

**Kết luận:** rủi ro chi phí duy nhất là dòng 11. Vì kênh tin nhắn đã trừu tượng hoá, **đổi sang Telegram là đổi một biến môi trường**, không phải sửa nghiệp vụ.

## 10.4. Bộ định tuyến nhà cung cấp miễn phí

```python
# packages/agents/src/ca_agents/router.py
NHA_CUNG_CAP = [
    {"ten": "groq",       "loai": "text",  "rpm": 30,   "rpd": 14400},
    {"ten": "gemini",     "loai": "multi", "rpm": None, "rpd": None},  # điền sau khi tra
    {"ten": "openrouter", "loai": "text",  "rpm": 20,   "rpd": 50},
    {"ten": "ollama",     "loai": "local", "rpm": None, "rpd": None},  # cuối, không giới hạn
]
# 1. Đếm số lần gọi mỗi nhà cung cấp bằng bộ đếm cửa sổ trượt
# 2. Gần hạn mức thì CHUYỂN TRƯỚC, không chờ tới lúc bị chặn
# 3. Hết nhà cung cấp trực tuyến thì chuyển Ollama cục bộ
# 4. Ollama cũng lỗi thì trả "tu_choi" và bộ điều phối ĐẨY LÊN NGƯỜI
# 5. Mọi lần gọi ghi vào agent_results: nhà cung cấp nào, token bao nhiêu
```

Tất cả nhà cung cấp trong danh sách tương thích SDK kiểu OpenAI, nên đổi là đổi tên và địa chỉ điểm cuối. Một bài kiểm thử chạy cùng một nhiệm vụ qua cả bốn hiện thực để bảo đảm điều đó.

**Bước 4 là bước quan trọng nhất:** khi hết mọi hạn mức, hệ thống **không im lặng bỏ qua và không đoán**. Nó đẩy lên người. **Chi phí 0 đồng không bao giờ được đổi bằng độ đúng.**


---
---

# PHẦN II — THỰC THI

# 11. Codebase sạch

## 11.1. Cây thư mục

```
nhip-quan/
├── apps/
│   ├── api/                            # [B] FastAPI, kiến trúc phân tầng
│   │   ├── src/ca_api/
│   │   │   ├── domain/                 # thực thể, quy tắc thuần, KHÔNG import hạ tầng
│   │   │   │   ├── entities/           # NhanVien, Ca, Lich, YeuCauDoiCa, Phieu, ViecTreo
│   │   │   │   ├── values/             # KhoangThoiGian, BoKyNang, NoCongBang
│   │   │   │   └── policies/           # quy tắc tuân thủ, quy tắc tự duyệt
│   │   │   ├── application/            # use case + cổng
│   │   │   │   └── ports/              # SolverPort, AgentPort, MessagePort, ClockPort
│   │   │   ├── orchestration/          # [B] BỘ ĐIỀU PHỐI, tất định, người ghi duy nhất
│   │   │   │   ├── state_machine.py    #   máy trạng thái phiên
│   │   │   │   ├── dispatcher.py       #   phát nhiệm vụ song song, giới hạn đồng thời
│   │   │   │   ├── idempotency.py      #   khoá theo nội dung, bộ nhớ đệm
│   │   │   │   ├── budget.py           #   trần số lần gọi và trần token mỗi phiên
│   │   │   │   └── replay.py           #   phát lại một phiên từ vết đã lưu
│   │   │   ├── infrastructure/         # adapter: db, solver, agents, messaging, jobs
│   │   │   └── interfaces/http/
│   │   ├── migrations/                 # Alembic
│   │   └── tests/{unit,integration}
│   └── web/                            # [D] Next.js, PWA
│       ├── src/features/               # chia theo TÍNH NĂNG, không theo loại tệp
│       │   ├── roster-grid/  swap-market/  fairness/  explain/
│       │   ├── constraints-inbox/  run-form/  today/  playbook/  sop-chat/
│       │   └── agent-trace/
│       ├── src/shared/{ui,api,lib}
│       └── tests/{unit,e2e}
├── packages/
│   ├── contracts/                      # [cả 4 duyệt] nguồn sự thật về kiểu dữ liệu
│   │   ├── src/ca_contracts/           #   Pydantic v2
│   │   ├── schema/                     #   JSON Schema sinh ra
│   │   └── ts/                         #   TypeScript sinh ra
│   ├── solver/                         # [A] CP-SAT, thư viện THUẦN
│   │   ├── src/ca_solver/
│   │   │   ├── model.py
│   │   │   ├── constraints/            #   c01..c06 cứng, s01..s05 mềm, MỘT TỆP MỘT RÀNG BUỘC
│   │   │   ├── objective.py  explain.py
│   │   │   └── benchmarks/             #   8 ca theo quy mô
│   │   └── tests/
│   ├── opsengine/                      # [A] máy quy trình vận hành, thư viện THUẦN
│   │   └── src/ca_ops/{template,phieu,buoc,viec_treo,escalate,tieu_thu}
│   ├── playbook/                       # [A] CẨM NANG SỐNG, thư viện THUẦN
│   │   └── src/ca_playbook/{so_lan_sua,tim_mau,tap_su,theo_doi}
│   ├── gates/                          # [A] 6 cổng kiểm chứng, thư viện THUẦN
│   │   └── src/ca_gates/{vf_schema,vf_trace,vf_conf,vf_conflict,vf_num,vf_rule}
│   └── agents/                         # [C] 9 agent lô 1, thư viện THUẦN
│       └── src/ca_agents/
│           ├── runtime.py  router.py   #   khung chạy + định tuyến nhà cung cấp miễn phí
│           ├── ag_tkb/  ag_msg/  ag_handover/  ag_waste/  ag_voc/
│           ├── ag_sop/  ag_explain/  ag_brief/  ag_rule/
│           └── prompts/                #   prompt là TỆP có phiên bản
├── infra/
│   ├── docker/{compose.yml,compose.dev.yml}
│   └── templates/                      # [D] mẫu phiếu YAML
│       └── {mo_quan,dong_quan,ban_giao_ca}.yaml
├── docs/
│   ├── adr/                            # 11 quyết định kiến trúc
│   ├── runbook-demo.md
│   ├── THIRD_PARTY.md
│   └── GIOI-HAN-PHUONG-PHAP.md
├── .github/{workflows,ISSUE_TEMPLATE,PULL_REQUEST_TEMPLATE.md,CODEOWNERS,labeler.yml}
├── Makefile
├── pyproject.toml                      # workspace uv, ruff, mypy, pytest
└── README.md
```

**Mỗi agent một thư mục, mỗi ràng buộc một tệp.** Cách này làm cho bảng ràng buộc trong tài liệu dự thi tự khớp với mã nguồn, và làm cho việc bật tắt từng ràng buộc để gỡ lỗi trở nên tầm thường.

## 11.2. Năm quy tắc kiến trúc, mỗi cái có kiểm thử tự động

| # | Quy tắc | Kiểm thử |
|---|---|---|
| 1 | `packages/*` là thư viện **thuần**: không import FastAPI, SQLAlchemy, requests | Duyệt AST |
| 2 | `domain/` không import `infrastructure/`. Chiều phụ thuộc hướng vào trong | Duyệt AST |
| 3 | Mọi thứ đi ra ngoài qua **cổng**, kể cả thời gian. Không `datetime.now()` trong nghiệp vụ | Duyệt AST |
| 4 | **Agent không gọi agent, không ghi DB, không quyết định luồng** | Duyệt AST |
| 5 | Mỗi agent có `PHAM_VI.md` đủ chín thuộc tính | Duyệt hệ thống tệp |

```python
# packages/agents/tests/test_architecture.py
import ast, pathlib

CAM = ("sqlalchemy", "psycopg", "redis", "fastapi", "ca_api", "ca_gates")

def test_agent_khong_goi_agent_va_khong_ghi_db():
    goc = pathlib.Path("src/ca_agents")
    ten_agent = {d.name for d in goc.iterdir() if d.is_dir() and d.name.startswith("ag_")}
    for tep in goc.rglob("*.py"):
        hien_tai = next((p for p in tep.parts if p.startswith("ag_")), None)
        for node in ast.walk(ast.parse(tep.read_text(encoding="utf-8"))):
            ten = ""
            if isinstance(node, ast.Import):
                ten = " ".join(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                ten = node.module or ""
            for x in CAM:
                assert x not in ten, f"{tep} không được import {x}"
            for khac in ten_agent - {hien_tai}:
                assert khac not in ten, f"{tep} không được gọi agent khác: {khac}"

def test_moi_agent_co_pham_vi():
    for d in pathlib.Path("src/ca_agents").iterdir():
        if d.is_dir() and d.name.startswith("ag_"):
            assert (d / "PHAM_VI.md").exists(), f"{d.name} thiếu PHAM_VI.md"
```

Bài kiểm thử này đắt đúng một lần viết, và nó chặn được việc ai đó trong đội, vào tuần 5 lúc đang gấp, cho một agent gọi agent khác cho nhanh.

## 11.3. Mười quy ước không tranh luận lại

1. Tên tiếng Việt không dấu cho khái niệm nghiệp vụ, tiếng Anh cho khái niệm kỹ thuật
2. Hàm dài tối đa 40 dòng
3. Không tham số kiểu boolean điều khiển luồng
4. Không `Any` trong `packages/*` và `domain/`; `mypy --strict` bắt điều này
5. Ngoại lệ nghiệp vụ là lớp riêng, chỉ tầng HTTP dịch thành mã trạng thái
6. **Không số hoặc chuỗi trần trong logic nghiệp vụ.** Tham số tuân thủ ở cấu hình, mã lý do ở từ điển, mẫu phiếu ở YAML
7. Thời gian luôn có múi giờ
8. Mọi truy vấn cơ sở dữ liệu nằm trong `infrastructure/db`
9. Log có cấu trúc, không log câu văn
10. Mỗi tệp một khái niệm

## 11.4. Kim tự tháp kiểm thử, mục tiêu 215 bài

| Tầng | Số bài | Chạy trong | Ai viết |
|---|---|---|---|
| Đơn vị | ~118 | dưới 30 giây | Cả 4 |
| Tầng agent và điều phối | 32 | dưới 60 giây | B, A, C |
| Tầng vận hành | 25 | dưới 45 giây | A, B, D |
| Cẩm nang sống | 10 | dưới 30 giây | A |
| Tích hợp | ~30 | dưới 3 phút | B |
| Đầu cuối | 8 luồng | dưới 5 phút | D |
| Kiểm chuẩn solver | 8 ca | dưới 5 phút | A |
| Đánh giá agent | 4 bộ mẫu vàng | dưới 3 phút | C |

**Tám luồng đầu cuối**, ba luồng quan trọng nhất:

- **Thất bại đóng:** ảnh mờ và hai tin nhắn trái nhau. Cổng đẩy lên người, phiên **không** chuyển sang trạng thái giải, người xử xong thì đi tiếp
- **Tranh chấp bù ca:** năm người bấm nhận cùng lúc, đúng một người được
- **Học một luật:** sửa ba lần cùng mẫu, luật được đề xuất, qua tập sự, người duyệt, hệ thống áp dụng đúng ở lần thứ tư

## 11.5. Makefile: mọi lệnh chạy bằng một dòng

```makefile
setup:      ## cài toàn bộ phụ thuộc và móc pre-commit
contracts:  ## sinh JSON Schema, TypeScript, client từ OpenAPI
dev:        ## chạy api + web + postgres + redis + worker
test:       ## toàn bộ kiểm thử
test-unit:  ## chỉ đơn vị, chạy dưới 30 giây
lint:       ## kiểm lỗi và định dạng
bench:      ## bộ kiểm chuẩn solver, in bảng
eval:       ## đánh giá 9 agent lô 1 trên bộ mẫu vàng, in bảng
ab:         ## thí nghiệm một agent xử lô so với N agent song song
replay:     ## make replay PHIEN=<id> — phát lại một phiên từ vết
budget:     ## in số lần gọi mô hình và token của N phiên gần nhất
seed:       ## nạp 25 nhân viên, 21 ca, 8 tuần lịch sử
demo:       ## nạp bộ dữ liệu demo và mở trình duyệt
demo-reset: ## đưa về trạng thái đầu của kịch bản demo, dưới 10 giây
```

`make replay` biến việc gỡ lỗi hệ nhiều thành phần từ bất khả thi thành việc thường ngày. `make budget` là lệnh chạy mỗi tuần để biết chi phí đang đi đâu, thay vì phát hiện lúc hết hạn mức.

---

# 12. GitHub: bốn người, bốn vùng nhánh

## 12.1. Một điều phải nói trước về nhánh cá nhân

Bốn nhánh cá nhân sống suốt tám tuần **là cách sai**, vì bốn nhánh sống lâu song song tạo ra xung đột hợp nhất tích luỹ, và đến tuần 5 việc gộp chúng lại tốn nhiều ngày hơn cả việc viết mã.

Cách đúng là **bốn vùng nhánh**: mỗi người sở hữu một tập tiền tố tên nhánh, cộng nhánh nháp cá nhân không bao giờ hợp nhất trực tiếp. Kết quả vẫn là mỗi người có không gian riêng, nhưng nhánh nào cũng sống dưới ba ngày.

## 12.2. Bảng phân vùng nhánh, có công việc thật cho cả bốn người

| Người | Vai trò | Tiền tố nhánh sở hữu | Nhánh ví dụ trong 8 tuần |
|---|---|---|---|
| **A** | Tối ưu hoá, cổng kiểm chứng, máy quy trình, cẩm nang | `feat/solver-*`<br>`feat/gates-*`<br>`feat/ops-*`<br>`feat/playbook-*` | `feat/solver-rang-buoc-cung-c01-c03`<br>`feat/solver-so-no-cong-bang`<br>`feat/gates-vf-rule`<br>`feat/ops-may-quy-trinh`<br>`feat/ops-so-tieu-thu`<br>`feat/playbook-che-do-tap-su` |
| **B** | Backend, điều phối, nền tảng, CI | `feat/api-*`<br>`feat/orc-*`<br>`ci/*`<br>`chore/infra-*` | `ci/11-cong-chat-luong`<br>`feat/orc-may-trang-thai`<br>`feat/orc-idempotency`<br>`feat/api-vong-doi-lich`<br>`feat/api-cho-doi-ca`<br>`feat/api-bu-ca-khan` |
| **C** | Mười agent, dữ liệu, bộ định tuyến, kênh tin nhắn | `feat/agents-*`<br>`feat/router-*`<br>`feat/eval-*` | `feat/router-nha-cung-cap-mien-phi`<br>`feat/agents-ag-tkb`<br>`feat/agents-ag-msg-hai-bac`<br>`feat/agents-ag-rule`<br>`feat/agents-ag-sop`<br>`feat/eval-bo-mau-vang` |
| **D** | Frontend, mẫu phiếu, trình bày | `feat/web-*`<br>`feat/tpl-*`<br>`docs/*` | `feat/web-luoi-lich-tuan`<br>`feat/web-chay-phieu-dien-thoai`<br>`feat/web-cam-nang`<br>`feat/web-vet-agent`<br>`feat/tpl-mo-quan-dong-quan`<br>`docs/runbook-demo` |

**Nháp cá nhân:** `wip/a/...`, `wip/b/...`, `wip/c/...`, `wip/d/...`. Đây là nhánh riêng để thử nghiệm, **không bao giờ mở pull request từ nhánh này vào `main`**. Muốn đưa vào thì rebase sang một nhánh `feat/` đúng vùng.

## 12.3. Tệp CODEOWNERS

```
# .github/CODEOWNERS
/packages/solver/                    @nguoi-A
/packages/gates/                     @nguoi-A
/packages/opsengine/                 @nguoi-A
/packages/playbook/                  @nguoi-A
/packages/agents/                    @nguoi-C
/apps/api/                           @nguoi-B
/apps/web/                           @nguoi-D
/infra/templates/                    @nguoi-D
/infra/                              @nguoi-B
/.github/                            @nguoi-B
/docs/                               @nguoi-D

# Bộ điều phối: B sở hữu, A phải duyệt cùng,
# vì đây là chỗ quyết định tính tất định của toàn hệ thống
/apps/api/src/ca_api/orchestration/  @nguoi-B @nguoi-A

# Hợp đồng dữ liệu: cả bốn người phải duyệt
/packages/contracts/                 @nguoi-A @nguoi-B @nguoi-C @nguoi-D
```

## 12.4. Quy trình nhánh và bảo vệ `main`

```
main  ─────●───────●───────●───────●───────●───────●──────▶  luôn xanh, luôn demo được
            \     /         \     /         \     /
             ●───●           ●───●           ●───●          nhánh feat, sống < 3 ngày
                                    ●────────────▶ release/semifinal  (tuần 6)
                                              ●──▶ release/final      (tuần 8)
```

| Quy tắc | Giá trị |
|---|---|
| Nhánh `feat` sống tối đa | **3 ngày.** Quá thì tách nhỏ task, không xin gia hạn |
| Số nhánh mở đồng thời mỗi người | Tối đa 2 |
| Cập nhật từ `main` | `git pull --rebase origin main` hằng ngày. **Không merge `main` vào nhánh** |
| Cách vào `main` | **Squash merge**, để lịch sử `main` là một dòng thẳng |
| Nhánh phát hành | Hai nhánh, tuần 6 và tuần 8, chỉ nhận `cherry-pick` bản sửa lỗi |
| Thẻ | `v0.1.0-semifinal` và `v1.0.0-final`, mỗi thẻ có ảnh Docker xây từ đúng thẻ đó |

**Bảo vệ `main`:** yêu cầu pull request · **1 lượt duyệt từ CODEOWNERS của vùng bị chạm** · loại bỏ lượt duyệt cũ khi có commit mới · toàn bộ cổng CI xanh · nhánh cập nhật với `main` · giải quyết hết bình luận · chặn force push và chặn xoá nhánh · **áp dụng cả cho người quản trị**.

**Conventional Commits**, có `commitlint` chặn:

```
<loai>(<vung>): <mô tả ở thể mệnh lệnh, không dấu chấm cuối>

loai: feat | fix | refactor | perf | test | docs | chore | ci
vung: solver | gates | ops | playbook | api | orc | agents | router | web | tpl | contracts | infra
```

**Chuẩn duyệt pull request**, người duyệt dừng ở lỗi đầu tiên tìm được:

1. Có mô tả **vì sao**, không chỉ **cái gì**?
2. Có kiểm thử cho hành vi mới, và kiểm thử đỏ nếu xoá mã mới?
3. Có phá quy tắc kiến trúc nào ở mục 11.2?
4. Có số trần, chuỗi trần, hay `Any` mới?
5. Chạm hợp đồng mà chưa chạy `make contracts`?
6. Thêm thư viện mà chưa ghi `THIRD_PARTY.md`?
7. Chạm agent mà chưa nâng phiên bản prompt và chưa chạy `make eval`?
8. Chạm điều phối hoặc lõi mà kiểm thử tất định còn xanh không?

Ba mức bình luận: `[chặn]` phải sửa mới merge · `[nên]` người viết quyết định · `[hỏi]` chỉ để hiểu.

## 12.5. Mười một cổng CI

| # | Cổng | Chạy khi | Đỏ khi |
|---|---|---|---|
| 1 | Kiểm lỗi và kiểu | Luôn | `ruff`, `mypy --strict`, `eslint`, `tsc` có lỗi |
| 2 | Kiểm thử đơn vị | Luôn | Bài đỏ, hoặc độ phủ `packages/*` và `domain/` dưới **85%** |
| 3 | Kiểm thử tích hợp | Luôn | Postgres và Redis dựng bằng dịch vụ, migration hoặc bài tích hợp đỏ |
| 4 | **Kiểm thử kiến trúc** | Luôn | Vi phạm một trong năm quy tắc ở 11.2 |
| 5 | Kiểm chuẩn solver | Chạm `packages/solver` | Thời gian giải tăng quá **20%** so với `main` |
| 6 | Đánh giá agent | Chạm `packages/agents` | Độ chính xác tụt dưới ngưỡng, hoặc prompt đổi mà không nâng phiên bản |
| 7 | Kiểm thử web | Chạm `apps/web` | `vitest` đỏ |
| 8 | Kiểm thử đầu cuối | `main` và nhánh phát hành | Playwright đỏ trên 3 luồng chính |
| 9 | Xây ảnh Docker | Luôn | Không xây được |
| 10 | **Không gọi mô hình thật trong kiểm thử** | Luôn | Bài kiểm thử nào mở kết nối ra ngoài |
| 11 | **Kiểm tra mẫu phiếu YAML** | Chạm `infra/templates` | YAML sai lược đồ, hoặc tham chiếu mặt hàng không tồn tại |

**Cổng 5, 6 và 10 là ba cổng làm nên sự khác biệt.** Cổng 5 và 6 biến chất lượng thuật toán và chất lượng mô hình thành thứ được máy kiểm ở mỗi lần thay đổi. Cổng 10 quan trọng hơn nó trông: nếu kiểm thử gọi mô hình thật thì CI vừa tốn hạn mức, vừa chậm, vừa **thất thường**, và một bộ kiểm thử thất thường sẽ bị cả đội bỏ qua trong hai tuần. Cách làm: đặt `CA_AGENT_MODE=replay` và một fixture trong `conftest.py` vá socket để ném lỗi nếu ai gọi ra ngoài.

---

# 13. Phân công: 25,5 ngày mỗi người

Sức chứa: 4 người × 6 tuần × 4,5 ngày hiệu quả = **108 ngày người**.

## 13.1. A — Tối ưu hoá, cổng kiểm chứng, máy quy trình, cẩm nang

| Nhóm việc | Ngày |
|---|---|
| Bộ giải: khung mô hình, 6 ràng buộc cứng, 5 ràng buộc mềm | 3,5 |
| **Sổ nợ công bằng 4 chiều, tối thiểu hoá nợ lớn nhất** | 2,0 |
| Sinh mã lý do cho từng phân công, và từ điển mã lý do | 1,5 |
| Ghim ô người sửa tay, giải lại phần còn lại | 0,5 |
| Bộ kiểm chuẩn 8 ca theo quy mô, script so sánh hồi quy | 1,0 |
| **Máy quy trình vận hành**: mẫu phiếu, bước, minh chứng, việc treo, escalate | 3,5 |
| **Sổ tiêu thụ suy ra từ kiểm kê** theo công thức mục 4.3 | 1,0 |
| Cơ chế chống tích khống và bảng dấu hiệu | 1,5 |
| **Sáu cổng kiểm chứng** | 3,5 |
| **Cẩm nang sống**: bảng ghi nhận lần sửa, tìm mẫu, chế độ tập sự, theo dõi và tự tắt | 4,0 |
| **Ánh xạ luật đã duyệt thành tham số của lõi**: 5 loại luật thành ràng buộc bộ giải, bước phiếu, hoặc ngưỡng tồn. Đây là bước 7 của vòng đời | 0,5 |
| Nửa tầng domain và policy tuân thủ, làm cùng B | 0,75 |
| Bộ dữ liệu mẫu: 25 nhân viên, 21 ca, 8 tuần lịch sử | 1,0 |
| Kiểm thử tầng vận hành và cẩm nang, và kiểm thử tất định của lõi | 1,0 |
| Phần A của tài liệu giới hạn phương pháp và bảng kết quả tổng hợp | 0,25 |
| **Tổng** | **25,5** |

## 13.2. B — Backend, điều phối, nền tảng, CI

| Nhóm việc | Ngày |
|---|---|
| Khởi tạo monorepo, ruff, mypy strict, eslint, prettier, pre-commit | 1,0 |
| **CI 11 cổng** | 1,5 |
| Bảo vệ nhánh, CODEOWNERS, mẫu pull request và issue, commitlint, labeler | 0,5 |
| Docker Compose 5 dịch vụ | 0,5 |
| **Hợp đồng dữ liệu** và máy chủ giả để D không bị chặn | 1,5 |
| **Bộ điều phối**: máy trạng thái, phát nhiệm vụ song song, idempotency, trần ngân sách, phát lại phiên | 4,5 |
| Lược đồ cơ sở dữ liệu và migration Alembic | 1,5 |
| Nửa tầng domain và policy tuân thủ, làm cùng A | 0,75 |
| Xác thực và ba vai trò | 1,0 |
| Vòng đời lịch: nháp, đang giải, chờ duyệt, đã công bố, đã đóng | 1,5 |
| Cổng solver chạy nền, theo dõi tiến độ, hết thời gian trả lời giải tốt nhất | 1,5 |
| Cổng agent và luồng phê duyệt ràng buộc trích xuất | 1,0 |
| Công bố lịch, gửi tin cho từng người, xuất tệp ICS | 1,0 |
| **Chợ đổi ca ba nhánh** | 2,0 |
| Điểm danh QR một lần, không dùng lại được | 1,0 |
| Nhắc việc hai mốc và escalate hai cấp, dùng cổng thời gian | 1,5 |
| **Bù ca khẩn và khoá tranh chấp ở tầng cơ sở dữ liệu** | 1,0 |
| Nhật ký chỉ ghi thêm cho mọi hành động thay đổi lịch và phiếu | 0,5 |
| **API đọc vết agent** cho màn hình của D: đồ thị nhiệm vụ, kết quả từng cổng, nhà cung cấp và token mỗi lần gọi | 0,5 |
| **Cổng thời gian tiêm được** và bộ chạy việc định kỳ, để nhắc việc và kiểm thử tất định lặp lại được | 0,5 |
| 11 tệp ADR và `THIRD_PARTY.md` | 0,75 |
| **Tổng** | **25,5** |

## 13.3. C — Mười agent, dữ liệu, bộ định tuyến, kênh tin nhắn

| Nhóm việc | Ngày |
|---|---|
| Thu 50 ảnh thời khoá biểu và 200 tin nhắn thật, **hai người gán nhãn độc lập** | 2,0 |
| Khung chạy agent, prompt có phiên bản, bộ nhớ đệm theo nội dung | 2,0 |
| **Bộ định tuyến bốn nhà cung cấp miễn phí** | 1,0 |
| AG-TKB đọc ảnh thời khoá biểu | 2,5 |
| AG-MSG phân loại ý định, **mô hình hai bậc** | 2,0 |
| AG-HANDOVER đọc bàn giao thành SBAR và việc treo | 1,5 |
| AG-WASTE đọc ghi chú hao hụt | 1,0 |
| AG-VOC đọc phản hồi khách, nối vào việc treo | 1,0 |
| **AG-SOP** hỏi đáp quy trình, chỉ trả lời từ mẫu phiếu và cẩm nang | 1,5 |
| AG-EXPLAIN dịch mã lý do thành câu | 1,0 |
| AG-BRIEF bản tin sáng cho chủ | 0,75 |
| **AG-RULE** đề xuất luật từ lần sửa | 1,5 |
| Kiểm thử kiến trúc agent, 4 bộ mẫu vàng, `make eval` | 1,5 |
| **Thí nghiệm A/B**: một agent xử lô so với N agent song song | 1,0 |
| Cổng tin nhắn ba hiện thực: Telegram, Zalo OA, console | 1,5 |
| Nhập lịch cũ và danh sách nhân viên từ Excel và Google Sheets | 1,5 |
| Ngưỡng tồn trong phiếu và cảnh báo hết hàng | 0,5 |
| Hộp thư ràng buộc: giao diện phê duyệt đầu ra của agent | 1,5 |
| Phần C của bảng kết quả tổng hợp | 0,25 |
| **Tổng** | **25,5** |

## 13.4. D — Frontend, mẫu phiếu, trình bày

| Nhóm việc | Ngày |
|---|---|
| Khung Next.js, PWA, hệ thống thiết kế, sinh client từ OpenAPI | 1,5 |
| **Lưới lịch tuần cho quản lý**: kéo thả, ghim ô, chặn vi phạm kèm giải thích tại chỗ | 3,0 |
| Tải ảnh thời khoá biểu và màn hình xác nhận đặt cạnh ảnh gốc | 1,5 |
| **Giao diện nhân viên trên điện thoại**: lịch của tôi, nhả ca, nhận ca | 2,0 |
| **Giao diện chạy phiếu trên điện thoại**, một tay, chụp ảnh một lần bấm | 2,5 |
| Bảng công bằng: số dư bốn chiều, so với trung bình nhóm, **không xếp hạng tên** | 1,5 |
| **Giao diện Cẩm nang quán** | 1,0 |
| Bảng tình trạng quán hôm nay cho chủ | 1,5 |
| Màn hình xem vết agent: đồ thị nhiệm vụ, kết quả từng cổng | 1,5 |
| Giao diện hỏi đáp SOP | 0,5 |
| **Ba mẫu phiếu YAML, lấy từ quán thật** bằng cách ngồi xem một ca | 1,5 |
| Kiểm thử đầu cuối 8 luồng bằng Playwright | 1,5 |
| Khả năng dùng được: cỡ chữ, tương phản, dùng một tay, trạng thái tải và lỗi | 0,5 |
| **Đo hiện trạng 7 con số tại quán** | 1,0 |
| Tài liệu mô tả hệ thống theo yêu cầu thể lệ | 1,5 |
| `docs/runbook-demo.md` | 1,0 |
| Video dưới 5 phút và slide | 1,5 |
| Xuất báo cáo PDF kiểm toán công bằng | 0,5 |
| **Tổng** | **25,5** |

## 13.5. Việc làm chung và tổng khối lượng

| Việc | Ngày |
|---|---|
| Buổi chốt năm hợp đồng dữ liệu và ba ADR nền, cả bốn người | 1,0 |
| Luyện phản biện chéo 20 câu ở mục 17 | 1,0 |

| | Ngày | Còn trống trên 27 |
|---|---|---|
| A | 25,5 | 1,5 |
| B | 25,5 | 1,5 |
| C | 25,5 | 1,5 |
| D | 25,5 | 1,5 |
| Làm chung | 2,0 | |
| **Tổng** | **104,0** / 108 | **Đệm 4,0 ngày** |

**Bốn người chia đúng đều nhau, mỗi người còn trống 1,5 ngày.**

## 13.6. Lô 2: đã thiết kế và tính chi phí, chưa xây

| Việc | Ngày | Điều kiện làm |
|---|---|---|
| AG-FORECAST dự báo nhu cầu và đề xuất ngưỡng tồn | 2,0 | Cần ít nhất 3 tuần dữ liệu sổ tiêu thụ |
| AG-INVOICE đọc phiếu giao hàng và hạn dùng | 1,5 | |
| AG-SHELF đọc ảnh kệ hàng | 1,5 | |
| AG-MENUOPS chỉ ra món gây hao hụt cao | 1,0 | Cần dữ liệu hao hụt của lô 1 |
| Sổ tồn đầy đủ có lịch sử và xu hướng | 1,0 | |
| **Tổng lô 2** | **7,0** | **Chỉ làm nếu cuối sprint 5 vùng đệm còn trên 4 ngày** |

Vì tất cả đều là **cấu hình hoặc agent trên hạ tầng đã có**, thêm sau rất rẻ. Đưa vào lộ trình sau cuộc thi là hợp lý, và **nói ra điều đó khi thuyết trình cho thấy đội biết quản lý phạm vi**.

## 13.7. Dây báo động

Vùng đệm 4,0 ngày là **dưới ngưỡng an toàn mà chính tài liệu này đặt ra là 5 ngày**. Nên có ba luật cứng:

1. Mỗi buổi mở sprint, trưởng nhóm đối chiếu ngày đã dùng với ngày còn lại và công bố số đệm còn lại
2. **Đệm xuống dưới 2 ngày thì cắt ngay** theo thứ tự: AG-BRIEF, AG-VOC, màn hình xem vết agent
3. **Không ai được thêm bất kỳ tính năng nào ngoài danh mục.** Trưởng nhóm là người duy nhất mở được danh mục, và chỉ mở bằng cách cắt một thứ khác ra, có ghi ADR

---

# 14. Kế hoạch tám sprint

## 14.1. Cách đọc kế hoạch này

Tám sprint, mỗi sprint một tuần. **Sprint 1 đến 6 là giai đoạn xây dựng**, đúng 108 ngày người sức chứa, đã lập kế hoạch 104,0. **Sprint 7 và 8 là giai đoạn hoàn thiện**, thêm 36 ngày người **không lập kế hoạch tính năng nào**. Đó mới là vùng đệm thật của dự án, và nó lớn hơn nhiều con số 4,0 ngày ở mục 13.

Bốn luật của mọi sprint:

1. Mỗi sprint có **đúng một mục tiêu** phát biểu được thành một câu
2. Mỗi sprint có **đúng một thứ chiếu được lên màn hình** cho người ngoài đội xem. Không có thứ đó thì sprint coi như trượt, dù mã nguồn đã viết xong
3. Mỗi sprint có **cổng ra** là danh sách điều kiện kiểm được bằng mắt hoặc bằng lệnh. Chưa qua cổng thì không mở sprint sau, chỉ được cắt phạm vi
4. Sức chứa mỗi người mỗi sprint là **4,5 ngày**. Không ai được lập kế hoạch quá con số đó

**Một điều phải nói rõ về cách tính:** hai buổi làm chung tổng 2,0 ngày người đã nằm trong 104,0, dù buổi thứ hai diễn ra ở sprint 7. Đây là cách tính thận trọng, cố ý đưa việc của tuần 7 vào ngân sách 6 tuần, không phải thiếu sót.

**Bốn nhóm việc ở mục 13 được cố ý chia ra nhiều sprint**, nên khi đối chiếu hai mục sẽ thấy tên hơi khác nhau. Tổng số ngày không đổi:

| Nhóm việc ở mục 13 | Ngày | Chia ra |
|---|---|---|
| A · Bộ giải | 3,5 | 2,5 ở sprint 1 là 6 ràng buộc cứng, 1,0 ở sprint 2 là 5 ràng buộc mềm |
| A · Sáu cổng kiểm chứng | 3,5 | 1,5 ở sprint 2 · 1,0 và 0,5 ở sprint 4 · 0,5 ở sprint 5, vì VF-RULE chỉ cần khi có cẩm nang |
| A · Cẩm nang sống | 4,0 | **0,5 ở sprint 3 là bảng ghi nhận lần sửa** · 3,5 ở sprint 5 là phần còn lại |
| B · Bộ điều phối | 4,5 | 3,0 ở sprint 3 · 1,5 ở sprint 5 là trần ngân sách và phát lại phiên |

Trước sprint 1 có **tuần 0**, và tuần 0 không tiêu ngày người xây dựng nào ngoài các việc đã tính ở mục 18.1.

## 14.2. Sprint 1 — Nền và hợp đồng

> **Mục tiêu: từ cuối tuần 1, không ai bị chặn bởi ai.**

**Chiếu được:** trên một máy trống, `git clone && make demo` chạy ra một trang web đăng nhập được, và máy chủ giả trả về đủ dữ liệu của cả năm hợp đồng. Chưa có tính năng nào thật.

| Người | Việc | Ngày |
|---|---|---|
| A | Bộ dữ liệu mẫu 25 nhân viên, 21 ca, 8 tuần lịch sử | 1,0 |
| A | Nửa tầng domain và policy tuân thủ | 0,75 |
| A | Bộ giải phần 1: khung mô hình và 6 ràng buộc cứng | 2,5 |
| B | Khởi tạo monorepo, ruff, mypy strict, eslint, prettier, pre-commit | 1,0 |
| B | CI 11 cổng | 1,5 |
| B | Năm hợp đồng dữ liệu và máy chủ giả | 1,5 |
| C | Thu 50 ảnh thời khoá biểu và 200 tin nhắn thật, hai người gán nhãn độc lập | 2,0 |
| C | Khung chạy agent, prompt có phiên bản, bộ nhớ đệm theo nội dung | 2,0 |
| D | Khung Next.js, PWA, hệ thống thiết kế, sinh client từ OpenAPI | 1,5 |
| D | **Đo hiện trạng 7 con số tại quán, và ngồi xem trọn một ca mở quán** | 1,0 |
| D | Ba mẫu phiếu YAML viết từ ca đã ngồi xem | 1,5 |
| Chung | Buổi chốt năm hợp đồng dữ liệu và ba ADR nền, 2 giờ mỗi người | 1,0 |

**Cổng ra sprint 1**, năm điều kiện:

1. Năm hợp đồng dữ liệu đã hợp nhất vào `main`, có kiểm thử lược đồ
2. CI 11 cổng xanh trên `main` và trên một pull request thử
3. `make demo` chạy được trên máy của cả bốn người
4. Ba ADR nền đã hợp nhất: ADR-001 monorepo, ADR-002 điều phối tất định, ADR-003 hợp đồng dữ liệu trước mã nguồn
5. **Ba mẫu phiếu YAML lấy từ quán thật, không phải do đội tự nghĩ ra.** Không có điều kiện này thì cả tầng vận hành đứng trên cát

## 14.3. Sprint 2 — Mốc sinh tử thứ nhất

> **Mục tiêu: máy sinh ra một lịch tuần hợp lệ, không vi phạm một ràng buộc cứng nào.**

**Chiếu được:** chạy một lệnh, đọc bộ dữ liệu mẫu, in ra lịch tuần cho 25 người và **báo cáo kiểm tra ràng buộc với con số 0 ở mọi dòng vi phạm cứng**. Chưa cần giao diện, chiếu bằng terminal là đủ.

| Người | Việc | Ngày |
|---|---|---|
| A | Bộ giải phần 2: 5 ràng buộc mềm và hàm mục tiêu | 1,0 |
| A | Sổ nợ công bằng 4 chiều, tối thiểu hoá nợ lớn nhất | 2,0 |
| A | Ba cổng đầu: VF-SCHEMA, VF-TRACE, VF-CONF | 1,5 |
| B | Bảo vệ nhánh, CODEOWNERS, mẫu pull request và issue, commitlint, labeler | 0,5 |
| B | Lược đồ cơ sở dữ liệu và migration Alembic | 1,5 |
| B | Docker Compose 5 dịch vụ | 0,5 |
| B | Nửa tầng domain và policy tuân thủ | 0,75 |
| B | Xác thực và ba vai trò | 1,0 |
| C | **AG-TKB** đọc ảnh thời khoá biểu | 2,5 |
| C | Bộ định tuyến bốn nhà cung cấp miễn phí | 1,0 |
| C | Kiểm thử kiến trúc agent và bộ mẫu vàng thứ nhất | 1,0 |
| D | Lưới lịch tuần cho quản lý: kéo thả, ghim ô, chặn vi phạm kèm giải thích tại chỗ | 3,0 |
| D | Tải ảnh thời khoá biểu và màn hình xác nhận đặt cạnh ảnh gốc | 1,5 |

**Cổng ra sprint 2, đây là mốc sinh tử thứ nhất**, sáu điều kiện:

1. **Lịch tuần cho 25 người, 21 ca, 0 vi phạm ràng buộc cứng.** Kiểm bằng script độc lập với bộ giải, không tin lời bộ giải tự khai
2. Bộ giải trả kết quả **dưới 60 giây** trên bộ dữ liệu mẫu, hoặc trả nghiệm tốt nhất tìm được khi hết thời gian
3. Sổ nợ công bằng có kiểm thử tính chất: chạy 8 tuần liên tiếp, khoảng cách nợ lớn nhất không phình ra
4. AG-TKB đạt trên bộ mẫu vàng: **ghi lại con số thật, dù nó là bao nhiêu**. Con số này vào mục 18.2
5. Ba cổng đầu chạy được, và có một trường hợp cố tình cho ảnh mờ để chứng minh VF-CONF đẩy lên người
6. Giao diện lưới lịch đọc được lịch từ máy chủ giả

**Nếu trượt mốc này thì làm gì:** không cắt tính năng nào của sprint 3, mà **cắt số ràng buộc mềm từ 5 xuống 3** và ghi ADR. Ràng buộc cứng không bao giờ được cắt.

## 14.4. Sprint 3 — Tầng vận hành và tri thức bắt đầu được ghi

> **Mục tiêu: một phiếu chạy trọn vẹn trên điện thoại, và hệ thống bắt đầu ghi lại mọi lần con người sửa nó.**

**Chiếu được:** một người cầm điện thoại chạy hết phiếu mở quán, chụp một ảnh minh chứng, để lại một việc treo. Trên máy quản lý, việc treo hiện ra.

| Người | Việc | Ngày |
|---|---|---|
| A | Máy quy trình vận hành: mẫu phiếu, bước, minh chứng, việc treo, escalate | 3,5 |
| A | Ghim ô người sửa tay, giải lại phần còn lại | 0,5 |
| A | **Bảng ghi nhận lần sửa, tức bước 1 của vòng đời luật** | 0,5 |
| B | Bộ điều phối phần 1: máy trạng thái, phát nhiệm vụ song song, idempotency | 3,0 |
| B | Cổng agent và luồng phê duyệt ràng buộc trích xuất | 1,0 |
| B | Cổng thời gian tiêm được và bộ chạy việc định kỳ | 0,5 |
| C | **AG-MSG** phân loại 6 ý định, mô hình hai bậc | 2,0 |
| C | Cổng tin nhắn ba hiện thực: Telegram, Zalo OA, console | 1,5 |
| C | Nhập lịch cũ và danh sách nhân viên từ Excel, phần 1 | 1,0 |
| D | Giao diện chạy phiếu trên điện thoại, một tay, chụp ảnh một lần bấm | 2,5 |
| D | Giao diện nhân viên trên điện thoại: lịch của tôi, nhả ca, nhận ca | 2,0 |

**Vì sao bước 1 của vòng đời luật phải làm ở sprint 3, không phải sprint 5:** một luật cần **ít nhất 3 lần sửa cùng mẫu** làm bằng chứng. Nếu chỉ bắt đầu ghi nhận ở sprint 5 thì đến ngày bảo vệ sẽ không có luật nào đủ bằng chứng, và Cẩm nang sống thành một cái vỏ rỗng. **Ghi nhận phải chạy trước phần còn lại của cẩm nang đúng hai tuần.** Đây là ràng buộc thứ tự quan trọng nhất của cả kế hoạch.

**Cổng ra sprint 3**, năm điều kiện:

1. Một phiếu 20 bước chạy hết trên điện thoại thật, không phải trên trình giả lập
2. Ảnh minh chứng lưu được, và bảng dấu hiệu ghi lại thời gian giữa các bước
3. Bộ điều phối phát 8 nhiệm vụ song song, có kiểm thử idempotency: gọi hai lần cùng khoá thì chỉ ghi một lần
4. AG-MSG có ma trận nhầm lẫn trên 6 ý định, ghi lại con số thật
5. **Bảng ghi nhận lần sửa đã có dữ liệu thật**, tức đã có người sửa lịch và hệ thống đã lưu cặp trước và sau

## 14.5. Sprint 4 — Mốc sinh tử thứ hai

> **Mục tiêu: quán dùng thật. Không phải chạy thử, mà là lịch tuần và phiếu mở quán của tuần đó do hệ thống quản lý.**

**Chiếu được:** ảnh chụp màn hình điện thoại của một nhân viên thật đang chạy phiếu thật, và lịch tuần đang có hiệu lực tại quán.

| Người | Việc | Ngày |
|---|---|---|
| A | Cơ chế chống tích khống và bảng dấu hiệu | 1,5 |
| A | Sinh mã lý do cho từng phân công, và từ điển mã lý do | 1,5 |
| A | VF-CONFLICT | 1,0 |
| A | VF-NUM | 0,5 |
| B | Vòng đời lịch: nháp, đang giải, chờ duyệt, đã công bố, đã đóng | 1,5 |
| B | Cổng solver chạy nền, theo dõi tiến độ, hết thời gian trả lời giải tốt nhất | 1,5 |
| B | Công bố lịch, gửi tin cho từng người, xuất tệp ICS | 1,0 |
| B | Nhật ký chỉ ghi thêm cho mọi hành động thay đổi lịch và phiếu | 0,5 |
| C | **AG-HANDOVER** đọc bàn giao thành SBAR và việc treo | 1,5 |
| C | Hộp thư ràng buộc: giao diện phê duyệt đầu ra của agent | 1,5 |
| C | Nhập lịch cũ từ Excel, phần 2 | 0,5 |
| C | Ngưỡng tồn trong phiếu và cảnh báo hết hàng | 0,5 |
| C | Ba bộ mẫu vàng còn lại và `make eval` | 0,5 |
| D | Bảng công bằng: số dư bốn chiều, so với trung bình nhóm, không xếp hạng tên | 1,5 |
| D | Bảng tình trạng quán hôm nay cho chủ | 1,5 |
| D | Xuất báo cáo PDF kiểm toán công bằng | 0,5 |
| D | Màn hình xem vết agent, phần 1 | 0,5 |
| D | Khả năng dùng được: cỡ chữ, tương phản, dùng một tay, trạng thái tải và lỗi | 0,5 |

**Cổng ra sprint 4, đây là mốc sinh tử thứ hai**, sáu điều kiện:

1. **Quán đã công bố một lịch tuần bằng hệ thống**, và nhân viên nhận được tin nhắn lịch của mình
2. Ít nhất **5 phiếu thật đã chạy xong** bởi nhân viên thật, không phải bởi thành viên trong đội
3. Nhật ký chỉ ghi thêm chứa đủ vết của mọi lần đổi lịch trong tuần đó
4. Hộp thư ràng buộc đã có người quản lý duyệt hoặc từ chối ít nhất 10 đầu ra của agent
5. VF-CONFLICT có một trường hợp thật hoặc dựng lại được: hai agent nói trái nhau, hệ thống hiện cả hai và không tự chọn
6. **Bảng ghi nhận lần sửa đã tích luỹ đủ dữ liệu để sprint 5 có luật để đề xuất.** Nếu chưa đủ 3 lần sửa cùng mẫu ở bất kỳ loại nào, phải nói ra ngay ở buổi đóng sprint

**Rủi ro lớn nhất của sprint này không nằm ở mã nguồn, mà ở người.** Quán có thể không muốn đổi cách làm giữa tuần. Cách xử lý ở mục 16.

## 14.6. Sprint 5 — Cẩm nang sống đóng vòng lặp

> **Mục tiêu: một luật đi hết tám bước, từ lần sửa của con người đến chỗ trở thành tham số của lõi quyết định.**

**Chiếu được:** một thẻ luật trong Cẩm nang, có nguồn gốc là bốn lần sửa cụ thể bấm vào xem được, có kết quả tập sự, có số lần đã áp dụng.

| Người | Việc | Ngày |
|---|---|---|
| A | **Cẩm nang sống phần còn lại**: tìm mẫu, chế độ tập sự 5 lần, theo dõi, tự tắt dưới 80% | 3,5 |
| A | VF-RULE | 0,5 |
| A | Ánh xạ luật đã duyệt thành tham số của lõi, bước 7 của vòng đời | 0,5 |
| B | Bộ điều phối phần 2: trần ngân sách, phát lại phiên | 1,5 |
| B | Chợ đổi ca ba nhánh | 2,0 |
| B | Điểm danh QR một lần, không dùng lại được | 1,0 |
| C | **AG-RULE** đề xuất luật từ lần sửa | 1,5 |
| C | **AG-SOP** hỏi đáp quy trình, chỉ trả lời từ mẫu phiếu và cẩm nang | 1,5 |
| C | AG-WASTE đọc ghi chú hao hụt | 1,0 |
| C | Phần C của bảng kết quả tổng hợp | 0,25 |
| D | Màn hình xem vết agent, phần 2 | 1,0 |
| D | Giao diện Cẩm nang quán | 1,0 |
| D | Giao diện hỏi đáp SOP | 0,5 |
| D | Kiểm thử đầu cuối 8 luồng bằng Playwright | 1,5 |

**Cổng ra sprint 5**, sáu điều kiện. Đây là cổng khắt khe nhất của cả dự án:

1. **Một luật đi hết cả tám bước** và đang có hiệu lực, với bằng chứng là các lần sửa thật của người thật tại quán
2. **Ít nhất một luật bị VF-RULE loại**, và lý do loại đọc được trên màn hình. Không có ca bị loại nào thì cổng chưa chứng minh được là nó hoạt động
3. Chế độ tập sự có bảng đối chiếu 5 lần: hệ thống định làm gì, người thật đã làm gì
4. Cơ chế tự tắt có kiểm thử: nhét một luật có tỉ lệ đúng 60% vào, luật phải tự tắt
5. AG-SOP trả lời 20 câu hỏi thật của nhân viên, **mọi câu có trích dẫn**, và có ít nhất một câu trả lời đúng kiểu *"chưa có trong cẩm nang của quán"*
6. **Bảng thí nghiệm A/B** đã có số liệu sơ bộ

**Nếu trượt điều kiện 1, tức không có luật nào đủ bằng chứng:** không được bịa dữ liệu sửa. Cách xử lý duy nhất được phép là **nói thật trong bài thuyết trình**: cơ chế đã chạy đủ tám bước trên dữ liệu dựng lại từ 8 tuần lịch sử của quán, và số luật thật đang là bao nhiêu. Trung thực về một con số nhỏ mạnh hơn một con số đẹp không kiểm được.

## 14.7. Sprint 6 — Nộp bán kết

> **Mục tiêu: đóng gói một sản phẩm chạy được thật, có tài liệu, có video, và nộp.**

**Chiếu được:** thẻ phiên bản `v0.1.0-semifinal` trên GitHub, kèm video dưới 5 phút và tài liệu mô tả hệ thống.

| Người | Việc | Ngày |
|---|---|---|
| A | Sổ tiêu thụ suy ra từ kiểm kê, theo công thức mục 4.3 | 1,0 |
| A | Bộ kiểm chuẩn 8 ca theo quy mô, script so sánh hồi quy | 1,0 |
| A | Kiểm thử tầng vận hành, cẩm nang, và kiểm thử tất định của lõi | 1,0 |
| A | Phần A của tài liệu giới hạn phương pháp và bảng kết quả tổng hợp | 0,25 |
| B | Nhắc việc hai mốc và escalate hai cấp | 1,5 |
| B | Bù ca khẩn và khoá tranh chấp ở tầng cơ sở dữ liệu | 1,0 |
| B | API đọc vết agent | 0,5 |
| B | 11 tệp ADR và `THIRD_PARTY.md` | 0,75 |
| C | AG-VOC đọc phản hồi khách, nối vào việc treo | 1,0 |
| C | AG-EXPLAIN dịch mã lý do thành câu | 1,0 |
| C | AG-BRIEF bản tin sáng cho chủ | 0,75 |
| C | Thí nghiệm A/B: một agent xử lô so với N agent song song | 1,0 |
| D | Tài liệu mô tả hệ thống theo yêu cầu thể lệ | 1,5 |
| D | `docs/runbook-demo.md` | 1,0 |
| D | Video dưới 5 phút và slide | 1,5 |

**Vì sao sổ tiêu thụ nằm ở sprint 6 chứ không sớm hơn:** nó cần **ít nhất hai tuần số kiểm kê thật**, và quán chỉ bắt đầu kiểm kê bằng hệ thống từ sprint 4. Xây sớm hơn thì không có gì để kiểm chứng.

**Cổng ra sprint 6**, bảy điều kiện:

1. **165 bài kiểm thử tự động xanh**, 11 cổng CI xanh
2. `make demo` chạy từ trạng thái trắng ra dữ liệu đầy đủ trong dưới 5 phút
3. Thẻ `v0.1.0-semifinal` đã đẩy lên GitHub, có ghi chú phát hành liệt kê đúng những gì chạy được và những gì chưa
4. 9 agent của lô 1 đều có tệp `PHAM_VI.md` đủ 9 thuộc tính, và có kiểm thử làm đỏ nếu thiếu tệp
5. 11 ADR đã hợp nhất, gồm **ADR-011 ghi lại bốn thứ đã cắt để nhét Cẩm nang sống vào**
6. `THIRD_PARTY.md` liệt kê đủ giấy phép của mọi thư viện và mô hình
7. **Bảng kết quả tổng hợp có con số thật ở mọi dòng, hoặc chữ "chưa đo" ở dòng chưa đo.** Không dòng nào được để số phỏng đoán

## 14.8. Sprint 7 — Làm cứng và đo

> **Mục tiêu: mọi con số trong hồ sơ đều là con số đo được, và mọi lỗi từ hai tuần quán dùng thật đã sửa.**

Sức chứa 18 ngày người, **không có tính năng mới nào**.

| Việc | Người | Ngày |
|---|---|---|
| Đưa số bài kiểm thử từ 165 lên **215**, ưu tiên nhánh lỗi và trường hợp biên | A, B, C, D | 2,0 mỗi người |
| Sửa lỗi thu được từ hai tuần quán dùng thật | A, B, C, D | 1,5 mỗi người |
| **Đo và vẽ 12 con số ở mục 18.2**, gồm đường cong tỉ lệ không cần sửa | A và D | 1,0 mỗi người |
| Kiểm thử hồi quy bộ giải trên 8 ca kiểm chuẩn, và kiểm thử tải nhẹ | A và B | 1,0 mỗi người |
| Luyện phản biện chéo 20 câu ở mục 17, đã tính trong phần làm chung | Chung | 1,0 |

**Cổng ra sprint 7**, năm điều kiện:

1. **215 bài kiểm thử xanh**, và độ phủ nhánh của tầng domain trên 90%
2. **Đường cong tỉ lệ không cần sửa theo tuần đã vẽ xong bằng dữ liệu thật.** Đây là slide mạnh nhất của bài thuyết trình, và nó chỉ có giá trị nếu có dữ liệu sau nó
3. Mười hai con số ở mục 18.2 đều có giá trị hoặc có chữ "chưa đo" kèm lý do
4. Không còn lỗi mức chặn hoặc mức nặng nào mở
5. Cả bốn người trả lời được cả 20 câu ở mục 17, **kiểm bằng cách hỏi chéo, mỗi người trả lời 5 câu không phải phần mình làm**

## 14.9. Sprint 8 — Đóng băng và bảo vệ

> **Mục tiêu: mã nguồn đóng băng, diễn tập demo đến mức không cần suy nghĩ.**

Sức chứa 18 ngày người, **chỉ sửa lỗi mức chặn**.

| Việc | Ngày người |
|---|---|
| Đóng băng mã nguồn từ đầu sprint. Chỉ lỗi mức chặn được sửa, mỗi lần sửa cần 2 người duyệt | 6,0 dự phòng |
| Diễn tập demo 10 phút **ít nhất 5 lần**, có bấm đồng hồ, có người đóng vai giám khảo ngắt lời | 4,0 |
| Chuẩn bị bộ dữ liệu demo cố định và phương án ngắt mạng ở mục 15.3 | 2,0 |
| Hoàn thiện slide, tài liệu, và bảng kết quả tổng hợp bản cuối | 3,0 |
| Chạy `make demo` trên **ba máy khác nhau**, một máy chưa từng cài dự án | 1,0 |
| Vùng trống cố ý không lấp | 2,0 |

**Cổng ra sprint 8**, bốn điều kiện:

1. Thẻ `v1.0.0-final` đã đẩy lên, `main` xanh, `make demo` chạy được trên máy sạch
2. Demo 10 phút chạy đủ 5 lần liên tiếp không lỗi, **có ít nhất 2 lần chạy ở chế độ ngắt mạng hoàn toàn**
3. Mọi thành viên biết chạy toàn bộ demo một mình, kể cả phần không phải mình làm
4. Hồ sơ nộp đủ: tài liệu mô tả hệ thống, video, slide, liên kết mã nguồn, `THIRD_PARTY.md`, bảng kết quả tổng hợp

## 14.10. Bảng khối lượng theo sprint

| Sprint | A | B | C | D | Chung | Tổng |
|---|---|---|---|---|---|---|
| 1 | 4,25 | 4,00 | 4,00 | 4,00 | 1,0 | 17,25 |
| 2 | 4,50 | 4,25 | 4,50 | 4,50 | | 17,75 |
| 3 | 4,50 | 4,50 | 4,50 | 4,50 | | 18,00 |
| 4 | 4,50 | 4,50 | 4,50 | 4,50 | | 18,00 |
| 5 | 4,50 | 4,50 | 4,25 | 4,00 | | 17,25 |
| 6 | 3,25 | 3,75 | 3,75 | 4,00 | | 14,75 |
| 7 | | | | | 1,0 | 1,0 |
| **Tổng** | **25,50** | **25,50** | **25,50** | **25,50** | **2,0** | **104,00** |

Không ô nào vượt 4,50 ngày sức chứa. Sprint 6 nhẹ đi có chủ ý, vì đó là tuần nộp bán kết và tuần đó luôn phát sinh việc không lường trước.

---

# 15. Demo mười phút: một ngày ở quán

## 15.1. Nguyên tắc dựng demo

Demo không đi theo kiến trúc, mà đi theo **một ngày làm việc thật**. Giám khảo không quan tâm tầng nào gọi tầng nào. Họ quan tâm buổi sáng ở quán xảy ra chuyện gì và hệ thống làm gì với chuyện đó.

Ba luật cứng:

1. **Không mở một slide kiến trúc nào trong 10 phút.** Kiến trúc để dành cho phần phản biện, và chỉ mở khi bị hỏi
2. **Mỗi phút phải có một thứ động trên màn hình.** Không có đoạn nào chỉ đọc chữ
3. **Có đúng một khoảnh khắc gây bất ngờ**, và nó nằm ở phút thứ 6. Toàn bộ 6 phút trước là để dựng bối cảnh cho khoảnh khắc đó

## 15.2. Kịch bản từng phút

| Thời điểm | Trên màn hình | Câu nói kèm theo |
|---|---|---|
| **0:00 – 0:40** | Một ảnh: bảng danh mục dán tường, cuốn sổ kiểm kê, tệp Excel xếp ca, 6 nhóm Zalo | "Đây là hệ điều hành hiện tại của quán. Nó chạy được, và nó chạy trong đầu một người." |
| **0:40 – 2:10** | Điện thoại thật: nhân viên chạy phiếu mở quán. Đến bước kiểm kê, nhập số sữa còn 4 hộp, **cảnh báo dưới ngưỡng 8 hộp hiện ngay tại bước đó**, sinh một việc treo cho quản lý | "Bước kiểm kê không phải để tuân thủ. Nó là **cảm biến**. Mục 4.3 nói vì sao." |
| **2:10 – 2:40** | Thành viên thứ hai cố tình tích một loạt 6 bước trong 15 giây. **Bảng dấu hiệu bật đỏ**: 6 bước, 15 giây, không ảnh minh chứng, quản lý nhận cảnh báo | "Hệ thống không tố ai. Nó chỉ nói: ca này có dấu hiệu bất thường, anh xem lại. **Quyết định vẫn của con người.**" |
| **2:40 – 4:00** | Kéo **8 ảnh thời khoá biểu** vào một lần. Màn hình vết agent: 8 nhiệm vụ chạy song song, từng cổng bật xanh. **Ảnh số 5 bị mờ, VF-CONF bật vàng và đẩy lên người.** Mở hộp thư ràng buộc, quản lý xác nhận thủ công ảnh đó, đặt cạnh ảnh gốc | "Bảy ảnh máy đọc. Một ảnh máy **không dám đọc** và nói ra là nó không dám. Đây là điều em muốn giám khảo nhớ nhất về cách chúng em dùng AI." |
| **4:00 – 5:00** | Bấm xếp ca. Thanh tiến độ, 40 giây. Lịch tuần 25 người hiện ra. Bấm vào một ô, **AG-EXPLAIN** trả lời bằng tiếng Việt vì sao người này vào ca này. Mở bảng công bằng: số dư bốn chiều, không có bảng xếp hạng tên nào | "Bộ giải là CP-SAT, không phải mô hình ngôn ngữ. Mô hình ngôn ngữ chỉ **dịch mã lý do thành câu tiếng Việt**, và VF-NUM kiểm mọi con số trong câu đó có tồn tại thật hay không." |
| **5:00 – 6:00** | Quản lý kéo thêm một người vào ca chiều thứ Bảy. Ô đó **được ghim**, hệ thống giải lại phần còn lại trong 12 giây, không phá phần đã chốt | "Chị vừa sửa. Chị đã sửa đúng kiểu này ba lần trước rồi. Hệ thống đã lặng lẽ ghi lại cả ba lần, từ tuần thứ ba." |
| **6:00 – 7:10** | **Khoảnh khắc chính.** Một hộp thoại hiện lên: *"Tôi thấy trong 4 tuần, mỗi thứ Bảy ca chiều anh chị đều thêm một người pha chế. Đây có phải là một luật của quán không?"* Bấm vào, mở Cẩm nang. Thẻ luật hiện: câu luật tiếng Việt, **4 lần sửa cụ thể bấm xem được**, kết quả tập sự 5 trên 5, đã áp dụng 7 lần, bị ghi đè 0 lần. Cuộn xuống: một luật **bị VF-RULE loại** kèm lý do "chỉ có 2 bằng chứng", và một luật **đã tự tắt** vì tỉ lệ đúng tụt còn 60% | "Không ai ngồi viết cẩm nang này. Nó được viết ra bởi chính những lần chị sửa hệ thống. Và ba thẻ này chứng minh ba việc khác nhau: nó **học được**, nó **biết từ chối**, và nó **biết tự rút lui**." |
| **7:10 – 8:00** | Chuyển sang 14h. Ca sáng gõ bàn giao bằng tiếng Việt tự do. **AG-HANDOVER** tách thành 4 ô SBAR và 3 việc treo. **Người nhận ca bấm xác nhận từng việc** trên điện thoại của họ. Tiếp đó: một người không điểm danh sau 15 phút, hệ thống chạy **bù ca khẩn**, gửi tin cho 3 người đủ điều kiện theo thứ tự sổ nợ công bằng, người đầu tiên nhận | "Ba việc treo hôm qua rơi mất. Hôm nay chúng **không rơi được**, vì có người phải bấm nhận. Và AI **không tự gọi ai đi làm** — nó gửi lời mời, người nhận là người quyết." |
| **8:00 – 8:40** | Nhân viên mới hỏi **AG-SOP** hai câu bằng tiếng Việt tự nhiên. Câu 1: *"sáng thứ Hai có gì khác không?"* trả lời kèm trích dẫn tới đúng bước phiếu và đúng luật trong Cẩm nang. Câu 2 hỏi một thứ không có trong cẩm nang, trả lời: *"chưa có trong cẩm nang của quán, hãy hỏi quản lý"* | "Tri thức học được từ chị quản lý vừa **quay lại dạy nhân viên mới thay chị**. Và khi không có căn cứ, nó nói là không có, chứ không đoán." |
| **8:40 – 9:20** | Mở tệp YAML, dán thêm một mẫu phiếu mới là vệ sinh máy pha 6 bước, lưu. **Bấm F5 trên điện thoại, phiếu mới hiện ra ngay.** Không build lại, không deploy | "Quy trình ở đây là **dữ liệu, không phải mã nguồn**. Quán tự thêm quy trình mới trong 60 giây, không cần chúng em." |
| **9:20 – 9:45** | Ba con số: **đường cong tỉ lệ không cần sửa theo tuần**, sổ chi phí với dòng cuối là 0 đồng, và số lần gọi mô hình mỗi ngày so với hạn mức miễn phí | "Đường cong này là bằng chứng duy nhất cho thấy hệ thống đang học thật. Nó là số đo, không phải lời hứa." |
| **9:45 – 10:00** | Trở lại ảnh mở đầu | Đọc nguyên văn đoạn ở mục 1.3, kết ở câu **"Đó là tài sản của quán, không phải của người sắp nghỉ."** |

## 15.3. Bản đồ demo sang thang điểm

Mỗi tiêu chí phải có một phút cụ thể trong demo trả lời nó. Đây là bảng đội dùng để kiểm demo trước khi lên sân khấu.

| Tiêu chí | Điểm | Phút nào trả lời |
|---|---|---|
| Tính thực tiễn và giá trị cho doanh nghiệp | 25 | 0:00 hiện trạng thật · 0:40 phiếu do nhân viên thật chạy · 7:10 ba việc treo không rơi · 9:20 sổ chi phí |
| Mức độ hoàn thiện và trải nghiệm người dùng | 20 | 0:40 giao diện điện thoại một tay · 4:00 kéo thả và ghim ô · 8:40 thêm quy trình trong 60 giây |
| Thiết kế quy trình tự động hoá và tích hợp | 20 | 2:40 tám nhiệm vụ song song và màn hình vết · 7:10 SBAR và bù ca khẩn · 8:40 quy trình là dữ liệu |
| Ứng dụng AI phù hợp, an toàn, có trách nhiệm | 15 | 2:40 **ảnh mờ bị từ chối** · 4:00 lõi là CP-SAT không phải mô hình · 6:00 luật bị loại và luật tự tắt · 8:00 từ chối trả lời khi không có căn cứ |
| Tính sáng tạo và khả năng mở rộng | 10 | 6:00 Cẩm nang sống · 0:40 kiểm kê thành cảm biến · 8:40 mẫu phiếu là dữ liệu |
| Hồ sơ, trình bày, demo, phản biện | 10 | Cả 10 phút · 20 câu ở mục 17 · tài liệu này |

**Chỗ dễ mất điểm nhất là 15 điểm AI có trách nhiệm, và demo trả lời nó bốn lần.** Đó là chủ ý.

## 15.4. Danh mục kiểm tra trước khi lên sân khấu

| Việc | Vì sao |
|---|---|
| Chạy `make demo:reset` để về đúng trạng thái đầu | Demo phải chạy lại được nhiều lần y như nhau |
| **Nạp sẵn bộ nhớ đệm cho toàn bộ 8 ảnh và mọi câu hỏi trong kịch bản** | Để demo chạy được khi mạng hội trường sập |
| **Rút mạng và chạy thử trọn 10 phút** | Nếu không chạy được khi rút mạng thì demo chưa xong |
| Bật Ollama cục bộ làm nhà cung cấp dự phòng | Để nếu giám khảo yêu cầu một đầu vào mới ngoài kịch bản thì vẫn chạy được, tuy chậm hơn |
| Mở sẵn 4 tab: hệ thống, màn hình vết, Cẩm nang, bảng kết quả tổng hợp | Không tìm tab trên sân khấu |
| Sạc đủ 2 điện thoại, và có 1 điện thoại dự phòng đã đăng nhập | Phiếu là phần chạy trên điện thoại |
| Chuẩn bị 1 ảnh thời khoá biểu **cố tình mờ** | Đó là điểm sáng của phần AI có trách nhiệm, không được để nó chạy đúng ngẫu nhiên |
| In bảng kết quả tổng hợp ra giấy, 4 bản | Để đưa cho giám khảo lúc phản biện |

**Một điều phải nói thẳng với giám khảo ở phút 2:40, không được che:**

> "Phần này đang chạy bằng **bộ nhớ đệm đã nạp trước**, vì hội trường có thể mất mạng. Đây không phải video quay sẵn. Nếu thầy cô muốn, em xoá đệm và cho một ảnh mới của thầy cô ngay bây giờ, nó sẽ gọi mô hình thật và chậm hơn khoảng vài giây."

Nói ra trước khi bị hỏi thì đó là sự cẩn thận. Bị hỏi mới nói thì đó là bị bắt.

---

# 16. Rủi ro và cách chặn

Mỗi rủi ro có bốn thứ: **dấu hiệu sớm** đo được, mức độ, **cách chặn trước**, và **phương án B** đã quyết trước, không phải quyết lúc cháy.

## 16.1. Bảng mười một rủi ro

| # | Rủi ro | Dấu hiệu sớm | Khả năng | Tác động |
|---|---|---|---|---|
| R1 | Vùng đệm 4,0 ngày thấp hơn ngưỡng 5 ngày mà tài liệu này tự đặt | Cuối sprint 2 đã tiêu quá 9,0 ngày mỗi người | Cao | Cao |
| R2 | Sprint 2 đến 5 của cả bốn người đều kín 4,5 ngày, không còn chỗ cho việc phát sinh | Bất kỳ ai báo trễ 2 lần liền | Cao | Cao |
| R3 | Quán thật rút lui hoặc không cho dùng thật ở sprint 4 | Quản lý hoãn buổi hẹn 2 lần | Trung bình | **Sinh tử** |
| R4 | Nhân viên không dùng phiếu, hoặc dùng vài ngày rồi bỏ | Tỉ lệ hoàn thành phiếu tụt dưới 70% trong 3 ngày liền | Cao | **Sinh tử** |
| R5 | Cẩm nang học được một luật sai và nó ảnh hưởng tới lịch thật | Một luật có tỉ lệ bị ghi đè trên 20% | Trung bình | Cao |
| R6 | Đến sprint 5 không có luật nào đủ 3 bằng chứng | Cuối sprint 4, bảng ghi nhận có dưới 10 lần sửa | Trung bình | Cao |
| R7 | Hạn mức miễn phí của nhà cung cấp đổi hoặc bị siết giữa dự án | Một nhà cung cấp trả 429 nhiều hơn bình thường | Trung bình | Trung bình |
| R8 | Zalo OA phát sinh phí hoặc yêu cầu doanh nghiệp xác thực | Không đăng ký được tài khoản thử | **Cao** | Thấp |
| R9 | Bộ giải không có nghiệm với dữ liệu thật của quán | Bộ giải trả vô nghiệm trên dữ liệu quán, dù chạy đúng trên dữ liệu mẫu | Trung bình | Cao |
| R10 | Một thành viên bệnh, thi lại, hoặc rời đội | Nghỉ họp 2 buổi liền | Trung bình | Cao |
| R11 | Demo lỗi trên sân khấu | Bất kỳ lần diễn tập nào lỗi | Trung bình | Cao |

## 16.2. Cách chặn và phương án B

**R1 — Đệm mỏng.** Chặn: mỗi buổi mở sprint, trưởng nhóm công bố số đệm còn lại thành một con số, viết vào issue của sprint. Không có buổi nào được bỏ bước này. Phương án B đã quyết trước, cắt theo **đúng thứ tự này, không tranh luận lại**:

1. AG-BRIEF, 0,75 ngày
2. AG-VOC, 1,0 ngày
3. Màn hình xem vết agent, 1,5 ngày, thay bằng một trang JSON thô
4. Xuất báo cáo PDF kiểm toán, 0,5 ngày
5. Thí nghiệm A/B, 1,0 ngày

Năm mục này cộng lại 4,75 ngày. **Không mục nào trong đó là điểm sáng của bài thuyết trình**, đó là lý do chúng đứng đầu danh sách cắt.

**R2 — Sprint kín.** Chặn: sức chứa lập kế hoạch là 4,5 ngày trên 5 ngày làm việc, tức đã trừ sẵn 0,5 ngày mỗi người mỗi tuần cho họp, hỏng máy, và đọc lại mã của nhau. Phương án B: **việc phát sinh không được nhét vào sprint đang chạy.** Nó vào một danh sách chờ, và chỉ được xét ở buổi mở sprint sau, cạnh câu hỏi "cắt cái gì để lấy chỗ".

**R3 — Quán rút lui.** Đây là rủi ro nguy hiểm nhất, vì 45 trên 100 điểm nằm ở nghiệp vụ thật. Chặn ba lớp:

1. **Tuần 0 phải có hai quán, không phải một.** Một quán chính và một quán dự bị, cả hai đều đã đồng ý bằng tin nhắn
2. Ký một **thoả thuận một trang**: quán được gì, đội được gì, dữ liệu nào được dùng, quán có quyền dừng lúc nào cũng được. Một trang, không phải hợp đồng
3. **Không phụ thuộc vào việc quán đổi cách làm.** Sprint 4 chỉ yêu cầu quán dùng hệ thống cho **lịch tuần và phiếu mở quán**, hai thứ ít xâm phạm nhất. Không yêu cầu quán bỏ Zalo, không yêu cầu bỏ sổ giấy ngay

Phương án B: nếu cả hai quán rút, đội chuyển sang **quán dự bị thứ ba là căng tin hoặc quầy nước trong trường**, và **nói thật trong hồ sơ** là dữ liệu vận hành đến từ đâu. Tuyệt đối không bịa một quán không tồn tại. Một hội đồng chuyên môn phát hiện chuyện đó trong ba câu hỏi.

**R4 — Nhân viên không dùng phiếu.** Đây là rủi ro bị đánh giá thấp nhất trong mọi dự án loại này. Phần mềm đúng về kỹ thuật mà không ai dùng thì bằng không. Chặn:

1. **Đo tỉ lệ hoàn thành phiếu mỗi ngày từ ngày đầu.** Đây là con số số 7 ở mục 18.2
2. Ngưỡng cứng: **dưới 70% ba ngày liền thì không sửa giao diện, mà đi hỏi nhân viên bước nào vô lý, rồi cắt bước đó**
3. Nguyên tắc thiết kế: **một bước phiếu chỉ được tồn tại nếu nhân viên hiểu vì sao nó ở đó.** Bước nào phải giải thích dài mới thuyết phục được thì bước đó sai

Phương án B: rút phiếu mở quán từ 20 bước xuống **7 bước quan trọng nhất**, và ghi ADR. Bảy bước có người làm tốt hơn hai mươi bước bị tích khống.

**R5 — Luật sai chạm vào quyết định thật.** Năm lớp chặn, xếp theo thứ tự một luật sai phải vượt qua:

| Lớp | Chặn gì |
|---|---|
| 1. Ngưỡng bằng chứng | Dưới 3 lần sửa cùng mẫu thì AG-RULE không được đề xuất |
| 2. VF-RULE | Điều kiện phải dùng trường tồn tại thật, không được xung đột luật đã có |
| 3. Chế độ tập sự 5 lần | Luật chạy im lặng, đối chiếu với quyết định thật, dưới 4 trên 5 thì không lên được |
| 4. Người duyệt | Không ai bấm duyệt thì luật vĩnh viễn không có hiệu lực |
| 5. Tự tắt | Tỉ lệ đúng tụt dưới 80% thì luật tự tắt và báo người xem lại |

**Một luật sai phải vượt cả năm lớp mới chạm được vào lịch thật, và lớp 4 là một con người bấm nút.** Đây là câu trả lời cho câu hỏi phản biện số 4 ở mục 17.

**R6 — Không đủ bằng chứng để sinh luật.** Chặn: bảng ghi nhận lần sửa chạy từ **sprint 3**, sớm hơn phần còn lại của cẩm nang hai tuần, đúng như đã giải thích ở mục 14.4. Thêm một lớp nữa: **nhập 8 tuần lịch cũ của quán từ Excel** ở sprint 3 và 4, để có dữ liệu quá khứ. Phương án B: chạy cơ chế trên dữ liệu dựng lại từ 8 tuần lịch sử đó và **ghi rõ trong hồ sơ là dữ liệu dựng lại, không phải dữ liệu ghi trực tiếp**.

**R7 — Hạn mức đổi.** Chặn: bộ định tuyến bốn nhà cung cấp, chuyển trước khi bị chặn, và Ollama cục bộ ở cuối hàng. Phương án B: mọi thứ chạy hết trên Ollama cục bộ, chậm hơn, chất lượng thấp hơn, **nhưng demo vẫn chạy và chi phí vẫn là 0**. Con số phải đo trước sprint 7: chất lượng AG-TKB khi chạy hoàn toàn cục bộ là bao nhiêu.

**R8 — Zalo OA.** ⚠️ Đội **chưa kiểm chứng** được là Zalo OA có gói miễn phí đủ dùng hay không. Vì thế **Telegram Bot là kênh chính**, và cổng tin nhắn có ba hiện thực sau một giao diện trừu tượng. Phương án B: chỉ dùng Telegram và console, và nói thẳng ở phần phản biện là Zalo OA nằm ở lộ trình sau, kèm lý do là chưa xác nhận được chi phí. **Không được ghi trong hồ sơ là "miễn phí" một thứ chưa kiểm.**

**R9 — Bộ giải vô nghiệm với dữ liệu thật.** Đây là chuyện gần như chắc chắn sẽ xảy ra lần đầu, vì dữ liệu thật luôn có người ghi giờ rảnh sai hoặc quán thiếu người thật. Chặn: mọi ràng buộc mềm đều có biến vi phạm có trọng số, nên **mô hình gần như luôn có nghiệm ở mức mềm**. Ràng buộc cứng thì không nhượng bộ, nhưng khi vô nghiệm ở mức cứng, hệ thống phải **chỉ ra ca nào không thể phủ và thiếu bao nhiêu người**, chứ không được im lặng trả về rỗng. Phương án B: nếu tính năng chỉ ra tập ràng buộc gây vô nghiệm quá tốn thời gian thì trả về câu đơn giản "ca X thiếu Y người có kỹ năng Z", đủ dùng cho quản lý.

**R10 — Mất người.** Chặn: CODEOWNERS yêu cầu **mỗi vùng mã có ít nhất hai người đọc được**, và mọi pull request phải có người ngoài vùng đó duyệt. Không ai được là người duy nhất hiểu một phần. Phương án B đã quyết trước theo từng người:

| Mất | Ai gánh | Cắt gì ngay |
|---|---|---|
| A | B gánh bộ giải, C gánh cổng | Bộ kiểm chuẩn 8 ca, cơ chế tự tắt của cẩm nang |
| B | A gánh bộ điều phối, D gánh API | Chợ đổi ca còn 1 nhánh, bỏ ICS |
| C | A gánh AG-RULE, D gánh agent đọc | 4 agent: VOC, BRIEF, WASTE, EXPLAIN |
| D | C gánh frontend | Bảng tình trạng quán, màn hình vết, PDF kiểm toán |

**R11 — Demo lỗi.** Chặn: diễn tập 5 lần có bấm đồng hồ ở sprint 8, trong đó **2 lần chạy khi đã rút mạng**. Phương án B ba lớp: bộ nhớ đệm đã nạp sẵn, Ollama cục bộ, và cuối cùng là **video 5 phút đã nộp trước** để mở nếu máy chết hẳn. Điều kiện: mọi thành viên phải chạy được toàn bộ demo một mình.

## 16.3. Ba rủi ro không có phương án B, và đội chấp nhận

Trung thực hơn là giả vờ đã lo hết:

1. **Nếu quán thay quản lý giữa dự án**, toàn bộ quan hệ phải xây lại từ đầu và Cẩm nang sống mất chuỗi bằng chứng. Không có cách chặn nào ngoài việc làm việc với cả chủ quán chứ không chỉ với quản lý
2. **Nếu chất lượng đọc ảnh thời khoá biểu trên dữ liệu thật thấp hơn nhiều so với bộ mẫu vàng**, phần thu ràng buộc tự động mất giá trị và mọi thứ dồn về nhập tay. Hệ thống vẫn chạy được, nhưng một điểm sáng biến mất. Cách giảm thiệt hại duy nhất là **đo sớm ở sprint 2 và nói ra con số thật**
3. **Nếu quán vốn đã hài lòng với Excel**, giá trị của dự án giảm mạnh dù kỹ thuật vẫn đúng. Đây là lý do 7 con số hiện trạng ở tuần 0 phải đo trước khi viết một dòng mã: **nếu 7 con số đó cho thấy quán không đau, phải đổi quán, không phải đổi hồ sơ**

---

# 17. Hai mươi câu phản biện

Cách luyện: mỗi người trả lời **5 câu không thuộc phần mình làm**. Mỗi câu trả lời trong **dưới 60 giây**, mở đầu bằng một câu kết luận, sau đó mới là căn cứ. Câu nào chưa kiểm chứng được thì nói thẳng là chưa kiểm chứng.

## Nhóm A — Về kiến trúc

**1. Vì sao bộ điều phối của các em không phải là một agent? Ngành đang làm agent điều phối trung tâm mà.**

Vì điều phối là chỗ **không được phép sai theo cách không lặp lại được**. Nghiên cứu MAST tại NeurIPS 2025 phân tích 150 vết chạy trên 7 framework đa agent, độ đồng thuận giữa những người gán nhãn κ = 0,88, và ba nhóm thất bại lớn nhất là đặc tả hệ thống, lệch pha giữa agent, và xác minh. Trang dự án nêu rõ các thất bại này cần **thiết kế lại cấu trúc, không sửa được bằng chỉnh prompt**. Nếu điều phối là mô hình ngôn ngữ, cùng một đầu vào có thể ra hai luồng khác nhau, và không ai gỡ lỗi được. Bộ điều phối của chúng em là máy trạng thái, nên `make replay` phát lại được đúng một phiên. **Mô hình ngôn ngữ nằm ở lá, không nằm ở gốc.**

**2. Mười ba agent, có phải để hồ sơ trông dày không?**

Ngược lại, chúng em **loại bốn đề xuất và thu hẹp hai đề xuất**, mục 6. Và mười ba agent này không tự do: mỗi con có tệp `PHAM_VI.md` đủ **chín thuộc tính**, trong đó có một mục là **danh sách cấm**. Có bài kiểm thử làm đỏ CI nếu một agent thiếu tệp đó. Thêm nữa, ba nguyên tắc bất biến giới hạn chúng: agent không gọi agent, agent không ghi cơ sở dữ liệu, agent không quyết định luồng. Trong 6 tuần chúng em chỉ ship **10 con**, ba con còn lại đã tính chi phí 7,0 ngày và **cố ý chưa xây** vì phụ thuộc dữ liệu chưa có.

**3. Vì sao không dùng LangGraph, CrewAI hay AutoGen cho nhanh?**

Vì thứ chúng em cần từ một framework như thế — điều phối động và agent tự thương lượng — chính là thứ chúng em **cố ý không muốn có**. Anthropic viết rằng các hiện thực agent thành công nhất dùng **khuôn mẫu đơn giản và ghép được thay vì framework phức tạp**. Đội Cognition, tức nhóm làm Devin, còn viết thẳng rằng phần lớn người ta **không nên xây hệ đa agent** vì các agent song song tự đưa ra những lựa chọn ngầm xung đột nhau. Với bài toán này, một máy trạng thái vài trăm dòng cho chúng em thứ framework không cho: **tính tất định và khả năng phát lại**.

**4. Vì sao sáu cổng kiểm chứng là mã nguồn thường, mà không dùng một mô hình làm trọng tài?**

Vì trọng tài bằng mô hình sẽ **thất bại theo cùng cách với thứ nó đang kiểm**. Nếu mô hình đọc ảnh bịa ra một cái tên, thì mô hình trọng tài không có cách nào biết cái tên đó không có trong ảnh. VF-TRACE thì biết, vì nó **so vị trí trích xuất với vùng ảnh thật**. VF-NUM biết, vì nó **tìm từng con số trong câu diễn giải xem có tồn tại trong dữ liệu đầu vào hay không**. Sáu cổng đều là phép kiểm cơ học, chạy hết dưới một phần nghìn giây, và **không tốn một lần gọi mô hình nào**.

**5. Hệ thống này khác gì một Google Sheet có Apps Script?**

Ba thứ Sheet không làm được. Thứ nhất, **xếp ca bằng CP-SAT với 6 ràng buộc cứng và tối thiểu hoá nợ công bằng lớn nhất** — đây là bài toán tối ưu tổ hợp, Apps Script không giải được ở quy mô 25 người và 21 ca. Thứ hai, **minh chứng có gắn thời gian và bảng dấu hiệu chống tích khống** — Sheet không có khái niệm ai bấm lúc nào và có ảnh hay không. Thứ ba, và đây là thứ quan trọng nhất, **Cẩm nang sống**: một cái Sheet không tự nhận ra rằng bạn đã sửa cùng một thứ bốn lần và đề nghị biến nó thành luật.

## Nhóm B — Về dữ liệu

**6. Quán không có hệ thống bán hàng thì dữ liệu tiêu thụ các em lấy ở đâu? Đừng nói là các em tự nghĩ ra.**

Mục 4.3. Chúng em suy ra bằng một phép trừ:

```
tiêu thụ trong ca = số đếm đầu ca + số nhập trong ca − số đếm cuối ca − hao hụt đã ghi
```

Bốn số bên phải đều là số **quán vốn đã phải đếm** vì bước kiểm kê nằm trong phiếu mở quán và đóng quán. Nói cách khác, **một bước tồn tại vì lý do tuân thủ đã trở thành mạng cảm biến**, không cần tích hợp, không cần chi phí.

Và giới hạn của nó chúng em nói trước: đây là **ước lượng gián tiếp, không phải số bán hàng**. Sai số đến từ ba nguồn — người đếm sai, hao hụt không được ghi, mặt hàng dùng cho nhiều món. Vì thế mọi đầu ra dự báo đều **gắn nhãn ước lượng** và **luôn cần người phê duyệt**. Sai số này là con số số 9 trong bảng kết quả, và chúng em đo nó bằng cách đếm kiểm tra độc lập.

**7. Ảnh thời khoá biểu có tên và mã sinh viên. Các em xử lý dữ liệu cá nhân thế nào?**

Bốn việc. Một, **chỉ trích khoảng giờ học, không lưu môn học, không lưu mã sinh viên, không lưu tên giảng viên**. Hai, **ảnh gốc chỉ giữ tới khi ràng buộc được người xác nhận**, sau đó xoá theo hạn ghi trong hợp đồng dữ liệu. Ba, nhân viên **tự tải ảnh của mình lên**, không phải quán tải hộ, và có màn hình cho họ xem hệ thống đã hiểu gì về mình. Bốn, dữ liệu dùng cho bộ mẫu vàng được **che tên trước khi vào repo**, và repo không chứa ảnh thật của người thật.

**8. Đây có phải là học máy trực tuyến không? Hệ thống tự học thì ai kiểm soát?**

**Không, và đây là chỗ dễ hiểu sai nhất.** Không có mô hình nào được huấn luyện, không có trọng số nào thay đổi, không có gì được tinh chỉnh. Thứ "học" ở đây là **một bảng luật viết bằng tiếng Việt, do con người bấm duyệt từng dòng**. Một luật là một hàng trong cơ sở dữ liệu, đọc được, tắt được, xoá được, và có danh sách bằng chứng bấm xem được. Nếu ngày mai đội biến mất, quán vẫn mở bảng đó ra đọc và sửa được. Đó là lý do chúng em gọi nó là cẩm nang, không gọi là mô hình.

**9. Con số về giờ làm, khoảng nghỉ giữa hai ca, giới hạn giờ làm của người đang học — các em lấy ở đâu?**

Chúng em **cố ý không viết một con số nào vào tài liệu này và không viết cứng vào mã nguồn**. Tất cả là **tham số cấu hình**, và trước ngày bảo vệ đội phải tra từ **Bộ luật Lao động và văn bản hướng dẫn hiện hành**, ghi số điều khoản vào tệp cấu hình. Lý do làm vậy không chỉ là cẩn thận: **quy định đổi thì hệ thống không phải sửa mã nguồn**, chỉ sửa một tệp cấu hình, và có kiểm thử chạy lại toàn bộ ràng buộc cứng với tham số mới.

**10. Bảng công bằng của các em — ai nói đó là công bằng?**

Chúng em không tuyên bố định nghĩa được công bằng. Chúng em làm ba việc cụ thể hơn. Một, **công bằng là một sổ nợ bốn chiều đo được**, không phải một cảm giác, và bốn chiều đó do **quán chọn**, không do đội chọn. Hai, bộ giải **tối thiểu hoá khoản nợ lớn nhất**, tức lo cho người bị đối xử tệ nhất trước, thay vì tối ưu con số trung bình đẹp mắt. Ba, bảng công bằng **không xếp hạng tên ai**; mỗi người chỉ thấy số dư của mình so với trung bình nhóm. Nếu quán muốn định nghĩa khác, họ đổi trọng số, và toàn bộ lịch giải lại.

## Nhóm C — Về AI có trách nhiệm

**11. Cẩm nang học được một luật sai thì sao? Nó ảnh hưởng tới lịch của người thật.**

Một luật sai phải vượt **năm lớp**, mục 16.2. Ngưỡng ba bằng chứng. Cổng VF-RULE. **Chế độ tập sự năm lần**, nơi luật chạy im lặng và bị đối chiếu với quyết định thật của con người. **Một con người bấm duyệt** — không bấm thì luật vĩnh viễn không có hiệu lực. Và cuối cùng, **cơ chế tự tắt khi tỉ lệ đúng tụt dưới 80%**. Trong demo, chúng em chiếu cả một luật **bị loại** và một luật **đã tự tắt**, vì một cơ chế an toàn chưa từng chặn gì thì chưa chứng minh được điều gì.

**12. AI của các em có chấm điểm nhân viên không?**

**Không, và có bốn chỗ trong mã nguồn cấm việc đó.** Một, AG-RULE bị cấm viết luật về một con người cụ thể; loại luật về kỹ năng là luật về **cách ghép người**, không phải luật đánh giá người. Hai, bảng công bằng **không có bảng xếp hạng**. Ba, bảng dấu hiệu chống tích khống báo **"ca này có dấu hiệu bất thường"**, không báo "người này gian"; quyết định thuộc về quản lý và có nhật ký ghi lại ai quyết định. Bốn, **15 việc cấm agent hoá ở ADR-008** có mục đánh giá con người. Đây là ranh giới đạo đức, không phải giới hạn kỹ thuật.

**13. Khi mô hình không chắc thì hệ thống làm gì?**

**Luôn dừng và đẩy lên người, không bao giờ chọn phương án nghe có lý.** Đó là nguyên tắc thất bại đóng. Cụ thể: VF-CONF dưới ngưỡng thì **không thử lại**, đẩy lên người ngay. VF-CONFLICT khi hai agent nói trái nhau thì **không tự hoà giải**, hiện cả hai. Và ở cuối bộ định tuyến nhà cung cấp, khi hết mọi hạn mức miễn phí, hệ thống trả `tu_choi` và đẩy lên người, chứ không đoán. **Chi phí 0 đồng không bao giờ được đổi bằng độ đúng.**

**14. Vì sao các em loại bốn đề xuất agent kia? Nghe chúng hay mà.**

Vì mỗi cái thiếu một thứ cụ thể, mục 6.3. Nhóm đặt hàng thông minh và trợ lý giọng nói ở làn xe: **quán không có hệ thống bán hàng để nối vào**, quán Việt Nam nhỏ **không có làn xe**, và phần gợi ý mua thêm cần **dữ liệu cá nhân của khách** mà thể lệ cuộc thi không cho dùng khi chưa xin phép. Trợ lý cho người pha chế: cần **luồng đơn hàng trực tiếp**, tức lại cần hệ thống bán hàng. Giữ chân khách theo từng người: **dữ liệu cá nhân**. Nhóm quản trị chiến lược: chúng em **không định nghĩa được chín thuộc tính** cho nó, và một agent không định nghĩa được phạm vi thì đúng là dạng thất bại thứ nhất trong MAST. **Loại bốn đề xuất là phần chúng em tự tin nhất trong hồ sơ này**, vì nó cho thấy tiêu chí nhận một agent là gì.

**15. Còn hai đề xuất các em thu hẹp?**

Nói rõ đã bỏ phần nào. **Tiếng nói khách hàng** giữ lại thành AG-VOC, nhưng **chỉ nhận phản hồi do quán tự chuyển vào**, vì việc đi quét Google Maps, ShopeeFood hay Grab **có thể vi phạm điều khoản sử dụng của các nền tảng đó**, và đội **chưa kiểm chứng được** nên không đưa vào. **Thiết kế thực đơn** giữ lại thành AG-MENUOPS, nhưng **chỉ ở góc vận hành** là hao hụt và thời gian pha chế, **không tính lợi nhuận**, vì quán không cho dữ liệu giá vốn và đội không muốn dựng một module tài chính trên số phỏng đoán.

## Nhóm D — Về thực thi

**16. Chứng minh 0 đồng đi. Đừng nói là "dùng gói miễn phí".**

Mục 10.3 là **sổ chi phí 14 dòng**, mỗi dòng là một hạng mục có thể phát sinh tiền, kèm cách xử lý. Ba điểm cần nhấn. Một, khối lượng thật là **khoảng 125 lần gọi mỗi tuần, tức khoảng 18 lần mỗi ngày** — nhỏ hơn cả hạn mức khắt khe nhất trong các nguồn chúng em tra được là 50 lần mỗi ngày. Hai, có **Ollama chạy cục bộ** ở cuối hàng, nên kể cả khi mọi hạn mức online biến mất, chi phí vẫn là 0. Ba, và đây là chỗ chúng em cẩn thận: có nguồn cảnh báo rằng **nhiều thứ gọi là miễn phí thực ra là bản dùng thử tự chuyển sang trả phí**, nên trước khi chốt nhà cung cấp, đội **mở trang giá chính thức xác nhận hạn mức là vĩnh viễn và ghi ngày kiểm tra vào `THIRD_PARTY.md`**. Còn hai dòng chúng em **không dám khẳng định miễn phí**: Zalo OA, và giấy phép của một vài mô hình. Chúng được đánh dấu cảnh báo trong sổ.

**17. Bốn người, 6 tuần, 13 agent — con số này có thật không?**

Kế hoạch là **104,0 ngày người trên sức chứa 108**, chia đúng **25,5 ngày mỗi người**, và có bảng khối lượng theo từng sprint ở mục 14.10 với **không ô nào vượt 4,5 ngày**. Ba điều làm con số này đứng được. Một, chỉ ship **9 agent**, không phải 13; 4 con còn lại đã tính chi phí và cố ý dừng. Hai, **9 trong 9 agent lô 1 đứng trên cùng một khung chạy agent**, nên con thứ hai trở đi rẻ hơn con thứ nhất rất nhiều — AG-BRIEF chỉ 0,75 ngày. Ba, **hai tuần hoàn thiện, tức 36 ngày người, không lập kế hoạch tính năng nào**; đó là vùng đệm thật, không phải 4,0 ngày.

**18. Nếu nhân viên không dùng phiếu thì cả tầng vận hành thành vô nghĩa?**

Đúng, và đó là **rủi ro R4, được xếp mức sinh tử**. Cách chúng em xử lý không phải là làm giao diện đẹp hơn. Chúng em **đo tỉ lệ hoàn thành phiếu mỗi ngày từ ngày đầu**, và có ngưỡng cứng: **dưới 70% trong ba ngày liền thì đi hỏi nhân viên bước nào vô lý và cắt bước đó**, chứ không đi thuyết phục nhân viên. Nguyên tắc thiết kế là **một bước chỉ được tồn tại nếu nhân viên hiểu ngay vì sao nó ở đó**. Phương án B là rút phiếu mở quán từ 20 bước xuống 7 bước và ghi ADR. **Bảy bước có người làm tốt hơn hai mươi bước bị tích khống.**

**19. Vì sao các em cắt đường Pareto và phần mô phỏng thiếu người? Đó là những thứ nghe học thuật nhất.**

Vì chúng em phải lấy chỗ cho **Cẩm nang sống**, và **ADR-011 ghi lại đúng bốn thứ đã cắt** cùng lý do. Tiêu chí cắt là: thứ nào **quản lý quán sẽ dùng hằng tuần** thì giữ, thứ nào **chỉ đẹp trong 10 phút thuyết trình** thì cắt. Đường Pareto giữa công bằng và chi phí là một biểu đồ đẹp mà chị quản lý sẽ không mở lần thứ hai. Cẩm nang sống là thứ chị mở mỗi tuần. **Nếu hội đồng cho rằng chúng em chọn sai, chúng em muốn nghe, vì cả hai đều nằm trong lộ trình và cả hai đều đã có chi phí ước lượng.**

**20. Sau cuộc thi thì sao? Hay đây là một sản phẩm chỉ sống được mười phút?**

Ba lớp trả lời. **Kỹ thuật**: lô 2 gồm 4 agent đã thiết kế xong và tính chi phí 7,0 ngày, vì tất cả đều là **cấu hình hoặc agent trên hạ tầng đã có**. **Quy trình**: mẫu phiếu là YAML nên **quán tự thêm quy trình mới trong 60 giây, không cần đội** — chúng em chiếu điều đó ở phút 8:40. **Chi phí sở hữu**: hệ thống chạy được ở mức 0 đồng, nên quán không có lý do tài chính nào để dừng. Còn thứ khiến nó đáng sống lâu là **Cẩm nang sống**: càng chạy lâu thì tài sản của quán càng dày, và tài sản đó **không nằm trong đầu một người sắp nghỉ việc**.

---

# 18. Việc phải làm ngay

## 18.1. Mười ba việc của ngày 1 và ngày 2

Thứ tự này quan trọng. Việc số 1, 2 và 3 chặn mọi việc còn lại.

| # | Việc | Ai | Xong nghĩa là gì |
|---|---|---|---|
| 1 | **Xin bằng được hai quán**, một chính một dự bị, cả hai đồng ý bằng tin nhắn | Cả bốn | Có hai tin nhắn đồng ý, chụp lại |
| 2 | Ký **thoả thuận một trang** với quán chính: quán được gì, đội được gì, dữ liệu nào được dùng, quán có quyền dừng lúc nào cũng được | Trưởng nhóm | Một trang có hai chữ ký |
| 3 | **Buổi chốt năm hợp đồng dữ liệu và ba ADR nền**, 2 giờ, cả bốn người | Cả bốn | Năm tệp lược đồ và ba tệp ADR đã hợp nhất vào `main` |
| 4 | **D ngồi xem trọn một ca mở quán thật**, ghi lại từng bước theo đúng thứ tự người ta làm, không theo thứ tự hợp lý | D | Ba mẫu phiếu YAML lấy từ thực tế, không do đội nghĩ ra |
| 5 | **Đo 7 con số hiện trạng** ở mục 3.3 tại quán | D | Bảy con số có nguồn, ghi vào `docs/hien-trang.md` |
| 6 | **C mở trang giá chính thức của từng nhà cung cấp, xác nhận hạn mức miễn phí là vĩnh viễn, không phải bản dùng thử** | C | `THIRD_PARTY.md` có bảng nhà cung cấp, hạn mức, **và ngày kiểm tra** |
| 7 | Khởi tạo monorepo, ruff, mypy strict, eslint, prettier, pre-commit | B | `make lint` và `make type` xanh trên máy cả bốn người |
| 8 | Dựng **CI 11 cổng** và bật bảo vệ `main` | B | Một pull request thử bị CI chặn đúng như mong đợi |
| 9 | Viết **CODEOWNERS** theo bốn vùng nhánh | B | Một pull request vào vùng của A tự động yêu cầu A duyệt |
| 10 | **Thu 50 ảnh thời khoá biểu và 200 tin nhắn thật**, hai người gán nhãn độc lập, che tên trước khi vào repo | C và A | Bộ mẫu vàng có số đo độ đồng thuận giữa hai người gán nhãn |
| 11 | Sinh **bộ dữ liệu mẫu**: 25 nhân viên, 21 ca, 8 tuần lịch sử | A | `make seed` chạy được, dữ liệu vào cơ sở dữ liệu |
| 12 | Tra **Bộ luật Lao động và văn bản hướng dẫn hiện hành**, đưa mọi con số về giờ làm vào tệp cấu hình kèm số điều khoản | A | Tệp cấu hình có chú thích nguồn từng tham số |
| 13 | Dựng **bảng kết quả tổng hợp** với 12 dòng ở mục 18.2, mọi dòng ghi "chưa đo" | D | Một tệp duy nhất cả đội cùng cập nhật suốt 8 tuần |

**Việc số 13 quan trọng hơn nó trông.** Dựng bảng rỗng từ ngày đầu buộc cả đội nhớ rằng cuối dự án phải có con số ở mỗi dòng. Nếu chỉ dựng bảng ở tuần 7, chắc chắn sẽ thiếu dữ liệu để lấp.

## 18.2. Mười hai con số phải có trước ngày bảo vệ

Đây là bảng kết quả tổng hợp. **Mọi dòng phải có con số thật, hoặc chữ "chưa đo" kèm lý do. Không dòng nào được để số phỏng đoán.**

| # | Con số | Đo bằng cách nào | Sức nặng khi phản biện |
|---|---|---|---|
| 1 | **Tỉ lệ không cần sửa theo từng tuần**, từ tuần 1 tới tuần 8 | Đếm số quyết định hệ thống đưa ra và số quyết định bị người sửa | **Mạnh nhất.** Đây là bằng chứng duy nhất cho thấy hệ thống học thật |
| 2 | **Chi phí thực tế của toàn dự án** | Sổ chi phí 14 dòng, kèm ảnh trang hạn mức miễn phí có ngày kiểm tra | **Mạnh thứ hai.** Một con số 0 kiểm được đánh bại mọi lời hứa |
| 3 | Thời gian xếp ca một tuần: trước và sau | Bấm đồng hồ ở quán trước khi dùng, và đo lại ở tuần 6 | Rất mạnh, vì đây là điểm đau số một của quản lý |
| 4 | Số vi phạm ràng buộc cứng trên lịch đã công bố | Script kiểm độc lập với bộ giải, chạy trên mọi lịch đã công bố | Mạnh. Con số phải là 0, và phải kiểm bằng công cụ khác |
| 5 | Độ chính xác **AG-TKB**: đúng theo trường, và **tỉ lệ đẩy lên người** | Bộ mẫu vàng 50 ảnh | Mạnh, **kể cả khi con số thấp**, miễn là tỉ lệ đẩy lên người cao tương ứng |
| 6 | Độ chính xác **AG-MSG** trên 6 ý định, có ma trận nhầm lẫn | Bộ mẫu vàng 200 tin nhắn | Mạnh, vì ma trận nhầm lẫn cho thấy đội hiểu mình sai ở đâu |
| 7 | **Tỉ lệ hoàn thành phiếu** và thời gian chạy phiếu trung bình | Nhật ký máy quy trình, tính theo từng ngày | Mạnh, vì nó trả lời câu "có ai dùng thật không" |
| 8 | Số việc treo được ca sau **bấm nhận**, chia cho tổng số việc treo | Nhật ký bàn giao ca | Mạnh, vì nó đo đúng điểm đau lúc 14h |
| 9 | **Sai số của sổ tiêu thụ** so với đếm kiểm tra độc lập | Chọn 5 mặt hàng, đếm tay song song trong 1 tuần, so với số suy ra | Rất mạnh, vì nó cho thấy đội tự đi tìm giới hạn của ý tưởng mình |
| 10 | Cẩm nang: số luật **đề xuất / bị VF-RULE loại / qua tập sự / được duyệt / tự tắt** | Bảng luật trong cơ sở dữ liệu | **Mạnh thứ ba.** Năm con số này chứng minh cả cơ chế học và cơ chế chặn |
| 11 | Số lần cổng kiểm chứng đẩy lên người, **chia theo từng cổng** | Bảng `agent_results` | Mạnh, vì nó chứng minh sáu cổng không phải để trang trí |
| 12 | Số lần gọi mô hình mỗi ngày, độ trễ p50 và p95, tổng token | Bộ định tuyến ghi lại mỗi lần gọi | Mạnh, vì nó là chỗ nối giữa lời khẳng định 0 đồng và số đo |

**Ba dòng mạnh nhất là số 1, số 2 và số 10.** Nếu chỉ còn thời gian đo ba con số, đo ba con số này.

**Một lời nhắc về số 5.** Sẽ có lúc con số đó thấp hơn kỳ vọng. **Không được sửa con số, và không được bỏ dòng đó khỏi bảng.** Cách trả lời đúng là: "độ chính xác trường là X, và đúng vì vậy chúng em đặt VF-CONF, nên Y phần trăm ảnh bị đẩy lên người thay vì bị đọc sai vào lịch." Một đội biết chỗ yếu của mình và đã dựng lưới đỡ ở đúng chỗ đó thì đáng tin hơn một đội có mọi con số đẹp.

## 18.3. Bốn việc phải tự kiểm chứng, tài liệu này cố ý không kết luận

Bốn mục dưới đây được đánh dấu cảnh báo trong toàn bộ tài liệu. **Không mục nào được phát biểu như một sự thật trong hồ sơ hoặc trên sân khấu cho tới khi có người trong đội tự kiểm và ghi ngày kiểm.**

| ⚠️ | Việc | Ai | Kiểm bằng cách nào | Nếu kết quả xấu |
|---|---|---|---|---|
| 1 | **Con số về giờ làm, khoảng nghỉ, giới hạn giờ của người đang học** | A | Tra Bộ luật Lao động và văn bản hướng dẫn hiện hành, ghi số điều khoản vào tệp cấu hình | Đổi tham số, không đổi mã nguồn. Đây là lý do chúng là tham số |
| 2 | **Hạn mức miễn phí là vĩnh viễn hay chỉ là bản dùng thử** | C | Mở trang giá chính thức của từng nhà cung cấp, chụp ảnh, ghi ngày | Bỏ nhà cung cấp đó khỏi bộ định tuyến, dồn về Ollama cục bộ |
| 3 | **Giấy phép của OR-Tools, pm4py, PhoWhisper và mọi mô hình dùng tới** | B | Đọc tệp LICENSE trong repo gốc, không đọc bài blog nói về nó | Đổi thư viện, hoặc rút tính năng và ghi ADR |
| 4 | **Zalo OA có gói miễn phí đủ dùng hay không**, và **việc đọc phản hồi từ Google Maps, ShopeeFood, Grab có vi phạm điều khoản sử dụng hay không** | C | Đọc điều khoản sử dụng và bảng giá chính thức | Chỉ dùng Telegram và console. AG-VOC chỉ nhận phản hồi do quán tự chuyển vào |

**Câu nói khi bị hỏi đúng vào một trong bốn mục này:** "Chỗ này chúng em chưa kiểm chứng được nên tài liệu đánh dấu là chưa kiểm chứng, và hệ thống được thiết kế để không phụ thuộc vào nó — cổng tin nhắn có ba hiện thực đằng sau một giao diện, đúng vì lý do đó." **Một câu trả lời như thế được cộng điểm, không bị trừ.**

## 18.4. Mười một tệp ADR phải viết

Mỗi ADR một trang, đúng bốn phần: bối cảnh, quyết định, hệ quả, các phương án đã loại.

| ADR | Nội dung | Sprint |
|---|---|---|
| ADR-001 | Monorepo, và ranh giới giữa các gói | 1 |
| ADR-002 | **Bộ điều phối tất định, không phải mô hình ngôn ngữ.** Kèm căn cứ MAST, Anthropic, Cognition | 1 |
| ADR-003 | Hợp đồng dữ liệu trước mã nguồn, và máy chủ giả | 1 |
| ADR-004 | CP-SAT cho bài toán xếp ca, và các phương án đã loại | 2 |
| ADR-005 | Định nghĩa sổ nợ công bằng bốn chiều, và vì sao tối thiểu hoá nợ lớn nhất | 2 |
| ADR-006 | **Mẫu phiếu là dữ liệu, không phải mã nguồn** | 3 |
| ADR-007 | Sáu cổng kiểm chứng là mã nguồn tất định, không dùng mô hình làm trọng tài | 3 |
| ADR-008 | **Mười lăm việc cấm agent hoá** | 4 |
| ADR-009 | Sổ tiêu thụ suy ra từ kiểm kê, và ba nguồn sai số đã biết | 4 |
| ADR-010 | Cẩm nang sống: vòng đời tám bước, và vì sao đây **không phải học máy trực tuyến** | 5 |
| ADR-011 | **Bốn thứ đã cắt để lấy chỗ cho Cẩm nang sống**, kèm chi phí ước lượng của từng thứ | 5 |

**ADR-002, ADR-008 và ADR-011 là ba tệp cần đọc lại trước ngày bảo vệ.** Chúng trả lời trực tiếp ba câu phản biện khó nhất: vì sao điều phối không phải agent, đâu là ranh giới đội tự đặt cho AI, và đội đã đánh đổi những gì.

---

# Lời cuối của tài liệu

Tài liệu này có ba chỗ cố ý không đẹp, và đội nên giữ nguyên chúng.

**Thứ nhất, không có một con số kết quả nào.** Mọi con số về hiệu quả đều nằm ở dạng "phải đi đo", và bảng kết quả tổng hợp được dựng rỗng từ ngày đầu. Một hồ sơ có sẵn con số đẹp ở tuần 0 là một hồ sơ đã bịa.

**Thứ hai, có bốn mục đánh dấu chưa kiểm chứng.** Zalo OA, hạn mức miễn phí vĩnh viễn, giấy phép thư viện, và điều khoản của các nền tảng đánh giá. Đội có thể xoá dấu cảnh báo bằng cách đi kiểm, không bằng cách viết lại câu cho tự tin hơn.

**Thứ ba, mục 6.3 liệt kê bốn đề xuất đã bị loại, và câu 19 ở mục 17 nói về bốn tính năng đã bị cắt.** Một hồ sơ chỉ liệt kê những gì mình làm được thì không cho ai biết đội có tiêu chí gì. Danh sách những thứ đã từ chối nói nhiều hơn danh sách những thứ đã nhận.

Còn thứ đáng làm nhất trong toàn bộ dự án này chỉ là một vòng lặp nhỏ: **con người sửa hệ thống, hệ thống ghi lại, đủ ba lần thì hỏi lại con người, con người duyệt, và tri thức đó ở lại với quán.** Mọi thứ khác trong tài liệu này tồn tại để vòng lặp đó chạy được mà không sai.
