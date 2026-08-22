"""망고 "검색필터명" 에 넣을 엑셀 열 선택 — 회귀 테스트.

★요건(2026-08-20): 검색필터명 = "최종 카테고리명".
옛 엑셀(그 열이 없는 경우)은 "상위 최종 카테고리명" 으로 대체한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import collect as C  # noqa: E402


def _write(fp: Path, headers: list[str], *rows: list[str]) -> str:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(fp)
    return str(fp)


def test_prefers_final_category_name(tmp_path: Path):
    fp = _write(
        tmp_path / "both.xlsx",
        ["상위 최종 카테고리명", "최종 카테고리명", "최종 카테고리 URL주소"],
        ["MEN", "MEN 스니커즈", "https://example.com/a"],
    )
    assert [r["label"] for r in C.read_excel(fp)] == ["MEN 스니커즈"]


def test_falls_back_to_top_final_category_name(tmp_path: Path):
    fp = _write(
        tmp_path / "old.xlsx",
        ["상위 최종 카테고리명", "최종 카테고리 URL주소"],
        ["MEN 스니커즈", "https://example.com/a"],
    )
    assert [r["label"] for r in C.read_excel(fp)] == ["MEN 스니커즈"]


def test_missing_both_label_columns_is_an_error(tmp_path: Path):
    fp = _write(
        tmp_path / "bad.xlsx",
        ["엉뚱한열", "최종 카테고리 URL주소"],
        ["MEN", "https://example.com/a"],
    )
    with pytest.raises(SystemExit):
        C.read_excel(fp)


def test_default_save_count_is_50():
    """★요건(2026-08-20): 행당 저장상품수 3 → 50."""
    assert C.DEFAULT_SAVE_COUNT == 50
