"""Smoke test end-to-end cho TikTok scraper (Apify primary + TikWM fallback).

Cách dùng:
    python scripts/smoke_tiktok_apify.py
    python scripts/smoke_tiktok_apify.py --keyword "xuhuong" --count 5
    python scripts/smoke_tiktok_apify.py --no-color
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Fix unicode cho Windows console (cp1252 default)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Thêm packages/agents/src vào sys.path để import ca_agents
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "agents" / "src"))
sys.path.insert(0, str(ROOT / "apps" / "api" / "src"))

# Load .env nếu có (không cần python-dotenv — parse thủ công)
_ENV_PATH = ROOT / ".env"
if _ENV_PATH.exists():
    try:
        with open(_ENV_PATH, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _v = _line.split("=", 1)
                # Chỉ set nếu chưa có (ưu tiên env thật)
                if _k.strip() and _k.strip() not in os.environ:
                    os.environ[_k.strip()] = _v.strip()
    except Exception as _e:
        print(f"[WARN] Không đọc được .env: {_e}")

try:
    from ca_agents.ag_trend import _scrape_tiktok_smart  # noqa: E402
except ImportError as e:
    print(f"[FATAL] Không import được _scrape_tiktok_smart: {e}")
    sys.exit(2)


# ANSI color
_USE_COLOR = sys.stdout.isatty()
_RED = "\033[91m" if _USE_COLOR else ""
_YELLOW = "\033[93m" if _USE_COLOR else ""
_GREEN = "\033[92m" if _USE_COLOR else ""
_CYAN = "\033[96m" if _USE_COLOR else ""
_RESET = "\033[0m" if _USE_COLOR else ""


def _colored(s: str, color: str) -> str:
    return f"{color}{s}{_RESET}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test TikTok scraper")
    parser.add_argument("--keyword", default="xuhuong", help="Từ khóa tìm kiếm")
    parser.add_argument("--count", type=int, default=5, help="Số video")
    parser.add_argument(
        "--nguon-goc",
        default="tiktok_vn",
        choices=["tiktok_vn", "tiktok_global"],
    )
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()

    global _USE_COLOR
    if args.no_color:
        _USE_COLOR = False

    print(_colored("═" * 60, _CYAN), flush=True)
    print(_colored("  TikTok scraper smoke test", _CYAN), flush=True)
    print(_colored("═" * 60, _CYAN), flush=True)
    print(f"  keyword  : {args.keyword}", flush=True)
    print(f"  count    : {args.count}", flush=True)
    print(f"  nguon_goc: {args.nguon_goc}", flush=True)
    print(f"  token?   : {'YES' if os.getenv('APIFY_TOKEN') else 'NO  ← sẽ fallback TikWM'}", flush=True)
    print(_colored("─" * 60, _CYAN), flush=True)
    print("  → calling Apify...", flush=True)

    start = time.monotonic()
    try:
        items = _scrape_tiktok_smart(
            keyword=args.keyword,
            count=args.count,
            nguon_goc=args.nguon_goc,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
    except Exception as e:  # noqa: BLE001
        print(_colored(f"[FATAL] Exception: {e}", _RED))
        return 1

    # Detect source dựa trên id prefix (xem convention trong source files)
    if items and items[0].id.startswith("apify_tiktok_"):
        source = "apify"
    elif items and items[0].id.startswith("live_tiktok_direct_"):
        source = "tiktokwm"
    else:
        source = "unknown"

    # In kết quả
    if not items:
        print(_colored("⚠️  Không trả về items nào", _YELLOW))
        return 0

    if source == "tiktokwm":
        print(_colored("⚠️  Apify fail, đang dùng FALLBACK TikWM", _RED))
        print(_colored("   Kiểm tra APIFY_TOKEN + quota + log", _YELLOW))

    print(_colored(f"✅ Source : {source}", _GREEN if source == "apify" else _YELLOW))
    print(_colored(f"   Items  : {len(items)}", _GREEN))
    print(_colored(f"   Time   : {elapsed_ms}ms", _GREEN))
    print(_colored("─" * 60, _CYAN))

    # In top 3
    for idx, item in enumerate(items[:3], start=1):
        print(_colored(f"  [{idx}] {item.tieu_de}", _CYAN))
        print(f"      URL      : {item.tiktok_url}")
        print(f"      Reach    : {item.luot_tiep_can}")
        print(f"      Comments : {len(item.binh_luan_that_tiktok)}")
        print()

    print(_colored("─" * 60, _CYAN))
    return 0


if __name__ == "__main__":
    sys.exit(main())