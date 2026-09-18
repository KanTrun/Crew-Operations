# AG-TWIN — phạm vi

| Thuộc tính | Giá trị |
|---|---|
| Nhiệm vụ | Mô phỏng "nếu... thì..." bằng Math Layer + nhân viên ảo |
| Phạm vi | Chạy kịch bản mô phỏng (tăng giá, thêm nhân sự...) & mô phỏng hành vi nhân viên ảo |
| Đầu vào | `{scenario_id, loai, tham_so, baseline}` / `{simulation_id, kich_ban, staff_rows}` |
| Đầu ra | `{ket_qua, rui_ro}` / `{simulation}` |
| Mô hình | Math Layer thuần (ADR-002) — không I/O, không bất định |
| Song song | Có. Mỗi kịch bản độc lập |
| Điều kiện dừng | Trả kết quả mô phỏng, hoặc rỗng nếu thiếu tham số |
| **Cấm** | Ghi DB · gọi agent khác (trừ `ag_predict.math_layer` — module toán thuần) · I/O mạng · nguồn bất định · quyết định luồng |
| Cổng | VF-SCHEMA, VF-NUM |

## Vì sao dùng `ag_predict.math_layer`

`math_layer` là module toán học thuần (ADR-002), không phải agent. `ag_twin`
tái sử dụng nó để tính toán kịch bản mà không vi phạm quy tắc "agent không gọi
agent khác".