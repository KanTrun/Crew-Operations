"""AI auto-poster cho page Nhịp Quán.

Su dung LLM (Gemini hoac Groq) de sinh caption Facebook tieng Viet,
sau do dang len page thong qua Graph API.

Usage:
    python scripts/fb_auto_poster.py --topic menu
    python scripts/fb_auto_poster.py --topic "khuyen mai cuoi tuan" --tone hai huoc
    python scripts/fb_auto_poster.py --dry-run --topic gio mo cua
"""

import argparse
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from datetime import UTC

from facebook_page_poster import FacebookPagePoster

PROMPT_TEMPLATE = """Ban la quan ly truyen thong cho quan ca phe "Nhip Quan" o Viet Nam.
Hay viet mot bai dang Facebook tieng Viet, gioi thieu/dam thoai voi khach hang.
- Chu de: {topic}
- Giong giong: {tone}
- Gio mo cua: 7:00 - 22:30
- Khong gian: yen tinh, co o cam, wifi, phuc vu ca phe specialty, tra, banh ngot.

Yeu cau:
- 3-5 doan ngan, moi doan 1-3 cau.
- Co emoji canh bao (vi du: cafe, tra, banh, khuyen mai, lien he).
- Ket thuc bang mot cau Call-To-Action (vi du: "Den quan hom nay nhe!").
- KHONG them hashtag "#" vi dang tren page chinh.
- KHONG su dung tieng Anh.
- Cho ra TEXT bai dang, khong giai thich.


POST:
"""


def llm_generate_gemini(prompt: str) -> str:
    """Sinh text qua Gemini (1.5 Flash — re, nhanh)."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("thieu GEMINI_API_KEY trong .env")

    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 600},
    }
    r = requests.post(url, json=body, timeout=30)
    r.raise_for_status()
    data = r.json()
    cand = (data.get("candidates") or [{}])[0]
    parts = cand.get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


def llm_generate_groq(prompt: str) -> str:
    """Fallback sang Groq (llama-3.1)."""
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("thieu GROQ_API_KEY trong .env")

    model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant").strip()
    url = "https://api.groq.com/openai/v1/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 600,
    }
    r = requests.post(url, json=body, headers={"Authorization": f"Bearer {key}"}, timeout=30)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _parse_iso(s: str):
    """Parse ISO 8601 tu Facebook (co the la '2026-08-30T09:57:16+0000' hoac '...Z')."""
    from datetime import datetime

    s = s.replace("Z", "+00:00")
    # Them ':' vao timezone neu thieu (vd: +0000 -> +00:00).
    if len(s) >= 5 and s[-5] in "+-" and s[-3] != ":":
        s = s[:-2] + ":" + s[-2:]
    return datetime.fromisoformat(s)


def generate_content(topic: str, tone: str = "than thien") -> str:
    prompt = PROMPT_TEMPLATE.format(topic=topic, tone=tone)
    try:
        return llm_generate_gemini(prompt)
    except Exception as e:
        print(f"[Gemini fail: {e}] -> fallback Groq")
    return llm_generate_groq(prompt)


def _count_posts_today(poster: FacebookPagePoster) -> int:
    """Dem so bai da dang hom nay (gio VN, UTC+7).

    FB tra created_time theo UTC. VN = UTC+7.
    """
    from datetime import datetime, timedelta

    try:
        # Lay 10 bai moi nhat, dem trong hom nay theo gio VN.
        url = f"{poster.BASE_URL}/{poster.page_id}/posts"
        r = requests.get(
            url,
            params={
                "fields": "id,created_time",
                "limit": 10,
                "access_token": poster.page_token,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json().get("data") or []
        vn_today = (datetime.now(UTC) + timedelta(hours=7)).date()
        count = 0
        for p in data:
            ct = p.get("created_time", "")
            if not ct:
                continue
            try:
                pt = _parse_iso(ct)
                pt_vn = (pt + timedelta(hours=7)).date()
                if pt_vn == vn_today:
                    count += 1
            except Exception:
                continue
        return count
    except Exception as e:
        print(f"[rate-limit] Khong check duoc so bai: {e}")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True, help="Chu de bai dang")
    ap.add_argument(
        "--tone",
        default="than thien",
        help="Giong: than thien | trang trong | hai huoc | truyen cam hung",
    )
    ap.add_argument("--dry-run", action="store_true", help="Chi in preview, khong dang that")
    args = ap.parse_args()

    poster = FacebookPagePoster()
    if not poster.verify_token():
        return 2

    print(f"\n[LLM] Dang sinh bai: topic='{args.topic}', tone='{args.tone}' ...")
    text = generate_content(args.topic, args.tone)
    print(f"\n=== PREVIEW ===\n{text}\n===============")

    if args.dry_run:
        print("[dry-run] Khong dang that")
        return 0

    # Chong spam: toi da 2 bai/ngay (Facebook se an neu dang nhieu hon).
    today_count = _count_posts_today(poster)
    if today_count >= 2:
        print(f"[rate-limit] Hom nay da dang {today_count} bai -> BO QUA dang that.")
        print("  (Facebook co the an page neu dang qua nhieu trong 24h.)")
        return 4

    print(f"\n[LLM] Dang sinh bai: topic='{args.topic}', tone='{args.tone}' ...")
    text = generate_content(args.topic, args.tone)
    print(f"\n=== PREVIEW ===\n{text}\n===============")

    if args.dry_run:
        print("[dry-run] Khong dang that")
        return 0

    result = poster.post_text(text)
    if not result.get("success"):
        print(f"LOI: {result.get('error')}")
        return 3

    print(f"\n=== POSTED ===\nID: {result.get('post_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
