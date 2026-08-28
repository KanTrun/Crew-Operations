"""Sprint 4–5 HTTP — lifecycle, audit, inbox, fairness, playbook, SOP, QR, swap."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, cast

from ca_agents.ag_handover import extract as extract_handover
from ca_agents.ag_rule import propose as propose_rule
from ca_agents.ag_sop import answer as sop_answer
from ca_agents.ag_waste import cluster as cluster_waste
from ca_gates import present_conflict, validate_num
from ca_ops import load_template
from ca_playbook import (
    de_xuat,
    duyet,
    kiem_chung,
    list_luat,
    list_sua,
    save_luat,
    tap_su,
    theo_doi,
    tim_mau,
)
from ca_solver.fairness import AXES, update_debt_from_assignment, zero_debt
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from ca_api.interfaces.http.sprint3 import _require_manager, _require_role
from ca_api.orchestration import Clock
from ca_api.persist import audit_add, audit_list, kv_get, kv_mutate, kv_set
from ca_api.persist import session as auth_session

router = APIRouter()
ROOT = Path(__file__).resolve().parents[6]
SEED = ROOT / "data" / "seed" / "sample.json"
LICH = ROOT / "data" / "out" / "lich_tuan.json"
_clock = Clock()
_ALLOWED = {
    "nhap": {"dang_giai"},
    "dang_giai": {"cho_duyet", "nhap"},
    "cho_duyet": {"da_cong_bo", "nhap"},
    "da_cong_bo": {"da_dong"},
    "da_dong": set(),
}
_REASON = {
    "cuoi_tuan": "R-WKND",
    "dem": "R-NIGHT",
    "gio": "R-HRS",
    "vun": "R-SHORT",
}


def _audit(hanh: str, ai: str, payload: dict[str, Any]) -> None:
    audit_add(_clock.now_iso(), ai, hanh, payload)


def _run_solver() -> dict[str, Any]:
    from ca_solver import apply_luat, build_lich_input, solve_cpsat

    inp = build_lich_input()
    # TKB đã xác nhận từ ảnh đè lên (hoặc bổ sung) TKB synthetic của fixture.
    stored = kv_get("tkb_nv", {})
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
                inp.tkb[str(nv_id)] = tuples
    inp, applied = apply_luat(inp, list_luat())
    result = solve_cpsat(inp, time_limit_s=60.0)
    payload = {
        "nguon": "quan",
        "adr": "ADR-012",
        "tuan_iso": "2026-W01",
        "status": result.status,
        "ok": result.ok,
        "elapsed_s": round(result.elapsed_s, 3),
        "objective": result.objective,
        "violations": result.violations,
        "phan_cong": result.phan_cong,
        "debt_after": result.debt_after,
        "luat_ap_dung": applied,
    }
    LICH.parent.mkdir(parents=True, exist_ok=True)
    LICH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    kv_set("phan_cong", result.phan_cong)
    return {
        "status": result.status,
        "ok": result.ok,
        "best_effort": result.ok,
        "luat_ap_dung": applied,
        "violations": len(result.violations),
    }


def _life() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        kv_get(
            "lifecycle",
            {"tuan_iso": "2026-W01", "trang_thai": "nhap", "nguon": "quan"},
        ),
    )


def _save_life(doc: dict[str, Any]) -> None:
    kv_set("lifecycle", doc)


def _seed_inbox() -> list[dict[str, Any]]:
    items = kv_get("inbox_rang_buoc", [])
    if items:
        return cast(list[dict[str, Any]], items)
    items = [
        {
            "id": f"in_{i + 1}",
            "agent": "ag_msg" if i % 2 == 0 else "ag_handover",
            "tom_tat": f"Ràng buộc #{i + 1} — chờ duyệt",
            "trang_thai": "cho_duyet",
            "nguon": "quan",
        }
        for i in range(10)
    ]
    kv_set("inbox_rang_buoc", items)
    return items


def _phan() -> dict[str, list[str]]:
    stored = kv_get("phan_cong", None)
    if stored:
        return cast(dict[str, list[str]], stored)
    if LICH.exists():
        raw = json.loads(LICH.read_text(encoding="utf-8")).get("phan_cong", {})
        return cast(dict[str, list[str]], raw)
    return {}


class LifeBody(BaseModel):
    to: str


class InboxBody(BaseModel):
    quyet_dinh: str


class HandoverBody(BaseModel):
    text: str
    alt_claim: str | None = None


class SopBody(BaseModel):
    question: str


class SwapBody(BaseModel):
    a: str
    b: str
    c: str
    ca_id: str


class DuyetLuatBody(BaseModel):
    id: str
    ok: bool = True


class QrBody(BaseModel):
    nv_id: str
    ca_id: str = "w1_c01"


@router.get("/api/v1/lich/lifecycle")
def lich_life(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    return _life()


@router.post("/api/v1/lich/lifecycle")
def lich_transition(
    body: LifeBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    doc = _life()
    cur = doc.get("trang_thai", "nhap")
    if body.to not in _ALLOWED.get(cur, set()):
        raise HTTPException(status_code=409, detail=f"illegal:{cur}->{body.to}")
    doc["trang_thai"] = body.to
    if body.to == "dang_giai":
        doc["solver"] = _run_solver()
    _save_life(doc)
    _audit("lifecycle", role, {"from": cur, "to": body.to})
    return doc


@router.get("/api/v1/lich/ics")
def lich_ics(authorization: Annotated[str | None, Header()] = None) -> dict[str, str]:
    _require_role(authorization)
    phan = _phan()
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//NHIPQUAN//CA//VI"]
    for ca_id, nvs in list(phan.items())[:21]:
        uid = f"{ca_id}@nhipquan.local"
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"SUMMARY:Ca {ca_id} {' '.join(nvs)}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return {"ics": "\n".join(lines), "nguon": "quan"}


@router.get("/api/v1/audit")
def audit_get(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_manager(authorization)
    return {"items": audit_list(), "nguon": "quan"}


@router.get("/api/v1/inbox/rang-buoc")
def inbox_list(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    _seed_inbox()
    return {"items": kv_get("inbox_rang_buoc", []), "nguon": "quan"}


@router.post("/api/v1/inbox/rang-buoc/{item_id}")
def inbox_decide(
    item_id: str,
    body: InboxBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    found: dict[str, Any] | None = None
    pending_swap: dict[str, Any] | None = None

    def mut(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        nonlocal found, pending_swap
        for it in items:
            if it.get("id") == item_id:
                if body.quyet_dinh not in {"duyet", "tu_choi"}:
                    raise HTTPException(status_code=400, detail="quyet_dinh")
                it["trang_thai"] = body.quyet_dinh
                if body.quyet_dinh == "duyet":
                    # Không silent ghi phan_cong — chỉ ghi hiệu lực nghiệp vụ.
                    y = str(it.get("y_dinh") or "")
                    if y in {"doi_ca", "nhan_ca"}:
                        pending_swap = {
                            "id": f"sw_inbox_{uuid.uuid4().hex[:6]}",
                            "a": it.get("nv_id") or "unknown",
                            "b": "",
                            "c": "",
                            "ca_id": "",
                            "trang_thai": "cho_3_nhanh",
                            "nguon": it.get("nguon") or "inbox",
                            "tu_inbox": item_id,
                            "tom_tat": it.get("tom_tat"),
                        }
                        it["hieu_luc"] = {
                            "loai": "cho_doi_ca",
                            "swap_id": pending_swap["id"],
                            "ghi": "Đã mở phiếu chợ đổi ca — chưa đổi lịch tự động",
                        }
                    elif y in {"xin_nghi", "bao_tre", "cap_nhat_tkb"}:
                        it["hieu_luc"] = {
                            "loai": "rang_buoc_cho_solver",
                            "ghi": "Đã duyệt — áp vào lượt xếp lịch tới (không sửa phan_cong tại chỗ)",
                        }
                    else:
                        it["hieu_luc"] = {
                            "loai": "ghi_nhan",
                            "ghi": "Đã ghi nhận — không đổi lịch",
                        }
                found = it
                break
        return items

    _seed_inbox()
    kv_mutate("inbox_rang_buoc", mut, [])
    if pending_swap is not None:

        def add_swap(items_sw: list[dict[str, Any]]) -> list[dict[str, Any]]:
            items_sw.append(pending_swap)
            return items_sw

        kv_mutate("swap", add_swap, [])
    if not found:
        raise HTTPException(status_code=404, detail="inbox_item")
    _audit("inbox", role, {"id": item_id, "q": body.quyet_dinh, "y": found.get("y_dinh")})
    return found


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
    hang: str
    so_luong: float
    don_vi: str = "khay"


class WasteNoteBody(BaseModel):
    thu: str
    ghi_chu: str


@router.get("/api/v1/hom-nay")
def hom_nay(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    life = _life()
    treo = kv_get("treo", [])
    inbox = kv_get("inbox_rang_buoc", [])
    cho = sum(1 for x in inbox if x.get("trang_thai") == "cho_duyet")
    luat = list_luat()
    ton = kv_get("tieu_thu", [])
    canh_bao = [x["hang"] for x in ton if x.get("duoi_nguong")]
    return {
        "ngay": datetime.now(UTC).date().isoformat(),
        "lich": life,
        "so_treo": len(treo),
        "so_inbox_cho": cho,
        "so_luat": len(luat),
        "canh_bao_ton": canh_bao,
        "nguon": "quan",
    }


@router.get("/api/v1/tieu-thu")
def tieu_thu_list(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    return {"items": kv_get("tieu_thu", []), "nguon": "quan", "ghi": "số lượng, không kế toán"}


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
    _require_role(authorization)
    note = {"thu": body.thu.strip(), "ghi_chu": body.ghi_chu.strip()}

    def mut(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows.append(note)
        return rows

    kv_mutate("waste_notes", mut, [])
    return {"ok": True, **note}


@router.post("/api/v1/handover")
def handover(
    body: HandoverBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_role(authorization)
    h = extract_handover(body.text)
    out = h.__dict__
    nums = validate_num(body.text, {"2", "3", "8", "15"})
    out["vf_num"] = nums.__dict__
    if body.alt_claim:
        other = {
            "nguoi": "nv_03",
            "khung": "sang",
            "claim": body.alt_claim,
        }
        mine = {"nguoi": "nv_03", "khung": "sang", "claim": h.tinh_hinh}
        c = present_conflict(mine, other)
        out["vf_conflict"] = c.__dict__
    return out


@router.get("/api/v1/cam-nang")
def cam_nang_get(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    return {"items": list_luat(), "mau": tim_mau(), "nguon": "dung_lai_8_tuan"}


@router.post("/api/v1/cam-nang/chay-8-buoc")
def cam_nang_run(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_manager(authorization)
    if len(list_sua(include_synthetic=False)) < 3:
        raise HTTPException(status_code=409, detail="chua_du_mau")
    mau = tim_mau(list_sua(include_synthetic=False))
    if not mau:
        raise HTTPException(status_code=409, detail="chua_du_mau")
    draft = propose_rule(mau[0])
    luat = de_xuat(mau[0])
    if draft:
        luat["cau"] = draft.cau
        luat["dieu_kien"] = draft.dieu_kien
    luat = kiem_chung(luat)
    luat = tap_su(luat, [("them_1_pha_che", "them_1_pha_che")] * 5)
    luat = duyet(luat, ok=True, ai="chu_quan")
    luat = theo_doi(luat, dung=7, ghi_de=0)
    bad = {
        "id": "luat_thai_do",
        "loai": "ghep_ky_nang",
        "cau": "nv_03 lười không xếp cuối tuần",
        "dieu_kien": {"thu": "T7"},
        "bang_chung": ["1", "2", "3"],
    }
    loai = kiem_chung(bad)
    weak = dict(luat)
    weak["id"] = "luat_60pct"
    weak = theo_doi(weak, dung=3, ghi_de=2)
    existing = {x.get("id"): x for x in list_luat()}
    for item in (luat, loai, weak):
        existing[item["id"]] = item
    save_luat(list(existing.values()))
    _audit("cam_nang_8_buoc", "chu_quan", {"hieu_luc": luat["id"], "loai": loai["vf_rule"]})
    return {
        "hieu_luc": luat,
        "bi_loai": loai,
        "tu_tat_60pct": weak,
        "nguon": "dung_lai_8_tuan",
        "so_luat_that_quan": 0,
    }


@router.post("/api/v1/cam-nang/duyet")
def cam_nang_duyet(
    body: DuyetLuatBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    role = _require_manager(authorization)
    items = list_luat()
    for i, it in enumerate(items):
        if it.get("id") == body.id:
            items[i] = duyet(it, ok=body.ok, ai=role)
            save_luat(items)
            return items[i]
    raise HTTPException(status_code=404, detail="luat")


@router.post("/api/v1/sop")
def sop(
    body: SopBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_role(authorization)
    tpl = load_template("mo_quan")
    r = sop_answer(body.question, buoc=tpl["buoc"], luat=list_luat())
    return r.__dict__


@router.get("/api/v1/sop/golden")
def sop_golden(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    path = ROOT / "data" / "golden" / "sop" / "questions.jsonl"
    if not path.exists():
        raise HTTPException(status_code=409, detail="thieu_golden_sop")
    tpl = load_template("mo_quan")
    laws = list_luat()
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    answers = []
    for row in rows:
        a = sop_answer(row["q"], buoc=tpl["buoc"], luat=laws)
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
    }


@router.post("/api/v1/qr")
def qr_issue(
    body: QrBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_manager(authorization)
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
    _require_role(authorization)
    used: dict[str, Any] | None = None

    def mut(bag: dict[str, Any]) -> dict[str, Any]:
        nonlocal used
        row = bag.get(token)
        if not row:
            raise HTTPException(status_code=404, detail="qr")
        if row["used"]:
            raise HTTPException(status_code=409, detail="qr_da_dung")
        row = dict(row)
        row["used"] = True
        bag[token] = row
        used = row
        return bag

    kv_mutate("qr", mut, {})
    assert used is not None
    return {"ok": True, "nv_id": used["nv_id"]}


@router.post("/api/v1/cho-doi-ca")
def swap_open(
    body: SwapBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    _require_role(authorization)
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
    _audit("swap", body.a, item)
    return item


@router.get("/api/v1/cho-doi-ca")
def swap_list(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    _require_role(authorization)
    return {"items": kv_get("swap", [])}


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
