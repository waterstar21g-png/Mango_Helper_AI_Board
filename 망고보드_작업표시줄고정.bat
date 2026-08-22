@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================
echo   망고보드 작업표시줄에 고정
echo ========================================

where py >nul 2>nul
if not errorlevel 1 (
  set "PY=py -3"
  goto havepy
)
where python >nul 2>nul
if not errorlevel 1 (
  set "PY=python"
  goto havepy
)
where python3 >nul 2>nul
if not errorlevel 1 (
  set "PY=python3"
  goto havepy
)
echo [ERROR] Python not found.
echo https://www.python.org/downloads/
pause
exit /b 1

:havepy
call %PY% board\desktop_icon.py --pin-only
set "EC=%ERRORLEVEL%"
echo.
pause
exit /b %EC%
