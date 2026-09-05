# Nghiên cứu Google Cloud Free Tier (2026) cho NHỊP QUÁN

> Ngày nghiên cứu: **05/09/2026**. Nguồn chính là tài liệu chính thức của Google (đã ghi ngày cập nhật từng trang) + đo latency thực tế từ máy ở VN (Viettel) ngày 05/09/2026.
> Đối chiếu: phương án thay thế đã nghiên cứu trước đó = Vercel Hobby + Render Free (Singapore) + Neon Free.

## 1. Hai loại "free" của GCP — phải phân biệt

| | Free Trial | Always Free (Free Tier) |
|---|---|---|
| Giá trị | **$300 tín dụng, hết hạn sau 90 ngày** | Free theo hạn mức **hàng tháng, không hết hạn** (Google có quyền đổi hạn mức với thông báo 30 ngày) |
| Yêu cầu | Thẻ tín dụng/ghi nợ hợp lệ lúc đăng ký (Google giữ tạm $0–1 để xác minh, không trừ thật) | Cần **billing account đang hoạt động** (tức vẫn phải gắn thẻ, kể cả sau trial) |
| Khi hết | Tự đóng: dừng toàn bộ resource, 30 ngày grace, sau đó **xóa vĩnh viễn dữ liệu** | Dùng trong hạn mức = $0 |

Nguồn: <https://docs.cloud.google.com/free/docs/free-cloud-features> (cập nhật 26/08/2026, đọc 05/09/2026).

Lưu ý: upgrade lên tài khoản Paid **trước khi** trial hết 90 ngày thì giữ nguyên resource; nếu không, mọi thứ bị stop rồi xóa.

## 2. Compute Engine e2-micro "always free"

Theo bảng Free Tier chính thức (trang trên, mục Compute Engine):

- **1 VM e2-micro non-preemptible/tháng** — chỉ free trong **3 vùng US**: `us-west1` (Oregon), `us-central1` (Iowa), `us-east1` (South Carolina). Chạy ở vùng khác (kể cả Singapore/Đông Nam Á) = **tính tiền đầy đủ**.
- Giới hạn tính theo **giờ**, không phải theo máy: tổng số giờ free mỗi tháng = tổng số giờ của tháng (~720–744h) → chỉ đủ 1 máy chạy 24/7.
- Kèm: **30 GB-months** standard persistent disk + **1 GB egress**/tháng (từ Bắc Mỹ).

Cấu hình e2-micro (nguồn: <https://docs.cloud.google.com/compute/docs/general-purpose-machines>, đọc 05/09/2026):

- 2 vCPU shared-core, mỗi vCPU được **12.5% CPU time** (tổng 25% = 0.25 vCPU), RAM **1 GB**, egress tối đa 1 Gbps.
- Burst: chạy 100% CPU được **~30 giây** (token bucket) rồi bị kẹp về 25% CPU time.

### 2.1. Đủ chạy ortools CP-SAT (60s) + Postgres không?

**Không đủ.** Lý do:

- Solver cần ~512 MB–1 GB RAM riêng → 1 GB RAM chung cho Postgres + Redis + FastAPI + Next.js + worker + solver = **tràn RAM (OOM)** gần như chắc chắn khi solve.
- CP-SAT 60 giây trên 0.25 vCPU: burst chỉ ~30s, sau đó CPU bị kẹp 25% → solve 60s biến thành hiệu dụng ~240s, dễ vượt timeout và treo request.

### 2.2. "Free" nhưng thực ra mất ~$3.6/tháng — phí IPv4

Từ **01/02/2024** Google tính phí địa chỉ IPv4 ngoài gắn trên VM standard: **$0.005/giờ** (≈ $3.6/tháng cho 24/7). Free tier cho IPv4 ngoài chỉ **1 giờ/tháng** (nguồn: <https://cloud.google.com/vpc/network-pricing>, mục External IP address pricing, đọc 05/09/2026). Muốn $0 thật sự phải bỏ IPv4 (chỉ IPv6 — người dùng VN không phải ai cũng có IPv6).

### 2.3. Latency từ Việt Nam (đo thực tế 05/09/2026, máy Viettel)

Đo TCP-connect tới endpoint vùng của AWS (proxy địa lý cho cloud US/Asia; GCP US ước lượng tương tự — same undersea routes):

| Đích | RTT đo được |
|---|---|
| Google nearest PoP (8.8.8.8, anycast ~HK) | ~36 ms |
| Hong Kong | ~42–48 ms |
| Singapore | ~57–60 ms |
| Tokyo | ~105–119 ms |
| **us-west2 / Oregon (~us-west1 của GCP)** | **~196 ms** |
| **us-east1 / Virginia** | **~250 ms** |

Traceroute xác nhận đường đi: VN → HK (~38 ms) → Osaka (~120 ms) → Seattle (~180 ms). Tức là **3 vùng free của GCP đều ~190–250 ms RTT từ VN** — mọi request API của NHỊP QUÁN (đăng nhập, duyệt ca, chat copilot…) đều chậm cảm nhận rõ rệt.

## 3. Cloud Run "always free"

Nguồn: <https://docs.cloud.google.com/free/docs/free-cloud-features> (26/08/2026) + <https://cloud.google.com/run/pricing> + <https://docs.cloud.google.com/run/quotas> (01/09/2026; đọc 05/09/2026).

Free tier hàng tháng (mô hình request-based, mặc định cho service có scale-to-zero):

- **2 triệu request/tháng**
- **180.000 vCPU-giây** compute
- **360.000 GiB-giây** RAM
- 1 GB egress (Bắc Mỹ; bảng giá Premium Tier cũng cho 1 GB đầu free cho nhóm đích Asia)

Hạn mức kỹ thuật liên quan:

- **Timeout request tối đa 60 phút** → chứa nổi bài solve CP-SAT 60 giây (cần set `--timeout` khi deploy, mặc định thấp hơn).
- RAM tối đa **32 GiB**, CPU tối đa **8 vCPU** mỗi instance → dư sức cho solver.
- Startup timeout 4 phút; **scale-to-zero** → có **cold start** (image Python + ortools nặng; thực nghiệm cộng đồng thường vài giây tới ~10s+, chưa có con số chính thức — [INFERENCE]).
- Filesystem là **in-memory** → **không tự chạy được Postgres/SQLite bền vững trong container**; phải dùng DB ngoài (Neon, Cloud SQL — Cloud SQL không có free tier, chỉ trial 30 ngày).

Khối lượng free quy đổi cho NHỊP QUÁN: 180k vCPU-s ≈ **3.000 lần solve 60s @ 1 vCPU/tháng**; RAM 360k GiB-s ≈ 100 giờ instance 1 GiB. 2M request ≈ dư dùng cho cả web+API của một quán cà phê.

**Vùng:** không bị giới hạn như e2-micro — bảng giá liệt kê free tier áp dụng cho **mọi vùng, gồm cả `asia-southeast1` (Singapore)** (nguồn: trang run/pricing, đọc 05/09/2026; mức free tính theo giá Tier 1/us-central1). → Cloud Run Singapore ~60 ms từ VN là khả thi về latency.

Kiến trúc nếu đi Cloud Run: API (FastAPI+ortools) = 1 Cloud Run service; worker = Cloud Run **Jobs** (free tier riêng 240k vCPU-s + 450k GiB-s) hoặc **worker pools** (free ~384k vCPU-s + ~729k GiB-s ≈ 0.15 vCPU + 0.28 GiB chạy 24/7 — đủ cho worker rảnh); web Next.js = Cloud Run service thứ hai (hoặc Vercel); Postgres = Neon; Redis = Upstash. Nhiều mảnh ghép hơn phương án Render.

## 4. Đăng ký từ Việt Nam & rủi ro trừ tiền

- Việt Nam **có trong danh sách** currency/payment: VND, thanh toán bằng **credit card** (Visa/MasterCard) — nguồn: <https://docs.cloud.google.com/billing/docs/resources/currency> (26/08/2026). Thẻ nội địa chỉ debit có 2FA có thể bị từ chối; **prepaid card không được chấp nhận** (trang payment-methods, đọc 05/09/2026).
- Luôn Free **vẫn yêu cầu thẻ** gắn trên billing account; vượt hạn mức bất kỳ dịch vụ nào là trừ tiền thật.
- Thứ hay quên tính phí: IPv4 ngoài ($3.6/tháng), Cloud Storage vùng ngoài US, Artifact Registry > 0.5 GB, egress vượt 1 GB, snapshot disk, Cloud SQL sau trial…
- Hàng rào: **Budget alerts** (chỉ gửi email, KHÔNG tự dừng dịch vụ); mới hơn là **spend cap budgets (preview)** — khi đạt ngưỡng có thể **tự pause dịch vụ** (nguồn: <https://docs.cloud.google.com/billing/docs/how-to/budgets>, đọc 05/09/2026). Nên bật spend cap $1–5 ngay từ đầu.

## 5. Thay đổi 2025–2026 cần biết

- **e2-micro vẫn free**, vùng vẫn chỉ 3 vùng US — không đổi (xác nhận qua doc cập nhật 26/08/2026).
- **Tháng 01/2025: Cloud Run free tier x2** — request 1M → **2M**, compute 90k → **180k vCPU-s**, memory → **360k GiB-s** (nguồn: <https://tcoiq.com/news/gcp-cloud-run-jan25.html>; khớp số liệu chính thức hiện tại trên run/pricing, đọc 05/09/2026).
- Phí **IPv4 ngoài $0.005/h** (từ 02/2024) vẫn còn hiệu lực 2026 → e2-micro "free" thực tế ~$3.6/tháng nếu cần public IPv4.
- Free Trial vẫn **$300/90 ngày**, không đổi.
- Cloud Run có thêm mô hình **worker pools** với free tier riêng (mới trong bảng giá hiện tại).
- Spend cap budgets xuất hiện ở dạng preview — công cụ chống "đốt tiền" tốt hơn trước.

## 6. Có dùng được cho NHỊP QUÁN không?

**Kết luận: KHÔNG khuyến nghị GCP always-free làm phương án chính. Giữ phương án đã nghiên cứu (Vercel Hobby + Render Free Singapore + Neon Free) — tốt hơn ở mọi tiêu chí quan trọng.**

Lý do:

1. **e2-micro: loại ngay.** 1 GB RAM / 0.25 vCPU không chứa nổi Postgres + Redis + API + web + solver CP-SAT (chi tiết mục 2.1); vùng free chỉ ở Mỹ → **~200 ms RTT** từ VN (đo thực tế, mục 2.3); cộng phí IPv4 ~$3.6/tháng nên cũng không free tuyệt đối.
2. **Cloud Run: khả năng kỹ thuật, không phải lựa chọn tối ưu.** Chạy được container FastAPI (timeout 60 phút chứa nổi solve 60s), free tier rất hào phóng (2M req/180k vCPU-s/360k GiB-s), đặt ở Singapore được ~60 ms từ VN. NHƯNG phải tự ghép 4–5 mảnh: Cloud Run (API) + Cloud Run/Jobs (worker) + Neon (Postgres) + Upstash (Redis) + nơi chạy web; thêm cold start cho image ortools nặng; và toàn bộ nằm trên billing account gắn thẻ với rủi ro trừ tiền ngoài ý muốn.

So sánh nhanh với phương án thay thế (Render Free Singapore): Render chạy nguyên **docker-compose đầy đủ** (Postgres + Redis + API + worker + web tùy chọn) tại Singapore với ~60 ms từ VN, không cần thẻ để khởi tạo mức free — đơn giản hơn hẳn, ít rủi ro hơn.

### Danh sách rủi ro nếu vẫn chọn GCP

- **Rủi ro tiền:** cần thẻ tín dụng quốc tế ngay từ đầu (thẻ VN debit 2FA hay bị chặn); vượt bất kỳ hạn mức nào (egress, storage, IPv4, build minutes) là trừ tiền thật; budget alert chỉ email — phải tự bật **spend cap** (preview) để chặn.
- **Rủi ro hết hạn:** nếu dùng $300 trial mà quên upgrade trước ngày 90 → toàn bộ resource bị stop, 30 ngày grace rồi **xóa dữ liệu vĩnh viễn**.
- **Rủi ro vận hành (nếu dùng e2-micro):** OOM khi solve (1 GB RAM), solve chậm 4× sau 30 giây burst đầu tiên, latency 200 ms làm UX tệ.
- **Rủi ro vận hành (nếu dùng Cloud Run):** cold start vài giây đến ~10s+ sau mỗi lần idle ([INFERENCE]); file trong container là tạm thời → mọi trạng thái phải đẩy ra DB/Redis ngoài; hệ sinh thái nhiều dịch vụ nhỏ → khó debug hơn một docker-compose đơn lẻ.
- **Rủi ro thay đổi chính sách:** Google được quyền đổi/xóa hạn mức always-free chỉ với 30 ngày thông báo (ghi rõ trong doc chính thức).

### Khi nào GCP free lại hợp lý?

- Muốn **thử nghiệm/POC** có sẵn skill GCP, tận dụng $300/90 ngày.
- Chỉ cần **1 service Python nhỏ** (ví dụ API solver tách riêng) chạy Singapore với Cloud Run + Neon + Upstash, chấp nhận ghép nhiều mảnh.

---

## Nguồn tham khảo (ngày đọc 05/09/2026 nếu không ghi khác)

1. Free Google Cloud features and trial offer — <https://docs.cloud.google.com/free/docs/free-cloud-features> (Google, cập nhật 26/08/2026)
2. Cloud Run pricing — <https://cloud.google.com/run/pricing> (Google)
3. Cloud Run Quotas and Limits — <https://docs.cloud.google.com/run/quotas> (Google, cập nhật 01/09/2026)
4. General-purpose machine family (e2-micro specs, burst) — <https://docs.cloud.google.com/compute/docs/general-purpose-machines> (Google)
5. Network pricing (phí IPv4 ngoài $0.005/h, free 1h/tháng; egress) — <https://cloud.google.com/vpc/network-pricing> (Google)
6. Currencies & payment methods by country (Việt Nam = VND, credit card) — <https://docs.cloud.google.com/billing/docs/resources/currency> (Google, cập nhật 26/08/2026)
7. Payment methods (prepaid không chấp nhận) — <https://docs.cloud.google.com/billing/docs/how-to/payment-methods> (Google)
8. Budgets & alerts, spend cap (preview) — <https://docs.cloud.google.com/billing/docs/how-to/budgets> (Google)
9. GCP Cloud Run free tier x2 tháng 01/2025 — <https://tcoiq.com/news/gcp-cloud-run-jan25.html> (tcoiq, 01/2025; khớp số chính thức hiện tại)
10. GCP Free Tier guide 2026 (xác nhận vùng e2-micro) — <https://agentdeals.dev/gcp-free-tier-2026> (AgentDeals, 2026)
11. Đo latency VN→HK/SG/Tokyo/Oregon/Virginia — thực hiện trực tiếp trên máy Việt Nam (Viettel), 05/09/2026: ping 8.8.8.8 = 36 ms; TCP-connect Singapore ≈ 57–60 ms, Hong Kong ≈ 42–48 ms, Tokyo ≈ 105–119 ms, us-west-2 ≈ 196 ms, us-east-1 ≈ 250 ms; traceroute VN→HK→Osaka→Seattle.
