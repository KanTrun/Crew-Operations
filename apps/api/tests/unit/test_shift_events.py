from __future__ import annotations

from ca_api.services.shift_events import build_operational_snapshot, event_rows, invalid_duties

POLICY = {
    "phien_ban": 3,
    "mui_gio": "Asia/Ho_Chi_Minh",
    "cua_so": {
        "ca_dau_ngay": {"mo_truoc_moc_phut": 60, "dong_sau_moc_phut": 30},
        "giao_ca": {"mo_truoc_moc_phut": 30, "dong_sau_moc_phut": 15},
        "ca_cuoi_ngay": {"mo_truoc_moc_phut": 30, "dong_sau_moc_phut": 60},
    },
}


def test_role_slots_are_grouped_into_operational_occurrences() -> None:
    shifts = [
        {"id": "c1", "thu": "T2", "khung": "sang", "bat_dau": "07:00", "ket_thuc": "12:00"},
        {"id": "c2", "thu": "T2", "khung": "sang", "bat_dau": "07:00", "ket_thuc": "12:00"},
        {"id": "c3", "thu": "T2", "khung": "chieu", "bat_dau": "12:00", "ket_thuc": "17:00"},
    ]
    snapshot = build_operational_snapshot(
        store_id="quan_01",
        tuan_iso="2026-W37",
        shifts=shifts,
        assignments={"c1": ["nv_1"], "c2": ["nv_2"], "c3": ["nv_3"]},
        duties={"T2|sang": "nv_1", "T2|chieu": "nv_3"},
        policy=POLICY,
    )
    assert len(snapshot["occurrences"]) == 2
    assert snapshot["occurrences"][0]["nhan_vien"] == ["nv_1", "nv_2"]
    assert invalid_duties(snapshot) == []
    assert [row["event_type"] for row in event_rows(snapshot)] == [
        "ca_dau_ngay",
        "giao_ca",
        "ca_cuoi_ngay",
    ]
    handover = event_rows(snapshot)[1]
    assert handover["responsible_nv_id"] == "nv_1"
    assert handover["receiver_nv_id"] == "nv_3"


def test_missing_or_external_duty_fails_publication_gate() -> None:
    snapshot = build_operational_snapshot(
        store_id="quan_01",
        tuan_iso="2026-W37",
        shifts=[
            {"id": "c1", "thu": "T2", "khung": "sang", "bat_dau": "07:00", "ket_thuc": "12:00"}
        ],
        assignments={"c1": ["nv_1"]},
        duties={"T2|sang": "nv_other"},
        policy=POLICY,
    )
    assert invalid_duties(snapshot) == ["T2|sang"]
