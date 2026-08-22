"""Windows 실행 파일의 줄바꿈 검증.

cmd.exe 는 LF 만 있는 `.bat` 을 제대로 파싱하지 못한다. 라벨·goto 가 깨지고
`set "PY=py -3"` 이 먹지 않아 `%PY%` 가 빈 값이 되며, 결국
`call -m pip install ...` 이 실행돼 `'-m' 은(는) 내부 또는 외부 명령...` 으로 죽는다.
그래서 모든 `.bat` 은 CRLF 여야 하고, `.gitattributes` 로 못박아야 한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BATS = sorted(p for p in ROOT.rglob("*.bat") if ".git" not in p.parts)


def test_bat_files_exist():
    assert BATS, ".bat 파일을 찾지 못했습니다."


@pytest.mark.parametrize("path", BATS, ids=lambda p: p.name)
def test_bat_uses_crlf(path: Path):
    raw = path.read_bytes()
    lone_lf = raw.replace(b"\r\n", b"").count(b"\n")
    assert lone_lf == 0, (
        f"{path.relative_to(ROOT)}: LF 만 있는 줄이 {lone_lf}개 —"
        " cmd.exe 가 파싱하지 못한다. CRLF 로 저장하세요."
    )


@pytest.mark.parametrize("path", BATS, ids=lambda p: p.name)
def test_bat_has_no_bom(path: Path):
    """.bat 에 BOM 이 붙으면 첫 줄(@echo off)이 깨진다."""
    assert not path.read_bytes().startswith(b"\xef\xbb\xbf"), f"{path.name}: BOM 제거 필요"


def test_gitattributes_pins_crlf():
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.bat text eol=crlf" in text
    assert "*.cmd text eol=crlf" in text


def test_run_bat_sets_python_before_use():
    """`set \"PY=...\"` 뒤에 `%PY%` 를 쓰는 구조가 유지되는지 (빈 값이면 pip 이 죽는다)."""
    text = (ROOT / "run.bat").read_text(encoding="utf-8")
    assert 'set "PY=' in text
    assert "%PY% -m pip install" in text
    assert text.index('set "PY=') < text.index("%PY% -m pip install")
