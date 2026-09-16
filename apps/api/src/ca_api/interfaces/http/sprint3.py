"""Sprint 3 HTTP — phiếu, orc, AG-MSG, lịch của tôi, ghi nhận sửa."""

from __future__ import annotations

import csv
import io
import json
import os
import uuid
from collections.abc import Callable

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone

    UTC = timezone.utc
from pathlib import Path
from typing import Annotated, Any, cast
from zoneinfo import ZoneInfo

from ca_agents.ag_msg import classify
from ca_agents.ag_tkb.extract import extract_tkb
from ca_agents.llm import agent_mode
from ca_agents.messaging import get_port
from ca_ops import (
    PhieuRun,
    add_treo,
    complete_buoc,
    dump_run,
    escalate,
    load_phieu_catalog,
    load_run,
    load_template,
    run_to_dict,
    start_phieu,
)
from ca_playbook import list_sua, record_sua
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ca_api.orchestration import Clock, IdempotencyStore, StateMachine, dispatch_parallel
from ca_api.persist import (
    da_diem_danh_ca,
    db_path,
    ghi_diem_danh,
    ghi_diem_danh_ca,
    kv_get,
    kv_mutate,
    kv_set,
)
from ca_api.persist import session as auth_session

router = APIRouter()
ROOT = Path(__file__).resolve().parents[6]
SEED = ROOT / "data" / "seed" / "sample.json"
LICH = ROOT / "data" / "out" / "lich_tuan.json"

_clock: Clock = Clock()
_sm_by_phieu: dict[str, StateMachine] = {}
_idem = IdempotencyStore()
_orc_writes: dict[str, int] = {}


def set_clock(clock: Clock) -> None:
    global _clock
    _clock = clock


def _role(authorization: str | None) -> str | None:
    s = auth_session(authorization)
    return None if s is None else s["role"]


def _require_role(authorization: str | None) -> str:
    role = _role(authorization)
    if not role:
        raise HTTPException(status_code=401, detail="thieu_token")
    return role


def _nv_from_token(authorization: str | None) -> str:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    return s["nv_id"]


def _store_from_token(authorization: str | None) -> str:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    return s.get("store_id", "quan_01")


def _can_touch(run: Any, authorization: str | None) -> str:
    nv = _nv_from_token(authorization)
    role = _require_role(authorization)
    if role in {"quan_ly", "chu_quan"}:
        return nv
    if run.nv_id != nv and getattr(run, "receiver_nv_id", "") != nv:
        raise HTTPException(status_code=403, detail="khong_phai_chu_phieu")
    return nv


def _can_operate(run: PhieuRun, authorization: str | None) -> str:
    nv = _nv_from_token(authorization)
    current = run.current()
    if current and current.ma == "nguoi_nhan_xac_nhan":
        if not run.receiver_nv_id or nv != run.receiver_nv_id:
            raise HTTPException(status_code=403, detail="chi_nguoi_nhan_duoc_xac_nhan")
        return nv
    if run.responsible_nv_id:
        if nv != run.responsible_nv_id:
            raise HTTPException(status_code=403, detail="chi_nguoi_phu_trach_duoc_lam")
        return nv
    return _can_touch(run, authorization)


def _require_chu_quan(authorization: str | None) -> str:
    role = _require_role(authorization)
    if role != "chu_quan":
        raise HTTPException(status_code=403, detail="forbidden — requires chu_quan")
    return role


def _require_manager(authorization: str | None) -> str:
    role = _require_role(authorization)
    if role not in {"quan_ly", "chu_quan"}:
        raise HTTPException(status_code=403, detail="forbidden")
    return role


def _known_ca(ca_id: str) -> bool:
    seed = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    ids = {c["id"] for c in seed.get("ca_mau_21", [])}
    ids |= set(_phan_cong())
    return ca_id in ids


def _known_nv(nv_id: str) -> bool:
    from ca_api.nhan_vien import list_nhan_vien_ops

    ids = {n["id"] for n in list_nhan_vien_ops(include_seed=True)}
    return nv_id in ids


def _phan_cong() -> dict[str, list[str]]:
    stored = kv_get("phan_cong", None)
    if stored:
        return cast(dict[str, list[str]], stored)
    phan: dict[str, list[str]] = {}
    if LICH.exists():
        phan = json.loads(LICH.read_text(encoding="utf-8")).get("phan_cong", {})
    elif SEED.exists():
        seed = json.loads(SEED.read_text(encoding="utf-8"))
        hist = (seed.get("lich_su_8_tuan") or [{}])[0].get("phan_cong", {})
        phan = hist
    data = {cid: list(nvs) for cid, nvs in phan.items()}
    kv_set("phan_cong", data)
    return data


def _save_run(run: Any) -> None:
    def mut(bag: dict[str, Any]) -> dict[str, Any]:
        bag[run.id] = dump_run(run)
        return bag

    kv_mutate("phieu", mut, {})


def _get_run(phieu_id: str) -> PhieuRun:
    bag = kv_get("phieu", {})
    raw = bag.get(phieu_id)
    if not raw:
        raise HTTPException(status_code=404, detail="phieu_khong_tim_thay")
    return load_run(raw)


def _signals(run: Any, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = run_to_dict(run)
    esc = escalate(run, _clock.now_ms())
    if esc:
        payload["escalate"] = esc
    if extra:
        payload["signals"] = {**payload.get("signals", {}), **extra}
    return payload


class StartBody(BaseModel):
    mau: str = Field(min_length=1)
    ca_id: str = ""
    event_id: str = ""


class DiemDanhBody(BaseModel):
    occurrence_id: str = ""


class BuocBody(BaseModel):
    ma: str
    gia_tri: Any = None


class ChungBody(BaseModel):
    buoc_ma: str
    data_url: str = ""


class TreoBody(BaseModel):
    noi_dung: str


class CaBody(BaseModel):
    ca_id: str


class MsgBody(BaseModel):
    text: str
    backend: str = "console"


class TkbExtractBody(BaseModel):
    image_path_or_id: str


class TkbConfirmBody(BaseModel):
    nv_id: str | None = None
    khoang_ban: list[dict[str, str]]
    source_id: str = ""
    upload_id: str = ""


def _tkb_upload_dir() -> Path:
    base = Path(os.environ.get("NHIPQUAN_TKB_UPLOAD", "")).expanduser()
    if not str(base):
        base = db_path().parent / "tkb_uploads"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _clean_khoang_api(raw: list[dict[str, str]]) -> list[dict[str, str]]:
    thu_ok = {"T2", "T3", "T4", "T5", "T6", "T7", "CN"}
    out: list[dict[str, str]] = []
    for item in raw:
        thu = str(item.get("thu") or "").strip().upper()
        if thu in {"CN", "T8"}:
            thu = "CN"
        start = str(item.get("start") or "").strip()
        end = str(item.get("end") or "").strip()
        # AG-TKB có thể trả "07:30:00" — chuẩn hóa về "HH:MM" 5 ký tự
        # trước khi kiểm, nếu không khung giờ thật bị lọc sạch → khoang_rong.
        if len(start) == 8 and start.count(":") == 2:
            start = start[:5]
        if len(end) == 8 and end.count(":") == 2:
            end = end[:5]
        if thu not in thu_ok or len(start) != 5 or len(end) != 5:
            continue
        out.append({"thu": thu, "start": start, "end": end})
    return out


class DispatchBody(BaseModel):
    n: int = Field(default=8, ge=1, le=32)
    key: str = "orc-8"


def _published_events() -> list[dict[str, Any]]:
    from ca_api.services.shift_events import event_rows

    snapshots = kv_get("lich_van_hanh_by_week", {})
    out: list[dict[str, Any]] = []
    if isinstance(snapshots, dict):
        for snapshot in snapshots.values():
            if isinstance(snapshot, dict):
                out.extend(event_rows(snapshot))
    return out


def _find_occurrence(store_id: str, occurrence_id: str, ngay: str) -> dict[str, Any] | None:
    snapshots = kv_get("lich_van_hanh_by_week", {})
    if not isinstance(snapshots, dict):
        return None
    for snapshot in snapshots.values():
        if not isinstance(snapshot, dict) or snapshot.get("store_id") != store_id:
            continue
        for row in snapshot.get("occurrences", []):
            if row.get("id") == occurrence_id and row.get("date") == ngay:
                return {**cast(dict[str, Any], row), "mui_gio": snapshot.get("mui_gio")}
    return None


@router.post("/api/v1/diem-danh")
def diem_danh(
    body: DiemDanhBody | None = None,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, str]:
    nv = _nv_from_token(authorization)
    occurrence_id = body.occurrence_id if body else ""
    if occurrence_id:
        store_id = _store_from_token(authorization)
        now_ms = _clock.now_ms()
        today = datetime.fromtimestamp(now_ms / 1000, ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()
        occurrence = _find_occurrence(store_id, occurrence_id, today)
        if not occurrence or nv not in set(occurrence.get("nhan_vien") or []):
            raise HTTPException(status_code=403, detail="khong_thuoc_o_ca")
        ghi_diem_danh_ca(
            store_id=store_id,
            occurrence_id=occurrence_id,
            nv_id=nv,
            at_ms=now_ms,
        )
    ghi_diem_danh(nv)
    return {"ok": "true", "nv_id": nv, "occurrence_id": occurrence_id}


def _task_for(authorization: str | None) -> dict[str, Any]:
    from ca_ops import evaluate_phieu_access

    nv = _nv_from_token(authorization)
    store_id = _store_from_token(authorization)
    now_ms = _clock.now_ms()
    runs = kv_get("phieu", {})
    indexes = kv_get("phieu_event_index", {})

    if isinstance(runs, dict):
        for raw in runs.values():
            if not isinstance(raw, dict) or raw.get("store_id") != store_id or raw.get("closed"):
                continue
            run = load_run(raw)
            current = run.current()
            if run.receiver_nv_id == nv and current and current.ma == "nguoi_nhan_xac_nhan":
                if run.opens_at_ms and not run.opens_at_ms <= now_ms <= run.closes_at_ms:
                    continue
                return {"status": "ready", "item": {"role": "receiver", "run": run_to_dict(run)}}
            if run.responsible_nv_id == nv or run.nv_id == nv:
                status = "waiting_receiver" if current and current.ma == "nguoi_nhan_xac_nhan" else "ready"
                return {"status": status, "item": {"role": "actor", "run": run_to_dict(run)}}

    catalog = {x["ma"] for x in load_phieu_catalog(store_id)}
    templates_by_event = {
        str(template.get("gan_voi")): (ma, template)
        for ma in catalog
        if (template := load_template(ma)).get("gan_voi")
    }
    fallback: dict[str, Any] | None = None
    for event in sorted(_published_events(), key=lambda x: x["opens_at_ms"]):
        if event.get("store_id") != store_id or event.get("responsible_nv_id") != nv:
            continue
        resolved_template = templates_by_event.get(str(event["event_type"]))
        if not resolved_template:
            continue
        mau, template = resolved_template
        checked = da_diem_danh_ca(
            store_id=store_id,
            ngay=str(event["id"]).split("|", 1)[0],
            occurrence_id=str(event["occurrence_id"]),
            nv_id=nv,
        )
        decision = evaluate_phieu_access(
            nv_id=nv,
            expected_nv_id=str(event["responsible_nv_id"]),
            checked_in=checked,
            requires_checkin=template.get("mo_khi") == "nhan_vien_da_diem_danh",
            now_ms=now_ms,
            opens_at_ms=int(event["opens_at_ms"]),
            closes_at_ms=int(event["closes_at_ms"]),
        )
        run_id = indexes.get(event["id"]) if isinstance(indexes, dict) else None
        if run_id and isinstance(runs, dict) and run_id in runs:
            run = load_run(runs[run_id])
            if run.closed:
                continue
            return {"status": "ready", "item": {"role": "actor", "run": run_to_dict(run)}}
        item = {
            "mau": mau,
            "ten": str(template.get("ten") or mau),
            "ca_id": event["ca_id"],
            "occurrence_id": event["occurrence_id"],
            "event_id": event["id"],
            "event_type": event["event_type"],
            "role": "actor",
        }
        if decision.allowed:
            return {"status": "ready", "item": item}
        if decision.reason == "chua_diem_danh_ca":
            return {"status": "needs_checkin", "item": item, "message": decision.reason}
        if fallback is None and decision.reason == "chua_den_cua_so":
            fallback = {"status": "not_due", "item": item, "message": decision.reason}
    return fallback or {"status": "done", "message": "khong_co_phieu_den_han"}


@router.get("/api/v1/phieu/current")
def phieu_current(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    return _task_for(authorization)


@router.post("/api/v1/phieu/resolve")
def phieu_resolve(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    task = _task_for(authorization)
    item = task.get("item") if isinstance(task.get("item"), dict) else {}
    if task.get("status") != "ready" or item.get("run") or item.get("role") == "receiver":
        return task
    event = next((x for x in _published_events() if x["id"] == item.get("event_id")), None)
    if event is None:
        raise HTTPException(status_code=409, detail="su_kien_khong_con_hieu_luc")
    nv = _nv_from_token(authorization)
    seq = kv_mutate("phieu_seq", lambda value: int(value) + 1, 0)
    proposed_id = f"ph_{seq}"

    def claim(indexes: dict[str, Any]) -> dict[str, Any]:
        indexes.setdefault(str(event["id"]), proposed_id)
        return indexes

    claimed = kv_mutate("phieu_event_index", claim, {})
    run_id = str(claimed[str(event["id"])])
    persisted = kv_get("phieu", {})
    if isinstance(persisted, dict) and isinstance(persisted.get(run_id), dict):
        existing = load_run(persisted[run_id])
        return {"status": "ready", "item": {"role": "actor", "run": run_to_dict(existing)}}
    run = start_phieu(
        run_id=run_id,
        mau=str(item["mau"]),
        nv_id=nv,
        ca_id=str(event["ca_id"]),
        now_ms=_clock.now_ms(),
        diem_danh=True,
        store_id=str(event["store_id"]),
        tuan_iso=str(event["tuan_iso"]),
        occurrence_id=str(event["occurrence_id"]),
        event_type=str(event["event_type"]),
        responsible_nv_id=str(event["responsible_nv_id"]),
        receiver_nv_id=str(event.get("receiver_nv_id") or ""),
        policy_version=int(event["policy_version"]),
        opens_at_ms=int(event["opens_at_ms"]),
        closes_at_ms=int(event["closes_at_ms"]),
    )
    _save_run(run)
    return {"status": "ready", "item": {"role": "actor", "run": run_to_dict(run)}}


@router.get("/api/v1/phieu/mau")
def phieu_mau(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """Liệt kê các mẫu được quán bật trong cấu hình, không phải mọi fixture."""
    items: list[dict[str, Any]] = []
    for entry in load_phieu_catalog(_store_from_token(authorization)):
        ma = str(entry["ma"])
        tpl = load_template(ma)
        items.append(
            {
                "ma": ma,
                "ten": tpl["ten"],
                "so_buoc": len(tpl["buoc"]),
                "gan_voi": tpl.get("gan_voi", ""),
                "mo_khi": tpl.get("mo_khi", ""),
                "han_hoan_thanh_phut": tpl.get("han_hoan_thanh_phut"),
                "bat_buoc": entry["bat_buoc"],
                "buoc": tpl["buoc"],
            }
        )
    if not items:
        raise HTTPException(status_code=404, detail="khong_co_mau_phieu")
    # Giữ các khoá phẳng của mẫu đầu để không phá client cũ đang đọc `buoc`.
    dau = items[0]
    return {"items": items, "ma": dau["ma"], "ten": dau["ten"], "buoc": dau["buoc"]}


@router.post("/api/v1/phieu/start")
def phieu_start(
    body: StartBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    catalog = {entry["ma"] for entry in load_phieu_catalog(_store_from_token(authorization))}
    if body.mau not in catalog:
        raise HTTPException(status_code=404, detail="mau_phieu_khong_bat")
    task = _task_for(authorization)
    item = task.get("item") if isinstance(task.get("item"), dict) else {}
    if task.get("status") != "ready":
        raise HTTPException(status_code=403, detail=task.get("message") or task.get("status"))
    if item.get("run"):
        run = cast(dict[str, Any], item["run"])
        if run.get("mau") != body.mau or (body.event_id and run.get("event_id") != body.event_id):
            raise HTTPException(status_code=403, detail="phieu_khong_dung_su_kien")
        return run
    if item.get("mau") != body.mau or item.get("ca_id") != body.ca_id:
        raise HTTPException(status_code=403, detail="phieu_khong_dung_su_kien")
    if body.event_id and item.get("event_id") != body.event_id:
        raise HTTPException(status_code=403, detail="phieu_khong_dung_su_kien")
    resolved = phieu_resolve(authorization)
    resolved_item = cast(dict[str, Any], resolved.get("item") or {})
    if not isinstance(resolved_item.get("run"), dict):
        raise HTTPException(status_code=409, detail="khong_tao_duoc_phieu")
    return cast(dict[str, Any], resolved_item["run"])


@router.get("/api/v1/phieu/{phieu_id}")
def phieu_get(
    phieu_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    run = _get_run(phieu_id)
    _can_touch(run, authorization)
    return _signals(run)


@router.post("/api/v1/phieu/{phieu_id}/buoc")
def phieu_buoc(
    phieu_id: str,
    body: BuocBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    run = _get_run(phieu_id)
    if (
        run.current()
        and run.current().ma == "nguoi_nhan_xac_nhan"
        and run.opens_at_ms
        and not run.opens_at_ms <= _clock.now_ms() <= run.closes_at_ms
    ):
        raise HTTPException(status_code=409, detail="ngoai_cua_so_xac_nhan_ban_giao")
    _can_operate(run, authorization)
    try:
        complete_buoc(run, body.ma, body.gia_tri, _clock.now_ms())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _save_run(run)
    if run.closed:
        sm = _sm_by_phieu.get(phieu_id)
        if sm and sm.state == "dang_chay":
            sm.transition("xong")
    return _signals(run)


@router.post("/api/v1/phieu/{phieu_id}/minh-chung")
def phieu_chung(
    phieu_id: str,
    body: ChungBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    run = _get_run(phieu_id)
    _can_operate(run, authorization)
    if not body.data_url.strip().startswith("data:image/"):
        raise HTTPException(status_code=400, detail="thieu_minh_chung_anh")
    if len(body.data_url) > 400_000:
        raise HTTPException(status_code=400, detail="anh_qua_lon")
    try:
        complete_buoc(run, body.buoc_ma, body.data_url, _clock.now_ms())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _save_run(run)
    if run.closed:
        sm = _sm_by_phieu.get(phieu_id)
        if sm and sm.state == "dang_chay":
            sm.transition("xong")
    return _signals(run, extra={"minh_chung": True})


@router.post("/api/v1/phieu/{phieu_id}/treo")
def phieu_treo(
    phieu_id: str,
    body: TreoBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    run = _get_run(phieu_id)
    _can_operate(run, authorization)
    try:
        add_treo(run, body.noi_dung)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _save_run(run)

    def mut(hung: list[dict[str, Any]]) -> list[dict[str, Any]]:
        hung.append(
            {
                "id": f"treo_{uuid.uuid4().hex[:8]}",
                "phieu_id": phieu_id,
                "nv_id": run.nv_id,
                "nhan_vien": run.nv_id,
                "noi_dung": body.noi_dung,
                "trang_thai": "dang_cho",
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        return hung

    kv_mutate("treo", mut, [])
    out = _signals(run)
    out["ok"] = True
    return out


@router.get("/api/v1/viec-treo")
def viec_treo(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    return {"items": kv_get("treo", [])}


class TreoPatchBody(BaseModel):
    trang_thai: str = "xong"


@router.patch("/api/v1/viec-treo/{treo_id}")
def viec_treo_patch(
    treo_id: str,
    body: TreoPatchBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    found: dict[str, Any] | None = None

    def mut(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal found
        for it in items:
            if isinstance(it, dict) and it.get("id") == treo_id:
                it["trang_thai"] = body.trang_thai
                it["xong_luc"] = datetime.now(UTC).isoformat()
                it["xong_boi"] = role
                found = dict(it)
                return items
        raise HTTPException(status_code=404, detail="treo_khong_tim_thay")

    kv_mutate("treo", mut, [])
    if not found:
        raise HTTPException(status_code=404, detail="treo_khong_tim_thay")
    return found


@router.post("/api/v1/orc/dispatch")
def orc_dispatch(
    body: DispatchBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_manager(authorization)

    def job() -> dict[str, Any]:
        def write(i: int) -> dict[str, Any]:
            _orc_writes[body.key] = _orc_writes.get(body.key, 0) + 1
            return {"i": i, "ok": True}

        # cast: lambda có tham số mặc định nên mypy không suy được kiểu từ ngữ cảnh
        tasks = [cast("Callable[[], dict[str, Any]]", lambda i=i: write(i)) for i in range(body.n)]
        results = dispatch_parallel(tasks)
        return {"n": len(results), "results": results, "writes": _orc_writes[body.key]}

    val, replayed = _idem.once(body.key, job)
    return {"replayed": replayed, **val}


class InboxMsgBody(BaseModel):
    tom_tat: str
    agent: str = "ag_msg"


@router.get("/api/v1/inbox")
def inbox(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_manager(authorization)
    return {"items": kv_get("inbox_msg", [])}


@router.post("/api/v1/inbox")
def inbox_add(
    body: InboxMsgBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_manager(authorization)

    def mut(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items.append(
            {
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "tom_tat": body.tom_tat,
                "agent": body.agent,
                "trang_thai": "moi",
            }
        )
        return items

    items = kv_mutate("inbox_msg", mut, [])
    return {"ok": True, "n": len(items)}


@router.post("/api/v1/msg/classify")
def msg_classify(
    body: MsgBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_role(authorization)
    r = classify(body.text)
    port = get_port(body.backend)
    recipient = _nv_from_token(authorization) if authorization else "lan"
    sent = port.send(recipient, f"intent={r.intent}")
    return {
        "intent": r.intent,
        "tier": r.tier,
        "do_tin_cay": r.do_tin_cay,
        "rang_buoc": r.rang_buoc,
        "message": sent.__dict__,
    }


@router.post("/api/v1/tkb/extract")
def tkb_extract(
    body: TkbExtractBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_role(authorization)
    return extract_tkb(body.image_path_or_id, mode=agent_mode())


@router.post("/api/v1/tkb/upload")
async def tkb_upload(
    authorization: Annotated[str | None, Header()] = None,
    file: UploadFile | None = File(None),
    fixture_id: Annotated[str | None, Form()] = None,
) -> dict[str, Any]:
    """Upload ảnh TKB (hoặc dùng fixture_id để thử) → AG-TKB extract."""
    _require_role(authorization)
    upload_id = ""
    source = ""

    if fixture_id and fixture_id.strip():
        source = fixture_id.strip()
        upload_id = f"fixture:{source}"
    elif file is not None and file.filename:
        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="file_trong")
        if len(raw) > 8_000_000:
            raise HTTPException(status_code=400, detail="file_qua_lon")
        suffix = Path(file.filename).suffix.lower() or ".jpg"
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            raise HTTPException(status_code=400, detail="dinh_dang")
        upload_id = f"up_{uuid.uuid4().hex[:12]}"
        dest = _tkb_upload_dir() / f"{upload_id}{suffix}"
        dest.write_bytes(raw)
        source = str(dest)
    else:
        raise HTTPException(status_code=400, detail="thieu_file")

    # Replay khi fixture; live khi file thật (theo CA_AGENT_MODE).
    mode = "replay" if upload_id.startswith("fixture:") else agent_mode()
    result = extract_tkb(source, mode=mode)
    result["upload_id"] = upload_id
    result["agent_mode"] = mode
    return result


@router.post("/api/v1/tkb/confirm")
def tkb_confirm(
    body: TkbConfirmBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Xác nhận khoảng bận và gắn vào nhân viên — dùng khi xếp lịch."""
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    role = s["role"]
    nv = (body.nv_id or "").strip() or s["nv_id"]
    if role not in {"quan_ly", "chu_quan"} and nv != s["nv_id"]:
        raise HTTPException(status_code=403, detail="chi_gan_tkb_cua_minh")

    seed = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    nv_ids = {n["id"] for n in seed.get("nhan_vien", [])}
    if nv not in nv_ids and not nv.startswith("nv_"):
        # Tài khoản đăng ký mới vẫn được lưu theo nv_id phiên.
        pass
    khoang = _clean_khoang_api(body.khoang_ban)
    if not khoang:
        raise HTTPException(status_code=400, detail="khoang_rong")

    entry = {
        "khoang_ban": khoang,
        "source_id": body.source_id,
        "upload_id": body.upload_id,
        "xac_nhan_boi": s["nv_id"],
        "vai": role,
    }

    def mut(doc: dict[str, Any]) -> dict[str, Any]:
        doc[nv] = entry
        return doc

    kv_mutate("tkb_nv", mut, {})
    record_sua(
        loai="tkb_xac_nhan",
        truoc={},
        sau={"nv_id": nv, "n": len(khoang)},
        ai=s["nv_id"],
        now_iso=datetime.now(UTC).isoformat(),
    )
    return {"ok": True, "nv_id": nv, "khoang_ban": khoang, "n": len(khoang)}


@router.get("/api/v1/tkb/mine")
def tkb_mine(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    nv = _nv_from_token(authorization)
    doc = kv_get("tkb_nv", {})
    item = doc.get(nv) if isinstance(doc, dict) else None
    return {"nv_id": nv, "item": item, "nguon": "quan"}


@router.get("/api/v1/tkb/{nv_id}")
def tkb_get(
    nv_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    s = auth_session(authorization)
    if not s:
        raise HTTPException(status_code=401, detail="thieu_token")
    if s["role"] not in {"quan_ly", "chu_quan"} and s["nv_id"] != nv_id:
        raise HTTPException(status_code=403, detail="cam")
    doc = kv_get("tkb_nv", {})
    item = doc.get(nv_id) if isinstance(doc, dict) else None
    return {"nv_id": nv_id, "item": item, "nguon": "quan"}


@router.get("/api/v1/toi/lich")
def toi_lich(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    nv = _nv_from_token(authorization)
    phan = _phan_cong()
    seed = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    meta = {c["id"]: c for c in seed.get("ca_mau_21", [])}
    thu = {1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN"}
    mine_ids = [cid for cid, nvs in phan.items() if nv in nvs]
    ca = []
    for cid in mine_ids:
        fallback = {
            "id": cid,
            "bat_dau": "07:00",
            "ket_thuc": "12:00",
            "vi_tri": "pha_che",
            "ngay_offset": 1,
        }
        m = meta.get(cid, fallback)
        ca.append(
            {
                "id": cid,
                "ngay": thu.get(int(m.get("ngay_offset", 1)), "T2"),
                "bat_dau": m.get("bat_dau", "07:00"),
                "ket_thuc": m.get("ket_thuc", "12:00"),
                "vi_tri": m.get("vi_tri", ""),
                "khung": m.get("khung", ""),
                "co_the_nha": nv in phan.get(cid, []),
                "co_the_nhan": nv not in phan.get(cid, []),
            }
        )
    # Ràng buộc đã duyệt liên quan tới tôi (xin nghỉ / TKB bận) — để nhân viên
    # thấy hiệu lực sau khi quản lý duyệt ở /inbox, không phải chờ xếp lịch sau.
    inbox_duyet = [
        {
            "id": it.get("id"),
            "y_dinh": it.get("y_dinh"),
            "ghi": (it.get("hieu_luc") or {}).get("ghi", ""),
        }
        for it in kv_get("inbox_rang_buoc", [])
        if isinstance(it, dict)
        and it.get("trang_thai") == "duyet"
        and it.get("nv_id") == nv
    ]
    return {
        "nv_id": nv,
        "ca": ca,
        "ca_ids": mine_ids,
        "items": ca,
        "rang_buoc_da_duyet": inbox_duyet,
    }


@router.post("/api/v1/ca/nha")
def ca_nha(body: CaBody, authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    nv = _nv_from_token(authorization)
    if not _known_ca(body.ca_id):
        raise HTTPException(status_code=404, detail="ca_khong_tim_thay")
    state: dict[str, Any] = {"truoc": [], "sau": []}

    def mut(phan: dict[str, list[str]]) -> dict[str, list[str]]:
        truoc = list(phan.get(body.ca_id, []))
        if nv not in truoc:
            raise HTTPException(status_code=409, detail="khong_trong_ca")
        sau = [x for x in truoc if x != nv]
        phan[body.ca_id] = sau
        state["truoc"] = truoc
        state["sau"] = sau
        return phan

    base = _phan_cong()
    kv_mutate("phan_cong", mut, base)
    record_sua(
        loai="nha_ca",
        truoc={"ca_id": body.ca_id, "nv": state["truoc"]},
        sau={"ca_id": body.ca_id, "nv": state["sau"]},
        ai=nv,
        now_iso=_clock.now_iso(),
    )
    return {
        "ok": True,
        "ca_id": body.ca_id,
        "hanh_dong": "nha",
        "truoc": state["truoc"],
        "sau": state["sau"],
    }


@router.post("/api/v1/ca/nhan")
def ca_nhan(body: CaBody, authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    nv = _nv_from_token(authorization)
    if not _known_ca(body.ca_id):
        raise HTTPException(status_code=404, detail="ca_khong_tim_thay")
    state: dict[str, Any] = {"truoc": [], "sau": []}

    def mut(phan: dict[str, list[str]]) -> dict[str, list[str]]:
        truoc = list(phan.get(body.ca_id, []))
        if nv in truoc:
            raise HTTPException(status_code=409, detail="da_trong_ca")
        sau = [*truoc, nv]
        phan[body.ca_id] = sau
        state["truoc"] = truoc
        state["sau"] = sau
        return phan

    base = _phan_cong()
    kv_mutate("phan_cong", mut, base)
    record_sua(
        loai="nhan_ca",
        truoc={"ca_id": body.ca_id, "nv": state["truoc"]},
        sau={"ca_id": body.ca_id, "nv": state["sau"]},
        ai=nv,
        now_iso=_clock.now_iso(),
    )
    return {
        "ok": True,
        "ca_id": body.ca_id,
        "hanh_dong": "nhan",
        "truoc": state["truoc"],
        "sau": state["sau"],
    }


@router.get("/api/v1/ghi-nhan-sua")
def ghi_nhan(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """Sổ lần sửa lịch — kể cả dòng dựng lại, nhưng nói rõ dòng nào là dựng lại.

    Trước đây hàm này lọc `include_synthetic=False`, nên khi quán chưa nhả/nhận
    ca lần nào thì bảng rỗng trắng — người dùng không thấy sổ này để làm gì. Giờ
    trả cả dòng fixture, mỗi dòng kèm `nguon` để không ai nhầm dựng lại là ghi
    thật. Cổng chặn luật (`/cam-nang/chay-8-buoc`) VẪN chỉ đếm dòng ghi trực
    tiếp, nên số #10 "0 luật quán thật" không bị fixture làm sai.
    """
    _require_role(authorization)
    items = []
    for i, row in enumerate(list_sua()):
        la_dung_lai = bool(row.get("synthetic"))
        mac_dinh = "mo_phong_fixture" if la_dung_lai else "ghi_truc_tiep"
        items.append(
            {
                "id": f"sua_{i}",
                "loai": row.get("loai"),
                "truoc": json.dumps(row.get("truoc"), ensure_ascii=False),
                "sau": json.dumps(row.get("sau"), ensure_ascii=False),
                "created_at": row.get("at"),
                "luc": row.get("at"),
                "ai": row.get("ai"),
                "nguon": row.get("nguon") or mac_dinh,
                "dung_lai": la_dung_lai,
            }
        )
    so_that = sum(1 for x in items if not x["dung_lai"])
    return {"items": items, "so_ghi_truc_tiep": so_that, "so_dung_lai": len(items) - so_that}


@router.post("/api/v1/import/nhan-vien")
def import_nv(
    body: dict[str, str],
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """CSV phần 1 — parse text, no live spreadsheet vendor."""
    _require_manager(authorization)
    raw = body.get("csv", "id,ten\nnv_x,Import")
    rows = list(csv.DictReader(io.StringIO(raw)))
    return {"n": len(rows), "preview": rows[:5], "nguon": "csv_p1"}
