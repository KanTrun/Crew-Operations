"""HTTP router for AI Meeting OS — Transcription, Extraction, and Operational Application."""

from __future__ import annotations

import base64
import json

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone
    UTC = timezone.utc
from pathlib import Path
from typing import Annotated, Any

from ca_agents.ag_meeting import extract_meeting, transcribe_audio
from ca_contracts import CuocHop
from ca_playbook import record_sua
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ca_api.interfaces.http.sprint3 import _require_manager, _require_role
from ca_api.persist import audit_add, kv_get, kv_mutate, list_users

router = APIRouter(tags=["meeting"])
ROOT = Path(__file__).resolve().parents[6]
SEED = ROOT / "data" / "seed" / "sample.json"


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_staff_list() -> list[dict[str, Any]]:
    """Retrieve staff list from users table or sample seed."""
    users = list_users()
    if users:
        return [
            {
                "id": u.get("nhan_vien_id") or u.get("username"),
                "ten": u.get("display_name") or u.get("username"),
            }
            for u in users
        ]
    if SEED.is_file():
        try:
            data = json.loads(SEED.read_text(encoding="utf-8"))
            return data.get("nhan_vien", [])
        except Exception:  # noqa: BLE001
            pass
    return [
        {"id": "nv_01", "ten": "Nguyễn Văn Tuấn"},
        {"id": "nv_02", "ten": "Trà My"},
        {"id": "nv_03", "ten": "Lê Hoàng Long"},
    ]


class AnalyzeMeetingBody(BaseModel):
    text: str
    segments: list[dict[str, Any]] = Field(default_factory=list)
    meeting_type: str = "giao_ca"
    audio_source: str = "google_meet_tab"
    meeting_id: str | None = None


class TranscribeAudioBody(BaseModel):
    audio_base64: str
    mime_type: str = "audio/webm"


@router.post("/api/v1/meeting/transcribe")
def transcribe_audio_endpoint(
    body: TranscribeAudioBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Convert audio bytes to transcript with speaker diarization."""
    _require_role(authorization)
    try:
        audio_bytes = base64.b64decode(body.audio_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {exc}") from exc

    res = transcribe_audio(audio_bytes=audio_bytes, mime_type=body.mime_type)
    return {
        "ok": res.ok,
        "raw_text": res.raw_text,
        "segments": [
            {
                "nguoi_noi": s.nguoi_noi,
                "noi_dung": s.noi_dung,
                "bat_dau_s": s.bat_dau_s,
                "ket_thuc_s": s.ket_thuc_s,
            }
            for s in res.segments
        ],
        "provider": res.provider,
        "reason": res.reason,
    }


@router.post("/api/v1/meeting/analyze")
def analyze_meeting_endpoint(
    body: AnalyzeMeetingBody,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Analyze meeting transcript into structured CuocHop contract."""
    _require_role(authorization)
    staff = _get_staff_list()
    res = extract_meeting(
        text=body.text,
        segments=body.segments,
        staff_list=staff,
        meeting_type=body.meeting_type,
        meeting_id=body.meeting_id,
        audio_source=body.audio_source,
    )
    return res


@router.post("/api/v1/meeting/process-audio")
async def process_audio_upload(
    file: UploadFile = File(...),
    meeting_type: str = Form("giao_ca"),
    audio_source: str = Form("google_meet_tab"),
    live_transcript: str = Form(""),
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """1-step pipeline: Upload audio file -> STT with Diarization -> Extract CuocHop."""
    _require_role(authorization)
    audio_bytes = await file.read()
    mime = file.content_type or "audio/webm"

    trans_res = transcribe_audio(audio_bytes=audio_bytes, mime_type=mime)
    staff = _get_staff_list()

    raw_text = trans_res.raw_text.strip()
    segments = [
        {
            "nguoi_noi": s.nguoi_noi,
            "noi_dung": s.noi_dung,
            "bat_dau_s": s.bat_dau_s,
            "ket_thuc_s": s.ket_thuc_s,
        }
        for s in trans_res.segments
    ]

    # If backend STT was empty or fallback, use live_transcript captured directly from user speech
    if (not raw_text or trans_res.provider == "replay_fixture") and live_transcript.strip():
        raw_text = live_transcript.strip()
        segments = [{"nguoi_noi": "Người nói", "noi_dung": live_transcript.strip()}]

    meeting_data = extract_meeting(
        text=raw_text,
        segments=segments,
        staff_list=staff,
        meeting_type=meeting_type,
        audio_source=audio_source,
    )
    return meeting_data


@router.post("/api/v1/meeting/apply")
def apply_meeting_decisions(
    body: CuocHop,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Human-in-the-loop: Apply approved action items to opsengine and playbook."""
    user = _require_manager(authorization)
    now_iso = _now()

    # 1. Add selected action items to opsengine (treo)
    selected_actions = [a for a in body.action_items if a.da_chon]
    created_tasks = 0
    if selected_actions:

        def mut_treo(cur: list[Any]) -> list[Any]:
            nonlocal created_tasks
            res = list(cur)
            for act in selected_actions:
                task_str = f"[{body.tieu_de}] {act.ten_nguoi_nhan}: {act.tieu_de}"
                if act.han_chot:
                    task_str += f" (Hạn: {act.han_chot})"
                if task_str not in res:
                    res.append(task_str)
                    created_tasks += 1
            return res

        kv_mutate("treo", mut_treo, [])

    # 2. Record SOP proposals to playbook (đúng signature record_sua)
    sop_count = 0
    if body.de_xuat_phe_duyet:
        for prop in body.de_xuat_phe_duyet:
            if prop.trang_thai == "da_duyet" and prop.loai_de_xuat == "quy_trinh_sop":
                try:
                    record_sua(
                        loai="sop",
                        truoc={"ma_quy_trinh": prop.quy_trinh_lien_quan or prop.tieu_de or "pha_che", "buoc_so": prop.buoc_so or 1},
                        sau={
                            "noi_dung": prop.noi_dung,
                            "ly_do": prop.ly_do or f"Từ cuộc họp: {body.tieu_de}",
                        },
                        ai=str(user),
                        now_iso=now_iso,
                    )
                    sop_count += 1
                except Exception:  # noqa: BLE001
                    pass

    if body.de_xuat_sop:
        for sop in body.de_xuat_sop:
            try:
                record_sua(
                    loai="sop",
                    truoc={"ma_quy_trinh": sop.quy_trinh_lien_quan, "buoc_so": sop.buoc_so or 1},
                    sau={
                        "noi_dung": sop.noi_dung_thay_doi,
                        "ly_do": sop.ly_do or f"Từ cuộc họp: {body.tieu_de}",
                    },
                    ai=str(user),
                    now_iso=now_iso,
                )
                sop_count += 1
            except Exception:  # noqa: BLE001
                pass

    # 3. Persist meeting to store
    meeting_dict = body.model_dump()
    meeting_dict["trang_thai"] = "da_duyet"
    meeting_dict["duyet_boi"] = str(user)
    meeting_dict["duyet_luc"] = now_iso

    def mut_meetings(cur: list[dict[str, Any]]) -> list[dict[str, Any]]:
        res = [m for m in cur if m.get("id") != body.id]
        res.insert(0, meeting_dict)
        return res

    kv_mutate("meetings", mut_meetings, [])

    # 4. Audit Trail
    audit_add(
        now_iso,
        str(user),
        "duyet_cuoc_hop",
        {
            "meeting_id": body.id,
            "tieu_de": body.tieu_de,
            "tasks_created": created_tasks,
            "sop_proposals": sop_count,
        },
    )

    return {
        "ok": True,
        "meeting_id": body.id,
        "tasks_created": created_tasks,
        "sop_proposals": sop_count,
        "applied_at": now_iso,
    }


@router.get("/api/v1/meetings")
def list_meetings(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """List all recorded and analyzed meetings."""
    _require_role(authorization)
    items = kv_get("meetings", [])
    return {"items": items}


@router.get("/api/v1/meetings/{meeting_id}")
def get_meeting(
    meeting_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Get single meeting detail by ID."""
    _require_role(authorization)
    items = kv_get("meetings", [])
    for m in items:
        if m.get("id") == meeting_id:
            return m
    raise HTTPException(status_code=404, detail="Meeting not found")


@router.delete("/api/v1/meetings/{meeting_id}")
def delete_meeting(
    meeting_id: str,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Delete a recorded meeting by ID. Manager/owner only."""
    _require_manager(authorization)

    items = kv_get("meetings", [])
    if not any(m.get("id") == meeting_id for m in items):
        raise HTTPException(status_code=404, detail="Meeting not found")

    def mut(cur: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # KHÔNG gọi audit_add bên trong (tránh SQLite lock do ghi chéo trong transaction).
        return [m for m in cur if m.get("id") != meeting_id]

    kv_mutate("meetings", mut, [])

    # Ghi audit SAU khi transaction đã commit (tránh deadlock).
    audit_add(_now(), str(authorization), "xoa_cuoc_hop", {"meeting_id": meeting_id})
    return {"ok": True, "meeting_id": meeting_id, "deleted": True}
