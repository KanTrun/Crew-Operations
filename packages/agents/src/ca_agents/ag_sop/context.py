"""Load phiếu YAML steps for AG-SOP context."""

from __future__ import annotations

from typing import Any

from ca_ops.engine import load_template

_TEMPLATE_MA = ("mo_quan", "ban_giao_ca", "dong_quan")


def load_all_buoc() -> list[dict[str, Any]]:
    """Merge steps from all SOP templates with phiếu metadata."""
    out: list[dict[str, Any]] = []
    for tpl_ma in _TEMPLATE_MA:
        tpl = load_template(tpl_ma)
        phieu_ten = str(tpl.get("ten") or tpl_ma)
        for b in tpl.get("buoc") or []:
            row = dict(b)
            row["phieu"] = tpl_ma
            row["phieu_ten"] = phieu_ten
            out.append(row)
    return out
