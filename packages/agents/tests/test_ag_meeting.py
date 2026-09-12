"""AG-MEETING tests — Meeting transcription, action item extraction, entity matching, and contracts validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from ca_agents.ag_meeting import extract_meeting, resolve_staff_id, transcribe_audio
from ca_contracts import CuocHop


def test_resolve_staff_id() -> None:
    staff = [
        {"id": "nv_01", "ten": "Nguyễn Văn Tuấn"},
        {"id": "nv_02", "ten": "Trà My"},
        {"id": "nv_03", "ten": "Lê Hoàng Long"},
    ]
    assert resolve_staff_id("Tuấn", staff) == "nv_01"
    assert resolve_staff_id("bé My", staff) == "nv_02"
    assert resolve_staff_id("Trà My", staff) == "nv_02"
    assert resolve_staff_id("Long", staff) == "nv_03"
    assert resolve_staff_id("Khách lạ", staff) is None
    assert resolve_staff_id("", staff) is None


def test_extract_golden_meeting_01(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    repo_root = Path(__file__).resolve().parents[4]

    golden_path = repo_root / "data" / "golden" / "meeting" / "meeting_01.json"

    if golden_path.is_file():
        golden_data = json.loads(golden_path.read_text(encoding="utf-8"))
        raw_text = golden_data["raw_transcript"]
        segments = golden_data["transcript_thoai"]
    else:
        raw_text = "Quản lý: Tuấn thay ron máy pha số 2 bị rỉ nước trước 16h."
        segments = []

    staff = [
        {"id": "nv_01", "ten": "Nguyễn Văn Tuấn"},
        {"id": "nv_02", "ten": "Trà My"},
    ]

    res = extract_meeting(
        text=raw_text,
        segments=segments,
        staff_list=staff,
        meeting_type="giao_ca",
    )

    # Validate against Pydantic CuocHop contract
    validated = CuocHop(**res)
    assert validated.loai_hop == "giao_ca"
    assert len(validated.action_items) >= 2

    # Check action items content
    tuan_items = [a for a in validated.action_items if a.ten_nguoi_nhan == "Tuấn"]
    assert len(tuan_items) >= 1
    assert tuan_items[0].nhan_vien_id == "nv_01"
    assert tuan_items[0].do_tin_cay >= 0.85

    # Check SOP proposals
    assert len(validated.de_xuat_sop) >= 1
    assert "Trà Đào" in validated.de_xuat_sop[0].quy_trinh_lien_quan


def test_transcribe_audio_replay_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    res = transcribe_audio(b"fake_audio_bytes", mime_type="audio/webm")
    assert res.ok is True
    assert len(res.segments) >= 1
    assert res.provider == "replay_fixture"


def test_extract_meeting_empty_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    res = extract_meeting("")
    validated = CuocHop(**res)
    assert validated.trang_thai == "cho_duyet"
    assert len(validated.action_items) >= 1


def test_extract_meeting_schedule_adjustments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CA_AGENT_MODE", "replay")
    meeting_text = (
        "Quản lý: Tuấn tuần sau bận thi gì không?\n"
        "Tuấn: Dạ em xin nghỉ thứ 4 vì bận thi chuyên ngành.\n"
        "Quản lý: Nhất trí duyệt Tuấn nghỉ T4. Chị Lan sẽ ghim My trực ca sáng thứ 2 nhé.\n"
        "My: Dạ em đồng ý làm ca sáng thứ 2.\n"
    )
    staff = [
        {"id": "nv_01", "ten": "Tuấn"},
        {"id": "nv_02", "ten": "My"},
        {"id": "nv_03", "ten": "Lan"},
    ]
    res = extract_meeting(text=meeting_text, staff_list=staff, meeting_type="hop_tuan")
    validated = CuocHop(**res)
    assert validated.loai_hop == "hop_tuan"
    assert len(validated.dieu_chinh_lich) >= 2
    # Verify xin_nghi
    leave_item = next((d for d in validated.dieu_chinh_lich if d.loai == "xin_nghi"), None)
    assert leave_item is not None
    assert leave_item.nhan_vien_id == "nv_01"
    assert leave_item.thu == "T4"
    # Verify ghim_ca
    pin_item = next((d for d in validated.dieu_chinh_lich if d.loai == "ghim_ca"), None)
    assert pin_item is not None
    assert pin_item.nhan_vien_id == "nv_02"
    assert pin_item.thu == "T2"
    assert pin_item.khung == "sang"

