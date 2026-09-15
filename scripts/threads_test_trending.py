"""Script kiểm tra thực tế tính năng cào bảng 'Trending Now' trên Threads bằng Camoufox.

Cách chạy:
    python scripts/threads_test_trending.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Đảm bảo đường dẫn import trong monorepo
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "packages" / "agents" / "src"))
sys.path.insert(0, str(_ROOT / "packages" / "contracts" / "src"))


def main() -> None:
    profile_dir = Path(os.getenv("CA_THREADS_USER_DATA_DIR", "./threads_profile")).resolve()

    print("=" * 70)
    print(" KIỂM TRA CÀO THỰC TẾ: THREADS 'TRENDING NOW' (CAMOUFOX)")
    print("=" * 70)
    print(f">> Profile đang dùng: {profile_dir}")

    if not profile_dir.exists():
        print(f"\n[CẢNH BÁO] Chưa tìm thấy thư mục profile '{profile_dir}'.")
        print("Nếu chưa đăng nhập, vui lòng chạy lệnh sau trước:")
        print("    python scripts/threads_setup_login.py\n")

    print(">> Đang kích hoạt Camoufox cào bảng Trending Now tại https://www.threads.net/search ...")

    try:
        from ca_agents.clients.camoufox_client import CamoufoxUnavailable
        from ca_agents.sources.threads_trending_source import scrape_threads_trending
    except ImportError as e:
        print(f"[LỖI IMPORT] {e}")
        sys.exit(1)

    try:
        items = scrape_threads_trending(user_data_dir=str(profile_dir), count=10)
    except CamoufoxUnavailable as e:
        print(f"\n[THÔNG BÁO] Không thể cào dữ liệu qua Camoufox: {e}")
        print("\nGợi ý:")
        print("1. Nếu chưa cài Camoufox: pip install -U 'camoufox[geoip]' && camoufox fetch")
        print("2. Nếu chưa đăng nhập: python scripts/threads_setup_login.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n[LỖI BẤT THƯỜNG] {e}")
        sys.exit(1)

    if not items:
        print("\n>> Không thu thập được mục xu hướng nào (có thể do phiên chưa đăng nhập hoặc mạng chậm).")
        return

    print(f"\n>> Thu thập thành công {len(items)} chủ đề xu hướng nóng:\n")
    print(f"{'#':<4} | {'Chủ đề (Title)':<40} | {'Thảo luận':<15} | {'Vòng đời':<12}")
    print("-" * 80)
    for idx, item in enumerate(items, 1):
        # Rút ngắn tiêu đề để hiển thị bảng
        t_clean = item.cum_tu_khoa_viral[:38]
        print(f"{idx:<4} | {t_clean:<40} | {item.luot_tiep_can:<15} | {item.vong_doi:<12}")

    print("\nChi tiết các liên kết gốc:")
    for idx, item in enumerate(items, 1):
        print(f"{idx}. {item.cum_tu_khoa_viral}")
        print(f"   Link: {item.link_goc}")
        print(f"   Ghi chú: {item.diem_nhan_dac_biet}")
        print()


if __name__ == "__main__":
    main()
