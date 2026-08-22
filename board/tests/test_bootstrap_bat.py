"""AI보드 루트의 망고보드 부트스트랩(망고보드_시작.bat) 검증.

부모 저장소 루트에 있는 파일이라 망고보드 폴더에서 상위 1단계를 본다.
독립 저장소로 clone 한 경우엔 이 파일이 없으므로 그 때는 건너뛴다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT.parent / "망고보드_시작.bat"

pytestmark = pytest.mark.skipif(
    not BOOTSTRAP.is_file(), reason="독립 저장소에는 부트스트랩이 없음"
)


def _text() -> str:
    return BOOTSTRAP.read_text(encoding="utf-8", errors="replace")


def test_bootstrap_pulls_then_copies_then_runs():
    text = _text()
    for step in ("git pull origin main", "robocopy", "board\\desktop_icon.py", "run.bat"):
        assert step in text, f"부트스트랩에 {step} 없음"


def test_bootstrap_forces_overwrite_of_stale_files():
    """/IS /IT 없으면 타임스탬프가 같은 옛 파일이 남는다 (v1.6.2 사고 재발 방지)."""
    line = next(l for l in _text().splitlines() if l.strip().startswith("robocopy"))
    assert "/IS" in line and "/IT" in line


def test_bootstrap_protects_user_data():
    line = next(l for l in _text().splitlines() if l.strip().startswith("robocopy"))
    for keep in ("run-logs", "output", ".chrome-profile", "*.xlsx", ".site_options.json"):
        assert keep in line, f"{keep} 가 보호 목록에 없음"


def test_bootstrap_targets_standalone_folder():
    text = _text()
    assert "D:\\My_Project\\Mango_Helper_AI_Board" in text
    # AI보드 폴더를 대상으로 삼으면 안 된다
    assert "set \"DST=D:\\My_Project\\AI_Program_Main_Board\"" not in text
