"""AG-EXPLAIN — Episodic Memory & Reflection (CoALA).

Nguồn: `plans/260918-y-tuong-dot-pha-nho.md` mục 4.

ADR-002: suy ngẫm (reflection) dựng từ dữ liệu thật (episode), không LLM.
ADR-008: chỉ đọc + suy ngẫm, không thay đổi gì.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from ca_contracts.episodic_memory import (
    Episode,
    EpisodeType,
    Reflection,
    ReflectionResult,
)


def _episode_from_row(row: dict[str, Any]) -> Episode | None:
    """Chuyển một bản ghi thô thành Episode (tất định)."""
    loai_raw = str(row.get("loai") or row.get("type") or "")
    loai_map = {
        "phan_nan": EpisodeType.PHAN_NAN,
        "doanh_thu_cao": EpisodeType.DOANH_THU_CAO,
        "doanh_thu_thap": EpisodeType.DOANH_THU_THAP,
        "su_co": EpisodeType.SU_CO,
        "khen_ngoi": EpisodeType.KHEN_NGOI,
    }
    loai = loai_map.get(loai_raw)
    if loai is None:
        return None
    return Episode(
        episode_id=str(row.get("id") or row.get("episode_id") or ""),
        loai=loai,
        thoi_gian=str(row.get("thoi_gian") or row.get("ngay") or row.get("at") or ""),
        mo_ta=str(row.get("mo_ta") or row.get("noi_dung") or ""),
        nhan_vien=str(row.get("nhan_vien") or row.get("nv") or ""),
        ca=str(row.get("ca") or ""),
        chi_tiet=dict(row.get("chi_tiet") or {}),
    )


def build_episodes(rows: list[dict[str, Any]]) -> list[Episode]:
    """Chuyển danh sách bản ghi thô thành episodes."""
    return [e for e in (_episode_from_row(r) for r in rows) if e is not None]


def reflect_on_episodes(
    episodes: list[Episode],
    *,
    min_episodes: int = 2,
) -> list[Reflection]:
    """Suy ngẫm nguyên nhân gốc từ nhóm episode (tất định).

    Nhóm episode theo (loai, nhan_vien, ca). Nếu nhóm có >= min_episodes,
    tạo reflection với nguyên nhân gốc dựa trên chi_tiet.
    """
    groups: dict[tuple[str, str, str], list[Episode]] = {}
    for ep in episodes:
        key = (ep.loai.value, ep.nhan_vien, ep.ca)
        groups.setdefault(key, []).append(ep)

    reflections: list[Reflection] = []
    for i, ((loai, nv, ca), eps) in enumerate(groups.items()):
        if len(eps) < min_episodes:
            continue
        # Nguyên nhân gốc: tìm chi_tiet phổ biến nhất
        chi_tiet_counter: Counter[str] = Counter()
        for ep in eps:
            for k, v in ep.chi_tiet.items():
                chi_tiet_counter[f"{k}={v}"] += 1
        top_detail = chi_tiet_counter.most_common(1)[0][0] if chi_tiet_counter else "không rõ"
        nguyen_nhan = (
            f"{len(eps)} episode {loai} ca {ca or '?'} nhân viên {nv or '?'} "
            f"với đặc điểm {top_detail}"
        )
        de_xuat = _de_xuat_tu_loai(loai, ca)
        reflections.append(
            Reflection(
                reflection_id=f"refl_{i + 1}",
                episode_ids=[ep.episode_id for ep in eps],
                nguyen_nhan_goc=nguyen_nhan,
                de_xuat=de_xuat,
                do_tin_cay=min(1.0, 0.5 + 0.1 * len(eps)),
            )
        )
    return reflections


def _de_xuat_tu_loai(loai: str, ca: str) -> str:
    """Đề xuất từ loại episode (tất định)."""
    if loai == EpisodeType.PHAN_NAN.value:
        return f"Rà soát quy trình ca {ca or '?'} để giảm phàn nàn"
    if loai == EpisodeType.DOANH_THU_CAO.value:
        return f"Nhân rộng yếu tố thành công ca {ca or '?'}"
    if loai == EpisodeType.DOANH_THU_THAP.value:
        return f"Điều tra nguyên nhân doanh thu thấp ca {ca or '?'}"
    if loai == EpisodeType.SU_CO.value:
        return f"Kiểm tra phòng ngừa sự cố ca {ca or '?'}"
    return "Ghi nhận và duy trì"


def answer_reflection(
    cau_hoi: str,
    rows: list[dict[str, Any]],
    *,
    min_episodes: int = 2,
) -> ReflectionResult:
    """Trả lời câu hỏi "tuần này có gì bất thường?" bằng suy ngẫm (tất định)."""
    episodes = build_episodes(rows)
    reflections = reflect_on_episodes(episodes, min_episodes=min_episodes)

    if not reflections:
        ket_luan = "Không phát hiện mẫu bất thường đủ lớn để suy ngẫm."
    else:
        top = reflections[0]
        ket_luan = f"Phát hiện {len(reflections)} nhóm bất thường. Nổi bật: {top.nguyen_nhan_goc}."

    return ReflectionResult(
        cau_hoi=cau_hoi,
        episodes=episodes,
        reflections=reflections,
        ket_luan=ket_luan,
    )