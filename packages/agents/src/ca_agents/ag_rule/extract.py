"""AG-RULE — one Vietnamese law sentence from a mined pattern. No DB."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from ca_agents.llm import agent_mode, complete, parse_json_object
from ca_gates.vf_rule import validate_rule
from ca_playbook.derive import derive_rule_from_edits

_RULE_SYSTEM = """Bạn là AG-RULE của NHỊP QUÁN.
Từ các lần sửa lịch/ca của quán, đề xuất ĐÚNG MỘT câu luật tiếng Việt ngắn gọn.
Trả JSON: {"cau": "...", "loai": "nhu_cau_ca|nguong_ton|buoc_phieu|ghep_ky_nang|hao_hut", "dieu_kien": {...}, "do_tin_cay": 0.0-1.0}
dieu_kien chỉ dùng các khóa: thu, khung, vi_tri, so_nguoi, nguong, ma_buoc, thang_kinh_nghiem.
CẤM luật về thái độ hay chỉ trích một người cụ thể (nv_XX, tên riêng).
Chỉ dựa trên bằng chứng được cung cấp."""


@dataclass
class RuleDraft:
    cau: str
    loai: str
    dieu_kien: dict[str, Any]
    bang_chung: list[str]
    do_tin_cay: float


def _replay_stub(mau: dict[str, Any]) -> RuleDraft:
    return RuleDraft(
        cau="Thứ Bảy ca chiều cần 3 người pha chế, không phải 2",
        loai=str(mau.get("loai_luat") or "nhu_cau_ca"),
        dieu_kien={"thu": "T7", "khung": "chieu", "vi_tri": "pha_che", "so_nguoi": 3},
        bang_chung=list(mau.get("bang_chung") or [])[:4],
        do_tin_cay=0.8,
    )


def _from_derived(mau: dict[str, Any], derived: dict[str, Any]) -> RuleDraft:
    return RuleDraft(
        cau=str(derived["cau"]),
        loai=str(derived.get("loai") or mau.get("loai_luat") or "nhu_cau_ca"),
        dieu_kien=dict(derived.get("dieu_kien") or {}),
        bang_chung=list(derived.get("bang_chung") or mau.get("bang_chung") or [])[:4],
        do_tin_cay=0.75,
    )


def _propose_live(mau: dict[str, Any], sua_rows: list[dict[str, Any]]) -> RuleDraft | None:
    user = json.dumps(
        {
            "mau": mau,
            "lan_sua": sua_rows[:10],
            "yeu_cau": "Một luật duy nhất, tiếng Việt, có dieu_kien máy đọc được.",
        },
        ensure_ascii=False,
    )
    res = complete(system=_RULE_SYSTEM, user=user, task="ag_rule", json_mode=True)
    if not res.ok:
        return None
    data = parse_json_object(res.text)
    if not data or not data.get("cau"):
        return None
    draft = RuleDraft(
        cau=str(data["cau"]),
        loai=str(data.get("loai") or mau.get("loai_luat") or "nhu_cau_ca"),
        dieu_kien=dict(data.get("dieu_kien") or {}),
        bang_chung=list(mau.get("bang_chung") or [])[:4],
        do_tin_cay=float(data.get("do_tin_cay") or 0.7),
    )
    check = validate_rule({**asdict(draft), "bang_chung": draft.bang_chung})
    if not check.passed:
        return None
    return draft


def propose(
    mau: dict[str, Any],
    *,
    sua_mau: list[dict[str, Any]] | None = None,
    mode: str | None = None,
) -> RuleDraft | None:
    if int(mau.get("n") or 0) < 3:
        return None

    resolved = (mode or agent_mode() or "replay").strip().lower()
    rows = sua_mau or []

    if resolved == "live" and rows:
        live = _propose_live(mau, rows)
        if live:
            return live

    if rows:
        derived = derive_rule_from_edits(mau, rows)
        if derived:
            draft = _from_derived(mau, derived)
            if validate_rule({**asdict(draft), "bang_chung": draft.bang_chung}).passed:
                return draft

    return _replay_stub(mau)
