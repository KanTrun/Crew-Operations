# AG-RULE-LEARNING — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Phát hiện quyết định lặp lại, đóng gói thành ứng viên luật có bằng chứng, chạy thử trên dữ liệu cũ |
| Phạm vi | Nhóm tín hiệu quyết định theo mẫu · dựng read-model bằng chứng · chạy shadow test cô lập |
| Đầu vào | `DecisionSignal[]` + `snapshot_hash` · ứng viên + sự kiện lịch sử (shadow) |
| Đầu ra | `RuleCandidate[]` kèm điều kiện đã map sang VF-RULE · `EvidenceReadModel` · `ShadowTestResult` |
| Mô hình | Tất định 100%. Không LLM trong lớp này — câu luật do AG-RULE viết, ở đây chỉ phát hiện và kiểm chứng |
| Song song | Không. Cùng một tập tín hiệu phải cho cùng tập ứng viên |
| Điều kiện dừng | Trả ứng viên (có thể rỗng), bằng chứng, hoặc kết quả chạy thử |
| **Cấm** | Đề xuất luật khi dưới ngưỡng bằng chứng · tạo state machine luật thứ hai · tự kích hoạt luật · ghi DB · gọi agent khác |
| Cổng | VF-SCHEMA, VF-RULE, VF-TRACE |

## Vòng đời luật có đúng một người ghi

`vong_doi.py` (cẩm nang 8 bước, ADR-010) là **sole writer** cho trạng thái luật.
Lớp này chỉ đóng gói bằng chứng và gọi vào đó — không tự đặt trạng thái, không
giữ bảng trạng thái riêng. Nhờ vậy không có hai nguồn sự thật về việc một luật
đang ở bước nào.

## `to_vf_condition` tồn tại vì một lỗi thật

Điều kiện mà lớp này phát hiện dùng từ vựng trải nghiệm (`day_part`, `skill`),
còn VF-RULE chỉ nhận `{thu, khung, vi_tri, so_nguoi, nguong, ma_buoc,
thang_kinh_nghiem}`. Đưa thẳng `day_part` vào `vong_doi` từng gây
`truong_khong_ton_tai` ở bước kiểm chứng. Hàm map là ranh giới bắt buộc giữa hai
từ vựng, không phải tiện ích trang trí.

## Không bịa luật khi thiếu tín hiệu

Dưới ngưỡng lặp lại, `discover_rule_candidates` trả danh sách rỗng và `de_xuat`
trả `None`. Quán thà không có luật còn hơn có một câu luật bịa từ hai lần sửa.
