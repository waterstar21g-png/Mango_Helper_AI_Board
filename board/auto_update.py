"""망고보드 자동 반영 — 바탕화면 아이콘(run.bat) 실행 시 최신 소스로 갱신.

- `VERSION.txt` 를 원격과 비교해 **더 높을 때만** 내려받는다
- PC 폴더에 `.git` 이 없어도 동작한다 (GitHub ZIP → 필요한 파일만 덮어쓰기)
- `.git` 이 있으면 `git pull` 을 먼저 시도한다
- 사용자 데이터(로그·엑셀·크롬 프로필·캐시)는 건드리지 않는다
- 표준 라이브러리만 사용 (urllib · zipfile)

단독 실행:
    py -3 board\\auto_update.py          # 갱신 확인 후 필요 시 반영
    py -3 board\\auto_update.py --check   # 확인만 (반영 안 함)
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

OWNER = "waterstar21g-png"
STANDALONE_REPO = "Mango_Helper_AI_Board"
PARENT_REPO = "AI_Program_Main_Board"
BRANCH = "main"
PARENT_SUBDIR = "Mango_Helper_AI_Board"

TIMEOUT = 20

# 갱신 시 덮지 않는 것 — 사용자 데이터·실행 산출물
PROTECTED = (
    ".git",
    "__pycache__",
    ".chrome-profile",
    "run-logs",
    "output",
    ".translate_options.json",
    ".site_options.json",
    ".last_mango_url",
    "icon-last.log",
)
PROTECTED_SUFFIXES = (".xlsx", ".lnk", ".pyc", ".log")


def board_root() -> Path:
    return Path(__file__).resolve().parent.parent


def parse_version(text: str) -> str:
    if not text:
        return ""
    m = re.search(r"(?:버전|version)\s*([0-9]+(?:\.[0-9]+)+)", text, re.I)
    if not m:
        m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", text)
    return m.group(1) if m else ""


def version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in str(version or "").split("."):
        digits = re.sub(r"\D", "", chunk)
        parts.append(int(digits) if digits else 0)
    return tuple(parts) or (0,)


def is_newer(remote: str, local: str) -> bool:
    if not remote:
        return False
    if not local:
        return True
    return version_tuple(remote) > version_tuple(local)


def local_version(root: Path | None = None) -> str:
    root = root or board_root()
    try:
        return parse_version((root / "VERSION.txt").read_text(encoding="utf-8"))
    except OSError:
        return ""


# ── 원격 소스 (독립 repo 우선 → 부모 repo 폴백) ───────────────────


def sources() -> list[dict]:
    raw = "https://raw.githubusercontent.com"
    gh = "https://github.com"
    return [
        {
            "name": f"{STANDALONE_REPO} (독립)",
            "version_url": f"{raw}/{OWNER}/{STANDALONE_REPO}/{BRANCH}/VERSION.txt",
            "zip_url": f"{gh}/{OWNER}/{STANDALONE_REPO}/archive/refs/heads/{BRANCH}.zip",
            "subdir": "",
        },
        {
            "name": f"{PARENT_REPO}/{PARENT_SUBDIR} (부모)",
            "version_url": (
                f"{raw}/{OWNER}/{PARENT_REPO}/{BRANCH}/{PARENT_SUBDIR}/VERSION.txt"
            ),
            "zip_url": f"{gh}/{OWNER}/{PARENT_REPO}/archive/refs/heads/{BRANCH}.zip",
            "subdir": PARENT_SUBDIR,
        },
    ]


def fetch_text(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:  # noqa: S310
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError):
        return ""


def pick_source() -> tuple[dict | None, str]:
    """버전을 읽을 수 있는 소스 중 가장 높은 버전을 고른다."""
    best: dict | None = None
    best_ver = ""
    for src in sources():
        ver = parse_version(fetch_text(src["version_url"]))
        if ver and is_newer(ver, best_ver):
            best, best_ver = src, ver
    return best, best_ver


# ── 반영 ─────────────────────────────────────────────────────────


def is_protected(rel_path: str) -> bool:
    parts = [p for p in Path(rel_path).parts if p not in (".", "")]
    if any(p in PROTECTED for p in parts):
        return True
    return Path(rel_path).suffix.lower() in PROTECTED_SUFFIXES


def apply_zip(zip_path: Path, root: Path, subdir: str) -> int:
    """ZIP 안의 (subdir 하위) 파일을 root 에 덮어쓴다. 반환: 쓴 파일 수."""
    written = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            parts = Path(info.filename).parts
            if len(parts) < 2:
                continue
            inner = parts[1:]  # GitHub ZIP 최상위 폴더 제거
            if subdir:
                if not inner or inner[0] != subdir:
                    continue
                inner = inner[1:]
            if not inner:
                continue
            rel = Path(*inner)
            if is_protected(str(rel)):
                continue
            dest = root / rel
            if ".." in rel.parts:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src_f, open(dest, "wb") as out:
                shutil.copyfileobj(src_f, out)
            written += 1
    return written


def download_zip(url: str, dest_dir: Path) -> Path | None:
    dest = dest_dir / "mango.zip"
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT * 3) as resp:  # noqa: S310
            dest.write_bytes(resp.read())
        return dest
    except (urllib.error.URLError, OSError, ValueError):
        return None


def git_repo_dir(root: Path) -> Path | None:
    """이 폴더 또는 상위(부모 저장소 하위 폴더인 경우)의 git 루트."""
    for candidate in (root, *root.parents):
        if (candidate / ".git").is_dir():
            return candidate
    return None


def git_pull(root: Path) -> bool:
    """git 저장소(자기 폴더 또는 부모)면 pull 로 갱신 (빠른 경로)."""
    repo = git_repo_dir(root)
    if repo is None:
        return False
    try:
        proc = subprocess.run(
            ["git", "pull", "origin", BRANCH],
            cwd=str(repo),
            capture_output=True,
            timeout=180,
            check=False,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def update_if_newer(root: Path | None = None, *, check_only: bool = False) -> dict:
    """원격이 더 높으면 반영. 반환: updated · before · after · remote · message."""
    root = root or board_root()
    before = local_version(root)
    src, remote = pick_source()

    if not remote:
        return {
            "updated": False,
            "before": before,
            "after": before,
            "remote": "",
            "message": f"v{before or '?'} — 최신 버전 확인 실패 (오프라인?) · 그대로 실행",
        }

    if not is_newer(remote, before):
        return {
            "updated": False,
            "before": before,
            "after": before,
            "remote": remote,
            "message": f"v{before} — 이미 최신입니다.",
        }

    if check_only:
        return {
            "updated": False,
            "before": before,
            "after": before,
            "remote": remote,
            "message": f"새 버전 v{remote} 있음 (현재 v{before or '?'})",
        }

    if git_pull(root):
        after = local_version(root)
        return {
            "updated": after != before,
            "before": before,
            "after": after,
            "remote": remote,
            "message": f"git pull 로 갱신: v{before or '?'} → v{after or '?'}",
        }

    with tempfile.TemporaryDirectory(prefix="mango_update_") as tmp:
        tmp_dir = Path(tmp)
        zip_path = download_zip(str(src["zip_url"]), tmp_dir) if src else None
        if zip_path is None:
            return {
                "updated": False,
                "before": before,
                "after": before,
                "remote": remote,
                "message": f"v{remote} 내려받기 실패 · 현재 v{before or '?'} 로 실행",
            }
        try:
            written = apply_zip(zip_path, root, str(src["subdir"]) if src else "")
        except (zipfile.BadZipFile, OSError) as e:
            return {
                "updated": False,
                "before": before,
                "after": before,
                "remote": remote,
                "message": f"갱신 실패({e}) · 현재 v{before or '?'} 로 실행",
            }

    after = local_version(root)
    return {
        "updated": after != before,
        "before": before,
        "after": after,
        "remote": remote,
        "message": (
            f"자동 반영 완료: v{before or '?'} → v{after or '?'} "
            f"({src['name'] if src else '?'} · 파일 {written}개)"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    check_only = "--check" in args
    result = update_if_newer(check_only=check_only)
    print(f"[망고보드 자동갱신] {result['message']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
