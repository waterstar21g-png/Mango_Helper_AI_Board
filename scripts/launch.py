"""
망고보드 통합 실행기 — registry.json 기준으로 모든 프로그램 호출.

사용법:
  python scripts/launch.py list
  python scripts/launch.py board
  python scripts/launch.py p2_collect -- 엑셀.xlsx 50
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "programs" / "registry.json"


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def list_programs() -> None:
    data = load_registry()
    print(f"{data['display_name_ko']} ({data['repository']}) v", end="")
    ver = ROOT / "VERSION.txt"
    if ver.is_file():
        print(ver.read_text(encoding="utf-8").splitlines()[0])
    else:
        print("?")
    print()
    for p in data["programs"]:
        tab = f" [보드탭:{p['board_tab']}]" if p.get("board_tab") else ""
        login = f" — {p['login']}" if p.get("login") else ""
        print(f"  {p['id']:14}  {p['name']}{tab}")
        print(f"                  {p.get('description', '')}{login}")
        print(f"                  → {p['folder']}/{p.get('launcher', p['script'])}")
        print()


def build_command(script: Path, extra_args: list[str]) -> list[str]:
    """확장자별 실행 명령 — .py 는 파이썬, .ps1/.bat 는 Windows 셸."""
    suffix = script.suffix.lower()
    if suffix == ".ps1":
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            *extra_args,
        ]
    if suffix in (".bat", ".cmd"):
        return ["cmd", "/c", str(script), *extra_args]
    return [sys.executable, str(script), *extra_args]


def run_program(prog_id: str, extra_args: list[str]) -> int:
    data = load_registry()
    prog = next((p for p in data["programs"] if p["id"] == prog_id), None)
    if prog is None:
        print(f"알 수 없는 프로그램: {prog_id}", file=sys.stderr)
        print("사용: python scripts/launch.py list", file=sys.stderr)
        return 1

    folder = ROOT / prog["folder"] if prog["folder"] != "." else ROOT
    if prog["id"] == "board":
        cmd = [sys.executable, str(ROOT / "board" / "app.py")]
    else:
        script = folder / prog["script"]
        if not script.is_file():
            print(f"스크립트 없음: {script}", file=sys.stderr)
            return 1
        cmd = build_command(script, extra_args)

    print(f"[망고보드] {prog['name']} 실행")
    print(f"  cwd: {folder}")
    print(f"  cmd: {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=str(folder))


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    if args[0] == "list":
        list_programs()
        return 0
    return run_program(args[0], args[1:])


if __name__ == "__main__":
    raise SystemExit(main())
