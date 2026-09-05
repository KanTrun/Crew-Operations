"""Reservation Management Endpoints for Store Managers and Shift Staff."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import _nv_from_token, _require_role
from ca_api.persist import (
    reservation_get,
    reservation_list,
    reservation_update_status,
    table_list,
    thong_bao_ca_ack,
    thong_bao_ca_list,
)

router = APIRouter()


class CancelBody(BaseModel):
    reason: str = Field(default="Khách hủy hoặc không liên lạc được")


@router.get("/api/v1/reservations")
def get_reservations(
    date: Annotated[str | None, Query(description="Lọc theo ngày YYYY-MM-DD")] = None,
    status: Annotated[str | None, Query(description="Lọc theo trạng thái")] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Danh sách đơn đặt bàn của quán."""
    _require_role(authorization)
    items = reservation_list(store_id="quan_01", date=date, status=status, limit=limit)
    return {"ok": True, "items": items, "total": len(items)}


@router.get("/api/v1/reservations/tables")
def get_tables(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Danh sách sơ đồ bàn của quán."""
    _require_role(authorization)
    tables = table_list(store_id="quan_01")
    return {"ok": True, "tables": tables}


@router.get("/api/v1/reservations/{res_id}")
def get_reservation_detail(
    res_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Xem chi tiết một đơn đặt bàn."""
    _require_role(authorization)
    res = reservation_get(res_id)
    if not res:
        raise HTTPException(status_code=404, detail="reservation_not_found")
    return {"ok": True, "reservation": res}


@router.post("/api/v1/reservations/{res_id}/check-in")
def check_in_reservation(
    res_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Đánh dấu khách đã đến nhận bàn (seated)."""
    nv_id = _nv_from_token(authorization)
    success = reservation_update_status(
        res_id, new_status="seated", actor=nv_id, reason="Khách đã đến nhận bàn"
    )
    if not success:
        raise HTTPException(status_code=404, detail="reservation_not_found")
    return {"ok": True, "status": "seated"}


@router.post("/api/v1/reservations/{res_id}/no-show")
def mark_no_show_reservation(
    res_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Đánh dấu khách không đến (no_show)."""
    nv_id = _nv_from_token(authorization)
    success = reservation_update_status(
        res_id,
        new_status="no_show",
        actor=nv_id,
        reason="Quá giờ hẹn 15 phút khách không đến",
    )
    if not success:
        raise HTTPException(status_code=404, detail="reservation_not_found")
    return {"ok": True, "status": "no_show"}


@router.post("/api/v1/reservations/{res_id}/complete")
def complete_reservation(
    res_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Đánh dấu bữa ăn/uống hoàn tất, giải phóng bàn."""
    nv_id = _nv_from_token(authorization)
    success = reservation_update_status(
        res_id, new_status="completed", actor=nv_id, reason="Khách dùng xong và thanh toán"
    )
    if not success:
        raise HTTPException(status_code=404, detail="reservation_not_found")
    return {"ok": True, "status": "completed"}


@router.post("/api/v1/reservations/{res_id}/cancel")
def cancel_reservation(
    res_id: str,
    body: CancelBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Hủy đặt bàn bởi nhân viên."""
    nv_id = _nv_from_token(authorization)
    success = reservation_update_status(
        res_id,
        new_status="cancelled",
        actor=nv_id,
        reason=body.reason,
        cancelled_by="staff",
    )
    if not success:
        raise HTTPException(status_code=404, detail="reservation_not_found")
    return {"ok": True, "status": "cancelled"}


@router.get("/api/v1/reservations/notifications/me")
def get_my_notifications(
    unread_only: bool = False,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Danh sách thông báo ca trực của nhân viên hiện tại."""
    nv_id = _nv_from_token(authorization)
    items = thong_bao_ca_list(nv_id=nv_id, unread_only=unread_only, store_id="quan_01")
    return {"ok": True, "notifications": items}


@router.post("/api/v1/reservations/notifications/{thong_bao_id}/ack")
def ack_notification(
    thong_bao_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Quản lý/Ca trực xác nhận đã xem thông báo đặt bàn."""
    nv_id = _nv_from_token(authorization)
    success = thong_bao_ca_ack(thong_bao_id, nv_id)
    return {"ok": success}


@router.get("/api/v1/reservations-metrics")
def get_reservation_metrics(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Các chỉ số thống kê đặt bàn của quán."""
    _require_role(authorization)
    all_res = reservation_list(store_id="quan_01", limit=1000)
    total = len(all_res)
    by_status: dict[str, int] = {}
    for r in all_res:
        st = r.get("status", "unknown")
        by_status[st] = by_status.get(st, 0) + 1

    return {
        "ok": True,
        "total": total,
        "by_status": by_status,
        "confirmed": by_status.get("confirmed", 0),
        "seated": by_status.get("seated", 0),
        "completed": by_status.get("completed", 0),
        "cancelled": by_status.get("cancelled", 0),
        "no_show": by_status.get("no_show", 0),
    }
