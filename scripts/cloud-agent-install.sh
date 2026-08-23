#!/usr/bin/env bash
# Cloud Agent 개발환경 설치 스크립트 (Linux).
# 망고보드는 순수 파이썬(tkinter UI + playwright 자동화)입니다.
# 이 스크립트는 멱등(idempotent) — 여러 번 실행해도 안전합니다.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[1/3] tkinter(GUI) 시스템 패키지 설치"
# board/app.py 의 Tkinter UI 에는 python3-tk 가 필요합니다.
sudo apt-get update
sudo apt-get install -y python3-tk

echo "[2/3] 파이썬 의존성 설치 (루트 + P2 + pytest)"
# 이 VM 의 파이썬은 externally-managed 이므로 --break-system-packages 사용.
python3 -m pip install --break-system-packages --disable-pip-version-check \
  -r requirements.txt -r P2/requirements.txt pytest

echo "[3/3] Playwright 브라우저(chromium) 설치"
python3 -m playwright install chromium

echo "완료: python3 scripts/launch.py list / python3 board/app.py / python3 -m pytest"
