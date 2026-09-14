"""Unit tests for AG-TREND Catchphrase & Slang Intelligence Engine."""

from unittest.mock import patch

from ca_agents.ag_trend import (
    TrendItem,
    fetch_trend_radar,
    get_trend_by_id,
)


def _mk_trend(tid: str, loai: str, toc_do: float) -> TrendItem:
    return TrendItem(
        id=tid,
        tieu_de=tid,
        cum_tu_khoa_viral=tid,
        nguon_goc="tiktok_vn",
        loai_xu_huong=loai,
        danh_muc="am_thuc_fnb",
        vong_doi="moi_nhu",
        diem_nhan_dac_biet="x",
        nguon_goc_chi_tiet="x",
        ngu_canh_su_dung="x",
        tam_ly_gioi_tre="x",
        toc_do_tang_truong_24h=toc_do,
        diem_tiem_nang_viral=50,
        du_bao_thoi_gian="x",
    )


def test_fetch_trend_radar_filters() -> None:
    # Test logic lọc/tổng hợp, KHÔNG gọi mạng thật (plan mục 1.4, ADR-002).
    # Mock 5 scraper nội bộ bằng fixture data tất định.
    breaking = [_mk_trend(f"b{i}", "breaking_vn_24h", 500.0 + i) for i in range(4)]
    predictive = [_mk_trend(f"p{i}", "predictive_global", 100.0 + i) for i in range(2)]
    all_items = breaking + predictive

    with (
        patch("ca_agents.ag_trend._scrape_tiktok_smart", return_value=all_items),
        patch("ca_agents.ag_trend._scrape_google_trends_vn", return_value=[]),
        patch("ca_agents.ag_trend._scrape_threads_smart", return_value=[]),
        patch("ca_agents.ag_trend._scrape_showbiz_kols_vn", return_value=[]),
        patch("ca_agents.ag_trend._scrape_google_trends_global", return_value=[]),
    ):
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
