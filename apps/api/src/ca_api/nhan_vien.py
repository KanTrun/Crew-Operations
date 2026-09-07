"""Nguồn nhân viên hợp nhất để xếp lịch — users thật + seed lịch sử.

Vấn đề gốc (đã audit): `build_lich_input` chỉ đọc `data/seed/sample.json`,
nên nhân viên tự đăng ký (bảng `users`) không bao giờ xuất hiện trong lịch
tuần. Module này là một nguồn duy nhất (SSOT) cho solver và API:

- `users` (SQLite/Postgres): nhân viên thật của quán — đăng ký qua
  `/api/v1/auth/register`, nâng/hạ vai qua `/nguoi`.
- seed `nhan_vien`: chỉ dùng cho dữ liệu lịch sử (nợ công bằng 8 tuần, TKB
  synthetic) và làm fallback khi DB trống (demo sạch).

Quy tắc gộp: NV thật (users) luôn thắng trùng id; NV seed chỉ vào khi
không trùng. Mọi người có `ky_nang` mặc định `da_nang` để không bị solver
chặn vì thiếu kỹ năng vị trí.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
SEED = ROOT / "data" / "seed" / "sample.json"

# Kỹ năng mặc định cho NV chưa khai báo hồ sơ: phủ mọi vị trí ca mẫu
# (solver C02 so khớp ky_nang với vi_tri — "da_nang" một mình bị chặn).
# Chủ quán có thể thu hẹp sau khi có hồ sơ kỹ năng thật.
KY_NANG_MAC_DINH = ["da_nang", "thu_ngan", "pha_che", "phuc_vu", "kho"]


def _seed_nhan_vien() -> list[dict[str, Any]]:
    if not SEED.exists():
        return []
    try:
        return list(json.loads(SEED.read_text(encoding="utf-8")).get("nhan_vien", []))
    except Exception:
        return []


def list_nhan_vien_ops(include_seed: bool | None = None) -> list[dict[str, Any]]:
    """Danh sách nhân viên dùng được cho xếp lịch, ưu tiên users thật.

    Trả list bản ghi dạng `{id, ten, vai, ky_nang, la_sinh_vien}`.
    `include_seed` mặc định đọc env `NHIPQUAN_LOI_GIAI_SEED`. Mặc định TẮT:
    quán vận hành thật chỉ dùng nhân viên thật (users) — seed ADR-012 chỉ
    dành cho dev/test/demo (set =1 trong .env khi cần lịch sử công bằng).
    """
    if include_seed is None:
        include_seed = os.environ.get("NHIPQUAN_LOI_GIAI_SEED", "0").strip().lower() in {"1", "true", "yes", "on"}

    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    # 1. NV thật từ bảng users — nguồn sự thật của quán
    try:
        from ca_api.persist import list_users

        for u in list_users():
            nv_id = str(u.get("nv_id") or "").strip()
            if not nv_id or nv_id in seen:
                continue
            seen.add(nv_id)
            out.append(
                {
                    "id": nv_id,
                    "ten": str(u.get("display_name") or u.get("username") or nv_id),
                    "vai": str(u.get("role") or "nhan_vien"),
                    "ky_nang": KY_NANG_MAC_DINH,
                    "la_sinh_vien": False,
                    "nguon": "users",
                }
            )
    except Exception:
        # persist chưa sẵn sàng (chạy solver độc lập) — bỏ qua, còn seed
        pass

    # 2. NV seed (lịch sử / demo) — chỉ thêm id chưa có
    if include_seed:
        for x in _seed_nhan_vien():
            nv_id = str(x.get("id") or "")
            if not nv_id or nv_id in seen:
                continue
            seen.add(nv_id)
            out.append(
                {
                    "id": nv_id,
                    "ten": str(x.get("ten") or nv_id),
                    "vai": "nhan_vien",
                    "ky_nang": list(x.get("ky_nang") or KY_NANG_MAC_DINH),
                    "la_sinh_vien": bool(x.get("la_sinh_vien")),
                    "nguon": "seed",
                }
            )
    return out
