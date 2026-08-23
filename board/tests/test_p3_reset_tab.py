"""P3_설정수정_카테고리매핑초기화 — 보드 연동 검증 (Tk 없이 소스·레지스트리만 확인)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FOLDER = "P3_설정수정_카테고리매핑초기화"
SCRIPT = "reset_category_mapping.py"
PROGRAM_ID = "p3_reset_mapping"
TAB = "p3_reset"


def test_program_files_exist():
    base = ROOT / FOLDER
    assert (base / SCRIPT).is_file()
    assert (base / "run.bat").is_file()
    assert (base / "__init__.py").is_file()
    assert (base / "README.md").is_file()
    assert (base / "tests").is_dir()


def test_run_bat_calls_the_script():
    text = (ROOT / FOLDER / "run.bat").read_text(encoding="utf-8")
    assert SCRIPT in text


def test_registry_entry():
    data = json.loads((ROOT / "programs" / "registry.json").read_text(encoding="utf-8"))
    entry = next((p for p in data["programs"] if p["id"] == PROGRAM_ID), None)
    assert entry is not None, f"registry.json 에 {PROGRAM_ID} 가 없습니다."
    assert entry["folder"] == FOLDER
    assert entry["script"] == SCRIPT
    assert entry["board_tab"] == TAB


def test_board_app_wires_the_tab():
    """모듈 로드 · 사이드 버튼 · 프레임 · _show 분기가 모두 있어야 탭이 열린다."""
    text = (ROOT / "board" / "app.py").read_text(encoding="utf-8")
    for needed in (
        f'"{FOLDER}"',
        f'"{SCRIPT}"',
        "self.btn_p3_reset",
        "self.frame_p3_reset",
        "self._build_p3_reset(",
        f'elif which == "{TAB}":',
        "def _run_p3_reset(",
        "def _stop_p3_reset(",
        "def _check_p3rst_rows(",
    ):
        assert needed in text, f"board/app.py 에 {needed} 가 없습니다."


def test_stop_flag_is_gitignored():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert f"{FOLDER}/.reset_stop" in text


def test_input_history_wired_for_site_and_url():
    """사이트명·작업 URL 을 리스트박스(콤보박스)로 고를 수 있고, 이력이 저장된다."""
    text = (ROOT / "board" / "app.py").read_text(encoding="utf-8")
    for needed in (
        "self.cbo_p3rst_site",
        "self.cbo_p3rst_url",
        "self._remember_p3rst_inputs",
        "P3RST_SITE_HISTORY",
        "P3RST_URL_HISTORY",
    ):
        assert needed in text, f"board/app.py 에 {needed} 가 없습니다."


def test_recent_history_files_are_gitignored():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert f"{FOLDER}/.recent_site.json" in text
    assert f"{FOLDER}/.recent_url.json" in text
