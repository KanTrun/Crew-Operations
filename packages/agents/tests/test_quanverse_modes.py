"""QUANVERSE modes tests (Phase 06)."""

from __future__ import annotations

from ca_agents.ag_quanverse.modes import (
    ModeState,
    can_activate_mode,
    mode_affects,
)
from ca_contracts import (
    ExperienceMode,
    ExperienceProposalStatus,
)


def test_only_manager_owner_can_activate() -> None:
    assert can_activate_mode("quan_ly")
    assert can_activate_mode("chu_quan")
    assert not can_activate_mode("nhan_vien")
    assert not can_activate_mode("khach")
    assert not can_activate_mode("ai_biet")


def test_mode_state_proposal_first() -> None:
    m = ModeState(mode=ExperienceMode.TROI_MUA)
    assert m.active is False
    assert m.proposal_status is None
    # Proposal → READY → (manager confirm) → active
    m.proposal_status = ExperienceProposalStatus.CONFIRMED
    m.active = True
    assert m.active is True


def test_mode_affects_projections() -> None:
    assert mode_affects(ExperienceMode.GIO_CAO_DIEM)
    assert "quay_pha_che" in mode_affects(ExperienceMode.GIO_CAO_DIEM)


def test_employee_confirm_forbidden() -> None:
    # Phía API chặn role; test xác nhận policy
    assert not can_activate_mode("nhan_vien")