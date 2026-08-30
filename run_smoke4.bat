@echo off
setlocal
set PYTHONPATH=d:\Crew-Operations\packages\agents\src
cd /d d:\Crew-Operations
python -u scripts\smoke_tiktok_apify.py --keyword viral --count 5 --no-color > d:\Crew-Operations\_smoke4.txt 2>&1
echo === EXIT %ERRORLEVEL% ===
type d:\Crew-Operations\_smoke4.txt