# AG-SPATIAL-MEMORY — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Ký ức quán gắn vào không gian: truy xuất có lọc quyền, trả lời có căn cứ, dẫn tour |
| Phạm vi | Truy xuất theo neo/trạng thái/đồng thuận · dựng câu trả lời kèm trích dẫn · xếp tuyến tour tất định |
| Đầu vào | `{store_id, anchor_id, role, requester_id, status?}` · câu hỏi dạng chữ + ngữ cảnh ký ức |
| Đầu ra | `ExperienceMemory[]` đã lọc · `GroundedAnswer` kèm `citation_memory_ids` · `TourPlan` |
| Mô hình | Tất định. Không LLM trong lớp này — LLM chỉ lo câu chữ khi có tầng riêng gọi vào |
| Song song | Không. Truy xuất phải cho cùng kết quả với cùng bộ lọc |
| Điều kiện dừng | Trả ký ức, câu trả lời có căn cứ, hoặc tuyến tour |
| **Cấm** | Trả ký ức khi đồng thuận đã thu hồi / hết hạn / đã xoá · trả câu trả lời không có trích dẫn cho câu hỏi cần căn cứ · mutate ký ức gốc · ghi DB · gọi agent khác |
| Cổng | VF-SCHEMA, VF-TRACE |

## Đồng thuận là bộ lọc, không phải nhãn trang trí

`retrieve_filtered` loại thẳng ký ức có `consent_status` là `revoked`/`expired`,
ký ức đã xoá, và ký ức hết hạn lưu. Không có tham số nào để bỏ qua bộ lọc này —
nếu có, nó sẽ bị dùng "cho tiện" ở đâu đó và biến cam kết quyền riêng tư thành
lời hứa suông.

## Trả lời phải nói được nguồn

Mỗi `GroundedAnswer` mang `citation_memory_ids`. Khi không tìm thấy ký ức nào
liên quan, câu trả lời phải nói thẳng là chưa có căn cứ thay vì suy diễn. Quán
dùng lớp này để nhân viên tra cứu, nên một câu trả lời không nguồn còn tệ hơn
không trả lời.

## Tái dùng, không nhân bản

Lớp này dựng trên `ag_explain/episodic_memory` qua adapter và **không** sửa ký ức
gốc. Bản sao duy nhất là read-model phục vụ hiển thị. Nhờ vậy sổ vết gốc vẫn là
nguồn sự thật cho `/vet`, và không có hai bản ký ức lệch nhau.
