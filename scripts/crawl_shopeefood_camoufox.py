"""Cào dữ liệu ShopeeFood VN bằng Camoufox — flow đã kiểm chứng (260922).

Kết luận từ chuỗi probe (bằng chứng: data/cache/sf_probe/*.json):
- shopeefood.vn là SPA; mọi dữ liệu qua host `gappapi.deliverynow.vn`.
- Gọi API chủ động từ ngoài KHÔNG qua được: httpx -> 403, page.request -> 403,
  fetch trong page -> CORS (gappapi không trả CORS header cho origin shopeefood.vn).
- Cách DUY NHẤT ổn định: mở trang thật bằng Camoufox, để SPA TỰ gọi API,
  và BẮT response qua page.on("response"). Cuộn listing để SPA tải thêm lô.
- Listing category gọi: `search_global` (toàn bộ restaurant_ids) + `get_infos`
  (25 quán/lô mỗi lần cuộn tới). Trang quán gọi `get_delivery_dishes` (menu + giá).

Chạy:
    python scripts/crawl_shopeefood_camoufox.py --menu-n 3
    python scripts/crawl_shopeefood_camoufox.py --max-stores 50 --menu-n 0

Output: JSON (default data/cache/sf_crawl_latest.json) — quán + rating + menu giá.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))
sys.path.insert(0, str(_REPO / "packages" / "contracts" / "src"))

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

# Endpoint markers cần bắt (2026) — substring match trên response URL.
M_INFO_LIST = ("get_infos", "get_browsing_infos")  # danh sách quán (2 dạng listing)
M_SEARCH = ("search_global",)  # tổng restaurant_ids theo category/từ khóa
M_DISHES = ("get_delivery_dishes",)  # menu quán

DEFAULT_LISTING = (
    "https://shopeefood.vn/ho-chi-minh/"
    "danh-sach-dia-diem-phuc-vu-soup-based-giao-tan-noi"  # "Mì phở" TP.HCM
)


def _cào_menu_trang(page: Any, store_url: str, parse_price: Any) -> list[dict[str, Any]]:
    """Mở trang quán, bắt `get_delivery_dishes`, trả món + giá đã parse."""
    dishes: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def on_dish(resp: Any) -> None:
        if M_DISHES[0] not in resp.url:
            return
        try:
            d = resp.json()
            for group in (d.get("reply") or {}).get("menu_infos") or []:
                if not isinstance(group, dict):
                    continue
                cat = str(group.get("dish_type_name") or "")
                for it in group.get("dishes") or []:
                    if not isinstance(it, dict):
                        continue
                    name = str(it.get("name") or "").strip()
                    if not name:
                        continue
                    p = it.get("price")
                    if isinstance(p, dict):
                        p = p.get("value") or p.get("text") or 0
                    key = (name, cat)
                    if key in seen:
                        continue
                    seen.add(key)
                    dishes.append(
                        {
                            "name": name,
                            "price": parse_price(p),
                            "price_raw": p,
                            "category": cat,
                        }
                    )
        except Exception:
            pass

    page.on("response", on_dish)
    try:
        page.goto(store_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(4000)
        page.mouse.wheel(0, 3000)  # cuộn nhẹ cho menu dài tải hết
        page.wait_for_timeout(1500)
    except Exception as exc:  # noqa: BLE001
        print(f"   [menu] lỗi mở trang quán: {type(exc).__name__}")
    finally:
        try:
            page.remove_listener("response", on_dish)
        except Exception:  # noqa: BLE001
            pass
    return dishes


def main() -> None:
    ap = argparse.ArgumentParser(description="Cào ShopeeFood VN qua Camoufox (bắt response SPA)")
    ap.add_argument("--cat-url", default=DEFAULT_LISTING, help="URL listing category ShopeeFood")
    ap.add_argument("--lat", type=float, default=10.7769)
    ap.add_argument("--lng", type=float, default=106.7009)
    ap.add_argument("--max-stores", type=int, default=0, help="0 = tất cả quán bắt được")
    ap.add_argument("--menu-n", type=int, default=3, help="Số quán rating cao nhất lấy menu (0 = bỏ qua)")
    ap.add_argument("--out", default=str(_REPO / "data" / "cache" / "sf_crawl_latest.json"))
    args = ap.parse_args()

    from ca_agents.sources.delivery_camoufox_source import parse_price
    from camoufox.sync_api import Camoufox

    quans: dict[int, dict[str, Any]] = {}  # restaurant_id -> info gốc
    sg_total_ids: list[int] = []

    with Camoufox(headless=True, geoip=True, humanize=True) as browser:
        page = browser.new_page()
        page.context.set_geolocation({"latitude": args.lat, "longitude": args.lng})

        def on_response(resp: Any) -> None:
            url = resp.url
            try:
                if any(m in url for m in M_SEARCH):
                    d = resp.json()
                    for item in (d.get("reply") or {}).get("search_result") or []:
                        if isinstance(item, dict):
                            sg_total_ids.extend(int(x) for x in item.get("restaurant_ids") or [])
                elif any(m in url for m in M_INFO_LIST):
                    d = resp.json()
                    for info in (d.get("reply") or {}).get("delivery_infos") or []:
                        if not isinstance(info, dict):
                            continue
                        rid = info.get("restaurant_id") or info.get("id")
                        if rid:
                            quans[int(rid)] = info
            except Exception:  # noqa: BLE001 — response không phải JSON: bỏ qua
                pass

        page.on("response", on_response)

        print(f"[crawl] mở listing: {args.cat_url}")
        page.goto(args.cat_url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(6000)

        # Tải thêm quán: cuộn + bấm nút next của now.vn (`.icon-paging-next`),
        # dừng khi 6 vòng liên tiếp không thêm quán mới.
        stable = 0
        vong = 0
        while stable < 6 and vong < 60:
            vong += 1
            truoc = len(quans)
            # 1) window scroll tới đáy — tinier load của SPA
            try:
                page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
            except Exception:  # noqa: BLE001
                pass
            page.wait_for_timeout(1200)
            # 2) Bấm nút paging next kiểu now.vn nếu có trên trang
            try:
                page.locator(
                    "a .icon-paging-next, a[href='#'] .icon-paging-next, .pagination-next"
                ).first.click(timeout=1200)
                print(f"   [pg] vong {vong}: bấm next -> {len(quans)} quán")
                page.wait_for_timeout(2000)
            except Exception:  # noqa: BLE001
                pass
            # 3) Thử "Xem thêm" nếu trang dùng dạng đó
            if vong % 5 == 0:
                try:
                    page.get_by_text("Xem thêm", exact=False).first.click(timeout=1200)
                    page.wait_for_timeout(2000)
                except Exception:  # noqa: BLE001
                    pass
            stable = stable + 1 if len(quans) == truoc else 0
        print(
            f"[crawl] cuộn {vong} vòng -> {len(quans)} quán "
            f"(search_global ids={len(sg_total_ids)})"
        )

        # Lấy href quán từ DOM (name -> href) — URL chuẩn, dùng cho bước menu.
        dom_cards = page.evaluate(
            """() => Array.from(document.querySelectorAll('.item-restaurant')).map(c => ({
                 name: ((c.querySelector('.name-res') || {}).innerText || '').trim(),
                 href: (c.querySelector('a[href]') || {}).href || '',
               })).filter(x => x.name && x.href)"""
        )
        name_to_href = {c["name"]: c["href"] for c in dom_cards if c.get("name") and c.get("href")}

        # Chuẩn hóa
        kq: list[dict[str, Any]] = []
        for _rid, info in quans.items():
            brand = info.get("brand") or {}
            rating = info.get("rating") or {}
            loc = str(info.get("location_url") or "")
            slug = str(info.get("url_rewrite_name") or info.get("restaurant_url") or "")
            ten = str(brand.get("name") or info.get("name") or "")
            url = name_to_href.get(ten) or (
                f"https://shopeefood.vn/{loc}/{slug}" if loc and slug else ""
            )
            kq.append(
                {
                    "restaurant_id": info.get("restaurant_id"),
                    "delivery_id": info.get("id"),
                    "name": ten,
                    "address": str(info.get("address") or info.get("short_address") or ""),
                    "rating": round(float(rating.get("avg") or 0), 1),
                    "review_count": int(rating.get("total_review") or 0),
                    "review_display": str(rating.get("display_total_review") or ""),
                    "is_open": bool(info.get("is_open")),
                    "is_quality_merchant": bool(info.get("is_quality_merchant")),
                    "categories": info.get("categories") or [],
                    "cuisines": info.get("cuisines") or [],
                    "url": url,
                }
            )
        kq.sort(key=lambda x: (x["rating"], x["review_count"]), reverse=True)
        if args.max_stores > 0:
            kq = kq[: args.max_stores]

        # Menu cho N quán đầu (rating cao nhất)
        if args.menu_n > 0:
            for i, q in enumerate(kq[: args.menu_n]):
                if not q["url"]:
                    continue
                print(f"[menu] {i + 1}/{min(args.menu_n, len(kq))} {q['name'][:40]} ...")
                dishes = _cào_menu_trang(page, q["url"], parse_price)
                q["dishes"] = dishes
                print(f"         -> {len(dishes)} món")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "listing_url": args.cat_url,
                "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "nguon": "gappapi.deliverynow.vn — bắt response SPA (Camoufox)",
                "tong_ids_search_global": len(sg_total_ids),
                "so_quan": len(kq),
                "danh_sach_quan": kq,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n[crawl] DONE — {len(kq)} quán -> {out}")
    for q in kq[:15]:
        print(f"   {q['rating']}* {q['review_display']:>5} | {q['name'][:45]:45} | menu={len(q.get('dishes') or [])}")


if __name__ == "__main__":
    main()