"""Load YAML phiếu templates and run a deterministic checklist."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

ROOT = Path(__file__).resolve().parents[4]
TEMPLATES = ROOT / "infra" / "templates"


@dataclass
class BuocState:
    ma: str
    ten: str
    minh_chung: str
    done: bool = False
    gia_tri: Any = None
    completed_at_ms: int | None = None
    nguong: dict[str, Any] | None = None


@dataclass
class PhieuRun:
    id: str
    mau: str
    nv_id: str
    ca_id: str
    buoc: list[BuocState]
    started_at_ms: int
    treo: list[str] = field(default_factory=list)
    timing_ms: list[int] = field(default_factory=list)
    anti_fake: list[str] = field(default_factory=list)
    closed: bool = False

    def current(self) -> BuocState | None:
        for b in self.buoc:
            if not b.done:
                return b
        return None


def load_template(ma: str) -> dict[str, Any]:
    path = TEMPLATES / f"{ma}.yaml"
    if not path.exists():
        raise FileNotFoundError(ma)
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def start_phieu(
    *,
    run_id: str,
    mau: str,
    nv_id: str,
    ca_id: str,
    now_ms: int,
    diem_danh: bool,
) -> PhieuRun:
    tpl = load_template(mau)
    if tpl.get("mo_khi") == "nhan_vien_da_diem_danh" and not diem_danh:
        raise PermissionError("chua_diem_danh")
    buoc = [
        BuocState(
            ma=b["ma"],
            ten=b["ten"],
            minh_chung=str(b.get("minh_chung", "khong")),
            nguong=b.get("nguong") if isinstance(b.get("nguong"), dict) else None,
        )
        for b in tpl["buoc"]
    ]
    return PhieuRun(
        id=run_id,
        mau=mau,
        nv_id=nv_id,
        ca_id=ca_id,
        buoc=buoc,
        started_at_ms=now_ms,
    )


def complete_buoc(run: PhieuRun, ma: str, gia_tri: Any, now_ms: int) -> BuocState:
    if run.closed:
        raise RuntimeError("phieu_da_dong")
    cur = run.current()
    if cur is None or cur.ma != ma:
        raise ValueError("sai_thu_tu_buoc")
    if cur.minh_chung == "anh" and not _is_photo_payload(gia_tri):
        raise ValueError("thieu_minh_chung_anh")
    last = run.started_at_ms
    for b in run.buoc:
        if b.done and b.completed_at_ms is not None:
            last = b.completed_at_ms
    gap = now_ms - last
    run.timing_ms.append(gap)
    if gap < 2000:
        run.anti_fake.append(f"nhanh:{cur.ma}")
    if cur.minh_chung == "anh" and gap < 3000:
        run.anti_fake.append("anh_qua_nhanh")
    if cur.nguong and cur.minh_chung == "so":
        try:
            val = float(str(gia_tri).replace(",", "."))
        except ValueError as exc:
            raise ValueError("gia_tri_khong_phai_so") from exc
        lo, hi = cur.nguong.get("min"), cur.nguong.get("max")
        if lo is not None and val < float(lo):
            run.anti_fake.append(f"duoi_nguong:{cur.ma}")
        if hi is not None and val > float(hi):
            run.anti_fake.append(f"tren_nguong:{cur.ma}")
    cur.done = True
    cur.gia_tri = gia_tri
    cur.completed_at_ms = now_ms
    if run.current() is None:
        run.closed = True
    return cur


def add_treo(run: PhieuRun, noi_dung: str) -> None:
    text = noi_dung.strip()
    if not text:
        raise ValueError("treo_rong")
    run.treo.append(text)


def escalate(run: PhieuRun, now_ms: int, han_phut: int = 30) -> str | None:
    elapsed_min = (now_ms - run.started_at_ms) / 60_000
    if elapsed_min > han_phut * 2:
        return "bao_chu_quan"
    if elapsed_min > han_phut:
        return "nhac_nhan_vien"
    return None


def _is_photo_payload(gia_tri: Any) -> bool:
    if not isinstance(gia_tri, str):
        return False
    raw = gia_tri.strip()
    if not raw.startswith("data:image/") or "," not in raw:
        return False
    return len(raw.split(",", 1)[1]) >= 8


def _timing_by_ma(run: PhieuRun) -> dict[str, int]:
    out: dict[str, int] = {}
    i = 0
    for b in run.buoc:
        if b.done and i < len(run.timing_ms):
            out[b.ma] = run.timing_ms[i]
            i += 1
    return out


def _loai(minh_chung: str) -> str:
    if minh_chung == "anh":
        return "photo"
    if minh_chung in {"so", "kiem_ke"}:
        return "text"
    return "confirm"


def run_to_dict(run: PhieuRun) -> dict[str, Any]:
    cur = run.current()
    return {
        "id": run.id,
        "mau": run.mau,
        "nv_id": run.nv_id,
        "ca_id": run.ca_id,
        "closed": run.closed,
        "trang_thai": "hoan_thanh" if run.closed else "dang_lam",
        "treo": list(run.treo),
        "timing_ms": _timing_by_ma(run),
        "signals": {
            "timing_ms": _timing_by_ma(run),
            "anti_fake": list(run.anti_fake),
        },
        "so_buoc": len(run.buoc),
        "so_xong": sum(1 for b in run.buoc if b.done),
        "buoc_hien_tai": None if cur is None else cur.ma,
        "hien_tai": None
        if cur is None
        else {"ma": cur.ma, "ten": cur.ten, "minh_chung": cur.minh_chung},
        "buocs": [
            {
                "ma": b.ma,
                "ten": b.ten,
                "loai": _loai(b.minh_chung),
                "minh_chung": b.minh_chung,
                "hoan_thanh": b.done,
                "done": b.done,
            }
            for b in run.buoc
        ],
        "buoc": [
            {
                "ma": b.ma,
                "ten": b.ten,
                "minh_chung": b.minh_chung,
                "done": b.done,
            }
            for b in run.buoc
        ],
    }


def dump_run(run: PhieuRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "mau": run.mau,
        "nv_id": run.nv_id,
        "ca_id": run.ca_id,
        "started_at_ms": run.started_at_ms,
        "treo": list(run.treo),
        "timing_ms": list(run.timing_ms),
        "anti_fake": list(run.anti_fake),
        "closed": run.closed,
        "buoc": [
            {
                "ma": b.ma,
                "ten": b.ten,
                "minh_chung": b.minh_chung,
                "done": b.done,
                "gia_tri": b.gia_tri if not str(b.gia_tri).startswith("data:image") else "[anh]",
                "completed_at_ms": b.completed_at_ms,
                "nguong": b.nguong,
            }
            for b in run.buoc
        ],
    }


def load_run(data: dict[str, Any]) -> PhieuRun:
    buoc = [
        BuocState(
            ma=b["ma"],
            ten=b["ten"],
            minh_chung=b["minh_chung"],
            done=bool(b.get("done")),
            gia_tri=b.get("gia_tri"),
            completed_at_ms=b.get("completed_at_ms"),
            nguong=b.get("nguong"),
        )
        for b in data["buoc"]
    ]
    run = PhieuRun(
        id=data["id"],
        mau=data["mau"],
        nv_id=data["nv_id"],
        ca_id=data["ca_id"],
        buoc=buoc,
        started_at_ms=int(data["started_at_ms"]),
        treo=list(data.get("treo") or []),
        timing_ms=list(data.get("timing_ms") or []),
        anti_fake=list(data.get("anti_fake") or []),
        closed=bool(data.get("closed")),
    )
    return run
