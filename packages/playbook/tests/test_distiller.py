from pathlib import Path

from ca_playbook.distiller import (
    distill_sop_to_dir,
    generate_skill_content,
    parse_sop_markdown,
)


def test_parse_sop_markdown() -> None:
    content = """# Quy trình mở ca sáng

## Mục đích
Đảm bảo quán sẵn sàng phục vụ khách trước 07:00.

## Các bước thực hiện
1. Kiểm tra nguồn điện nước và aptomat
2. Bật máy pha cà phê trước 30 phút để đủ nhiệt
3. Đếm tiền lẻ đầu ca và đối soát két
4. Kiểm tra hạn sử dụng sữa và siro
5. Đăng nhập hệ thống POS
"""
    parsed = parse_sop_markdown(content)
    assert parsed["title"] == "Quy trình mở ca sáng"
    assert parsed["step_count"] == 5
    assert "Kiểm tra nguồn điện nước và aptomat" in parsed["steps"][0]
    assert "Đăng nhập hệ thống POS" in parsed["steps"][4]


def test_generate_skill_content() -> None:
    steps = ["Bật máy pha", "Kiểm kho sữa", "Mở két"]
    content = generate_skill_content("sop-mo-ca", "Quy trình mở ca", steps)
    assert "name: sop-mo-ca" in content
    assert "disable-model-invocation: true" in content
    assert "1. `Bật máy pha`" in content


def test_distill_sop_to_dir(tmp_path: Path) -> None:
    content = """# Vệ sinh máy pha cuối ngày
1. Xả bã cà phê trong họng pha
2. Dùng bột vệ sinh chuyên dụng chạy chu trình backflush
3. Tháo ngâm vòi đánh sữa qua đêm
"""
    out_dir = tmp_path / "sop-ve-sinh-may"
    res = distill_sop_to_dir("sop-ve-sinh-may", content, out_dir)

    assert res["sop_id"] == "sop-ve-sinh-may"
    assert res["steps_count"] == 3
    assert (out_dir / "SKILL.md").exists()
    assert "Vệ sinh máy pha cuối ngày" in (out_dir / "SKILL.md").read_text(encoding="utf-8")
