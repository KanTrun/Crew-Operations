# Kế Hoạch Kỹ Thuật: Thu Thập Dữ Liệu "Trending Now" Trên Threads Qua Camoufox Với Phiên Đăng Nhập Xác Thực

> **Ngày lập:** 2026-09-14 · **Phiên bản:** v1.0 (Production Blueprint)  
> **Nhánh đề xuất:** `feat/agents-threads-trending-authenticated`  
> **Bám chuẩn kiến trúc:** ADR-002 (Điều phối tất định) · ADR-003 (Contracts-first) · ADR-008 (Agent trích xuất - Người ra quyết định)  
> **Vùng sở hữu:** `packages/agents` (AG-TREND) · `packages/contracts` · `apps/api` · `apps/web`  
> **Trạng thái:** Sẵn sàng triển khai  

---

## Tóm Tắt Điều Hành (Executive Summary)

Tính năng này mở rộng năng lực của radar xu hướng (**AG-TREND**) trong hệ thống Nhịp Quán, bổ sung khả năng thu thập trực tiếp bảng xếp hạng **"Trending Now" (Xu hướng hiện tại)** từ giao diện tìm kiếm của Meta Threads (`threads.net/search`). 

Khác với các cơ chế tìm kiếm từ khóa công khai (Public Search) vốn chỉ phản ánh kết quả khi đã có từ khóa định trước, bảng **Trending Now** là danh sách động do Meta tự động tính toán theo thời gian thực dựa trên vị trí địa lý của tài khoản (Việt Nam). Việc tích hợp trình duyệt chống phát hiện **Camoufox** kết hợp cơ chế quản lý phiên cố định (**Persistent Authenticated Profile**) cho phép hệ thống trích xuất dữ liệu xu hướng chuẩn xác, ổn định dài hạn mà không gặp phải rào cản tường đăng nhập (Login-wall) hay bị đánh dấu tài khoản bất thường.

---

# PHẦN I — NGỮ CẢNH & ĐỘNG LỰC NGHIỆP VỤ

### 1.1. Bối cảnh hệ sinh thái hiện tại
Trong cấu trúc hiện nay của AG-TREND (`packages/agents/src/ca_agents/ag_trend.py`), luồng dữ liệu Threads chủ yếu dựa vào ba tầng:
1. Google News RSS Bridge qua từ khóa định sẵn.
2. Jina Reader (`r.jina.ai`) đọc trang web public.
3. Apify Actor (sử dụng tài nguyên trả phí / giới hạn gói miễn phí).

### 1.2. Hạn chế của luồng cũ
* **Không lấy được bảng "Trending Now":** Meta Threads khóa danh mục "Trending Now" tại trang `/search` đối với người dùng vãng lai hoặc IP không xác định vùng; chỉ tài khoản có phiên hoạt động tại Việt Nam mới hiển thị trọn vẹn danh sách chủ đề thịnh hành cùng số lượng bài viết (`posts`).
* **Bị động về từ khóa:** Luồng cũ bắt buộc phải có sẵn từ khóa tìm kiếm (Query-dependent). Nếu một xu hướng mới bất ngờ bùng nổ mà quán chưa nhập từ khóa, hệ thống sẽ bỏ lọt hoàn toàn.
* **Chi phí & Phụ thuộc:** Apify tiêu tốn hạn ngạch định kỳ; Jina Reader thường xuyên gặp hiện tượng quá tải và trả về dữ liệu rỗng.

### 1.3. Vai trò của Camoufox kết hợp Authenticated Session
* **Camoufox:** Cung cấp nhân trình duyệt Firefox tùy biến sâu ở tầng C++/Rust, tự động che giấu dấu vân tay thiết bị (Canvas, WebGL, AudioContext, WebRTC, OS Header), ngăn chặn hệ thống Bot Detection của Meta gắn cờ nghi vấn.
* **Persistent Profile (Hồ sơ người dùng cố định):** Lưu trữ toàn bộ Cookie, Token và Local Storage của tài khoản thật trên máy trạm/server, loại bỏ hoàn toàn việc phải đăng nhập tự động lại mỗi lần quét, biến mỗi lần cào thành một phiên duyệt web hoàn toàn tự nhiên.

---

# PHẦN II — MỤC TIÊU & RANH GIỚI PHẠM VI (GOALS & NON-GOALS)

### 2.1. Mục tiêu cốt lõi (Core Goals)
1. **Thu thập tự động 100% danh mục Trending Now:** Lấy chính xác danh sách các chủ đề xu hướng đang thịnh hành tại Việt Nam hiển thị tại màn hình tìm kiếm Threads.
2. **Bóc tách đầy đủ 5 trường thuộc tính nghiệp vụ:**
   * Thứ hạng xu hướng (Rank index).
   * Tiêu đề chủ đề (Topic Title).
   * Tóm tắt ngữ cảnh / Giải thích (Context Summary).
   * Dung lượng thảo luận (Post volume - quy đổi về số nguyên tuyệt đối).
   * Ảnh đại diện / Thumbnail chủ đề (nếu có).
3. **Quản lý phiên an toàn tuyệt đối (Fail-Safe Session):** Không lưu mật khẩu thô trong mã nguồn hoặc file cấu hình; chỉ dùng session ủy quyền qua profile trình duyệt; tự động dừng khẩn cấp khi phát hiện Checkpoint.
4. **Theo dõi vòng đời xu hướng (Trend Lifecycle Tracking):** So sánh lịch sử giữa các chu kỳ để gắn nhãn trạng thái (Mới xuất hiện, Đang tăng trưởng, Đạt đỉnh, Đang thoái trào).

### 2.2. Ranh giới không thực hiện (Non-Goals)
* **Không tự động đăng nhập qua code (No Automated Login):** Hệ thống không chứa bất kỳ logic nào tự gõ Username/Password. Việc đăng nhập được người vận hành thực hiện thủ công một lần duy nhất qua giao diện đồ họa.
* **Không tương tác tạo hành vi (No Active Engagement):** Không like, không follow, không bình luận, không đăng bài; chỉ thực hiện hành vi thụ động (Read-only observation).
* **Không cào thông tin cá nhân nhạy cảm:** Không thu thập danh sách chi tiết người dùng cá nhân trong từng bài viết; chỉ tập trung vào cấp độ chủ đề (Topic-level metrics).
* **Không quét dồn dập:** Tuyệt đối không quét tần suất dưới 10 phút/lần nhằm tuân thủ quy chuẩn đạo đức dữ liệu và bảo toàn an toàn mạng.

---

# PHẦN III — KIẾN TRÚC KỸ THUẬT & MÔ HÌNH THỰC THI

### 3.1. Sơ đồ luồng dữ liệu tổng thể (End-to-End Flow)

```
┌────────────────────────────────────────────────────────────────────────┐
│                        BỘ LẬP LỊCH CHU KỲ (JITTER)                     │
│  - Chu kỳ: 20 - 30 phút/lần + Sai số ngẫu nhiên (±60s - 180s)          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Kích hoạt phiên làm việc
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   BỘ KHỞI TẠO CAMOUFOX PROFILE                        │
│  - Nạp thư mục Persistent Profile (chứa Cookie/Session hợp lệ)         │
│  - Đồng bộ múi giờ, định vị GeoIP Việt Nam                             │
│  - Áp dụng Semaphore kiểm soát tối đa 1 tiến trình chạy tại một thời điểm│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  KIỂM TRA TÌNH TRẠNG PHIÊN (HEALTH CHECK)               │
│  - Kiểm tra xem phiên còn sống hay bị văng về Login / Checkpoint       │
└─────────┬────────────────────────────────────────────────────┬─────────┘
          │ (Nếu bị lỗi / Checkpoint)                          │ (Phiên hợp lệ)
          ▼                                                    ▼
┌──────────────────────────────────────┐     ┌───────────────────────────────────┐
│     BỘ NGẮT KHẨN CẤP (CIRCUIT BREAKER)│     │  TRUY CẬP: threads.net/search     │
│  - Đóng ngay trình duyệt             │     │  - Bật bộ lắng nghe gói tin mạng  │
│  - Chụp ảnh màn hình sự cố           │     │    (Network Interceptor)          │
│  - Bắn cảnh báo về Telegram/Log      │     └─────────────────┬─────────────────┘
│  - Đưa cờ hệ thống về PAUSED         │                       │
└──────────────────────────────────────┘                       ▼
                                             ┌───────────────────────────────────┐
                                             │    CHIẾN LƯỢC TRÍCH XUẤT KÉP      │
                                             ├───────────────────────────────────┤
                                             │ KÊNH CHÍNH (Ưu tiên):             │
                                             │  Bắt trực tiếp gói tin GraphQL    │
                                             │  từ API máy chủ Threads           │
                                             ├───────────────────────────────────┤
                                             │ KÊNH DỰ PHÒNG (Fallback):         │
                                             │  Trích xuất từ cấu trúc DOM cây   │
                                             │  giao diện (Semantic Selector)    │
                                             └─────────────────┬─────────────────┘
                                                               │
                                                               ▼
                                             ┌───────────────────────────────────┐
                                             │    BỘ CHUẨN HÓA DỮ LIỆU (PARSER)  │
                                             │  - Chuyển đổi "9K" -> 9000        │
                                             │  - Tạo mã băm nhận diện Topic     │
                                             │  - Tính toán độ tăng trưởng       │
                                             └─────────────────┬─────────────────┘
                                                               │
                                                               ▼
                                             ┌───────────────────────────────────┐
                                             │    KHO DỮ LIỆU & ĐIỀU PHỐI (AG)   │
                                             │  - Cập nhật Radar Xu Hướng        │
                                             │  - Đóng hoàn toàn tài nguyên RAM  │
                                             └───────────────────────────────────┘
```

### 3.2. Thiết kế chi tiết các tầng xử lý

#### 1. Quản lý Concurrency & Bộ nhớ (Resource Throttling)
* Launch trình duyệt tiêu tốn tài nguyên (ước tính 300MB – 600MB RAM mỗi phiên làm việc). Do đó, áp dụng cơ chế khóa phân luồng cứng (**Concurrency Barrier**): chỉ cho phép tối đa 1 phiên Camoufox chạy tác vụ Threads Trending tại một thời điểm.
* Mọi tiến trình phải được bao bọc trong khối giải phóng tài nguyên bắt buộc: Dù trích xuất thành công, thất bại, hay gặp timeout, trình duyệt và các tiến trình nền Firefox đều phải bị hủy triệt để, không để tồn tại tiến trình zombie.

#### 2. Chiến lược trích xuất kép (Dual Extraction Strategy)
* **Kênh chính - Network Response Interception:**
  Khi trình duyệt truy cập `threads.net/search`, máy khách gửi request POST tới endpoint nội bộ `https://www.threads.net/api/graphql`. Hệ thống bắt lấy phản hồi HTTP Response trước khi trình duyệt thực hiện render giao diện. Dữ liệu này chứa trực tiếp danh mục Trending dưới dạng cấu trúc JSON nguyên bản, loại bỏ hoàn toàn nguy cơ gãy code khi Meta đổi tên class CSS.
* **Kênh dự phòng - Semantic DOM Parser:**
  Trong trường hợp Meta mã hóa luồng dữ liệu mạng hoặc phân mảnh gói tin phức tạp, hệ thống chuyển sang quét cây DOM. Sử dụng các mốc định vị ngữ nghĩa (như `role="main"`, liên kết có cấu trúc `/search?q=`, các thẻ chứa tiền tố/hậu tố định lượng `posts` hoặc `bài viết`) thay vì dựa vào các class CSS ngẫu nhiên.

---

# PHẦN IV — MÔ HÌNH DỮ LIỆU & QUẢN LÝ VÒNG ĐỜI XU HƯỚNG

### 4.1. Cấu trúc dữ liệu chuẩn hóa (Normalized Trend Item Contract)
Mỗi chủ đề xu hướng thu thập được sẽ được đưa về cấu trúc dữ liệu tuân thủ chuẩn `TrendItem` của hệ thống Nhịp Quán:

| Trường thông tin | Kiểu dữ liệu | Ý nghĩa nghiệp vụ | Ví dụ minh họa |
| :--- | :--- | :--- | :--- |
| `platform` | Chuỗi | Định danh nền tảng | `"threads"` |
| `topic_id` | Chuỗi | Mã băm duy nhất dựa trên tiêu đề | `"th_trend_8f2b1a"` |
| `rank` | Số nguyên | Vị trí thứ hạng trên bảng | `1`, `2`, `3` |
| `title` | Chuỗi | Tiêu đề xu hướng | `"Video cũ Trường Giang ôm đồng nghiệp nữ"` |
| `summary` | Chuỗi | Tóm tắt bối cảnh / nội dung xu hướng | `"Nhã Phương đăng ảnh bên chồng sau khi video cũ..."` |
| `volume_raw` | Chuỗi | Số liệu nguyên gốc trên giao diện | `"9K posts"` |
| `volume_count`| Số nguyên | Số lượng bài viết đã quy đổi chuẩn | `9000` |
| `thumbnail_url`| Chuỗi | Đường dẫn ảnh đại diện nếu có | `https://scontent...` |
| `search_url` | Chuỗi | Đường dẫn truy cập trực tiếp | `https://www.threads.net/search?q=...` |
| `lifecycle` | Chuỗi Enum | Giai đoạn của xu hướng | `NEW` \| `RISING` \| `PEAKING` \| `FADING` |
| `scraped_at` | Chuỗi ISO | Thời điểm ghi nhận dữ liệu | `2026-09-14T10:15:00Z` |

### 4.2. Logic phân tích vòng đời xu hướng (Lifecycle Logic)
So sánh bộ dữ liệu của chu kỳ $T$ với chu kỳ trước đó $T-1$:
1. **Trạng thái `NEW`:** Chủ đề chưa từng xuất hiện trong cơ sở dữ liệu xu hướng trong vòng 24 giờ qua.
2. **Trạng thái `RISING`:** Chủ đề đã xuất hiện, thứ hạng tăng (ví dụ từ #5 lên #2) hoặc số lượng bài viết tăng trên 30% so với chu kỳ trước.
3. **Trạng thái `PEAKING`:** Chủ đề giữ vị trí Top 1 - Top 3 liên tiếp từ 2 chu kỳ trở lên với tốc độ tăng trưởng thảo luận bắt đầu đi ngang.
4. **Trạng thái `FADING`:** Chủ đề tụt hạng sâu (rơi quá 3 bậc) hoặc biến mất khỏi danh sách Trending Now.

---

# PHẦN V — CHIẾN LƯỢC BẢO VỆ TÀI KHOẢN & AN TOÀN ANTI-DETECT

Meta áp dụng hệ thống bảo mật đa tầng nghiêm ngặt bậc nhất hiện nay. Để duy trì tài khoản cào hoạt động bền vững hàng tháng/hàng năm, hệ thống phải tuân thủ 4 lớp bảo vệ:

### Lớp 1: Thiết lập & Bảo vệ Profile tĩnh (Persistent Profile Isolation)
* Thư mục Profile lưu trữ độc lập trên ổ đĩa bảo mật.
* Thiết lập quyền truy cập chặt chẽ, không để các tiến trình khác can thiệp hoặc ghi đè đồng thời.
* Toàn bộ thao tác đăng nhập ban đầu được thực hiện thủ công 100% trên màn hình có đầu (Headful) để vượt qua các bước xác thực bảo mật thông thường (nhập mã 2FA, bấm "Nhớ thiết bị này").

### Lớp 2: Che giấu dấu vết máy ảo & Tự động hóa qua Camoufox
* Tắt bỏ hoàn toàn các cờ tự động hóa đặc trưng của các thư viện như Selenium hay Puppeteer chuẩn (ví dụ `navigator.webdriver`).
* Cơ chế spoofing phần cứng ở cấp mã nguồn trình duyệt: Giả lập nhiễu Canvas (Canvas Noise Injection), giả lập cấu hình GPU thông dụng của người dùng văn phòng, tạo sai số ngẫu nhiên trên AudioBuffer.
* Camoufox đồng bộ hóa tham số GeoIP với địa chỉ mạng thực tế tại Việt Nam, ngăn chặn việc IP ở Việt Nam nhưng Header trình duyệt lại báo múi giờ hoặc ngôn ngữ châu Âu.

### Lớp 3: Điều tiết nhịp độ sinh học (Human Jitter & Pacing)
* Nghiêm cấm kích hoạt tác vụ theo nhịp cố định (ví dụ chính xác 00 giây của mỗi phút thứ 15).
* Thuật toán lập lịch bổ sung độ trễ giả lập ngẫu nhiên: Thời gian chờ tải trang biến thiên từ 2.5 giây đến 5.2 giây; cuộn trang ngẫu nhiên với gia tốc chuột mô phỏng hành vi con người lướt đọc nội dung.

### Lớp 4: Cơ chế ngắt mạch an toàn (Circuit Breaker)
* Nếu gặp bất kỳ dấu hiệu nào sau đây:
  1. URL chuyển hướng chứa `/login/` hoặc `/challenge/`.
  2. Trang hiển thị biểu mẫu bắt xác minh danh tính hoặc tải ảnh giấy tờ.
  3. Mã lỗi trả về `429 Too Many Requests`.
* Hệ thống **ngắt kết nối ngay lập tức**, ghi nhận cờ `CRITICAL_PAUSE`, dừng tất cả các chu kỳ cào tiếp theo và thông báo cho người quản trị. Tuyệt đối không để bot thử quét lại làm tăng điểm rủi ro tài khoản.

---

# PHẦN VI — MA TRẬN RỦI RO & PHƯƠNG ÁN ỨNG PHÓ

| Rủi ro tiềm ẩn | Mức độ | Khả năng | Giải pháp ứng phó kỹ thuật |
| :--- | :---: | :---: | :--- |
| **Tài khoản bị hết hạn phiên (Cookie Expiration)** | Thấp | Định kỳ | Hệ thống phát hiện chuyển hướng trang trắng, không raise lỗi vỡ luồng; gửi thông báo định kỳ yêu cầu quản trị viên mở trình duyệt gia hạn lại phiên. |
| **Meta thay đổi cấu trúc bảng Trending** | Trung bình | Định kỳ | Hệ thống có cơ chế trích xuất kép: khi gói tin GraphQL không khớp schema, cơ chế Fallback DOM sẽ tiếp quản tự động. |
| **Nghẽn tài nguyên do treo trình duyệt** | Cao | Thấp | Thiết lập cứng giới hạn thời gian (Hard Timeout) tối đa 45 giây cho mỗi lần chạy; nếu quá thời gian, tiến trình sẽ bị tiêu diệt cưỡng bức. |
| **Bị chặn IP mạng (Network IP Rate Limit)** | Trung bình | Thấp | Do chu kỳ quét giãn cách dài (20-30 phút/lần) và chỉ load đúng 1 trang `/search`, lưu lượng này thấp hơn rất nhiều so với người dùng thực tế lướt Threads. |

---

# PHẦN VII — LỘ TRÌNH TRIỂN KHAI THEO GIAI ĐOẠN

Quy trình triển khai được phân bổ thành 4 mốc (Milestones), đảm bảo kiểm thử cô lập trước khi tích hợp vào hệ thống chung:

### Cột mốc 1: Chuẩn bị Hồ sơ & Định vị Trình duyệt (Milestone 1)
* Khởi tạo cấu trúc lưu trữ Profile Camoufox trên môi trường vận hành.
* Chạy quy trình cấp quyền và hướng dẫn quản trị viên đăng nhập tài khoản một lần duy nhất.
* Xác nhận tính bền vững của Cookie sau 3 lần tắt mở trình duyệt liên tiếp.

### Cột mốc 2: Xây dựng Module Thu Thập Kép (Milestone 2)
* Xây dựng trình bao bọc (Wrapper) quản lý vòng đời Camoufox, áp dụng cơ chế Semaphore kiểm soát tài nguyên và bộ đếm thời gian Timeout.
* Xây dựng bộ chặn gói tin mạng (Network Response Interceptor) chuyên biệt cho endpoint GraphQL của Threads.
* Xây dựng bộ trích xuất dự phòng cây DOM (Semantic Fallback Parser).

### Cột mốc 3: Chuẩn hóa Hợp đồng Dữ liệu & Lưu trữ (Milestone 3)
* Hiện thực hóa bộ làm sạch chuỗi và chuyển đổi định lượng số bài viết (`volume_count`).
* Cập nhật Schema hợp đồng trong `packages/contracts` để hỗ trợ hiển thị thứ hạng và tóm tắt xu hướng.
* Tích hợp cơ chế so sánh dữ liệu lịch sử để tự động gán nhãn vòng đời (`NEW`, `RISING`, `PEAKING`, `FADING`).

### Cột mốc 4: Tích hợp Hệ Thống & Kiểm Thử Độ Bền (Milestone 4)
* Đấu nối nguồn dữ liệu mới vào Router radar xu hướng (`/api/v1/trends/radar`) của AG-TREND.
* Cấu hình bộ lập lịch định kỳ có Jitter ngẫu nhiên.
* Chạy thử nghiệm ngầm liên tục 48 giờ để đo lường độ ổn định, tỷ lệ thành công và kiểm tra nhật ký tài khoản Meta.

---

# PHẦN VIII — ĐỊNH NGHĨA HOÀN THÀNH (DEFINITION OF DONE)

Một tính năng được coi là hoàn tất và đủ tiêu chuẩn bàn giao khi đạt đầy đủ các tiêu chí:
1. **Tính chính xác dữ liệu:** Trích xuất đầy đủ 100% các mục trong bảng Trending Now trên Threads, không bị sót tiêu đề hay mô tả.
2. **Khả năng tự phục hồi (Resilience):** Thử nghiệm ngắt mạng hoặc đổi payload giả lập, hệ thống tự kích hoạt chế độ Fallback hoặc ghi log lịch sự, không làm treo ứng dụng API chính.
3. **An toàn tài khoản:** Sau 48 giờ chạy thử nghiệm định kỳ, tài khoản hoạt động bình thường, không xuất hiện bất kỳ thông báo cảnh báo bảo mật, xác minh số điện thoại hoặc mã captcha từ Meta.
4. **Giải phóng tài nguyên sạch:** Kiểm tra qua hệ thống giám sát tiến trình máy chủ, không còn bất kỳ tiến trình Firefox / Camoufox chạy ngầm nào sau khi kết thúc chu kỳ quét.
5. **Tài liệu bàn giao:** Có đầy đủ hướng dẫn vận hành (Runbook) cho người quản trị về cách khởi tạo hồ sơ, cách gia hạn phiên khi hết hạn và cách xử lý sự cố.
