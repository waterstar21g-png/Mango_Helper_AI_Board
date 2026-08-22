#!/usr/bin/env bash
# 망고보드 → 독립 GitHub 저장소 publish (bash / Git Bash)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_URL="https://github.com/waterstar21g-png/Mango_Helper_AI_Board.git"
TMP="${TMPDIR:-/tmp}/Mango_Helper_AI_Board_publish"

echo "망고보드 독립 저장소 publish"
echo "대상: $REPO_URL"

rm -rf "$TMP"
mkdir -p "$TMP"
cp -a "$ROOT/." "$TMP/"
rm -rf "$TMP/.git" 2>/dev/null || true
find "$TMP" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$TMP" -type d -name output -exec rm -rf {} + 2>/dev/null || true
find "$TMP" -type d -name run-logs -exec rm -rf {} + 2>/dev/null || true
find "$TMP" -type d -name .chrome-profile -exec rm -rf {} + 2>/dev/null || true

cd "$TMP"
git init -b main
git add -A
git commit -m "feat: Mango_Helper_AI_Board 망고보드 v1.4.1 — 독립 저장소 publish"

if ! git remote get-url origin &>/dev/null; then
  git remote add origin "$REPO_URL"
else
  git remote set-url origin "$REPO_URL"
fi

echo "push 시도..."
if git push -u origin main; then
  echo "[OK] publish 완료: $REPO_URL"
else
  echo "[안내] push 실패 — GitHub 로그인(gh auth login 또는 PAT) 확인"
  echo "  PC PowerShell: .\\scripts\\publish-standalone.ps1"
  exit 1
fi
