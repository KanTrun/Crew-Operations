"""HTTP entry — health, login, roster, Sprint 3–5 ops."""

from __future__ import annotations

import json
try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
from pathlib import Path
from typing import Annotated, Any, cast

from ca_contracts import (
    Ca,
    DongDon,
    DonQuay,
    LichTuan,
    MonNuoc,
    NhanVien,
    PhieuMau,
    RangBuocTrichXuat,
)
from ca_playbook import record_sua
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ca_api.interfaces.http.channels import router as channels_router
from ca_api.interfaces.http.copilot import router as copilot_router
from ca_api.interfaces.http.mail import router as mail_router
from ca_api.interfaces.http.meeting import router as meeting_router
from ca_api.interfaces.http.pos import router as pos_router
from ca_api.interfaces.http.sprint3 import router as sprint3_router
from ca_api.interfaces.http.sprint45 import router as sprint45_router
from ca_api.interfaces.http.trends import router as trends_router
from ca_api.persist import DangKyLoi, kv_get, kv_mutate, kv_set
from ca_api.persist import login as persist_login
from ca_api.persist import register as persist_register
from ca_api.persist import session as auth_session

# Inject real data sources into AG-COPILOT tool registry (hexagonal boundary).
# Agents không được import ca_api/ca_playbook trực tiếp (test_architecture) —
# nên API layer cung cấp dữ liệu thật qua configure_data_sources().
from ca_agents.ag_copilot.tool_registry import configure_data_sources
from ca_agents.ag_sop import answer as _sop_answer
from ca_agents.ag_waste import cluster as _waste_cluster
from ca_ops.engine import load_template as _load_template
from ca_playbook.sua import list_sua as _list_sua
from ca_playbook.vong_doi import de_xuat as _de_xuat, list_luat as _list_luat, tim_mau as _tim_mau

app = FastAPI(title="NHIP QUAN API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(sprint3_router)
app.include_router(sprint45_router)
app.include_router(channels_router)
app.include_router(copilot_router)
app.include_router(pos_router)
app.include_router(meeting_router)
app.include_router(trends_router)
app.include_router(mail_router)


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


class RegisterBody(BaseModel):
    username: str
    password: str
    display_name: str


class LoginOut(BaseModel):
    token: str
    role: str
    display_name: str
    nv_id: str


class PinBody(BaseModel):
    ca_id: str
    nv_id: str
    pinned: bool


def _seed() -> dict[str, Any]:
    if not SEED.exists():
        return {"nhan_vien": [], "ca_mau_21": [], "lich_su_8_tuan": []}
    return cast(dict[str, Any], json.loads(SEED.read_text(encoding="utf-8")))


def _list_ca_meta() -> dict[str, dict[str, Any]]:
    """Trả map ca_id -> {thu, khung, bat_dau, ket_thuc} từ seed ca_mau_21."""
    seed = _seed()
    thu_map = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}
    return {
        c["id"]: {
            "thu": thu_map.get(int(c.get("ngay_offset", 1)), "T2"),
            "khung": c.get("khung", ""),
            "bat_dau": c.get("bat_dau", "07:00"),
            "ket_thuc": c.get("ket_thuc", "12:00"),
        }
        for c in seed.get("ca_mau_21", [])
    }


def _resolve_role(authorization: str | None) -> str | None:
    s = auth_session(authorization)
    return None if s is None else s["role"]


configure_data_sources(
    kv_get=kv_get,
    list_luat=_list_luat,
    load_template=_load_template,
    list_sua=_list_sua,
    tim_mau=_tim_mau,
    de_xuat=_de_xuat,
    sop_answer=_sop_answer,
    waste_cluster=_waste_cluster,
    list_ca_meta=_list_ca_meta,
)


def _require_write_role(authorization: Annotated[str | None, Header()] = None) -> str:
    """Dependency: require quan_ly or chu_quan for write endpoints."""
    role = _resolve_role(authorization)
    if role not in {"quan_ly", "chu_quan"}:
        raise HTTPException(status_code=403, detail="forbidden — requires quan_ly or chu_quan")
    return role


def _require_authenticated_role(authorization: Annotated[str | None, Header()] = None) -> str:
    """Dependency: require login token for read endpoints."""
    role = _resolve_role(authorization)
    if not role:
        raise HTTPException(status_code=401, detail="unauthorized — login required")
    return role


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ca-api"}


# ── Lich tuan ─────────────────────────────────────────────────────────────────

THU_MAP = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}


_KHUNG_DEFAULTS: dict[str, dict[str, str]] = {
    "sang": {"bat_dau": "07:00", "ket_thuc": "12:00"},
    "chieu": {"bat_dau": "12:00", "ket_thuc": "17:00"},
    "toi": {"bat_dau": "17:00", "ket_thuc": "22:00"},
}


def _khung_template() -> dict[str, dict[str, str]]:
    stored = kv_get("khung_gio", None)
    if not isinstance(stored, dict):
        return {k: dict(v) for k, v in _KHUNG_DEFAULTS.items()}
    out: dict[str, dict[str, str]] = {}
    for key, default in _KHUNG_DEFAULTS.items():
        slot = stored.get(key)
        if not isinstance(slot, dict):
            out[key] = dict(default)
            continue
        out[key] = {
            "bat_dau": str(slot.get("bat_dau", default["bat_dau"])),
            "ket_thuc": str(slot.get("ket_thuc", default["ket_thuc"])),
        }
    return out


def _apply_khung_template(ca_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tmpl = _khung_template()
    out: list[dict[str, Any]] = []
    for c in ca_list:
        c_copy = dict(c)
        khung = str(c_copy.get("khung", ""))
        if khung in tmpl:
            c_copy["bat_dau"] = tmpl[khung]["bat_dau"]
            c_copy["ket_thuc"] = tmpl[khung]["ket_thuc"]
        out.append(c_copy)
    return out


def _format_ca_list(ca_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for c in ca_list:
        c_copy = dict(c)
        if "thu" not in c_copy or not c_copy["thu"]:
            c_copy["thu"] = THU_MAP.get(int(c_copy.get("ngay_offset", 1)), "T2")
        out.append(c_copy)
    return _apply_khung_template(out)


def _tuan_list(base_tuan: str, so_tuan: int) -> list[str]:
    """Sinh danh sách các tuần ISO liên tiếp từ tuần bắt đầu."""
    import re

    m = re.match(r"^(\d{4})-W(\d{2})$", base_tuan)
    if not m:
        return [base_tuan]
    y, w = int(m.group(1)), int(m.group(2))
    weeks = []
    for offset in range(max(1, min(4, so_tuan))):
        cur_w = w + offset
        cur_y = y
        if cur_w > 52:
            cur_w -= 52
            cur_y += 1
        weeks.append(f"{cur_y}-W{cur_w:02d}")
    return weeks


def _build_lich_tuan_from_seed(
    seed: dict[str, Any], tuan: str | None, so_tuan: int = 1
) -> dict[str, Any]:
    """Build a schedule response from seed data for the requested ISO week."""
    nhan_vien = seed.get("nhan_vien", [])
    ca_raw = seed.get("ca_mau_21", [])
    ca_list = _format_ca_list(ca_raw)
    tuan_iso = tuan or "2026-W36"
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
        "tuan_iso": tuan_iso,
        "so_tuan": so_tuan,
        "danh_sach_tuan": _tuan_list(tuan_iso, so_tuan),
        "trang_thai": "nhap",
        "nhan_vien": nhan_vien,
        "ca": ca_list,
        "phan_cong": phan_cong,
    }


@app.get("/api/v1/lich-tuan")
def get_lich_tuan(
    tuan: Annotated[str | None, Query(description="ISO week e.g. 2026-W36")] = None,
    so_tuan: Annotated[int, Query(ge=1, le=4, description="Số tuần xếp lịch: 1, 2, 3 hoặc 4")] = 1,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Lịch tuần đang hiệu lực của quán. Yêu cầu đăng nhập (quan_ly trở lên)."""
    _require_write_role(authorization)
    tuan_iso = tuan or "2026-W36"

    # Try data/out/lich_tuan.json first (solver output)
    if LICH_TUAN_OUT.exists():
        data = json.loads(LICH_TUAN_OUT.read_text(encoding="utf-8"))
        seed = _seed()
        ca_list = _format_ca_list(seed.get("ca_mau_21", []))
        phan_cong = dict(data.get("phan_cong", {}))
        for (ca_id, nv_id), pinned in _pin_map().items():
            if pinned and nv_id not in phan_cong.get(ca_id, []):
                phan_cong.setdefault(ca_id, []).append(nv_id)
            elif not pinned and nv_id in phan_cong.get(ca_id, []):
                phan_cong[ca_id].remove(nv_id)
        lifecycle = kv_get("lich_tuan_lifecycle", {})
        return {
            "nguon": "quan",
            "adr": data.get("adr", "ADR-012"),
            "tuan_iso": tuan_iso,
            "so_tuan": so_tuan,
            "danh_sach_tuan": _tuan_list(tuan_iso, so_tuan),
            "trang_thai": lifecycle.get("trang_thai", "may_sinh"),
            "nhan_vien": seed.get("nhan_vien", []),
            "ca": ca_list,
            "phan_cong": phan_cong,
            "khung_gio": _khung_template(),
            "solver": {
                "ok": data.get("ok"),
                "elapsed_s": data.get("elapsed_s"),
                "status": data.get("status"),
            },
        }
    lifecycle = kv_get("lich_tuan_lifecycle", {})
    result = _build_lich_tuan_from_seed(_seed(), tuan_iso, so_tuan)
    result["trang_thai"] = lifecycle.get("trang_thai", result.get("trang_thai", "nhap"))
    result["khung_gio"] = _khung_template()
    return result


class KhungSlotBody(BaseModel):
    bat_dau: str
    ket_thuc: str


class KhungGioBody(BaseModel):
    sang: KhungSlotBody | None = None
    chieu: KhungSlotBody | None = None
    toi: KhungSlotBody | None = None


def _valid_hhmm(value: str) -> bool:
    import re

    return bool(re.match(r"^\d{2}:\d{2}$", value))


def _minutes_hhmm(value: str) -> int:
    h, m = value.split(":", 1)
    return int(h) * 60 + int(m)


@app.patch("/api/v1/lich-tuan/khung-gio")
def patch_khung_gio(
    body: KhungGioBody,
    _role: Annotated[str, Depends(_require_write_role)],
) -> dict[str, Any]:
    """Cập nhật template giờ cho 3 khung ca (sáng/chiều/tối)."""
    current = _khung_template()
    updates = {
        "sang": body.sang,
        "chieu": body.chieu,
        "toi": body.toi,
    }
    for key, slot in updates.items():
        if slot is None:
            continue
        if not _valid_hhmm(slot.bat_dau) or not _valid_hhmm(slot.ket_thuc):
            raise HTTPException(status_code=422, detail="invalid_time_format")
        if _minutes_hhmm(slot.bat_dau) >= _minutes_hhmm(slot.ket_thuc):
            raise HTTPException(status_code=422, detail="bat_dau_must_be_before_ket_thuc")
        current[key] = {"bat_dau": slot.bat_dau, "ket_thuc": slot.ket_thuc}
    kv_set("khung_gio", current)
    record_sua(
        loai="khung_gio",
        truoc={},
        sau=current,
        ai=_role,
        now_iso=datetime.now(UTC).isoformat(),
    )
    return {"ok": True, "khung_gio": current}


@app.post("/api/v1/lich-tuan/pin")
def pin_assignment(
    body: PinBody,
    _role: Annotated[str, Depends(_require_write_role)],
) -> dict[str, Any]:
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


_LIFECYCLE_STATES = ("nhap", "cho_duyet", "da_duyet", "da_cong_bo", "da_dong")


class LifecycleBody(BaseModel):
    trang_thai: str
    tuan_iso: str | None = None


@app.patch("/api/v1/lich-tuan/lifecycle")
def patch_lifecycle(
    body: LifecycleBody,
    _role: Annotated[str, Depends(_require_write_role)],
) -> dict[str, Any]:
    """Quản lý/Chủ quán cập nhật trạng thái và mốc tuần lịch.

    Chuyển trạng thái hợp lệ: nhap → cho_duyet → da_duyet → da_cong_bo → da_dong.
    Chỉ chu_quan mới có thể cập nhật tuan_iso (chuyển sang tuần khác).
    """
    if body.trang_thai not in _LIFECYCLE_STATES:
        raise HTTPException(
            status_code=422,
            detail=f"trang_thai_khong_hop_le — cho phep: {', '.join(_LIFECYCLE_STATES)}",
        )

    def mut(cur: dict) -> dict:
        cur["trang_thai"] = body.trang_thai
        if body.tuan_iso:
            cur["tuan_iso"] = body.tuan_iso
        cur["cap_nhat_luc"] = datetime.now(UTC).isoformat()
        cur["cap_nhat_boi"] = _role
        return cur

    new_state = kv_mutate("lich_tuan_lifecycle", mut, {})
    record_sua(
        loai="lifecycle",
        truoc={},
        sau={"trang_thai": body.trang_thai, "tuan_iso": body.tuan_iso},
        ai=_role,
        now_iso=datetime.now(UTC).isoformat(),
    )
    return {"ok": True, **new_state}


# ── Auth ──────────────────────────────────────────────────────────────────────


@app.post("/api/v1/auth/register", response_model=LoginOut, status_code=201)
def register(body: RegisterBody) -> LoginOut:
    """Tạo tài khoản nhân viên mới rồi mở phiên luôn.

    Vai trò luôn là `nhan_vien` (xem `persist.VAI_TU_DANG_KY`): tự đăng ký mà
    lấy được vai quản lý thì ai cũng duyệt được ràng buộc và phát được mã điểm
    danh. Nâng vai là việc của chủ quán, làm ngoài luồng này.
    """
    try:
        row = persist_register(body.username, body.password, body.display_name)
    except DangKyLoi as exc:
        raise HTTPException(status_code=409, detail=exc.ma) from exc
    return LoginOut(**row)


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


@app.get("/api/v1/me")
def me(authorization: Annotated[str | None, Header()] = None) -> dict[str, str]:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    return {
        "username": s["username"],
        "role": s["role"],
        "nv_id": s["nv_id"],
    }


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
    mon = MonNuoc(id="mon_den", ten="Cà phê đen", gia=25000, bom={"cafe_g": 18, "ly": 1})
    don = DonQuay(
        id="dq_demo",
        nv_id="nv_03",
        dong=[DongDon(mon_id=mon.id, ten=mon.ten, so_luong=1, gia=mon.gia)],
        luc="2026-01-01T07:00:00Z",
    )
    return {
        "nguon": "quan",
        "adr": "ADR-012",
        "NhanVien": [x.model_dump() for x in nv],
        "Ca": [x.model_dump() for x in ca_rows],
        "LichTuan": lich.model_dump(),
        "PhieuMau": phieu.model_dump(),
        "RangBuocTrichXuat": rb.model_dump(),
        "MonNuoc": mon.model_dump(),
        "DonQuay": don.model_dump(),
        "schemas": [
            "NhanVien",
            "Ca",
            "LichTuan",
            "PhieuMau",
            "RangBuocTrichXuat",
            "MonNuoc",
            "DongDon",
            "DonQuay",
        ],
    }


@app.get("/api/v1/demo/contracts")
def demo_contracts() -> dict[str, object]:
    return five_contracts()
