"""Regression: kỳ \"hom_nay\" phải khớp ngày Việt Nam, không phải UTC.

CI GitHub Actions chạy UTC. Sau 17:00 UTC (= 00:00 VN ngày kế) thì
`date.today()` (UTC) và `ngay_hom_nay()` (+7) lệch một ngày. Test fixture
nạp dữ liệu bằng UTC date sẽ bị `_loc_theo_ky` lọc sạch → 02 unit đỏ.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from ca_agents.ag_waste import ngay_hom_nay, tinh_tu_nguon


def test_ngay_hom_nay_khac_utc_sau_17h() -> None:
    """Đóng băng lúc 17:30 UTC (= 00:30 VN ngày sau) — hai múi giờ phải lệch."""
    utc = datetime(2026, 9, 25, 17, 30, tzinfo=ZoneInfo("UTC"))
    with patch("ca_agents.ag_waste.loss.datetime") as mock_dt:
        mock_dt.now.side_effect = lambda tz=None: utc.astimezone(tz) if tz else utc
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        vn = ngay_hom_nay()
    assert vn == "2026-09-26"
    assert utc.date().isoformat() == "2026-09-25"
    assert vn != utc.date().isoformat()


def test_tinh_tu_nguon_hom_nay_khong_mat_du_lieu_sau_17h_utc() -> None:
    """Fixture dùng ngay_hom_nay() vẫn còn dòng sau khi UTC đã sang ngày khác."""
    utc = datetime(2026, 9, 25, 17, 30, tzinfo=ZoneInfo("UTC"))
    with patch("ca_agents.ag_waste.loss.datetime") as mock_dt:
        mock_dt.now.side_effect = lambda tz=None: utc.astimezone(tz) if tz else utc
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        hom_nay = ngay_hom_nay()
        s = tinh_tu_nguon(
            kiem_ke=[{
                "ngay": hom_nay,
                "muc": [{"mat_hang": "da", "dau_ca": 10, "nhap_trong_ca": 0, "cuoi_ca": 4, "hao_hut_ghi": 0}],
            }],
            ky="hom_nay",
        )
    assert s.tong_dong == 1
    assert s.dong[0].mat_hang == "da"
