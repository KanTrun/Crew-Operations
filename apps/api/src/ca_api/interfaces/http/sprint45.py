"""Sprint 4–5 HTTP — lifecycle, audit, inbox, fairness, playbook, SOP, QR, swap."""

from __future__ import annotations

import json
import hashlib
import os
import uuid
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, cast

try:
    from datetime import UTC, date, datetime, timedelta
except ImportError:
    from datetime import date, datetime, timedelta, timezone

    UTC = timezone.utc

from ca_agents.ag_handover import extract as extract_handover
from ca_agents.ag_rule import propose as propose_rule
from ca_agents.ag_sop import answer as sop_answer
from ca_agents.ag_sop.context import load_all_buoc
from ca_agents.ag_sop.ops import default_ops_context, ops_context_from_dict
from ca_agents.ag_waste import cluster as cluster_waste
from ca_agents.smart_swap import find_swap_candidates
from ca_gates import present_conflict, validate_num
from ca_playbook import (
    count_luat_that_quan,
    de_xuat,
    derive_rule_from_edits,
    duyet,
    enrich_luat_ui,
    go_luat,
    kiem_chung,
    list_luat,
    list_sua,
    pipeline_snapshot,
    save_luat,
    sua_rows_for_mau,
    tap_su_tu_sua,
    tim_mau,
)
from ca_solver.fairness import AXES, update_debt_from_assignment, zero_debt
from fastapi import APIRouter, Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import (
    _known_ca,
    _known_nv,
    _require_chu_quan,
    _require_manager,
    _require_role,
)
from ca_api.nhan_vien import list_nhan_vien_ops
from ca_api.orchestration import Clock
from ca_api.persist import (
    audit_add,
    audit_list,
    availability_confirmed_list,
    ghi_diem_danh,
    kv_get,
    kv_mutate,
    kv_set,
    list_users,
    open_shift_create,
    open_shift_list,
    shift_application_claim_first,
    thong_bao_lich_ack,
    thong_bao_lich_create_for_week,
    thong_bao_lich_list,
)
from ca_api.persist import session as auth_session
from ca_api.services.chat_ws import notify_ops_changed
from ca_api.services.scheduling_service import resolve_schedule_gaps, run_authoritative_schedule

router = APIRouter()
ROOT = Path(__file__).resolve().parents[6]
SEED = ROOT / "data" / "seed" / "sample.json"


def _lich_out() -> Path:
    """Output solver — đọc MỖI LẦN GỌI, không phải lúc import module.

    Conftest set ``NHIPQUAN_LICH_TUAN_OUT`` per-test (sau import), nên nếu
    đọc env một lần lúc import thì test vẫn ghi đè ``data/out/lich_tuan.json``
    thật của quán. Đọc mỗi lần gọi mới trỏ đúng tmp_path của test.
    """
    env = os.environ.get("NHIPQUAN_LICH_TUAN_OUT")
    if env:
        return Path(env)
    return ROOT / "data" / "out" / "lich_tuan.json"
_clock = Clock()
_THU_MAP = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}
_VI_TRI_VI = {
    "thu_ngan": "Thu ngân",
    "pha_che": "Pha chế",
    "phuc_vu": "Phục vụ",
    "kho": "Kho",
    "quan_ly_ca": "Quản lý ca",
    "da_nang": "Đa năng",
}
_ALLOWED = {
    "may_sinh": {"nhap"},
    "nhap": {"dang_giai"},
    "dang_giai": {"cho_duyet", "nhap"},
    "cho_duyet": {"da_duyet", "nhap"},
    "da_duyet": {"da_cong_bo"},
    "da_cong_bo": {"da_dong"},
    "da_dong": {"nhap"},
}
_REASON = {
    "cuoi_tuan": "R-WKND",
    "dem": "R-NIGHT",
    "gio": "R-HRS",
    "vun": "R-SHORT",
}


def _la_ban_ghi_mau(row: Any) -> bool:
    """Một bản ghi là dữ liệu mẫu khi mang nhãn fixture hoặc id fx_."""
    if not isinstance(row, dict):
        return False
    if row.get("nguon") == "mo_phong_fixture":
        return True
    return str(row.get("id") or "").startswith("fx_")


def _co_du_lieu_mau(rows: Any) -> bool:
    """True khi danh sách có ít nhất một bản ghi fixture — để UI gắn nhãn mẫu."""
    if not isinstance(rows, list):
        return False
    return any(_la_ban_ghi_mau(r) for r in rows)


def _audit(hanh: str, ai: str, payload: dict[str, Any]) -> None:
    audit_add(_clock.now_iso(), ai, hanh, payload)


def _week_value(key: str, tuan_iso: str, default: Any) -> Any:
    """Read week-scoped KV with a one-way compatible fallback to legacy data."""
    raw = kv_get(key, None)
    if isinstance(raw, dict) and raw:
        return raw.get(tuan_iso, default)
    if key.endswith("_by_week"):
        legacy = kv_get(key.removesuffix("_by_week"), None)
        if legacy is not None:
            return legacy
    return default


def _set_week_value(key: str, tuan_iso: str, value: Any) -> None:
    def mut(raw: dict[str, Any]) -> dict[str, Any]:
        raw[tuan_iso] = value
        return raw

    kv_mutate(key, mut, {})


def _publish_schedule_notification(week: str) -> int:
    """Persist one exact-week notification for each active real account."""
    recipients = [
        str(user.get("nv_id") or "")
        for user in list_users()
        if user.get("role") in {"nhan_vien", "quan_ly", "chu_quan"}
        and str(user.get("status") or "active") == "active"
        and str(user.get("nv_id") or "")
    ]
    return thong_bao_lich_create_for_week(
        tuan_iso=week,
        su_kien="da_cong_bo",
        tieu_de=f"Lịch tuần {week} đã được công bố",
        noi_dung="Lịch mới đã sẵn sàng. Mở để xem ca làm và xác nhận lịch của bạn.",
        url=f"/lich-tuan?tuan={week}",
        nv_ids=recipients,
    )


@router.get("/api/v1/lich/thong-bao")
def lich_notifications(
    unread_only: bool = False,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = _require_role_session(authorization)
    items = thong_bao_lich_list(str(session.get("nv_id") or ""), unread_only=unread_only)
    return {"ok": True, "notifications": items, "unread": sum(1 for item in items if not item.get("da_xem"))}


@router.post("/api/v1/lich/thong-bao/{notification_id}/ack")
def ack_lich_notification(
    notification_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = _require_role_session(authorization)
    return {"ok": thong_bao_lich_ack(notification_id, str(session.get("nv_id") or ""))}


def _previous_week(tuan_iso: str) -> str | None:
    try:
        year, week = tuan_iso.split("-W")
        previous = date.fromisocalendar(int(year), int(week), 1) - timedelta(days=7)
        iso = previous.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    except (TypeError, ValueError):
        return None


def _run_solver(
    tuan_iso: str | None = None,
    *,
    extra_pin: tuple[str, str] | None = None,
    confirmed_availability: dict[str, dict[str, list[str]]] | None = None,
) -> dict[str, Any]:
    from ca_solver import apply_luat, build_lich_input, solve_cpsat

    from ca_api.nhan_vien import list_nhan_vien_ops

    inp = build_lich_input(nhan_vien_ngoai=list_nhan_vien_ops())
    tuan_hien_tai = tuan_iso or _life().get("tuan_iso", "2026-W01")

    if confirmed_availability is not None:
        allowed_ids = set(confirmed_availability)
        inp.nhan_vien_ids = [nv_id for nv_id in inp.nhan_vien_ids if nv_id in allowed_ids]
        # CP-SAT treats TKB as unavailable time. Replace synthetic TKB with
        # explicit blocks for every shift that was not confirmed available.
        khung_gio_for_availability = kv_get("khung_gio", {})
        shift_frames = {
            "Sáng": ("06:30", "12:00"),
            "Chiều": ("12:00", "17:30"),
            "Tối": ("17:30", "22:30"),
        }
        for shift, frame in shift_frames.items():
            configured = khung_gio_for_availability.get(shift) if isinstance(khung_gio_for_availability, dict) else None
            if isinstance(configured, dict):
                shift_frames[shift] = (str(configured.get("bat_dau") or frame[0]), str(configured.get("ket_thuc") or frame[1]))
        inp.tkb = {
            nv_id: [
                (day, *shift_frames[shift])
                for day in _THU_MAP.values()
                for shift in shift_frames
                if shift not in (confirmed_availability.get(nv_id) or {}).get(day, [])
            ]
            for nv_id in inp.nhan_vien_ids
        }

    # Giờ ca do quản lý cấu hình phải là đầu vào thật của CP-SAT.
    khung_gio = kv_get("khung_gio", {})
    if isinstance(khung_gio, dict):
        for meta in inp.ca_meta.values():
            frame = khung_gio.get(meta.get("khung", ""))
            if isinstance(frame, dict):
                meta["bat_dau"] = str(frame.get("bat_dau") or meta["bat_dau"])
                meta["ket_thuc"] = str(frame.get("ket_thuc") or meta["ket_thuc"])

    debt = _week_value("fairness_debt_by_week", tuan_hien_tai, {})
    if isinstance(debt, dict) and debt:
        inp.debt = debt
    previous_week = _previous_week(str(tuan_hien_tai))
    if previous_week:
        previous_assignments = _week_value("phan_cong_by_week", previous_week, {})
        if isinstance(previous_assignments, dict):
            inp.phan_cong_tuan_truoc = {
                str(ca_id): list(nv_ids)
                for ca_id, nv_ids in previous_assignments.items()
                if isinstance(nv_ids, list)
            }

    # TKB đã xác nhận từ ảnh đè lên (hoặc bổ sung) TKB synthetic của fixture.
    by_week = kv_get("tkb_nv_by_week", {})
    stored = by_week.get(tuan_hien_tai, {}) if isinstance(by_week, dict) else {}
    legacy = kv_get("tkb_nv", {})
    if isinstance(legacy, dict):
        stored = dict(stored) if isinstance(stored, dict) else {}
        for nv_id, entry in legacy.items():
            if (
                nv_id not in stored
                and isinstance(entry, dict)
                and entry.get("tuan_iso") == tuan_hien_tai
            ):
                stored[nv_id] = entry
    if isinstance(stored, dict):
        for nv_id, entry in stored.items():
            if not isinstance(entry, dict):
                continue
            blocks = entry.get("khoang_ban") or []
            tuples: list[tuple[str, str, str]] = []
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                thu = str(b.get("thu") or "")
                start = str(b.get("start") or "")
                end = str(b.get("end") or "")
                if thu and start and end:
                    tuples.append((thu, start, end))
            if tuples:
                if confirmed_availability is not None:
                    existing_tkb = inp.tkb.setdefault(str(nv_id), [])
                    for block in tuples:
                        if block not in existing_tkb:
                            existing_tkb.append(block)
                else:
                    inp.tkb[str(nv_id)] = tuples

    # Tôn trọng quyết định du_bi hoặc bo_ca của quản lý trong tuần hiện tại: không xếp ca cố định
    status_store = kv_get("roster_nv_status", {})
    week_decisions = status_store.get(tuan_hien_tai, {}) if isinstance(status_store, dict) else {}
    for d_nvid, st in week_decisions.items():
        if st in {"du_bi", "bo_ca"}:
            for d_thu in ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]:
                inp.nghi_phep.add((str(d_nvid), d_thu))

    # Đọc các ràng buộc từ inbox_rang_buoc đã được duyệt khớp tuần hiện tại
    inbox_items = kv_get("inbox_rang_buoc", [])
    added_nghi: set[tuple[str, str]] = set()
    added_tkb: set[tuple[str, str, str, str]] = set()

    if isinstance(inbox_items, list):
        for it in inbox_items:
            if not isinstance(it, dict) or it.get("trang_thai") != "duyet":
                continue
            hl = it.get("hieu_luc")
            if not isinstance(hl, dict) or hl.get("loai") != "rang_buoc_cho_solver":
                continue

            # Ngữ cảnh tuần: chỉ nạp item khớp tuần đang giải
            rb_raw = it.get("rang_buoc")
            rb = rb_raw if isinstance(rb_raw, dict) else {}
            it_tuan = rb.get("tuan_id") or hl.get("tuan_id")
            if it_tuan and it_tuan != tuan_hien_tai:
                continue

            nv_id = str(it.get("nv_id") or hl.get("nv_id") or "")
            if not nv_id or nv_id == "unknown":
                continue

            y = str(it.get("y_dinh") or "")
            # rb đã chuẩn hóa dict ở trên (dòng 148) — không gán lại.
            thu = str(rb.get("thu") or hl.get("thu") or "")

            if y == "xin_nghi" and thu:
                pair = (nv_id, thu)
                if pair not in added_nghi:
                    added_nghi.add(pair)
                    inp.nghi_phep.add(pair)
            elif y in {"cap_nhat_tkb", "bao_tre"} and thu:
                start = str(rb.get("start") or hl.get("start") or "07:00")
                end = str(rb.get("end") or hl.get("end") or "12:00")
                key = (nv_id, thu, start, end)
                if key not in added_tkb:
                    added_tkb.add(key)
                    inp.tkb.setdefault(nv_id, []).append((thu, start, end))

    # Ghim ca từ KV "pins"
    raw_pins = _week_value("pins_by_week", tuan_hien_tai, {})
    if isinstance(raw_pins, dict):
        for pin_key, is_pinned in raw_pins.items():
            if is_pinned and "|" in str(pin_key):
                ca_id, nv_id = str(pin_key).split("|", 1)
                if ca_id in inp.ca_ids and nv_id in inp.nhan_vien_ids:
                    inp.phan_cong.setdefault(ca_id, [])
                    if nv_id not in inp.phan_cong[ca_id]:
                        inp.phan_cong[ca_id].append(nv_id)
    if extra_pin:
        ca_id, nv_id = extra_pin
        inp.phan_cong.setdefault(ca_id, [])
        if nv_id not in inp.phan_cong[ca_id]:
            inp.phan_cong[ca_id].append(nv_id)

    inp, applied = apply_luat(inp, list_luat())
    result = solve_cpsat(inp, time_limit_s=60.0)

    # Phân tích danh sách xung đột cụ thể nếu INFEASIBLE hoặc không ok
    danh_sach_xung_dot: list[str] = []
    if not result.ok or "INFEASIBLE" in result.status:
        for ca_id in inp.ca_ids:
            meta = inp.ca_meta.get(ca_id, {})
            thu_ca = meta.get("thu", "")
            req = inp.so_nguoi_toi_thieu.get(ca_id, 1)
            c_start = meta.get("bat_dau", "07:00")
            c_end = meta.get("ket_thuc", "12:00")
            available = 0
            for nv in inp.nhan_vien_ids:
                if (nv, thu_ca) in inp.nghi_phep:
                    continue
                nv_tkb = inp.tkb.get(nv, [])
                overlap = False
                for (b_thu, b_start, b_end) in nv_tkb:
                    if b_thu == thu_ca:
                        try:
                            h_cs, m_cs = map(int, c_start.split(":"))
                            h_ce, m_ce = map(int, c_end.split(":"))
                            h_bs, m_bs = map(int, b_start.split(":"))
                            h_be, m_be = map(int, b_end.split(":"))
                            if max(h_cs * 60 + m_cs, h_bs * 60 + m_bs) < min(h_ce * 60 + m_ce, h_be * 60 + m_be):
                                overlap = True
                                break
                        except Exception:
                            pass
                if not overlap:
                    available += 1
            if available < req:
                danh_sach_xung_dot.append(
                    f"Ca {ca_id} ({thu_ca} {c_start}-{c_end}) cần tối thiểu {req} người nhưng chỉ còn {available} nhân viên khả dụng do ràng buộc nghỉ phép/TKB."
                )

    payload = {
        "nguon": "quan",
        "adr": "ADR-012",
        "tuan_iso": tuan_hien_tai,
        "status": result.status,
        "ok": result.ok,
        "elapsed_s": round(result.elapsed_s, 3),
        "objective": result.objective,
        "violations": result.violations,
        "phan_cong": result.phan_cong,
        "debt_after": result.debt_after,
        "luat_ap_dung": applied,
        "danh_sach_xung_dot": danh_sach_xung_dot,
    }
    o_ca = {
        (str(meta.get("thu") or ""), str(meta.get("khung") or ""))
        for meta in inp.ca_meta.values()
        if meta.get("thu") and meta.get("khung")
    }
    o_ca_da_xep = {
        (
            str(inp.ca_meta.get(ca_id, {}).get("thu") or ""),
            str(inp.ca_meta.get(ca_id, {}).get("khung") or ""),
        )
        for ca_id, nhan_vien_ids in result.phan_cong.items()
        if nhan_vien_ids
    }
    payload["tong_so_o_ca"] = len(o_ca)
    payload["so_o_ca_da_xep"] = len(o_ca_da_xep & o_ca)
    payload["kiem_tra"] = {
        "hard": {
            "passed": result.ok and not result.violations,
            "gates": ["C01", "C02", "C03", "C04", "C05", "C06"],
            "violations": result.violations,
        },
        "vf": {
            "applies_to_solver": False,
            "message": (
                "VF kiểm dữ liệu do agent trích xuất và lời giải thích; "
                "CP-SAT được hậu kiểm bằng C01–C06."
            ),
            "gates": ["VF-SCHEMA", "VF-TRACE", "VF-CONF", "VF-CONFLICT", "VF-NUM", "VF-RULE"],
        },
        "coverage": {
            "passed": len(o_ca_da_xep & o_ca) == len(o_ca),
            "filled": len(o_ca_da_xep & o_ca),
            "total": len(o_ca),
        },
    }
    out = _lich_out()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if result.ok:
        _set_week_value("phan_cong_by_week", tuan_hien_tai, result.phan_cong)
        _set_week_value("lich_tuan_results_by_week", tuan_hien_tai, payload)
        _set_week_value("fairness_debt_by_week", tuan_hien_tai, result.debt_after)
        # Latest-week mirror for older workers/tests; week-scoped stores remain authoritative.
        kv_set("phan_cong", result.phan_cong)
    return {
        "status": result.status,
        "ok": result.ok,
        "best_effort": result.ok,
        "luat_ap_dung": applied,
        "violations": len(result.violations),
        "danh_sach_xung_dot": danh_sach_xung_dot,
        "tong_so_o_ca": len(o_ca),
        "so_o_ca_da_xep": len(o_ca_da_xep & o_ca),
        "kiem_tra": payload["kiem_tra"],
        "phan_cong": result.phan_cong,
        "ca_meta": inp.ca_meta,
    }


def _life(tuan_iso: str | None = None) -> dict[str, Any]:
    """Trạng thái lịch tuần — SSOT là kv `lich_tuan_lifecycle` (giờ main.py,
    copilot và sprint45 cùng một nguồn). Fallback đọc kv `lifecycle` cũ cho
    data trước khi nhất hóa; thiếu hẳn thì về máy-sinh tuần mặc định."""
    requested = tuan_iso
    if requested:
        by_week = kv_get("lich_tuan_lifecycle_by_week", {})
        if isinstance(by_week, dict) and isinstance(by_week.get(requested), dict):
            return cast(dict[str, Any], by_week[requested])
        return {"tuan_iso": requested, "trang_thai": "nhap", "nguon": "quan"}
    moi = kv_get("lich_tuan_lifecycle", None)
    if isinstance(moi, dict) and moi.get("trang_thai"):
        return cast(dict[str, Any], moi)
    cu = kv_get("lifecycle", None)
    if isinstance(cu, dict) and cu.get("trang_thai"):
        return cast(dict[str, Any], cu)
    return {"tuan_iso": "2026-W01", "trang_thai": "may_sinh", "nguon": "quan"}


def _save_life(doc: dict[str, Any]) -> None:
    # Ghi CẢ HAI khóa: mới là nguồn sự thật, cũ giữ đồng bộ cho tiến trình
    # còn đọc chưa nâng cấp (đọc soft ở trên tự bỏ qua khi mới tồn tại).
    kv_set("lich_tuan_lifecycle", doc)
    kv_set("lifecycle", doc)
    _set_week_value(
        "lich_tuan_lifecycle_by_week",
        str(doc.get("tuan_iso") or "2026-W01"),
        doc,
    )


def _seed_inbox() -> list[dict[str, Any]]:
    items = kv_get("inbox_rang_buoc", [])
    if items:
        return cast(list[dict[str, Any]], items)
    if os.environ.get("NHIPQUAN_INBOX_SEED_FIXTURE", "0").strip().lower() not in {"1", "true", "yes"}:
        return []
    items = [
        {
            "id": f"in_{i + 1}",
            "agent": "ag_msg" if i % 2 == 0 else "ag_handover",
            "tom_tat": f"Ràng buộc #{i + 1} — chờ duyệt",
            "trang_thai": "cho_duyet",
            "nguon": "mo_phong_fixture",
        }
        for i in range(10)
    ]
    kv_set("inbox_rang_buoc", items)
    return items


def _phan(tuan_iso: str | None = None) -> dict[str, list[str]]:
    week = tuan_iso or str(_life().get("tuan_iso") or "2026-W01")
    stored = _week_value("phan_cong_by_week", week, None)
    if stored:
        return cast(dict[str, list[str]], stored)
    out = _lich_out()
    if out.exists():
        doc = json.loads(out.read_text(encoding="utf-8"))
        if not doc.get("tuan_iso") or doc.get("tuan_iso") == week:
            return cast(dict[str, list[str]], doc.get("phan_cong", {}))
    return {}


class LifeBody(BaseModel):
    to: str
    ly_do: str | None = None
    tuan_iso: str | None = None


class InboxBody(BaseModel):
    quyet_dinh: str
    ca_id: str | None = None
    doi_tac_nv_id: str | None = None
    ap_dat: bool = False
    tu_dong_xep_lich: bool = False
    ly_do: str | None = Field(default=None, max_length=500)


class SmartApproveBody(BaseModel):
    selected_nv_id: str | None = None
    ap_dat: bool = True


class HandoverBody(BaseModel):
    text: str = Field(min_length=1, max_length=10000)
    alt_claim: str | None = Field(default=None, max_length=5000)


class SopBody(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    ngu_canh: dict[str, str] | None = None


class SwapBody(BaseModel):
    a: str
    b: str
    c: str
    ca_id: str


class OpenShiftBody(BaseModel):
    schedule_run_id: str
    tuan_iso: str
    ca_id: str
    deadline_at: str | None = None


class ShiftClaimBody(BaseModel):
    open_shift_id: str


class ResolveScheduleBody(BaseModel):
    schedule_run_id: str
    tuan_iso: str
    expected_fingerprint: str
    idempotency_key: str = Field(min_length=1, max_length=200)
    ca_id: str | None = None
    nv_id: str | None = None


class DuyetLuatBody(BaseModel):
    id: str
    ok: bool = True


class QrBody(BaseModel):
    nv_id: str
    ca_id: str = "w1_c01"


@router.get("/api/v1/lich/lifecycle")
def lich_life(
    authorization: Annotated[str | None, Header()] = None,
    tuan: str | None = Query(default=None),
) -> dict[str, Any]:
    _require_role(authorization)
    return _life(tuan)


@router.post("/api/v1/lich/lifecycle")
async def lich_transition(
    body: LifeBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    current = _life()
    week = (body.tuan_iso or "").strip() or str(current.get("tuan_iso") or "2026-W01")
    doc = _life(week) if body.tuan_iso else current
    cur = doc.get("trang_thai", "may_sinh")
    if body.to not in _ALLOWED.get(cur, set()):
        raise HTTPException(status_code=409, detail=f"illegal:{cur}->{body.to}")
    if body.to == "da_dong":
        _require_chu_quan(authorization)
    if cur == "da_dong" and body.to == "nhap":
        _require_chu_quan(authorization)
        if not body.ly_do or not body.ly_do.strip():
            raise HTTPException(status_code=400, detail="can_ly_do_mo_lai_lich")
        _audit("schedule.lifecycle_reopen", role, {"entity_type": "schedule", "entity_id": doc.get("tuan_iso", "2026-W01"), "from": cur, "to": body.to, "ly_do": body.ly_do.strip()})

    session = auth_session(authorization) or {}
    store_id = str(session.get("store_id") or "quan_01")
    if body.to in {"da_duyet", "da_cong_bo"}:
        _guard_authoritative_lifecycle(week, body.to, store_id)

    doc["tuan_iso"] = week
    doc["trang_thai"] = body.to
    if body.to == "dang_giai":
        try:
            authoritative = run_authoritative_schedule(
                store_id=str((auth_session(authorization) or {}).get("store_id") or "quan_01"),
                tuan_iso=week, actor_id=role, idempotency_key=f"lifecycle:{week}:solve",
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        solver = authoritative.get("result") or {}
        doc["solver"] = solver
        doc["schedule_run"] = authoritative
        doc["trang_thai"] = "cho_duyet" if solver.get("ok") else "nhap"
    _save_life(doc)
    _audit("schedule.lifecycle", role, {"entity_type": "schedule", "entity_id": doc.get("tuan_iso", "2026-W01"), "from": cur, "to": body.to})
    if body.to == "da_cong_bo":
        _publish_schedule_notification(week)
    await notify_ops_changed("roster:lifecycle", doc.get("tuan_iso"))
    return doc


def _guard_authoritative_lifecycle(week: str, target: str, store_id: str) -> dict[str, Any]:
    from ca_api.persist import schedule_run_latest
    from ca_api.services.scheduling_service import authoritative_input_fingerprint

    run = schedule_run_latest(store_id, week)
    if not run:
        raise HTTPException(status_code=409, detail="authoritative_schedule_run_required")
    _, current_fingerprint = authoritative_input_fingerprint(store_id, week)
    if run.get("fingerprint") != current_fingerprint:
        raise HTTPException(status_code=409, detail="stale_schedule_run")
    if target == "da_cong_bo" and run.get("status") != "computed":
        raise HTTPException(status_code=409, detail="schedule_has_unresolved_gaps")
    if target == "da_duyet" and run.get("status") != "computed":
        raise HTTPException(status_code=409, detail="invalid_schedule_run")
    if target == "da_cong_bo":
        from ca_api.persist import open_shift_list
        if open_shift_list(store_id, tuan_iso=week):
            raise HTTPException(status_code=409, detail="schedule_has_open_shifts")
    return run


@router.post("/api/v1/lich/resolve-gaps")
async def resolve_gaps(
    body: ResolveScheduleBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    session = auth_session(authorization) or {}
    try:
        run = resolve_schedule_gaps(
            store_id=str(session.get("store_id") or "quan_01"), tuan_iso=body.tuan_iso,
            actor_id=str(session.get("nv_id") or role), schedule_run_id=body.schedule_run_id,
            expected_fingerprint=body.expected_fingerprint, idempotency_key=body.idempotency_key,
            ca_id=body.ca_id, nv_id=body.nv_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    result = run.get("result") or {}
    if result.get("ok"):
        doc = _life(body.tuan_iso)
        doc["trang_thai"] = "cho_duyet"
        doc["schedule_run"] = run
        doc["solver"] = result
        _save_life(doc)
    _audit("schedule.resolve_gaps", role, {"entity_type": "schedule_run", "entity_id": body.schedule_run_id, "tuan_iso": body.tuan_iso, "ok": bool(result.get("ok"))})
    await notify_ops_changed("roster:gap-resolution", body.tuan_iso)
    return {"ok": bool(result.get("ok")), "schedule_run": run, "solver": result}


def _export_rows(
    authorization: str | None,
    tuan: str | None,
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    s = _require_role_session(authorization)
    tuan_iso = (tuan or "").strip() or str(_life().get("tuan_iso") or "2026-W01")
    life = _life(tuan_iso)
    if s.get("role") == "nhan_vien" and life.get("trang_thai") not in {"da_cong_bo", "da_dong"}:
        raise HTTPException(status_code=409, detail="lich_chua_cong_bo")
    phan = _phan(tuan_iso)
    try:
        y_str, w_str = tuan_iso.split("-W")
        iso_year, iso_week = int(y_str), int(w_str)
    except Exception:
        raise HTTPException(status_code=422, detail="tuan_iso_khong_hop_le") from None

    seed_data = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    ca_meta_map = {c["id"]: c for c in seed_data.get("ca_mau_21", [])}
    ten_map = {
        str(nv["id"]): str(nv.get("ten") or nv["id"])
        for nv in list_nhan_vien_ops()
    }
    khung_gio = kv_get("khung_gio", {})
    personal = s.get("role") == "nhan_vien"
    rows: list[dict[str, Any]] = []
    for ca_id, assigned_raw in phan.items():
        assigned = list(assigned_raw)
        if personal:
            assigned = [nv for nv in assigned if nv == s.get("nv_id")]
        if not assigned:
            continue
        meta = ca_meta_map.get(ca_id, {})
        frame = khung_gio.get(meta.get("khung"), {}) if isinstance(khung_gio, dict) else {}
        start = str(frame.get("bat_dau") or meta.get("bat_dau", "07:00"))
        finish = str(frame.get("ket_thuc") or meta.get("ket_thuc", "12:00"))
        day_offset = int(meta.get("ngay_offset", 1))
        shift_date = date.fromisocalendar(iso_year, iso_week, day_offset)
        rows.append(
            {
                "ca_id": ca_id,
                "date": shift_date,
                "thu": _THU_MAP.get(day_offset, "T2"),
                "khung": str(meta.get("khung") or ""),
                "bat_dau": start,
                "ket_thuc": finish,
                "vi_tri": _VI_TRI_VI.get(str(meta.get("vi_tri") or ""), str(meta.get("vi_tri") or "")),
                "nhan_vien": [ten_map.get(nv, nv) for nv in assigned],
            }
        )
    rows.sort(key=lambda row: (row["date"], row["bat_dau"], row["vi_tri"]))
    return tuan_iso, s, rows


@router.post("/api/v1/open-shifts")
def create_open_shift(
    body: OpenShiftBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_manager(authorization)
    store_id = str(auth_session(authorization).get("store_id") or "quan_01")
    deadline_at = body.deadline_at
    if not deadline_at:
        sla_minutes = int(os.environ.get("OPEN_SHIFT_SLA_MINUTES", "120"))
        deadline_at = (datetime.now(UTC) + timedelta(minutes=sla_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return open_shift_create(
        store_id=store_id,
        schedule_run_id=body.schedule_run_id,
        tuan_iso=body.tuan_iso,
        ca_id=body.ca_id,
        deadline_at=deadline_at,
    )


@router.get("/api/v1/open-shifts")
def list_open_shifts(
    authorization: Annotated[str | None, Header()] = None,
    tuan_iso: str | None = Query(default=None),
) -> dict[str, Any]:
    _require_role(authorization)
    store_id = str(auth_session(authorization).get("store_id") or "quan_01")
    return {"items": open_shift_list(store_id, tuan_iso=tuan_iso)}


@router.post("/api/v1/open-shifts/claim")
def claim_open_shift(
    body: ShiftClaimBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    session = auth_session(authorization)
    if not session:
        raise HTTPException(status_code=401, detail="thieu_token")
    if session.get("role") != "nhan_vien":
        raise HTTPException(status_code=403, detail="chi_nhan_vien_duoc_nhan_ca")
    store_id = str(session.get("store_id") or "quan_01")
    shifts = [item for item in open_shift_list(store_id) if item["id"] == body.open_shift_id]
    if not shifts:
        raise HTTPException(status_code=404, detail="open_shift_khong_ton_tai")
    shift = shifts[0]
    confirmed = availability_confirmed_list(store_id, shift["tuan_iso"])
    if not any(item["nv_id"] == session.get("nv_id") for item in confirmed):
        raise HTTPException(status_code=409, detail="chua_xac_nhan_kha_dung_dung_tuan")
    claimed = shift_application_claim_first(
        open_shift_id=body.open_shift_id,
        store_id=store_id,
        nv_id=str(session["nv_id"]),
    )
    if claimed is None:
        raise HTTPException(status_code=409, detail="ca_da_duoc_nhan")
    return claimed


@router.get("/api/v1/lich/ics")
def lich_ics(
    authorization: Annotated[str | None, Header()] = None,
    download: bool = Query(default=False),
    tuan: str | None = Query(default=None, description="Tuần ISO muốn xuất, vd 2026-W37"),
) -> Any:
    tuan_iso, s, rows = _export_rows(authorization, tuan)
    now_stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//NHIPQUAN//CA//VI",
        "CALSCALE:GREGORIAN",
        "X-WR-TIMEZONE:Asia/Ho_Chi_Minh",
    ]
    for row in rows:
        uid = f"{row['ca_id']}_{tuan_iso}_{s['nv_id']}@nhipquan.local"
        d_str = row["date"].strftime("%Y%m%d")
        dtstart = f"{d_str}T{str(row['bat_dau']).replace(':', '')}00"
        dtend = f"{d_str}T{str(row['ket_thuc']).replace(':', '')}00"
        summary = _ics_escape(
            f"{row['vi_tri']} — {' · '.join(row['nhan_vien'])}"
        )
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_stamp}",
            f"DTSTART;TZID=Asia/Ho_Chi_Minh:{dtstart}",
            f"DTEND;TZID=Asia/Ho_Chi_Minh:{dtend}",
            f"SUMMARY:{summary}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    ics_text = "\r\n".join(lines)
    if download:
        return Response(
            content=ics_text,
            media_type="text/calendar; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="lich_tuan_{tuan_iso}.ics"',
            },
        )
    return {"ics": ics_text, "nguon": "quan", "tuan_iso": tuan_iso}


@router.get("/api/v1/lich/xlsx")
def lich_xlsx(
    authorization: Annotated[str | None, Header()] = None,
    tuan: str | None = Query(default=None),
) -> Response:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    tuan_iso, _session, rows = _export_rows(authorization, tuan)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Lịch tuần"
    sheet.append(["Tuần", "Ngày", "Thứ", "Khung", "Giờ", "Vị trí", "Nhân viên"])
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="8C5A3C")
        cell.alignment = Alignment(horizontal="center")
    for row in rows:
        sheet.append(
            [
                tuan_iso,
                row["date"].strftime("%d/%m/%Y"),
                row["thu"],
                row["khung"],
                f"{row['bat_dau']}–{row['ket_thuc']}",
                row["vi_tri"],
                ", ".join(row["nhan_vien"]),
            ]
        )
    for width, column in zip((14, 14, 8, 12, 16, 18, 42), "ABCDEFG", strict=True):
        sheet.column_dimensions[column].width = width
    output = BytesIO()
    workbook.save(output)
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="lich_tuan_{tuan_iso}.xlsx"'},
    )


@router.get("/api/v1/lich/pdf")
def lich_pdf(
    authorization: Annotated[str | None, Header()] = None,
    tuan: str | None = Query(default=None),
) -> Response:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

    tuan_iso, _session, rows = _export_rows(authorization, tuan)
    font_name = "Helvetica"
    for font_path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        if Path(font_path).exists():
            pdfmetrics.registerFont(TTFont("NhipQuanUnicode", font_path))
            font_name = "NhipQuanUnicode"
            break
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    styles = getSampleStyleSheet()
    styles["Title"].fontName = font_name
    story: list[Any] = [Paragraph(f"Lịch tuần {tuan_iso}", styles["Title"])]
    data = [["Ngày", "Khung giờ", "Vị trí", "Nhân viên"]]
    data.extend(
        [
            row["date"].strftime("%d/%m/%Y"),
            f"{row['khung']} {row['bat_dau']}–{row['ket_thuc']}",
            row["vi_tri"],
            ", ".join(row["nhan_vien"]),
        ]
        for row in rows
    )
    table = Table(data, colWidths=[35 * mm, 45 * mm, 42 * mm, 145 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8C5A3C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4EEE9")]),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return Response(
        content=output.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="lich_tuan_{tuan_iso}.pdf"'},
    )


@router.get("/api/v1/audit")
def audit_get(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_manager(authorization)
    return {"items": audit_list(), "nguon": "quan"}


def _ics_escape(text: str) -> str:
    """Escape ký tự theo RFC 5545 TEXT: backslash, chấm phẩy, phẩy, xuống dòng."""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _require_role_session(authorization: str | None) -> dict[str, Any]:
    """Yêu cầu đăng nhập và trả về session (để chèn người duyệt vào UID ICS)."""
    role = _require_role(authorization)
    from ca_api.persist import session as auth_session

    s = auth_session(authorization)
    return s if s else {"nv_id": role, "role": role}


def _get_swap_candidates_for_item(it: dict[str, Any]) -> list[dict[str, Any]]:
    """Tính toán danh sách ứng viên đổi ca phù hợp cho một inbox item."""
    nv_id = str(it.get("nv_id") or "")
    rb = it.get("rang_buoc") or {}
    ca_id = str(rb.get("ca_id") or "")

    thu = str(rb.get("thu") or "")
    start = str(rb.get("start") or "")
    khung = "sang" if "07" in start else ("chieu" if "12" in start else ("toi" if "17" in start else ""))
    vi_tri = str(rb.get("vi_tri") or "pha_che")
    shift_info = {"thu": thu, "khung": khung, "vi_tri": vi_tri}

    seed = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    staff_list = seed.get("nhan_vien", [])
    raw_ca = seed.get("ca_mau_21", [])
    ca_list = []
    for c in raw_ca:
        item_c = dict(c)
        if "thu" not in item_c:
            item_c["thu"] = _THU_MAP.get(int(item_c.get("ngay_offset") or 1), "T2")
        ca_list.append(item_c)

    phan_cong: dict[str, list[str]] = {}
    lich_out = _lich_out()
    if lich_out.exists():
        try:
            lich_data = json.loads(lich_out.read_text(encoding="utf-8"))
            phan_cong = lich_data.get("phan_cong", {})
        except Exception:
            pass

    cands = find_swap_candidates(
        requester_id=nv_id,
        ca_id=ca_id if ca_id else None,
        shift_info=shift_info,
        staff_list=staff_list,
        ca_list=ca_list,
        phan_cong=phan_cong,
        max_ca_lien_tuc=2,
    )
    return [c.to_dict() for c in cands]


@router.get("/api/v1/inbox/rang-buoc")
def inbox_list(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_manager(authorization)
    existing = kv_get("inbox_rang_buoc", [])
    has_real_channel = any(
        isinstance(it, dict) and it.get("nguon") in {"telegram", "zalo", "facebook"}
        for it in existing
    )
    if not existing and not has_real_channel:
        _seed_inbox()
    items = kv_get("inbox_rang_buoc", [])
    enriched = []
    for it in items:
        if isinstance(it, dict):
            item_copy = dict(it)
            rb = item_copy.get("rang_buoc") or {}
            item_copy["khan_cap"] = bool(rb.get("khan_cap"))
            if item_copy.get("y_dinh") in {"doi_ca", "nhan_ca"}:
                try:
                    cands = _get_swap_candidates_for_item(item_copy)
                    item_copy["goi_y_doi_tac"] = cands[:3]
                except Exception:
                    item_copy["goi_y_doi_tac"] = []
            enriched.append(item_copy)
        else:
            enriched.append(it)
    return {"items": enriched, "nguon": "quan", "co_du_lieu_mau": _co_du_lieu_mau(enriched)}


@router.post("/api/v1/inbox/rang-buoc/{item_id}")
def inbox_decide(
    item_id: str,
    body: InboxBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    tuan_default = _life().get("tuan_iso", "2026-W01")
    found: dict[str, Any] | None = None
    pending_swap: dict[str, Any] | None = None

    def mut(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal found, pending_swap
        for it in items:
            if it.get("id") == item_id:
                if body.quyet_dinh not in {"duyet", "tu_choi"}:
                    raise HTTPException(status_code=400, detail="quyet_dinh")
                it["trang_thai"] = body.quyet_dinh
                if body.ly_do and str(body.ly_do).strip():
                    it["ly_do_quyet"] = str(body.ly_do).strip()[:500]
                if body.quyet_dinh == "duyet":
                    y = str(it.get("y_dinh") or "")
                    rb = it.get("rang_buoc") or {}
                    tuan_id = rb.get("tuan_id") or tuan_default
                    if y in {"doi_ca", "nhan_ca"}:
                        ca_id = (body.ca_id or rb.get("ca_id") or "").strip()
                        doi_tac_nv_id = (body.doi_tac_nv_id or rb.get("doi_tac") or "").strip()
                        if it.get("doi_tac_khong_ro") and not body.doi_tac_nv_id:
                            raise HTTPException(
                                status_code=400,
                                detail="doi_tac_khong_ro_can_chon_nhan_vien",
                            )
                        if not ca_id or not doi_tac_nv_id:
                            raise HTTPException(
                                status_code=400,
                                detail="doi_ca_can_ca_id_va_doi_tac",
                            )
                        is_ap_dat = bool(body.ap_dat)
                        swap_status = "dong_y" if is_ap_dat else "cho_xac_nhan"
                        dong_y_list = [it.get("nv_id") or "unknown", doi_tac_nv_id, role] if is_ap_dat else [it.get("nv_id") or "unknown"]
                        pending_swap = {
                            "id": f"sw_inbox_{uuid.uuid4().hex[:6]}",
                            "a": it.get("nv_id") or "unknown",
                            "b": doi_tac_nv_id,
                            "c": role,
                            "ca_id": ca_id,
                            "trang_thai": swap_status,
                            "dong_y": dong_y_list,
                            "ap_dat": is_ap_dat,
                            "nguon": it.get("nguon") or "inbox",
                            "tu_inbox": item_id,
                            "tom_tat": it.get("tom_tat"),
                            "tuan_id": tuan_id,
                        }
                        it["hieu_luc"] = {
                            "loai": "cho_doi_ca",
                            "swap_id": pending_swap["id"],
                            "ghi": (
                                f"Đã áp đặt đổi ca {ca_id} với {doi_tac_nv_id}"
                                if is_ap_dat
                                else f"Đã mở phiếu đổi ca {ca_id} với {doi_tac_nv_id} — chờ đối tác xác nhận"
                            ),
                            "tuan_id": tuan_id,
                        }
                    elif y == "xin_nghi":
                        thu = rb.get("thu", "")
                        it["hieu_luc"] = {
                            "loai": "rang_buoc_cho_solver",
                            "ghi": f"Đã duyệt nghỉ phép {thu} ({tuan_id}) — áp vào lượt xếp lịch tới",
                            "nv_id": it.get("nv_id"),
                            "thu": thu,
                            "tuan_id": tuan_id,
                        }
                    elif y in {"bao_tre", "cap_nhat_tkb"}:
                        thu = rb.get("thu", "")
                        start = rb.get("start", "07:00")
                        end = rb.get("end", "12:00")
                        it["hieu_luc"] = {
                            "loai": "rang_buoc_cho_solver",
                            "ghi": f"Đã duyệt TKB bận {thu} {start}-{end} ({tuan_id}) — áp vào lượt xếp lịch tới",
                            "nv_id": it.get("nv_id"),
                            "thu": thu,
                            "start": start,
                            "end": end,
                            "tuan_id": tuan_id,
                        }
                    else:
                        it["hieu_luc"] = {
                            "loai": "ghi_nhan",
                            "ghi": "Đã ghi nhận — không đổi lịch",
                        }
                found = it
                break
        return items

    kv_mutate("inbox_rang_buoc", mut, [])
    if pending_swap is not None:
        def add_swap(items_sw: list[dict[str, Any]]) -> list[dict[str, Any]]:
            items_sw.append(pending_swap)
            return items_sw

        kv_mutate("swap", add_swap, [])
    if not found:
        raise HTTPException(status_code=404, detail="inbox_item")

    y_dinh = str(found.get("y_dinh") or "")
    if y_dinh == "doi_ca":
        action_name = (
            "shift_swap.approve"
            if body.quyet_dinh == "duyet"
            else "shift_swap.reject"
        )
    else:
        action_name = (
            "constraint.approve"
            if body.quyet_dinh == "duyet"
            else "constraint.reject"
        )
    _audit(
        action_name,
        role,
        {
            "entity_type": "inbox_item",
            "entity_id": item_id,
            "q": body.quyet_dinh,
            "y": y_dinh,
        },
    )

    response = dict(found)
    if (
        body.quyet_dinh == "duyet"
        and body.tu_dong_xep_lich
        and found.get("hieu_luc", {}).get("loai") == "rang_buoc_cho_solver"
    ):
        life = _life()
        current_state = str(life.get("trang_thai") or "may_sinh")
        if current_state in {"da_duyet", "da_cong_bo", "da_dong"}:
            solver_result = {
                "ok": False,
                "skipped": True,
                "status": "LIFECYCLE_LOCKED",
                "detail": f"lich_{current_state}_khong_tu_dong_xep_lai",
            }
        else:
            try:
                solver_result = _run_solver()
            except Exception:
                solver_result = {
                    "ok": False,
                    "status": "ERROR",
                    "detail": "khong_the_chay_solver",
                }
            if solver_result.get("ok"):
                life["trang_thai"] = "cho_duyet"
                life["solver"] = solver_result
                life["cap_nhat_luc"] = _clock.now_iso()
                life["cap_nhat_boi"] = role
                _save_life(life)
        response["tu_dong_xep_lich"] = solver_result
        _audit(
            "inbox_auto_schedule",
            role,
            {
                "id": item_id,
                "ok": solver_result.get("ok"),
                "status": solver_result.get("status"),
                "so_o_ca_da_xep": solver_result.get("so_o_ca_da_xep"),
                "tong_so_o_ca": solver_result.get("tong_so_o_ca"),
            },
        )
    return response


@router.get("/api/v1/inbox/candidates/{item_id}")
def get_swap_candidates(
    item_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Lấy danh sách xếp hạng các ứng viên đổi ca cho một yêu cầu."""
    _require_manager(authorization)
    items = kv_get("inbox_rang_buoc", [])
    found = next((it for it in items if it.get("id") == item_id), None)
    if not found:
        raise HTTPException(status_code=404, detail="item_not_found")

    cands = _get_swap_candidates_for_item(found)
    return {
        "item_id": item_id,
        "nv_id": found.get("nv_id"),
        "candidates": cands,
    }


@router.post("/api/v1/inbox/rang-buoc/{item_id}/smart-approve")
def inbox_smart_approve(
    item_id: str,
    body: SmartApproveBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Duyệt đổi ca 1-chạm với ứng viên AI đề xuất tốt nhất (hoặc ứng viên được chọn)."""
    _require_manager(authorization)
    items = kv_get("inbox_rang_buoc", [])
    found = next((it for it in items if it.get("id") == item_id), None)
    if not found:
        raise HTTPException(status_code=404, detail="item_not_found")

    target_nv = body.selected_nv_id
    if not target_nv:
        cands = _get_swap_candidates_for_item(found)
        top_cand = next((c for c in cands if c.get("score", 0) > 0), None)
        if not top_cand:
            raise HTTPException(status_code=400, detail="khong_co_ung_vien_phu_hop")
        target_nv = top_cand["nv_id"]

    rb = found.get("rang_buoc") or {}
    ca_id = (rb.get("ca_id") or "w1_c01").strip()

    decide_body = InboxBody(
        quyet_dinh="duyet",
        doi_tac_nv_id=target_nv,
        ca_id=ca_id,
        ap_dat=body.ap_dat,
    )
    res = inbox_decide(item_id, decide_body, authorization)
    res["selected_candidate"] = target_nv
    res["smart_matched"] = True
    
    _require_manager(authorization)
    role = _require_manager(authorization)
    _audit("shift_swap.smart_approve", role, {"entity_type": "inbox_item", "entity_id": item_id, "selected_candidate": target_nv})
    return res


@router.get("/api/v1/cong-bang")
def cong_bang(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    seed = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    nvs = [n["id"] for n in seed.get("nhan_vien", [])]
    meta = {
        c["id"]: {
            "thu": {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}.get(
                int(c.get("ngay_offset", 1)), "T2"
            ),
            "khung": c.get("khung", ""),
            "bat_dau": c.get("bat_dau", "07:00"),
            "ket_thuc": c.get("ket_thuc", "12:00"),
        }
        for c in seed.get("ca_mau_21", [])
    }
    debt = update_debt_from_assignment(zero_debt(nvs), _phan(), meta)
    means = {a: 0.0 for a in AXES}
    if nvs:
        for a in AXES:
            means[a] = sum(debt[n][a] for n in nvs) / len(nvs)
    me = s["nv_id"]
    if s["role"] in {"quan_ly", "chu_quan"}:
        so_du = debt
        ma_ly_do = {nv: [_REASON[a] for a in AXES if debt[nv][a] > means[a]] for nv in nvs}
    else:
        so_du = {me: debt.get(me, {a: 0.0 for a in AXES})}
        ma_ly_do = {me: [_REASON[a] for a in AXES if so_du[me][a] > means[a]]}
    return {
        "axes": list(AXES),
        "means": means,
        "so_du": so_du,
        "ma_ly_do": ma_ly_do,
        "nv_id": me,
        "nguon": "quan",
        "khong_xep_hang_ten": True,
    }


@router.get("/api/v1/cong-bang/bao-cao")
def cong_bang_bao_cao(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    body = cong_bang(authorization)
    lines = [
        "NHIP QUAN — báo cáo công bằng",
        f"nguon={body['nguon']}",
        "khong xep hang ten",
    ]
    for a, m in body["means"].items():
        lines.append(f"TB {a}={m:.2f}")
    return {"text": "\n".join(lines), "dinh_dang": "text/plain"}


class TieuThuBody(BaseModel):
    hang: str = Field(min_length=1, max_length=100)
    so_luong: float = Field(ge=0)
    don_vi: str = Field(default="khay", min_length=1, max_length=30)


class WasteNoteBody(BaseModel):
    thu: str = "T2"
    ghi_chu: str = ""
    mon_id: str | None = None
    so_luong: float | None = Field(default=None, ge=0)
    don_vi: str | None = None
    ly_do: str | None = None


@router.get("/api/v1/hom-nay")
def hom_nay(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    role = _require_role(authorization)
    life = _life()
    treo = kv_get("treo", [])
    inbox = kv_get("inbox_rang_buoc", [])
    cho = sum(1 for x in inbox if x.get("trang_thai") == "cho_duyet")
    if role == "nhan_vien":
        cho = 0
    luat = list_luat()
    ton = kv_get("tieu_thu", [])
    canh_bao = [x["hang"] for x in ton if x.get("duoi_nguong")]
    so_nv = sum(1 for u in list_users() if u.get("role") == "nhan_vien")
    treo_preview = [
        {
            "id": t.get("id"),
            "noi_dung": str(t.get("noi_dung") or "")[:120],
            "trang_thai": t.get("trang_thai") or "dang_cho",
            "nhan_vien": t.get("nhan_vien") or t.get("nv_id"),
        }
        for t in treo[:5]
        if isinstance(t, dict)
    ]
    sua_gan_day = [
        {
            "loai": row.get("loai"),
            "luc": row.get("at"),
            "ai": row.get("ai"),
        }
        for row in list(reversed(list_sua(include_synthetic=False)))[:5]
    ]
    ton_tom_tat = [
        {
            "hang": x.get("hang"),
            "so_luong": x.get("so_luong"),
            "don_vi": x.get("don_vi") or "đơn vị",
            "duoi_nguong": bool(x.get("duoi_nguong")),
        }
        for x in ton[-8:]
        if isinstance(x, dict)
    ]
    treo_counts: dict[str, int] = {}
    for t in treo:
        if not isinstance(t, dict):
            continue
        st = str(t.get("trang_thai") or "dang_cho")
        treo_counts[st] = treo_counts.get(st, 0) + 1
    treo_theo_trang_thai = [{"trang_thai": k, "so_luong": v} for k, v in sorted(treo_counts.items(), key=lambda x: -x[1])]
    # Hàng đợi "Việc của bạn hôm nay" — quản lý/chủ quán thấy ngay việc chờ mình.
    # Mỗi mục: việc gì, vì sao, bấm vào đâu. NV chỉ thấy việc ca của mình.
    viec_cho_toi: list[dict[str, Any]] = []
    de_xuat_lich = kv_get("worker_de_xuat_lich", None)
    if role in {"quan_ly", "chu_quan"}:
        life_trang_thai = str(life.get("trang_thai") or "nhap")
        if cho > 0:
            viec_cho_toi.append(
                {
                    "id": "inbox_cho",
                    "tieu_de": f"Duyệt {cho} mục hộp thư",
                    "chi_tiet": "Yêu cầu của nhân viên đang chờ quyết.",
                    "link": "/inbox",
                    "muc": cho,
                }
            )
        if de_xuat_lich and de_xuat_lich.get("trang_thai") == "cho_duyet":
            viec_cho_toi.append(
                {
                    "id": "lich_tuan_cho",
                    "tieu_de": "Duyệt lịch tuần sau",
                    "chi_tiet": f"Worker đã xếp sẵn ({de_xuat_lich.get('tong_so_luot', 0)} lượt) — xem rồi công bố.",
                    "link": "/roster",
                    "muc": 1,
                }
            )
        if life_trang_thai in {"may_sinh", "nhap"}:
            viec_cho_toi.append(
                {
                    "id": "xep_lich",
                    "tieu_de": "Xếp lịch tuần",
                    "chi_tiet": "Lịch tuần chưa được duyệt — chạy solver để có lịch công bố.",
                    "link": "/roster",
                    "muc": 1,
                }
            )
        luat_cho = [lt for lt in luat if isinstance(lt, dict) and lt.get("trang_thai") == "cho_chot"]
        if luat_cho and role == "chu_quan":
            viec_cho_toi.append(
                {
                    "id": "luat_cho",
                    "tieu_de": f"Chốt {len(luat_cho)} luật cẩm nang",
                    "chi_tiet": "Luật đã qua tập sự — chốt để có hiệu lực.",
                    "link": "/cam-nang",
                    "muc": len(luat_cho),
                }
            )
        qua_han = [t for t in treo if isinstance(t, dict) and t.get("trang_thai") == "qua_han"]
        if qua_han:
            viec_cho_toi.append(
                {
                    "id": "treo_qua_han",
                    "tieu_de": f"{len(qua_han)} việc treo quá hạn",
                    "chi_tiet": "Việc kẹt quá hạn cần xử lý trước cuối ca.",
                    "link": "/treo",
                    "muc": len(qua_han),
                }
            )
    else:
        mo = [t for t in treo if isinstance(t, dict) and t.get("trang_thai") != "xong"]
        if mo:
            viec_cho_toi.append(
                {
                    "id": "treo_ca",
                    "tieu_de": f"{len(mo)} việc treo trong ca của bạn",
                    "chi_tiet": "Đọc việc từ ca trước và xử lý trong ca.",
                    "link": "/treo",
                    "muc": len(mo),
                }
            )
    return {
        "ngay": datetime.now(UTC).date().isoformat(),
        "lich": life,
        "so_treo": len(treo),
        "so_inbox_cho": cho,
        "so_luat": len(luat),
        "canh_bao_ton": canh_bao,
        "so_nhan_vien": so_nv if role == "chu_quan" else 0,
        "treo_preview": treo_preview,
        "treo_theo_trang_thai": treo_theo_trang_thai,
        "sua_gan_day": sua_gan_day,
        "ton_tom_tat": ton_tom_tat,
        "viec_cho_toi": viec_cho_toi,
        "brief_hom_nay": kv_get("brief_hom_nay", None),
        "de_xuat_lich": de_xuat_lich,
        "co_du_lieu_mau": _co_du_lieu_mau([*treo, *inbox, *ton]),
        "nguon": "quan",
    }


@router.get("/api/v1/tieu-thu")
def tieu_thu_list(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    ton = kv_get("tieu_thu", [])
    return {
        "items": ton,
        "nguon": "quan",
        "ghi": "số lượng, không kế toán",
        "co_du_lieu_mau": _co_du_lieu_mau(ton),
    }


@router.post("/api/v1/tieu-thu")
def tieu_thu_ghi(
    body: TieuThuBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    item = {
        "id": f"tt_{uuid.uuid4().hex[:8]}",
        "hang": body.hang.strip(),
        "so_luong": body.so_luong,
        "don_vi": body.don_vi,
        "duoi_nguong": body.so_luong < 2,
        "ai": role,
        "luc": datetime.now(UTC).isoformat(),
    }

    def mut(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows.append(item)
        return rows

    kv_mutate("tieu_thu", mut, [])
    _audit("tieu_thu", role, item)
    return item


@router.post("/api/v1/waste")
def waste_ghi(
    body: WasteNoteBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_role(authorization)
    thu = (body.thu or "T2").strip()
    ghi_chu = (body.ghi_chu or "").strip()
    if not ghi_chu:
        if body.ly_do:
            ghi_chu = body.ly_do.strip()
        elif body.mon_id:
            ghi_chu = f"Hao phí {body.mon_id}: {body.so_luong or 1} {body.don_vi or 'đơn vị'}"
        else:
            ghi_chu = "Ghi nhận hao phí"
    note = {
        "thu": thu,
        "ghi_chu": ghi_chu,
        "mon_id": body.mon_id,
        "so_luong": body.so_luong,
        "don_vi": body.don_vi,
        "ly_do": body.ly_do,
        "ai": role,
        "luc": datetime.now(UTC).isoformat(),
    }

    def mut(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows.append(note)
        return rows

    kv_mutate("waste_notes", mut, [])
    return {"ok": True, **note}


@router.get("/api/v1/handover")
def handover_list(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    return {"items": kv_get("handover_history", []), "nguon": "quan"}


@router.post("/api/v1/handover")
def handover(
    body: HandoverBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_role(authorization)
    s = auth_session(authorization) or {}
    h = extract_handover(body.text)
    out = h.__dict__
    nums = validate_num(body.text, {"2", "3", "8", "15"})
    out["vf_num"] = nums.__dict__
    nv_id = s.get("nv_id") or role
    if body.alt_claim:
        other = {
            "nguoi": nv_id,
            "khung": "sang",
            "claim": body.alt_claim,
        }
        mine = {"nguoi": nv_id, "khung": "sang", "claim": h.tinh_hinh}
        c = present_conflict(mine, other)
        out["vf_conflict"] = c.__dict__
    entry = {
        "id": f"ho_{uuid.uuid4().hex[:8]}",
        "luc": datetime.now(UTC).isoformat(),
        "ai": role,
        **out,
    }

    def mut_hist(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows.append(entry)
        return rows[-50:]

    kv_mutate("handover_history", mut_hist, [])
    out["id"] = entry["id"]
    out["luc"] = entry["luc"]
    return out


@router.get("/api/v1/cam-nang")
def cam_nang_get(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    items = [enrich_luat_ui(x) for x in list_luat()]
    snap = pipeline_snapshot()
    return {
        "items": items,
        "mau": tim_mau(list_sua(include_synthetic=False)),
        "pipeline": snap,
        "nguon": "dung_lai_8_tuan",
        "so_luat_that_quan": snap["so_luat_that_quan"],
        "co_du_lieu_mau": _co_du_lieu_mau(items),
    }


@router.post("/api/v1/cam-nang/chay-8-buoc")
def cam_nang_run(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    role = _require_manager(authorization)
    sua_that = list_sua(include_synthetic=False)
    if len(sua_that) < 3:
        raise HTTPException(status_code=409, detail="chua_du_mau")
    mau_list = tim_mau(sua_that)
    if not mau_list:
        raise HTTPException(status_code=409, detail="chua_du_mau")

    existing = {x.get("id"): x for x in list_luat()}
    cho_chot: dict[str, Any] | None = None
    bi_loai: dict[str, Any] | None = None
    ung_vien: list[dict[str, Any]] = []

    for mau in mau_list:
        sua_loai = sua_rows_for_mau(mau, sua_that)
        goi_y = derive_rule_from_edits(mau, sua_loai)
        draft = propose_rule(mau, sua_mau=sua_loai, goi_y=goi_y)
        luat = de_xuat(
            mau,
            sua_rows=sua_loai,
            ban_nhap=asdict(draft) if draft is not None else None,
        )
        if luat is None:
            ung_vien.append(
                {"mau": mau["mau"], "trang_thai": "khong_du_tin_hieu", "buoc": 3, "id": None}
            )
            continue

        luat = kiem_chung(luat)
        if luat.get("trang_thai") == "loai":
            existing[luat["id"]] = luat
            if bi_loai is None:
                bi_loai = luat
            ung_vien.append(
                {
                    "mau": mau["mau"],
                    "id": luat["id"],
                    "trang_thai": luat["trang_thai"],
                    "buoc": luat["buoc"],
                    "vf_rule": luat.get("vf_rule", ""),
                }
            )
            continue

        luat = tap_su_tu_sua(luat, sua_loai)
        if luat.get("trang_thai") == "du_tap_su":
            luat["buoc"] = 6
            luat["trang_thai"] = "cho_chu_quan"
            luat["nguoi_de_xuat"] = role
            luat["nguoi_duyet_tap_su"] = role
            if cho_chot is None:
                cho_chot = luat
        existing[luat["id"]] = luat
        ung_vien.append(
            {
                "mau": mau["mau"],
                "id": luat["id"],
                "trang_thai": luat["trang_thai"],
                "buoc": luat["buoc"],
                "tap_su_dung": luat.get("tap_su_dung", 0),
            }
        )

    saved = list(existing.values())
    save_luat(saved)
    so_that = count_luat_that_quan(saved)
    _audit(
        "cam_nang_8_buoc",
        role,
        {
            "so_mau": len(mau_list),
            "cho_chu_quan": (cho_chot or {}).get("id"),
            "bi_loai": (bi_loai or {}).get("id"),
        },
    )
    return {
        "cho_chot": cho_chot,
        "bi_loai": bi_loai,
        "ung_vien": ung_vien,
        "nguon": mau_list[0].get("nguon", "ghi_truc_tiep"),
        "so_luat_that_quan": so_that,
        "pipeline": pipeline_snapshot(),
    }


@router.post("/api/v1/cam-nang/duyet")
def cam_nang_duyet(
    body: DuyetLuatBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    if body.ok:
        _require_chu_quan(authorization)
        role = "chu_quan"
    items = list_luat()
    for i, it in enumerate(items):
        if it.get("id") == body.id:
            if body.ok and it.get("trang_thai") != "cho_chu_quan":
                raise HTTPException(status_code=409, detail="luat_chua_cho_chu_quan")
            items[i] = duyet(it, ok=body.ok, ai=role)
            save_luat(items)
            _audit("cam_nang_chot", role, {"id": body.id, "ok": body.ok})
            return items[i]
    raise HTTPException(status_code=404, detail="luat")


class GoLuatBody(BaseModel):
    id: str


@router.post("/api/v1/cam-nang/go")
def cam_nang_go(
    body: GoLuatBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_chu_quan(authorization)
    items = list_luat()
    for i, it in enumerate(items):
        if it.get("id") == body.id:
            if it.get("trang_thai") != "hieu_luc":
                raise HTTPException(status_code=409, detail="luat_chua_hieu_luc")
            items[i] = go_luat(it, ai=role)
            save_luat(items)
            _audit("cam_nang_go", role, {"id": body.id})
            return items[i]
    raise HTTPException(status_code=404, detail="luat")


@router.post("/api/v1/sop")
def sop(
    body: SopBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_role(authorization)
    ctx = ops_context_from_dict(body.ngu_canh) or default_ops_context()
    r = sop_answer(
        body.question,
        buoc=load_all_buoc(),
        luat=list_luat(),
        ops_context=ctx,
    )
    return r.__dict__


@router.get("/api/v1/sop/golden")
def sop_golden(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    path = ROOT / "data" / "golden" / "sop" / "questions.jsonl"
    if not path.exists():
        raise HTTPException(status_code=409, detail="thieu_golden_sop")
    buoc = load_all_buoc()
    laws = list_luat()
    ctx = default_ops_context()
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    answers = []
    for row in rows:
        a = sop_answer(row["q"], buoc=buoc, luat=laws, ops_context=ctx)
        answers.append({"q": row["q"], **a.__dict__})
    chua = sum(1 for x in answers if x["chua_co"])
    cited = sum(1 for x in answers if x["trich_dan"] or x["chua_co"])
    return {
        "n": len(answers),
        "moi_cau_co_nguon_hoac_chua_co": cited == len(answers),
        "co_cau_chua_co": chua >= 1,
        "items": answers,
    }


@router.get("/api/v1/waste")
def waste(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    stored = kv_get("waste_notes", [])
    pairs = [(str(x.get("thu", "")), str(x.get("ghi_chu", ""))) for x in stored if x.get("ghi_chu")]
    return {
        "items": [x.__dict__ for x in cluster_waste(pairs)] if pairs else [],
        "ghi_chu": stored,
        "nguon": "quan",
        "co_du_lieu_mau": _co_du_lieu_mau(stored),
    }


@router.post("/api/v1/qr")
def qr_issue(
    body: QrBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_manager(authorization)
    if not _known_nv(body.nv_id):
        raise HTTPException(status_code=422, detail="nhan_vien_khong_ton_tai")
    if not _known_ca(body.ca_id):
        raise HTTPException(status_code=422, detail="ca_khong_hop_le")
    tok = uuid.uuid4().hex

    def mut(bag: dict[str, Any]) -> dict[str, Any]:
        bag[tok] = {"nv_id": body.nv_id, "ca_id": body.ca_id, "used": False}
        return bag

    kv_mutate("qr", mut, {})
    return {"token": tok, "mot_lan": True}


@router.post("/api/v1/qr/{token}")
def qr_use(
    token: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    caller = auth_session(authorization)
    if not caller:
        raise HTTPException(status_code=401, detail="thieu_token")
    used: dict[str, Any] | None = None

    def mut(bag: dict[str, Any]) -> dict[str, Any]:
        nonlocal used
        row = bag.get(token)
        if not row:
            raise HTTPException(status_code=404, detail="qr")
        if row["used"]:
            raise HTTPException(status_code=409, detail="qr_da_dung")
        if row.get("nv_id") != caller["nv_id"]:
            raise HTTPException(status_code=403, detail="qr_khong_phai_cua_ban")
        row = dict(row)
        row["used"] = True
        bag[token] = row
        used = row
        return bag

    kv_mutate("qr", mut, {})
    assert used is not None

    # Khoá theo ngày {ngay: [nv_id, ...]} — đồng bộ với /api/v1/diem-danh.
    ghi_diem_danh(used["nv_id"])
    _audit(
        "attendance.check_in",
        used["nv_id"],
        {
            "entity_type": "attendance",
            "entity_id": used["nv_id"],
            "nv_id": used["nv_id"],
            "ca_id": used.get("ca_id"),
            "source": "qr",
        },
    )
    return {"ok": True, "nv_id": used["nv_id"]}


@router.post("/api/v1/cho-doi-ca")
async def swap_open(
    body: SwapBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    caller = auth_session(authorization)
    if not caller:
        raise HTTPException(status_code=401, detail="thieu_token")
    if len({body.a, body.b, body.c}) != 3 or not _known_ca(body.ca_id):
        raise HTTPException(status_code=422, detail="doi_ca_khong_hop_le")
    if caller["role"] == "nhan_vien" and caller["nv_id"] not in {body.a, body.b, body.c}:
        raise HTTPException(status_code=403, detail="khong_phai_nguoi_tham_gia")
    if not _known_nv(body.a) or not _known_nv(body.b) or not _known_nv(body.c):
        raise HTTPException(status_code=422, detail="nhan_vien_khong_hop_le")
    item = {
        "id": f"sw_{uuid.uuid4().hex[:8]}",
        "a": body.a,
        "b": body.b,
        "c": body.c,
        "ca_id": body.ca_id,
        "trang_thai": "cho_3_nhanh",
        "nguon": "quan",
    }

    def mut(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items.append(item)
        return items

    kv_mutate("swap", mut, [])
    
    actor = str(caller.get("nv_id") or caller.get("username") or caller["role"])
    audit_payload = {
        "entity_type": "shift_swap",
        "entity_id": item["id"],
        "a": body.a,
        "b": body.b,
        "c": body.c,
        "ca_id": body.ca_id,
        "trang_thai": item["trang_thai"],
    }
    _audit("shift_swap.request", actor, audit_payload)
    await notify_ops_changed(
        "audit:shift_swap",
        details={"action": "shift_swap.request", "swap_id": item["id"]},
    )
    return item


@router.get("/api/v1/cho-doi-ca")
def swap_list(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    return {"items": kv_get("swap", [])}


@router.post("/api/v1/cho-doi-ca/{swap_id}/dong-y")
@router.post("/api/v1/doi-ca/{swap_id}/xac-nhan")
async def swap_dong_y(
    swap_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    caller = auth_session(authorization)
    if not caller:
        raise HTTPException(status_code=401, detail="thieu_token")
    nv = caller.get("nv_id")
    found: dict[str, Any] | None = None

    def mut(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal found
        for it in items:
            if it.get("id") != swap_id:
                continue
            # Swap đã bị từ chối thì không ai "đồng ý" hồi sinh được nữa.
            if it.get("trang_thai") == "tu_choi":
                raise HTTPException(status_code=409, detail="swap_da_tu_choi")
            parties = {it.get("a"), it.get("b"), it.get("c")} - {None, ""}
            caller_ids = {caller.get("nv_id"), caller.get("username")} - {None, ""}
            if not (caller_ids & parties) and caller.get("role") not in {"quan_ly", "chu_quan"}:
                raise HTTPException(status_code=403, detail="khong_phai_nguoi_tham_gia")
            agreed = set(it.get("dong_y", []))
            if nv and (nv in parties or caller.get("role") in {"quan_ly", "chu_quan"}):
                agreed.add(nv)
            it["dong_y"] = sorted(agreed)
            if {it["a"], it["b"]} <= agreed:
                it["trang_thai"] = "dong_y"
            found = dict(it)
            return items
        raise HTTPException(status_code=404, detail="swap_khong_tim_thay")

    kv_mutate("swap", mut, [])
    if not found:
        raise HTTPException(status_code=404, detail="swap_khong_tim_thay")
    _audit(
        "shift_swap.confirm",
        nv or caller["role"],
        {
            "entity_type": "shift_swap",
            "entity_id": swap_id,
            "dong_y": found.get("dong_y", []),
            "trang_thai": found.get("trang_thai"),
        },
    )
    await notify_ops_changed(
        "audit:shift_swap",
        details={"action": "shift_swap.confirm", "swap_id": swap_id},
    )
    return found


@router.post("/api/v1/cho-doi-ca/{swap_id}/tu-choi")
@router.post("/api/v1/doi-ca/{swap_id}/tu-choi")
async def swap_tu_choi(
    swap_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    caller = auth_session(authorization)
    if not caller:
        raise HTTPException(status_code=401, detail="thieu_token")
    nv = caller.get("nv_id")
    found: dict[str, Any] | None = None

    def mut(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal found
        for it in items:
            if it.get("id") != swap_id:
                continue
            parties = {it.get("a"), it.get("b"), it.get("c")} - {None, ""}
            caller_ids = {caller.get("nv_id"), caller.get("username")} - {None, ""}
            if not (caller_ids & parties) and caller.get("role") not in {"quan_ly", "chu_quan"}:
                raise HTTPException(status_code=403, detail="khong_phai_nguoi_tham_gia")
            it["trang_thai"] = "tu_choi"
            found = dict(it)
            return items
        raise HTTPException(status_code=404, detail="swap_khong_tim_thay")

    kv_mutate("swap", mut, [])
    if not found:
        raise HTTPException(status_code=404, detail="swap_khong_tim_thay")
    _audit(
        "shift_swap.reject",
        nv or caller["role"],
        {
            "entity_type": "shift_swap",
            "entity_id": swap_id,
            "trang_thai": found.get("trang_thai"),
        },
    )
    await notify_ops_changed(
        "audit:shift_swap",
        details={"action": "shift_swap.reject", "swap_id": swap_id},
    )
    return found


@router.get("/api/v1/ops/pickers")
def ops_pickers(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """Nhân viên và ca cho dropdown — mọi vai đăng nhập."""
    _require_role(authorization)
    seed = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    staff = [
        {"id": n["id"], "ten": n.get("ten") or n["id"]}
        for n in list_nhan_vien_ops()
        if isinstance(n, dict) and n.get("id")
    ]
    shifts = []
    for c in seed.get("ca_mau_21", []):
        if not isinstance(c, dict) or not c.get("id"):
            continue
        thu = c.get("thu") or _THU_MAP.get(int(c.get("ngay_offset", 1)), "T2")
        vi = _VI_TRI_VI.get(str(c.get("vi_tri", "")), str(c.get("vi_tri", "")).replace("_", " "))
        bat = c.get("bat_dau", "")
        ket = c.get("ket_thuc", "")
        label = f"{thu} · {bat}–{ket} · {vi}".strip(" ·")
        shifts.append(
            {
                "id": c["id"],
                "label": label,
                "thu": thu,
                "bat_dau": bat,
                "ket_thuc": ket,
                "vi_tri": c.get("vi_tri"),
            }
        )
    me = auth_session(authorization)
    return {
        "nhan_vien": staff,
        "ca": shifts,
        "me_nv_id": me.get("nv_id") if me else None,
        "nguon": "quan",
    }


@router.get("/api/v1/ab")
def ab_table() -> dict[str, Any]:
    return {
        "nguon": "quan",
        "hang": [
            {"ten": "1 agent xử lô", "p50_ms": None, "ghi": "chưa đo live"},
            {"ten": "N agent song song", "p50_ms": None, "ghi": "chưa đo live"},
            {"ten": "replay 8 task orc", "p50_ms": 0, "ghi": "cùng process"},
        ],
    }


@router.get("/api/v1/vf/conflict")
@router.get("/api/v1/vf/conflict-demo")
def conflict_sample() -> dict[str, Any]:
    a = {"nguoi": "nv_03", "khung": "sang", "claim": "có mặt"}
    b = {"nguoi": "nv_03", "khung": "sang", "claim": "vắng"}
    return present_conflict(a, b).__dict__
