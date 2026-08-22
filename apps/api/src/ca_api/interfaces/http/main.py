"""HTTP entry — health, login, roster, Sprint 3–5 ops."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from ca_contracts import Ca, LichTuan, NhanVien, PhieuMau, RangBuocTrichXuat
from ca_playbook import record_sua
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ca_api.interfaces.http.sprint3 import router as sprint3_router
from ca_api.interfaces.http.sprint45 import router as sprint45_router
from ca_api.persist import kv_get, kv_mutate
from ca_api.persist import login as persist_login
from ca_api.persist import session as auth_session

app = FastAPI(title="NHIP QUAN API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(sprint3_router)
app.include_router(sprint45_router)

ROOT = Path(__file__).resolve().parents[6]
SEED = ROOT / "data" / "seed" / "sample.json"
LICH_TUAN_OUT = ROOT / "data" / "out" / "lich_tuan.json"

# Pins persist in SQLite kv


def _pin_map() -> dict[tuple[str, str], bool]:
    raw = kv_get("pins", {})
    out: dict[tuple[str, str], bool] = {}
    for key, val in raw.items():
        ca_id, nv_id = str(key).split("|", 1)
        out[(ca_id, nv_id)] = bool(val)
    return out


def _set_pin(ca_id: str, nv_id: str, pinned: bool) -> bool:
    state = {"prev": False}

    def mut(raw: dict[str, bool]) -> dict[str, bool]:
        key = f"{ca_id}|{nv_id}"
        state["prev"] = bool(raw.get(key, False))
        raw[key] = pinned
        return raw

    kv_mutate("pins", mut, {})
    return state["prev"]


class LoginBody(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    role: str
    display_name: str
    nv_id: str


class PinBody(BaseModel):
    ca_id: str
    nv_id: str
    pinned: bool


def _seed() -> dict:
    if not SEED.exists():
        return {"nhan_vien": [], "ca_mau_21": [], "lich_su_8_tuan": []}
    return json.loads(SEED.read_text(encoding="utf-8"))


def _resolve_role(authorization: str | None) -> str | None:
    s = auth_session(authorization)
    return None if s is None else s["role"]


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
    # Map ca_id → list of nv_ids (round-robin assignment)
    phan_cong: dict[str, list[str]] = {}
    for i, ca in enumerate(ca_list):
        ca_id = ca["id"]
        assigned = [nhan_vien[j]["id"] for j in range(min(2, len(nhan_vien))) if (i + j) % 3 != 2]
        phan_cong[ca_id] = assigned
    for (ca_id, nv_id), pinned in _pin_map().items():
        if pinned and nv_id not in phan_cong.get(ca_id, []):
            phan_cong.setdefault(ca_id, []).append(nv_id)
        elif not pinned and nv_id in phan_cong.get(ca_id, []):
            phan_cong[ca_id].remove(nv_id)
    return {
        "nguon": "quan",
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
    """Lịch tuần đang hiệu lực của quán."""
    # Try data/out/lich_tuan.json first (solver output)
    if LICH_TUAN_OUT.exists():
        data = json.loads(LICH_TUAN_OUT.read_text(encoding="utf-8"))
        seed = _seed()
        phan_cong = dict(data.get("phan_cong", {}))
        for (ca_id, nv_id), pinned in _pin_map().items():
            if pinned and nv_id not in phan_cong.get(ca_id, []):
                phan_cong.setdefault(ca_id, []).append(nv_id)
            elif not pinned and nv_id in phan_cong.get(ca_id, []):
                phan_cong[ca_id].remove(nv_id)
        return {
            "nguon": "quan",
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
    prev = _set_pin(body.ca_id, body.nv_id, body.pinned)
    record_sua(
        loai="pin_ca",
        truoc={"ca_id": body.ca_id, "nv_id": body.nv_id, "pinned": prev},
        sau={"ca_id": body.ca_id, "nv_id": body.nv_id, "pinned": body.pinned},
        ai=_role,
        now_iso=datetime.now(UTC).isoformat(),
    )
    return {"ok": True, "ca_id": body.ca_id, "nv_id": body.nv_id, "pinned": body.pinned}


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/api/v1/auth/login", response_model=LoginOut)
def login(body: LoginBody) -> LoginOut:
    row = persist_login(body.username, body.password)
    if not row:
        raise HTTPException(status_code=401, detail="sai_thong_tin_dang_nhap")
    return LoginOut(
        token=row["token"],
        role=row["role"],
        display_name=row["display_name"],
        nv_id=row["nv_id"],
    )


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
        id="rb_01",
        nguon="tkb",
        noi_dung="T2 ca sáng — ràng buộc từ TKB",
        do_tin_cay=0.9,
    )
    return {
        "nguon": "quan",
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
