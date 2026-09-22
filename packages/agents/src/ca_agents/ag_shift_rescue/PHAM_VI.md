# AG-SHIFT-RESCUE — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Ca vắng đột xuất → danh sách người bù an toàn, có thứ hạng và lý do |
| Phạm vi | Chuẩn hoá báo vắng · lọc theo ràng buộc cứng · xếp hạng theo công bằng và tải việc |
| Đầu vào | `{case_id, absence_nv_id, shift_id, reported_by, reason, snapshot_hash}` · hồ sơ nhân viên + metadata ca |
| Đầu ra | `RescueCandidate[]` (an toàn, kèm lý do đạt) + danh sách bị chặn kèm lý do chặn |
| Mô hình | Tất định 100%. Xếp hạng theo `policy_version`; không LLM tham gia chọn người |
| Song song | Có. Mỗi ca cứu độc lập |
| Điều kiện dừng | Trả danh sách ứng viên, hoặc danh sách rỗng khi không ai đủ điều kiện |
| **Cấm** | Đề xuất người vi phạm ràng buộc cứng như "an toàn" · gán người vào ca khi chưa ai đồng ý · tự đổi lịch · ghi DB · gọi agent khác |
| Cổng | VF-SCHEMA, VF-RULE |

## Ràng buộc cứng không được nới để có đủ ứng viên

`filter_eligible` loại người vướng TKB, thiếu kỹ năng vị trí, trùng ca, chưa đủ
giờ nghỉ, vượt trần giờ tuần, đang nghỉ phép. Khi không còn ai, hệ thống trả
danh sách rỗng và lớp gọi phải mở đường leo thang (quản lý đứng ca, giảm suất,
hoặc War Room) — **không** hạ chuẩn để có người. Một người được xếp vào ca mà
vi phạm ràng buộc còn tệ hơn một ca thiếu người, vì nó phá cả tuần lịch.

## Trạng thái ca do `ca_ops.shift_rescue_policy` sở hữu

Máy trạng thái (`reported → resolving → candidates_ready → proposed → invited →
responded → confirmed`) nằm ở `packages/opsengine`, không ở đây. Lớp này chỉ
tính toán; mọi chuyển trạng thái đi qua policy để không có hai nguồn sự thật.

## Lý do phải nói được cả hai chiều

Mỗi ứng viên an toàn mang `reason_passes` (vì sao được chọn) và mỗi người bị
chặn mang `reason_blocks` (vì sao bị loại). Quản lý phải giải thích được với
nhân viên tại sao mình không được mời — "hệ thống không cho" là câu trả lời
không chấp nhận được.
