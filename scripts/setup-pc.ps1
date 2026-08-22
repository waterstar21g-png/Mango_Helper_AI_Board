# 망고보드 PC 최초 설정 (PowerShell)
# 사용: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned  (최초 1회)
#       .\scripts\setup-pc.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  망고보드 (Mango_Helper_AI_Board) PC 설정" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "경로: $Root"

# Python
$py = $null
foreach ($cmd in @("py -3", "python", "python3")) {
    try {
        $v = Invoke-Expression "$cmd --version" 2>$null
        if ($LASTEXITCODE -eq 0) { $py = $cmd; break }
    } catch {}
}
if (-not $py) {
    Write-Host "[ERROR] Python 3 없음. https://www.python.org/downloads/ 설치 후 PATH 추가" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Python: $py"

# pip install
Write-Host "[1/3] pip install (루트)..."
Invoke-Expression "$py -m pip install --upgrade pip"
Invoke-Expression "$py -m pip install -r requirements.txt"
if (Test-Path "P2\requirements.txt") {
    Write-Host "[2/3] pip install (P2)..."
    Invoke-Expression "$py -m pip install -r P2\requirements.txt"
}

# 바탕화면 아이콘 — 생성 로직은 board/desktop_icon.py 하나로만 유지
Invoke-Expression "$py board\desktop_icon.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[안내] 바탕화면 아이콘은 나중에 .\망고보드_바탕화면아이콘.bat 로 만들 수 있습니다" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/3] 완료. 실행 방법:" -ForegroundColor Green
Write-Host "  .\run.bat"
Write-Host "  .\scripts\launch\00_망고보드_메인.bat"
Write-Host "  $py scripts\launch.py list"
Write-Host ""
Write-Host "GitHub 업데이트: .\scripts\pull-update.ps1" -ForegroundColor Cyan
