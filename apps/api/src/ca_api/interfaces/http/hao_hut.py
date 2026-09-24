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


def _seed_kiem_ke() -> list[dict[str, Any]]:
    """Phiếu kiểm kê cho môi trường test/demo — có khi kv trống và cờ seed bật.

    `NHIPQUAN_HAO_HUT_SEED_FIXTURE` theo cùng lối với `NHIPQUAN_INBOX_SEED_FIXTURE`:
    chỉ nhồi khi kv thật trống, để không bao giờ ghi đè dữ liệu của quán.

    Vì sao cần: tóm tắt hao hụt ghép *lý thuyết* (công thức món × số phần đã bán,
    đọc từ đơn quầy) với *thực tế* (phiếu kiểm kê). Trên cơ sở dữ liệu mới, không
    có phiếu nào ⇒ không dòng nào có vế thực tế, nên không dòng nào ở mức
    `thieu_du_lieu` — đúng về logic nhưng làm màn hao hụt rỗng và e2e không còn
    gì để kiểm.

    Danh sách mặt hàng cố ý gồm **hai nhóm** theo `_MENU_MAC_DINH`:
      - `cafe_g`, `sua_ml`, `ly` — có trong công thức món, nên khi quán có đơn
        quầy thì đủ hai vế ⇒ dòng hiện **số thật** (e2e "vế có dữ liệu hiện số").
      - `dao_lat`, `banh` — không món nào trong menu mặc định dùng, nên thiếu vế
        lý thuyết ⇒ dòng ở mức `thieu_du_lieu` (e2e "thiếu dữ liệu hiện gạch").
    """
    items = _ds("kiem_ke")
    if items:
        return items
    if os.environ.get("NHIPQUAN_HAO_HUT_SEED_FIXTURE", "0").strip().lower() not in {"1", "true", "yes"}:
        return []
    mat_hangs = ["cafe_g", "sua_ml", "ly", "dao_lat", "banh"]
    return [
        {
            "id": f"kk_fx_{i + 1}",
            "khung": "sang" if i % 2 == 0 else "toi",
            "luc": f"2026-09-{20 + i:02d}T08:00:00+00:00",
            "muc": [{"mat_hang": m, "dau_ca": 10.0, "nhap_trong_ca": 5.0, "cuoi_ca": 12.0}],
        }
        for i, m in enumerate(mat_hangs)
    ]


def _dung_tong(ky: str) -> dict[str, Any]:
    """Ghép bốn nguồn thật thành tóm tắt hao hụt — dùng chung với agent mẹ."""
    summary = tinh_tu_nguon(
        kiem_ke=_seed_kiem_ke(),
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
    tu_kiem_ke = {str(r.get("mat_hang") or "") for phieu in _seed_kiem_ke() for r in (phieu.get("muc") or []) if isinstance(r, dict)}
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
