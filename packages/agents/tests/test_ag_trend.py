"""Unit tests for AG-TREND Catchphrase & Slang Intelligence Engine."""

from ca_agents.ag_trend import (
    fetch_trend_radar,
    get_trend_by_id,
)


def test_fetch_trend_radar_filters():
    all_trends = fetch_trend_radar("all", "all")
    assert len(all_trends) >= 5

    # Test filtering by breaking VN trends
    vn_trends = fetch_trend_radar("breaking_vn_24h", "all")
    assert len(vn_trends) >= 3
    for t in vn_trends:
        assert t.loai_xu_huong == "breaking_vn_24h"
        assert t.toc_do_tang_truong_24h > 300.0


def test_trend_catchphrase_and_slang_analysis():
    trend = get_trend_by_id("vn_slang_co_dia_that_nghiep")
    assert trend is not None
    assert trend.cum_tu_khoa_viral == "Cơ địa khó thất nghiệp"
    assert "Lê Bống" in trend.nguon_goc_chi_tiet
    assert len(trend.diem_nhan_dac_biet) > 20
    assert len(trend.ngu_canh_su_dung) > 20
    assert len(trend.mau_comment_viral) >= 2


def test_fetch_trend_radar_google_vn_serpapi_primary() -> None:
    from unittest.mock import patch

    from ca_agents.ag_trend import TrendItem

    mock_serp_items = [
        TrendItem(
            id="gtrend_001",
            tieu_de="[Google Trends VN] Xu hướng: Cà phê muối",
            cum_tu_khoa_viral="cà phê muối",
            nguon_goc="google_vn",
            loai_xu_huong="breaking_vn_24h",
            danh_muc="am_thuc_fnb",
            vong_doi="moi_nhu",
            diem_nhan_dac_biet="Từ khóa bùng nổ tìm kiếm",
            nguon_goc_chi_tiet="Google Trends SerpApi",
            ngu_canh_su_dung="Đưa vào menu",
            tam_ly_gioi_tre="Tò mò",
            toc_do_tang_truong_24h=5000.0,
            diem_tiem_nang_viral=95,
            du_bao_thoi_gian="Đang hot",
        )
    ]

    with patch(
        "ca_agents.sources.gtrends_serpapi_source.fetch_fnb_trends_serpapi",
        return_value=mock_serp_items,
    ) as mock_fetch:
        results = fetch_trend_radar(platform_filter="google_vn", keyword="cà phê muối")
        mock_fetch.assert_called_once()
        assert len(results) == 1
        assert results[0].cum_tu_khoa_viral == "cà phê muối"
        assert results[0].nguon_goc == "google_vn"
