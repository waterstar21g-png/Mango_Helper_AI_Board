# 망고보드 PC 원클릭 전체 설치
# - GitHub clone/pull
# - pip 설치
# - 바탕화면 바로가기
# - 동작 확인
#
# 사용: .\망고보드_한번에설치.bat  (더블클릭)

$ErrorActionPreference = "Stop"

$RepoUrl      = "https://github.com/waterstar21g-png/Mango_Helper_AI_Board.git"
$ParentUrl    = "https://github.com/waterstar21g-png/AI_Program_Main_Board.git"
$ParentBranch = "main"
$DefaultRoot  = "D:\My_Project\Mango_Helper_AI_Board"
$AiBoardPath  = "D:\My_Project\AI_Program_Main_Board"   # 절대 수정 금지

function Write-Step($n, $total, $msg) {
    Write-Host ""
    Write-Host "[$n/$total] $msg" -ForegroundColor Cyan
}

function Find-Python {
    foreach ($cmd in @("py -3", "python", "python3")) {
        try {
            $null = Invoke-Expression "$cmd --version" 2>$null
            if ($LASTEXITCODE -eq 0) { return $cmd }
        } catch {}
    }
    return $null
}

function Test-Git {
    try {
        $null = git --version 2>$null
        return $LASTEXITCODE -eq 0
    } catch { return $false }
}

function Ensure-Directory($path) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
        Write-Host "  폴더 생성: $path" -ForegroundColor Yellow
    }
}

function Test-MangoRoot($path) {
    return (Test-Path (Join-Path $path "run.bat")) -and (Test-Path (Join-Path $path "board\app.py"))
}

function Clone-IntoEmpty($url, $branch, $target) {
    Ensure-Directory (Split-Path -Parent $target)
    if (Test-Path $target) {
        $items = Get-ChildItem -Force $target -ErrorAction SilentlyContinue
        if ($items.Count -gt 0) {
            throw "대상 폴더가 비어 있지 않습니다: $target"
        }
    } else {
        New-Item -ItemType Directory -Path $target -Force | Out-Null
    }
    if ($branch) {
        git clone --branch $branch --single-branch $url $target
    } else {
        git clone $url $target
    }
}

function Sync-FromParent($target) {
    $temp = Join-Path $env:TEMP "Mango_Helper_AI_Board_parent_sync"
    if (Test-Path $temp) { Remove-Item -Recurse -Force $temp }
    git clone --branch $ParentBranch --single-branch --depth 1 $ParentUrl $temp
    $src = Join-Path $temp "Mango_Helper_AI_Board"
    if (-not (Test-Path $src)) { throw "부모 저장소에 Mango_Helper_AI_Board 폴더 없음" }
    robocopy $src $target /E /XD .git __pycache__ .chrome-profile output run-logs /XF *.pyc /NFL /NDL /NJH /NJS | Out-Null
    Remove-Item -Recurse -Force $temp
}

function Init-GitAndPull($root) {
    Set-Location $root
    if (-not (Test-Path ".git")) {
        git init -b main | Out-Null
        git remote add origin $RepoUrl 2>$null
        if ($LASTEXITCODE -ne 0) { git remote set-url origin $RepoUrl }
    }
    git fetch origin main 2>$null
    if ($LASTEXITCODE -eq 0) {
        git checkout -B main 2>$null
        git pull origin main 2>$null
    }
}

# ── 시작 ─────────────────────────────────────────────
Write-Host "========================================" -ForegroundColor Green
Write-Host "  망고보드 (Mango_Helper_AI_Board)" -ForegroundColor Green
Write-Host "  PC 원클릭 전체 설치" -ForegroundColor Green
Write-Host "  ※ AI board 폴더는 건드리지 않습니다" -ForegroundColor DarkGray
Write-Host "========================================" -ForegroundColor Green

$total = 6

# 1) Python
Write-Step 1 $total "Python 확인"
$py = Find-Python
if (-not $py) {
    Write-Host "[ERROR] Python 3 없음 → https://www.python.org/downloads/ 설치 (Add to PATH)" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] $py" -ForegroundColor Green

# 2) Git
Write-Step 2 $total "Git 확인"
if (-not (Test-Git)) {
    Write-Host "[ERROR] Git 없음 → https://git-scm.com/download/win 설치" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] git $(git --version)" -ForegroundColor Green

# 3) 작업 경로 결정
Write-Step 3 $total "망고보드 경로 준비"
$ScriptRoot = $null
try {
    $inv = $MyInvocation.MyCommand.Path
    if ($inv) {
        $cand = Split-Path -Parent (Split-Path -Parent $inv)
        if (Test-MangoRoot $cand) { $ScriptRoot = $cand }
    }
} catch {}

if ($ScriptRoot) {
    $Root = $ScriptRoot
    Write-Host "  스크립트 위치 사용: $Root" -ForegroundColor Green
} elseif (Test-Path $DefaultRoot) {
    $Root = $DefaultRoot
    Write-Host "  기본 경로 사용: $Root" -ForegroundColor Green
} else {
    $Root = $DefaultRoot
    Ensure-Directory $Root
    Write-Host "  기본 경로 생성: $Root" -ForegroundColor Yellow
}

if ($Root -eq $AiBoardPath) {
    Write-Host "[ERROR] 망고보드 경로가 AI board 와 같습니다. Mango_Helper_AI_Board 폴더를 사용하세요." -ForegroundColor Red
    exit 1
}

# 4) 소스 받기 (clone / pull / 부모 폴백)
Write-Step 4 $total "GitHub 소스 동기화"
Ensure-Directory $Root
Set-Location $Root

if (Test-MangoRoot $Root) {
    Write-Host "  소스 이미 있음 — 최신화 시도" -ForegroundColor Green
    if (Test-Path (Join-Path $Root ".git")) {
        git fetch origin main 2>$null
        if ($LASTEXITCODE -eq 0) {
            git pull origin main 2>$null
            Write-Host "  git pull origin main 완료" -ForegroundColor Green
        }
    }
} else {
    $cloned = $false
    # 독립 repo clone 시도
    try {
        Write-Host "  clone: $RepoUrl" -ForegroundColor Yellow
        $parentDir = Split-Path -Parent $Root
        Ensure-Directory $parentDir
        $items = @()
        if (Test-Path $Root) { $items = Get-ChildItem -Force $Root -ErrorAction SilentlyContinue }
        if ($items.Count -eq 0) {
            if (Test-Path $Root) { Remove-Item $Root -Force -Recurse -ErrorAction SilentlyContinue }
            git clone $RepoUrl $Root
            if (Test-MangoRoot $Root) { $cloned = $true }
        }
    } catch {
        Write-Host "  [안내] 독립 repo clone 실패: $_" -ForegroundColor Yellow
    }

  # 독립 repo 비어 있으면 부모 브랜치에서 복사
    if (-not (Test-MangoRoot $Root)) {
        Write-Host "  부모 저장소에서 소스 복사 (폴백)..." -ForegroundColor Yellow
        Ensure-Directory $Root
        Sync-FromParent $Root
        if (Test-MangoRoot $Root) {
            Init-GitAndPull $Root
            Write-Host "  [OK] 부모 브랜치에서 소스 복사 완료" -ForegroundColor Green
        }
    } elseif ($cloned) {
        Write-Host "  [OK] 독립 repo clone 완료" -ForegroundColor Green
    }
}

if (-not (Test-MangoRoot $Root)) {
    Write-Host "[ERROR] 망고보드 소스를 받지 못했습니다." -ForegroundColor Red
    Write-Host "  수동: git clone $RepoUrl $Root" -ForegroundColor Yellow
    exit 1
}

Set-Location $Root
Write-Host "  경로: $Root" -ForegroundColor Green
$ver = Get-Content "VERSION.txt" -Encoding UTF8 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($ver) { Write-Host "  버전: $ver" -ForegroundColor Green }

# 5) pip 설치
Write-Step 5 $total "Python 패키지 설치"
Invoke-Expression "$py -m pip install --upgrade pip --quiet"
Invoke-Expression "$py -m pip install -r requirements.txt --quiet"
if (Test-Path "P2\requirements.txt") {
    Invoke-Expression "$py -m pip install -r P2\requirements.txt --quiet"
}
Write-Host "  [OK] pip install 완료" -ForegroundColor Green

# 6) 바로가기 + 검증
Write-Step 6 $total "바로가기 생성 · 동작 확인"

# 바탕화면 아이콘 — 생성 로직은 board/desktop_icon.py 하나로만 유지
Invoke-Expression "$py board\desktop_icon.py"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [안내] 바탕화면 아이콘 생성 실패 — .\망고보드_바탕화면아이콘.bat 로 다시 시도" -ForegroundColor Yellow
}

# smoke test
$launchOut = Invoke-Expression "$py scripts\launch.py list" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] 프로그램 목록 로드 성공" -ForegroundColor Green
} else {
    Write-Host "  [경고] launch.py 검증 실패 (실행은 가능할 수 있음)" -ForegroundColor Yellow
}

# 완료
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  설치 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  실행:  $Root\run.bat" -ForegroundColor White
Write-Host "  또는 바탕화면 [망고보드] 더블클릭" -ForegroundColor White
Write-Host ""
Write-Host "  프로그램 목록: $py scripts\launch.py list" -ForegroundColor Cyan
Write-Host "  업데이트:      .\scripts\pull-update.ps1" -ForegroundColor Cyan
Write-Host ""

$runNow = Read-Host "지금 망고보드를 실행할까요? (Y/N)"
if ($runNow -match '^[Yy]') {
    Start-Process -FilePath (Join-Path $Root "run.bat") -WorkingDirectory $Root
}

exit 0
