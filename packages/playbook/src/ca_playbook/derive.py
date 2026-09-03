"""Suy luật luật từ lần sửa thật — deterministic, không LLM."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
_CA_CATALOG: dict[str, dict[str, Any]] | None = None

THU_LABEL: dict[str, str] = {
    "T2": "Thứ Hai",
    "T3": "Thứ Ba",
    "T4": "Thứ Tư",
    "T5": "Thứ Năm",
    "T6": "Thứ Sáu",
    "T7": "Thứ Bảy",
    "CN": "Chủ nhật",
}

KHUNG_LABEL: dict[str, str] = {
    "sang": "ca sáng",
    "chieu": "ca chiều",
    "toi": "ca tối",
}

VI_TRI_LABEL: dict[str, str] = {
    "pha_che": "pha chế",
    "kho": "kho",
    "thu_ngan": "thu ngân",
    "phuc_vu": "phục vụ",
}


_THU_OFFSET = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}


def _load_ca_catalog() -> dict[str, dict[str, Any]]:
    global _CA_CATALOG
    if _CA_CATALOG is not None:
        return _CA_CATALOG
    path = ROOT / "data" / "seed" / "sample.json"
    out: dict[str, dict[str, Any]] = {}
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        for ca in raw.get("ca_mau_21", []) or []:
            cid = str(ca.get("id") or "")
            if not cid:
                continue
            off = int(ca.get("ngay_offset") or 0)
            out[cid] = {
                **ca,
                "thu": _THU_OFFSET.get(off, ""),
            }
    _CA_CATALOG = out
    return out


def sua_rows_for_mau(mau: dict[str, Any], sua: list[dict[str, Any]]) -> list[dict[str, Any]]:
    key = str(mau.get("mau") or "khac")
    return [r for r in sua if str(r.get("loai") or "khac") == key]


def _headcount_from_row(row: dict[str, Any]) -> int:
    sau = row.get("sau")
    if isinstance(sau, dict) and isinstance(sau.get("nv"), list):
        return len(sau["nv"])
    if isinstance(sau, dict) and sau.get("nv_id"):
        return 1
    return 0


def _ca_id_from_row(row: dict[str, Any]) -> str:
    for side in ("sau", "truoc"):
        blob = row.get(side)
        if isinstance(blob, dict) and blob.get("ca_id"):
            return str(blob["ca_id"])
    return ""


def derive_rule_from_edits(mau: dict[str, Any], sua_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Suy luật có cấu trúc từ các lần sửa cùng loại. Trả None nếu không đủ tín hiệu."""
    if len(sua_rows) < 3:
        return None

    counts: list[int] = []
    ca_ids: list[str] = []
    for row in sua_rows:
        counts.append(_headcount_from_row(row))
        cid = _ca_id_from_row(row)
        if cid:
            ca_ids.append(cid)

    if not counts:
        return None

    so_nguoi = max(counts)
    if so_nguoi < 1:
        return None

    ca_id = max(set(ca_ids), key=ca_ids.count) if ca_ids else ""
    meta = _load_ca_catalog().get(ca_id, {})
    thu = str(meta.get("thu") or "")
    khung = str(meta.get("khung") or "")
    vi_tri = str(meta.get("vi_tri") or "")

    parts: list[str] = []
    if thu and thu in THU_LABEL:
        parts.append(THU_LABEL[thu])
    if khung and khung in KHUNG_LABEL:
        parts.append(KHUNG_LABEL[khung])
    elif khung:
        parts.append(f"ca {khung}")
    if vi_tri and vi_tri in VI_TRI_LABEL:
        parts.append(f"vị trí {VI_TRI_LABEL[vi_tri]}")
    when = " ".join(parts) if parts else (f"ca {ca_id}" if ca_id else "ca làm việc")

    cau = f"{when.capitalize()} cần ít nhất {so_nguoi} người trong ca (từ {len(sua_rows)} lần sửa tương tự)."

    dieu_kien: dict[str, Any] = {"so_nguoi": so_nguoi}
    if thu:
        dieu_kien["thu"] = thu
    if khung:
        dieu_kien["khung"] = khung
    if vi_tri:
        dieu_kien["vi_tri"] = vi_tri

    return {
        "cau": cau,
        "loai": str(mau.get("loai_luat") or "nhu_cau_ca"),
        "dieu_kien": dieu_kien,
        "bang_chung": list(mau.get("bang_chung") or [])[:4],
    }
