# Nghiên cứu Oracle Cloud Always Free (2026) cho NHỊP QUÁN

> Ngày nghiên cứu: **05/09/2026**. Nguồn chính là tài liệu chính thức của Oracle (đã ghi ngày cập nhật từng trang) + đo latency thực tế từ máy ở VN (Viettel) ngày 05/09/2026.
> Ngữ cảnh: user gửi screenshot ChatGPT so sánh "free VM mãi mãi" và hỏi "cái này sử dụng được không" — bài này xác minh từng con số đó.
> Đối chiếu: phương án đã nghiên cứu = Vercel Hobby + Render Free (Singapore) + Neon Free.

## 0. Screenshot user gửi nói gì?

Screenshot là **app ChatGPT (điện thoại)**, đoạn hội thoại tiếng Việt có bảng "🏆 Danh sách đáng chú ý" so sánh nền tảng free VM: 🥇 Oracle (Ampere A1 **2 OCPU + 12 GB RAM**, ∞), 🥈 Google Cloud (1× e2-micro, ∞), 🥉 AWS (t4g.small, ⚠️ đến 31/xx), Azure (750h/th), Alibaba, IBM (Lite), Cloudflare (Workers); kèm đoạn "Oracle Always Free hiện cho Ampere A1 tổng cộng 2 OCPU + 12 GB RAM, cùng 200 GB block volume".

**Xác minh: các con số về Oracle trong screenshot ĐÚNG với thực trạng 2026** (không phải "4 OCPU + 24 GB" lỗi thời nữa — xem mục 2). Phần GCP e2-micro cũng đúng. Bảng ChatGPT dùng được làm tham khảo, nhưng thiếu các rủi ro thực tế (đăng ký, capacity, reclaim) bên dưới.

## 1. Always Free hiện tại gồm gì (đọc 05/09/2026)

Nguồn chính: <https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm> (cập nhật **12/06/2026**).

| Hạng mục | Always Free hiện tại |
|---|---|
| AMD VM.Standard.E2.1.Micro | **2 máy**: mỗi máy 1/8 OCPU + **1 GB RAM** (tổng 2 GB RAM) |
| Arm VM.Standard.A1.Flex (Ampere A1) | **1.500 OCPU-giờ + 9.000 GB-giờ/tháng** = chạy 24/7 thì **2 OCPU + 12 GB RAM** (1 máy 2/12, hoặc 2 máy 1 OCPU/6 GB) |
| Block Volume | **200 GB tổng** (gồm cả boot volume; boot mặc định 50 GB, tối thiểu 47 GB/máy) + 5 bản backup |
| Egress (outbound) | **10 TB/tháng** |
| Load Balancer | 1 Flexible LB 10 Mbps (tenancy từ 15/12/2020) + 1 Network LB |
| Object Storage | 20 GB (tổng 3 tier, sau khi trial hết) |
| Autonomous DB / HeatWave / NoSQL | 2 ADB (20 GB), 1 MySQL HeatWave, NoSQL… |
| IPv4 public | **Không mất phí** — bảng giá Networking hiện tại **không có dòng tính phí IPv4** (khác AWS/GCP $0.005/giờ); xem mục 6 |

## 2. Thay đổi lớn tháng 06/2026: A1 bị cắt đôi

- **Trước:** 3.000 OCPU-giờ + 18.000 GB-giờ/tháng = **4 OCPU + 24 GB RAM**.
- **Từ giữa 06/2026:** Oracle âm thimps giảm còn 1.500 OCPU-giờ + 9.000 GB-giờ = **2 OCPU + 12 GB RAM** — tài liệu docs cập nhật 12/06/2026; báo chí ghi nhận ngày 15/06/2026.
- Nguồn: docs Oracle (mục 1) + <https://linuxiac.com/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half/> (15/06/2026, bản cache: <https://vuink.com/post/yvahkvnp-d-dpbz/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half>).
- **Máy đang chạy vượt mức** (vd 4/24 cũ): theo docs <https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm> (cập nhật 29/06/2026), nếu tổng A1 vượt 2 OCPU/12 GB thì **toàn bộ instance A1 bị disable rồi xóa sau 30 ngày** nếu không upgrade trả phí → tenancy cũ buộc phải shrink máy.
- Ảnh hưởng NHỊP QUÁN: vẫn đủ RAM cho stack (mục 7), nhưng chứng minh Oracle **có tiền lệ giảm quota không báo trước** — rủi ro chính sách thực tế.

## 3. Đăng ký từ Việt Nam — rào cản lớn nhất

Yêu cầu (nguồn: <https://www.oracle.com/cloud/free/faq/>, đọc 05/09/2026):

- **Thẻ tín dụng/ghi nợ bắt buộc** (để xác minh danh tính; Oracle giữ tạm tiền authorize vài USD rồi trả lại, không trừ thật).
- Chấp nhận: **credit card và debit card "chạy như credit"** — tức thẻ ghi nợ quốc tế có tính năng tín dụng (Visa/Master).
- **KHÔNG chấp nhận:** "debit cards with a PIN, virtual, single-use, or prepaid cards" → loại gần hết thẻ debit nội địa VN (thẻ PIN/ATM), thẻ ảo số (Virtual card các app ngân hàng), prepaid.
- **Số điện thoại** cần xác minh OTP.

Thực trạng VN (không có nguồn chính thức thống kê — tổng hợp cộng đồng):

- Thẻ **credit quốc tế thật** (Visa/Master do ngân hàng VN phát cho CREDIT, không phải debit) là lựa chọn duy nhất khả thi; tỉ lệ thành công thấp và khó dự đoán vì Oracle chấm điểm rủi ro theo quốc gia/IP/thẻ.
- Báo cáo quốc tế 04/2026 cho thấy **kể cả người dùng EU/Mỹ với thông tin + thẻ thật vẫn thường bị chặn** "We can't register you": thread LowEndTalk <https://lowendtalk.com/discussion/215831/> (04/2026) — một user Thụy Điển thử 10–20 lần trong 5 năm, 100% thông tin thật, không qua nổi. → VN (risk score cao hơn) xác suất thành công thấp hơn nữa. [INFERENCE từ bằng chứng gián tiếp]
- Mua account sẵn (gray market) = vi phạm điều khoản "1 account/người", hay bị khóa không hoàn tiền — **không nên**.

## 4. Home region & Singapore

- **Always Free chỉ tạo được ở home region** (docs: "You must create the Always Free compute instances in your home region"). Home region **không đổi được sau khi tạo** — chọn sai là bỏ cả tenancy: <https://docs.oracle.com/en-us/iaas/Content/Identity/regions/managingregions.htm#Home>.
- **Singapore (ap-singapore-1) là vùng thương mại chính thức** và user quốc tế xác nhận chọn được Singapore khi signup (thread LowEndTalk 04/2026 có người nuôi A1 ở Singapore).
- **Vấn đề "Out of host capacity" với A1 vẫn hiện diện 2026**: Oracle docs chính thức ghi rõ lỗi "out of host capacity" = thiếu dụng Always Free shape ở home region, khuyên thử AD khác / chờ / upgrade trả phí (<https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm#compute>). Cộng đồng chạy script retry nhiều tuần không xong: cùng thread LowEndTalk (04/2026) — "I have been trying in Singapore since a week, no success". → **Sinh tồn của dự án phụ thuộc vào may mắn tạo được máy ở vùng mình chọn, không có SLA.**
- Lưu ý: tenancy chạy 30 ngày không dùng cũng có thể bị coi abandoned (FAQ Always Free).

## 5. Idle reclaim — quy tắc thu hồi máy "nghỉ"

Docs chính thức (cập nhật 12/06/2026): Oracle coi instance là **idle nếu trong 7 ngày liên tục**: CPU (95th percentile) < 20%, network < 20%, và **memory < 20% (áp dụng riêng shape A1)** → **có thể bị thu hồi (reclaim)**.

Đối chiếu NHỊP QUÁN: app quán cà phê dùng ít, một ngày vài lần solve → máy 12 GB RAM chỉ dùng ~1,5–2,5 GB = **~15–20% memory utilization → nằm sát/dưới ngưỡng thu hồi**. Phải chủ động chống: chạy cron đẩy tải CPU/mem định kỳ, hoặc gắn monitoring agent. Đây là chi phí vận hành ngầm ít người để ý. (Đã có báo cáo cộng đồng về reclaim máy idle A1/E2 các năm trước; quy tắc vẫn nằm nguyên trong docs 2026.)

## 6. Public IP: có bị đổi/trừ tiền không?

- **Ephemeral IP**: sống theo instance — **giữ nguyên khi stop/reboot** (docs: "When you stop an instance, its ephemeral public IPs remain assigned"), mất khi **terminate** máy.
- **Reserved IP**: tồn tại mãi, unassign/reassign thoải mái (giới hạn 50 reserved/region, free tier được dùng). Nguồn: <https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm> (cập nhật 03/02/2026).
- **Chi phí IPv4: hiện TƯ DOANH** — bảng giá OCI Networking (price list cập nhật **25/08/2026**, đọc 05/09/2026) **không có dòng tính phí public IPv4** nào (chỉ LB, egress 10 TB đầu free, inbound free). Khác hẳn AWS/GCP ( $0.005/giờ). → Muốn IP ổn định: tạo **reserved IP** gắn vào máy, $0/tháng.
- Lưu ý tenancy Free KHÔNG được support ticket chính thức (chỉ forum cộng đồng) — FAQ Oracle.

## 7. Có chạy nổi Docker stack NHỊP QUÁN trên 1 VM A1 không?

**Về kỹ thuật: CÓ, dư sức.** VM.Standard.A1.Flex 2 OCPU + 12 GB RAM (ARM64):

- RAM: Postgres (~150–300 MB) + Redis (~50–100 MB) + FastAPI/ortools (tăng đột biến ~0,5–1 GB lúc solve 60s) + worker nhỏ + Next.js standalone (~200–400 MB) ≈ **1–2,5 GB đỉnh** → 12 GB dư ~5×. **Hết nguy OOM** mà Render Free (512 MB) hay gặp.
- CPU: 2 OCPU ARM = ~4 threads; solve CP-SAT 60s sẽ chậm hơn x86 một chút nhưng chấp nhận được.
- **ortools có wheel Linux aarch64 chính thức** cho Python 3.12 (đã kiểm PyPI bản 9.15.6755, 05/09/2026: <https://pypi.org/project/ortools/>) → cài được trên ARM không cần build.
- Ổ: 200 GB block volume (boot 50 GB + volume gắn thêm cho Postgres) → lưu trữ bền vững qua restart.
- Docker Compose trên Ubuntu ARM: chuẩn, không khác x86.
- Public URL: IP reserved + mở port security list, hoặc gắn domain. Egress 10 TB/tháng quá đủ.
- **Latency VN → Oracle Singapore đo thực tế 05/09/2026 (máy Viettel): ~36 ms RTT** (objectstorage.ap-singapore-1.oraclecloud.com). So với Tokyo ~117 ms, Seoul ~119 ms, US ~261 ms. **Singapore là lựa chọn đúng.**

## 8. Có dùng được cho NHỊP QUÁN không?

**Kết luận: KHÔNG dùng làm phương án chính. Chỉ dùng khi đã có sẵn account Oracle hợp lệ (đăng ký được từ trước) — và khi đó là phương án k68 rất mạnh về phần cứng. Ưu tiên giữ phương án đã nghiên cứu: Vercel Hobby + Render Free Singapore + Neon Free.**

Lý do — rủi ro nằm ở "cửa vào", không phải ở phần cứng:

1. **Rủi ro đăng ký (chặn cửa):** cần thẻ credit quốc tế thật; thẻ debit PIN/ảo/prepaid VN bị loại công khai (FAQ Oracle). Báo cáo quốc tế 04/2026 cho thấy cả user EU với hồ sơ sạch còn fail; xác suất thành công từ VN thấp và không kiểm soát được. Thất bại = dự án không đi tiếp.
2. **Rủi ro capacity sau khi đăng ký:** phải chọn Singapore làm home region (đổi không được); A1 "out of host capacity" vẫn phổ biến 2026, có thể chờ hàng tuần không có máy. Phương án Render tạo instance ngay lập tức.
3. **Rủi ro chính sách quota:** Oracle vừa **cắt đôi A1 trong im lặng 06/2026** (4/24 → 2/12), máy cũ vượt mức bị disable + xóa 30 ngày nếu không trả phí → tiền lệ cắt giảm đột ngột đã xảy ra, có thể lặp lại.
4. **Rủi ro idle reclaim:** ngưỡng memory < 20%/7 ngày áp cho A1 — stack nhẹ 2 GB trên 12 GB dễ rơi vào vùng "idle" → phải nuôi cron tạo tải, ai quên là mất máy (mất luôn cả volume? — reclaim instance xóa kèm boot volume; block volume gắn riêng vẫn còn nhưng phải gắn lại máy mới).
5. **Không có support:** Free Tier chỉ được hỏi cộng đồng, không mở ticket.

Khi nào Oracle hợp lý: **đã có account** (tự đăng ký thành công trước đây) → 1 VM A1 2/12 tại Singapore chạy nguyên docker-compose (Postgres nội bộ thay Neon, không cần Redis external), $0 tuyệt đối (kể cả IPv4), latency 36 ms, egress 10 TB — **vượt trội hơn Render Free ở RAM (12 GB vs 512 MB) và không phụ thuộc dịch vụ bên thứ ba**. Lúc đó nên chạy song song/khả năng dự phòng: Neon làm DB chính + VM chạy API/solver, hoặc full-stack trên VM + backup Postgres qua Neon.

### Danh sách rủi ro (tóm tắt)

| # | Rủi ro | Mức độ | Giảm thiểu |
|---|---|---|---|
| 1 | Không đăng ký được (thẻ VN bị chặn) | Cao | Thử với credit card quốc tế thật; nếu fail → dùng phương án Render |
| 2 | Chọn nhầm home region (không đổi được) | Cao khi signup | Chọn Singapore ngay bước đầu |
| 3 | A1 out of capacity ở Singapore | Trung bình–cao | Chờ/retry script nhiều ngày; fallback 2 máy E2 Micro 1 GB (không đủ RAM cho stack) → thực tế không có fallback free tốt |
| 4 | Quota bị cắt thêm (tiền lệ 06/2026) | Trung bình | Không phụ thuộc duy nhất 1 nhà cung cấp; giữ script deploy di chuyển được |
| 5 | Idle reclaim (mem < 20%/7 ngày) | Trung bình | Cron tạo tải định kỳ + theo dõi email từ Oracle |
| 6 | Mất IP khi terminate máy | Thấp | Dùng reserved IP |
| 7 | Không có support chính thức | Thấp | Forum cộng đồng + tự chủ vận hành |

---

## Nguồn tham khảo (ngày đọc 05/09/2026 nếu không ghi khác)

1. Always Free Resources — <https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm> (Oracle, cập nhật 12/06/2026): quota E2/A1/200 GB/10 TB egress, idle reclaim, lỗi out of capacity.
2. OCI Free Tier overview — <https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier.htm> (Oracle, cập nhật 29/06/2026): cần thẻ + SĐT, quy tắc A1 vượt mức bị disable/xóa 30 ngày.
3. Free Tier FAQ — <https://www.oracle.com/cloud/free/faq/> (Oracle): thẻ PIN/ảo/prepaid không chấp nhận; 1 account/người.
4. Public IP Addresses — <https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/managingpublicIPs.htm> (Oracle, cập nhật 03/02/2026): ephemeral vs reserved.
5. Managing Regions (home region) — <https://docs.oracle.com/en-us/iaas/Content/Identity/regions/managingregions.htm> (Oracle): home region không đổi được.
6. OCI Price List — <https://www.oracle.com/cloud/price-list/> (Oracle, cập nhật 25/08/2026): không có dòng phí IPv4 public; egress 10 TB đầu free.
7. Oracle Quietly Cuts Free Tier Ampere A1 Resources in Half — <https://linuxiac.com/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half/> (Linuxiac, 15/06/2026; bản cache: <https://vuink.com/post/yvahkvnp-d-dpbz/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half>) + <https://korben.info/en/oracle-quietly-cuts-free-arm-offer-in-half.html>.
8. Thread LowEndTalk "Out of Capacity" — <https://lowendtalk.com/discussion/215831/oracle-free-tier-out-of-capacity-in-chicago-region-any-success-stories-with-scripts-lately> (04/2026): signup fail cả ở EU, A1 Singapore thiếu máy cả tuần 04/2026.
9. ortools PyPI — <https://pypi.org/project/ortools/> (kiểm wheel aarch64 Python 3.12 bản 9.15.6755, 05/09/2026).
10. Đo latency VN (Viettel) → Oracle: objectstorage.ap-singapore-1 = ~36 ms, ap-tokyo-1 = ~117 ms, ap-seoul-1 = ~119 ms, us-ashburn-1 = ~261 ms (ping trực tiếp, 05/09/2026).
