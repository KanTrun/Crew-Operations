# Thư viện Kỹ năng NHỊP QUÁN (Agent Skills Library)

Thư viện kỹ năng được chưng cất theo phương pháp **Repo-To-Skill** và **Playbook-To-Skill**, tuân thủ quy chuẩn quốc tế [Agent Skills Format](https://github.com/agentskills/agentskills) và kiến trúc [DisCo / AREX-Skill](https://github.com/VectorSpaceLab/AREX-Skill).

Mỗi kỹ năng đại diện cho một gói tri thức vận hành thực tế (**Operational Knowledge**) độc lập, có thể kiểm chứng offline và tái sử dụng bởi **AG-COPILOT** cùng toàn bộ 10 Agent chuyên trách mà không cần nạp toàn bộ mã nguồn repo vào context.

## Cấu trúc chuẩn của một Skill

```text
skill/
├── SKILL.md       # Định nghĩa phạm vi, điều kiện kích hoạt, luồng xử lý và cổng an toàn
├── references/    # Tài liệu nghiệp vụ chi tiết, bảng mã lỗi, quy tắc ràng buộc
└── scripts/       # Mã thực thi Python kiểm thử offline, smoke checks, validator
```

## Danh mục 13 Kỹ năng Hoàn chỉnh (100% Verified)

| Kỹ năng | Vị trí thư mục | Nguồn mã nguồn | Nghiệp vụ cốt lõi |
|---|---|---|---|
| **Skill Router** | `skills/repositories/repo-skills-router/` | Toàn hệ thống | Điều hướng tăng dần (Progressive Disclosure) giữ context $\le$ 1.500 tokens |
| **Solver Scheduling** | `skills/repositories/repo-skills/solver-scheduling/` | `packages/solver` | Xếp ca CP-SAT, kiểm tra 6 ràng buộc cứng C01–C06 |
| **Smart Swap Recommender** | `skills/repositories/repo-skills/smart-swap-recommender/` | `ca_agents/smart_swap.py` | Đề xuất ứng viên thế ca tối ưu khi có người vắng mặt |
| **VF Gates Audit** | `skills/repositories/repo-skills/vf-gates-audit/` | `packages/gates` | Kiểm tra an toàn fail-closed (VF-SCHEMA, VF-TRACE, VF-CONF) |
| **SOP Execution** | `skills/repositories/repo-skills/sop-execution/` | `packages/playbook` | Chuyển đổi cẩm nang thành checklist mở/đóng ca có thể xác minh |
| **Rule Mining Lifecycle** | `skills/repositories/repo-skills/rule-mining-lifecycle/` | `packages/playbook` + `AG-RULE` | Khai phá lỗi lặp lại ($\ge 3$ lần) để tự đề xuất luật cẩm nang 8 bước |
| **Barista Waste Audit** | `skills/repositories/repo-skills/barista-waste-audit/` | `opsengine` + `AG-BARISTA` + `AG-WASTE` | Kiểm tra định mức công thức pha chế và tính toán tỷ lệ hao hụt |
| **Inventory Restock Check** | `skills/repositories/repo-skills/inventory-restock-check/` | `packages/opsengine` | Cảnh báo tồn kho cạn và kiểm tra điểm đặt hàng lại (ROP) |
| **Handover Reconciliation**| `skills/repositories/repo-skills/handover-reconciliation/`| `opsengine` + `AG-HANDOVER` | Bàn giao ca làm việc & đối soát cân bằng tiền két thu ngân |
| **Daily Brief Generator** | `skills/repositories/repo-skills/daily-brief-generator/` | `ca_agents/ag_brief/` | Tự động tạo bản tin giao ban ca sáng/chiều |
| **Meeting Memo Extractor** | `skills/repositories/repo-skills/meeting-memo-extractor/` | `ca_agents/ag_meeting/` | Bóc tách biên bản họp ca thành danh sách việc cần làm có hạn chót |
| **Customer Memory & VOC** | `skills/repositories/repo-skills/customer-memory-voc/` | `customer_memory.py` + `ag_voc/` | Ghi nhớ sở thích khách quen và phân loại đánh giá khen/chê |
| **Fanpage & Concierge** | `skills/repositories/repo-skills/fbpage-concierge/` | `ag_fbpage.py` + `ag_concierge.py` | Trực tin nhắn Facebook/Zalo, báo giá menu và kiểm tra bàn trống |
| **Mailwriter Notification**| `skills/repositories/repo-skills/mailwriter-notification/`| `ag_mailwriter/` + `ag_mail.py` | Soạn thảo email điều hành gửi nhà cung cấp hoặc thông báo nội bộ |
