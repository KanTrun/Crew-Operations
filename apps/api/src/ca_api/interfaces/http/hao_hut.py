"""HTTP — Hao hụt tiêu thụ theo nguyên liệu (plan 260923-1736).

Bề mặt đầy đủ của miền hao hụt. Trước đây chỉ có `POST/GET /api/v1/waste` ghi và
gom cụm ghi chú, nên không trả lời được "nguyên liệu nào hao, bao nhiêu".

Đường đọc ở đây **gọi đúng một hàm** với agent mẹ:
`ca_agents.ag_waste.tinh_tu_nguon`. Trang web và câu trả lời của AG-COPILOT nhờ
vậy không thể lệch số — hai đường tự ghép lấy là hai cơ hội để lệch.

Giữ nguyên `POST/GET /api/v1/waste` cũ cho UI và e2e hiện có.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Annotated, Any

try:
    from datetime import UTC, datetime
except ImportError:  # pragma: no cover
    from datetime import datetime, timezone

    UTC = timezone.utc

import yaml
from ca_agents.ag_waste import tinh_tu_nguon
from ca_contracts import LossThreshold
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import _require_manager, _require_role
from ca_api.persist import audit_add, kv_get, kv_mutate, menu_list

router = APIRouter()

ROOT = Path(__file__).resolve().parents[6]
NGUONG_FILE = ROOT / "config" / "nguong-hao-hut.yaml"

_LOAI_KY = {"hom_nay", "tuan", "thang", "all"}


def _nguong() -> LossThreshold:
    """Đọc ngưỡng từ cấu hình. Thiếu file ⇒ dùng mặc định của hợp đồng.

    Không hard-code ngưỡng trong mã nghiệp vụ: đổi quy định của quán là sửa YAML.
    """
    path = Path(os.environ.get("NHIPQUAN_NGUONG_HAO_HUT") or NGUONG_FILE)
    if not path.exists():
        return LossThreshold()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return LossThreshold()
    if not isinstance(raw, dict):
        return LossThreshold()
    return LossThreshold(
        mac_dinh_phan_tram=float(raw.get("mac_dinh_phan_tram") or 5.0),
        nghiem_trong_phan_tram=float(raw.get("nghiem_trong_phan_tram") or 15.0),
        theo_mat_hang={
            str(k): float(v)
            for k, v in (raw.get("theo_mat_hang") or {}).items()
            if isinstance(v, (int, float))
        },
        phien_ban=str(raw.get("phien_ban") or ""),
        ngay_kiem=str(raw.get("ngay_kiem") or ""),
    )


def _ky_chuan(ky: str | None) -> str:
    """Kỳ lạ ⇒ về `hom_nay`. Không nhận kỳ tự do để tránh lọc ra danh sách rỗng im lặng."""
    k = (ky or "hom_nay").strip().lower()
    return k if k in _LOAI_KY else "hom_nay"


def _ds(key: str) -> list[dict[str, Any]]:
    """Đọc một khoá KV dạng danh sách, bỏ phần tử không phải dict."""
    raw = kv_get(key, [])
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def _dung_tong(ky: str) -> dict[str, Any]:
    """Ghép bốn nguồn thật thành tóm tắt hao hụt — dùng chung với agent mẹ."""
    summary = tinh_tu_nguon(
        kiem_ke=_ds("kiem_ke"),
        don_quay=_ds_don(),
        menu=menu_list(gom_an=True),
        waste_notes=_ds("waste_notes"),
        nguong=_nguong(),
        ky=ky,
    )
    return summary.model_dump()


def _ds_don() -> list[dict[str, Any]]:
    """Đơn quầy. Có nguồn inject thì dùng, không thì đọc qua persist."""
    from ca_api.persist import don_list

    try:
        return list(don_list() or [])
    except Exception:
        return []


@router.get("/api/v1/hao-hut")
def hao_hut_tong(
    ky: str | None = Query(default="hom_nay", description="hom_nay | tuan | thang | all"),
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Hao hụt theo nguyên liệu: lý thuyết ↔ thực tế, mức độ, xếp hạng nguyên nhân.

    Không có dữ liệu ⇒ trả tóm tắt rỗng (`tong_dong: 0`), **không** raise và không
    bịa số. Nguyên liệu thiếu một vế trả `muc_do: "thieu_du_lieu"` kèm `thieu_ve`.
    """
    _require_role(authorization)
    k = _ky_chuan(ky)
    try:
        data = _dung_tong(k)
    except Exception:
        # Nguồn hỏng không được làm sập màn hao hụt — trả rỗng và nói rõ.
        raise HTTPException(status_code=409, detail="khong_doc_duoc_nguon_hao_hut") from None
    return {**data, "nguon": "quan"}


@router.get("/api/v1/hao-hut/nguong")
def hao_hut_nguong(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """Ngưỡng đang áp dụng — để UI giải thích vì sao một dòng bị coi là vượt."""
    _require_role(authorization)
    n = _nguong()
    return {
        "mac_dinh_phan_tram": n.mac_dinh_phan_tram,
        "nghiem_trong_phan_tram": n.nghiem_trong_phan_tram,
        "theo_mat_hang": dict(n.theo_mat_hang),
        "phien_ban": n.phien_ban,
        "ngay_kiem": n.ngay_kiem,
        "nguon": "quan",
    }


class HaoHutGhiBody(BaseModel):
    """Ghi một lần hao hụt có nguyên nhân và mặt hàng."""

    mat_hang: str = Field(min_length=1, max_length=64)
    so_luong: float = Field(gt=0)
    don_vi: str = Field(default="đơn vị", max_length=16)
    nguyen_nhan: str = Field(default="", max_length=64)
    ghi_chu: str = Field(default="", max_length=300)
    thu: str = Field(default="T2", max_length=4)
    ca_id: str | None = Field(default=None, max_length=64)


@router.post("/api/v1/hao-hut")
def hao_hut_ghi(
    body: HaoHutGhiBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Ghi hao hụt — có mặt hàng, số lượng, nguyên nhân, và **có vết audit**.

    `POST /api/v1/waste` cũ không ghi audit, trong khi `POST /api/v1/tieu-thu` cùng
    file có ghi. Ghi dữ liệu vận hành mà không để lại vết là vi phạm ADR-008.
    """
    role = _require_role(authorization)
    mat_hang = body.mat_hang.strip()
    if not mat_hang:
        raise HTTPException(status_code=422, detail="thieu_mat_hang")

    note = {
        "id": f"hh_{uuid.uuid4().hex[:10]}",
        "mat_hang": mat_hang,
        "so_luong": body.so_luong,
        "don_vi": (body.don_vi or "đơn vị").strip(),
        "nguyen_nhan": (body.nguyen_nhan or "").strip(),
        "ghi_chu": (body.ghi_chu or "").strip(),
        "thu": (body.thu or "T2").strip(),
        "ca_id": body.ca_id,
        "ai": role,
        "luc": datetime.now(UTC).isoformat(),
        "nguon": "quan",
    }

    def mut(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows.append(note)
        return rows

    kv_mutate("waste_notes", mut, [])
    audit_add(
        datetime.now(UTC).isoformat(),
        role,
        "hao_hut",
        {
            "entity_type": "waste_note",
            "entity_id": note["id"],
            "mat_hang": note["mat_hang"],
            "so_luong": note["so_luong"],
            "nguyen_nhan": note["nguyen_nhan"],
        },
    )
    return {"ok": True, **note}


@router.get("/api/v1/hao-hut/danh-muc")
def hao_hut_danh_muc(authorization: Annotated[str | None, Header()] = None) -> dict[str, Any]:
    """Mặt hàng đã từng xuất hiện — gợi ý cho ô nhập hao hụt.

    Gộp từ ba nguồn để người ghi không phải nhớ mã: phiếu kiểm kê, ghi chú hao hụt
    đã có, và nguyên liệu trong công thức món.
    """
    _require_manager(authorization)
    tu_kiem_ke = {str(r.get("mat_hang") or "") for phieu in _ds("kiem_ke") for r in (phieu.get("muc") or []) if isinstance(r, dict)}
    tu_ghi_chu = {str(r.get("mat_hang") or "") for r in _ds("waste_notes")}
    tu_cong_thuc: set[str] = set()
    for mon in menu_list(gom_an=True):
        bom = mon.get("bom")
        if isinstance(bom, dict):
            tu_cong_thuc |= {str(k) for k in bom}

    tat_ca = sorted(x for x in (tu_kiem_ke | tu_ghi_chu | tu_cong_thuc) if x)
    return {
        "items": tat_ca,
        "tu_kiem_ke": sorted(x for x in tu_kiem_ke if x),
        "tu_ghi_chu": sorted(x for x in tu_ghi_chu if x),
        "tu_cong_thuc": sorted(x for x in tu_cong_thuc if x),
        "nguon": "quan",
    }


class KiemKeRowBody(BaseModel):
    """Một dòng mặt hàng trong phiếu kiểm kê (công thức §4.3)."""

    mat_hang: str = Field(min_length=1, max_length=64)
    dau_ca: float = 0
    nhap_trong_ca: float = 0
    cuoi_ca: float = 0
    hao_hut_ghi: float = 0


class KiemKeSeedBody(BaseModel):
    """Phiếu kiểm kê để e2e tự dựng dữ liệu của mình."""

    ngay: str = Field(min_length=10, max_length=10)
    muc: list[KiemKeRowBody] = Field(default_factory=list)


@router.post("/api/v1/hao-hut/kiem-ke-seed")
def hao_hut_kiem_ke_seed(
    body: KiemKeSeedBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Nạp một phiếu kiểm kê — CHỈ khi chạy chế độ replay/demo.

    Vì sao cần: bài e2e `hao-hut.spec.ts` kiểm rằng dòng thiếu một vế hiện **gạch**
    chứ không hiện số 0 (fail-closed). Muốn kiểm được điều đó thì phải có dữ liệu
    kiểm kê thật, nhưng `demo_api.py` (server e2e CI dùng) chỉ seed menu/bàn —
    `kiem_ke` nằm ở `scripts/seed_demo_data.py` mà e2e không chạy. Kết quả cũ:
    máy dev nào đã `make seed` thì xanh, CI sạch thì đỏ — test phụ thuộc trạng thái
    môi trường chứ không kiểm chính nó.

    Khuôn giống `/experience/rules/reset`: chỉ mở khi `CA_AGENT_MODE=replay`,
    ngoài ra trả 403 — production không gọi được để nhồi dữ liệu giả.

    Phiếu nạp vào mang `nguon="mo_phong_fixture"` để UI gắn chip "dữ liệu mẫu"
    (không ai nhầm là số đo thật), và `_la_ban_ghi_mau` nhận ra để đánh dấu.
    """
    if os.environ.get("CA_AGENT_MODE", "").strip().lower() != "replay":
        raise HTTPException(status_code=403, detail="chi_cho_phep_o_che_do_replay")
    _require_manager(authorization)

    phieu = {
        "id": f"kk_e2e_{uuid.uuid4().hex[:10]}",
        "ngay": body.ngay,
        "muc": [r.model_dump() for r in body.muc],
        "nguon": "mo_phong_fixture",
        "synthetic": True,
    }

    def mut(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rows.append(phieu)
        return rows

    kv_mutate("kiem_ke", mut, [])
    audit_add(
        datetime.now(UTC).isoformat(),
        "hao_hut_e2e_seed",
        "kiem_ke_seed",
        {"id": phieu["id"], "ngay": body.ngay, "so_dong": len(phieu["muc"])},
        actor_type="system",
        agent_name="ag_waste",
    )
    return {"ok": True, "id": phieu["id"], "so_dong": len(phieu["muc"])}
