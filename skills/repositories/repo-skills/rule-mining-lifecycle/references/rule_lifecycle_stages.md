# Vòng Đời Tự Động Hóa Luật Cẩm Nang (Rule Lifecycle Engine)

Tuân thủ nguyên tắc ADR-010 trong dự án NHỊP QUÁN:

```
[Ghi nhận sự cố] ──> [Tìm mẫu >= 3 lần] ──> [Đề xuất AG-RULE]
                                                     │
[Đào thải tự động < 80%] <── [Tham số hóa lõi] <── [Người duyệt] <── [Tập sự 5 ca]
```

## Các Giai đoạn Cốt lõi
1. **Ghi nhận (Record):** Mọi chỉnh sửa lịch hoặc thao tác can thiệp thủ công đều được lưu vết.
2. **Tìm mẫu (Mining - Ngưỡng 3 lần):** Nếu một lý do sửa đổi lặp lại từ 3 lần trở lên (ví dụ: "Lan luôn xin nghỉ sáng T4 vì học thêm"), hệ thống đánh dấu là một MẪU TIỀM NĂNG (`candidate_pattern`).
3. **Đề xuất luật:** AG-RULE sinh câu quy tắc ngắn gọn (ví dụ: *"Không xếp Lan vào ca sáng T4"*).
4. **Tập sự (Trial - 5 ca):** Luật chạy thử nghiệm ngầm trong 5 ca tiếp theo để đo độ chính xác.
5. **Duyệt chính thức:** Quản lý bấm 1-Click Duyệt để luật trở thành một ràng buộc cứng trong Solver.
