"""War Room evidence — mỗi con số output phải trỏ tới input/thuật toán/solver."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvidenceRef:
    """Một bằng chứng: loại + nguồn + thông tin.

    - `loai` ∈ {input_row, deterministic_fn, solver_result}
    - `value` giá trị gốc (để trace)
    - `note` giải thích ngắn gọn
    """

    loai: str
    nguon: str
    value: str = ""
    note: str = ""


@dataclass
class EvidenceBuilder:
    """Tích luỹ evidence cho một option — không cho phép số không nguồn."""

    refs: list[EvidenceRef] = field(default_factory=list)

    def add_input_row(self, nguon: str, value: Any, note: str = "") -> None:
        self.refs.append(EvidenceRef("input_row", nguon, str(value), note))

    def add_deterministic(self, nguon: str, value: Any, note: str = "") -> None:
        self.refs.append(EvidenceRef("deterministic_fn", nguon, str(value), note))

    def add_solver(self, nguon: str, value: Any, note: str = "") -> None:
        self.refs.append(EvidenceRef("solver_result", nguon, str(value), note))

    def to_dicts(self) -> list[dict[str, str]]:
        return [
            {"loai": r.loai, "nguon": r.nguon, "value": r.value, "note": r.note}
            for r in self.refs
        ]