@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================
echo   망고보드 (mango board)  (Python)
echo ========================================

where py >nul 2>nul
if errorlevel 1 goto trypython
set "PY=py -3"
goto havepy

:trypython
where python >nul 2>nul
if errorlevel 1 goto trypython3
set "PY=python"
goto havepy

:trypython3
where python3 >nul 2>nul
if errorlevel 1 goto nopython
set "PY=python3"
goto havepy

:nopython
echo [ERROR] Python not found.
echo https://www.python.org/downloads/
pause
exit /b 1

:havepy
:: 바탕화면 아이콘 실행 시 최신 소스 자동 반영 (--noupdate 로 생략)
if /I "%~1"=="--noupdate" goto skipupdate
echo [1/3] 최신 버전 확인 · 자동 반영 ...
call %PY% board\auto_update.py
goto afterupdate

:skipupdate
echo [1/3] 자동 반영 생략 (--noupdate)

:afterupdate
echo [2/3] pip install ...
call %PY% -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed
  pause
  exit /b 1
)

echo [3/3] board start
call %PY% board\app.py
if errorlevel 1 pause
