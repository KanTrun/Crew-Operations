"""AG-EXPLAIN — Causal Memory: nối sự kiện/quyết định/luật/kết quả thành chuỗi nhân quả.

Nguồn: `plans/260918-y-tuong-dot-pha-nho.md` mục 3.

ADR-002: câu trả lời "tại sao" dựng từ dữ liệu thật (audit trace, playbook, solver)
— không LLM, không bịa. Độ chính xác 100% từ dữ liệu.

ADR-008: causal memory chỉ ĐỌC và giải thích, không thay đổi gì.
"""

from __future__ import annotations

from typing import Any

from ca_contracts.causal_memory import (
    CausalChain,
    CausalLink,
    CausalNode,
    CausalNodeType,
)


def _find_luat_nodes(luat: dict[str, Any]) -> list[CausalNode]:
    """Trích nút luật từ một luật trong playbook."""
    nodes: list[CausalNode] = []
    luat_id = str(luat.get("id") or "")
    if not luat_id:
        return nodes
    nodes.append(
        CausalNode(
            node_id=f"luat_{luat_id}",
            loai=CausalNodeType.LUAT,
            mo_ta=str(luat.get("cau") or luat_id),
            thoi_gian=str(luat.get("last_modified_at") or ""),
            nguon="playbook",
        )
    )
    # Bằng chứng (các lần sửa) → nút sự kiện
    for i, bc in enumerate(luat.get("bang_chung") or []):
        nodes.append(
            CausalNode(
                node_id=f"su_kien_{luat_id}_{i}",
                loai=CausalNodeType.SU_KIEN,
                mo_ta=f"Bằng chứng: {bc}",
                nguon="playbook",
            )
        )
    return nodes


def _find_audit_nodes(audit: dict[str, Any]) -> list[CausalNode]:
    """Trích nút quyết định từ một vết audit."""
    nodes: list[CausalNode] = []
    entity_id = str(audit.get("entity_id") or "")
    if not entity_id:
        return nodes
    nodes.append(
        CausalNode(
            node_id=f"quyet_dinh_{entity_id}",
            loai=CausalNodeType.QUYET_DINH,
            mo_ta=f"{audit.get('hanh_dong') or audit.get('action') or 'quyết định'} bởi {audit.get('actor') or '?'}",
            thoi_gian=str(audit.get("luc") or audit.get("at") or ""),
            nguon="audit",
        )
    )
    return nodes


def build_causal_chain(
    cau_hoi: str,
    luat_list: list[dict[str, Any]],
    audit_list: list[dict[str, Any]],
    ket_qua_list: list[dict[str, Any]] | None = None,
) -> CausalChain:
    """Dựng chuỗi nhân quả cho câu hỏi "tại sao" (tất định).

    Nối: sự kiện → luật → quyết định → kết quả.
    """
    nodes: list[CausalNode] = []
    links: list[CausalLink] = []
    _seen_nodes: set[str] = set()
    _seen_links: set[tuple[str, str, str]] = set()

    def _add_node(n: CausalNode) -> bool:
        """Thêm node nếu chưa có (dedupe theo node_id). Trả True nếu node mới."""
        if n.node_id in _seen_nodes:
            return False
        _seen_nodes.add(n.node_id)
        nodes.append(n)
        return True

    def _add_link(link: CausalLink) -> None:
        key = (link.from_id, link.to_id, link.ly_do)
        if key in _seen_links:
            return
        _seen_links.add(key)
        links.append(link)

    # 1. Nút luật + sự kiện bằng chứng
    for luat in luat_list:
        luat_nodes = _find_luat_nodes(luat)
        if not luat_nodes:
            continue
        luat_node = luat_nodes[0]
        if not _add_node(luat_node):
            # Luật đã có trong chuỗi — bỏ qua để không lặp bằng chứng.
            continue
        # Liên kết sự kiện → luật
        for n in luat_nodes[1:]:
            _add_node(n)
            _add_link(CausalLink(from_id=n.node_id, to_id=luat_node.node_id, ly_do="bằng chứng"))

    # 2. Nút quyết định từ audit
    for audit in audit_list:
        audit_nodes = _find_audit_nodes(audit)
        for n in audit_nodes:
            if not _add_node(n):
                continue
            # Liên kết luật → quyết định (nếu có luật)
            if nodes:
                luat_nodes_found = [x for x in nodes if x.loai == CausalNodeType.LUAT]
                if luat_nodes_found:
                    _add_link(
                        CausalLink(
                            from_id=luat_nodes_found[-1].node_id,
                            to_id=n.node_id,
                            ly_do="được duyệt",
                        )
                    )

    # 3. Nút kết quả
    for i, kq in enumerate(ket_qua_list or []):
        kq_node = CausalNode(
            node_id=f"ket_qua_{i}",
            loai=CausalNodeType.KET_QUA,
            mo_ta=str(kq.get("mo_ta") or str(kq)),
            nguon="solver",
        )
        if not _add_node(kq_node):
            continue
        # Liên kết quyết định → kết quả
        quyet_dinh_nodes = [x for x in nodes if x.loai == CausalNodeType.QUYET_DINH]
        if quyet_dinh_nodes:
            _add_link(
                CausalLink(
                    from_id=quyet_dinh_nodes[-1].node_id,
                    to_id=kq_node.node_id,
                    ly_do="kết quả",
                )
            )

    # Kết luận tất định
    ket_luan = _build_ket_luan(nodes, links)

    return CausalChain(
        chain_id=f"chain_{abs(hash(cau_hoi)) % 100000}",
        cau_hoi=cau_hoi,
        nodes=nodes,
        links=links,
        ket_luan=ket_luan,
    )


def _build_ket_luan(nodes: list[CausalNode], links: list[CausalLink]) -> str:
    """Dựng câu kết luận tất định từ chuỗi nhân quả."""
    luat_nodes = [n for n in nodes if n.loai == CausalNodeType.LUAT]
    quyet_dinh_nodes = [n for n in nodes if n.loai == CausalNodeType.QUYET_DINH]
    ket_qua_nodes = [n for n in nodes if n.loai == CausalNodeType.KET_QUA]

    parts: list[str] = []
    if luat_nodes:
        parts.append(f"Luật {luat_nodes[0].mo_ta}")
    if quyet_dinh_nodes:
        parts.append(f"được {quyet_dinh_nodes[0].mo_ta}")
    if ket_qua_nodes:
        parts.append(f"kết quả: {ket_qua_nodes[0].mo_ta}")
    if not parts:
        return "Không tìm thấy chuỗi nhân quả cho câu hỏi này."
    return " → ".join(parts) + "."