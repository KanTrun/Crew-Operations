"""Kiểm tra KV store: golden memory + customer profile + threads — tìm nguồn 'trả lời theo mẫu'."""

from __future__ import annotations

import sys

sys.stdout.reconfigure(encoding="utf-8")

from ca_api.persist import kv_get  # noqa: E402

print("=== cskh_golden_memory (bài học mẫu QL đã dạy — nếu có, bot trả lời NGUYÊN VĂN, bỏ LLM) ===")
goldens = kv_get("cskh_golden_memory:quan_01", [])
print(f"Số lượng: {len(goldens)}")
for g in goldens[:10]:
    print(f"  intent={g.get('intent')} reply={str(g.get('manager_reply'))[:100]!r}")

print()
print("=== page_quan threads (hội thoại đã xử lý) ===")
page = kv_get("page_quan", {}) or {}
threads = page.get("threads", [])
print(f"Số threads: {len(threads)}")
for t in threads[:5]:
    print(f"  psid={t.get('psid')} intent={t.get('intent')} conf={t.get('confidence')} pending={t.get('pending_approval')}")
    print(f"    suggested={str(t.get('suggested_reply'))[:120]!r}")
    replies = t.get("replies", [])
    for r in replies[-2:]:
        print(f"    reply by={r.get('by')}: {str(r.get('text'))[:120]!r}")

print()
print("=== AI learning rules (quy tắc chủ quán duyệt) ===")
try:
    from ca_api.persist import get_conn
    with get_conn() as conn:
        rows = conn.execute("SELECT id, channel, status, rule FROM ai_learning_rule LIMIT 10").fetchall()
        print(f"Số rules: {len(rows)}")
        for row in rows:
            print(f"  id={row[0]} channel={row[1]} status={row[2]}")
            print(f"    rule={str(row[3])[:150]!r}")
except Exception as exc:  # noqa: BLE001
    print(f"  (không đọc được: {exc})")
