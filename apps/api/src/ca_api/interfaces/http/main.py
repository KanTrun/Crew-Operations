"""HTTP entry — health, login stub, five contracts mock for Sprint 1 demo."""

from __future__ import annotations

import json
from pathlib import Path

from ca_contracts import Ca, LichTuan, NhanVien, PhieuMau, RangBuocTrichXuat
from fastapi import FastAPI, HTTPException
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


class LoginBody(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    role: str
    display_name: str


def _seed() -> dict:
    if not SEED.exists():
        return {"nhan_vien": [], "ca_mau_21": [], "lich_su_8_tuan": []}
    return json.loads(SEED.read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ca-api"}


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
