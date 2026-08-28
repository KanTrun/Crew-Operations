# ADR-005 — Sổ nợ công bằng 4 chiều, tối thiểu hoá nợ lớn nhất

- Status: accepted
- Date: 2026-08-22

## Context

Công bằng không phải cảm giác. Hồ sơ §8.2: bốn chiều ca cuối tuần, đêm, tổng giờ, ca vụn.

## Decision

Mỗi NV có số dư nợ 4 chiều tích luỹ. Objective CP-SAT **minimize max debt** (không minimize tổng). ADR-006 trong hồ sơ cùng tinh thần — ghi tại đây cho repo.

## Consequences

Property test 8 tuần: khoảng cách nợ không được phình vô hạn. Bảng UI không xếp hạng tên.
