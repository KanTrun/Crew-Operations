---
name: solver-scheduling
description: "Kỹ năng chuẩn bị dữ liệu và kích hoạt bộ giải xếp ca tất định CP-SAT (Google OR-Tools) với các ràng buộc C01–C06."
disable-model-invocation: true
metadata:
  role: operating
  package: packages/solver
---

# Solver Scheduling Skill

Sử dụng kỹ năng này khi cần giải quyết bài toán xếp lịch ca làm việc cho nhân viên quán cà phê, đổi ca hoặc kiểm tra tính khả thi của lịch trực.

## 1. Điều kiện tiên quyết & Kiểm tra nhanh (Smoke Check)

Trước khi gửi dữ liệu tới CP-SAT solver, chạy script kiểm tra định dạng dữ liệu:

```bash
python skills/repositories/repo-skills/solver-scheduling/scripts/validate_solver_payload.py <input.json>
```

Nếu chạy không tham số, script sẽ tự chạy smoke check với dữ liệu mẫu:
```bash
python skills/repositories/repo-skills/solver-scheduling/scripts/validate_solver_payload.py
```

## 2. Các ràng buộc cốt lõi cần tuân thủ

Xem chi tiết tại [references/constraints_c01_c06.md](references/constraints_c01_c06.md):
- **C01:** Không trùng lịch học (TKB).
- **C02:** Đủ số người tối thiểu và đúng kỹ năng vị trí (barista, thu ngân).
- **C03:** Một nhân viên không thể ở hai ca cùng lúc.
- **C04:** Đảm bảo khoảng cách nghỉ tối thiểu giữa hai ca liên tiếp.
- **C05:** Không vượt quá trần giờ tuần.
- **C06:** Không phân ca vào ngày đã duyệt nghỉ phép.

## 3. Quy trình thực thi chuẩn cho Agent

1. **Chuẩn bị payload JSON:** Bao gồm danh sách `nhan_vien`, `ca_ids`, `ca_meta`, `tkb`, `nghi_phep`.
2. **Kiểm tra sơ bộ:** Thực thi `scripts/validate_solver_payload.py`. Nếu trả về `valid: false`, agent phản hồi ngay cho người dùng các lỗi cụ thể thay vì gọi solver.
3. **Giải bài toán:** Gọi API xếp ca hoặc import `ca_solver.solve_cpsat` (tùy cấu hình `SKILL_BACKEND=local|api`).
4. **Giải trình (Explain):** Nếu vô nghiệm, sử dụng bảng mã lý do `MA_VO_NGHIEM` từ `ca_solver.explain` để thông báo rõ ràng cho người quản lý.
