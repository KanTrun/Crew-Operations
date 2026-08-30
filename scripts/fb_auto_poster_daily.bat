@echo off
REM Daily AI auto-poster for Nhip Quan page.
REM Topics rotate theo thu trong tuan.
REM Goi boi Windows Task Scheduler (recurring).

setlocal
set PYTHONIOENCODING=utf-8
chcp 65001 > nul

REM Map thu -> topic
set "DAY=%DATE:~0,3%"
if "%DAY%"=="Mon" set "TOPIC=menu dau tuan" & set "TONE=than thien"
if "%DAY%"=="Tue" set "TOPIC=ca phe specialty hom nay" & set "TONE=trang trong"
if "%DAY%"=="Wed" set "TOPIC=khuyen mai giua tuan" & set "TONE=hai huoc"
if "%DAY%"=="Thu" set "TOPIC=khong gian lam viec tai quan" & set "TONE=truyen cam hung"
if "%DAY%"=="Fri" set "TOPIC=happy weekend tang keo dua" & set "TONE=hai huoc"
if "%DAY%"=="Sat" set "TOPIC=tra va banh ngot cuoi tuan" & set "TONE=than thien"
if "%DAY%"=="Sun" set "TOPIC=chill chu nhat tai quan" & set "TONE=truyen cam hung"

cd /d "D:\Crew-Operations"
python scripts\fb_auto_poster.py --topic "%TOPIC%" --tone "%TONE%"

REM Log ket qua
echo [%DATE% %TIME%] topic=%TOPIC% tone=%TONE% >> logs\fb_auto_poster.log
endlocal