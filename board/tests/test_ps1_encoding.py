"""PowerShell 스크립트 인코딩 검증.

Windows PowerShell 5.1 은 BOM 없는 `.ps1` 을 시스템 ANSI 코드페이지(한글 Windows
는 CP949)로 읽는다. 한글이나 `→`·`※` 같은 기호가 들어 있으면 2바이트로 잘못
소비되면서 뒤따르는 큰따옴표를 삼켜 문자열이 깨지고 구문 오류가 난다.
그래서 한글이 든 `.ps1` 은 **UTF-8 BOM** 이 반드시 있어야 한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = sorted((ROOT / "scripts").glob("*.ps1"))

BOM = b"\xef\xbb\xbf"


def _dbcs_read(body: bytes) -> str:
    """CP949(DBCS) 디코더 흉내 — 0x81~0xFE 는 lead 로 보고 다음 바이트를 함께 삼킨다."""
    out: list[str] = []
    i = 0
    while i < len(body):
        b = body[i]
        if 0x81 <= b <= 0xFE and i + 1 < len(body):
            out.append("?")
            i += 2
        else:
            out.append(chr(b))
            i += 1
    return "".join(out)


def test_scripts_exist():
    assert SCRIPTS, "scripts/*.ps1 을 찾지 못했습니다."


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_ps1_has_utf8_bom(path: Path):
    assert path.read_bytes().startswith(BOM), (
        f"{path.name}: UTF-8 BOM 이 없습니다. "
        "PowerShell 5.1 이 CP949 로 읽어 구문 오류가 납니다."
    )


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_ps1_body_is_valid_utf8(path: Path):
    body = path.read_bytes()
    body = body[len(BOM) :] if body.startswith(BOM) else body
    body.decode("utf-8")  # 깨지면 UnicodeDecodeError


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_bom_needed_when_cp949_would_break_quotes(path: Path):
    """BOM 이 필요한 이유를 고정 — CP949 로 읽으면 따옴표가 사라지는 파일이 있다.

    그런 파일에 BOM 이 없으면 `test_ps1_has_utf8_bom` 이 잡는다. 이 테스트는
    따옴표 소실이라는 실제 파손 조건 자체를 기록해 둔다.
    """
    raw = path.read_bytes()
    body = raw[len(BOM) :] if raw.startswith(BOM) else raw
    utf8_quotes = body.decode("utf-8").count('"')
    dbcs_quotes = _dbcs_read(body).count('"')
    if dbcs_quotes != utf8_quotes:
        assert raw.startswith(BOM), (
            f"{path.name}: CP949 로 읽으면 따옴표가 "
            f"{utf8_quotes - dbcs_quotes}개 사라진다 — BOM 이 반드시 필요하다."
        )
