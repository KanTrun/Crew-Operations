"""Generate synthetic seed (25 NV, 21 ca/week pattern, 8 weeks) + golden fixtures.

All outputs are labeled synthetic — not real cafe PII.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seed"
GOLDEN_MSG = ROOT / "data" / "golden" / "messages"
GOLDEN_TKB = ROOT / "data" / "golden" / "tkb"
RNG = random.Random(42)

SKILLS = ["pha_che", "thu_ngan", "phuc_vu", "kho"]
INTENTS = [
    "xin_nghi",
    "doi_ca",
    "nhan_ca",
    "bao_tre",
    "cap_nhat_tkb",
    "khac",
]


def build_staff(n: int = 25) -> list[dict]:
    out = []
    for i in range(1, n + 1):
        out.append(
            {
                "id": f"nv_{i:02d}",
                "ten": f"Nhan Vien {i:02d}",
                "ky_nang": RNG.sample(SKILLS, k=RNG.randint(1, 3)),
                "la_sinh_vien": i <= 20,
                "synthetic": True,
            }
        )
    return out


def build_shifts_for_week(week: int) -> list[dict]:
    """21 ca / tuần: 7 ngày × 3 khung."""
    slots = [("sang", "07:00", "12:00"), ("chieu", "12:00", "17:00"), ("toi", "17:00", "22:00")]
    out = []
    idx = 1
    for d in range(1, 8):
        for ten, start, end in slots:
            out.append(
                {
                    "id": f"w{week}_c{idx:02d}",
                    "ngay_offset": d,
                    "khung": ten,
                    "bat_dau": start,
                    "ket_thuc": end,
                    "vi_tri": RNG.choice(SKILLS),
                    "so_nguoi_toi_thieu": 2 if ten != "toi" else 3,
                    "synthetic": True,
                }
            )
            idx += 1
    return out


def build_history(staff: list[dict], weeks: int = 8) -> list[dict]:
    hist = []
    for w in range(1, weeks + 1):
        shifts = build_shifts_for_week(w)
        assign = {}
        for sh in shifts:
            need = sh["so_nguoi_toi_thieu"]
            chosen = RNG.sample(staff, k=min(need, len(staff)))
            assign[sh["id"]] = [c["id"] for c in chosen]
        hist.append({"tuan": w, "tuan_iso": f"2026-W{w:02d}", "ca": shifts, "phan_cong": assign})
    return hist


def build_messages(n: int = 200) -> list[dict]:
    templates = {
        "xin_nghi": "em xin nghỉ ca {khung} ngày {thu} ạ",
        "doi_ca": "anh cho em đổi ca {khung} với bạn được không",
        "nhan_ca": "em nhận ca {khung} bị thiếu người nhé",
        "bao_tre": "em xin phép đến trễ 15 phút ca {khung}",
        "cap_nhat_tkb": "tuần này em học {thu} sáng, nhờ cập nhật TKB",
        "khac": "máy pha bên em hơi kêu lạ ca {khung}",
    }
    thu = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
    khung = ["sang", "chieu", "toi"]
    rows = []
    for i in range(1, n + 1):
        intent = INTENTS[i % len(INTENTS)]
        text = templates[intent].format(khung=RNG.choice(khung), thu=RNG.choice(thu))
        rows.append(
            {
                "id": f"msg_{i:03d}",
                "text": text,
                "intent": intent,
                "annotator_a": intent,
                "annotator_b": intent if i % 17 else "khac",
                "synthetic": True,
            }
        )
    agree = sum(1 for r in rows if r["annotator_a"] == r["annotator_b"])
    kappa_proxy = agree / len(rows)
    meta = {
        "n": n,
        "simple_agreement": round(kappa_proxy, 3),
        "note": "synthetic dual labels — not real Cohen kappa from humans",
        "synthetic": True,
    }
    return rows, meta


def build_tkb(n: int = 50) -> None:
    GOLDEN_TKB.mkdir(parents=True, exist_ok=True)
    index = []
    for i in range(1, n + 1):
        nv = f"nv_{(i % 25) + 1:02d}"
        # synthetic busy blocks Mon/Wed/Fri mornings
        blocks = [
            {"thu": "T2", "start": "07:30", "end": "11:00"},
            {"thu": "T4", "start": "07:30", "end": "11:00"},
            {"thu": "T6", "start": "13:00", "end": "16:30"},
        ]
        if i % 2 == 0:
            blocks.append({"thu": "T7", "start": "08:00", "end": "11:30"})
        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='640' height='360'>
<rect width='100%' height='100%' fill='#f7f2ea'/>
<text x='24' y='40' font-size='20' font-family='sans-serif'>TKB synthetic {i:02d} — {nv}</text>
"""
        y = 80
        for b in blocks:
            label = f"{b['thu']} {b['start']}-{b['end']}"
            svg += (
                f"<text x='24' y='{y}' font-size='16' "
                f"font-family='monospace'>{label}</text>\n"
            )
            y += 28
        svg += "</svg>\n"
        name = f"tkb_{i:02d}.svg"
        (GOLDEN_TKB / name).write_text(svg, encoding="utf-8")
        gt = {
            "id": f"tkb_{i:02d}",
            "file": name,
            "nhan_vien_id": nv,
            "khoang_ban": blocks,
            "synthetic": True,
        }
        (GOLDEN_TKB / f"tkb_{i:02d}.json").write_text(
            json.dumps(gt, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        index.append(gt)
    (GOLDEN_TKB / "index.json").write_text(
        json.dumps({"n": n, "items": index, "synthetic": True}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    SEED.mkdir(parents=True, exist_ok=True)
    GOLDEN_MSG.mkdir(parents=True, exist_ok=True)
    staff = build_staff(25)
    history = build_history(staff, 8)
    # 21 ca reference = week 1 pattern
    ca21 = build_shifts_for_week(1)
    payload = {
        "synthetic": True,
        "nhan_vien": staff,
        "ca_mau_21": ca21,
        "lich_su_8_tuan": history,
        "ghi_chu": "Fixture seed — Quán Fixture NHỊP QUÁN (ADR-012)",
    }
    (SEED / "sample.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    msgs, meta = build_messages(200)
    (GOLDEN_MSG / "messages.jsonl").write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in msgs) + "\n",
        encoding="utf-8",
    )
    (GOLDEN_MSG / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    build_tkb(50)
    print("seed", len(staff), "staff", len(ca21), "shifts", len(history), "weeks")
    print("golden messages", len(msgs), "tkb", 50)


if __name__ == "__main__":
    main()
