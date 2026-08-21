# Hiện trạng quán — 7 con số (hồ sơ §3.3)

> Chế độ hiện tại: **Quán Fixture** (ADR-012). Cột “giá trị fixture” lấy từ giả thuyết hồ sơ §3.2 để team không bị chặn; cột “giá trị quán thật” để trống đến khi đo tại quán.

| # | Chỉ số | Giá trị fixture | Nhãn | Giá trị quán thật | Ngày đo thật |
|---|--------|-----------------|------|-------------------|--------------|
| 1 | Phút quản lý xếp lịch một tuần | 180 | gia_thuyet_ho_so (2,5–4h) | chưa đo | |
| 2 | Số ca đổi sau chốt (tuần) | 8 | gia_thuyet_ho_so | chưa đo | |
| 3 | Tổng NV / SV có TKB | 25 / 20 | synthetic seed | chưa đo | |
| 4 | Ai làm cuối tuần nhiều/ít nhất (8 tuần) | xem `data/seed/sample.json` fairness later | synthetic | chưa đo | |
| 5 | Ngày sổ mở/đóng ghi bù (tuần) | 3 | gia_thuyet_ho_so | chưa đo | |
| 6 | Việc treo bỏ rơi — lần gần + hậu quả | “hầu như mỗi ngày” (hồ sơ) | gia_thuyet_ho_so | chưa đo | |
| 7 | Hết hàng giữa cao điểm / tháng | 4 | gia_thuyet_ho_so | chưa đo | |

## Quan sát ca mở quán

- Nguồn YAML hiện tại: `infra/templates/mo_quan.yaml` — **mẫu kỹ thuật từ hồ sơ §8.4**, chưa ngồi ca ngoài đời.
- Khi D ngồi ca thật: ghi thứ tự vào đây và diff với YAML.
