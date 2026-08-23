"""P5_101 보드 탭 — 사이트명·목록 URL 리스트박스(이력) 연동 검증."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = "P5_101_카테고리매핑_필터세부설정"


def test_input_history_wired_for_site_and_url():
    """사이트명·목록 URL 을 리스트박스(콤보박스)로 고를 수 있고, 이력이 저장된다."""
    text = (ROOT / "board" / "app.py").read_text(encoding="utf-8")
    for needed in (
        "self.cbo_p5m_site",
        "self.cbo_p5m_url",
        "self._remember_p5m_inputs",
        "P5M_SITE_HISTORY",
        "P5M_URL_HISTORY",
    ):
        assert needed in text, f"board/app.py 에 {needed} 가 없습니다."


def test_recent_history_files_are_gitignored():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert f"{FOLDER}/.recent_site.json" in text
    assert f"{FOLDER}/.recent_url.json" in text
