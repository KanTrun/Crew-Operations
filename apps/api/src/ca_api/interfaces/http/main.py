"""HTTP entry — health + stub contracts for make demo."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="NHIP QUAN API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ca-api"}


@app.get("/api/v1/demo/contracts")
def demo_contracts() -> dict[str, object]:
    """Five contract stubs so D is not blocked (hồ sơ Sprint 1)."""
    return {
        "nhan_vien": {"count": 25, "schema": "NhanVien"},
        "ca": {"count": 21, "schema": "Ca"},
        "lich": {"schema": "LichTuan", "status": "mock"},
        "phieu": {"schemas": ["mo_quan", "dong_quan", "ban_giao_ca"]},
        "rang_buoc": {"schema": "RangBuocTrichXuat", "inbox": []},
    }
