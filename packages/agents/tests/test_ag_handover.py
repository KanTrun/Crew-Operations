"""AG-HANDOVER — trích xuất văn bản bàn giao ca SBAR và việc treo."""

from __future__ import annotations

from ca_agents.ag_handover import Handover, extract


def test_extract_full_sbar_with_treo() -> None:
    """Trích xuất đầy đủ văn bản SBAR với tiêu đề S, B, A, R và 2 việc treo."""
    text = (
        "S: Khách đông ca trưa, hết đá 2 lần\n"
        "B: Thời tiết nóng, tủ làm đá bị chậm\n"
        "A: Cần tăng tốc độ làm đá hoặc mua thêm đá ngoài\n"
        "R: Ca chiều theo dõi tủ đá và bổ sung đá kịp thời\n"
        "Việc treo: Gọi thợ bảo trì tủ đá\n"
        "Việc treo: Kiểm tra hóa đơn mua đá ngoài"
    )
    res = extract(text)
    assert isinstance(res, Handover)
    assert res.tinh_hinh == "Khách đông ca trưa, hết đá 2 lần"
    assert res.boi_canh == "Thời tiết nóng, tủ làm đá bị chậm"
    assert res.danh_gia == "Cần tăng tốc độ làm đá hoặc mua thêm đá ngoài"
    assert res.de_nghi == "Ca chiều theo dõi tủ đá và bổ sung đá kịp thời"
    assert res.treo == ["Gọi thợ bảo trì tủ đá", "Kiểm tra hóa đơn mua đá ngoài"]
    assert res.do_tin_cay == 0.82
    assert res.nguon == "keyword"


def test_extract_vietnamese_headers() -> None:
    """Trích xuất với tiêu đề tiếng Việt đầy đủ (Tình hình, Bối cảnh, Đánh giá, Đề nghị)."""
    text = (
        "Tình hình: Doanh thu ca sáng đạt 5 triệu\n"
        "Bối cảnh: Khai trương món mới\n"
        "Đánh giá: Khách phản hồi tốt về món mới\n"
        "Đề nghị: Chuẩn bị thêm nguyên liệu cho ca tối"
    )
    res = extract(text)
    assert res.tinh_hinh == "Doanh thu ca sáng đạt 5 triệu"
    assert res.boi_canh == "Khai trương món mới"
    assert res.danh_gia == "Khách phản hồi tốt về món mới"
    assert res.de_nghi == "Chuẩn bị thêm nguyên liệu cho ca tối"
    assert res.treo == []
    assert res.do_tin_cay == 0.82


def test_extract_unstructured_fallback() -> None:
    """Văn bản không có các mục SBAR trả về độ tin cậy 0.55 và bối cảnh chứa 'chưa tách được'."""
    text = "Việc treo: Kiểm tra hóa đơn tồn ca trước"
    res = extract(text)
    assert res.do_tin_cay == 0.55
    assert "chưa tách được" in res.boi_canh
    assert res.danh_gia == "chưa tách được"
    assert res.de_nghi == "hỏi ca sau xác nhận từng việc treo"
    assert res.treo == []


def test_extract_empty_string() -> None:
    """Chuỗi rỗng trả về fallback độ tin cậy 0.55 và danh sách treo rỗng."""
    res = extract("")
    assert res.do_tin_cay == 0.55
    assert res.treo == []
    assert "chưa tách được" in res.boi_canh
    assert res.danh_gia == "chưa tách được"
    assert res.de_nghi == "hỏi ca sau xác nhận từng việc treo"


def test_extract_multiple_treo_items() -> None:
    """Kiểm tra nhiều việc treo tồn đọng được thu thập đầy đủ."""
    text = (
        "S: Bàn giao ca sáng sang ca chiều\n"
        "B: Cuối tuần đông khách\n"
        "A: Hoạt động bình thường\n"
        "R: Tiếp tục duy trì chuẩn bị nguyên liệu\n"
        "Việc treo: Gọi đổi bình gas số 2\n"
        "treo: Nhập hóa đơn VAT cho khách bàn 4\n"
        "viec treo: Kiểm tra hạn sử dụng sữa đặc trong kho"
    )
    res = extract(text)
    assert res.treo == [
        "Gọi đổi bình gas số 2",
        "Nhập hóa đơn VAT cho khách bàn 4",
        "Kiểm tra hạn sử dụng sữa đặc trong kho",
    ]


def test_extract_windows_line_endings() -> None:
    """Văn bản có ký tự xuống dòng kiểu Windows (\\r\\n) vẫn trích xuất chính xác."""
    text = (
        "S: Máy POS quầy bar bị mất kết nối\r\n"
        "B: Mạng chập chờn từ sáng\r\n"
        "A: Cần khởi động lại thiết bị mạng\r\n"
        "R: Đã liên hệ bên kỹ thuật hỗ trợ\r\n"
        "Việc treo: Theo dõi tình trạng máy POS ca chiều\r\n"
    )
    res = extract(text)
    assert res.tinh_hinh == "Máy POS quầy bar bị mất kết nối"
    assert res.boi_canh == "Mạng chập chờn từ sáng"
    assert res.danh_gia == "Cần khởi động lại thiết bị mạng"
    assert res.de_nghi == "Đã liên hệ bên kỹ thuật hỗ trợ"
    assert res.treo == ["Theo dõi tình trạng máy POS ca chiều"]


def test_extract_missing_sections_filled_with_trong() -> None:
    """Khi chỉ có S và R, các trường bối cảnh và đánh giá được điền là (trống)."""
    text = "S: Khách đông ca trưa\nR: Ca chiều chuẩn bị thêm đá và ly sạch"
    res = extract(text)
    assert res.tinh_hinh == "Khách đông ca trưa"
    assert res.boi_canh == "(trống)"
    assert res.danh_gia == "(trống)"
    assert res.de_nghi == "Ca chiều chuẩn bị thêm đá và ly sạch"
    assert res.treo == []
