"""Cẩm nang sống — 8 bước từ lần sửa đến tham số lõi (hồ sơ §9.2)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ca_gates.vf_rule import validate_rule

from ca_playbook.sua import list_sua

ROOT = Path(__file__).resolve().parents[4]
STORE = ROOT / "data" / "out" / "cam_nang.json"

LOAI_TU_SUA = {
    "nhan_ca": "nhu_cau_ca",
    "nha_ca": "nhu_cau_ca",
    "pin_ca": "ghep_ky_nang",
}


def _path(path: Path | None = None) -> Path:
    if path is not None:
        return path
    override = os.environ.get("NHIPQUAN_CAMNANG")
    return Path(override) if override else STORE


def _load(path: Path | None = None) -> list[dict[str, Any]]:
    p = _path(path)
    if not p.exists():
        return []
    raw = json.loads(p.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else raw.get("items", [])


def _save(items: list[dict[str, Any]], path: Path | None = None) -> None:
    p = _path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def tim_mau(sua: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = sua if sua is not None else list_sua()
    buckets: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        loai = str(r.get("loai") or "khac")
        buckets.setdefault(loai, []).append(r)
    out = []
    for loai, items in buckets.items():
        if len(items) >= 3:
            out.append(
                {
                    "mau": loai,
                    "loai_luat": LOAI_TU_SUA.get(loai, "nhu_cau_ca"),
                    "n": len(items),
                    "bang_chung": [str(i) for i, _ in enumerate(items[:10])],
                    "nguon": (
                        "dung_lai_8_tuan"
                        if all(x.get("synthetic") for x in items)
                        else "ghi_truc_tiep"
                    ),
                }
            )
    return out


def de_xuat(mau: dict[str, Any]) -> dict[str, Any]:
    luat = {
        "id": f"luat_{mau['mau']}",
        "loai": mau["loai_luat"],
        "cau": "Thứ Bảy ca chiều cần 3 người pha chế, không phải 2",
        "dieu_kien": {"thu": "T7", "khung": "chieu", "vi_tri": "pha_che", "so_nguoi": 3},
        "bang_chung": mau["bang_chung"][:4],
        "buoc": 3,
        "nguon": mau.get("nguon", "dung_lai_8_tuan"),
        "tap_su": [],
        "ap_dung": 0,
        "ghi_de": 0,
        "trang_thai": "de_xuat",
    }
    return luat


def kiem_chung(luat: dict[str, Any]) -> dict[str, Any]:
    r = validate_rule(luat)
    luat = dict(luat)
    if r.passed:
        luat["buoc"] = 4
        luat["trang_thai"] = "qua_vf_rule"
        luat["vf_rule"] = "dat"
    else:
        luat["buoc"] = 4
        luat["trang_thai"] = "loai"
        luat["vf_rule"] = r.reason
    return luat


def tap_su(luat: dict[str, Any], lan: list[tuple[str, str]]) -> dict[str, Any]:
    """lan = (he_thong_se_lam, nguoi_da_lam) × 5."""
    luat = dict(luat)
    bang = [{"he_thong": a, "nguoi": b, "dung": a == b} for a, b in lan]
    luat["tap_su"] = bang
    dung = sum(1 for x in bang if x["dung"])
    luat["tap_su_dung"] = dung
    luat["buoc"] = 5
    luat["trang_thai"] = "du_tap_su" if dung >= 4 else "truot_tap_su"
    return luat


def duyet(luat: dict[str, Any], *, ok: bool, ai: str) -> dict[str, Any]:
    luat = dict(luat)
    luat["nguoi_duyet"] = ai
    if not ok:
        luat["trang_thai"] = "tu_choi"
        return luat
    luat["buoc"] = 7
    luat["trang_thai"] = "hieu_luc"
    luat["tham_so_loi"] = dict(luat.get("dieu_kien") or {})
    return luat


def theo_doi(luat: dict[str, Any], *, dung: int, ghi_de: int) -> dict[str, Any]:
    luat = dict(luat)
    luat["ap_dung"] = dung + ghi_de
    luat["ghi_de"] = ghi_de
    total = dung + ghi_de
    ti_le = (dung / total) if total else 1.0
    luat["ti_le_dung"] = ti_le
    luat["buoc"] = 8
    if total and ti_le < 0.8:
        luat["trang_thai"] = "tu_tat"
    return luat


def list_luat(path: Path | None = None) -> list[dict[str, Any]]:
    return _load(path)


def save_luat(items: list[dict[str, Any]], path: Path | None = None) -> None:
    _save(items, path)
