"""Pure, deterministic authorization policy for operational shift forms."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AccessDecision:
    allowed: bool
    reason: str
    opens_at_ms: int
    closes_at_ms: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_phieu_access(
    *,
    nv_id: str,
    expected_nv_id: str,
    checked_in: bool,
    requires_checkin: bool,
    now_ms: int,
    opens_at_ms: int,
    closes_at_ms: int,
) -> AccessDecision:
    """Evaluate already-resolved facts; never reads storage or calls an agent."""
    if not expected_nv_id or nv_id != expected_nv_id:
        reason = "chua_phan_cong_phu_trach" if not expected_nv_id else "khong_phai_nguoi_phu_trach"
        return AccessDecision(False, reason, opens_at_ms, closes_at_ms)
    if now_ms < opens_at_ms:
        return AccessDecision(False, "chua_den_cua_so", opens_at_ms, closes_at_ms)
    if now_ms > closes_at_ms:
        return AccessDecision(False, "da_qua_cua_so", opens_at_ms, closes_at_ms)
    if requires_checkin and not checked_in:
        return AccessDecision(False, "chua_diem_danh_ca", opens_at_ms, closes_at_ms)
    return AccessDecision(True, "duoc_mo", opens_at_ms, closes_at_ms)


def load_phieu_policy(store_id: str, path: Path) -> dict[str, Any]:
    """Load default policy and shallow-merge an optional per-store override."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("quy-trinh-phieu.yaml must be a mapping")
    default = data.get("chinh_sach")
    if not isinstance(default, dict):
        raise ValueError("quy-trinh-phieu.yaml must contain chinh_sach")
    policy = {
        **default,
        "cua_so": dict(default.get("cua_so") or {}),
    }
    venue = (data.get("quan") or {}).get(store_id)
    override = venue.get("chinh_sach") if isinstance(venue, dict) else None
    if isinstance(override, dict):
        policy.update({k: v for k, v in override.items() if k != "cua_so"})
        policy["cua_so"].update(override.get("cua_so") or {})
    if not isinstance(policy.get("mui_gio"), str) or not isinstance(policy.get("phien_ban"), int):
        raise ValueError("chinh_sach must contain mui_gio and integer phien_ban")
    for event in ("ca_dau_ngay", "giao_ca", "ca_cuoi_ngay"):
        window = policy["cua_so"].get(event)
        if not isinstance(window, dict):
            raise ValueError(f"missing event window: {event}")
        if not all(isinstance(window.get(k), int) for k in ("mo_truoc_moc_phut", "dong_sau_moc_phut")):
            raise ValueError(f"invalid event window: {event}")
    return policy
