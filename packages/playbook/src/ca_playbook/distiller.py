"""Module chưng cất Cẩm nang (Playbook & SOP) thành Kỹ năng Thực thi (Playbook-To-Skill).

Chuyển đổi các tài liệu quy trình dạng văn bản/markdown thành cấu trúc
kỹ năng chuẩn có thể tự động kiểm tra và thực thi.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def parse_sop_markdown(content: str) -> dict[str, Any]:
    """Phân tích văn bản SOP dạng Markdown thành cấu trúc dữ liệu máy đọc được."""
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Quy trình không tên"

    # Trích xuất các bước dạng gạch đầu dòng hoặc đánh số
    steps: list[str] = []
    lines = content.splitlines()
    in_steps_section = False

    for line in lines:
        stripped = line.strip()
        if re.search(r"^##\s+.*(bước|checklist|quy trình|thực hiện)", stripped, re.IGNORECASE):
            in_steps_section = True
            continue
        elif stripped.startswith("## ") and in_steps_section:
            in_steps_section = False

        if in_steps_section:
            step_match = re.match(r"^(\d+\.|\-|\*)\s+(.+)$", stripped)
            if step_match:
                steps.append(step_match.group(2).strip())

    # Nếu không tìm thấy header riêng, gom tất cả các dòng list
    if not steps:
        for line in lines:
            step_match = re.match(r"^(\d+\.|\-|\*)\s+(.+)$", line.strip())
            if step_match:
                steps.append(step_match.group(2).strip())

    return {
        "title": title,
        "raw_length": len(content),
        "steps": steps,
        "step_count": len(steps),
    }


def generate_skill_content(sop_id: str, title: str, steps: list[str]) -> str:
    """Tạo nội dung file SKILL.md từ SOP đã phân tích."""
    steps_md = "\n".join(f"{i+1}. `{s}`" for i, s in enumerate(steps))
    return f"""---
name: {sop_id}
description: "Kỹ năng thực thi quy trình: {title}"
disable-model-invocation: true
metadata:
  role: operating
  distilled-from: playbook
---

# {title}

Kỹ năng được chưng cất tự động từ cẩm nang vận hành NHỊP QUÁN.

## Các bước bắt buộc

{steps_md}

## Hướng dẫn thực thi

1. Xác nhận các bước nhân viên đã báo cáo hoàn thành.
2. Đối chiếu với danh sách các bước bắt buộc ở trên.
3. Nhắc nhở các bước còn thiếu trước khi xác nhận hoàn tất quy trình.
"""


def distill_sop_to_dir(sop_id: str, content: str, target_dir: Path) -> dict[str, Any]:
    """Chưng cất SOP thành một thư mục skill hoàn chỉnh."""
    parsed = parse_sop_markdown(content)
    target_dir.mkdir(parents=True, exist_ok=True)

    skill_file = target_dir / "SKILL.md"
    skill_content = generate_skill_content(sop_id, parsed["title"], parsed["steps"])
    skill_file.write_text(skill_content, encoding="utf-8")

    return {
        "sop_id": sop_id,
        "title": parsed["title"],
        "steps_count": parsed["step_count"],
        "skill_path": str(skill_file),
    }
