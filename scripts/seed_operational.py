"""Nạp dữ liệu vận hành fixture vào store để 6 bề mặt web có gì mà xem.

Đọc `data/seed/sample.json` (do `scripts/generate_fixture_data.py` sinh) và ghi
vào đúng nơi từng router đang đọc:

| khoá / tệp                     | bề mặt                               |
|--------------------------------|--------------------------------------|
| kv `treo`                      | GET /api/v1/viec-treo                |
| kv `inbox_msg`                 | GET /api/v1/inbox                    |
| kv `inbox_rang_buoc`           | GET /api/v1/inbox/rang-buoc          |
| kv `waste_notes`               | GET /api/v1/waste                    |
| kv `tieu_thu`                  | GET /api/v1/tieu-thu                 |
| kv `kiem_ke`                   | số #9 §4.3 (chưa có router riêng)    |
| `cam_nang.json` (NHIPQUAN_CAMNANG) | GET /api/v1/cam-nang             |
| `so_lan_sua.jsonl` (NHIPQUAN_SUA)  | GET /api/v1/ghi-nhan-sua         |

TẤT ĐỊNH và IDEMPOTENT: mỗi bản ghi mang `nguon="mo_phong_fixture"`; mỗi lần
nạp sẽ gỡ hết bản ghi mang nhãn đó rồi ghi lại, nên chạy bao nhiêu lần cũng ra
cùng một store và không đụng tới bản ghi do người trong quán tạo.

KHÔNG gắn nhãn quán thật: mọi dòng giữ `synthetic: True`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed" / "sample.json"
NGUON_FIXTURE = "mo_phong_fixture"

for _p in (
    ROOT / "apps" / "api" / "src",
    ROOT / "packages" / "playbook" / "src",
    ROOT / "packages" / "gates" / "src",
):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from ca_api.persist import kv_get, kv_set  # noqa: E402
from ca_playbook import list_luat, save_luat  # noqa: E402
from ca_playbook.sua import _store as sua_store  # noqa: E402

# kv nào nhận danh sách nào trong sample.json
KHOA_KV: dict[str, str] = {
    "treo": "viec_treo",
    "inbox_rang_buoc": "inbox_rang_buoc",
    "waste_notes": "hao_phi",
    "tieu_thu": "tieu_thu",
    "kiem_ke": "kiem_ke",
}


def doc_seed(path: Path | None = None) -> dict[str, Any]:
    p = path or SEED
    if not p.exists():
        raise SystemExit(f"thiếu {p} — chạy `python scripts/generate_fixture_data.py` trước")
    raw: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    return raw


def _la_cho_trong_router(r: dict[str, Any]) -> bool:
    """Mục kê tạm do `_seed_inbox()` tự đẻ: "Ràng buộc #N — chờ duyệt".

    Chúng mang `nguon="quan"` nhưng không phải ràng buộc nào của quán cả, chỉ là
    chỗ trống cho giao diện đỡ trắng. Nạp dữ liệu thật thì gỡ chúng đi.
    """
    return str(r.get("tom_tat", "")).startswith("Ràng buộc #")


def _khong_phai_fixture(rows: list[Any]) -> list[Any]:
    """Giữ lại bản ghi do quán tạo, gỡ bản ghi fixture của lần nạp trước."""
    out = []
    for r in rows:
        if isinstance(r, dict) and (r.get("nguon") == NGUON_FIXTURE or r.get("synthetic")):
            continue
        if isinstance(r, dict) and _la_cho_trong_router(r):
            continue
        out.append(r)
    return out


def _inbox_msg(inbox: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """/api/v1/inbox chỉ cần id · tom_tat · agent · trang_thai."""
    return [
        {
            "id": it["id"],
            "tom_tat": it["tom_tat"],
            "agent": it["agent"],
            "trang_thai": it["trang_thai"],
            "do_tin_cay": it.get("do_tin_cay"),
            "nguon": NGUON_FIXTURE,
            "synthetic": True,
        }
        for it in inbox
    ]


def nap_kv(seed: dict[str, Any]) -> dict[str, int]:
    dem: dict[str, int] = {}
    for khoa, nguon_khoa in KHOA_KV.items():
        moi = list(seed.get(nguon_khoa) or [])
        cu = _khong_phai_fixture(list(kv_get(khoa, [])))
        kv_set(khoa, [*cu, *moi])
        dem[khoa] = len(moi)
    inbox = _inbox_msg(list(seed.get("inbox_rang_buoc") or []))
    cu_msg = _khong_phai_fixture(list(kv_get("inbox_msg", [])))
    kv_set("inbox_msg", [*cu_msg, *inbox])
    dem["inbox_msg"] = len(inbox)
    return dem


def nap_cam_nang(seed: dict[str, Any]) -> int:
    """Upsert theo `id`: luật của quán ở lại, luật fixture ghi lại từ đầu."""
    moi = list(seed.get("luat_cam_nang") or [])
    theo_id: dict[str, dict[str, Any]] = {
        str(x.get("id")): x for x in _khong_phai_fixture(list(list_luat()))
    }
    for luat in moi:
        theo_id[str(luat["id"])] = luat
    save_luat(list(theo_id.values()))
    return len(moi)


def nap_ghi_nhan_sua(seed: dict[str, Any]) -> int:
    moi = list(seed.get("ghi_nhan_sua") or [])
    p = sua_store()
    p.parent.mkdir(parents=True, exist_ok=True)
    cu: list[dict[str, Any]] = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("nguon") == NGUON_FIXTURE:
                continue
            cu.append(row)
    dong = [json.dumps(r, ensure_ascii=False) for r in [*cu, *moi]]
    p.write_text("\n".join(dong) + "\n", encoding="utf-8")
    return len(moi)


def nap_tat_ca(seed: dict[str, Any] | None = None) -> dict[str, int]:
    doc = seed if seed is not None else doc_seed()
    dem = nap_kv(doc)
    dem["cam_nang"] = nap_cam_nang(doc)
    dem["ghi_nhan_sua"] = nap_ghi_nhan_sua(doc)
    return dem


def main() -> None:
    dem = nap_tat_ca()
    print("nap dữ liệu vận hành — nguồn:", NGUON_FIXTURE)
    for k in sorted(dem):
        print(f"  {k:20s} {dem[k]:4d}")
    print("idempotent: chạy lại không nhân bản (lọc theo nhãn nguon)")


if __name__ == "__main__":
    main()
