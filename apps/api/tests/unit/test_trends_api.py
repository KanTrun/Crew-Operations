# mypy: disable-error-code="no-untyped-def,no-untyped-call,type-arg,no-any-return,unused-ignore"
"""Unit tests for Pure Trends API endpoints."""

from unittest.mock import patch

from ca_agents.ag_trend import TrendItem
from ca_api.interfaces.http.main import app
from ca_api.persist import init_db, login
from fastapi.testclient import TestClient

client = TestClient(app)


def _mk_trend(tid: str) -> TrendItem:
    return TrendItem(
        id=tid,
        tieu_de=tid,
        cum_tu_khoa_viral=tid,
        nguon_goc="tiktok_vn",
        loai_xu_huong="breaking_vn_24h",
        danh_muc="am_thuc_fnb",
        vong_doi="moi_nhu",
        diem_nhan_dac_biet="x",
        nguon_goc_chi_tiet="x",
        ngu_canh_su_dung="x",
        tam_ly_gioi_tre="x",
        toc_do_tang_truong_24h=500.0,
        diem_tiem_nang_viral=50,
        du_bao_thoi_gian="x",
    )


def test_trends_radar_endpoints() -> None:
    init_db()
    auth = login("lan", "nhipquan")
    headers = {"Authorization": f"Bearer {auth['token']}"}

    # Mock scraper để test hermetic, không gọi mạng thật (plan mục 1.4).
    mock_trends = [_mk_trend(f"t{i}") for i in range(6)]
    with patch(
        "ca_api.interfaces.http.trends.fetch_trend_radar", return_value=mock_trends
    ):
        # 1. GET all trends
        res = client.get("/api/v1/trends/radar?region=all&category=all", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert len(data["trends"]) >= 5

        # 2. GET breaking VN trends
        res_vn = client.get(
            "/api/v1/trends/radar?region=breaking_vn_24h&category=all", headers=headers
        )
        assert res_vn.status_code == 200
        data_vn = res_vn.json()
        assert data_vn["region_filter"] == "breaking_vn_24h"
        assert len(data_vn["trends"]) >= 3
