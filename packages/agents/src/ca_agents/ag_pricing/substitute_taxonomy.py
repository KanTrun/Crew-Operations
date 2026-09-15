"""Taxonomy nhóm món thay thế nạp từ config (plan mục 3.4).

Plan mục 3.4: ma trận nhu cầu → nhóm thay thế phải là DỮ LIỆU CẤU HÌNH versioned,
KHÔNG hard-code trong logic nghiệp vụ — để đội vận hành thêm nhóm nhu cầu mới
(VD "Ăn chay", "Ăn kiêng low-carb") mà không cần release code.

Module này thay thế `_MEAL_GROUPS` hard-code trong `substitute_matrix.py` (WIP).
`substitute_matrix.py` giữ nguyên để không phá test/tương thích ngược của v1.0.

ADR-002: mọi hàm tra cứu ở đây là THUẦN — cùng input + cùng file config → cùng
kết quả. Không LLM, không network. Loader fail-fast khi config thiếu trường
bắt buộc thay vì âm thầm bỏ qua entry.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from ca_contracts.catchment_survey_v2 import (
    SubstituteTaxonomy,
    SubstituteTaxonomyEntry,
)

ROOT = Path(__file__).resolve().parents[5]
TAXONOMY_PATH = ROOT / "config" / "substitute-taxonomy.yaml"

# Các nhóm nằm trong `entries_cho_duyet` KHÔNG được nạp vào taxonomy hoạt động
# (plan mục 1.5: agent không tự chốt thay chủ dự án).
_PENDING_SECTION = "entries_cho_duyet"

_DAU_CACH = re.compile(r"[\s_\-/]+")
# Giữ lại "_" vì `_DAU_CACH` vừa chèn nó làm dấu cách từ.
_KY_TU_LA = re.compile(r"[^a-z0-9_]+")
_KY_TU_GACH_THUA = re.compile(r"_+")


class SubstituteTaxonomyError(ValueError):
    """File taxonomy thiếu trường bắt buộc hoặc sai cấu trúc."""


@dataclass(frozen=True, slots=True)
class TaxonomyGroup:
    """Một nhóm JTBD đã nạp, kèm thông tin vận hành ngoài contract."""

    entry: SubstituteTaxonomyEntry
    mo_ta: str = ""
    nhom_lam_tron: str = "mon_chinh"
    alias: Mapping[str, tuple[str, ...]] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.alias is None:
            object.__setattr__(self, "alias", {})

    @property
    def jtbd_group(self) -> str:
        return self.entry.jtbd_group

    @property
    def core_categories(self) -> tuple[str, ...]:
        return tuple(self.entry.core_categories)

    @property
    def substitute_categories(self) -> tuple[str, ...]:
        return tuple(self.entry.substitute_categories)

    @property
    def version(self) -> int:
        return self.entry.version


def normalize_category_name(raw: str) -> str:
    """Chuẩn hoá tên món về snake_case không dấu — tất định, không suy đoán.

    "Cơm Sườn Bì Chả" → "com_suon_bi_cha". Dùng để so khớp giữa OCR output,
    từ khoá request và các khóa trong config taxonomy.

    KHÔNG suy đoán: chỉ bỏ dấu thanh, thay ký tự phân cách bằng "_" và loại ký tự
    lạ. Không tự tách từ, không phiên âm, không tra từ điển.
    """
    text = unicodedata.normalize("NFD", (raw or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d")
    text = _DAU_CACH.sub("_", text)
    text = _KY_TU_LA.sub("", text)
    text = _KY_TU_GACH_THUA.sub("_", text)
    return text.strip("_")


def _as_entry_list(raw: Any, section: str) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise SubstituteTaxonomyError(f"{section}: phải là danh sách, nhận {type(raw).__name__}")
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise SubstituteTaxonomyError(f"{section}[{i}]: phải là mapping")
        out.append(item)
    return out


def _as_str_list(raw: Any, where: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise SubstituteTaxonomyError(f"{where}: phải là danh sách chuỗi")
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise SubstituteTaxonomyError(f"{where}: phần tử phải là chuỗi không rỗng, nhận {item!r}")
        out.append(normalize_category_name(item))
    return out


def _as_alias_map(raw: Any, where: str) -> dict[str, tuple[str, ...]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise SubstituteTaxonomyError(f"{where}: alias phải là mapping")
    out: dict[str, tuple[str, ...]] = {}
    for key, values in raw.items():
        norm_key = normalize_category_name(str(key))
        if not norm_key:
            raise SubstituteTaxonomyError(f"{where}: khóa alias rỗng")
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise SubstituteTaxonomyError(f"{where}: alias['{key}'] phải là danh sách chuỗi")
        out[norm_key] = tuple(normalize_category_name(v) for v in values if v.strip())
    return out


def parse_taxonomy(data: Any) -> tuple[SubstituteTaxonomy, dict[str, TaxonomyGroup]]:
    """Hàm THUẦN: dict YAML → (contract `SubstituteTaxonomy`, map nhóm đã nạp).

    Trả về cả contract Pydantic (để validate/serialize) lẫn map tra cứu nhanh.
    Chỉ nạp `entries`; `entries_cho_duyet` bị bỏ qua có chủ đích.
    """
    if not isinstance(data, dict):
        raise SubstituteTaxonomyError("config taxonomy phải là mapping ở gốc")

    raw_entries = _as_entry_list(data.get("entries"), "entries")
    if _PENDING_SECTION in data:
        # Không nạp — chỉ kiểm tra cấu trúc để file không âm thầm sai cú pháp.
        _as_entry_list(data.get(_PENDING_SECTION), _PENDING_SECTION)

    entries: list[SubstituteTaxonomyEntry] = []
    groups: dict[str, TaxonomyGroup] = {}
    seen: set[str] = set()

    for i, raw in enumerate(raw_entries):
        where = f"entries[{i}]"
        jtbd = raw.get("jtbd_group")
        if not isinstance(jtbd, str) or not jtbd.strip():
            raise SubstituteTaxonomyError(f"{where}: thiếu 'jtbd_group' không rỗng")
        key = jtbd.strip()
        if key in seen:
            raise SubstituteTaxonomyError(f"{where}: trùng jtbd_group '{key}'")
        seen.add(key)

        cores = _as_str_list(raw.get("core_categories"), f"{where}.core_categories")
        subs = _as_str_list(raw.get("substitute_categories"), f"{where}.substitute_categories")
        if not cores:
            raise SubstituteTaxonomyError(f"{where}: 'core_categories' không được rỗng")
        if not subs:
            raise SubstituteTaxonomyError(f"{where}: 'substitute_categories' không được rỗng")

        version = raw.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise SubstituteTaxonomyError(f"{where}: 'version' phải là số nguyên >= 1, nhận {version!r}")

        overlap = sorted(set(cores) & set(subs))
        if overlap:
            raise SubstituteTaxonomyError(
                f"{where}: món vừa là core vừa là substitute: {overlap}"
            )

        entry = SubstituteTaxonomyEntry(
            jtbd_group=key,
            core_categories=cores,
            substitute_categories=subs,
            version=version,
        )
        entries.append(entry)

        nhom = raw.get("nhom_lam_tron", "mon_chinh")
        if not isinstance(nhom, str) or not nhom.strip():
            raise SubstituteTaxonomyError(f"{where}: 'nhom_lam_tron' phải là chuỗi không rỗng")
        mo_ta = raw.get("mo_ta", "")
        if not isinstance(mo_ta, str):
            raise SubstituteTaxonomyError(f"{where}: 'mo_ta' phải là chuỗi")

        groups[key] = TaxonomyGroup(
            entry=entry,
            mo_ta=mo_ta.strip(),
            nhom_lam_tron=nhom.strip(),
            alias=_as_alias_map(raw.get("alias"), f"{where}.alias"),
        )

    schema_version = data.get("schema_version", 1)
    if not isinstance(schema_version, int) or isinstance(schema_version, bool) or schema_version < 1:
        raise SubstituteTaxonomyError(
            f"'schema_version' phải là số nguyên >= 1, nhận {schema_version!r}"
        )

    return SubstituteTaxonomy(schema_version=schema_version, entries=entries), groups


def load_taxonomy(path: Path | None = None) -> tuple[SubstituteTaxonomy, dict[str, TaxonomyGroup]]:
    """Đọc `config/substitute-taxonomy.yaml` và parse."""
    cfg = path or TAXONOMY_PATH
    if not cfg.exists():
        raise SubstituteTaxonomyError(f"không tìm thấy file taxonomy: {cfg}")
    data = yaml.safe_load(cfg.read_text(encoding="utf-8"))
    return parse_taxonomy(data)


class SubstituteTaxonomyIndex:
    """Index tra cứu tất định trên taxonomy đã nạp.

    Không cache toàn cục có trạng thái ẩn — caller giữ instance (thường một
    instance cho mỗi lượt khảo sát) để hành vi test được rõ ràng.
    """

    def __init__(
        self,
        taxonomy: SubstituteTaxonomy,
        groups: Mapping[str, TaxonomyGroup],
    ) -> None:
        self._taxonomy = taxonomy
        self._groups: dict[str, TaxonomyGroup] = dict(groups)
        # category (đã normalize) → các nhóm chứa nó ở vai trò core
        self._core_index: dict[str, list[str]] = {}
        # alias (đã normalize) → category chuẩn
        self._alias_index: dict[str, str] = {}
        for key, group in self._groups.items():
            for cat in group.core_categories:
                self._core_index.setdefault(cat, []).append(key)
                self._alias_index.setdefault(cat, cat)
            for cat in group.substitute_categories:
                self._alias_index.setdefault(cat, cat)
            for cat, aliases in group.alias.items():
                self._alias_index.setdefault(cat, cat)
                for alias in aliases:
                    self._alias_index.setdefault(alias, cat)

    @classmethod
    def from_file(cls, path: Path | None = None) -> SubstituteTaxonomyIndex:
        taxonomy, groups = load_taxonomy(path)
        return cls(taxonomy, groups)

    @property
    def taxonomy(self) -> SubstituteTaxonomy:
        return self._taxonomy

    @property
    def groups(self) -> tuple[TaxonomyGroup, ...]:
        return tuple(self._groups.values())

    def group(self, jtbd_group: str) -> TaxonomyGroup | None:
        return self._groups.get(jtbd_group)

    def resolve_category(self, raw_name: str) -> str | None:
        """Ánh xạ tên món thô → category chuẩn trong taxonomy. None nếu không biết.

        KHÔNG suy đoán: tên không có trong config/alias thì trả None, để caller
        xếp vào "mon_khac" thay vì gán nhầm nhóm (ADR-002).
        """
        norm = normalize_category_name(raw_name)
        if not norm:
            return None
        return self._alias_index.get(norm)

    def groups_for_core(self, core_category: str) -> tuple[TaxonomyGroup, ...]:
        """Các nhóm JTBD mà `core_category` là món lõi."""
        norm = normalize_category_name(core_category)
        return tuple(self._groups[k] for k in self._core_index.get(norm, ()))

    def substitute_categories(self, core_category: str) -> tuple[str, ...]:
        """Danh sách nhóm thay thế cho món lõi (plan mục 1.2).

        Nhiều nhóm khớp → hợp nhất, giữ thứ tự xuất hiện trong config, khử trùng.
        """
        out: list[str] = []
        seen: set[str] = set()
        for group in self.groups_for_core(core_category):
            for cat in group.substitute_categories:
                if cat not in seen:
                    seen.add(cat)
                    out.append(cat)
        return tuple(out)

    def rounding_group(self, core_category: str) -> str:
        """Nhóm làm tròn hiển thị cho món lõi (plan mục 1.5.7).

        Không khớp nhóm nào → "mon_chinh" (bội số 5.000đ, an toàn hơn 1.000đ).
        """
        groups = self.groups_for_core(core_category)
        if not groups:
            return "mon_chinh"
        return groups[0].nhom_lam_tron

    def all_categories(self) -> tuple[str, ...]:
        """Toàn bộ category đã khai báo (core + substitute + alias), đã khử trùng.

        Nhiều alias có thể trỏ về cùng một category → phải khử trùng, nếu không
        caller đếm sai số nhóm món khi tính AMBI.
        """
        return tuple(sorted(set(self._alias_index.values())))

    def versions(self) -> dict[str, int]:
        """Version từng nhóm — dùng cho observability (plan mục 9)."""
        return {key: group.version for key, group in self._groups.items()}


def union_core_and_substitutes(
    core_prices: Sequence[float],
    substitute_prices_by_category: Mapping[str, Sequence[float]],
    *,
    include_categories: Iterable[str] | None = None,
) -> list[float]:
    """Gộp rổ giá Core ∪ Substitutes cho Sweet Spot (plan mục 4.4).

    `include_categories=None` → lấy tất cả nhóm thay thế có dữ liệu.
    Ngược lại chỉ lấy các nhóm được liệt kê (đã lọc cùng `positioning_tier`
    ở tầng gọi — plan mục 1.5.3).

    Thứ tự kết quả tất định: core trước, rồi substitute theo thứ tự khóa đã sort.
    """
    out: list[float] = [float(p) for p in core_prices]
    wanted = None if include_categories is None else {str(c) for c in include_categories}
    for cat in sorted(substitute_prices_by_category):
        if wanted is not None and cat not in wanted:
            continue
        out.extend(float(p) for p in substitute_prices_by_category[cat])
    return out
