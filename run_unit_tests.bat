@echo off
setlocal
set PYTHONPATH=d:\Crew-Operations\packages\agents\src;d:\Crew-Operations\apps\api\src;d:\Crew-Operations\packages\opsengine\src
cd /d "d:\Crew-Operations"
python -m pytest apps\api\tests\unit\test_apify_client.py apps\api\tests\unit\test_tiktok_apify_source.py apps\api\tests\unit\test_tiktok_smart_fallback.py --tb=short -q 2>&1 > d:\Crew-Operations\_test_result.txt
type d:\Crew-Operations\_test_result.txt
echo.
echo === EXIT CODE: %ERRORLEVEL% ===