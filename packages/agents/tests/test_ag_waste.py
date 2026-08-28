from __future__ import annotations

from ca_agents.ag_waste.extract import WasteHint, cluster


def test_cluster_empty() -> None:
    """Danh sách ghi chú rỗng trả về danh sách rỗng."""
    assert cluster([]) == []


def test_cluster_no_keyword_match() -> None:
    """Ghi chú không chứa từ khóa dư/hết/hao sẽ bị bỏ qua và trả về danh sách rỗng."""
    notes = [
        ("T2", "quán đông khách"),
        ("T2", "máy pha cà phê hoạt động tốt"),
        ("T3", "nhân viên đi làm đúng giờ"),
    ]
    assert cluster(notes) == []


def test_cluster_single_occurrence_ignored() -> None:
    """Từ khóa chỉ xuất hiện 1 lần trong ngày không đủ điều kiện (cần >= 2) nên trả về rỗng."""
    notes = [("T2", "dư 2 ly trà"), ("T3", "hết đá")]
    assert cluster(notes) == []


def test_cluster_two_occurrences() -> None:
    """Từ khóa xuất hiện 2 lần trong thứ Hai trả về 1 gợi ý WasteHint tương ứng."""
    notes = [("T2", "dư 2 ly"), ("T2", "hết sữa tươi")]
    hints = cluster(notes)
    assert len(hints) == 1
    assert isinstance(hints[0], WasteHint)
    assert hints[0].thu == "T2"
    assert hints[0].n == 2


def test_cluster_sorted_by_frequency() -> None:
    """Kết quả gom nhóm được sắp xếp giảm dần theo tần suất xuất hiện (T7 có 3 lần xếp trước T2 có 2 lần)."""
    notes = [
        ("T2", "dư sữa"),
        ("T2", "hết trà"),
        ("T7", "hao hụt đá"),
        ("T7", "dư bánh mì"),
        ("T7", "hết siro"),
    ]
    hints = cluster(notes)
    assert len(hints) == 2
    assert hints[0].thu == "T7"
    assert hints[0].n == 3
    assert hints[1].thu == "T2"
    assert hints[1].n == 2


def test_cluster_cau_text_format() -> None:
    """Trường cau chứa đúng tên thứ của ngày có hao hụt lặp lại."""
    notes = [("T5", "hao hụt nguyên liệu"), ("T5", "hết sữa đặc")]
    hints = cluster(notes)
    assert len(hints) == 1
    assert "T5" in hints[0].cau
    assert hints[0].cau == "Hao hụt lặp lại vào T5 — xem lại nhập hàng ngày đó"


def test_cluster_loai_default() -> None:
    """Trường loai của WasteHint mặc định là 'hao_hut'."""
    notes = [("T3", "dư đường"), ("T3", "hết sữa")]
    hints = cluster(notes)
    assert len(hints) == 1
    assert hints[0].loai == "hao_hut"
