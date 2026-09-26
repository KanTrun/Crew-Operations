# AG-WAR-ROOM — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | So sánh các phương án "nếu… thì…" trên cùng một mốc dữ liệu, tất định |
| Phạm vi | Chuẩn hoá lệnh mô phỏng · chạy từng kịch bản · kiểm tra khả thi bằng ràng buộc cứng · so sánh đa phương án với baseline |
| Đầu vào | `{request_id, baseline_snapshot, scenarios[], requested_by}` |
| Đầu ra | `WarRoomComparison` (baseline + `WarRoomOption[]` kèm rủi ro, vi phạm ràng buộc, nhãn ước tính) |
| Mô hình | Tất định 100%. LLM chỉ parse ý định; **không** LLM sinh số |
| Song song | Có. Mỗi kịch bản độc lập, kết quả không phụ thuộc thứ tự |
| Điều kiện dừng | Trả bảng so sánh, hoặc lỗi khi baseline lệch mốc |
| **Cấm** | Sinh số bằng LLM · đề xuất phương án vi phạm ràng buộc cứng như hợp lệ · tự ghi lịch/kho · chạy với baseline cũ mà không cảnh báo · ghi DB · gọi agent khác |
| Cổng | VF-SCHEMA, VF-NUM, VF-RULE |

## Số thuộc về math layer, không thuộc về mô hình ngôn ngữ

Mọi con số trong bảng so sánh đến từ math layer và solver. Tầng này không có
đường nào để một mô hình ngôn ngữ chèn số vào kết quả. Đây là ràng buộc cứng
(ADR-002): chủ quán ra quyết định dựa trên bảng này, nên số phải tái lập được và
giải thích được.

## Phương án vi phạm vẫn hiện, nhưng bị khoá

Kịch bản vi phạm ràng buộc cứng (thiếu người, vượt trần giờ) vẫn được trả về
kèm `constraint_violations` và bị đánh dấu chặn. Người dùng cần thấy "phương án
này rẻ hơn nhưng không hợp lệ" — giấu đi sẽ khiến họ tưởng nó chưa được xét.
Lớp gọi chịu trách nhiệm không cho đề xuất phương án bị chặn.

## Baseline lệch mốc thì dừng, không đoán

`validate_baseline_snapshot` từ chối chạy khi mốc dữ liệu nền không còn khớp.
So sánh trên một mốc đã cũ cho ra kết luận sai mà trông vẫn hợp lý — đúng loại
lỗi khó phát hiện nhất trong vận hành.
