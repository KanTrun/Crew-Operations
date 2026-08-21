"""HTTP entry — health, login stub, five contracts mock for Sprint 1 demo.

Auth roles (Sprint 2):
  quan_ly   — fixture-quanly   — full access (read + write)
  chu_quan  — fixture-chu      — full access (read + write)
  nhan_vien — fixture-nhanvien — read-only (GET only)
  <no token>                   — read-only demo access allowed on GET /lich-tuan
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from ca_contracts import Ca, LichTuan, NhanVien, PhieuMau, RangBuocTrichXuat
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="NHIP QUAN API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT = Path(__file__).resolve().parents[6]
SEED = ROOT / "data" / "seed" / "sample.json"
LICH_TUAN_OUT = ROOT / "data" / "out" / "lich_tuan.json"

# ── Fixture token → role map ──────────────────────────────────────────────────
_TOKEN_ROLE: dict[str, str] = {
    "fixture-quanly": "quan_ly",
    "fixture-chu": "chu_quan",
    "fixture-nhanvien": "nhan_vien",
}

# ── In-memory pin store ───────────────────────────────────────────────────────
_PINS: dict[tuple[str, str], bool] = {}  # (ca_id, nv_id) → pinned


class LoginBody(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    role: str
    display_name: str


class PinBody(BaseModel):
    ca_id: str
    nv_id: str
    pinned: bool


def _seed() -> dict:
    if not SEED.exists():
        return {"nhan_vien": [], "ca_mau_21": [], "lich_su_8_tuan": []}
    return json.loads(SEED.read_text(encoding="utf-8"))


def _resolve_role(authorization: str | None) -> str | None:
    """Map Bearer token → role string, or None if absent/invalid."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return _TOKEN_ROLE.get(parts[1])


def _require_write_role(authorization: Annotated[str | None, Header()] = None) -> str:
    """Dependency: require quan_ly or chu_quan for write endpoints."""
    role = _resolve_role(authorization)
    if role not in {"quan_ly", "chu_quan"}:
        raise HTTPException(
            status_code=403, detail="forbidden — requires quan_ly or chu_quan"
        )
    return role


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ca-api"}


# ── Lich tuan ─────────────────────────────────────────────────────────────────

def _build_lich_tuan_from_seed(seed: dict, tuan: str | None) -> dict:
    """Build a schedule response from seed data for the requested ISO week."""
    nhan_vien = seed.get("nhan_vien", [])
    ca_list = seed.get("ca_mau_21", [])
    # Map ca_id → list of nv_ids (simple round-robin assignment for demo)
    phan_cong: dict[str, list[str]] = {}
    for i, ca in enumerate(ca_list):
        ca_id = ca["id"]
        assigned = [nhan_vien[j]["id"] for j in range(min(2, len(nhan_vien))) if (i + j) % 3 != 2]
        phan_cong[ca_id] = assigned
    # Apply in-memory pins
    for (ca_id, nv_id), pinned in _PINS.items():
        if pinned and nv_id not in phan_cong.get(ca_id, []):
            phan_cong.setdefault(ca_id, []).append(nv_id)
        elif not pinned and nv_id in phan_cong.get(ca_id, []):
            phan_cong[ca_id].remove(nv_id)
    return {
        "nguon": "fixture_synthetic",
        "tuan_iso": tuan or "2026-W34",
        "trang_thai": "nhap",
        "nhan_vien": nhan_vien,
        "ca": ca_list,
        "phan_cong": phan_cong,
    }


@app.get("/api/v1/lich-tuan")
def get_lich_tuan(
    tuan: Annotated[str | None, Query(description="ISO week e.g. 2026-W34")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Return weekly roster. Read allowed without auth for demo.

    Auth roles:
    - quan_ly (fixture-quanly): read + write
    - chu_quan (fixture-chu): read + write
    - nhan_vien (fixture-nhanvien): read-only
    - anonymous: read-only (demo)
    """
    # Try data/out/lich_tuan.json first (solver output)
    if LICH_TUAN_OUT.exists():
        data = json.loads(LICH_TUAN_OUT.read_text(encoding="utf-8"))
        seed = _seed()
        phan_cong = dict(data.get("phan_cong", {}))
        for (ca_id, nv_id), pinned in _PINS.items():
            if pinned and nv_id not in phan_cong.get(ca_id, []):
                phan_cong.setdefault(ca_id, []).append(nv_id)
            elif not pinned and nv_id in phan_cong.get(ca_id, []):
                phan_cong[ca_id].remove(nv_id)
        return {
            "nguon": data.get("nguon", "fixture_synthetic"),
            "adr": data.get("adr", "ADR-012"),
            "tuan_iso": tuan or data.get("tuan_iso") or "2026-W34",
            "trang_thai": "may_sinh",
            "nhan_vien": seed.get("nhan_vien", []),
            "ca": seed.get("ca_mau_21", []),
            "phan_cong": phan_cong,
            "solver": {
                "ok": data.get("ok"),
                "elapsed_s": data.get("elapsed_s"),
                "status": data.get("status"),
            },
        }
    return _build_lich_tuan_from_seed(_seed(), tuan)


@app.post("/api/v1/lich-tuan/pin")
def pin_assignment(
    body: PinBody,
    _role: Annotated[str, Depends(_require_write_role)],
) -> dict:
    """Pin or unpin a nhan_vien to a ca. Requires quan_ly or chu_quan token."""
    seed = _seed()
    ca_ids = {c["id"] for c in seed.get("ca_mau_21", [])}
    nv_ids = {n["id"] for n in seed.get("nhan_vien", [])}
    if body.ca_id not in ca_ids or body.nv_id not in nv_ids:
        raise HTTPException(status_code=404, detail="ca_or_nv_not_found")
    _PINS[(body.ca_id, body.nv_id)] = body.pinned
    return {"ok": True, "ca_id": body.ca_id, "nv_id": body.nv_id, "pinned": body.pinned}


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/v1/auth/login", response_model=LoginOut)
def login(body: LoginBody) -> LoginOut:
    """Demo auth — fixture users only."""
    users = {
        "quanly": ("demo", "quan_ly", "Quản lý Fixture"),
        "nhanvien": ("demo", "nhan_vien", "Nhân viên Fixture"),
        "chu": ("demo", "chu_quan", "Chủ quán Fixture"),
    }
    row = users.get(body.username)
    if not row or body.password != row[0]:
        raise HTTPException(status_code=401, detail="sai_thong_tin_dang_nhap")
    return LoginOut(token=f"fixture-{body.username}", role=row[1], display_name=row[2])


@app.get("/api/v1/contracts")
def five_contracts() -> dict[str, object]:
    seed = _seed()
    nv = [
        NhanVien.model_validate({**x, "ky_nang": x.get("ky_nang", [])})
        for x in seed.get("nhan_vien", [])[:5]
    ]
    ca_rows = []
    for x in seed.get("ca_mau_21", [])[:5]:
        ca_rows.append(
            Ca(
                id=x["id"],
                ngay=f"2026-01-{x.get('ngay_offset', 1):02d}",
                bat_dau=x["bat_dau"],
                ket_thuc=x["ket_thuc"],
                vi_tri=x["vi_tri"],
                so_nguoi_toi_thieu=x.get("so_nguoi_toi_thieu", 1),
            )
        )
    lich = LichTuan(tuan_iso="2026-W01", trang_thai="nhap", phan_cong={})
    phieu = PhieuMau(ma="mo_quan", ten="Mở quán", buoc=[])
    rb = RangBuocTrichXuat(
        id="rb_demo",
        nguon="tkb",
        noi_dung="synthetic T2 sáng",
        do_tin_cay=0.9,
    )
    return {
        "nguon": "fixture_synthetic",
        "adr": "ADR-012",
        "NhanVien": [x.model_dump() for x in nv],
        "Ca": [x.model_dump() for x in ca_rows],
        "LichTuan": lich.model_dump(),
        "PhieuMau": phieu.model_dump(),
        "RangBuocTrichXuat": rb.model_dump(),
        "schemas": ["NhanVien", "Ca", "LichTuan", "PhieuMau", "RangBuocTrichXuat"],
    }


@app.get("/api/v1/demo/contracts")
def demo_contracts() -> dict[str, object]:
    return five_contracts()
