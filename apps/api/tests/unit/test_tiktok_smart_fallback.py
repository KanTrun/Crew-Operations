"""Unit tests cho _scrape_tiktok_smart — verify Apify primary + TikWM fallback."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from ca_agents.ag_trend import TrendItem, _scrape_tiktok_smart
from ca_agents.clients.apify_client import ApifyError


def _tiktokwm_item(idx: int) -> TrendItem:
    return TrendItem(
        id=f"live_tiktok_direct_{idx}_xxx",
        tieu_de=f"TikWM title {idx}",
        cum_tu_khoa_viral="kw",
        nguon_goc="tiktok_vn",
        loai_xu_huong="breaking_vn_24h",
        danh_muc="trao_luu_pop_culture",
        vong_doi="dang_dinh",
        diem_nhan_dac_biet="",
        nguon_goc_chi_tiet="",
        ngu_canh_su_dung="",
        tam_ly_gioi_tre="",
        toc_do_tang_truong_24h=500.0,
        diem_tiem_nang_viral=90,
        du_bao_thoi_gian="",
    )


def _apify_item(idx: int) -> TrendItem:
    return TrendItem(
        id=f"apify_tiktok_{idx}_yyy",
        tieu_de=f"Apify title {idx}",
        cum_tu_khoa_viral="kw",
        nguon_goc="tiktok_vn",
        loai_xu_huong="breaking_vn_24h",
        danh_muc="trao_luu_pop_culture",
        vong_doi="dang_dinh",
        diem_nhan_dac_biet="",
        nguon_goc_chi_tiet="",
        ngu_canh_su_dung="",
        tam_ly_gioi_tre="",
        toc_do_tang_truong_24h=500.0,
        diem_tiem_nang_viral=90,
        du_bao_thoi_gian="",
    )


def test_tiktokwm_primary_success_skips_apify():
    """Khi TikWM Direct OK thì Apify không bị gọi (tiết kiệm quota 100%)."""
    tiktokwm_items = [_tiktokwm_item(0), _tiktokwm_item(1)]
    with patch(
        "ca_agents.ag_trend._scrape_tiktokwm_fallback",
        return_value=tiktokwm_items,
    ) as tiktokwm_mock, patch(
        "ca_agents.sources.tiktok_apify_source.scrape_tiktok_apify"
    ) as apify_mock:
        result = _scrape_tiktok_smart(keyword="k", count=2)

    assert result == tiktokwm_items
    tiktokwm_mock.assert_called_once_with(keyword="k", count=2)
    apify_mock.assert_not_called()


def test_tiktokwm_error_triggers_apify_backup():
    """Khi TikWM lỗi → tự động kích hoạt Apify backup."""
    apify_items = [_apify_item(0)]
    with patch(
        "ca_agents.ag_trend._scrape_tiktokwm_fallback",
        side_effect=Exception("TikWM rate limited"),
    ) as tiktokwm_mock, patch(
        "ca_agents.sources.tiktok_apify_source.scrape_tiktok_apify",
        return_value=apify_items,
    ) as apify_mock:
        result = _scrape_tiktok_smart(keyword="k", count=1)

    assert result == apify_items
    tiktokwm_mock.assert_called_once()
    apify_mock.assert_called_once_with(
        keyword="k",
        count=1,
        mode="search",
        nguon_goc="tiktok_vn",
    )


def test_both_fail_returns_empty():
    """Khi cả TikWM và Apify đều fail → trả [] an toàn (không crash)."""
    with patch(
        "ca_agents.ag_trend._scrape_tiktokwm_fallback",
        side_effect=Exception("TikWM dead"),
    ), patch(
        "ca_agents.sources.tiktok_apify_source.scrape_tiktok_apify",
        side_effect=ApifyError("Apify also dead"),
    ):
        result = _scrape_tiktok_smart(keyword="k", count=1)

    assert result == []