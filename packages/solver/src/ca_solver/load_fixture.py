"""Load ADR-012 seed into LichInput (+ synthetic sparse TKB)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from ca_solver.model import LichInput

_THU = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}
ROOT = Path(__file__).resolve().parents[4]


def load_labor_params(path: Path | None = None) -> dict[str, Any]:
    import yaml

    p = path or ROOT / "config" / "tham-so-lao-dong.yaml"
    return cast(dict[str, Any], yaml.safe_load(p.read_text(encoding="utf-8")))


def load_seed(path: Path | None = None) -> dict[str, Any]:
    p = path or ROOT / "data" / "seed" / "sample.json"
    return cast(dict[str, Any], json.loads(p.read_text(encoding="utf-8")))


def build_lich_input(
    seed: dict[str, Any] | None = None,
    *,
    tuan_index: int = 0,
    debt: dict[str, dict[str, float]] | None = None,
) -> LichInput:
    """Build empty assignment input for CP-SAT (phan_cong starts empty)."""
    seed = seed or load_seed()
    params = load_labor_params()
    nvs = seed["nhan_vien"]
    cas = seed["ca_mau_21"]
    nv_ids = [x["id"] for x in nvs]
    ca_ids = [x["id"] for x in cas]
    ca_meta: dict[str, dict[str, str]] = {}
    so_nguoi: dict[str, int] = {}
    vi_tri: dict[str, str] = {}
    for c in cas:
        thu = _THU[int(c["ngay_offset"])]
        ca_meta[c["id"]] = {
            "thu": thu,
            "bat_dau": c["bat_dau"],
            "ket_thuc": c["ket_thuc"],
            "khung": c.get("khung", ""),
        }
        so_nguoi[c["id"]] = int(c.get("so_nguoi_toi_thieu", 1))
        vi_tri[c["id"]] = c["vi_tri"]
    ky_nang = {x["id"]: set(x.get("ky_nang", [])) for x in nvs}
    # Sparse synthetic TKB: odd-id students busy Tue morning only — keeps solve feasible
    tkb: dict[str, list[tuple[str, str, str]]] = {}
    for x in nvs:
        if x.get("la_sinh_vien") and x["id"].endswith(("1", "3", "5", "7", "9")):
            tkb[x["id"]] = [("T2", "07:00", "10:00")]
    nghi: set[tuple[str, str]] = set()
    # One approved leave: nv_25 on Sunday
    if "nv_25" in nv_ids:
        nghi.add(("nv_25", "CN"))
    return LichInput(
        nhan_vien_ids=nv_ids,
        ca_ids=ca_ids,
        phan_cong={cid: [] for cid in ca_ids},
        tkb=tkb,
        ca_meta=ca_meta,
        ky_nang=ky_nang,
        vi_tri_can=vi_tri,
        so_nguoi_toi_thieu=so_nguoi,
        nghi_phep=nghi,
        gio_da_lam={},
        tran_gio_tuan=float(params["tran_gio_tuan"]),
        khoang_nghi_gio=float(params["khoang_nghi_toi_thieu_gio"]),
        debt=debt or {nid: {"cuoi_tuan": 0, "dem": 0, "gio": 0, "vun": 0} for nid in nv_ids},
        soft_enabled=True,
    )
