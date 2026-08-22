# 망고보드 GitHub 최신 반영 (PowerShell)
# 사용: .\scripts\pull-update.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "망고보드 업데이트 — $Root" -ForegroundColor Cyan

if (Test-Path ".git") {
    # 독립 저장소 (Mango_Helper_AI_Board)
    git fetch origin main --prune
    git pull origin main
} else {
    # 부모 저장소 하위 폴더인 경우
    $parent = Split-Path -Parent $Root
    if (Test-Path (Join-Path $parent ".git")) {
        Set-Location $parent
        Write-Host "부모 저장소에서 pull: $parent" -ForegroundColor Yellow
        git fetch origin main --prune
        git pull origin main
        Set-Location $Root
    } else {
        Write-Host "[ERROR] .git 없음. PC_SETUP.md 의 클론 절차를 따르세요." -ForegroundColor Red
        exit 1
    }
}

$ver = Get-Content "VERSION.txt" -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -First 1
Write-Host "[OK] $ver" -ForegroundColor Green
