@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   P2 Tmg Product Collector (Python)
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
echo Install from https://www.python.org/downloads/
echo During setup, check the box: Add python.exe to PATH
pause
exit /b 1

:havepy
echo [1/2] checking packages ...
call %PY% -m pip install --quiet --disable-pip-version-check -r ..\requirements.txt
if errorlevel 1 (
  call %PY% -m pip install --quiet --disable-pip-version-check -r requirements.txt
)
if errorlevel 1 goto pipfail
goto pipok

:pipfail
echo [ERROR] pip install failed
pause
exit /b 1

:pipok
set "EXCEL=%~1"
if not "%EXCEL%"=="" goto haveexcel
echo.
echo Drag Excel onto run.bat, or type path.
set /p EXCEL=Excel file path: 

:haveexcel
if exist "%EXCEL%" goto runcollect
echo [ERROR] File not found: %EXCEL%
pause
exit /b 1

:runcollect
echo [2/2] starting: %EXCEL%
echo Extra args: %2 %3 %4 %5 %6 %7 %8 %9
echo.
REM 기본: 저장수 3 + 행 재시도 3 + 무중단
REM 로그인: 브라우저에서 사용자가 직접 (자동 ID/PW 입력 없음)
REM 나머지 인자: --verify 등
call %PY% collect.py "%EXCEL%" 3 --retries 3 --yes %2 %3 %4 %5 %6 %7 %8 %9
set ERR=%ERRORLEVEL%

echo.
if not "%ERR%"=="0" (
  echo [FAIL] exit %ERR%
  pause
  exit /b %ERR%
)
echo done. press any key to close.
pause >nul
