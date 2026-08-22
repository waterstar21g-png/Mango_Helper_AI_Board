@echo off
setlocal
cd /d "%~dp0"
REM 1행×3상품 검증 — ID/PW 는 collect.py 가 CLI로 요청 (또는 --id/--pw)
if "%~1"=="" (
  echo Usage: run-verify.bat excel.xlsx
  echo Or: run-verify.bat excel.xlsx --id MYID --pw MYPW
  pause
  exit /b 1
)
call "%~dp0run.bat" %*
