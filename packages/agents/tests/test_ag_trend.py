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