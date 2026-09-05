"""Enterprise Unit & Concurrency Tests for Auto Table Reservation Engine.

Verifies:
1. Concurrency & Race condition (TOCTOU) — zero double booking with multi-threaded attempts.
2. Table combinability matrix (single fit vs combinable pair vs >8 escalation).
3. Idempotency on repeated webhook attempts.
4. Anti-abuse guard (active booking cap & no-show blacklist).
5. 2-Phase Dialog State Machine (Extracting -> Confirming -> Confirmed).
6. Customer cancellation via chat.
7. Shift manager resolution & notification dispatch.
8. Fail-closed safety fallback.
"""

from __future__ import annotations

import concurrent.futures
import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from ca_api.persist import (
    _conn,
    init_db,
    reservation_create,
    reservation_find_active_by_psid,
    reservation_get,
    reservation_list,
    reservation_update_status,
    table_list,
    thong_bao_ca_list,
)
from ca_api.services.table_reservation_service import (
    ICT,
    NoTableAvailableError,
    atomic_hold_or_book_table,
    check_anti_abuse,
    customer_cancel_reservation,
    dispatch_reservation_notification,
    format_ict_iso,
    generate_reservation_idempotency_key,
    parse_booking_datetime,
    resolve_shift_manager_and_backup,
)
from ca_agents.ag_concierge import (
    extract_reservation_entities,
    handle_reservation,
)


@pytest.fixture(autouse=True)
def setup_clean_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_reservation.db"
    monkeypatch.setenv("NHIPQUAN_DB", str(test_db))
    monkeypatch.setenv("NHIPQUAN_AUTO_RESERVATION", "1")
    init_db()
    yield


# ── 1. Table Combinability & Matching ─────────────────────────────────────────


def test_single_table_matching():
    # 2 people -> should pick a 2-seat table (B101..B104)
    res = atomic_hold_or_book_table(
        psid="psid_01",
        customer_name="Anh Tuấn",
        phone="0912345678",
        booking_time="2026-09-10T19:00:00",
        party_size=2,
    )
    assert res["status"] == "confirmed"
    assert len(res["table_ids"]) == 1
    assert res["table_ids"][0] in ("B101", "B102", "B103", "B104")


def test_combined_table_matching():
    # 7 people -> no single table can fit (max single is 4), should combine B203 + B204 (4+4=8)
    res = atomic_hold_or_book_table(
        psid="psid_02",
        customer_name="Chị Linh",
        phone="0987654321",
        booking_time="2026-09-10T19:00:00",
        party_size=7,
    )
    assert res["status"] == "confirmed"
    assert sorted(res["table_ids"]) == ["B203", "B204"]


def test_large_group_exceeds_auto_limit():
    # 12 people -> exceeds auto limit (>8), should raise NoTableAvailableError
    with pytest.raises(NoTableAvailableError):
        atomic_hold_or_book_table(
            psid="psid_03",
            customer_name="Anh Nam",
            phone="0901234567",
            booking_time="2026-09-10T19:00:00",
            party_size=12,
        )


# ── 2. Concurrency & TOCTOU Double-Booking Test ───────────────────────────────


def test_concurrency_race_condition_no_double_booking():
    # Set all tables inactive except B105 (4 seats)
    with _conn() as cx:
        cx.execute("UPDATE ban_an SET trang_thai_hoat_dong=0 WHERE id != 'B105'")

    assert len([t for t in table_list() if t["trang_thai_hoat_dong"] == 1]) == 1

    success_count = 0
    failure_count = 0

    def attempt_booking(i: int):
        try:
            res = atomic_hold_or_book_table(
                psid=f"psid_race_{i}",
                customer_name=f"Khách {i}",
                phone=f"091100000{i}",
                booking_time="2026-09-12T19:00:00",
                party_size=4,
            )
            return True, res
        except NoTableAvailableError:
            return False, None

    # Run 8 concurrent booking requests for the exact same table and time
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(attempt_booking, i) for i in range(8)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    for ok, res in results:
        if ok:
            success_count += 1
        else:
            failure_count += 1

    # Exactly 1 request must win B105, the other 7 must fail
    assert success_count == 1, f"Expected 1 winner but got {success_count}"
    assert failure_count == 7, f"Expected 7 failures but got {failure_count}"


# ── 3. Webhook Idempotency ───────────────────────────────────────────────────


def test_idempotency_repeated_webhook():
    time_str = "2026-09-15T18:30:00"
    res1 = atomic_hold_or_book_table(
        psid="psid_idem",
        customer_name="Trùng Lặp",
        phone="0933111222",
        booking_time=time_str,
        party_size=3,
    )
    # Repeated attempt with same customer and time
    res2 = atomic_hold_or_book_table(
        psid="psid_idem",
        customer_name="Trùng Lặp",
        phone="0933111222",
        booking_time=time_str,
        party_size=3,
    )
    assert res1["id"] == res2["id"]
    # Verify only 1 record exists in DB
    all_res = reservation_list()
    assert len([r for r in all_res if r["psid"] == "psid_idem"]) == 1


# ── 4. Anti-Abuse & Blacklist ────────────────────────────────────────────────


def test_anti_abuse_active_booking_cap():
    # First booking succeeds
    atomic_hold_or_book_table(
        psid="psid_abuser",
        customer_name="Khách Spam",
        phone="0944000111",
        booking_time="2026-09-16T19:00:00",
        party_size=2,
    )
    # Second booking from same PSID is blocked by anti-abuse
    allowed, reason = check_anti_abuse(psid="psid_abuser", phone="0944000111")
    assert not allowed
    assert reason == "active_booking_exists"


def test_anti_abuse_no_show_blacklist():
    # Insert 2 previous no-show records for this phone
    for i in range(2):
        res_id = reservation_create(
            {
                "psid": f"psid_old_{i}",
                "customer_name": "Khách Bùng",
                "phone": "0999888777",
                "booking_time": f"2026-09-0{i+1}T19:00:00",
                "party_size": 2,
                "table_ids": ["B101"],
                "status": "no_show",
            }
        )

    allowed, reason = check_anti_abuse(phone="0999888777")
    assert not allowed
    assert reason == "no_show_blacklist"


# ── 5. Dialog State Machine (Extracting -> Confirming -> Confirmed) ───────────


def test_dialog_state_machine_3_turns():
    psid = "psid_dialog_user"

    # Turn 1: Customer asks without time & phone
    ticket1 = handle_reservation("Cho mình đặt bàn 4 người nha", psid=psid)
    assert ticket1.action_type == "ask_info"
    assert not ticket1.requires_human_approval
    assert "mấy giờ" in ticket1.suggested_reply.lower()

    # State carried over
    session_state = ticket1.extracted_data

    # Turn 2: Customer provides time and phone
    ticket2 = handle_reservation(
        "19h tối nay nhé, sđt 0912345678, tên Hùng",
        psid=psid,
        session_state=session_state,
    )
    assert ticket2.action_type == "ask_confirmation"
    assert not ticket2.requires_human_approval
    assert "xác nhận lại thông tin" in ticket2.suggested_reply.lower()
    assert "4" in ticket2.suggested_reply
    assert "0912345678" in ticket2.suggested_reply

    # State now in CONFIRMING
    session_state = ticket2.extracted_data
    assert session_state.get("dialog_step") == "CONFIRMING"

    # Turn 3: Customer confirms "Đúng rồi em"
    ticket3 = handle_reservation(
        "Đúng rồi em ơi",
        psid=psid,
        session_state=session_state,
    )
    assert ticket3.action_type == "confirmed"
    assert not ticket3.requires_human_approval
    assert "đã xác nhận giữ bàn" in ticket3.suggested_reply.lower()

    # Check reservation in database
    actives = reservation_find_active_by_psid(psid)
    assert len(actives) == 1
    assert actives[0]["customer_name"] == "Hùng"
    assert actives[0]["party_size"] == 4


# ── 6. Cancellation via Chat ─────────────────────────────────────────────────


def test_customer_cancellation_flow():
    psid = "psid_cancel_user"
    # Create confirmed booking
    atomic_hold_or_book_table(
        psid=psid,
        customer_name="Khách Hủy",
        phone="0911223344",
        booking_time="2026-09-17T20:00:00",
        party_size=2,
    )
    assert len(reservation_find_active_by_psid(psid)) == 1

    # Customer chats "mình bận không đến được, hủy bàn giúp mình"
    ticket = handle_reservation("mình bận không đến được, hủy bàn giúp mình", psid=psid)
    assert ticket.action_type == "cancelled"
    assert "đã hủy lịch đặt bàn" in ticket.suggested_reply.lower()

    # Active reservations should now be 0
    assert len(reservation_find_active_by_psid(psid)) == 0


# ── 7. Shift Manager Resolution & Notification Dispatch ──────────────────────


def test_shift_manager_resolution_and_notification():
    dt = parse_booking_datetime("2026-09-18T19:30:00")  # Evening shift
    shift_info = resolve_shift_manager_and_backup(dt)

    assert shift_info["khung"] == "toi"
    assert shift_info["primary_nv_id"] is not None

    # Test notification dispatch
    res = {
        "id": "res_notif_test",
        "customer_name": "Bảo An",
        "phone": "0988776655",
        "booking_time": "2026-09-18T19:30:00+07:00",
        "party_size": 4,
        "table_ids": ["B105"],
        "notified_nv_id": shift_info["primary_nv_id"],
    }
    dispatch_res = dispatch_reservation_notification(res)
    assert dispatch_res["notification_id"] is not None

    # Check in database
    notifs = thong_bao_ca_list(shift_info["primary_nv_id"])
    assert any(n["dat_ban_id"] == "res_notif_test" for n in notifs)


def test_auto_reservation_disabled_flag_requires_human_approval(monkeypatch):
    monkeypatch.setenv("NHIPQUAN_AUTO_RESERVATION", "0")
    ticket = handle_reservation("Cho mình đặt bàn 4 người lúc 19h tối nay", psid="psid_off")
    assert ticket.requires_human_approval is True
    assert ticket.action_type == "needs_manager_review"
    assert "chuẩn bị bàn" in ticket.suggested_reply.lower()


# ── 8. HTTP API Endpoints Full Lifecycle & RBAC Tests ─────────────────────────


def test_reservation_http_endpoints_full_lifecycle():
    from fastapi.testclient import TestClient
    from ca_api.interfaces.http.main import app as fastapi_app
    from unit.auth_util import headers

    client = TestClient(fastapi_app)
    auth = headers(client, "lan")

    # 1. RBAC check: Unauthenticated access blocked
    unauth = client.get("/api/v1/reservations")
    assert unauth.status_code == 401

    # 2. Get tables (should return 10 seeded tables)
    r_tables = client.get("/api/v1/reservations/tables", headers=auth)
    assert r_tables.status_code == 200
    tables = r_tables.json()["tables"]
    assert len(tables) == 10
    assert any(t["id"] == "B101" for t in tables)

    # 3. Create a reservation
    res = atomic_hold_or_book_table(
        psid="psid_http_test",
        customer_name="Trần Văn Nam",
        phone="0918889999",
        booking_time="2026-09-20T19:00:00",
        party_size=4,
    )
    res_id = res["id"]

    # 4. List reservations
    r_list = client.get("/api/v1/reservations", headers=auth)
    assert r_list.status_code == 200
    items = r_list.json()["items"]
    assert any(item["id"] == res_id for item in items)

    # 5. Get detail
    r_detail = client.get(f"/api/v1/reservations/{res_id}", headers=auth)
    assert r_detail.status_code == 200
    assert r_detail.json()["reservation"]["customer_name"] == "Trần Văn Nam"

    # 6. Check-in (seated)
    r_checkin = client.post(f"/api/v1/reservations/{res_id}/check-in", headers=auth)
    assert r_checkin.status_code == 200
    assert r_checkin.json()["status"] == "seated"

    # 7. Complete (completed)
    r_complete = client.post(f"/api/v1/reservations/{res_id}/complete", headers=auth)
    assert r_complete.status_code == 200
    assert r_complete.json()["status"] == "completed"

    # 8. No-show workflow on new booking
    res2 = atomic_hold_or_book_table(
        psid="psid_http_noshow",
        customer_name="Khách Vắng",
        phone="0917778888",
        booking_time="2026-09-21T19:00:00",
        party_size=2,
    )
    r_noshow = client.post(f"/api/v1/reservations/{res2['id']}/no-show", headers=auth)
    assert r_noshow.status_code == 200
    assert r_noshow.json()["status"] == "no_show"

    # 9. Cancel workflow on new booking
    res3 = atomic_hold_or_book_table(
        psid="psid_http_cancel",
        customer_name="Khách Bận",
        phone="0916667777",
        booking_time="2026-09-22T19:00:00",
        party_size=2,
    )
    r_cancel = client.post(
        f"/api/v1/reservations/{res3['id']}/cancel",
        json={"reason": "Khách đổi kế hoạch đột xuất"},
        headers=auth,
    )
    assert r_cancel.status_code == 200
    assert r_cancel.json()["status"] == "cancelled"

    # 10. Metrics endpoint
    r_metrics = client.get("/api/v1/reservations-metrics", headers=auth)
    assert r_metrics.status_code == 200
    metrics = r_metrics.json()
    assert metrics["ok"] is True
    assert metrics["total"] >= 3
    assert metrics["completed"] >= 1
    assert metrics["no_show"] >= 1
    assert metrics["cancelled"] >= 1


