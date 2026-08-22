@echo off
chcp 65001 >nul
cd /d "%~dp0"
python update_product_count.py %*
