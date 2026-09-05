# Bảng Tra cứu Ràng buộc Cứng CP-SAT (C01 – C06)

Mọi lịch phân ca trong NHỊP QUÁN phải thỏa mãn 100% các ràng buộc cứng sau:

| Mã | Tên ràng buộc | Diễn giải kỹ thuật | Mã vi phạm trả về |
|---|---|---|---|
| **C01** | Trùng thời khóa biểu | Nhân viên không được xếp ca trùng với khung giờ học đã đăng ký trong `tkb`. | `c01:<ca_id>:<nv>:trung_tkb` |
| **C02** | Thiếu người / Thiếu kỹ năng | Ca làm việc phải đủ `so_nguoi_toi_thieu` và nhân viên phải sở hữu kỹ năng trong `vi_tri_can` (ví dụ: `barista`, `thu_ngan`). | `c02:<ca_id>:thieu_nguoi` hoặc `c02:<ca_id>:<nv>:thieu_ky_nang` |
| **C03** | Trùng ca cùng lúc | Một nhân viên không thể trực 2 ca có khung giờ giao nhau trong cùng một ngày. | `c03:<nv>:<ca_a>:<ca_b>:trung_ca` |
| **C04** | Khoảng nghỉ tối thiểu | Khoảng cách giữa giờ kết thúc ca trước và giờ bắt đầu ca kế tiếp của 1 người phải >= `khoang_nghi_gio * 60` phút. | `c04:<nv>:<ca_truoc>:<ca_sau>:thieu_nghi` |
| **C05** | Trần giờ tuần | Tổng thời gian làm việc trong tuần (bao gồm `gio_da_lam` trước đó) không được vượt quá `tran_gio_tuan`. | `c05:<nv>:vuot_tran_tuan` |
| **C06** | Trùng ngày nghỉ phép | Không phân công nhân viên vào ngày đã được duyệt đơn nghỉ phép (`nghi_phep`). | `c06:<ca_id>:<nv>:trung_nghi_phep` |
