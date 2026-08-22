# 망고보드 → 독립 GitHub 저장소(Mango_Helper_AI_Board) 올리기
#
# 사용: .\망고보드_독립저장소올리기.bat  (또는 .\scripts\publish-standalone.ps1)
#
# 3가지 상황을 자동 판별한다.
#   A) 이 폴더가 이미 독립 저장소 클론      → 커밋 후 push
#   B) 이 폴더가 단독 폴더(.git 없음)        → 여기서 git init 후 push (이후 git pull 가능)
#   C) 부모 저장소(AI보드) 하위 폴더         → 임시 복사본으로 push (원본은 건드리지 않음)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$RepoUrl = "https://github.com/waterstar21g-png/Mango_Helper_AI_Board.git"
$Branch = "main"

function Get-ParentRepo($path) {
    $cur = Split-Path -Parent $path
    while ($cur) {
        if (Test-Path (Join-Path $cur ".git")) { return $cur }
        $next = Split-Path -Parent $cur
        if ($next -eq $cur) { break }
        $cur = $next
    }
    return $null
}

function Invoke-Push($workDir, $message) {
    Set-Location $workDir
    if (-not (Test-Path ".git")) {
        git init -b $Branch | Out-Null
    }
    $remotes = git remote 2>$null
    if ($remotes -notcontains "origin") {
        git remote add origin $RepoUrl
    } else {
        git remote set-url origin $RepoUrl
    }
    git add -A
    git commit -m $message 2>$null | Out-Null
    git branch -M $Branch 2>$null | Out-Null
    git push -u origin $Branch
    return $LASTEXITCODE
}

$ver = (Get-Content (Join-Path $Root "VERSION.txt") -Encoding UTF8 -ErrorAction SilentlyContinue |
        Select-Object -First 1)
$message = "feat: 망고보드 독립 저장소 소스 반영 ($ver)"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  망고보드 독립 저장소 올리기" -ForegroundColor Cyan
Write-Host "  대상: $RepoUrl" -ForegroundColor Cyan
Write-Host "  버전: $ver" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$parentRepo = Get-ParentRepo $Root
$hasOwnGit = Test-Path (Join-Path $Root ".git")

if ($hasOwnGit) {
    Write-Host "[A] 이 폴더가 git 저장소 — 그대로 push" -ForegroundColor Green
    $code = Invoke-Push $Root $message
} elseif ($parentRepo) {
    Write-Host "[C] 부모 저장소 하위 폴더 ($parentRepo) — 임시 복사본으로 push" -ForegroundColor Yellow
    $temp = Join-Path $env:TEMP "Mango_Helper_AI_Board_publish"
    if (Test-Path $temp) { Remove-Item -Recurse -Force $temp }
    New-Item -ItemType Directory -Path $temp | Out-Null
    robocopy $Root $temp /E /XD .git __pycache__ .pytest_cache .chrome-profile output run-logs `
        /XF *.pyc *.lnk /NFL /NDL /NJH /NJS | Out-Null
    $code = Invoke-Push $temp $message
} else {
    Write-Host "[B] 단독 폴더 — 여기서 git 저장소로 만들어 push" -ForegroundColor Green
    $code = Invoke-Push $Root $message
}

Write-Host ""
if ($code -eq 0) {
    Write-Host "[OK] 올렸습니다: https://github.com/waterstar21g-png/Mango_Helper_AI_Board" -ForegroundColor Green
    Write-Host "     이후 망고보드 아이콘을 누르면 이 저장소에서 자동 갱신됩니다." -ForegroundColor Green
    if (-not $hasOwnGit -and $parentRepo) {
        Write-Host ""
        Write-Host "  권장: 독립 폴더로 clone 해서 쓰기" -ForegroundColor Cyan
        Write-Host "    git clone $RepoUrl D:\My_Project\Mango_Helper_AI_Board"
    }
    Write-Host ""
    Write-Host "  ※ GitHub 저장소 기본 브랜치가 main 이 아니면" -ForegroundColor DarkGray
    Write-Host "    Settings → Branches → Default branch 를 main 으로 바꿔주세요." -ForegroundColor DarkGray
} else {
    Write-Host "[실패] push 거부 (exit=$code)" -ForegroundColor Red
    Write-Host "  - GitHub 로그인 계정에 그 저장소 쓰기 권한이 있는지 확인" -ForegroundColor Yellow
    Write-Host "  - 저장소가 없으면 https://github.com/new → Mango_Helper_AI_Board" -ForegroundColor Yellow
}
exit $code
