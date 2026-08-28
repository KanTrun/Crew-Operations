"""AG-SOP — trả lời câu hỏi nghiệp vụ từ phiếu quy trình và luật hiệu lực."""

from __future__ import annotations

from ca_agents.ag_sop import SopAnswer, answer


def test_answer_matches_buoc_by_keyword() -> None:
    """Bước quy trình khớp từ khóa trong câu hỏi trả về đúng nội dung và trích dẫn phiếu."""
    buoc = [{"ma": "B01", "ten": "Kiểm tra nhiệt độ tủ đông"}]
    luat: list[dict] = []
    res = answer("Làm thế nào để kiểm tra nhiệt độ?", buoc=buoc, luat=luat)
    assert isinstance(res, SopAnswer)
    assert not res.chua_co
    assert "Kiểm tra nhiệt độ tủ đông" in res.cau_tra_loi
    assert res.trich_dan == ["phieu:B01"]


def test_answer_includes_nguong_in_response() -> None:
    """Bước quy trình có khai báo ngưỡng trả về kèm thông tin khoảng ngưỡng min-max."""
    buoc = [
        {
            "ma": "B02",
            "ten": "Bảo quản sữa chua",
            "nguong": {"min": 2, "max": 8},
        }
    ]
    luat: list[dict] = []
    res = answer("Bảo quản sữa chua như thế nào?", buoc=buoc, luat=luat)
    assert not res.chua_co
    assert "(ngưỡng 2–8)" in res.cau_tra_loi
    assert "phieu:B02" in res.trich_dan


def test_answer_matches_law_hieu_luc() -> None:
    """Luật có hiệu lực khớp từ khóa được trích dẫn và đưa vào câu trả lời."""
    buoc: list[dict] = []
    luat = [
        {
            "id": "L01",
            "trang_thai": "hieu_luc",
            "cau": "Nhân viên phải mặc đúng đồng phục khi vào ca làm việc.",
        }
    ]
    res = answer("Quy định đồng phục nhân viên", buoc=buoc, luat=luat)
    assert not res.chua_co
    assert "Nhân viên phải mặc đúng đồng phục khi vào ca làm việc." in res.cau_tra_loi
    assert res.trich_dan == ["luat:L01"]


def test_answer_ignores_inactive_law() -> None:
    """Luật ở trạng thái chờ duyệt (cho_duyet) bị bỏ qua, không được trích dẫn."""
    buoc: list[dict] = []
    luat = [
        {
            "id": "L02",
            "trang_thai": "cho_duyet",
            "cau": "Nhân viên phải đeo khẩu trang trong suốt ca làm.",
        }
    ]
    res = answer("Quy định đeo khẩu trang cho nhân viên", buoc=buoc, luat=luat)
    assert res.chua_co is True
    assert res.trich_dan == []
    assert "Chưa có trong cẩm nang của quán" in res.cau_tra_loi


def test_answer_unknown_question() -> None:
    """Câu hỏi không khớp với bất kỳ bước hay luật nào trả về thông báo chưa có."""
    buoc = [{"ma": "B01", "ten": "Pha chế cà phê đen"}]
    luat = [
        {
            "id": "L01",
            "trang_thai": "hieu_luc",
            "cau": "Rửa tay trước khi pha chế đồ uống.",
        }
    ]
    res = answer("Thời gian mở cửa quán vào ngày lễ?", buoc=buoc, luat=luat)
    assert res.chua_co is True
    assert res.trich_dan == []
    assert "Chưa có trong cẩm nang của quán, hãy hỏi quản lý." in res.cau_tra_loi


def test_answer_deduplicates_citations() -> None:
    """Trích dẫn trùng lặp từ nhiều nhánh khớp chỉ xuất hiện một lần duy nhất."""
    buoc = [{"ma": "B01", "ten": "Kiểm tra nhiệt độ máy làm đá"}]
    luat: list[dict] = []
    res = answer("Kiểm tra nhiệt độ máy làm đá", buoc=buoc, luat=luat)
    assert not res.chua_co
    assert res.trich_dan == ["phieu:B01"]
    assert len(res.trich_dan) == 1


def test_answer_empty_sources() -> None:
    """Nguồn dữ liệu bước và luật đều rỗng trả về trạng thái chưa có."""
    res = answer("Quy trình phục vụ bàn ca sáng", buoc=[], luat=[])
    assert res.chua_co is True
    assert res.trich_dan == []
    assert res.cau_tra_loi == "Chưa có trong cẩm nang của quán, hãy hỏi quản lý."


def test_answer_tu_lanh_keyword() -> None:
    """Câu hỏi chứa cụm từ 'tủ lạnh' khớp chính xác bước có tên tủ lạnh."""
    buoc = [{"ma": "B05", "ten": "Vệ sinh tủ lạnh định kỳ hàng tuần"}]
    luat: list[dict] = []
    res = answer("Hướng dẫn vệ sinh tủ lạnh", buoc=buoc, luat=luat)
    assert not res.chua_co
    assert "Vệ sinh tủ lạnh định kỳ hàng tuần" in res.cau_tra_loi
    assert res.trich_dan == ["phieu:B05"]
