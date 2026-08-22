@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: 망고보드 PC 원클릭 전체 설치
:: ★ AI board (D:\My_Project\AI_Program_Main_Board) 는 절대 수정하지 않음
:: ★ 이 스크립트는 Mango_Helper_AI_Board 폴더만 사용
::
:: 사용: D:\My_Project\Mango_Helper_AI_Board 에 이 파일을 넣고 더블클릭
::       (또는 저장소 clone 후 이 파일 더블클릭)

set "ROOT=D:\My_Project\Mango_Helper_AI_Board"
if exist "%~dp0run.bat" set "ROOT=%~dp0"
if exist "%~dp0board\app.py" set "ROOT=%~dp0"

cd /d "%ROOT%"
echo ========================================
echo   망고보드 PC 원클릭 전체 설치
echo   경로: %ROOT%
echo ========================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git 없음. https://git-scm.com/download/win 설치 후 다시 실행
  pause
  exit /b 1
)

where powershell >nul 2>nul
if errorlevel 1 (
  echo [ERROR] PowerShell 없음
  pause
  exit /b 1
)

:: 소스 없으면 GitHub에서 자동 받기
if not exist "%ROOT%\run.bat" (
  echo [1] 망고보드 소스 받는 중...
  if not exist "%ROOT%" mkdir "%ROOT%"
  cd /d "%ROOT%"

  :: 독립 repo clone 시도
  git clone https://github.com/waterstar21g-png/Mango_Helper_AI_Board.git . 2>nul
  if not exist "%ROOT%\run.bat" (
    echo [안내] 독립 repo 비어있음 - 부모 저장소 main 에서 복사...
    set "TMP=%TEMP%\mango_parent_%RANDOM%"
    git clone -b main --single-branch --depth 1 https://github.com/waterstar21g-png/AI_Program_Main_Board.git "!TMP!"
    if exist "!TMP!\Mango_Helper_AI_Board\run.bat" (
      xcopy "!TMP!\Mango_Helper_AI_Board\*" "%ROOT%\" /E /Y /Q >nul
      echo [OK] 소스 복사 완료
    )
    if exist "!TMP!" rmdir /s /q "!TMP!"
  ) else (
    echo [OK] 독립 repo clone 완료
  )
)

if not exist "%ROOT%\run.bat" (
  echo [ERROR] 소스를 받지 못했습니다. 인터넷·GitHub 로그인 확인
  pause
  exit /b 1
)

cd /d "%ROOT%"

:: install-all.ps1 없으면 부모에서 한번 더 시도
if not exist "%ROOT%\scripts\install-all.ps1" (
  echo [ERROR] scripts\install-all.ps1 없음 - 저장소가 불완전합니다
  pause
  exit /b 1
)

echo [2] 전체 설치 실행...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\install-all.ps1"
set "EC=%ERRORLEVEL%"
echo.
if not "%EC%"=="0" (
  echo [실패] exit=%EC%
  pause
  exit /b %EC%
)
pause
exit /b 0
