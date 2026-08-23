"""마켓별 카테고리 JSON 캐시 테스트 — 요건 2026-08-23.

"구축된 DB 내용을 파일(JSON)로 저장해 매번 엑셀을 다시 읽지 않고
캐시로 재사용" 요건을 검증한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import market_cache  # noqa: E402

SAMPLE = {
    "AUC20": ["패션잡화 > 남성 모자 > 비니", "패션잡화 > 남성 모자 > 캡"],
    "11ST": ["가방/잡화 > 모자 > 야구모자"],
}


def test_save_creates_file_and_load_roundtrips(tmp_path):
    path = tmp_path / "cache.json"
    saved = market_cache.save(SAMPLE, path)
    assert saved == path
    assert path.exists()

    loaded = market_cache.load(path)
    assert loaded == SAMPLE


def test_save_normalizes_market_code_case():
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "cache.json"
        market_cache.save({"auc20": ["A > B"]}, path)
        loaded = market_cache.load(path)
        assert "AUC20" in loaded
        assert loaded["AUC20"] == ["A > B"]


def test_save_drops_blank_paths(tmp_path):
    path = tmp_path / "cache.json"
    market_cache.save({"AUC20": ["A > B", "", "  ", None]}, path)
    loaded = market_cache.load(path)
    assert loaded["AUC20"] == ["A > B"]


def test_load_missing_file_returns_empty_dict(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    assert market_cache.load(missing) == {}


def test_load_corrupt_file_returns_empty_dict(tmp_path):
    path = tmp_path / "cache.json"
    path.write_text("{not valid json", encoding="utf-8")
    assert market_cache.load(path) == {}


def test_exists_reflects_file_presence(tmp_path):
    path = tmp_path / "cache.json"
    assert market_cache.exists(path) is False
    market_cache.save(SAMPLE, path)
    assert market_cache.exists(path) is True


def test_stats_reports_market_and_path_counts(tmp_path):
    path = tmp_path / "cache.json"
    market_cache.save(SAMPLE, path)
    info = market_cache.stats(path)
    assert info["market_count"] == 2
    assert info["path_count"] == 3
    assert info["exists"] is True


def test_stats_on_missing_cache(tmp_path):
    missing = tmp_path / "nope.json"
    info = market_cache.stats(missing)
    assert info["market_count"] == 0
    assert info["path_count"] == 0
    assert info["exists"] is False


def test_default_cache_path_is_under_data_dir():
    assert market_cache.DEFAULT_CACHE_PATH.parent.name == "data"
    assert market_cache.DEFAULT_CACHE_PATH.name == "market_categories_cache.json"


def test_repo_cache_file_exists_and_has_all_six_markets():
    """★요건: 실제 6개 마켓 카테고리를 커밋된 캐시 파일로도 확인할 수 있어야 한다."""
    if not market_cache.exists():
        return  # 캐시 파일이 아직 없는 환경(최초 클론 등)에서는 건너뛴다
    data = market_cache.load()
    assert len(data) == 6
    assert sum(len(v) for v in data.values()) > 10_000
