"""Canary hàng ngày cho các nguồn cào bên thứ ba (plan `260913-1455` mục 7).

Plan mục 7 [ĐỀ XUẤT MỚI] nói rõ: *"cần test canary hàng ngày chạy riêng (không nằm
trong CI chặn merge) để cảnh báo sớm khi ShopeeFood/Google Maps đổi UI, tách biệt khỏi
test suite chính để không block release vì lỗi bên ngoài."*

Ba ràng buộc từ câu đó, và cách file này đáp ứng:

1. **CHẠY RIÊNG.** Nằm ở `scripts/canary/`, ngoài `testpaths = ["apps","packages"]`
   của `pyproject.toml`, nên `pytest -q` mặc định KHÔNG bao giờ nhặt tới. Workflow
   canary cũng đặt `continue-on-error: true`.
2. **KHÔNG BLOCK RELEASE.** Exit code 0 kể cả khi nguồn chết — kết quả là một BÁO
   CÁO, không phải một gate. Người đọc quyết định có dừng crawl hay không.
3. **CẢNH BÁO SỚM.** Dò selector THẬT trên trang THẬT. Selector lấy từ
   `ca_agents.sources.scraper_selectors` — cùng một danh sách scraper đang dùng, nên
   canary không thể xanh trong khi scraper đã mù.

Chạy:
    python scripts/canary/chay_canary_nguon.py
    python scripts/canary/chay_canary_nguon.py --json   # cho máy đọc / đẩy alert

Cần `camoufox` + mạng thật. Không có hai thứ đó thì in "KHONG_CHAY_DUOC" và thoát 0
— canary không chạy được là chuyện của hạ tầng, không phải của nguồn.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Chạy được bằng `python scripts/canary/chay_canary_nguon.py` mà không cần cài đặt
# package trước — canary phải chạy được trên máy vận hành tối giản.
_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "packages" / "agents" / "src"))
sys.path.insert(0, str(_REPO / "packages" / "contracts" / "src"))

# Console Windows mặc định là cp1252 và sẽ UnicodeEncodeError khi in tiếng Việt —
# tức canary chết ngay chỗ in báo cáo, đúng lúc người vận hành cần đọc nó nhất.
# `errors="replace"` để một ký tự lạ không làm mất cả báo cáo.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):  # stream bị thay bằng thứ không reconfigure được
        pass

from ca_agents.sources.scraper_selectors import (  # noqa: E402
    CAC_NGUON,
    MUC_DO,
    MUC_KHONG_CHAY,
    MUC_VANG,
    MUC_XANH,
    NguonCanary,
    selector_can_do,
    tim_dau_hieu_chan,
    xep_muc_chung,
    xep_muc_nguon,
)

# Luật xếp mức (`xep_muc_nguon`, `tim_dau_hieu_chan`, `xep_muc_chung`) nằm ở
# `scraper_selectors.py` chứ không ở đây: nó là hàm THUẦN, test lại được mà không cần
# mở Google Maps thật. Script này chỉ lo phần I/O trình duyệt và in báo cáo.


@dataclass(slots=True)
class KetQuaNguon:
    """Kết quả dò MỘT nguồn.

    Giữ cả `so_phan_tu_tim_thay` thô chứ không chỉ giữ mức xanh/vàng/đỏ: người vận
    hành cần thấy "hôm qua 10 kết quả, hôm nay 1" để tự kết luận, thay vì phải tin
    một nhãn nhị phân do script đặt ra.
    """

    ma: str
    ten: str
    muc: str
    url: str
    selector_thieu: list[str]
    selector_mat_tuy_chon: list[str]
    so_phan_tu_tim_thay: dict[str, int]
    dau_hieu_bi_chan: list[str]
    loi: str = ""
    thoi_gian_giay: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "ma": self.ma,
            "ten": self.ten,
            "muc": self.muc,
            "url": self.url,
            "selector_thieu": self.selector_thieu,
            "selector_mat_tuy_chon": self.selector_mat_tuy_chon,
            "so_phan_tu_tim_thay": self.so_phan_tu_tim_thay,
            "dau_hieu_bi_chan": self.dau_hieu_bi_chan,
            "loi": self.loi,
            "thoi_gian_giay": round(self.thoi_gian_giay, 2),
        }


def _do_trang(page: Any, nguon: NguonCanary) -> KetQuaNguon:
    """Mở trang và đếm số phần tử khớp từng selector.

    Đếm chứ không chỉ kiểm tra tồn tại: "có 1 kết quả" khác "có 10 kết quả", và
    tụt từ 10 xuống 1 thường là dấu hiệu trang đổi layout trước khi chết hẳn.
    """
    bat_dau = time.monotonic()
    ket_qua = KetQuaNguon(
        ma=nguon.ma,
        ten=nguon.ten,
        muc=MUC_XANH,
        url=nguon.url_mau,
        selector_thieu=[],
        selector_mat_tuy_chon=[],
        so_phan_tu_tim_thay={},
        dau_hieu_bi_chan=[],
    )

    try:
        page.goto(nguon.url_mau, wait_until="domcontentloaded", timeout=45000)
        # Chờ SPA render — scraper thật cũng chờ, nên canary phải chờ giống nhau,
        # nếu không canary sẽ báo đỏ oan cho trang chỉ render chậm.
        page.wait_for_timeout(4000)

        noi_dung = ""
        try:
            noi_dung = page.content()
        except Exception:  # noqa: BLE001 — không lấy được HTML thì bỏ qua bước dò chặn
            pass
        ket_qua.dau_hieu_bi_chan = tim_dau_hieu_chan(noi_dung) or tim_dau_hieu_chan(page.url)

        # `selector_can_do` chứ không tự nối tuple: thiếu một selector là nhóm chứa
        # nó sẽ bị kết luận là chết và canary báo đỏ oan.
        for selector in selector_can_do(nguon):
            try:
                so_luong = page.locator(selector).count()
            except Exception:  # noqa: BLE001 — selector sai cú pháp cũng là một phát hiện
                so_luong = 0
            ket_qua.so_phan_tu_tim_thay[selector] = so_luong

    except Exception as exc:  # noqa: BLE001 — canary phải sống sót để báo cáo tiếp nguồn khác
        ket_qua.loi = f"{type(exc).__name__}: {exc}"
        ket_qua.dau_hieu_bi_chan = ket_qua.dau_hieu_bi_chan or tim_dau_hieu_chan(str(exc))

    ket_qua.thoi_gian_giay = time.monotonic() - bat_dau

    ket_qua.muc, ket_qua.selector_thieu, ket_qua.selector_mat_tuy_chon = xep_muc_nguon(
        nguon,
        ket_qua.so_phan_tu_tim_thay,
        dau_hieu_bi_chan=ket_qua.dau_hieu_bi_chan,
        loi=ket_qua.loi,
    )
    return ket_qua


def chay_canary() -> dict[str, Any]:
    """Dò mọi nguồn. Trả payload tổng; KHÔNG raise kể cả khi thiếu camoufox."""
    thoi_diem = datetime.now(timezone.utc).isoformat()

    try:
        from camoufox.sync_api import Camoufox  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return {
            "chay_luc": thoi_diem,
            "muc": MUC_KHONG_CHAY,
            "ly_do_khong_chay": (
                f"không import được camoufox ({type(exc).__name__}: {exc}). "
                "Canary cần trình duyệt anti-detect thật — cài `camoufox` rồi chạy lại."
            ),
            "nguon": [],
        }

    ket_qua: list[KetQuaNguon] = []
    try:
        # headless=False là cố ý: Google phát hiện headless rất gắt, và canary cần
        # thấy đúng thứ scraper thấy. CI không có display thì bước này sẽ lỗi và
        # được ghi nhận là `khong_chay_duoc` chứ không phải "nguồn chết".
        with Camoufox(headless=False) as browser:
            page = browser.new_page()
            for nguon in CAC_NGUON:
                ket_qua.append(_do_trang(page, nguon))
            page.close()
    except Exception as exc:  # noqa: BLE001
        return {
            "chay_luc": thoi_diem,
            "muc": MUC_KHONG_CHAY,
            "ly_do_khong_chay": f"không mở được trình duyệt: {type(exc).__name__}: {exc}",
            "nguon": [k.as_dict() for k in ket_qua],
        }

    return {
        "chay_luc": thoi_diem,
        "muc": xep_muc_chung(k.muc for k in ket_qua),
        "ly_do_khong_chay": "",
        "nguon": [k.as_dict() for k in ket_qua],
    }


def _in_bao_cao(payload: dict[str, Any]) -> None:
    """In báo cáo cho người đọc. Ngôn ngữ vận hành, không mã HTTP, không stack trace."""
    bieu_tuong = {
        MUC_XANH: "[OK]",
        MUC_VANG: "[CANH BAO]",
        MUC_DO: "[NGUON HONG]",
        MUC_KHONG_CHAY: "[KHONG CHAY DUOC]",
    }
    print(f"Canary nguồn cào — {payload['chay_luc']}")
    print(f"Tình trạng chung: {bieu_tuong.get(payload['muc'], payload['muc'])}")

    if payload.get("ly_do_khong_chay"):
        print(f"Lý do: {payload['ly_do_khong_chay']}")

    for nguon in payload["nguon"]:
        nhan = bieu_tuong.get(nguon["muc"], nguon["muc"])
        print(f"\n{nhan} {nguon['ten']} ({nguon['thoi_gian_giay']}s)")
        if nguon["dau_hieu_bi_chan"]:
            print(f"  Trang trả dấu hiệu chặn bot: {', '.join(nguon['dau_hieu_bi_chan'])}")
        if nguon["loi"]:
            print(f"  Không tải được trang: {nguon['loi']}")
        for selector in nguon["selector_thieu"]:
            print(f"  MẤT selector bắt buộc: {selector}")
        for selector in nguon["selector_mat_tuy_chon"]:
            print(f"  Mất selector phụ (suy giảm, chưa chết): {selector}")
        if not (nguon["selector_thieu"] or nguon["selector_mat_tuy_chon"] or nguon["loi"]):
            for selector, so in nguon["so_phan_tu_tim_thay"].items():
                print(f"  Đọc được {so} phần tử: {selector}")
            if not nguon["so_phan_tu_tim_thay"]:
                print("  Không có selector DOM nào để dò (nguồn đọc qua response JSON).")

    print(
        "\nCanary KHÔNG chặn merge và KHÔNG tự tắt tính năng. "
        "Mức [NGUON HONG] nghĩa là nên giảm tần suất crawl và cập nhật selector "
        "trong packages/agents/src/ca_agents/sources/scraper_selectors.py trước khi chạy tiếp."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="In JSON thay vì báo cáo cho người đọc"
    )
    args = parser.parse_args()

    payload = chay_canary()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _in_bao_cao(payload)

    # LUÔN trả 0. Đây là điểm khác biệt cốt lõi với test suite: một workflow canary
    # đỏ không được phép chặn release vì lỗi của bên thứ ba (plan mục 7).
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
