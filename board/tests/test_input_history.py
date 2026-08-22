"""입력 이력(사이트명·목록 URL 리스트박스) 저장·불러오기 검증."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import input_history as ih  # noqa: E402


def test_load_missing_file_is_empty(tmp_path):
    assert ih.load(tmp_path / "no_such.json") == []


def test_remember_adds_and_persists(tmp_path):
    path = tmp_path / ".recent.json"
    result = ih.remember(path, "MUSINSA.com")
    assert result == ["MUSINSA.com"]
    assert ih.load(path) == ["MUSINSA.com"]


def test_remember_moves_existing_value_to_front():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / ".recent.json"
        ih.remember(path, "A")
        ih.remember(path, "B")
        result = ih.remember(path, "A")
        assert result == ["A", "B"]


def test_remember_dedupes_and_caps_length(tmp_path):
    path = tmp_path / ".recent.json"
    for i in range(15):
        ih.remember(path, f"v{i}", limit=5)
    result = ih.load(path)
    assert len(result) == 5
    assert result[0] == "v14"          # 가장 최근이 맨 앞


def test_remember_ignores_blank_value(tmp_path):
    path = tmp_path / ".recent.json"
    ih.remember(path, "kept")
    result = ih.remember(path, "   ")
    assert result == ["kept"]
    assert ih.load(path) == ["kept"]


def test_remember_strips_whitespace(tmp_path):
    path = tmp_path / ".recent.json"
    result = ih.remember(path, "  MUSINSA.com  ")
    assert result == ["MUSINSA.com"]


def test_corrupted_file_is_treated_as_empty(tmp_path):
    path = tmp_path / ".recent.json"
    path.write_text("not json", encoding="utf-8")
    assert ih.load(path) == []
    assert ih.remember(path, "A") == ["A"]
