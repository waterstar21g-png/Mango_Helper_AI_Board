@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ========================================
echo   망고보드 독립 저장소 올리기
echo   github.com/waterstar21g-png/Mango_Helper_AI_Board
echo ========================================

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git 없음. https://git-scm.com/download/win
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\publish-standalone.ps1"
set "EC=%ERRORLEVEL%"
echo.
pause
exit /b %EC%
