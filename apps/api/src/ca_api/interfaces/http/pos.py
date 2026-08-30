"""Quầy nội bộ: menu, đơn pha chế và số tiêu thụ ước lượng.

Không có khách hàng hay cổng thanh toán trong router này.  Mọi đơn đều do
người đang làm ca ghi tại quầy và luôn có nhãn ``quay_noi_bo``.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from ca_contracts import DonQuay, DongDon, MonNuoc
from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import _require_chu_quan, _require_manager, _require_role
from ca_api.persist import (
    NangVaiLoi,
    audit_add,
    da_diem_danh,
    db_path,
    don_get,
    don_insert,
    don_list,
    don_update,
    ha_vai,
    list_users,
    menu_get,
    menu_list,
    menu_set_hinh,
    menu_upsert,
    set_role,
    tieu_thu_append,
)
from ca_api.persist import (
    session as auth_session,
)

router = APIRouter()

_MON_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
_STATUS_NEXT = {
    "cho_pha": {"dang_pha", "huy"},
    "dang_pha": {"xong", "huy"},
    "xong": set(),
    "huy": set(),
}
_DON_VI_BOM = {
    "cafe_g": "g",
    "sua_ml": "ml",
    "dao_lat": "lát",
    "ly": "ly",
}


class MonBody(BaseModel):
    ten: str = Field(min_length=1, max_length=120)
    gia: int = Field(ge=0, le=10_000_000)
    an: bool = False
    hinh_url: str = Field(default="", max_length=500)
    bom: dict[str, float] = Field(default_factory=dict)


class DongDatBody(BaseModel):
    mon_id: str = Field(min_length=2, max_length=64)
    so_luong: int = Field(ge=1, le=99)


class TaoDonBody(BaseModel):
    dong: list[DongDatBody] = Field(min_length=1, max_length=30)
    thanh_toan: Literal["tien_mat", "da_ck", "chua_thu"] = "chua_thu"


class ChuyenDonBody(BaseModel):
    trang_thai: Literal["dang_pha", "xong", "huy"]
    ly_do_huy: str = Field(default="", max_length=300)


class ChinhDonBody(BaseModel):
    dong: list[DongDatBody] = Field(min_length=1, max_length=30)
    thanh_toan: Literal["tien_mat", "da_ck", "chua_thu"]


class NangVaiBody(BaseModel):
    role: Literal["quan_ly"] = "quan_ly"


def _menu_image_dir() -> Path:
    base = db_path().parent / "menu_images"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _menu_image_path(mon_id: str) -> Path | None:
    mid = mon_id.strip().lower()
    base = _menu_image_dir()
    for ext in (".webp", ".jpg", ".jpeg", ".png", ".gif"):
        p = base / f"{mid}{ext}"
        if p.is_file():
            return p
    return None


def _session(authorization: str | None) -> dict[str, str]:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    return s


def _require_dang_ca(authorization: str | None) -> dict[str, str]:
    s = _session(authorization)
    if not da_diem_danh(s["nv_id"]):
        raise HTTPException(status_code=403, detail="chua_diem_danh")
    return s


def _audit(ai: str, hanh: str, payload: dict[str, Any]) -> None:
    audit_add(datetime.now(UTC).isoformat(), ai, hanh, payload)


def _dong_theo_menu(rows: list[DongDatBody]) -> list[dict[str, Any]]:
    dong: list[dict[str, Any]] = []
    for row in rows:
        mon = menu_get(row.mon_id)
        if not mon or mon["an"]:
            raise HTTPException(status_code=404, detail="mon_khong_ban")
        dong.append(
            DongDon(
                mon_id=mon["id"], ten=mon["ten"], so_luong=row.so_luong, gia=mon["gia"]
            ).model_dump()
        )
    return dong


def _can_cham_don(don: dict[str, Any], authorization: str | None) -> dict[str, str]:
    s = _require_dang_ca(authorization)
    if s["role"] == "nhan_vien" and don["nv_id"] != s["nv_id"]:
        raise HTTPException(status_code=403, detail="khong_phai_don_ca_minh")
    return s


def _ghi_tieu_thu_uoc_luong(don: dict[str, Any], ai: str) -> None:
    """Ghi một dòng cho từng thành phần BOM, chỉ tại chuyển trạng thái sang xong."""
    for dong in don["dong"]:
        mon = menu_get(str(dong["mon_id"]))
        if not mon:
            continue
        for hang, mot_don_vi in mon["bom"].items():
            try:
                so_luong = float(mot_don_vi) * int(dong["so_luong"])
            except (TypeError, ValueError):
                continue
            if so_luong <= 0:
                continue
            tieu_thu_append(
                {
                    "id": f"ttq_{uuid.uuid4().hex[:10]}",
                    "hang": hang,
                    "so_luong": so_luong,
                    "don_vi": _DON_VI_BOM.get(hang, "đơn vị"),
                    "duoi_nguong": False,
                    "ai": ai,
                    "luc": datetime.now(UTC).isoformat(),
                    "nguon": "uoc_luong_tu_quay",
                    "don_quay_id": don["id"],
                    "ghi": "Ước lượng từ quầy nội bộ, không phải số Grab.",
                }
            )


def _don_cho_role(
    authorization: str | None, *, trang_thai: str | None = None
) -> list[dict[str, Any]]:
    s = _require_dang_ca(authorization)
    items = don_list(trang_thai=trang_thai)
    if s["role"] == "nhan_vien":
        return [x for x in items if x["nv_id"] == s["nv_id"]]
    return items


@router.get("/api/v1/menu")
def menu(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    return {
        "items": menu_list(),
        "nguon": "quan",
        "ghi": "Menu quầy nội bộ, không phải storefront khách.",
    }


@router.get("/api/v1/menu/quan-tri")
def menu_quan_tri(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_chu_quan(authorization)
    return {"items": menu_list(gom_an=True), "nguon": "quan"}


@router.put("/api/v1/menu/{mon_id}")
def menu_luu(
    mon_id: str,
    body: MonBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_chu_quan(authorization)
    mid = mon_id.strip().lower()
    if not _MON_ID.fullmatch(mid):
        raise HTTPException(status_code=422, detail="ma_mon_khong_hop_le")
    try:
        mon = MonNuoc(id=mid, **body.model_dump()).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="mon_khong_hop_le") from exc
    out = menu_upsert(mon)
    _audit(role, "menu_luu", {"id": mid, "an": out["an"], "gia": out["gia"]})
    return {**out, "nguon": "quan"}


@router.get("/api/v1/nguoi")
def nguoi_list(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_chu_quan(authorization)
    return {"items": list_users(), "nguon": "quan"}


@router.post("/api/v1/nguoi/{username}/nang-vai")
def nguoi_nang_vai(
    username: str,
    body: NangVaiBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_chu_quan(authorization)
    try:
        out = set_role(username, body.role)
    except NangVaiLoi as exc:
        raise HTTPException(status_code=409, detail=exc.ma) from exc
    _audit(role, "nang_vai", {"username": out["username"], "role": out["role"]})
    return {**out, "nguon": "quan"}


@router.post("/api/v1/nguoi/{username}/ha-vai")
def nguoi_ha_vai(
    username: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_chu_quan(authorization)
    try:
        out = ha_vai(username)
    except NangVaiLoi as exc:
        raise HTTPException(status_code=409, detail=exc.ma) from exc
    _audit(role, "ha_vai", {"username": out["username"], "role": out["role"]})
    return {**out, "nguon": "quan"}


@router.get("/api/v1/menu/{mon_id}/anh")
def menu_anh_get(mon_id: str) -> FileResponse:
    """Ảnh món — public read để <img> không cần Bearer."""
    path = _menu_image_path(mon_id)
    if not path:
        raise HTTPException(status_code=404, detail="khong_co_anh")
    return FileResponse(path)


@router.post("/api/v1/menu/{mon_id}/anh")
async def menu_anh_upload(
    mon_id: str,
    file: UploadFile = File(...),
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_chu_quan(authorization)
    mid = mon_id.strip().lower()
    if not _MON_ID.fullmatch(mid):
        raise HTTPException(status_code=422, detail="ma_mon_khong_hop_le")
    if not menu_get(mid):
        raise HTTPException(status_code=404, detail="mon_khong_co")
    raw = await file.read()
    if len(raw) > 4_000_000:
        raise HTTPException(status_code=413, detail="anh_qua_lon")
    suffix = Path(file.filename or "img.jpg").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"
    dest = _menu_image_dir() / f"{mid}{suffix}"
    for old in _menu_image_dir().glob(f"{mid}.*"):
        if old != dest:
            old.unlink(missing_ok=True)
    dest.write_bytes(raw)
    url = f"/api/v1/menu/{mid}/anh"
    out = menu_set_hinh(mid, url)
    return {**(out or {}), "hinh_url": url, "nguon": "quan"}


@router.get("/api/v1/quay/don")
def quay_don_list(
    trang_thai: Literal["cho_pha", "dang_pha", "xong", "huy"] | None = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    return {"items": _don_cho_role(authorization, trang_thai=trang_thai), "nguon": "quay_noi_bo"}


@router.post("/api/v1/quay/don", status_code=201)
def quay_don_tao(
    body: TaoDonBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    s = _require_dang_ca(authorization)
    raw = {
        "id": f"dq_{uuid.uuid4().hex[:10]}",
        "nv_id": s["nv_id"],
        "trang_thai": "cho_pha",
        "thanh_toan": body.thanh_toan,
        "dong": _dong_theo_menu(body.dong),
        "luc": datetime.now(UTC).isoformat(),
    }
    don = DonQuay.model_validate(raw).model_dump()
    don_insert(don)
    _audit(s["role"], "quay_tao_don", {"id": don["id"], "nv_id": don["nv_id"]})
    return don


@router.post("/api/v1/quay/don/{don_id}/chuyen")
def quay_don_chuyen(
    don_id: str,
    body: ChuyenDonBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    don = don_get(don_id)
    if not don:
        raise HTTPException(status_code=404, detail="don_khong_tim_thay")
    s = _can_cham_don(don, authorization)
    cur = don["trang_thai"]
    if body.trang_thai not in _STATUS_NEXT.get(cur, set()):
        raise HTTPException(status_code=409, detail=f"chuyen_khong_hop_le:{cur}->{body.trang_thai}")
    if body.trang_thai == "huy" and not body.ly_do_huy.strip():
        raise HTTPException(status_code=422, detail="can_ly_do_huy")
    don["trang_thai"] = body.trang_thai
    don["ly_do_huy"] = body.ly_do_huy.strip() if body.trang_thai == "huy" else None
    don_update(don)
    if body.trang_thai == "xong":
        _ghi_tieu_thu_uoc_luong(don, s["role"])
    _audit(s["role"], "quay_chuyen_don", {"id": don_id, "from": cur, "to": body.trang_thai})
    return don


@router.post("/api/v1/quay/don/{don_id}/chinh")
def quay_don_chinh(
    don_id: str,
    body: ChinhDonBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    s = _require_dang_ca(authorization)
    if s["role"] not in {"quan_ly", "chu_quan"}:
        raise HTTPException(status_code=403, detail="forbidden")
    don = don_get(don_id)
    if not don:
        raise HTTPException(status_code=404, detail="don_khong_tim_thay")
    if don["trang_thai"] in {"xong", "huy"}:
        raise HTTPException(status_code=409, detail="don_da_ket_thuc")
    don["dong"] = _dong_theo_menu(body.dong)
    don["thanh_toan"] = body.thanh_toan
    don_update(don)
    _audit(s["role"], "quay_chinh_don", {"id": don_id})
    return don


@router.get("/api/v1/quay/bao-cao")
def quay_bao_cao(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_manager(authorization)
    items = [x for x in don_list() if x["trang_thai"] != "huy"]
    tong_ly = sum(int(row["so_luong"]) for don in items for row in don["dong"])
    tong_tien = sum(int(row["so_luong"]) * int(row["gia"]) for don in items for row in don["dong"])
    chua_thu = sum(
        int(row["so_luong"]) * int(row["gia"])
        for don in items
        if don["thanh_toan"] == "chua_thu"
        for row in don["dong"]
    )
    return {
        "so_don": len(items),
        "tong_ly": tong_ly,
        "tong_tien": tong_tien,
        "chua_thu": chua_thu,
        "nguon": "quay_noi_bo",
        "ghi": "Đơn ghi tại quầy nội bộ; không phải số Grab.",
    }
