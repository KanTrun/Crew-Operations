#!/usr/bin/env python3
"""Eval AG-FBPAGE moderation pipeline (5 lớp cổng) trên golden fixtures.

Replay mode: classifier + supervisor đều tất định → kết quả lặp lại được.
Tính pass rate, fail rate, confusion matrix action x intent. Fail 1 case
escalate_owner hoặc block_* nào cũng là RED (kế hoạch §5.2 / §6.4).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "contracts" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "agents" / "src"))
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

# Replay để router LLM không can thiệp; classifier ag_msg dùng replay.
os.environ.setdefault("CA_AGENT_MODE", "replay")
os.environ.setdefault("NHIPQUAN_PAGE_MODE", "live")
os.environ.setdefault("NHIPQUAN_FB_PAGE_TOKEN", "tok_eval")
os.environ.setdefault("NHIPQUAN_FB_PAGE_ID", "page_1")
os.environ.setdefault("NHIPQUAN_FB_APP_SECRET", "")
os.environ.setdefault("NHIPQUAN_FB_AUTO_SEND", "0")

from ca_api.services.fb_moderation import moderate_fb_message  # noqa: E402

GOLDEN = ROOT / "data" / "fixtures" / "fb_moderation_golden.jsonl"
MIN_CASES = 60
MIN_PASS_RATE = 0.95

PUBLIC_CTX = {
    "profile": {
        "gio_mo_cua": "07:00 - 22:30",
        "dia_chi": "123 Cà Phê, Q.3",
        "wifi": "nhipquan-wifi",
    },
    "menu": [
        {"ten": "Cà phê muối", "gia": 28000},
        {"ten": "Bạc xỉu", "gia": 32000},
        {"ten": "Cà phê đen", "gia": 25000},
    ],
    "promotions": [],
}


def main() -> int:
    if not GOLDEN.exists():
        print(f"ERR: missing golden fixtures {GOLDEN}")
        return 2
    cases = [
        json.loads(line)
        for line in GOLDEN.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not cases:
        print("ERR: golden empty")
        return 2
    if len(cases) < MIN_CASES:
        print(f"RED: golden has {len(cases)} cases; requires at least {MIN_CASES}")
        return 1

    matrix: dict[tuple[str, str], int] = Counter()
    by_action: dict[str, int] = Counter()
    fail = 0
    hard_fail = 0
    for c in cases:
        psid = f"eval_{c['id']}"
        try:
            out = moderate_fb_message(
                psid=psid,
                text=c["message"],
                message_id=f"mid_{c['id']}",
                timestamp=0.0,
                public_context=PUBLIC_CTX,
                repeat_ask_count=3 if c.get("id") == "loop_01" else 0,
            )
        except Exception as e:  # noqa: BLE001
            print(f"  {c['id']}: EXCEPTION {e!r}")
            fail += 1
            hard_fail += 1
            continue
        actual = out.get("action") or "n/a"
        expected = c["expected_action"]
        matrix[(expected, actual)] += 1
        by_action[actual] += 1
        ok = actual == expected
        if not ok:
            fail += 1
            # escalate_owner và block_* lọt qua là RED build theo §5.2
            if expected in {"block_silent", "block_polite"} and actual != expected:
                hard_fail += 1
            if expected == "escalate_owner" and actual != "escalate_owner":
                hard_fail += 1
        flag = "OK " if ok else "MISS"
        print(
            f"  {flag} {c['id']:>9}  expected={expected:<18} actual={actual:<18}  "
            f"role={c.get('expected_role')}  {c.get('note', '')}"
        )

    n = len(cases)
    rate = (n - fail) / n if n else 0
    print("")
    print(f"PASS: {n - fail}/{n} ({rate:.2%})")
    print(f"BY ACTION: {dict(by_action)}")
    print(f"CONFUSION (expected→actual): {dict(matrix)}")
    print(f"HARD FAIL (lọt escalate/block): {hard_fail}")

    if hard_fail > 0:
        print("RED: hard fail (escalate/block sai) > 0")
        return 1
    if rate < MIN_PASS_RATE:
        print(f"RED: pass rate {rate:.2%} < {MIN_PASS_RATE:.2%}")
        return 1
    print("GREEN")
    return 0


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() not in {"utf-8", "utf8"}:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    raise SystemExit(main())
