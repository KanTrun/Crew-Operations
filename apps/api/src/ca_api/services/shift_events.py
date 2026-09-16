"""Resolve published roster cells into deterministic operational events."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

DAY_INDEX = {"T2": 1, "T3": 2, "T4": 3, "T5": 4, "T6": 5, "T7": 6, "CN": 7}


def build_operational_snapshot(
    *,
    store_id: str,
    tuan_iso: str,
    shifts: list[dict[str, Any]],
    assignments: dict[str, list[str]],
    duties: dict[str, str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    year, week = (int(x) for x in tuan_iso.replace("-W", " ").split())
    grouped: dict[str, dict[str, Any]] = {}
    for shift in shifts:
        thu = str(shift.get("thu") or "")
        khung = str(shift.get("khung") or "")
        if thu not in DAY_INDEX or not khung:
            continue
        occurrence_id = f"{thu}|{khung}"
        row = grouped.setdefault(
            occurrence_id,
            {
                "id": occurrence_id,
                "thu": thu,
                "khung": khung,
                "date": date.fromisocalendar(year, week, DAY_INDEX[thu]).isoformat(),
                "bat_dau": str(shift.get("bat_dau") or ""),
                "ket_thuc": str(shift.get("ket_thuc") or ""),
                "ca_ids": [],
                "nhan_vien": [],
                "phu_trach_nv_id": str(duties.get(occurrence_id) or ""),
            },
        )
        ca_id = str(shift.get("id") or "")
        if ca_id:
            row["ca_ids"].append(ca_id)
            row["nhan_vien"].extend(str(x) for x in assignments.get(ca_id, []))
    occurrences = list(grouped.values())
    for row in occurrences:
        row["ca_ids"] = sorted(set(row["ca_ids"]))
        row["nhan_vien"] = sorted(set(row["nhan_vien"]))
    occurrences.sort(key=lambda x: (x["date"], x["bat_dau"], x["ket_thuc"], x["khung"]))
    return {
        "store_id": store_id,
        "tuan_iso": tuan_iso,
        "policy_version": int(policy["phien_ban"]),
        "mui_gio": str(policy["mui_gio"]),
        "cua_so": policy["cua_so"],
        "occurrences": occurrences,
    }


def invalid_duties(snapshot: dict[str, Any]) -> list[str]:
    return [
        str(row["id"])
        for row in snapshot.get("occurrences", [])
        if not row.get("phu_trach_nv_id")
        or row["phu_trach_nv_id"] not in set(row.get("nhan_vien") or [])
    ]


def event_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    by_date: dict[str, list[dict[str, Any]]] = {}
    for occurrence in snapshot.get("occurrences", []):
        by_date.setdefault(str(occurrence["date"]), []).append(occurrence)
    out: list[dict[str, Any]] = []
    tz = ZoneInfo(str(snapshot["mui_gio"]))
    windows = snapshot["cua_so"]
    for day_rows in by_date.values():
        day_rows.sort(key=lambda x: (x["bat_dau"], x["ket_thuc"]))
        for index, occurrence in enumerate(day_rows):
            if index == 0:
                out.append(_event(snapshot, occurrence, "ca_dau_ngay", occurrence["bat_dau"], tz, windows))
            if index < len(day_rows) - 1:
                next_occurrence = day_rows[index + 1]
                row = _event(snapshot, occurrence, "giao_ca", occurrence["ket_thuc"], tz, windows)
                row["receiver_nv_id"] = next_occurrence.get("phu_trach_nv_id", "")
                row["receiver_occurrence_id"] = next_occurrence["id"]
                out.append(row)
            if index == len(day_rows) - 1:
                out.append(_event(snapshot, occurrence, "ca_cuoi_ngay", occurrence["ket_thuc"], tz, windows))
    return out


def _event(
    snapshot: dict[str, Any],
    occurrence: dict[str, Any],
    event_type: str,
    marker_hhmm: str,
    tz: ZoneInfo,
    windows: dict[str, Any],
) -> dict[str, Any]:
    marker = datetime.fromisoformat(f"{occurrence['date']}T{marker_hhmm}:00").replace(tzinfo=tz)
    cfg = windows[event_type]
    opens = marker - timedelta(minutes=int(cfg["mo_truoc_moc_phut"]))
    closes = marker + timedelta(minutes=int(cfg["dong_sau_moc_phut"]))
    return {
        "id": f"{occurrence['date']}|{event_type}|{occurrence['id']}",
        "store_id": snapshot["store_id"],
        "tuan_iso": snapshot["tuan_iso"],
        "event_type": event_type,
        "occurrence_id": occurrence["id"],
        "ca_id": occurrence["ca_ids"][0] if occurrence["ca_ids"] else "",
        "responsible_nv_id": occurrence.get("phu_trach_nv_id", ""),
        "receiver_nv_id": "",
        "opens_at_ms": int(opens.timestamp() * 1000),
        "closes_at_ms": int(closes.timestamp() * 1000),
        "policy_version": snapshot["policy_version"],
    }
