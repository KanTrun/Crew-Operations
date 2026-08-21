# ADR-004 — CP-SAT cho xếp ca

- Status: accepted
- Date: 2026-08-22

## Context

Xếp ca 25 người × 21 ca với 6 ràng buộc cứng là bài toán tối ưu tổ hợp. LLM không được ghi lịch (ADR-002).

## Decision

Dùng Google OR-Tools CP-SAT trong `packages/solver` (`solve_cpsat`). Ràng buộc cứng là constraint; mềm và sổ nợ là objective.

## Consequences

Phụ thuộc `ortools`. Solve có `max_time_in_seconds=60` — trả nghiệm tốt nhất khi hết giờ.
