"""Flavor Universe — recommend từ khẩu vị khách (deterministic catalog scorer).

KHÔNG infer dị ứng từ khẩu vị. Dị ứng chỉ khi khách tuyên bố tường minh và
được lưu riêng có consent. Recommendation gắn "lý do" (nó khớp field nào).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FlavorPreference:
    """Khẩu vị khách — map sang dimension tường minh."""

    do_ngot: str = "vua"  # it / vua / ngot
    huong_tra: bool = False
    co_sua: bool = True
    dietary_allergy: list[str] = field(default_factory=list)  # chỉ khi khách khai báo


@dataclass(frozen=True)
class FlavorResult:
    """Một gợi ý đồ uống có lý do."""

    mon_id: str
    ten: str
    score: float
    reasons: list[str]
    allergy_flag: bool = False


def _base_score(pref: FlavorPreference, item: dict[str, Any]) -> tuple[float, list[str]]:
    """Scorer deterministic trên catalog (menu approved). Không LLM."""
    score = 2.0
    reasons: list[str] = []

    do_ngot_item = str(item.get("do_ngot") or "vua")
    if do_ngot_item == pref.do_ngot:
        score += 3.0
        reasons.append(f"độ ngọt {do_ngot_item} khớp khẩu vị")
    else:
        reasons.append(f"độ ngọt {do_ngot_item} (khác khẩu vị)")

    co_sua_item = bool(item.get("co_sua", True))
    if co_sua_item == pref.co_sua:
        score += 1.5
        reasons.append("loại sữa phù hợp" if pref.co_sua else "không sữa đúng yêu cầu")
    else:
        reasons.append("thành phần sữa khác yêu cầu")

    if pref.huong_tra and item.get("huong_tra"):
        score += 1.0
        reasons.append("có hương trà")

    # Allergy: chỉ khi khách khai báo tường minh → flag để chặn tuyệt đối
    return score, reasons


def scorer(pref: FlavorPreference, item: dict[str, Any]) -> FlavorResult:
    """Score một item — allergy có trong thành phần → loại ngay với flag."""
    ingredients = {str(x).lower() for x in item.get("nguyen_lieu") or []}
    allergy_hit = [a for a in pref.dietary_allergy if a.lower() in ingredients]
    if allergy_hit:
        return FlavorResult(
            mon_id=str(item.get("id") or ""),
            ten=str(item.get("ten") or ""),
            score=-100.0,
            reasons=[f"chứa {', '.join(allergy_hit)} — không gợi ý"],
            allergy_flag=True,
        )
    score, reasons = _base_score(pref, item)
    return FlavorResult(
        mon_id=str(item.get("id") or ""),
        ten=str(item.get("ten") or ""),
        score=score,
        reasons=reasons,
    )


def recommend_from_taste(
    pref: FlavorPreference,
    catalog: list[dict[str, Any]],
    *,
    limit: int = 3,
) -> list[FlavorResult]:
    """Recommend từ catalog đã duyệt — sắp xếp giảm dần score, không bịa món."""
    results = [scorer(pref, item) for item in catalog]
    # Loại allergy + score âm
    safe = [r for r in results if not r.allergy_flag and r.score > 0]
    safe.sort(key=lambda r: r.score, reverse=True)
    return safe[:limit]