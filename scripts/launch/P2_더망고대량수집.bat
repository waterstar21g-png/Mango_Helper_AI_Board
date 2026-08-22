@echo off
chcp 65001 >nul
cd /d "%~dp0..\..\P2"
where py >nul 2>nul && set "PY=py -3" || set "PY=python"
%PY% collect.py %*
pause
