import os

os.environ['CA_AGENT_MODE'] = 'live'

from ca_agents.ag_trend import fetch_trend_radar

print('=== TIKTOK VN ===')
tiktok_items = fetch_trend_radar(platform_filter='tiktok_vn', keyword='cà phê', force_live=True, scrape_mode='auto')
for i, item in enumerate(tiktok_items[:3]):
    print(f'{i+1}. {item.tieu_de}')
    print(f'   Keyword: {item.cum_tu_khoa_viral}')
    print(f'   Source: {item.nguon_goc} | Live: {item.is_live_scraped}')
    print(f'   URL: {item.link_goc}')
    print(f'   Stats: {item.luot_tiep_can}')
    print()

print('=== THREADS VN ===')
threads_items = fetch_trend_radar(platform_filter='threads_vn', keyword='cà phê', force_live=True, scrape_mode='auto')
for i, item in enumerate(threads_items[:3]):
    print(f'{i+1}. {item.tieu_de}')
    print(f'   Keyword: {item.cum_tu_khoa_viral}')
    print(f'   Source: {item.nguon_goc} | Live: {item.is_live_scraped}')
    print(f'   URL: {item.link_goc}')
    print(f'   Stats: {item.luot_tiep_can}')
    print()