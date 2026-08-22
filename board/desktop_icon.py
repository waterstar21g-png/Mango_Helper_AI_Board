"""망고보드 바탕화면 실행 아이콘 만들기 (순수 파이썬 · 표준 라이브러리만).

- 바탕화면(OneDrive·한글 「바탕 화면」 포함)에 **망고보드.lnk** 생성 → `run.bat` 실행
- 드래그용으로 프로젝트 폴더에도 같은 바로가기를 하나 둔다
- .lnk 는 Windows 전용 형식이므로 생성만 PowerShell(WScript.Shell COM) 에 위임하고,
  경로 탐색·검증·로그는 모두 파이썬에서 처리한다
- PowerShell 은 -EncodedCommand(UTF-16LE) 로 호출 — 한글 경로·이름 코드페이지 문제 회피

단독 실행:
    py -3 board\\desktop_icon.py
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys
from pathlib import Path

LNK_NAME = "망고보드.lnk"
DESCRIPTION = "망고보드 (mango board) — Mango_Helper_AI_Board"
LAUNCHER = "run.bat"

# AI보드 아이콘(imageres.dll,109) 과 구분되는 인덱스
ICON_PRIMARY = r"%SystemRoot%\System32\imageres.dll,171"
ICON_FALLBACK = r"%SystemRoot%\System32\shell32.dll,44"

PREFERRED_ROOT = r"D:\My_Project\Mango_Helper_AI_Board"

# 한글 Windows 의 「바탕 화면」
_KO_DESKTOP = "바탕 화면"


def board_root() -> Path:
    """망고보드 루트 — 이 파일 기준. AI보드 등 상위 폴더를 올려다보지 않는다."""
    return Path(__file__).resolve().parent.parent


def is_windows() -> bool:
    return os.name == "nt"


def desktop_dirs(env: dict[str, str] | None = None) -> list[Path]:
    """존재하는 바탕화면 폴더 전부 (중복 제거, 순서 유지)."""
    env = dict(os.environ if env is None else env)
    home = env.get("USERPROFILE") or env.get("HOME") or ""
    onedrive = env.get("OneDrive") or env.get("OneDriveConsumer") or ""

    candidates: list[str] = []
    for base in (home, onedrive, os.path.join(home, "OneDrive"), os.path.join(home, "OneDrive - Personal")):
        if not base:
            continue
        candidates.append(os.path.join(base, "Desktop"))
        candidates.append(os.path.join(base, _KO_DESKTOP))

    found: list[Path] = []
    for c in candidates:
        p = Path(c)
        if not p.is_dir():
            continue
        real = p.resolve()
        if real not in found:
            found.append(real)
    return found


REG_DESKTOP_KEY = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"


def parse_reg_desktop(output: str) -> str:
    """`reg query … /v Desktop` 출력에서 실제 바탕화면 경로만 뽑는다."""
    for line in (output or "").splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[0].strip().lower() != "desktop":
            continue
        idx = line.lower().find("reg_sz")
        if idx < 0:
            continue
        return line[idx + len("reg_sz") :].strip()
    return ""


def registry_desktop(runner=None) -> Path | None:
    """Windows 가 실제로 쓰는 바탕화면 폴더 (OneDrive 리디렉션 포함)."""
    if runner is None:
        if not is_windows():
            return None

        def runner(args):  # noqa: WPS430
            return subprocess.run(args, capture_output=True, timeout=15, check=False)

    try:
        proc = runner(["reg", "query", REG_DESKTOP_KEY, "/v", "Desktop"])
    except (OSError, subprocess.TimeoutExpired):
        return None

    out = getattr(proc, "stdout", b"") or b""
    if isinstance(out, bytes):
        for enc in ("cp949", "utf-8", "mbcs"):
            try:
                out = out.decode(enc)
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            out = out.decode("utf-8", errors="replace")

    path = parse_reg_desktop(str(out))
    if not path:
        return None
    expanded = Path(os.path.expandvars(path))
    return expanded if expanded.is_dir() else None


def primary_desktop(env: dict[str, str] | None = None, runner=None) -> Path | None:
    """아이콘을 놓을 바탕화면 한 곳 — 레지스트리 값 우선."""
    reg = registry_desktop(runner)
    if reg is not None:
        return reg
    dirs = desktop_dirs(env)
    return dirs[0] if dirs else None


def shortcut_paths(
    root: Path | None = None,
    env: dict[str, str] | None = None,
    *,
    all_targets: bool = False,
) -> list[Path]:
    """만들 .lnk 경로.

    기본: **실행파일 아이콘 1개** — 실제 바탕화면에만.
    `all_targets=True`: 바탕화면 후보 전부 + 프로젝트 폴더(드래그용) 사본.
    """
    root = root or board_root()
    if all_targets:
        paths = [d / LNK_NAME for d in desktop_dirs(env)]
        paths.append(root / LNK_NAME)
        return paths

    desktop = primary_desktop(env)
    return [desktop / LNK_NAME] if desktop is not None else []


def _ps_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


PIN_DIR_SUFFIX = r"Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"

# 한글/영문 Windows 의 「작업 표시줄에 고정」 verb (폴백 — 1순위는 아래 리소스 조회)
PIN_VERB_PATTERN = "작업.?표시줄에 고정|Pin to tas"

# 「작업 표시줄에 고정」 의 현지화 문자열은 shell32.dll 문자열 리소스 5386 에 있다.
# 하드코딩 문자열로 찾으면 언어팩·빌드에 따라 못 찾으므로 이 값을 1순위로 쓴다.
PIN_VERB_RESOURCE_ID = 5386


def build_pin_powershell(lnk: Path) -> str:
    """바탕화면 아이콘을 작업표시줄에 고정 (+ 시작메뉴 배치) 스크립트."""
    return "\n".join(
        [
            f"$lnk = {_ps_quote(lnk)}",
            f"$pinDir = Join-Path $env:APPDATA {_ps_quote(PIN_DIR_SUFFIX)}",
            "try {",
            "  if (-not (Test-Path -LiteralPath $pinDir)) {",
            "    New-Item -ItemType Directory -Force -Path $pinDir | Out-Null",
            "  }",
            "  Copy-Item -LiteralPath $lnk -Destination $pinDir -Force",
            "  Write-Output \"PINDIR $pinDir\"",
            "} catch { Write-Output \"PINDIRFAIL $($_.Exception.Message)\" }",
            # 시작 메뉴에도 둬서 우클릭 고정이 가능하게
            "try {",
            "  $menu = [Environment]::GetFolderPath('Programs')",
            "  Copy-Item -LiteralPath $lnk -Destination $menu -Force",
            "  Write-Output \"MENU $menu\"",
            "} catch { Write-Output \"MENUFAIL $($_.Exception.Message)\" }",
            # shell32.dll 에서 현지화된 verb 이름을 읽어온다 (언어 무관)
            "$verbName = ''",
            "try {",
            "  $sig = @'",
            "[DllImport(\"kernel32.dll\", CharSet=CharSet.Unicode, SetLastError=true)]",
            "public static extern IntPtr LoadLibrary(string lpFileName);",
            "[DllImport(\"user32.dll\", CharSet=CharSet.Unicode, SetLastError=true)]",
            "public static extern int LoadString(IntPtr h, uint id,"
            " System.Text.StringBuilder buf, int max);",
            "'@",
            "  Add-Type -MemberDefinition $sig -Name PinRes -Namespace Win32"
            " -PassThru | Out-Null",
            "  $h = [Win32.PinRes]::LoadLibrary('shell32.dll')",
            "  $sb = New-Object System.Text.StringBuilder 1024",
            f"  [void][Win32.PinRes]::LoadString($h, {PIN_VERB_RESOURCE_ID},"
            " $sb, $sb.Capacity)",
            "  $verbName = ($sb.ToString() -replace '&','')",
            "  if ($verbName) { Write-Output \"PINVERBNAME $verbName\" }",
            "} catch { Write-Output \"PINVERBNAMEFAIL $($_.Exception.Message)\" }",
            # 셸 verb 로 실제 고정 시도 — 리소스 이름 우선, 그 다음 패턴
            "try {",
            "  $shell = New-Object -ComObject Shell.Application",
            "  $folder = $shell.Namespace((Split-Path -Parent $lnk))",
            "  $item = $folder.ParseName((Split-Path -Leaf $lnk))",
            "  $done = $false",
            "  foreach ($verb in $item.Verbs()) {",
            "    $name = ($verb.Name -replace '&','')",
            "    $hit = $false",
            "    if ($verbName -and $name -eq $verbName) { $hit = $true }",
            f"    elseif ($name -match '{PIN_VERB_PATTERN}') {{ $hit = $true }}",
            "    if ($hit) {",
            "      $verb.DoIt()",
            "      $done = $true",
            "      break",
            "    }",
            "  }",
            "  if ($done) { Write-Output \"PIN $lnk\" }",
            "  else {",
            "    $names = (($item.Verbs() | ForEach-Object { $_.Name }) -join ' | ')",
            "    Write-Output \"PINVERB none :: $names\"",
            # 자동 고정이 막히면 아이콘을 선택한 상태로 탐색기를 띄워
            # 우클릭 → [작업 표시줄에 고정] 을 바로 할 수 있게 한다
            "    try { Start-Process explorer.exe -ArgumentList \"/select,$lnk\" } catch {}",
            "  }",
            "} catch { Write-Output \"PINFAIL $($_.Exception.Message)\" }",
        ]
    )


def build_powershell(root: Path, targets: list[Path], *, pin: bool = True) -> str:
    """WScript.Shell 로 .lnk 를 만들고, 작업표시줄 고정까지 하는 스크립트 본문."""
    launcher = root / LAUNCHER
    lines = [
        "$ErrorActionPreference = 'Stop'",
        f"$bat = {_ps_quote(launcher)}",
        # ★ .bat 을 직접 가리키는 바로가기는 Windows 가 작업표시줄 고정을 막는다.
        #   cmd.exe 를 타깃으로 두고 run.bat 을 인자로 넘기면 고정이 가능해진다.
        "$target = Join-Path $env:SystemRoot 'System32\\cmd.exe'",
        f"$work = {_ps_quote(root)}",
        f"$icon = [Environment]::ExpandEnvironmentVariables({_ps_quote(ICON_PRIMARY)})",
        f"$iconFallback = [Environment]::ExpandEnvironmentVariables({_ps_quote(ICON_FALLBACK)})",
        "if (-not (Test-Path -LiteralPath ($icon -split ',')[0])) { $icon = $iconFallback }",
        "if (-not (Test-Path -LiteralPath $bat)) { throw \"run.bat not found: $bat\" }",
        "$shell = New-Object -ComObject WScript.Shell",
    ]
    for lnk in targets:
        lines += [
            f"$p = {_ps_quote(lnk)}",
            "try {",
            "  if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force }",
            "  $sc = $shell.CreateShortcut($p)",
            "  $sc.TargetPath = $target",
            "  $sc.Arguments = '/c ' + [char]34 + $bat + [char]34",
            "  $sc.WorkingDirectory = $work",
            "  $sc.WindowStyle = 1",
            f"  $sc.Description = {_ps_quote(DESCRIPTION)}",
            "  $sc.IconLocation = $icon",
            "  $sc.Save()",
            "  Write-Output \"OK $p\"",
            "} catch {",
            "  Write-Output \"FAIL $p :: $($_.Exception.Message)\"",
            "}",
        ]
    if pin and targets:
        lines.append(build_pin_powershell(targets[0]))
    return "\n".join(lines)


def build_pin_only_powershell(lnk: Path) -> str:
    """이미 있는 아이콘만 작업표시줄에 고정 (아이콘 재생성 없음)."""
    return "\n".join(
        [
            f"$check = {_ps_quote(lnk)}",
            "if (-not (Test-Path -LiteralPath $check)) {",
            "  Write-Output \"NOLNK $check\"",
            "  exit 1",
            "}",
            f"Write-Output \"OK {lnk}\"",
            build_pin_powershell(lnk),
        ]
    )


def powershell_command(script: str) -> list[str]:
    """코드페이지 영향을 받지 않는 -EncodedCommand 호출 인자."""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        encoded,
    ]


def create(
    root: Path | None = None,
    env: dict[str, str] | None = None,
    *,
    all_targets: bool = False,
    pin: bool = True,
    pin_only: bool = False,
) -> dict:
    """바탕화면에 실행파일 아이콘 생성 + 작업표시줄 고정.

    `pin_only=True` 면 아이콘을 다시 만들지 않고 고정만 시도한다.

    반환: ok · created · failed · pinned · message
    """
    root = root or board_root()
    launcher = root / LAUNCHER
    if not launcher.is_file():
        return {
            "ok": False,
            "created": [],
            "failed": [],
            "pinned": [],
            "message": f"{LAUNCHER} 없음 — 망고보드 폴더에서 실행하세요: {root}",
        }
    if not is_windows():
        return {
            "ok": False,
            "created": [],
            "failed": [],
            "pinned": [],
            "message": "바탕화면 바로가기(.lnk)는 Windows 에서만 생성됩니다.",
        }

    targets = shortcut_paths(root, env, all_targets=all_targets)
    if not targets:
        return {
            "ok": False,
            "created": [],
            "failed": [],
            "pinned": [],
            "message": "바탕화면 폴더를 찾지 못했습니다.",
        }
    if pin_only:
        script = build_pin_only_powershell(targets[0])
    else:
        script = build_powershell(root, targets, pin=pin)
    try:
        proc = subprocess.run(
            powershell_command(script),
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return {
            "ok": False,
            "created": [],
            "failed": [],
            "pinned": [],
            "message": f"PowerShell 실행 실패: {e}",
        }

    out = (proc.stdout or b"") + b"\n" + (proc.stderr or b"")
    for enc in ("utf-8", "cp949", "mbcs"):
        try:
            text = out.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        text = out.decode("utf-8", errors="replace")

    created = [l[3:].strip() for l in text.splitlines() if l.startswith("OK ")]
    failed = [l[5:].strip() for l in text.splitlines() if l.startswith("FAIL ")]
    pinned = [l[4:].strip() for l in text.splitlines() if l.startswith("PIN ")]
    ok = bool(created)
    if ok:
        if pin_only:
            message = "아이콘: " + "\n".join(created)
        else:
            message = "바탕화면에 [망고보드] 아이콘을 만들었습니다.\n" + "\n".join(created)
        if pinned:
            message += "\n작업표시줄에 고정했습니다."
        elif pin or pin_only:
            message += (
                "\n작업표시줄 자동고정이 Windows 에 막혔습니다 (Win10 1903+ · Win11).\n"
                "아이콘을 선택한 탐색기 창을 띄웠습니다 — 우클릭 →"
                " [작업 표시줄에 고정] 을 누르세요.\n"
                "Win11 이면 [자세히 보기] 안에 있습니다. 시작 메뉴에도 등록해 뒀습니다."
            )
    elif pin_only and "NOLNK" in text:
        message = (
            "바탕화면에 [망고보드] 아이콘이 없습니다 — 먼저 아이콘을 만드세요"
            " (망고보드_바탕화면아이콘.bat)."
        )
    else:
        message = "아이콘 생성 실패\n" + (text.strip() or "출력 없음")
    return {"ok": ok, "created": created, "failed": failed, "pinned": pinned, "message": message}


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    all_targets = "--all" in args  # 바탕화면 후보 전부 + 폴더 사본까지
    pin = "--no-pin" not in args  # 기본: 작업표시줄 고정까지 시도
    pin_only = "--pin-only" in args  # 아이콘 재생성 없이 고정만
    root = board_root()
    print("=" * 44)
    print("  망고보드 작업표시줄 고정" if pin_only else "  망고보드 바탕화면 아이콘 만들기")
    print(f"  경로: {root}")
    print("=" * 44)
    result = create(root, all_targets=all_targets, pin=pin, pin_only=pin_only)
    print(result["message"])
    for f in result["failed"]:
        print(f"  [실패] {f}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
