# Kế hoạch dữ liệu giả vận hành từ tháng 7 đến 16/09/2026

## 1. Mục tiêu và phạm vi

- Tạo dữ liệu giả nhất quán cho quán `quan_01` từ `2026-07-01` đến hết `2026-09-16`.
- Giữ nguyên 13 nhân sự và 13 tài khoản hiện có; không tạo thêm tài khoản giả ngoài dataset đã duyệt.
- Giữ tuần hiện tại `2026-W37` làm dữ liệu tham chiếu tương thích với API, sau đó bổ sung lịch sử và trạng thái vận hành theo thời gian.
- Không ghi thẳng vào `data/quan.db` cho tới khi toàn bộ validation và dry-run đạt.

Phạm vi lịch theo ISO:

- Tuần biên đầu: `2026-W27`, chỉ lấy `01/07`–`05/07`.
- 10 tuần đầy đủ: `2026-W28`–`2026-W37`.
- Tuần biên cuối: `2026-W38`, chỉ lấy `14/09`–`16/09`.
- Tổng: 78 ngày, 156 slot ca nếu giữ 2 ca/ngày, mỗi ca 8 giờ.

## 2. Nguyên tắc dữ liệu

1. **Một nguồn sự thật**: nhân sự lấy từ `files/staff_database_complete.json`; ID, kỹ năng, hợp đồng, giới hạn giờ và username không thay đổi.
2. **Lịch theo tuần**: mỗi tuần có ca, assignment, trạng thái lịch và metadata riêng; ID phải có namespace tuần, ví dụ `2026-W28_ca_01`.
3. **Dữ liệu đã xảy ra và dữ liệu hiện tại tách biệt**:
   - Tuần trước ngày hiện tại: trạng thái hoàn tất, có chấm công/bàn giao/tổng kết.
   - Tuần hiện tại: trạng thái đang vận hành, có việc chờ, xin nghỉ hoặc đổi ca pending nếu phù hợp.
4. **Không sinh lỗi ngẫu nhiên**: các conflict dùng để kiểm thử phải nằm trong fixture riêng, không đưa vào dataset vận hành hợp lệ.
5. **Idempotent**: chạy lại generator với cùng seed cho ra cùng JSON; nạp lại không nhân bản record và không xóa tài khoản bot hoặc dữ liệu ngoài namespace của dataset.

## 3. Các lớp dữ liệu cần sinh

### 3.1. Lịch và phân công

- 156 shift slot trong khoảng ngày cho phép, theo mẫu 06:00–14:00 và 14:00–22:00.
- Mỗi ngày 1 ca sáng và 1 ca chiều; nhu cầu tối thiểu giữ theo mẫu hiện tại, tăng người ở các ngày cao điểm cuối tuần.
- Assignment phân bổ theo kỹ năng, loại hợp đồng, ngày có thể làm và lịch sử ca chiều/cuối tuần.
- Mỗi tuần lưu:
  - `tuan_iso`, ngày bắt đầu/kết thúc, trạng thái vòng đời.
  - danh sách ca.
  - `phan_cong`.
  - snapshot fairness và tổng giờ theo nhân sự.

### 3.2. Nghỉ phép và khả dụng

- Mỗi tuần có một số yêu cầu nghỉ đã duyệt, pending và bị từ chối, với lý do hợp lý như lịch học, việc gia đình, sức khỏe.
- Rải theo nhóm nhân sự, không để một người bị nghỉ quá dày hoặc nghỉ trùng assignment đã duyệt.
- Availability có thể thay đổi theo tuần cho sinh viên, weekend-only và flexible; full-time/manager ổn định hơn.

### 3.3. Đổi ca

- Tạo chuỗi sự kiện có ngữ cảnh: đề nghị, chờ duyệt, được duyệt, từ chối, hủy.
- Đổi ca đã duyệt phải cập nhật assignment/snapshot tương ứng hoặc được đánh dấu là lịch sử trước khi ghi nhận.
- Người nhận ca phải có kỹ năng, khả dụng và không vượt giới hạn giờ/ngày.

### 3.4. Bàn giao và vận hành

- Mỗi ngày có bản ghi bàn giao mở ca/đóng ca hoặc task tồn: tồn kho, vệ sinh máy, đơn chưa xử lý, sự cố thiết bị.
- Task có người phụ trách, hạn xử lý, trạng thái `done`/`open`/`overdue` theo đúng mốc thời gian.
- Tuần hiện tại giữ một số việc mở để UI có dữ liệu cảnh báo; lịch sử cũ chủ yếu đã hoàn tất.

### 3.5. Công bằng và tổng kết

- Fairness ledger tích lũy theo tuần, không tạo lại độc lập từng tuần.
- Theo dõi tối thiểu: tổng giờ, số ca chiều, số ca cuối tuần, số ngày liên tiếp, số lần đổi ca.
- Snapshot cuối mỗi tuần dùng để kiểm tra xu hướng, không chỉ kiểm tra từng tuần đơn lẻ.

### 3.6. Ngữ cảnh kênh và thông báo

- Giữ channel binding hiện có; chỉ thêm sự kiện/notification nếu có contract rõ trong runtime.
- Có thể sinh inbox/notification cho thay đổi lịch, duyệt nghỉ và đổi ca, nhưng không giả lập token, tin nhắn riêng tư hoặc dữ liệu khách hàng thật.

## 4. Phân bố kịch bản theo giai đoạn

| Giai đoạn | Tuần | Bối cảnh chính |
|---|---|---|
| Khởi tạo | W27–W28 | Đội hình ổn định, làm quen lịch mới, vài yêu cầu nghỉ học |
| Vận hành bình thường | W29–W32 | Lịch đều, đổi ca ít, bàn giao phần lớn hoàn tất |
| Cao điểm | W33–W35 | Cuối tuần nhiều người hơn, tăng ca chiều hợp lý, có một vài đổi ca được duyệt |
| Ổn định và kiểm soát | W36–W37 | Theo dõi fairness, có nghỉ phép/pending và task tồn có chủ đích |
| Hiện tại | W38 đến 16/09 | Chỉ ghi dữ liệu đã phát sinh, không bịa phần ngày 17–20/09 |

## 5. Hard constraints bắt buộc

- Không assignment người không tồn tại hoặc không có kỹ năng cho vị trí ca.
- Không assignment vào ngày đã nghỉ phép `approved`.
- Không quá 1 ca/ngày/người.
- Không chồng ca và có ít nhất 12 giờ nghỉ giữa hai ca liên tiếp.
- Không quá 6 ngày liên tiếp.
- Không vượt `max_hours_tuan` theo hồ sơ nhân sự.
- Đủ `so_nguoi_toi_thieu` cho mọi ca.
- Ngày của shift phải khớp ISO week.
- ID, username, shift ID, request ID và task ID không trùng.
- Tài khoản runtime vẫn đủ 13/13, active và password hash xác thực được.

## 6. Cấu trúc lưu trữ dự kiến

Tạo một artifact nguồn mới, ví dụ `files/staff_history_jul_to_sep_2026.json`, gồm:

- `metadata`: khoảng thời gian, seed generator, version, store, số tuần/ca/assignment.
- `staff`: bản sao có kiểm tra hash từ dataset hiện tại.
- `weeks`: snapshot từng tuần, gồm shifts, assignments, availability, leave, swaps, handover và fairness.
- `current_week`: con trỏ tới tuần hiện tại và các trạng thái đang mở.
- `validation_expectations`: số lượng và các invariant cần đạt.

Khi nạp runtime, dùng các key KV có namespace/payload rõ ràng. Không ghi đè toàn bộ các key vận hành không thuộc dataset. Dữ liệu tuần hiện tại tiếp tục được API đọc qua các key đang dùng (`ca_mau_21`, `phan_cong`, `lich_tuan`); lịch sử dùng key riêng để không làm solver hiểu nhầm lịch cũ là lịch hiện hành.

## 7. Quy trình thực hiện

1. Viết generator deterministic, nhận `--start`, `--end`, `--seed`, `--output` và mặc định chỉ tạo JSON.
2. Sinh từng tuần từ template ca hiện tại, sau đó phân assignment bằng các ràng buộc hard trước và fairness sau.
3. Sinh sự kiện nghỉ phép, đổi ca, bàn giao theo timeline; cập nhật snapshot sau sự kiện đã duyệt.
4. Chạy validator độc lập trên toàn khoảng thời gian và từng tuần.
5. Chạy dry-run loader trên bản sao DB, so sánh trước/sau về users, KV và số record.
6. Chạy API smoke/read checks cho lịch hiện tại, lịch sử, nhân sự và các endpoint liên quan.
7. Backup `data/quan.db`, nạp thật trong một transaction/namespace có thể rollback.
8. Chạy lại validator, kiểm tra idempotency và xác nhận 13 tài khoản vẫn đăng nhập được.

## 8. Tiêu chí nghiệm thu

- JSON nguồn parse được, deterministic và có đủ metadata.
- 100% shift trong khoảng thời gian, 100% assignment hợp lệ.
- 0 hard conflict; các fixture conflict chỉ nằm trong bộ kiểm thử riêng.
- Fairness không tăng đột biến giữa các tuần; mọi thay đổi có lý do từ nghỉ/đổi ca.
- Không mất dữ liệu ngoài phạm vi dataset khi nạp runtime.
- Chạy lại generator/loader không tạo bản ghi trùng.
- API đọc được tuần hiện tại và không bị lịch sử làm sai solver.
- 13/13 tài khoản vẫn active, username unique và password verification pass.

## 9. Những điểm cần xác nhận trước khi triển khai

- Có muốn dữ liệu ảo bao gồm thêm chấm công thực tế (giờ vào/ra, đi muộn, vắng) hay chỉ lịch/phân công và nghiệp vụ liên quan?
- Có muốn tạo dữ liệu khách đặt bàn/đơn hàng theo cùng thời gian không? Đây là phạm vi khác và cần tránh làm bẩn báo cáo doanh thu thật.
- Dữ liệu sau khi tạo sẽ chỉ lưu trong artifact/DB local để demo, hay cần fixture dùng được cho test CI?