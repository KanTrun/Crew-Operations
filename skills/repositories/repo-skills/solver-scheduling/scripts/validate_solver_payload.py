#!/usr/bin/env python3
"""Script kiểm tra tính hợp lệ của dữ liệu đầu vào cho bộ giải xếp ca CP-SAT.

Chạy độc lập (standalone) không cần DB để kiểm tra nhanh payload từ agent.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VALID_THU = {"T2", "T3", "T4", "T5", "T6", "T7", "CN"}
HHMM_REGEX = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def validate_solver_payload(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    # 1. Kiểm tra các trường bắt buộc
    required_fields = ["nhan_vien", "ca_ids", "ca_meta"]
    for f in required_fields:
        if f not in data:
            errors.append(f"MISSING_FIELD: Thiếu trường bắt buộc '{f}'")

    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    nhan_vien = data.get("nhan_vien", [])
    ca_ids = data.get("ca_ids", [])
    ca_meta = data.get("ca_meta", {})

    if not isinstance(nhan_vien, list) or len(nhan_vien) == 0:
        errors.append("EMPTY_STAFF: Danh sách nhân viên phải là list không rỗng.")

    if not isinstance(ca_ids, list) or len(ca_ids) == 0:
        errors.append("EMPTY_SHIFTS: Danh sách ca làm việc (ca_ids) phải là list không rỗng.")

    # 2. Kiểm tra metadata từng ca
    for cid in ca_ids:
        meta = ca_meta.get(cid)
        if not meta:
            errors.append(f"MISSING_CA_META: Không tìm thấy ca_meta cho ca '{cid}'")
            continue

        thu = meta.get("thu")
        if thu not in VALID_THU:
            errors.append(f"INVALID_THU: Ca '{cid}' có thứ '{thu}' không hợp lệ (phải thuộc {sorted(VALID_THU)})")

        bat = meta.get("bat_dau")
        ket = meta.get("ket_thuc")
        if not bat or not HHMM_REGEX.match(bat):
            errors.append(f"INVALID_TIME: Ca '{cid}' có giờ bắt đầu '{bat}' không đúng định dạng HH:MM")
        if not ket or not HHMM_REGEX.match(ket):
            errors.append(f"INVALID_TIME: Ca '{cid}' có giờ kết thúc '{ket}' không đúng định dạng HH:MM")

        if bat and ket and HHMM_REGEX.match(bat) and HHMM_REGEX.match(ket):
            if _to_min(bat) >= _to_min(ket):
                errors.append(f"INVALID_DURATION: Ca '{cid}' có giờ kết thúc ({ket}) <= giờ bắt đầu ({bat})")

    # 3. Kiểm tra TKB nếu có
    tkb = data.get("tkb", {})
    for nv, blocks in tkb.items():
        if nv not in nhan_vien:
            warnings.append(f"UNKNOWN_STAFF_TKB: Nhân viên '{nv}' có TKB nhưng không nằm trong danh sách nhan_vien")
        for b in blocks:
            if not isinstance(b, (list, tuple)) or len(b) != 3:
                errors.append(f"INVALID_TKB_FORMAT: TKB của '{nv}' có định dạng sai (yêu cầu [thu, bat_dau, ket_thuc]): {b}")
            else:
                b_thu, b0, b1 = b
                if b_thu not in VALID_THU or not HHMM_REGEX.match(b0) or not HHMM_REGEX.match(b1):
                    errors.append(f"INVALID_TKB_VALUE: Giá trị TKB của '{nv}' không hợp lệ: {b}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_shifts": len(ca_ids),
        "total_staff": len(nhan_vien),
    }


def main() -> int:
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            print(json.dumps({"valid": False, "errors": [f"FILE_READ_ERROR: {e}"]}, ensure_ascii=False, indent=2))
            return 1
    else:
        # Chạy test mẫu smoke check nếu không truyền tham số
        payload = {
            "nhan_vien": ["lan", "hung", "minh"],
            "ca_ids": ["ca_sang_t2", "ca_chieu_t2"],
            "ca_meta": {
                "ca_sang_t2": {"thu": "T2", "bat_dau": "07:00", "ket_thuc": "12:00"},
                "ca_chieu_t2": {"thu": "T2", "bat_dau": "12:00", "ket_thuc": "17:00"},
            },
            "so_nguoi_toi_thieu": {"ca_sang_t2": 1, "ca_chieu_t2": 1},
        }

    res = validate_solver_payload(payload)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
