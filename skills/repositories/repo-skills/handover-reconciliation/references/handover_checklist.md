# Quy Chuẩn Bàn Giao Ca & Đối Soát Tiền Két (Cash Reconciliation)

Quy trình chuẩn hóa bàn giao giữa ca sáng và ca chiều (hoặc ca tối đóng quán):

## 1. Công thức cân bằng Tiền mặt Két thu ngân
$$\text{Tiền thực tế trong két} = \text{Tiền ban đầu (Tiền lẻ đầu ca)} + \text{Doanh thu tiền mặt trên POS} - \text{Chi phí xuất két có hóa đơn}$$

- **Lệch tiền = 0 VNĐ:** Cân bằng hoàn hảo (`MATCHED`).
- **Lệch tiền âm (Thiếu tiền):** Yêu cầu thu ngân ca trước bù tiền két hoặc ghi nhận biên bản (`SHORTAGE`).
- **Lệch tiền dương (Thừa tiền):** Ghi sổ quỹ phụ thu hoặc kiểm tra bill quên thanh toán (`SURPLUS`).

## 2. Checklist Bàn giao Thiết bị & Việc Treo
- Máy POS, máy in hóa đơn đã chốt ca.
- Tủ lạnh, tủ đông đóng kín, nhiệt độ chuẩn.
- Các việc treo (`pending tasks`) được chuyển giao tường minh cho ca tiếp theo.
