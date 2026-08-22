@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."
where py >nul 2>nul && set "PY=py -3" || set "PY=python"
%PY% scripts\launch.py p3_filter %*
pause
